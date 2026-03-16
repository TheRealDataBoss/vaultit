"""Tests for Django ORM models — accounts, projects, billing."""

from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import Organization, UserProfile
from apps.billing.models import Subscription, UsageRecord
from apps.projects.models import Handoff, Project, Session

User = get_user_model()


class OrganizationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.org = Organization.objects.create(
            name="Test Org", slug="test-org", plan="free", owner=self.user
        )

    def test_str(self):
        self.assertEqual(str(self.org), "Test Org (free)")

    def test_plan_limits_free(self):
        self.assertEqual(self.org.project_limit, 3)
        self.assertEqual(self.org.history_days, 30)
        self.assertEqual(self.org.seat_limit, 1)

    def test_plan_limits_pro(self):
        self.org.plan = "pro"
        self.org.save()
        self.assertEqual(self.org.project_limit, 0)  # unlimited
        self.assertEqual(self.org.history_days, 365)

    def test_plan_limits_team(self):
        self.org.plan = "team"
        self.assertEqual(self.org.seat_limit, 10)

    def test_plan_limits_enterprise(self):
        self.org.plan = "enterprise"
        limits = self.org.limits
        self.assertEqual(limits["projects"], 0)
        self.assertEqual(limits["history_days"], 0)
        self.assertEqual(limits["seats"], 0)

    def test_slug_unique(self):
        with self.assertRaises(IntegrityError):
            Organization.objects.create(
                name="Dupe", slug="test-org", owner=self.user
            )


class UserProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.org = Organization.objects.create(
            name="Test Org", slug="test-org", owner=self.user
        )
        self.profile = UserProfile.objects.create(
            user=self.user, org=self.org, github_username="testgh"
        )

    def test_str(self):
        self.assertIn("test@example.com", str(self.profile))
        self.assertIn("testgh", str(self.profile))

    def test_generate_api_key(self):
        key = self.profile.generate_api_key()
        self.assertTrue(key.startswith("ck_"))
        self.assertTrue(len(key) > 10)
        self.assertTrue(self.profile.api_key_hash)

    def test_verify_api_key(self):
        key = self.profile.generate_api_key()
        self.assertTrue(self.profile.verify_api_key(key))
        self.assertFalse(self.profile.verify_api_key("wrong-key"))

    def test_verify_no_key_set(self):
        self.assertFalse(self.profile.verify_api_key("anything"))

    def test_regenerate_overwrites(self):
        key1 = self.profile.generate_api_key()
        key2 = self.profile.generate_api_key()
        self.assertNotEqual(key1, key2)
        self.assertFalse(self.profile.verify_api_key(key1))
        self.assertTrue(self.profile.verify_api_key(key2))

    def test_one_to_one_user(self):
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(user=self.user)


class ProjectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.org = Organization.objects.create(
            name="Test Org", slug="test-org", owner=self.user
        )
        self.project = Project.objects.create(
            project_id="test-proj", name="Test Project", org=self.org, owner=self.user
        )

    def test_str(self):
        self.assertEqual(str(self.project), "Test Project (test-proj)")

    def test_project_id_unique(self):
        with self.assertRaises(IntegrityError):
            Project.objects.create(
                project_id="test-proj", name="Dupe", org=self.org, owner=self.user
            )

    def test_defaults(self):
        self.assertEqual(self.project.backend, "postgres")
        self.assertEqual(self.project.coordination, "sequential")


class SessionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.org = Organization.objects.create(
            name="Test Org", slug="test-org", owner=self.user
        )
        self.project = Project.objects.create(
            project_id="test-proj", name="Test", org=self.org, owner=self.user
        )
        self.session = Session.objects.create(
            session_id="sess-001", project=self.project, agent="claude"
        )

    def test_str_open(self):
        s = str(self.session)
        self.assertIn("sess-001", s)
        self.assertIn("open", s)

    def test_str_closed(self):
        from django.utils import timezone
        self.session.closed_at = timezone.now()
        self.session.save()
        self.assertIn("closed", str(self.session))

    def test_session_id_unique(self):
        with self.assertRaises(IntegrityError):
            Session.objects.create(
                session_id="sess-001", project=self.project, agent="gpt"
            )

    def test_cascade_delete(self):
        self.project.delete()
        self.assertEqual(Session.objects.filter(session_id="sess-001").count(), 0)


class HandoffTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.org = Organization.objects.create(
            name="Test Org", slug="test-org", owner=self.user
        )
        self.project = Project.objects.create(
            project_id="test-proj", name="Test", org=self.org, owner=self.user
        )
        self.session = Session.objects.create(
            session_id="sess-001", project=self.project
        )
        self.handoff = Handoff.objects.create(
            handoff_id="ho-001",
            session=self.session,
            version=1,
            agent="claude",
            tasks=[{"id": "T1", "title": "Setup", "status": "done"}],
            decisions=[{"id": "D1", "summary": "Use Django"}],
            next_steps=["Deploy"],
        )

    def test_str(self):
        self.assertIn("v1", str(self.handoff))

    def test_json_fields(self):
        ho = Handoff.objects.get(handoff_id="ho-001")
        self.assertEqual(len(ho.tasks), 1)
        self.assertEqual(ho.tasks[0]["id"], "T1")
        self.assertEqual(len(ho.decisions), 1)
        self.assertEqual(ho.next_steps, ["Deploy"])

    def test_unique_together_session_version(self):
        with self.assertRaises(IntegrityError):
            Handoff.objects.create(
                handoff_id="ho-002", session=self.session, version=1
            )

    def test_ordering(self):
        Handoff.objects.create(
            handoff_id="ho-002", session=self.session, version=2, agent="claude"
        )
        handoffs = list(Handoff.objects.filter(session=self.session))
        self.assertEqual(handoffs[0].version, 2)
        self.assertEqual(handoffs[1].version, 1)

    def test_cascade_delete(self):
        self.session.delete()
        self.assertEqual(Handoff.objects.filter(handoff_id="ho-001").count(), 0)


class SubscriptionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.org = Organization.objects.create(
            name="Test Org", slug="test-org", owner=self.user
        )
        self.sub = Subscription.objects.create(org=self.org, plan="pro")

    def test_str(self):
        self.assertEqual(str(self.sub), "Test Org - pro")

    def test_defaults(self):
        sub = Subscription.objects.create(
            org=Organization.objects.create(name="O2", slug="o2", owner=self.user)
        )
        self.assertEqual(sub.plan, "free")
        self.assertFalse(sub.cancel_at_period_end)

    def test_one_to_one(self):
        with self.assertRaises(IntegrityError):
            Subscription.objects.create(org=self.org, plan="team")


class UsageRecordTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.org = Organization.objects.create(
            name="Test Org", slug="test-org", owner=self.user
        )

    def test_create_and_str(self):
        rec = UsageRecord.objects.create(
            org=self.org, month=date(2025, 1, 1),
            handoff_count=10, session_count=5, api_call_count=100
        )
        self.assertIn("2025-01", str(rec))

    def test_unique_together_org_month(self):
        UsageRecord.objects.create(org=self.org, month=date(2025, 1, 1))
        with self.assertRaises(IntegrityError):
            UsageRecord.objects.create(org=self.org, month=date(2025, 1, 1))

    def test_defaults(self):
        rec = UsageRecord.objects.create(org=self.org, month=date(2025, 2, 1))
        self.assertEqual(rec.handoff_count, 0)
        self.assertEqual(rec.session_count, 0)
        self.assertEqual(rec.api_call_count, 0)
