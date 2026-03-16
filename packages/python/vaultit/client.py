"""Primary SDK entry point for vaultit."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from vaultit.backends.base import VaultItBackend
from vaultit.backends.file import FileBackend
from vaultit.backends.lock import LockManager
from vaultit.backends.sqlite import SQLiteBackend
from vaultit.exceptions import (
    BackendError,
    VaultItError,
    HandoffNotFoundError,
    ProjectNotInitializedError,
)
from vaultit.models import (
    AgentType,
    Decision,
    Handoff,
    HandoffDiff,
    ProjectConfig,
    Session,
    Task,
    TaskStatus,
)
from vaultit.renderer import render_bootstrap

logger = logging.getLogger("vaultit.client")


def _detect_backend(project_dir: Path) -> VaultItBackend:
    """Auto-detect backend from config.json, falling back to FileBackend."""
    config_path = project_dir / ".vaultit" / "config.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            backend_type = data.get("backend", "file")
            if backend_type == "sqlite":
                return SQLiteBackend(project_dir)
            if backend_type == "postgres":
                from vaultit.backends.postgres import PostgresBackend
                return PostgresBackend()
        except (json.JSONDecodeError, OSError):
            pass
    return FileBackend(project_dir)


def _make_backend(backend_type: str, project_dir: Path) -> VaultItBackend:
    """Create a backend by type name."""
    if backend_type == "sqlite":
        return SQLiteBackend(project_dir)
    if backend_type == "postgres":
        from vaultit.backends.postgres import PostgresBackend
        return PostgresBackend()
    return FileBackend(project_dir)


class VaultItClient:
    """High-level client for vaultit operations.

    All business logic lives here. The CLI is a thin wrapper.
    """

    def __init__(
        self,
        project_dir: Path | None = None,
        backend: VaultItBackend | None = None,
    ) -> None:
        self._project_dir = Path(project_dir) if project_dir else Path(".")
        if backend is not None:
            self._backend = backend
        else:
            self._backend = _detect_backend(self._project_dir)
        self._lock_manager = LockManager(self._backend)

    @property
    def backend(self) -> VaultItBackend:
        return self._backend

    # ── init ──

    def init(
        self,
        name: str,
        coordination: str = "sequential",
        backend_type: str = "file",
    ) -> ProjectConfig:
        """Initialize a new vaultit project."""
        project_id = _slugify(name)
        config = ProjectConfig(
            project_id=project_id,
            name=name,
            coordination=coordination,
            backend=backend_type,
        )
        self._backend = _make_backend(backend_type, self._project_dir)
        self._lock_manager = LockManager(self._backend)
        self._backend.init_project(config)
        logger.info("Initialized project '%s' with %s backend", project_id, backend_type)
        return config

    # ── sync ──

    def sync(
        self,
        tasks: list[dict] | None = None,
        decisions: list[dict] | None = None,
        open_questions: list[str] | None = None,
        next_steps: list[str] | None = None,
        notes: str = "",
        agent: str = "custom",
        agent_version: str = "",
    ) -> Handoff:
        """Create or continue a session and write a versioned handoff."""
        config = self._backend.read_config()
        agent_enum = AgentType(agent)

        # Resolve session: use the latest open session or create a new one
        sessions = self._backend.list_sessions(config.project_id)
        open_sessions = [s for s in sessions if s.closed_at is None]

        if open_sessions:
            session = open_sessions[-1]
        else:
            session = Session(
                project_id=config.project_id,
                agent=agent_enum,
            )
            self._backend.write_session(session)

        # Coordination enforcement
        if config.coordination == "sequential":
            acquired = self._lock_manager.acquire(
                config.project_id, session.id, agent,
            )
            if not acquired:
                lock = self._lock_manager.lock_info(config.project_id)
                holder = lock["session_id"][:8] if lock else "unknown"
                raise VaultItError(
                    f"Cannot sync: project is locked by session {holder}... "
                    "Wait for the lock to expire or use coordination='lock' for advisory mode."
                )
        elif config.coordination in ("lock", "merge"):
            if self._lock_manager.is_locked(config.project_id):
                lock = self._lock_manager.lock_info(config.project_id)
                holder = lock["session_id"][:8] if lock else "unknown"
                logger.warning(
                    "Advisory: project is locked by session %s...", holder,
                )
            self._lock_manager.acquire(
                config.project_id, session.id, agent,
            )

        # Determine version
        try:
            latest = self._backend.read_handoff(session.id)
            version = latest.version + 1
        except Exception:
            version = 1

        # Build typed lists
        task_list = [Task.model_validate(t) for t in (tasks or [])]
        dec_list = [Decision.model_validate(d) for d in (decisions or [])]

        handoff = Handoff(
            session_id=session.id,
            project_id=config.project_id,
            version=version,
            agent=agent_enum,
            agent_version=agent_version,
            tasks=task_list,
            decisions=dec_list,
            open_questions=open_questions or [],
            next_steps=next_steps or [],
            raw_notes=notes,
        )

        self._backend.write_handoff(handoff)

        if config.coordination == "sequential":
            self._lock_manager.release(config.project_id, session.id)

        logger.info(
            "Synced handoff v%d for session %s",
            version,
            session.id,
        )
        return handoff

    # ── bootstrap ──

    def bootstrap(self) -> str:
        """Generate a bootstrap briefing from the latest handoff."""
        config = self._backend.read_config()
        handoff = self._backend.read_latest_handoff(config.project_id)
        if handoff is None:
            return (
                f"Project '{config.name}' is initialized but has no handoffs yet.\n"
                "Run 'vaultit sync' to create the first handoff."
            )
        return render_bootstrap(handoff, config)

    # ── status ──

    def status(self) -> dict:
        """Return a summary of the current project state."""
        config = self._backend.read_config()
        sessions = self._backend.list_sessions(config.project_id)
        handoff = self._backend.read_latest_handoff(config.project_id)

        task_counts: dict[str, int] = {}
        latest_summary = "No handoffs yet"
        if handoff is not None:
            for st in TaskStatus:
                count = sum(1 for t in handoff.tasks if t.status == st)
                if count:
                    task_counts[st.value] = count
            latest_summary = (
                f"v{handoff.version} by {handoff.agent.value} "
                f"at {handoff.updated_at.isoformat()}"
            )

        return {
            "project_id": config.project_id,
            "name": config.name,
            "coordination": config.coordination,
            "backend": config.backend,
            "session_count": len(sessions),
            "latest_handoff": latest_summary,
            "task_counts": task_counts,
        }

    # ── diff ──

    def diff(self, from_version: int, to_version: int) -> HandoffDiff:
        """Compute the diff between two handoff versions."""
        config = self._backend.read_config()
        return self._backend.diff(config.project_id, from_version, to_version)

    # ── doctor ──

    def doctor(self) -> dict:
        """Run health checks and return results."""
        checks: list[dict] = []

        ck_dir = self._project_dir / ".vaultit"
        if ck_dir.is_dir():
            checks.append({"name": ".vaultit directory", "status": "ok", "message": "Found"})
        else:
            checks.append({
                "name": ".vaultit directory",
                "status": "fail",
                "message": "Not found. Run 'vaultit init'.",
            })
            return {"healthy": False, "checks": checks}

        try:
            config = self._backend.read_config()
            checks.append({
                "name": "config.json",
                "status": "ok",
                "message": f"Project '{config.name}' ({config.project_id})",
            })
        except Exception as exc:
            checks.append({
                "name": "config.json",
                "status": "fail",
                "message": str(exc),
            })
            return {"healthy": False, "checks": checks}

        backend_name = config.backend
        if backend_name == "sqlite":
            db_path = ck_dir / "vaultit.db"
            if db_path.exists():
                size_kb = db_path.stat().st_size / 1024
                checks.append({
                    "name": "backend",
                    "status": "ok",
                    "message": f"sqlite ({size_kb:.1f} KB)",
                })
            else:
                checks.append({
                    "name": "backend",
                    "status": "fail",
                    "message": "sqlite configured but vaultit.db not found",
                })
        else:
            sessions_dir = ck_dir / "sessions"
            if sessions_dir.is_dir():
                session_count = len(list(sessions_dir.glob("*.json")))
                checks.append({
                    "name": "backend",
                    "status": "ok",
                    "message": f"file ({session_count} session file(s))",
                })
            else:
                checks.append({
                    "name": "backend",
                    "status": "warn",
                    "message": "file (sessions dir missing -- will be created on first sync)",
                })

        try:
            handoff = self._backend.read_latest_handoff(config.project_id)
            if handoff is not None:
                checks.append({
                    "name": "latest handoff",
                    "status": "ok",
                    "message": f"v{handoff.version} ({handoff.session_id[:8]}...)",
                })
            else:
                checks.append({
                    "name": "latest handoff",
                    "status": "info",
                    "message": "No handoffs yet",
                })
        except Exception as exc:
            checks.append({
                "name": "latest handoff",
                "status": "fail",
                "message": str(exc),
            })

        try:
            lock = self._backend.lock_info(config.project_id)
            if lock is not None:
                checks.append({
                    "name": "lock",
                    "status": "info",
                    "message": f"Locked by {lock['agent']} (session {lock['session_id'][:8]}...)",
                })
            else:
                checks.append({
                    "name": "lock",
                    "status": "ok",
                    "message": "Unlocked",
                })
        except Exception:
            checks.append({
                "name": "lock",
                "status": "ok",
                "message": "Unlocked",
            })

        healthy = all(c["status"] != "fail" for c in checks)
        return {"healthy": healthy, "checks": checks}

    # ── switch_backend ──

    def switch_backend(self, target: str) -> dict:
        """Migrate all data from current backend to target backend."""
        config = self._backend.read_config()

        if config.backend == target:
            raise VaultItError(
                f"Already using '{target}' backend. Nothing to migrate."
            )

        target_backend = _make_backend(target, self._project_dir)

        target_config = ProjectConfig(
            project_id=config.project_id,
            name=config.name,
            created_at=config.created_at,
            backend=target,
            coordination=config.coordination,
            schema_version=config.schema_version,
        )
        target_backend.init_project(target_config)

        sessions = self._backend.list_sessions(config.project_id)
        for session in sessions:
            target_backend.write_session(session)

        handoff_count = 0
        for session in sessions:
            version = 1
            while True:
                try:
                    handoff = self._backend.read_handoff(session.id, version=version)
                    target_backend.write_handoff(handoff)
                    handoff_count += 1
                    version += 1
                except Exception:
                    break

        import os
        config_path = self._project_dir / ".vaultit" / "config.json"
        tmp = config_path.with_suffix(".tmp")
        try:
            tmp.write_text(target_config.model_dump_json(indent=2), encoding="utf-8")
            os.replace(str(tmp), str(config_path))
        except OSError:
            tmp.unlink(missing_ok=True)
            raise VaultItError("Migration completed but failed to update config.json")

        self._backend = target_backend
        self._lock_manager = LockManager(self._backend)

        return {
            "from": config.backend,
            "to": target,
            "sessions": len(sessions),
            "handoffs": handoff_count,
        }

    # ── session management ──

    def open_session(self, agent: str = "custom", agent_version: str = "") -> Session:
        """Explicitly open a new session."""
        config = self._backend.read_config()
        session = Session(
            project_id=config.project_id,
            agent=AgentType(agent),
        )
        self._backend.write_session(session)
        logger.info("Opened session %s", session.id)
        return session

    def close_session(self, session_id: str | None = None) -> Session:
        """Close current or specified session. Sets closed_at timestamp."""
        config = self._backend.read_config()
        if session_id is None:
            sessions = self._backend.list_sessions(config.project_id)
            open_sessions = [s for s in sessions if s.closed_at is None]
            if not open_sessions:
                raise VaultItError("No open sessions to close.")
            session = open_sessions[-1]
        else:
            session = self._backend.read_session(session_id)

        closed = Session(
            id=session.id,
            project_id=session.project_id,
            created_at=session.created_at,
            closed_at=datetime.now(timezone.utc),
            agent=session.agent,
            user_id=session.user_id,
        )
        self._backend.write_session(closed)
        logger.info("Closed session %s", closed.id)
        return closed

    def get_session(self, session_id: str) -> Session:
        """Return Session by ID."""
        return self._backend.read_session(session_id)

    def list_sessions(self) -> list[Session]:
        """Return all sessions for project, newest first."""
        config = self._backend.read_config()
        sessions = self._backend.list_sessions(config.project_id)
        return list(reversed(sessions))

    # ── handoff access ──

    def get_handoff(self, session_id: str, version: int) -> Handoff:
        """Return specific handoff version."""
        return self._backend.read_handoff(session_id, version=version)

    def list_handoffs(self, session_id: str) -> list[Handoff]:
        """Return all handoff versions for session, newest first."""
        result: list[Handoff] = []
        version = 1
        while True:
            try:
                h = self._backend.read_handoff(session_id, version=version)
                result.append(h)
                version += 1
            except Exception:
                break
        return list(reversed(result))

    # ── task management ──

    def _get_latest_handoff_or_raise(self) -> Handoff:
        config = self._backend.read_config()
        handoff = self._backend.read_latest_handoff(config.project_id)
        if handoff is None:
            raise HandoffNotFoundError("none", None)
        return handoff

    def _write_new_version(self, base: Handoff, **overrides) -> Handoff:
        """Create a new handoff version based on an existing one."""
        data = base.model_dump(mode="json")
        data.pop("id", None)
        data["version"] = base.version + 1
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        data.update(overrides)
        new_handoff = Handoff.model_validate(data)
        self._backend.write_handoff(new_handoff)
        return new_handoff

    def add_task(
        self,
        task_id: str,
        title: str,
        status: str = "pending",
        owner: str = "human",
        depends_on: list[str] | None = None,
        notes: str = "",
    ) -> Handoff:
        """Add or update a task in the latest handoff. Creates new version."""
        latest = self._get_latest_handoff_or_raise()
        task = Task(
            id=task_id,
            title=title,
            status=TaskStatus(status),
            owner=owner,
            depends_on=depends_on or [],
            notes=notes,
        )
        tasks = [t for t in latest.tasks if t.id != task_id]
        tasks.append(task)
        return self._write_new_version(
            latest, tasks=[t.model_dump(mode="json") for t in tasks],
        )

    def update_task_status(self, task_id: str, status: str) -> Handoff:
        """Update status of existing task. Creates new handoff version."""
        latest = self._get_latest_handoff_or_raise()
        found = False
        tasks = []
        for t in latest.tasks:
            if t.id == task_id:
                found = True
                updated = t.model_copy(update={"status": TaskStatus(status)})
                tasks.append(updated)
            else:
                tasks.append(t)
        if not found:
            raise ValueError(f"Task '{task_id}' not found in latest handoff.")
        return self._write_new_version(
            latest, tasks=[t.model_dump(mode="json") for t in tasks],
        )

    # ── decision management ──

    def add_decision(
        self,
        decision_id: str,
        summary: str,
        rationale: str = "",
        made_by: str = "human",
        supersedes: str | None = None,
    ) -> Handoff:
        """Add a decision to latest handoff. Creates new version."""
        latest = self._get_latest_handoff_or_raise()
        decision = Decision(
            id=decision_id,
            summary=summary,
            rationale=rationale,
            made_by=made_by,
            supersedes=supersedes,
        )
        decisions = list(latest.decisions) + [decision]
        return self._write_new_version(
            latest, decisions=[d.model_dump(mode="json") for d in decisions],
        )

    # ── export ──

    def export_briefing(self, output_path: Path | None = None) -> str:
        """Render bootstrap briefing. Optionally write to file."""
        briefing = self.bootstrap()
        if output_path is not None:
            output_path.write_text(briefing, encoding="utf-8")
            logger.info("Exported briefing to %s", output_path)
        return briefing


def _slugify(name: str) -> str:
    """Convert a project name to a slug-safe identifier."""
    return (
        name.lower()
        .replace(" ", "-")
        .replace("_", "-")
    )
