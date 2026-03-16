"""Tests for the vaultit REST API (FastAPI)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vaultit.server import app, _get_client


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def api(project_dir: Path) -> TestClient:
    """TestClient with X-Project-Dir header pointing at tmp_path."""
    client = TestClient(app)
    # Initialize the project
    client.post(
        "/projects/init",
        json={"name": "API Test"},
        headers={"X-Project-Dir": str(project_dir)},
    )
    return client


@pytest.fixture
def headers(project_dir: Path) -> dict:
    return {"X-Project-Dir": str(project_dir)}


# ── project endpoints ──


class TestProjectEndpoints:
    def test_init(self, project_dir: Path):
        client = TestClient(app)
        resp = client.post(
            "/projects/init",
            json={"name": "Fresh Project", "backend": "file"},
            headers={"X-Project-Dir": str(project_dir)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Fresh Project"
        assert data["project_id"] == "fresh-project"

    def test_status(self, api: TestClient, headers: dict):
        resp = api.get("/projects/status", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "API Test"
        assert data["session_count"] == 0

    def test_doctor(self, api: TestClient, headers: dict):
        resp = api.get("/projects/doctor", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["healthy"] is True
        assert len(data["checks"]) >= 3


# ── session endpoints ──


class TestSessionEndpoints:
    def test_create_session(self, api: TestClient, headers: dict):
        resp = api.post(
            "/sessions",
            json={"agent": "claude"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent"] == "claude"
        assert data["closed_at"] is None

    def test_list_sessions(self, api: TestClient, headers: dict):
        api.post("/sessions", json={"agent": "claude"}, headers=headers)
        api.post("/sessions", json={"agent": "gpt"}, headers=headers)
        resp = api.get("/sessions", headers=headers)
        assert resp.status_code == 200
        sessions = resp.json()
        assert len(sessions) >= 2

    def test_get_session(self, api: TestClient, headers: dict):
        create_resp = api.post("/sessions", json={}, headers=headers)
        session_id = create_resp.json()["id"]
        resp = api.get(f"/sessions/{session_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == session_id

    def test_close_session(self, api: TestClient, headers: dict):
        create_resp = api.post("/sessions", json={}, headers=headers)
        session_id = create_resp.json()["id"]
        resp = api.delete(f"/sessions/{session_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["closed_at"] is not None


# ── handoff endpoints ──


class TestHandoffEndpoints:
    def test_create_handoff(self, api: TestClient, headers: dict):
        resp = api.post(
            "/handoffs",
            json={"notes": "First sync", "agent": "claude"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == 1
        assert data["raw_notes"] == "First sync"

    def test_get_latest_handoff(self, api: TestClient, headers: dict):
        api.post("/handoffs", json={"notes": "v1"}, headers=headers)
        resp = api.get("/handoffs/latest", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["version"] == 1

    def test_get_latest_handoff_none(self, api: TestClient, headers: dict):
        resp = api.get("/handoffs/latest", headers=headers)
        assert resp.status_code == 200
        assert resp.json() is None

    def test_list_handoffs_for_session(self, api: TestClient, headers: dict):
        h1 = api.post("/handoffs", json={"notes": "v1"}, headers=headers).json()
        api.post("/handoffs", json={"notes": "v2"}, headers=headers)
        session_id = h1["session_id"]
        resp = api.get(f"/handoffs/{session_id}", headers=headers)
        assert resp.status_code == 200
        handoffs = resp.json()
        assert len(handoffs) == 2

    def test_get_specific_handoff(self, api: TestClient, headers: dict):
        h = api.post("/handoffs", json={"notes": "v1"}, headers=headers).json()
        session_id = h["session_id"]
        resp = api.get(f"/handoffs/{session_id}/1", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["version"] == 1

    def test_handoff_with_tasks(self, api: TestClient, headers: dict):
        resp = api.post(
            "/handoffs",
            json={
                "notes": "with tasks",
                "tasks": [{"id": "TASK-0001", "title": "Do thing"}],
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()["tasks"]) == 1


# ── task endpoints ──


class TestTaskEndpoints:
    def _seed_handoff(self, api: TestClient, headers: dict):
        api.post(
            "/handoffs",
            json={
                "tasks": [{"id": "TASK-0001", "title": "Alpha"}],
            },
            headers=headers,
        )

    def test_add_task(self, api: TestClient, headers: dict):
        self._seed_handoff(api, headers)
        resp = api.post(
            "/tasks",
            json={"task_id": "TASK-0002", "title": "Beta"},
            headers=headers,
        )
        assert resp.status_code == 200
        tasks = resp.json()["tasks"]
        assert len(tasks) == 2

    def test_update_task_status(self, api: TestClient, headers: dict):
        self._seed_handoff(api, headers)
        resp = api.patch(
            "/tasks/TASK-0001/status",
            json={"status": "done"},
            headers=headers,
        )
        assert resp.status_code == 200
        task = [t for t in resp.json()["tasks"] if t["id"] == "TASK-0001"][0]
        assert task["status"] == "done"

    def test_update_task_not_found(self, api: TestClient, headers: dict):
        self._seed_handoff(api, headers)
        resp = api.patch(
            "/tasks/TASK-9999/status",
            json={"status": "done"},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_add_task_no_handoff(self, api: TestClient, headers: dict):
        resp = api.post(
            "/tasks",
            json={"task_id": "TASK-0001", "title": "Orphan"},
            headers=headers,
        )
        assert resp.status_code == 404


# ── decision endpoints ──


class TestDecisionEndpoints:
    def _seed_handoff(self, api: TestClient, headers: dict):
        api.post("/handoffs", json={"notes": "seed"}, headers=headers)

    def test_add_decision(self, api: TestClient, headers: dict):
        self._seed_handoff(api, headers)
        resp = api.post(
            "/decisions",
            json={
                "decision_id": "DEC-0001",
                "summary": "Use file backend",
                "rationale": "Simpler",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()["decisions"]) == 1

    def test_add_decision_no_handoff(self, api: TestClient, headers: dict):
        resp = api.post(
            "/decisions",
            json={"decision_id": "DEC-0001", "summary": "No handoff"},
            headers=headers,
        )
        assert resp.status_code == 404


# ── bootstrap endpoint ──


class TestBootstrapEndpoint:
    def test_bootstrap_no_handoff(self, api: TestClient, headers: dict):
        resp = api.get("/bootstrap", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "briefing" in data

    def test_bootstrap_with_handoff(self, api: TestClient, headers: dict):
        api.post("/handoffs", json={"notes": "seed"}, headers=headers)
        resp = api.get("/bootstrap", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()["briefing"]) > 0


# ── diff endpoint ──


class TestDiffEndpoint:
    def test_diff(self, api: TestClient, headers: dict):
        api.post(
            "/handoffs",
            json={"tasks": [{"id": "TASK-0001", "title": "Alpha"}]},
            headers=headers,
        )
        api.post(
            "/handoffs",
            json={"tasks": [{"id": "TASK-0001", "title": "Alpha"}, {"id": "TASK-0002", "title": "Beta"}]},
            headers=headers,
        )
        resp = api.get("/diff/1/2", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["from_version"] == 1
        assert data["to_version"] == 2

    def test_diff_not_found(self, api: TestClient, headers: dict):
        resp = api.get("/diff/1/2", headers=headers)
        assert resp.status_code == 404
