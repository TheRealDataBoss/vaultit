"""Tests for REST API auth middleware and auth endpoints."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from vaultit.auth import APIKeyManager, AuthMiddleware
from vaultit.server import app as main_app


@pytest.fixture
def key_mgr(tmp_path: Path) -> APIKeyManager:
    return APIKeyManager(store_path=tmp_path / "api_keys.json")


# ── AuthMiddleware tests with a standalone app ──


def _make_authed_app(key_mgr: APIKeyManager) -> FastAPI:
    """Create a minimal FastAPI app with AuthMiddleware enabled."""
    test_app = FastAPI()

    @test_app.get("/protected")
    def protected(request: Request):
        return {"status": "ok"}

    @test_app.post("/mutate")
    def mutate(request: Request):
        return {"status": "mutated"}

    @test_app.post("/auth/admin-action")
    def admin_action(request: Request):
        return {"status": "admin"}

    test_app.add_middleware(AuthMiddleware, auth_required=True, key_manager=key_mgr)
    return test_app


class TestAuthMiddleware:
    def test_missing_key_returns_401(self, key_mgr: APIKeyManager):
        client = TestClient(_make_authed_app(key_mgr))
        resp = client.get("/protected")
        assert resp.status_code == 401
        assert "Missing" in resp.json()["detail"]

    def test_invalid_key_returns_401(self, key_mgr: APIKeyManager):
        client = TestClient(_make_authed_app(key_mgr))
        resp = client.get("/protected", headers={"X-API-Key": "ck_boguskey12345678901234567890"})
        assert resp.status_code == 401
        assert "Invalid" in resp.json()["detail"]

    def test_valid_key_passes(self, key_mgr: APIKeyManager):
        plaintext, _ = key_mgr.generate_key(name="test", user_id="u1")
        client = TestClient(_make_authed_app(key_mgr))
        resp = client.get("/protected", headers={"X-API-Key": plaintext})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_write_scope_required_for_post(self, key_mgr: APIKeyManager):
        plaintext, _ = key_mgr.generate_key(
            name="readonly", user_id="u1", scopes=["read"],
        )
        client = TestClient(_make_authed_app(key_mgr))
        resp = client.post("/mutate", headers={"X-API-Key": plaintext})
        assert resp.status_code == 403
        assert "scope" in resp.json()["detail"].lower()

    def test_write_scope_passes_for_post(self, key_mgr: APIKeyManager):
        plaintext, _ = key_mgr.generate_key(
            name="writer", user_id="u1", scopes=["read", "write"],
        )
        client = TestClient(_make_authed_app(key_mgr))
        resp = client.post("/mutate", headers={"X-API-Key": plaintext})
        assert resp.status_code == 200

    def test_admin_scope_required_for_auth_endpoints(self, key_mgr: APIKeyManager):
        plaintext, _ = key_mgr.generate_key(
            name="non-admin", user_id="u1", scopes=["read", "write"],
        )
        client = TestClient(_make_authed_app(key_mgr))
        resp = client.post("/auth/admin-action", headers={"X-API-Key": plaintext})
        assert resp.status_code == 403

    def test_admin_scope_passes(self, key_mgr: APIKeyManager):
        plaintext, _ = key_mgr.generate_key(
            name="admin", user_id="u1", scopes=["read", "write", "admin"],
        )
        client = TestClient(_make_authed_app(key_mgr))
        resp = client.post("/auth/admin-action", headers={"X-API-Key": plaintext})
        assert resp.status_code == 200


# ── Auth endpoints on main app (auth disabled by default) ──


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def api(project_dir: Path) -> TestClient:
    client = TestClient(main_app)
    client.post(
        "/projects/init",
        json={"name": "Auth Test"},
        headers={"X-Project-Dir": str(project_dir)},
    )
    return client


@pytest.fixture
def headers(project_dir: Path) -> dict:
    return {"X-Project-Dir": str(project_dir)}


class TestAuthEndpoints:
    def test_keygen_endpoint(self, api: TestClient, headers: dict):
        resp = api.post("/auth/keys", json={"name": "my-key"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"].startswith("ck_")
        assert data["api_key"]["name"] == "my-key"
        assert data["api_key"]["revoked"] is False

    def test_list_keys_endpoint(self, api: TestClient):
        api.post("/auth/keys", json={"name": "k1"})
        api.post("/auth/keys", json={"name": "k2"})
        resp = api.get("/auth/keys")
        assert resp.status_code == 200
        keys = resp.json()
        assert len(keys) >= 2
        # Hashes should be redacted
        for k in keys:
            assert k["key_hash"].endswith("...")

    def test_revoke_endpoint(self, api: TestClient):
        create_resp = api.post("/auth/keys", json={"name": "to-revoke"})
        key_id = create_resp.json()["api_key"]["id"]
        resp = api.delete(f"/auth/keys/{key_id}")
        assert resp.status_code == 200
        assert "revoked" in resp.json()["detail"].lower()

    def test_revoke_nonexistent_returns_404(self, api: TestClient):
        resp = api.delete("/auth/keys/nonexistent")
        assert resp.status_code == 404

    def test_keygen_with_custom_scopes(self, api: TestClient):
        resp = api.post(
            "/auth/keys",
            json={"name": "admin-key", "scopes": ["read", "write", "admin"]},
        )
        assert resp.status_code == 200
        assert "admin" in resp.json()["api_key"]["scopes"]

    def test_keygen_with_expiry(self, api: TestClient):
        resp = api.post(
            "/auth/keys",
            json={"name": "temp-key", "expires_in_days": 30},
        )
        assert resp.status_code == 200
        assert resp.json()["api_key"]["expires_at"] is not None
