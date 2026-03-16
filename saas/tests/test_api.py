"""Tests for DRF API endpoints."""

import hashlib

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Organization, UserProfile
from apps.projects.models import Handoff, Project, Session

User = get_user_model()


class APITestBase(TestCase):
    """Base class that sets up an authenticated API client."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="apiuser", email="api@example.com", password="testpass123"
        )
        self.org = Organization.objects.create(
            name="API Org", slug="api-org", owner=self.user
        )
        self.profile = UserProfile.objects.create(
            user=self.user, org=self.org
        )
        self.api_key = self.profile.generate_api_key()
        self.client = APIClient()
        self.client.credentials(HTTP_X_API_KEY=self.api_key)


class APIKeyAuthTests(APITestBase):
    def test_valid_key(self):
        resp = self.client.get("/api/v1/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_invalid_key(self):
        c = APIClient()
        c.credentials(HTTP_X_API_KEY="ck_invalid_key_12345")
        resp = c.get("/api/v1/auth/me/")
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_no_key(self):
        c = APIClient()
        resp = c.get("/api/v1/auth/me/")
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class ProjectAPITests(APITestBase):
    def test_list_empty(self):
        resp = self.client.get("/api/v1/projects/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json(), [])

    def test_create_project(self):
        resp = self.client.post("/api/v1/projects/", {"name": "My Project"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.json()
        self.assertEqual(data["name"], "My Project")
        self.assertEqual(data["project_id"], "my-project")

    def test_get_project(self):
        Project.objects.create(
            project_id="test-proj", name="Test", org=self.org, owner=self.user
        )
        resp = self.client.get("/api/v1/projects/test-proj/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["name"], "Test")

    def test_delete_project(self):
        Project.objects.create(
            project_id="test-proj", name="Test", org=self.org, owner=self.user
        )
        resp = self.client.delete("/api/v1/projects/test-proj/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Project.objects.filter(project_id="test-proj").exists())

    def test_project_not_found(self):
        resp = self.client.get("/api/v1/projects/nonexistent/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_org_isolation(self):
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass123"
        )
        other_org = Organization.objects.create(
            name="Other Org", slug="other-org", owner=other_user
        )
        Project.objects.create(
            project_id="secret-proj", name="Secret", org=other_org, owner=other_user
        )
        resp = self.client.get("/api/v1/projects/secret-proj/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class SessionAPITests(APITestBase):
    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(
            project_id="test-proj", name="Test", org=self.org, owner=self.user
        )

    def test_create_session(self):
        resp = self.client.post(
            "/api/v1/projects/test-proj/sessions/", {"agent": "claude"}
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.json()["agent"], "claude")

    def test_list_sessions(self):
        Session.objects.create(session_id="s1", project=self.project, agent="claude")
        resp = self.client.get("/api/v1/projects/test-proj/sessions/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.json()), 1)

    def test_close_session(self):
        Session.objects.create(session_id="s1", project=self.project)
        resp = self.client.delete("/api/v1/projects/test-proj/sessions/s1/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(resp.json()["closed_at"])


class HandoffAPITests(APITestBase):
    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(
            project_id="test-proj", name="Test", org=self.org, owner=self.user
        )
        self.session = Session.objects.create(
            session_id="s1", project=self.project, agent="claude"
        )

    def test_create_handoff(self):
        resp = self.client.post(
            "/api/v1/projects/test-proj/sessions/s1/handoffs/",
            {
                "agent": "claude",
                "tasks": [{"id": "T1", "title": "Setup", "status": "done"}],
                "decisions": [],
                "next_steps": ["Deploy"],
                "notes": "First handoff",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.json()
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["agent"], "claude")
        self.assertEqual(len(data["tasks"]), 1)

    def test_auto_increment_version(self):
        Handoff.objects.create(
            handoff_id="h1", session=self.session, version=1, agent="claude"
        )
        resp = self.client.post(
            "/api/v1/projects/test-proj/sessions/s1/handoffs/",
            {"agent": "claude"},
            format="json",
        )
        self.assertEqual(resp.json()["version"], 2)

    def test_get_handoff_by_version(self):
        Handoff.objects.create(
            handoff_id="h1", session=self.session, version=1, agent="claude",
            tasks=[{"id": "T1", "title": "Test", "status": "pending"}],
        )
        resp = self.client.get(
            "/api/v1/projects/test-proj/sessions/s1/handoffs/1/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["version"], 1)

    def test_list_handoffs(self):
        Handoff.objects.create(
            handoff_id="h1", session=self.session, version=1, agent="claude"
        )
        resp = self.client.get(
            "/api/v1/projects/test-proj/sessions/s1/handoffs/"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.json()), 1)


class BootstrapAPITests(APITestBase):
    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(
            project_id="test-proj", name="Test", org=self.org, owner=self.user
        )

    def test_bootstrap_no_handoffs(self):
        resp = self.client.get("/api/v1/projects/test-proj/bootstrap/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("no handoffs", resp.json()["briefing"])

    def test_bootstrap_with_handoff(self):
        session = Session.objects.create(
            session_id="s1", project=self.project, agent="claude"
        )
        Handoff.objects.create(
            handoff_id="h1", session=session, version=1, agent="claude",
            tasks=[{"id": "T1", "title": "Setup", "status": "done"}],
            next_steps=["Deploy"],
        )
        resp = self.client.get("/api/v1/projects/test-proj/bootstrap/")
        data = resp.json()
        self.assertIn("T1", data["briefing"])
        self.assertIn("Deploy", data["briefing"])


class TaskAPITests(APITestBase):
    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(
            project_id="test-proj", name="Test", org=self.org, owner=self.user
        )
        self.session = Session.objects.create(
            session_id="s1", project=self.project, agent="claude"
        )
        Handoff.objects.create(
            handoff_id="h1", session=self.session, version=1, agent="claude",
            tasks=[{"id": "T1", "title": "Setup", "status": "pending"}],
        )

    def test_create_task(self):
        resp = self.client.post(
            "/api/v1/projects/test-proj/tasks/",
            {"task_id": "T2", "title": "Build", "status": "in_progress", "owner": "agent"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        tasks = resp.json()["tasks"]
        task_ids = [t["id"] for t in tasks]
        self.assertIn("T1", task_ids)
        self.assertIn("T2", task_ids)

    def test_update_task(self):
        resp = self.client.patch(
            "/api/v1/projects/test-proj/tasks/T1/",
            {"status": "done"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        t1 = [t for t in resp.json()["tasks"] if t["id"] == "T1"][0]
        self.assertEqual(t1["status"], "done")

    def test_update_task_not_found(self):
        resp = self.client.patch(
            "/api/v1/projects/test-proj/tasks/NOPE/",
            {"status": "done"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class DecisionAPITests(APITestBase):
    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(
            project_id="test-proj", name="Test", org=self.org, owner=self.user
        )
        self.session = Session.objects.create(
            session_id="s1", project=self.project, agent="claude"
        )
        Handoff.objects.create(
            handoff_id="h1", session=self.session, version=1, agent="claude",
            decisions=[],
        )

    def test_create_decision(self):
        resp = self.client.post(
            "/api/v1/projects/test-proj/decisions/",
            {"decision_id": "D1", "summary": "Use Django", "rationale": "Best fit"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(resp.json()["decisions"]), 1)
        self.assertEqual(resp.json()["decisions"][0]["summary"], "Use Django")


class AuthAPITests(APITestBase):
    def test_auth_me(self):
        resp = self.client.get("/api/v1/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_generate_key(self):
        resp = self.client.post("/api/v1/auth/keys/")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("key", resp.json())
        self.assertTrue(resp.json()["key"].startswith("ck_"))

    def test_list_keys(self):
        resp = self.client.get("/api/v1/auth/keys/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("has_key", resp.json())

    def test_revoke_key(self):
        resp = self.client.delete("/api/v1/auth/keys/current/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.api_key_hash, "")


class BillingAPITests(APITestBase):
    def test_usage(self):
        resp = self.client.get("/api/v1/billing/usage/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json(), [])

    def test_plans(self):
        resp = self.client.get("/api/v1/billing/plans/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        plans = resp.json()
        self.assertEqual(len(plans), 4)
        slugs = [p["slug"] for p in plans]
        self.assertIn("free", slugs)
        self.assertIn("pro", slugs)
