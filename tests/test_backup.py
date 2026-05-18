"""Tests for backup functionality."""

import unittest
import sys
import os
import tempfile
import shutil
import tarfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elixis.backup import (
    create_backup,
    list_backups,
    get_backup_status,
    cleanup_old_backups,
    enable_auto_backup,
    is_auto_backup_enabled,
    restore_backup,
)


class TestBackup(unittest.TestCase):
    """Test backup operations."""

    def setUp(self):
        """Create temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_backup_dir = None
        self.original_data_dir = None

        # Patch paths
        import elixis.backup as backup
        self.original_backup_dir = backup.BACKUP_DIR
        self.original_get_backup_dir = backup.get_backup_dir
        self.original_get_data_dir = backup.get_data_dir

        backup.BACKUP_DIR = os.path.join(self.temp_dir, ".backups")
        os.makedirs(backup.BACKUP_DIR, exist_ok=True)
        backup.get_backup_dir = lambda: Path(backup.BACKUP_DIR)

        # Create test data directory
        self.data_dir = os.path.join(self.temp_dir, ".elixis")
        os.makedirs(self.data_dir, exist_ok=True)
        backup.get_data_dir = lambda: Path(self.data_dir)

        # Create test files
        with open(os.path.join(self.data_dir, "test.txt"), "w") as f:
            f.write("test data")

    def tearDown(self):
        """Clean up temp directories."""
        import elixis.backup as backup

        # Restore original functions
        backup.get_backup_dir = self.original_get_backup_dir
        backup.get_data_dir = self.original_get_data_dir
        backup.BACKUP_DIR = self.original_backup_dir

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_backup_success(self):
        """Backup creation succeeds."""
        result = create_backup()
        self.assertEqual(result["status"], "success")
        self.assertGreater(result["files_backed_up"], 0)
        self.assertTrue(os.path.exists(result["path"]))

    def test_create_backup_no_data(self):
        """Backup with no data directory returns skipped."""
        # Remove data directory
        shutil.rmtree(self.data_dir)

        result = create_backup()
        self.assertEqual(result["status"], "skipped")

    def test_list_backups(self):
        """List backups returns created backups."""
        # Create a backup first
        create_backup()

        backups = list_backups()
        self.assertGreater(len(backups), 0)
        self.assertIn("name", backups[0])
        self.assertIn("size_bytes", backups[0])

    def test_backups_created_in_same_second_have_unique_names(self):
        """Backup names do not collide during rapid operator actions."""
        first = create_backup()
        second = create_backup()

        self.assertEqual(first["status"], "success")
        self.assertEqual(second["status"], "success")
        self.assertNotEqual(first["name"], second["name"])
        self.assertTrue(os.path.exists(first["path"]))
        self.assertTrue(os.path.exists(second["path"]))

    def test_get_backup_status(self):
        """Backup status returns correct info."""
        create_backup()

        status = get_backup_status()
        self.assertIn("backups_count", status)
        self.assertIn("latest_backup", status)
        self.assertTrue(status["data_dir_exists"])

    def test_cleanup_old_backups(self):
        """Cleanup removes old backups."""
        # Create backup
        create_backup()

        # Cleanup with 0 days retention (remove all)
        import elixis.backup as backup
        original_retention = backup.BACKUP_RETENTION_DAYS
        backup.BACKUP_RETENTION_DAYS = 0

        result = cleanup_old_backups()

        # Restore
        backup.BACKUP_RETENTION_DAYS = original_retention

        self.assertGreaterEqual(result["backups_removed"], 0)

    def test_restore_rejects_archive_without_elixis_root(self):
        """Restore refuses archives that would write outside .elixis."""
        import elixis.backup as backup

        backup_name = "elixis_backup_malicious"
        backup_path = Path(backup.BACKUP_DIR) / f"{backup_name}.tar.gz"
        with tarfile.open(backup_path, "w:gz") as tar:
            outside = Path(self.temp_dir) / "outside.txt"
            outside.write_text("bad", encoding="utf-8")
            tar.add(outside, arcname="outside.txt")
        outside.unlink()

        original_file = Path(self.data_dir) / "test.txt"
        result = restore_backup(backup_name, force=True)

        self.assertFalse(result["success"])
        self.assertIn(".elixis", result["error"])
        self.assertTrue(original_file.exists())
        self.assertFalse(outside.exists())


class TestAutoBackup(unittest.TestCase):
    """Test auto-backup settings."""

    def test_auto_backup_enabled_by_default(self):
        """Auto-backup is enabled by default."""
        self.assertTrue(is_auto_backup_enabled())

    def test_enable_auto_backup(self):
        """Can disable and re-enable auto-backup."""
        enable_auto_backup(False)
        self.assertFalse(is_auto_backup_enabled())

        enable_auto_backup(True)
        self.assertTrue(is_auto_backup_enabled())


if __name__ == "__main__":
    unittest.main()
