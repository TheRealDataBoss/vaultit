"""Tests for LockManager — parametrized across FileBackend and SQLiteBackend."""

import time
from pathlib import Path

import pytest

from vaultit.backends.file import FileBackend
from vaultit.backends.lock import LockManager
from vaultit.backends.sqlite import SQLiteBackend
from vaultit.models import ProjectConfig


@pytest.fixture(params=["file", "sqlite"], ids=["FileBackend", "SQLiteBackend"])
def lock_env(request, tmp_path: Path):
    """Yield (backend, lock_manager, project_id) for each backend type."""
    if request.param == "file":
        backend = FileBackend(root=tmp_path)
    else:
        backend = SQLiteBackend(root=tmp_path)

    config = ProjectConfig(project_id="lock-test", name="Lock Test")
    backend.init_project(config)
    lm = LockManager(backend, ttl_seconds=3600)
    return backend, lm, "lock-test"


class TestLockManager:
    def test_acquire_returns_true_when_free(self, lock_env):
        _, lm, pid = lock_env
        assert lm.acquire(pid, "sess-1") is True

    def test_acquire_returns_false_when_locked_by_other(self, lock_env):
        _, lm, pid = lock_env
        lm.acquire(pid, "sess-1")
        assert lm.acquire(pid, "sess-2") is False

    def test_acquire_returns_true_for_same_session(self, lock_env):
        _, lm, pid = lock_env
        lm.acquire(pid, "sess-1")
        assert lm.acquire(pid, "sess-1") is True  # re-entrant

    def test_release_returns_true_for_owner(self, lock_env):
        _, lm, pid = lock_env
        lm.acquire(pid, "sess-1")
        assert lm.release(pid, "sess-1") is True

    def test_release_returns_false_for_non_owner(self, lock_env):
        _, lm, pid = lock_env
        lm.acquire(pid, "sess-1")
        assert lm.release(pid, "sess-2") is False

    def test_expired_lock_can_be_acquired(self, lock_env):
        backend, _, pid = lock_env
        # Use a LockManager with TTL=0 so lock expires immediately
        lm_short = LockManager(backend, ttl_seconds=0)
        lm_short.acquire(pid, "sess-1")
        time.sleep(0.01)  # ensure expiry
        assert lm_short.acquire(pid, "sess-2") is True

    def test_is_locked_false_when_free(self, lock_env):
        _, lm, pid = lock_env
        assert lm.is_locked(pid) is False

    def test_is_locked_true_when_locked(self, lock_env):
        _, lm, pid = lock_env
        lm.acquire(pid, "sess-1")
        assert lm.is_locked(pid) is True

    def test_lock_info_returns_none_when_free(self, lock_env):
        _, lm, pid = lock_env
        assert lm.lock_info(pid) is None

    def test_lock_info_returns_dict_when_locked(self, lock_env):
        _, lm, pid = lock_env
        lm.acquire(pid, "sess-1", agent="claude")
        info = lm.lock_info(pid)
        assert info is not None
        assert info["session_id"] == "sess-1"
        assert info["agent"] == "claude"
        assert "acquired_at" in info
        assert "expires_at" in info

    def test_release_then_free(self, lock_env):
        _, lm, pid = lock_env
        lm.acquire(pid, "sess-1")
        lm.release(pid, "sess-1")
        assert lm.is_locked(pid) is False
        assert lm.lock_info(pid) is None

    def test_release_allows_other_to_acquire(self, lock_env):
        _, lm, pid = lock_env
        lm.acquire(pid, "sess-1")
        lm.release(pid, "sess-1")
        assert lm.acquire(pid, "sess-2") is True
