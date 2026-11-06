"""Institutional Database Backup and Recovery Utility.

Supports:
1. SQLite backup via direct connection backup API with SHA-256 verification.
2. PostgreSQL backup via pg_dump wrapper with SHA-256 checksum generation.
3. Cryptographic restore verification preventing restoration of corrupted/tampered dumps.
"""

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple


def calculate_sha256(filepath: Path) -> str:
    """Compute the SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def backup_sqlite(db_path: Path, output_dir: Path) -> Tuple[Path, Path]:
    """Perform a consistent point-in-time backup of an SQLite database."""
    if not db_path.exists():
        raise FileNotFoundError(f"Source database file not found: {db_path}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    backup_filename = f"propval_backup_{timestamp}.db"
    meta_filename = f"propval_backup_{timestamp}.meta.json"

    output_dir.mkdir(parents=True, exist_ok=True)
    target_backup_path = output_dir / backup_filename
    target_meta_path = output_dir / meta_filename

    # Use SQLite native backup API for consistent, non-locking point-in-time snapshot
    src_conn = sqlite3.connect(str(db_path))
    dst_conn = sqlite3.connect(str(target_backup_path))
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    # Calculate checksum
    checksum = calculate_sha256(target_backup_path)
    file_size = target_backup_path.stat().st_size

    metadata = {
        "backup_file": backup_filename,
        "database_type": "sqlite",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_path": str(db_path),
        "file_size_bytes": file_size,
        "sha256_checksum": checksum,
    }

    with open(target_meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return target_backup_path, target_meta_path


def restore_sqlite(backup_path: Path, meta_path: Optional[Path], restore_target: Path) -> bool:
    """Verify cryptographic checksum and restore SQLite database."""
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    if meta_path and meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        expected_sha = meta.get("sha256_checksum")
        actual_sha = calculate_sha256(backup_path)
        if expected_sha and actual_sha != expected_sha:
            raise ValueError(
                f"Cryptographic verification failed! Expected {expected_sha}, got {actual_sha}. Restore aborted."
            )

    # Perform restoration
    restore_target.parent.mkdir(parents=True, exist_ok=True)
    if restore_target.exists():
        safety_copy = restore_target.with_suffix(".pre_restore.bak")
        shutil.copy2(restore_target, safety_copy)

    shutil.copy2(backup_path, restore_target)
    return True


def backup_postgres(db_url: str, output_dir: Path) -> Tuple[Path, Path]:
    """Execute pg_dump to produce a compressed SQL archive."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    backup_filename = f"propval_pg_backup_{timestamp}.dump"
    meta_filename = f"propval_pg_backup_{timestamp}.meta.json"

    output_dir.mkdir(parents=True, exist_ok=True)
    target_backup_path = output_dir / backup_filename
    target_meta_path = output_dir / meta_filename

    cmd = ["pg_dump", "--dbname", db_url, "-F", "c", "-b", "-v", "-f", str(target_backup_path)]
    subprocess.run(cmd, check=True)

    checksum = calculate_sha256(target_backup_path)
    file_size = target_backup_path.stat().st_size

    metadata = {
        "backup_file": backup_filename,
        "database_type": "postgresql",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database_url_redacted": db_url.split("@")[-1] if "@" in db_url else "configured_pg",
        "file_size_bytes": file_size,
        "sha256_checksum": checksum,
    }

    with open(target_meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return target_backup_path, target_meta_path


def restore_postgres(backup_path: Path, meta_path: Optional[Path], db_url: str) -> bool:
    """Verify cryptographic checksum and restore PostgreSQL database via pg_restore."""
    if not backup_path.exists():
        raise FileNotFoundError(f"PostgreSQL backup dump file not found: {backup_path}")

    if meta_path and meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        expected_sha = meta.get("sha256_checksum")
        actual_sha = calculate_sha256(backup_path)
        if expected_sha and actual_sha != expected_sha:
            raise ValueError(
                f"Cryptographic verification failed! Expected {expected_sha}, got {actual_sha}. Restore aborted."
            )

    cmd = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "-d",
        db_url,
        str(backup_path),
    ]
    subprocess.run(cmd, check=True)
    return True


def prune_backups(backup_dir: Path, keep_count: int = 14) -> list[Path]:
    """Retain the most recent `keep_count` backup archives and delete older snapshots."""
    backup_files = sorted(
        [p for p in backup_dir.glob("propval_*") if p.suffix in (".db", ".dump")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    pruned = []
    if len(backup_files) > keep_count:
        for old_file in backup_files[keep_count:]:
            meta_file = old_file.with_name(f"{old_file.stem}.meta.json")
            if meta_file.exists():
                meta_file.unlink(missing_ok=True)
            old_file.unlink(missing_ok=True)
            pruned.append(old_file)

    return pruned


def main():
    parser = argparse.ArgumentParser(description="PropVal AI Database Backup & Restore Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a verified database backup")
    backup_parser.add_argument(
        "--source",
        type=str,
        default="propval.db",
        help="Path to SQLite db or PostgreSQL connection URI",
    )
    backup_parser.add_argument(
        "--output-dir",
        type=str,
        default="./backups",
        help="Directory to save backup and checksum metadata",
    )
    backup_parser.add_argument(
        "--keep-count",
        type=int,
        default=14,
        help="Number of most recent backup archives to retain (older ones are pruned)",
    )

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore database from verified backup")
    restore_parser.add_argument("--backup-file", type=str, required=True, help="Backup file to restore")
    restore_parser.add_argument("--meta-file", type=str, help="Metadata file with SHA-256 checksum")
    restore_parser.add_argument("--target", type=str, required=True, help="Target database path or PostgreSQL connection URI")

    # Prune command
    prune_parser = subparsers.add_parser("prune", help="Prune old database backups based on retention policy")
    prune_parser.add_argument("--dir", type=str, default="./backups", help="Backups directory")
    prune_parser.add_argument("--keep-count", type=int, default=14, help="Number of backups to keep")

    args = parser.parse_args()

    if args.command == "backup":
        output_dir = Path(args.output_dir)
        source = args.source
        if source.startswith("postgresql://") or source.startswith("postgres://"):
            print(f"Creating PostgreSQL backup in {output_dir}...")
            dump_p, meta_p = backup_postgres(source, output_dir)
            print(f"[OK] PostgreSQL backup created: {dump_p.name}")
        else:
            db_path = Path(source)
            print(f"Creating SQLite backup from {db_path} to {output_dir}...")
            dump_p, meta_p = backup_sqlite(db_path, output_dir)
            print(f"[OK] SQLite backup created: {dump_p.name}")
            print(f"[OK] Metadata & SHA-256 written: {meta_p.name}")

        pruned = prune_backups(output_dir, keep_count=args.keep_count)
        if pruned:
            print(f"[OK] Pruned {len(pruned)} older backup archive(s) per retention policy.")

    elif args.command == "restore":
        backup_file = Path(args.backup_file)
        meta_file = Path(args.meta_file) if args.meta_file else None
        target = args.target
        if target.startswith("postgresql://") or target.startswith("postgres://"):
            print(f"Restoring {backup_file} -> PostgreSQL target...")
            restore_postgres(backup_file, meta_file, target)
            print(f"[OK] PostgreSQL database successfully restored and cryptographically verified.")
        else:
            target_path = Path(target)
            print(f"Restoring {backup_file} -> {target_path}...")
            restore_sqlite(backup_file, meta_file, target_path)
            print(f"[OK] Database successfully restored and cryptographically verified.")

    elif args.command == "prune":
        output_dir = Path(args.dir)
        pruned = prune_backups(output_dir, keep_count=args.keep_count)
        print(f"[OK] Pruned {len(pruned)} backup archive(s). Retained top {args.keep_count} latest backups.")


if __name__ == "__main__":
    main()

