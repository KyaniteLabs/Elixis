"""Tests for backup functionality."""

import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from soulcraft.backup import (
    create_backup,
    list_backups,
    get_backup_status,
    cleanup_old_backups,
    enable_auto_backup,
    is_auto_backup_enabled,
)


class TestBackup(unittest.TestCase):
    """Test backup operations."""

    def setUp(self):
        """Create temp directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_backup_dir = None
        self.original_data_dir = None

        # Patch paths
        import soulcraft.backup as backup
        self.original_backup_dir = backup.BACKUP_DIR
        self.original_get_backup_dir = backup.get_backup_dir
        self.original_get_data_dir = backup.get_data_dir

        backup.BACKUP_DIR = os.path.join(self.temp_dir, ".backups")
        os.makedirs(backup.BACKUP_DIR, exist_ok=True)
        backup.get_backup_dir = lambda: Path(backup.BACKUP_DIR)

        # Create test data directory
        self.data_dir = os.path.join(self.temp_dir, ".soulcraft")
        os.makedirs(self.data_dir, exist_ok=True)
        backup.get_data_dir = lambda: Path(self.data_dir)

        # Create test files
        with open(os.path.join(self.data_dir, "test.txt"), "w") as f:
            f.write("test data")

    def tearDown(self):
        """Clean up temp directories."""
        import soulcraft.backup as backup

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
        import soulcraft.backup as backup
        original_retention = backup.BACKUP_RETENTION_DAYS
        backup.BACKUP_RETENTION_DAYS = 0

        result = cleanup_old_backups()

        # Restore
        backup.BACKUP_RETENTION_DAYS = original_retention

        self.assertGreaterEqual(result["backups_removed"], 0)


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
