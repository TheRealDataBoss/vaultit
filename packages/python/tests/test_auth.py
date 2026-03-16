"""Tests for API key authentication module."""

from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from vaultit.auth import APIKeyManager, _hash_key
from vaultit.models import ApiKey


@pytest.fixture
def mgr(tmp_path: Path) -> APIKeyManager:
    return APIKeyManager(store_path=tmp_path / "api_keys.json")


class TestAPIKeyManager:
    def test_generate_key_format(self, mgr: APIKeyManager):
        plaintext, api_key = mgr.generate_key(name="test", user_id="u1")
        assert plaintext.startswith("ck_")
        assert len(plaintext) > 35  # ck_ + 32+ urlsafe chars

    def test_generate_key_hash_not_plaintext(self, mgr: APIKeyManager):
        plaintext, api_key = mgr.generate_key(name="test", user_id="u1")
        assert api_key.key_hash != plaintext
        assert api_key.key_hash == _hash_key(plaintext)

    def test_verify_valid_key(self, mgr: APIKeyManager):
        plaintext, _ = mgr.generate_key(name="test", user_id="u1")
        result = mgr.verify_key(plaintext, required_scope="read")
        assert result is not None
        assert result.name == "test"

    def test_verify_revoked_key_returns_none(self, mgr: APIKeyManager):
        plaintext, api_key = mgr.generate_key(name="test", user_id="u1")
        mgr.revoke_key(api_key.id)
        result = mgr.verify_key(plaintext)
        assert result is None

    def test_verify_expired_key_returns_none(self, mgr: APIKeyManager):
        plaintext, api_key = mgr.generate_key(
            name="test", user_id="u1", expires_in_days=0,
        )
        # Key with 0 days expiry should be expired immediately (or very soon)
        # Force expiry by manipulating stored data
        import json
        keys = json.loads(mgr._store_path.read_text(encoding="utf-8"))
        keys[0]["expires_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        mgr._store_path.write_text(json.dumps(keys, default=str), encoding="utf-8")
        result = mgr.verify_key(plaintext)
        assert result is None

    def test_verify_wrong_scope_returns_none(self, mgr: APIKeyManager):
        plaintext, _ = mgr.generate_key(
            name="readonly", user_id="u1", scopes=["read"],
        )
        result = mgr.verify_key(plaintext, required_scope="admin")
        assert result is None

    def test_verify_nonexistent_key_returns_none(self, mgr: APIKeyManager):
        result = mgr.verify_key("ck_doesnotexist123456789012345678901234")
        assert result is None

    def test_revoke_key(self, mgr: APIKeyManager):
        _, api_key = mgr.generate_key(name="test", user_id="u1")
        assert mgr.revoke_key(api_key.id) is True

    def test_revoke_nonexistent_key(self, mgr: APIKeyManager):
        assert mgr.revoke_key("nonexistent") is False

    def test_list_keys_excludes_revoked(self, mgr: APIKeyManager):
        _, k1 = mgr.generate_key(name="keep", user_id="u1")
        _, k2 = mgr.generate_key(name="revoke-me", user_id="u1")
        mgr.revoke_key(k2.id)
        keys = mgr.list_keys()
        assert len(keys) == 1
        assert keys[0].name == "keep"

    def test_list_keys_by_user(self, mgr: APIKeyManager):
        mgr.generate_key(name="user1-key", user_id="u1")
        mgr.generate_key(name="user2-key", user_id="u2")
        keys = mgr.list_keys(user_id="u1")
        assert len(keys) == 1
        assert keys[0].name == "user1-key"

    def test_generate_key_with_custom_scopes(self, mgr: APIKeyManager):
        _, api_key = mgr.generate_key(
            name="admin", user_id="u1",
            scopes=["read", "write", "admin"],
        )
        assert "admin" in api_key.scopes

    def test_generate_key_with_org(self, mgr: APIKeyManager):
        _, api_key = mgr.generate_key(
            name="org-key", user_id="u1", org_id="org-123",
        )
        assert api_key.org_id == "org-123"

    def test_verify_updates_last_used(self, mgr: APIKeyManager):
        plaintext, api_key = mgr.generate_key(name="test", user_id="u1")
        assert api_key.last_used_at is None
        result = mgr.verify_key(plaintext)
        assert result is not None
        # Re-read from storage
        keys = mgr.list_keys()
        assert keys[0].last_used_at is not None

    def test_multiple_keys_independent(self, mgr: APIKeyManager):
        p1, k1 = mgr.generate_key(name="key1", user_id="u1")
        p2, k2 = mgr.generate_key(name="key2", user_id="u1")
        assert mgr.verify_key(p1) is not None
        assert mgr.verify_key(p2) is not None
        mgr.revoke_key(k1.id)
        assert mgr.verify_key(p1) is None
        assert mgr.verify_key(p2) is not None
