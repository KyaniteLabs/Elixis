"""Backup and restore functionality for SoulCraft data.

Manages backup creation, rotation, and restoration of .soulcraft/ data.
"""

import json
import os
import shutil
import tarfile
import gzip
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Dict


# Backup configuration
BACKUP_RETENTION_DAYS = 30
BACKUP_DIR = ".backups"
MAX_BACKUP_SIZE_MB = 100


def get_backup_dir() -> Path:
    """Get backup directory path."""
    base_dir = Path(__file__).parent.parent
    backup_dir = base_dir / BACKUP_DIR
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


def get_data_dir() -> Path:
    """Get data directory path."""
    base_dir = Path(__file__).parent.parent
    return base_dir / ".soulcraft"


def create_backup() -> Dict:
    """Create a new backup of all SoulCraft data.

    Returns:
        Backup metadata dictionary
    """
    data_dir = get_data_dir()
    backup_dir = get_backup_dir()

    # Ensure backup directory exists
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_name = f"soulcraft_backup_{timestamp}"
    backup_path = backup_dir / f"{backup_name}.tar.gz"

    backup_info = {
        "name": backup_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": str(backup_path),
        "size_bytes": 0,
        "files_backed_up": 0,
        "status": "success",
        "error": None,
    }

    try:
        if not data_dir.exists():
            backup_info["status"] = "skipped"
            backup_info["error"] = "No data directory found"
            return backup_info

        # Create tar.gz archive
        with tarfile.open(backup_path, "w:gz") as tar:
            for item in data_dir.rglob("*"):
                if item.is_file():
                    arcname = item.relative_to(data_dir.parent)
                    tar.add(item, arcname=arcname)
                    backup_info["files_backed_up"] += 1

        # Get final size
        backup_info["size_bytes"] = backup_path.stat().st_size

        # Check size limit
        size_mb = backup_info["size_bytes"] / (1024 * 1024)
        if size_mb > MAX_BACKUP_SIZE_MB:
            backup_path.unlink()
            backup_info["status"] = "failed"
            backup_info["error"] = f"Backup too large ({size_mb:.1f}MB > {MAX_BACKUP_SIZE_MB}MB)"

    except Exception as e:
        backup_info["status"] = "failed"
        backup_info["error"] = str(e)

    return backup_info


def list_backups() -> List[Dict]:
    """List all available backups.

    Returns:
        List of backup metadata dictionaries
    """
    backup_dir = get_backup_dir()
    backups = []

    if not backup_dir.exists():
        return backups

    for backup_file in sorted(backup_dir.glob("soulcraft_backup_*.tar.gz"), reverse=True):
        try:
            stat = backup_file.stat()
            backups.append({
                "name": backup_file.stem.replace(".tar", ""),
                "timestamp": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
                "path": str(backup_file),
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
            })
        except OSError:
            continue

    return backups


def restore_backup(backup_name: str, force: bool = False) -> Dict:
    """Restore from a backup.

    Args:
        backup_name: Name of backup to restore (without extension)
        force: Skip confirmation safety check

    Returns:
        Restore result dictionary
    """
    backup_dir = get_backup_dir()
    data_dir = get_data_dir()

    result = {
        "success": False,
        "backup_name": backup_name,
        "files_restored": 0,
        "error": None,
    }

    # Find backup file
    backup_path = backup_dir / f"{backup_name}.tar.gz"
    if not backup_path.exists():
        result["error"] = f"Backup not found: {backup_name}"
        return result

    try:
        # Create safety backup of current data unless forced
        if data_dir.exists() and not force:
            safety_backup = create_backup()
            if safety_backup["status"] != "success":
                result["error"] = "Failed to create safety backup"
                return result
            result["safety_backup"] = safety_backup["name"]

        # Clear existing data
        if data_dir.exists():
            shutil.rmtree(data_dir)

        # Extract backup
        with tarfile.open(backup_path, "r:gz") as tar:
            # Extract to parent directory (preserves .soulcraft/ structure)
            extract_dir = data_dir.parent
            tar.extractall(path=extract_dir)

            # Count restored files
            for member in tar.getmembers():
                if member.isfile():
                    result["files_restored"] += 1

        result["success"] = True

    except Exception as e:
        result["error"] = str(e)

    return result


def cleanup_old_backups() -> Dict:
    """Remove backups older than retention period.

    Returns:
        Cleanup result dictionary
    """
    backup_dir = get_backup_dir()
    cutoff = datetime.now(timezone.utc) - timedelta(days=BACKUP_RETENTION_DAYS)

    result = {
        "backups_removed": 0,
        "bytes_freed": 0,
        "errors": [],
    }

    if not backup_dir.exists():
        return result

    for backup_file in backup_dir.glob("soulcraft_backup_*.tar.gz"):
        try:
            stat = backup_file.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

            if mtime < cutoff:
                result["bytes_freed"] += stat.st_size
                backup_file.unlink()
                result["backups_removed"] += 1

        except OSError as e:
            result["errors"].append(f"Failed to remove {backup_file}: {e}")

    return result


def get_backup_status() -> Dict:
    """Get current backup status and statistics.

    Returns:
        Status dictionary
    """
    backup_dir = get_backup_dir()
    data_dir = get_data_dir()

    backups = list_backups()
    total_backup_size = sum(b["size_bytes"] for b in backups)

    status = {
        "backups_count": len(backups),
        "backups_total_size_mb": round(total_backup_size / (1024 * 1024), 2),
        "retention_days": BACKUP_RETENTION_DAYS,
        "latest_backup": backups[0] if backups else None,
        "data_dir_exists": data_dir.exists(),
    }

    if data_dir.exists():
        try:
            data_size = sum(f.stat().st_size for f in data_dir.rglob("*") if f.is_file())
            status["data_size_mb"] = round(data_size / (1024 * 1024), 2)
        except OSError:
            status["data_size_mb"] = None

    return status


# Auto-backup on shutdown flag
_auto_backup_enabled = True


def enable_auto_backup(enabled: bool = True):
    """Enable or disable automatic backup on shutdown."""
    global _auto_backup_enabled
    _auto_backup_enabled = enabled


def is_auto_backup_enabled() -> bool:
    """Check if auto-backup is enabled."""
    return _auto_backup_enabled


def auto_backup_if_enabled() -> Optional[Dict]:
    """Create backup if auto-backup is enabled.

    Returns:
        Backup info if created, None if disabled
    """
    if _auto_backup_enabled:
        return create_backup()
    return None
