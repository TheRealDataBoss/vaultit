"""Tests for dashboard views — render, redirect, auth."""

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from apps.accounts.models import Organization, UserProfile
from apps.projects.models import Handoff, Project, Session

User = get_user_model()


class IndexViewTests(TestCase):
    def test_anonymous_sees_landing_page(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "home.html")
        self.assertContains(resp, "vaultit")
        self.assertContains(resp, "Zero model drift")

    def test_authenticated_redirects_to_dashboard(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("dashboard", resp.url)


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.org = Organization.objects.create(
            name="Test Org", slug="test-org", owner=self.user
        )
        self.profile = UserProfile.objects.create(user=self.user, org=self.org)
        self.client.login(username="testuser", password="testpass123")

    def test_dashboard_renders(self):
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "dashboard/index.html")

    def test_dashboard_shows_projects(self):
        Project.objects.create(
            project_id="my-proj", name="My Project", org=self.org, owner=self.user
        )
        resp = self.client.get("/dashboard/")
        self.assertContains(resp, "My Project")

    def test_dashboard_creates_org_if_missing(self):
        user2 = User.objects.create_user(
            username="newuser", email="new@example.com", password="testpass123"
        )
        self.client.login(username="newuser", password="testpass123")
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 200)
        profile = UserProfile.objects.get(user=user2)
        self.assertIsNotNone(profile.org)

    def test_dashboard_requires_login(self):
        self.client.logout()
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 302)


class ProjectDetailViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.org = Organization.objects.create(
            name="Test Org", slug="test-org", owner=self.user
        )
        UserProfile.objects.create(user=self.user, org=self.org)
        self.project = Project.objects.create(
            project_id="my-proj", name="My Project", org=self.org, owner=self.user
        )
        self.client.login(username="testuser", password="testpass123")

    def test_renders(self):
        resp = self.client.get("/dashboard/projects/my-proj/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "dashboard/project_detail.html")
        self.assertContains(resp, "My Project")

    def test_shows_sessions(self):
        Session.objects.create(session_id="s1", project=self.project, agent="claude")
        resp = self.client.get("/dashboard/projects/my-proj/")
        self.assertContains(resp, "s1")

    def test_404_wrong_org(self):
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass123"
        )
        other_org = Organization.objects.create(
            name="Other", slug="other-org", owner=other_user
        )
        UserProfile.objects.create(user=other_user, org=other_org)
        Project.objects.create(
            project_id="secret", name="Secret", org=other_org, owner=other_user
        )
        resp = self.client.get("/dashboard/projects/secret/")
        self.assertEqual(resp.status_code, 404)


class SessionDetailViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.org = Organization.objects.create(
            name="Test Org", slug="test-org", owner=self.user
        )
        UserProfile.objects.create(user=self.user, org=self.org)
        self.project = Project.objects.create(
            project_id="my-proj", name="My Project", org=self.org, owner=self.user
        )
        self.session = Session.objects.create(
            session_id="s1", project=self.project, agent="claude"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_renders(self):
        resp = self.client.get("/dashboard/projects/my-proj/sessions/s1/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "dashboard/session_detail.html")

    def test_shows_handoffs(self):
        Handoff.objects.create(
            handoff_id="h1", session=self.session, version=1, agent="claude",
            tasks=[{"id": "T1", "title": "Setup", "status": "done"}],
        )
        resp = self.client.get("/dashboard/projects/my-proj/sessions/s1/")
        self.assertContains(resp, "v1")
        self.assertContains(resp, "Setup")

    def test_empty_handoffs(self):
        resp = self.client.get("/dashboard/projects/my-proj/sessions/s1/")
        self.assertContains(resp, "No handoffs")


class SettingsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        UserProfile.objects.create(user=self.user)
        self.client.login(username="testuser", password="testpass123")

    def test_renders(self):
        resp = self.client.get("/settings/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "accounts/settings.html")

    def test_generate_key(self):
        resp = self.client.post("/settings/", {"generate_key": "1"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ck_")

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get("/settings/")
        self.assertEqual(resp.status_code, 302)


class PlansViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_renders(self):
        resp = self.client.get("/billing/plans/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "billing/plans.html")
        self.assertContains(resp, "Pro")
        self.assertContains(resp, "Enterprise")
