"""Tests for backend migration (switch_backend)."""

from pathlib import Path

import pytest

from vaultit.client import VaultItClient
from vaultit.backends.file import FileBackend
from vaultit.backends.sqlite import SQLiteBackend
from vaultit.exceptions import VaultItError
from vaultit.models import TaskStatus


class TestMigrateFileToSqlite:
    def test_full_migration(self, tmp_path: Path):
        """Init with file backend, sync 3 handoffs, migrate to sqlite, verify."""
        client = VaultItClient(project_dir=tmp_path)
        client.init(name="migrate-test", backend_type="file")

        # Create 3 handoffs
        client.sync(
            tasks=[{"id": "TASK-0001", "title": "First"}],
            notes="Handoff 1",
            agent="claude",
        )
        client.sync(
            tasks=[
                {"id": "TASK-0001", "title": "First", "status": "done"},
                {"id": "TASK-0002", "title": "Second"},
            ],
            notes="Handoff 2",
        )
        client.sync(
            tasks=[
                {"id": "TASK-0001", "title": "First", "status": "done"},
                {"id": "TASK-0002", "title": "Second", "status": "in_progress"},
            ],
            notes="Handoff 3",
            next_steps=["Deploy"],
        )

        # Migrate
        result = client.switch_backend("sqlite")
        assert result["from"] == "file"
        assert result["to"] == "sqlite"
        assert result["sessions"] == 1
        assert result["handoffs"] == 3

        # Verify data accessible from sqlite
        assert isinstance(client.backend, SQLiteBackend)
        status = client.status()
        assert status["backend"] == "sqlite"
        assert status["session_count"] == 1
        assert status["task_counts"]["done"] == 1
        assert status["task_counts"]["in_progress"] == 1

        # Verify bootstrap works
        briefing = client.bootstrap()
        assert "TASK-0001" in briefing
        assert "TASK-0002" in briefing
        assert "Deploy" in briefing

        # Verify diff works across migrated versions
        d = client.diff(1, 3)
        assert d.from_version == 1
        assert d.to_version == 3


class TestMigrateSqliteToFile:
    def test_reverse_migration(self, tmp_path: Path):
        """Init with sqlite, sync, migrate to file, verify."""
        client = VaultItClient(project_dir=tmp_path)
        client.init(name="reverse-test", backend_type="sqlite")

        client.sync(
            tasks=[{"id": "TASK-0001", "title": "Task A"}],
            notes="SQLite handoff",
        )
        client.sync(
            tasks=[
                {"id": "TASK-0001", "title": "Task A", "status": "done"},
            ],
            notes="SQLite handoff 2",
        )

        result = client.switch_backend("file")
        assert result["from"] == "sqlite"
        assert result["to"] == "file"
        assert result["sessions"] == 1
        assert result["handoffs"] == 2

        # Verify via file backend
        assert isinstance(client.backend, FileBackend)
        briefing = client.bootstrap()
        assert "TASK-0001" in briefing
        assert "Task A" in briefing


class TestMigrateEdgeCases:
    def test_migrate_same_backend_raises(self, tmp_path: Path):
        client = VaultItClient(project_dir=tmp_path)
        client.init(name="same-test", backend_type="file")
        with pytest.raises(VaultItError, match="Already using"):
            client.switch_backend("file")

    def test_migrate_empty_project(self, tmp_path: Path):
        """Migrate with no sessions/handoffs should succeed."""
        client = VaultItClient(project_dir=tmp_path)
        client.init(name="empty-test", backend_type="file")
        result = client.switch_backend("sqlite")
        assert result["sessions"] == 0
        assert result["handoffs"] == 0
        # Should still work after migration
        status = client.status()
        assert status["backend"] == "sqlite"

    def test_migrate_preserves_config_on_success(self, tmp_path: Path):
        """Config.json should reflect new backend after migration."""
        import json
        client = VaultItClient(project_dir=tmp_path)
        client.init(name="config-test", backend_type="file")
        client.sync(notes="pre-migration")
        client.switch_backend("sqlite")

        config_path = tmp_path / ".vaultit" / "config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert data["backend"] == "sqlite"

    def test_doctor_healthy_after_migration(self, tmp_path: Path):
        """Doctor should pass after migration."""
        client = VaultItClient(project_dir=tmp_path)
        client.init(name="doctor-test", backend_type="file")
        client.sync(notes="data")
        client.switch_backend("sqlite")
        result = client.doctor()
        assert result["healthy"] is True
