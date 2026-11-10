"""State-machine tests for the backup outcome (elixis.backup.BackupStatus)."""

import json
import random
import tarfile
from pathlib import Path
from unittest import mock

import pytest

from elixis import backup
from elixis.backup import (
    TERMINAL_BACKUP_STATUSES,
    BackupStatus,
    IllegalBackupTransition,
    _fail_backup,
    _finish_backup,
    _settle,
    _skip_backup,
    create_backup,
    list_backups,
)


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    backup_dir = tmp_path / ".backups"
    backup_dir.mkdir()
    data_dir = tmp_path / ".elixis"
    data_dir.mkdir()
    (data_dir / "a.txt").write_text("a")
    (data_dir / "b.txt").write_text("b")
    monkeypatch.setattr(backup, "get_backup_dir", lambda: backup_dir)
    monkeypatch.setattr(backup, "get_data_dir", lambda: data_dir)
    return backup_dir, data_dir


def _fresh():
    return {"status": BackupStatus.IN_PROGRESS, "error": None}


class TestTable:
    def test_stored_values_are_unchanged(self):
        assert {s.value for s in TERMINAL_BACKUP_STATUSES} == {"success", "skipped", "failed"}

    def test_every_status_is_initial_or_terminal(self):
        assert set(BackupStatus) == TERMINAL_BACKUP_STATUSES | {BackupStatus.IN_PROGRESS}

    def test_status_is_json_string(self):
        assert json.dumps({"status": BackupStatus.SUCCESS}) == '{"status": "success"}'


@pytest.mark.parametrize("start", list(BackupStatus), ids=lambda s: s.value)
@pytest.mark.parametrize("target", list(BackupStatus), ids=lambda s: s.value)
def test_settle_exhaustive(start, target):
    info = {"status": start, "error": None}
    legal = start is BackupStatus.IN_PROGRESS and target in TERMINAL_BACKUP_STATUSES
    if legal:
        _settle(info, target, "why" if target is not BackupStatus.SUCCESS else None)
        assert info["status"] is target
    else:
        with pytest.raises(IllegalBackupTransition):
            _settle(info, target)
        assert info["status"] is start


def test_named_moves(tmp_path):
    assert _finish_backup(_fresh()) == {"status": "success", "error": None}
    assert _skip_backup(_fresh(), "nope") == {"status": "skipped", "error": "nope"}
    partial = tmp_path / "x.tar.gz"
    partial.write_bytes(b"partial")
    assert _fail_backup(_fresh(), partial, "boom") == {"status": "failed", "error": "boom"}
    assert not partial.exists()


def test_second_outcome_is_refused():
    info = _finish_backup(_fresh())
    with pytest.raises(IllegalBackupTransition):
        _skip_backup(info, "late")


def test_legacy_plain_string_status_compares_equal():
    # Callers/older code comparing against plain strings keep working.
    assert BackupStatus("success") == "success"
    assert {"status": "failed"}["status"] == BackupStatus.FAILED


class TestCreateBackupOutcomes:
    def test_success(self, dirs):
        info = create_backup()
        assert info["status"] == "success" and info["error"] is None
        assert Path(info["path"]).exists()

    def test_skipped(self, dirs, monkeypatch):
        monkeypatch.setattr(backup, "get_data_dir", lambda: dirs[1].parent / "missing")
        info = create_backup()
        assert info["status"] == "skipped"
        assert list_backups() == []

    def test_too_large(self, dirs, monkeypatch):
        monkeypatch.setattr(backup, "MAX_BACKUP_SIZE_MB", -1)
        info = create_backup()
        assert info["status"] == "failed"
        assert "too large" in info["error"]
        assert list_backups() == []

    def test_failure_mid_archive_leaves_no_partial_file(self, dirs):
        """Bug: an exception while writing the archive set status=failed but
        left the partial .tar.gz on disk (only the size-limit failure path
        unlinked it). list_backups() then advertised the failed backup and
        restore_backup() would try to restore it.
        """
        real_add = tarfile.TarFile.add
        calls = {"n": 0}

        def flaky_add(self, *args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError("disk went away")
            return real_add(self, *args, **kwargs)

        with mock.patch.object(tarfile.TarFile, "add", flaky_add):
            info = create_backup()

        assert info["status"] == "failed"
        assert info["error"] == "disk went away"
        assert not Path(info["path"]).exists()
        assert list_backups() == []


@pytest.mark.parametrize("seed", range(10))
def test_random_outcomes_always_terminal_and_consistent(dirs, monkeypatch, seed):
    """Model test: random mixes of missing data / oversize / write errors.

    Invariant after every run: status is terminal, error is set iff not
    SUCCESS, and an archive exists on disk iff SUCCESS.
    """
    rng = random.Random(seed)
    _backup_dir, data_dir = dirs
    real_add = tarfile.TarFile.add
    for _ in range(6):
        scenario = rng.choice(["ok", "missing", "oversize", "write_error"])
        target = data_dir if scenario != "missing" else data_dir.parent / "nope"
        fail_writes = scenario == "write_error"
        with mock.patch.object(backup, "get_data_dir", lambda target=target: target), \
             mock.patch.object(backup, "MAX_BACKUP_SIZE_MB", -1 if scenario == "oversize" else 100):
            def add(self, *a, _fail=fail_writes, **k):
                if _fail:
                    raise OSError("x")
                return real_add(self, *a, **k)
            with mock.patch.object(tarfile.TarFile, "add", add):
                info = create_backup()
        assert info["status"] in TERMINAL_BACKUP_STATUSES
        assert (info["error"] is None) == (info["status"] == BackupStatus.SUCCESS)
        assert Path(info["path"]).exists() == (info["status"] == BackupStatus.SUCCESS)
    assert all(b["name"].startswith("elixis_backup_") for b in list_backups())
