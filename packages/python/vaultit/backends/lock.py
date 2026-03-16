"""Advisory lock manager for vaultit."""

from __future__ import annotations

from vaultit.backends.base import VaultItBackend

_DEFAULT_TTL = 3600  # 1 hour


class LockManager:
    """High-level advisory lock manager that delegates to a backend.

    Wraps the backend's lock primitives with a configurable TTL.
    """

    def __init__(
        self,
        backend: VaultItBackend,
        ttl_seconds: int = _DEFAULT_TTL,
    ) -> None:
        self._backend = backend
        self._ttl = ttl_seconds

    def acquire(
        self, project_id: str, session_id: str, agent: str = "custom",
    ) -> bool:
        """Try to acquire lock. Returns True if acquired or re-acquired by same session."""
        return self._backend.acquire_lock(
            project_id, session_id, agent, self._ttl,
        )

    def release(self, project_id: str, session_id: str) -> bool:
        """Release lock. Returns True if released, False if not owner."""
        return self._backend.release_lock(project_id, session_id)

    def is_locked(self, project_id: str) -> bool:
        """Returns True if project has an active unexpired lock."""
        return self._backend.is_locked(project_id)

    def lock_info(self, project_id: str) -> dict | None:
        """Returns lock details or None if not locked."""
        return self._backend.lock_info(project_id)
