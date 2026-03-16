"""PostgreSQL-based backend for vaultit."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta

from vaultit.backends.base import VaultItBackend
from vaultit.exceptions import (
    BackendError,
    HandoffNotFoundError,
    ProjectNotInitializedError,
    SessionNotFoundError,
)
from vaultit.models import (
    AuditEvent,
    Handoff,
    HandoffDiff,
    ProjectConfig,
    Session,
)

logger = logging.getLogger("vaultit.backends.postgres")

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    backend TEXT NOT NULL DEFAULT 'postgres',
    coordination TEXT NOT NULL DEFAULT 'sequential',
    schema_version TEXT NOT NULL DEFAULT '1.0',
    org_id TEXT NOT NULL DEFAULT '',
    user_id TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id),
    created_at TIMESTAMPTZ NOT NULL,
    closed_at TIMESTAMPTZ,
    agent TEXT NOT NULL DEFAULT 'custom',
    user_id TEXT NOT NULL DEFAULT '',
    org_id TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS handoffs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    project_id TEXT NOT NULL REFERENCES projects(project_id),
    version INTEGER NOT NULL,
    schema_version TEXT NOT NULL DEFAULT '1.0',
    agent TEXT NOT NULL DEFAULT 'custom',
    agent_version TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    tasks JSONB NOT NULL DEFAULT '[]',
    decisions JSONB NOT NULL DEFAULT '[]',
    open_questions JSONB NOT NULL DEFAULT '[]',
    next_steps JSONB NOT NULL DEFAULT '[]',
    raw_notes TEXT NOT NULL DEFAULT '',
    metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS locks (
    project_id TEXT PRIMARY KEY REFERENCES projects(project_id),
    session_id TEXT NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    agent TEXT NOT NULL DEFAULT 'custom'
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    session_id TEXT NOT NULL DEFAULT '',
    user_id TEXT NOT NULL DEFAULT '',
    org_id TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL,
    agent TEXT NOT NULL DEFAULT '',
    timestamp TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    ip_address TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    user_id TEXT NOT NULL,
    org_id TEXT NOT NULL DEFAULT '',
    scopes TEXT[] NOT NULL DEFAULT ARRAY['read','write'],
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    revoked BOOLEAN NOT NULL DEFAULT FALSE
);
"""

_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_handoffs_session ON handoffs(session_id);
CREATE INDEX IF NOT EXISTS idx_handoffs_project_version ON handoffs(project_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_audit_project ON audit_events(project_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_apikeys_hash ON api_keys(key_hash);
"""


class PostgresBackend(VaultItBackend):
    """Stores vaultit data in PostgreSQL.

    Requires ``psycopg2-binary``.  Connection string from
    ``VAULTIT_DATABASE_URL`` env var.
    """

    def __init__(self, database_url: str | None = None) -> None:
        try:
            import psycopg2
            from psycopg2 import pool as pg_pool
        except ImportError:
            raise BackendError(
                "psycopg2 is required for PostgresBackend. "
                "Install with: pip install vaultit[postgres]"
            )

        self._database_url = database_url or os.environ.get("VAULTIT_DATABASE_URL", "")
        if not self._database_url:
            raise BackendError(
                "VAULTIT_DATABASE_URL env var is not set. "
                "Format: postgresql://user:password@host:port/dbname"
            )

        self._psycopg2 = psycopg2
        try:
            self._pool = pg_pool.SimpleConnectionPool(
                minconn=1, maxconn=10, dsn=self._database_url,
            )
        except psycopg2.Error as exc:
            raise BackendError(f"Failed to create connection pool: {exc}", cause=exc) from exc

        self._initialized = False

    def _get_conn(self):
        try:
            return self._pool.getconn()
        except self._psycopg2.Error as exc:
            raise BackendError(f"Failed to get connection: {exc}", cause=exc) from exc

    def _put_conn(self, conn):
        self._pool.putconn(conn)

    def _ensure_init(self) -> None:
        if not self._initialized:
            conn = self._get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                        "WHERE table_name = 'projects')"
                    )
                    exists = cur.fetchone()[0]
                conn.commit()
                if not exists:
                    raise ProjectNotInitializedError("postgres")
                self._initialized = True
            except ProjectNotInitializedError:
                raise
            except self._psycopg2.Error as exc:
                conn.rollback()
                raise BackendError(f"Failed to check initialization: {exc}", cause=exc) from exc
            finally:
                self._put_conn(conn)

    # ── interface ──

    def init_project(self, config: ProjectConfig) -> None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(_SCHEMA_SQL)
                cur.execute(_INDEX_SQL)
                cur.execute(
                    """INSERT INTO projects
                       (project_id, name, created_at, backend, coordination, schema_version)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT (project_id) DO UPDATE SET
                       name = EXCLUDED.name,
                       backend = EXCLUDED.backend,
                       coordination = EXCLUDED.coordination""",
                    (
                        config.project_id,
                        config.name,
                        config.created_at,
                        config.backend,
                        config.coordination,
                        config.schema_version,
                    ),
                )
            conn.commit()
            self._initialized = True
        except self._psycopg2.Error as exc:
            conn.rollback()
            raise BackendError(f"Failed to init project: {exc}", cause=exc) from exc
        finally:
            self._put_conn(conn)
        logger.info("Initialized Postgres project '%s'", config.project_id)

    def write_handoff(self, handoff: Handoff) -> str:
        self._ensure_init()
        data = handoff.model_dump(mode="json")
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO handoffs
                       (id, session_id, project_id, version, schema_version,
                        agent, agent_version, created_at, updated_at,
                        tasks, decisions, open_questions, next_steps,
                        raw_notes, metadata)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (id) DO UPDATE SET
                       version = EXCLUDED.version,
                       updated_at = EXCLUDED.updated_at,
                       tasks = EXCLUDED.tasks,
                       decisions = EXCLUDED.decisions,
                       open_questions = EXCLUDED.open_questions,
                       next_steps = EXCLUDED.next_steps,
                       raw_notes = EXCLUDED.raw_notes,
                       metadata = EXCLUDED.metadata""",
                    (
                        data["id"],
                        data["session_id"],
                        data["project_id"],
                        data["version"],
                        data["schema_version"],
                        data["agent"],
                        data["agent_version"],
                        data["created_at"],
                        data["updated_at"],
                        json.dumps(data["tasks"]),
                        json.dumps(data["decisions"]),
                        json.dumps(data["open_questions"]),
                        json.dumps(data["next_steps"]),
                        data["raw_notes"],
                        json.dumps(data["metadata"]),
                    ),
                )
            conn.commit()
        except self._psycopg2.Error as exc:
            conn.rollback()
            raise BackendError(f"Failed to write handoff: {exc}", cause=exc) from exc
        finally:
            self._put_conn(conn)
        logger.debug("Wrote handoff %s v%d", handoff.session_id, handoff.version)
        return handoff.id

    def _row_to_handoff(self, row: dict) -> Handoff:
        d = dict(row)
        for field in ("tasks", "decisions", "open_questions", "next_steps", "metadata"):
            if isinstance(d[field], str):
                d[field] = json.loads(d[field])
        return Handoff.model_validate(d)

    def _fetchone_dict(self, cur) -> dict | None:
        row = cur.fetchone()
        if row is None:
            return None
        cols = [desc[0] for desc in cur.description]
        return dict(zip(cols, row))

    def _fetchall_dicts(self, cur) -> list[dict]:
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in rows]

    def read_handoff(self, session_id: str, version: int | None = None) -> Handoff:
        self._ensure_init()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                if version is not None:
                    cur.execute(
                        "SELECT * FROM handoffs WHERE session_id = %s AND version = %s",
                        (session_id, version),
                    )
                else:
                    cur.execute(
                        "SELECT * FROM handoffs WHERE session_id = %s ORDER BY version DESC LIMIT 1",
                        (session_id,),
                    )
                row = self._fetchone_dict(cur)
            conn.commit()
        except self._psycopg2.Error as exc:
            conn.rollback()
            raise BackendError(f"Failed to read handoff: {exc}", cause=exc) from exc
        finally:
            self._put_conn(conn)
        if row is None:
            raise HandoffNotFoundError(session_id, version)
        return self._row_to_handoff(row)

    def read_latest_handoff(self, project_id: str) -> Handoff | None:
        self._ensure_init()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM handoffs WHERE project_id = %s ORDER BY updated_at DESC LIMIT 1",
                    (project_id,),
                )
                row = self._fetchone_dict(cur)
            conn.commit()
        except self._psycopg2.Error as exc:
            conn.rollback()
            raise BackendError(f"Failed to read latest handoff: {exc}", cause=exc) from exc
        finally:
            self._put_conn(conn)
        if row is None:
            return None
        return self._row_to_handoff(row)

    def list_sessions(self, project_id: str) -> list[Session]:
        self._ensure_init()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, project_id, created_at, closed_at, agent, user_id "
                    "FROM sessions WHERE project_id = %s ORDER BY created_at",
                    (project_id,),
                )
                rows = self._fetchall_dicts(cur)
            conn.commit()
        except self._psycopg2.Error as exc:
            conn.rollback()
            raise BackendError(f"Failed to list sessions: {exc}", cause=exc) from exc
        finally:
            self._put_conn(conn)
        return [Session.model_validate(r) for r in rows]

    def write_session(self, session: Session) -> None:
        self._ensure_init()
        data = session.model_dump(mode="json")
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO sessions (id, project_id, created_at, closed_at, agent, user_id)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT (id) DO UPDATE SET
                       closed_at = EXCLUDED.closed_at,
                       agent = EXCLUDED.agent""",
                    (
                        data["id"],
                        data["project_id"],
                        data["created_at"],
                        data["closed_at"],
                        data["agent"],
                        data["user_id"],
                    ),
                )
            conn.commit()
        except self._psycopg2.Error as exc:
            conn.rollback()
            raise BackendError(f"Failed to write session: {exc}", cause=exc) from exc
        finally:
            self._put_conn(conn)
        logger.debug("Wrote session %s", session.id)

    def read_session(self, session_id: str) -> Session:
        self._ensure_init()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, project_id, created_at, closed_at, agent, user_id "
                    "FROM sessions WHERE id = %s",
                    (session_id,),
                )
                row = self._fetchone_dict(cur)
            conn.commit()
        except self._psycopg2.Error as exc:
            conn.rollback()
            raise BackendError(f"Failed to read session: {exc}", cause=exc) from exc
        finally:
            self._put_conn(conn)
        if row is None:
            raise SessionNotFoundError(session_id)
        return Session.model_validate(row)

    def project_exists(self, project_id: str) -> bool:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = 'projects')"
                )
                table_exists = cur.fetchone()[0]
                if not table_exists:
                    conn.commit()
                    return False
                cur.execute(
                    "SELECT COUNT(*) FROM projects WHERE project_id = %s",
                    (project_id,),
                )
                count = cur.fetchone()[0]
            conn.commit()
            return count > 0
        except self._psycopg2.Error:
            conn.rollback()
            return False
        finally:
            self._put_conn(conn)

    def read_config(self) -> ProjectConfig:
        self._ensure_init()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT project_id, name, created_at, backend, coordination, schema_version "
                    "FROM projects LIMIT 1"
                )
                row = self._fetchone_dict(cur)
            conn.commit()
        except self._psycopg2.Error as exc:
            conn.rollback()
            raise BackendError(f"Failed to read config: {exc}", cause=exc) from exc
        finally:
            self._put_conn(conn)
        if row is None:
            raise ProjectNotInitializedError("postgres")
        return ProjectConfig.model_validate(row)

    def diff(self, project_id: str, from_version: int, to_version: int) -> HandoffDiff:
        self._ensure_init()
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM handoffs WHERE project_id = %s AND version = %s",
                    (project_id, from_version),
                )
                from_row = self._fetchone_dict(cur)
                cur.execute(
                    "SELECT * FROM handoffs WHERE project_id = %s AND version = %s",
                    (project_id, to_version),
                )
                to_row = self._fetchone_dict(cur)
            conn.commit()
        except self._psycopg2.Error as exc:
            conn.rollback()
            raise BackendError(f"Failed to compute diff: {exc}", cause=exc) from exc
        finally:
            self._put_conn(conn)

        if from_row is None:
            raise HandoffNotFoundError("unknown", from_version)
        if to_row is None:
            raise HandoffNotFoundError("unknown", to_version)

        old = self._row_to_handoff(from_row)
        new = self._row_to_handoff(to_row)
        return _compute_diff(old, new)

    # ── lock operations ──

    def acquire_lock(
        self, project_id: str, session_id: str, agent: str, ttl_seconds: int,
    ) -> bool:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=ttl_seconds)
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                # Clean expired
                cur.execute(
                    "DELETE FROM locks WHERE project_id = %s AND expires_at <= %s",
                    (project_id, now),
                )
                # Check existing
                cur.execute(
                    "SELECT session_id FROM locks WHERE project_id = %s",
                    (project_id,),
                )
                row = cur.fetchone()
                if row is not None and row[0] != session_id:
                    conn.commit()
                    return False
                # Upsert
                cur.execute(
                    """INSERT INTO locks (project_id, session_id, acquired_at, expires_at, agent)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (project_id) DO UPDATE SET
                       session_id = EXCLUDED.session_id,
                       acquired_at = EXCLUDED.acquired_at,
                       expires_at = EXCLUDED.expires_at,
                       agent = EXCLUDED.agent""",
                    (project_id, session_id, now, expires, agent),
                )
            conn.commit()
            return True
        except self._psycopg2.Error as exc:
            conn.rollback()
            raise BackendError(f"Failed to acquire lock: {exc}", cause=exc) from exc
        finally:
            self._put_conn(conn)

    def release_lock(self, project_id: str, session_id: str) -> bool:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT session_id FROM locks WHERE project_id = %s",
                    (project_id,),
                )
                row = cur.fetchone()
                if row is None or row[0] != session_id:
                    conn.commit()
                    return False
                cur.execute(
                    "DELETE FROM locks WHERE project_id = %s AND session_id = %s",
                    (project_id, session_id),
                )
            conn.commit()
            return True
        except self._psycopg2.Error as exc:
            conn.rollback()
            raise BackendError(f"Failed to release lock: {exc}", cause=exc) from exc
        finally:
            self._put_conn(conn)

    def is_locked(self, project_id: str) -> bool:
        now = datetime.now(timezone.utc)
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM locks WHERE project_id = %s AND expires_at <= %s",
                    (project_id, now),
                )
                cur.execute(
                    "SELECT COUNT(*) FROM locks WHERE project_id = %s",
                    (project_id,),
                )
                count = cur.fetchone()[0]
            conn.commit()
            return count > 0
        except self._psycopg2.Error:
            conn.rollback()
            return False
        finally:
            self._put_conn(conn)

    def lock_info(self, project_id: str) -> dict | None:
        now = datetime.now(timezone.utc)
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM locks WHERE project_id = %s AND expires_at <= %s",
                    (project_id, now),
                )
                cur.execute(
                    "SELECT session_id, agent, acquired_at, expires_at "
                    "FROM locks WHERE project_id = %s",
                    (project_id,),
                )
                row = cur.fetchone()
            conn.commit()
            if row is None:
                return None
            return {
                "session_id": row[0],
                "agent": row[1],
                "acquired_at": row[2].isoformat() if hasattr(row[2], 'isoformat') else row[2],
                "expires_at": row[3].isoformat() if hasattr(row[3], 'isoformat') else row[3],
            }
        except self._psycopg2.Error:
            conn.rollback()
            return None
        finally:
            self._put_conn(conn)

    # ── postgres-specific extensions ──

    def add_audit_event(self, event: AuditEvent) -> None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO audit_events
                       (id, project_id, session_id, user_id, org_id,
                        action, agent, timestamp, metadata, ip_address)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        event.id,
                        event.project_id,
                        event.session_id,
                        event.user_id,
                        event.org_id,
                        event.action,
                        event.agent,
                        event.timestamp,
                        json.dumps(event.metadata),
                        event.ip_address,
                    ),
                )
            conn.commit()
        except self._psycopg2.Error as exc:
            conn.rollback()
            raise BackendError(f"Failed to write audit event: {exc}", cause=exc) from exc
        finally:
            self._put_conn(conn)

    def ping(self) -> bool:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
            conn.commit()
            return result is not None and result[0] == 1
        except self._psycopg2.Error:
            conn.rollback()
            return False
        finally:
            self._put_conn(conn)


def _compute_diff(old: Handoff, new: Handoff) -> HandoffDiff:
    """Compute a structured diff between two handoffs."""
    old_tasks = {t.id: t for t in old.tasks}
    new_tasks = {t.id: t for t in new.tasks}

    tasks_added = [t for tid, t in new_tasks.items() if tid not in old_tasks]
    tasks_removed = [t for tid, t in old_tasks.items() if tid not in new_tasks]
    tasks_changed = [
        t for tid, t in new_tasks.items()
        if tid in old_tasks and t != old_tasks[tid]
    ]

    old_decs = {d.id for d in old.decisions}
    decisions_added = [d for d in new.decisions if d.id not in old_decs]

    old_q = set(old.open_questions)
    questions_added = [q for q in new.open_questions if q not in old_q]

    next_steps_changed = (
        new.next_steps if new.next_steps != old.next_steps else []
    )

    return HandoffDiff(
        from_version=old.version,
        to_version=new.version,
        tasks_added=tasks_added,
        tasks_removed=tasks_removed,
        tasks_changed=tasks_changed,
        decisions_added=decisions_added,
        questions_added=questions_added,
        next_steps_changed=next_steps_changed,
    )
