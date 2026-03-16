"""SQLite-based backend for vaultit."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

from vaultit.backends.base import VaultItBackend
from vaultit.exceptions import (
    BackendError,
    HandoffNotFoundError,
    ProjectNotInitializedError,
    SessionNotFoundError,
)
from vaultit.models import (
    Handoff,
    HandoffDiff,
    ProjectConfig,
    Session,
)

logger = logging.getLogger("vaultit.backends.sqlite")

_CK_DIR = ".vaultit"
_DB_NAME = "vaultit.db"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS project_config (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    backend TEXT NOT NULL DEFAULT 'sqlite',
    coordination TEXT NOT NULL DEFAULT 'sequential',
    schema_version TEXT NOT NULL DEFAULT '1.0'
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    closed_at TEXT,
    agent TEXT NOT NULL DEFAULT 'custom',
    user_id TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS handoffs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    schema_version TEXT NOT NULL DEFAULT '1.0',
    agent TEXT NOT NULL DEFAULT 'custom',
    agent_version TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    tasks TEXT NOT NULL DEFAULT '[]',
    decisions TEXT NOT NULL DEFAULT '[]',
    open_questions TEXT NOT NULL DEFAULT '[]',
    next_steps TEXT NOT NULL DEFAULT '[]',
    raw_notes TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS locks (
    project_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    agent TEXT NOT NULL DEFAULT 'custom'
);
"""


class SQLiteBackend(VaultItBackend):
    """Stores vaultit data in a SQLite database.

    Storage: ``<root>/.vaultit/vaultit.db``
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._ck = root / _CK_DIR
        self._db_path = self._ck / _DB_NAME

    @property
    def root(self) -> Path:
        return self._root

    @property
    def db_path(self) -> Path:
        return self._db_path

    # ── helpers ──

    def _connect(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            return conn
        except sqlite3.Error as exc:
            raise BackendError(
                f"Failed to connect to database: {self._db_path}", cause=exc,
            ) from exc

    def _ensure_init(self) -> None:
        if not self._db_path.exists():
            raise ProjectNotInitializedError(str(self._root))

    # ── interface ──

    def init_project(self, config: ProjectConfig) -> None:
        self._ck.mkdir(parents=True, exist_ok=True)
        # Also write config.json for backend auto-detection
        config_path = self._ck / "config.json"
        import os as _os
        tmp = config_path.with_suffix(".tmp")
        try:
            tmp.write_text(config.model_dump_json(indent=2), encoding="utf-8")
            _os.replace(str(tmp), str(config_path))
        except OSError:
            tmp.unlink(missing_ok=True)

        with self._connect() as conn:
            conn.executescript(_SCHEMA_SQL)
            conn.execute(
                """INSERT OR REPLACE INTO project_config
                   (project_id, name, created_at, backend, coordination, schema_version)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    config.project_id,
                    config.name,
                    config.created_at.isoformat(),
                    config.backend,
                    config.coordination,
                    config.schema_version,
                ),
            )
        logger.info("Initialized SQLite project '%s' at %s", config.project_id, self._db_path)

    def write_handoff(self, handoff: Handoff) -> str:
        self._ensure_init()
        data = handoff.model_dump(mode="json")
        try:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO handoffs
                       (id, session_id, project_id, version, schema_version,
                        agent, agent_version, created_at, updated_at,
                        tasks, decisions, open_questions, next_steps,
                        raw_notes, metadata)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
        except sqlite3.Error as exc:
            raise BackendError(f"Failed to write handoff: {exc}", cause=exc) from exc
        logger.debug("Wrote handoff %s v%d", handoff.session_id, handoff.version)
        return handoff.id

    def _row_to_handoff(self, row: sqlite3.Row) -> Handoff:
        d = dict(row)
        d["tasks"] = json.loads(d["tasks"])
        d["decisions"] = json.loads(d["decisions"])
        d["open_questions"] = json.loads(d["open_questions"])
        d["next_steps"] = json.loads(d["next_steps"])
        d["metadata"] = json.loads(d["metadata"])
        return Handoff.model_validate(d)

    def read_handoff(self, session_id: str, version: int | None = None) -> Handoff:
        self._ensure_init()
        try:
            with self._connect() as conn:
                if version is not None:
                    row = conn.execute(
                        "SELECT * FROM handoffs WHERE session_id = ? AND version = ?",
                        (session_id, version),
                    ).fetchone()
                    if row is None:
                        raise HandoffNotFoundError(session_id, version)
                else:
                    row = conn.execute(
                        "SELECT * FROM handoffs WHERE session_id = ? ORDER BY version DESC LIMIT 1",
                        (session_id,),
                    ).fetchone()
                    if row is None:
                        raise HandoffNotFoundError(session_id)
        except (HandoffNotFoundError, SessionNotFoundError):
            raise
        except sqlite3.Error as exc:
            raise BackendError(f"Failed to read handoff: {exc}", cause=exc) from exc
        return self._row_to_handoff(row)

    def read_latest_handoff(self, project_id: str) -> Handoff | None:
        self._ensure_init()
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM handoffs WHERE project_id = ? ORDER BY updated_at DESC LIMIT 1",
                    (project_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise BackendError(f"Failed to read latest handoff: {exc}", cause=exc) from exc
        if row is None:
            return None
        return self._row_to_handoff(row)

    def list_sessions(self, project_id: str) -> list[Session]:
        self._ensure_init()
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM sessions WHERE project_id = ? ORDER BY created_at",
                    (project_id,),
                ).fetchall()
        except sqlite3.Error as exc:
            raise BackendError(f"Failed to list sessions: {exc}", cause=exc) from exc
        return [Session.model_validate(dict(r)) for r in rows]

    def write_session(self, session: Session) -> None:
        self._ensure_init()
        data = session.model_dump(mode="json")
        try:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO sessions
                       (id, project_id, created_at, closed_at, agent, user_id)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        data["id"],
                        data["project_id"],
                        data["created_at"],
                        data["closed_at"],
                        data["agent"],
                        data["user_id"],
                    ),
                )
        except sqlite3.Error as exc:
            raise BackendError(f"Failed to write session: {exc}", cause=exc) from exc
        logger.debug("Wrote session %s", session.id)

    def read_session(self, session_id: str) -> Session:
        self._ensure_init()
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM sessions WHERE id = ?", (session_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise BackendError(f"Failed to read session: {exc}", cause=exc) from exc
        if row is None:
            raise SessionNotFoundError(session_id)
        return Session.model_validate(dict(row))

    def project_exists(self, project_id: str) -> bool:
        if not self._db_path.exists():
            return False
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM project_config WHERE project_id = ?",
                    (project_id,),
                ).fetchone()
                return row["cnt"] > 0
        except (sqlite3.Error, BackendError):
            return False

    def read_config(self) -> ProjectConfig:
        self._ensure_init()
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM project_config LIMIT 1",
                ).fetchone()
        except sqlite3.Error as exc:
            raise BackendError(f"Failed to read config: {exc}", cause=exc) from exc
        if row is None:
            raise ProjectNotInitializedError(str(self._root))
        return ProjectConfig.model_validate(dict(row))

    def diff(self, project_id: str, from_version: int, to_version: int) -> HandoffDiff:
        self._ensure_init()
        try:
            with self._connect() as conn:
                from_row = conn.execute(
                    "SELECT * FROM handoffs WHERE project_id = ? AND version = ?",
                    (project_id, from_version),
                ).fetchone()
                to_row = conn.execute(
                    "SELECT * FROM handoffs WHERE project_id = ? AND version = ?",
                    (project_id, to_version),
                ).fetchone()
        except sqlite3.Error as exc:
            raise BackendError(f"Failed to compute diff: {exc}", cause=exc) from exc

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
        self._ensure_init()
        now = datetime.now(timezone.utc)
        try:
            with self._connect() as conn:
                # Clear expired locks
                conn.execute(
                    "DELETE FROM locks WHERE project_id = ? AND expires_at <= ?",
                    (project_id, now.isoformat()),
                )
                # Check existing lock
                row = conn.execute(
                    "SELECT * FROM locks WHERE project_id = ?",
                    (project_id,),
                ).fetchone()
                if row is not None:
                    if row["session_id"] != session_id:
                        return False
                # Acquire / re-acquire
                conn.execute(
                    """INSERT OR REPLACE INTO locks
                       (project_id, session_id, acquired_at, expires_at, agent)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        project_id,
                        session_id,
                        now.isoformat(),
                        (now + timedelta(seconds=ttl_seconds)).isoformat(),
                        agent,
                    ),
                )
        except sqlite3.Error as exc:
            raise BackendError(f"Failed to acquire lock: {exc}", cause=exc) from exc
        return True

    def release_lock(self, project_id: str, session_id: str) -> bool:
        self._ensure_init()
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT session_id FROM locks WHERE project_id = ?",
                    (project_id,),
                ).fetchone()
                if row is None or row["session_id"] != session_id:
                    return False
                conn.execute(
                    "DELETE FROM locks WHERE project_id = ? AND session_id = ?",
                    (project_id, session_id),
                )
        except sqlite3.Error as exc:
            raise BackendError(f"Failed to release lock: {exc}", cause=exc) from exc
        return True

    def is_locked(self, project_id: str) -> bool:
        self._ensure_init()
        now = datetime.now(timezone.utc)
        try:
            with self._connect() as conn:
                conn.execute(
                    "DELETE FROM locks WHERE project_id = ? AND expires_at <= ?",
                    (project_id, now.isoformat()),
                )
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM locks WHERE project_id = ?",
                    (project_id,),
                ).fetchone()
                return row["cnt"] > 0
        except (sqlite3.Error, BackendError):
            return False

    def lock_info(self, project_id: str) -> dict | None:
        self._ensure_init()
        now = datetime.now(timezone.utc)
        try:
            with self._connect() as conn:
                conn.execute(
                    "DELETE FROM locks WHERE project_id = ? AND expires_at <= ?",
                    (project_id, now.isoformat()),
                )
                row = conn.execute(
                    "SELECT * FROM locks WHERE project_id = ?",
                    (project_id,),
                ).fetchone()
                if row is None:
                    return None
                return {
                    "session_id": row["session_id"],
                    "agent": row["agent"],
                    "acquired_at": row["acquired_at"],
                    "expires_at": row["expires_at"],
                }
        except (sqlite3.Error, BackendError):
            return None


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
