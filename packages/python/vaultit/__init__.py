"""vaultit — Zero model drift between AI agents."""

from vaultit.client import VaultItClient
from vaultit.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BackendError,
    VaultItError,
    HandoffNotFoundError,
    ProjectNotInitializedError,
    RateLimitError,
    SchemaVersionError,
    SessionNotFoundError,
)
from vaultit.models import (
    AgentType,
    ApiKey,
    AuditEvent,
    Decision,
    Handoff,
    HandoffDiff,
    Organization,
    ProjectConfig,
    Session,
    Task,
    TaskStatus,
    User,
)

__version__ = "0.6.0"

__all__ = [
    # Client
    "VaultItClient",
    # Models
    "AgentType",
    "ApiKey",
    "AuditEvent",
    "Decision",
    "Handoff",
    "HandoffDiff",
    "Organization",
    "ProjectConfig",
    "Session",
    "Task",
    "TaskStatus",
    "User",
    # Exceptions
    "AuthenticationError",
    "AuthorizationError",
    "BackendError",
    "VaultItError",
    "HandoffNotFoundError",
    "ProjectNotInitializedError",
    "RateLimitError",
    "SchemaVersionError",
    "SessionNotFoundError",
]
