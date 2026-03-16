"""Abstract backend interface for vaultit storage."""

from __future__ import annotations

from abc import ABC, abstractmethod

from vaultit.models import (
    Handoff,
    HandoffDiff,
    ProjectConfig,
    Session,
)


class VaultItBackend(ABC):
    """Abstract base for all vaultit storage backends."""

    @abstractmethod
    def init_project(self, config: ProjectConfig) -> None:
        """Create the storage structure for a new project."""

    @abstractmethod
    def write_handoff(self, handoff: Handoff) -> str:
        """Persist a handoff. Returns the handoff id."""

    @abstractmethod
    def read_handoff(self, session_id: str, version: int | None = None) -> Handoff:
        """Read a specific handoff by session id and optional version.

        If version is None, reads the latest version for that session.
        """

    @abstractmethod
    def read_latest_handoff(self, project_id: str) -> Handoff | None:
        """Read the most recent handoff across all sessions for a project.

        Returns None if no handoffs exist.
        """

    @abstractmethod
    def list_sessions(self, project_id: str) -> list[Session]:
        """List all sessions for a project, ordered by creation time."""

    @abstractmethod
    def write_session(self, session: Session) -> None:
        """Persist a session."""

    @abstractmethod
    def read_session(self, session_id: str) -> Session:
        """Read a session by id."""

    @abstractmethod
    def project_exists(self, project_id: str) -> bool:
        """Check whether a project has been initialized."""

    @abstractmethod
    def read_config(self) -> ProjectConfig:
        """Read the project configuration."""

    @abstractmethod
    def diff(self, project_id: str, from_version: int, to_version: int) -> HandoffDiff:
        """Compute the diff between two handoff versions."""

    # ── lock operations ──

    @abstractmethod
    def acquire_lock(
        self, project_id: str, session_id: str, agent: str, ttl_seconds: int,
    ) -> bool:
        """Try to acquire advisory lock. Returns True if acquired."""

    @abstractmethod
    def release_lock(self, project_id: str, session_id: str) -> bool:
        """Release lock. Returns True if released, False if not owner."""

    @abstractmethod
    def is_locked(self, project_id: str) -> bool:
        """Check if project has an active (unexpired) lock."""

    @abstractmethod
    def lock_info(self, project_id: str) -> dict | None:
        """Return lock details or None if unlocked."""
