"""Authentication module for vaultit — API key management and middleware."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from vaultit.exceptions import AuthenticationError, AuthorizationError
from vaultit.models import ApiKey

logger = logging.getLogger("vaultit.auth")

_KEY_PREFIX = "ck_"
_KEY_LENGTH = 32


def _hash_key(plaintext: str) -> str:
    """SHA-256 hash of a plaintext API key."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


class APIKeyManager:
    """Manage API keys with file-based or backend storage."""

    def __init__(self, store_path: Path | None = None) -> None:
        self._store_path = store_path or Path(".vaultit") / "api_keys.json"

    def _load_keys(self) -> list[dict]:
        if not self._store_path.exists():
            return []
        try:
            return json.loads(self._store_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save_keys(self, keys: list[dict]) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._store_path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(keys, indent=2, default=str), encoding="utf-8")
            os.replace(str(tmp), str(self._store_path))
        except OSError:
            tmp.unlink(missing_ok=True)
            raise

    def generate_key(
        self,
        name: str,
        user_id: str,
        org_id: str = "",
        scopes: list[str] | None = None,
        expires_in_days: int | None = None,
    ) -> tuple[str, ApiKey]:
        """Generate a new API key. Returns (plaintext_key, ApiKey model).

        The plaintext key is shown once. Only the SHA-256 hash is stored.
        """
        plaintext = f"{_KEY_PREFIX}{secrets.token_urlsafe(_KEY_LENGTH)}"
        key_hash = _hash_key(plaintext)
        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        api_key = ApiKey(
            key_hash=key_hash,
            name=name,
            user_id=user_id,
            org_id=org_id,
            scopes=scopes or ["read", "write"],
            expires_at=expires_at,
        )

        keys = self._load_keys()
        keys.append(api_key.model_dump(mode="json"))
        self._save_keys(keys)

        logger.info("Generated API key '%s' for user %s", name, user_id)
        return plaintext, api_key

    def verify_key(self, plaintext_key: str, required_scope: str = "read") -> ApiKey | None:
        """Verify key exists, not revoked, not expired, has required scope.

        Returns ApiKey if valid, None if invalid.
        Updates last_used_at on success.
        """
        key_hash = _hash_key(plaintext_key)
        keys = self._load_keys()

        for i, kd in enumerate(keys):
            if kd.get("key_hash") != key_hash:
                continue

            api_key = ApiKey.model_validate(kd)

            if api_key.revoked:
                return None

            if api_key.expires_at is not None:
                now = datetime.now(timezone.utc)
                expires = api_key.expires_at
                if not expires.tzinfo:
                    from datetime import timezone as tz
                    expires = expires.replace(tzinfo=tz.utc)
                if now > expires:
                    return None

            if required_scope not in api_key.scopes:
                return None

            # Update last_used_at
            keys[i]["last_used_at"] = datetime.now(timezone.utc).isoformat()
            self._save_keys(keys)

            return api_key

        return None

    def revoke_key(self, key_id: str) -> bool:
        """Mark key as revoked. Returns True if found and revoked."""
        keys = self._load_keys()
        for i, kd in enumerate(keys):
            if kd.get("id") == key_id:
                keys[i]["revoked"] = True
                self._save_keys(keys)
                logger.info("Revoked API key %s", key_id)
                return True
        return False

    def list_keys(self, user_id: str | None = None) -> list[ApiKey]:
        """List all non-revoked keys, optionally filtered by user_id."""
        keys = self._load_keys()
        result = []
        for kd in keys:
            api_key = ApiKey.model_validate(kd)
            if api_key.revoked:
                continue
            if user_id is not None and api_key.user_id != user_id:
                continue
            result.append(api_key)
        return result


class AuthMiddleware:
    """FastAPI middleware for API key authentication.

    Reads ``X-API-Key`` header.  Injects authenticated ``ApiKey`` into
    ``request.state.api_key``.

    - 401 if missing or invalid key
    - 403 if valid key lacks required scope
    - Configurable via ``auth_required`` (default True, set False for local dev)
    """

    # Paths that never require auth
    _PUBLIC_PATHS = {"/docs", "/redoc", "/openapi.json"}

    def __init__(self, app: Any, auth_required: bool = True, key_manager: APIKeyManager | None = None) -> None:
        self.app = app
        self.auth_required = auth_required
        self.key_manager = key_manager or APIKeyManager()

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http" or not self.auth_required:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Allow public paths
        if path in self._PUBLIC_PATHS:
            await self.app(scope, receive, send)
            return

        # Extract API key from headers
        headers = dict(scope.get("headers", []))
        api_key_header = headers.get(b"x-api-key", b"").decode("utf-8", errors="ignore")

        if not api_key_header:
            await self._send_error(send, 401, "Missing X-API-Key header")
            return

        # Determine required scope from method
        method = scope.get("method", "GET")
        required_scope = "read" if method == "GET" else "write"

        # Auth endpoints require admin scope
        if path.startswith("/auth/"):
            required_scope = "admin"

        api_key = self.key_manager.verify_key(api_key_header, required_scope="read")
        if api_key is None:
            await self._send_error(send, 401, "Invalid or expired API key")
            return

        # Check scope
        if required_scope not in api_key.scopes:
            await self._send_error(send, 403, f"Insufficient scope: requires '{required_scope}'")
            return

        # Inject into ASGI scope for downstream access
        scope.setdefault("state", {})
        scope["state"]["api_key"] = api_key

        await self.app(scope, receive, send)

    async def _send_error(self, send: Any, status: int, detail: str) -> None:
        import json as _json
        body = _json.dumps({"detail": detail}).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(body)).encode()],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
