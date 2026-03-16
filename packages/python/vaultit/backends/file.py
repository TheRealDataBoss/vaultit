"""Filesystem-based backend for vaultit."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

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
    Task,
    Decision,
)
from vaultit.backends.base import VaultItBackend

logger = logging.getLogger("vaultit.backends.file")

_CK_DIR = ".vaultit"


class FileBackend(VaultItBackend):
    """Stores vaultit data as JSON files on the local filesystem.

    Layout::

        <root>/.vaultit/
            config.json
            sessions/
                {session_id}.json
            handoffs/
                {session_id}/
                    v{version}.json
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._ck = root / _CK_DIR

    @property
    def root(self) -> Path:
        return self._root

    # ── helpers ──

    def _ensure_init(self) -> None:
        if not self._ck.is_dir():
            raise ProjectNotInitializedError(str(self._root))

    def _atomic_write(self, path: Path, data: str) -> None:
        """Write data atomically: write to tmp, then os.replace."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(data, encoding="utf-8")
            os.replace(str(tmp), str(path))
        except OSError as exc:
            # Clean up tmp on failure
            tmp.unlink(missing_ok=True)
            raise BackendError(f"Failed to write {path}", cause=exc) from exc

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise BackendError(f"File not found: {path}", cause=exc) from exc
        except json.JSONDecodeError as exc:
            raise BackendError(f"Corrupt JSON: {path}", cause=exc) from exc

    # ── interface ──

    def init_project(self, config: ProjectConfig) -> None:
        self._ck.mkdir(parents=True, exist_ok=True)
        (self._ck / "sessions").mkdir(exist_ok=True)
        (self._ck / "handoffs").mkdir(exist_ok=True)
        self._atomic_write(
            self._ck / "config.json",
            config.model_dump_json(indent=2),
        )
        logger.info("Initialized project '%s' at %s", config.project_id, self._ck)

    def write_handoff(self, handoff: Handoff) -> str:
        self._ensure_init()
        session_dir = self._ck / "handoffs" / handoff.session_id
        path = session_dir / f"v{handoff.version}.json"
        self._atomic_write(path, handoff.model_dump_json(indent=2))
        logger.debug("Wrote handoff %s v%d", handoff.session_id, handoff.version)
        return handoff.id

    def read_handoff(self, session_id: str, version: int | None = None) -> Handoff:
        self._ensure_init()
        session_dir = self._ck / "handoffs" / session_id
        if not session_dir.is_dir():
            raise HandoffNotFoundError(session_id)

        if version is not None:
            path = session_dir / f"v{version}.json"
            if not path.exists():
                raise HandoffNotFoundError(session_id, version)
            return Handoff.model_validate(self._read_json(path))

        # Find latest version
        versions = self._list_versions(session_dir)
        if not versions:
            raise HandoffNotFoundError(session_id)
        path = session_dir / f"v{versions[-1]}.json"
        return Handoff.model_validate(self._read_json(path))

    def _list_versions(self, session_dir: Path) -> list[int]:
        """Return sorted list of version numbers in a session handoff dir."""
        versions: list[int] = []
        for f in session_dir.iterdir():
            if f.suffix == ".json" and f.stem.startswith("v"):
                try:
                    versions.append(int(f.stem[1:]))
                except ValueError:
                    continue
        versions.sort()
        return versions

    def read_latest_handoff(self, project_id: str) -> Handoff | None:
        self._ensure_init()
        handoffs_dir = self._ck / "handoffs"
        if not handoffs_dir.is_dir():
            return None

        latest: Handoff | None = None
        for session_dir in handoffs_dir.iterdir():
            if not session_dir.is_dir():
                continue
            versions = self._list_versions(session_dir)
            if not versions:
                continue
            path = session_dir / f"v{versions[-1]}.json"
            try:
                handoff = Handoff.model_validate(self._read_json(path))
            except BackendError:
                continue
            if handoff.project_id != project_id:
                continue
            if latest is None or handoff.updated_at > latest.updated_at:
                latest = handoff
        return latest

    def list_sessions(self, project_id: str) -> list[Session]:
        self._ensure_init()
        sessions_dir = self._ck / "sessions"
        result: list[Session] = []
        for f in sessions_dir.iterdir():
            if f.suffix != ".json":
                continue
            try:
                session = Session.model_validate(self._read_json(f))
            except (BackendError, Exception):
                continue
            if session.project_id == project_id:
                result.append(session)
        result.sort(key=lambda s: s.created_at)
        return result

    def write_session(self, session: Session) -> None:
        self._ensure_init()
        path = self._ck / "sessions" / f"{session.id}.json"
        self._atomic_write(path, session.model_dump_json(indent=2))
        logger.debug("Wrote session %s", session.id)

    def read_session(self, session_id: str) -> Session:
        self._ensure_init()
        path = self._ck / "sessions" / f"{session_id}.json"
        if not path.exists():
            raise SessionNotFoundError(session_id)
        return Session.model_validate(self._read_json(path))

    def project_exists(self, project_id: str) -> bool:
        config_path = self._ck / "config.json"
        if not config_path.exists():
            return False
        try:
            config = ProjectConfig.model_validate(self._read_json(config_path))
            return config.project_id == project_id
        except Exception:
            return False

    def read_config(self) -> ProjectConfig:
        self._ensure_init()
        path = self._ck / "config.json"
        if not path.exists():
            raise ProjectNotInitializedError(str(self._root))
        return ProjectConfig.model_validate(self._read_json(path))

    def diff(self, project_id: str, from_version: int, to_version: int) -> HandoffDiff:
        self._ensure_init()

        # Find the session that has these versions
        handoffs_dir = self._ck / "handoffs"
        from_handoff: Handoff | None = None
        to_handoff: Handoff | None = None

        for session_dir in handoffs_dir.iterdir():
            if not session_dir.is_dir():
                continue
            from_path = session_dir / f"v{from_version}.json"
            to_path = session_dir / f"v{to_version}.json"
            if from_path.exists() and from_handoff is None:
                h = Handoff.model_validate(self._read_json(from_path))
                if h.project_id == project_id:
                    from_handoff = h
            if to_path.exists() and to_handoff is None:
                h = Handoff.model_validate(self._read_json(to_path))
                if h.project_id == project_id:
                    to_handoff = h

        if from_handoff is None:
            raise HandoffNotFoundError("unknown", from_version)
        if to_handoff is None:
            raise HandoffNotFoundError("unknown", to_version)

        return _compute_diff(from_handoff, to_handoff)

    # ── lock operations ──

    def _lock_path(self) -> Path:
        return self._ck / "lock.json"

    def acquire_lock(
        self, project_id: str, session_id: str, agent: str, ttl_seconds: int,
    ) -> bool:
        self._ensure_init()
        lock_path = self._lock_path()
        now = datetime.now(timezone.utc)

        # Check existing lock
        if lock_path.exists():
            try:
                data = self._read_json(lock_path)
                expires = datetime.fromisoformat(data["expires_at"])
                if expires > now and data.get("session_id") != session_id:
                    return False
                # Expired or same session — overwrite
            except (BackendError, KeyError, ValueError):
                pass  # Corrupt lock file — overwrite

        lock_data = {
            "project_id": project_id,
            "session_id": session_id,
            "acquired_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
            "agent": agent,
        }
        self._atomic_write(lock_path, json.dumps(lock_data, indent=2))
        return True

    def release_lock(self, project_id: str, session_id: str) -> bool:
        self._ensure_init()
        lock_path = self._lock_path()
        if not lock_path.exists():
            return False
        try:
            data = self._read_json(lock_path)
            if data.get("session_id") != session_id:
                return False
            lock_path.unlink()
            return True
        except BackendError:
            return False

    def is_locked(self, project_id: str) -> bool:
        self._ensure_init()
        lock_path = self._lock_path()
        if not lock_path.exists():
            return False
        try:
            data = self._read_json(lock_path)
            expires = datetime.fromisoformat(data["expires_at"])
            if expires <= datetime.now(timezone.utc):
                lock_path.unlink(missing_ok=True)
                return False
            return True
        except (BackendError, KeyError, ValueError):
            return False

    def lock_info(self, project_id: str) -> dict | None:
        self._ensure_init()
        lock_path = self._lock_path()
        if not lock_path.exists():
            return None
        try:
            data = self._read_json(lock_path)
            expires = datetime.fromisoformat(data["expires_at"])
            if expires <= datetime.now(timezone.utc):
                lock_path.unlink(missing_ok=True)
                return None
            return {
                "session_id": data["session_id"],
                "agent": data["agent"],
                "acquired_at": data["acquired_at"],
                "expires_at": data["expires_at"],
            }
        except (BackendError, KeyError, ValueError):
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
