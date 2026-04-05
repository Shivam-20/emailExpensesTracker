"""
core/training_data_exporter.py — Training data management: exports, imports, backups.

Provides utilities for:
- Exporting training data to CSV with versioning
- Importing CSV files
- Creating automatic backups
- Listing available training data versions
- Exporting the full expenses database
"""

import csv
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from classifier.config import DATA_DIR, TRAINING_CSV

logger = logging.getLogger(__name__)

_BACKUP_DIR = DATA_DIR / "training_backups"


def _ensure_backup_dir() -> None:
    """Ensure backup directory exists."""
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def create_backup(csv_path: Optional[Path] = None) -> Path:
    """
    Create a timestamped backup of training data.
    
    Args:
        csv_path: Path to CSV to backup (defaults to TRAINING_CSV)
    
    Returns:
        Path to the backup file
    """
    _ensure_backup_dir()
    source = csv_path or TRAINING_CSV
    
    if not source.exists():
        raise FileNotFoundError(f"Training data not found at {source}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"training_emails_backup_{timestamp}.csv"
    backup_path = _BACKUP_DIR / backup_name
    
    shutil.copy2(source, backup_path)
    logger.info("Backup created: %s", backup_path)
    return backup_path


def list_backups() -> list[dict]:
    """
    List all available training data backups.
    
    Returns:
        List of dicts with keys: filename, path, size_mb, created_at
    """
    _ensure_backup_dir()
    backups = []
    
    for path in sorted(_BACKUP_DIR.glob("training_emails_backup_*.csv")):
        stat = path.stat()
        backups.append({
            "filename": path.name,
            "path": str(path),
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return backups


def restore_backup(backup_path: Path, create_new_backup: bool = True) -> None:
    """
    Restore a backup to the main training file.
    
    Args:
        backup_path: Path to the backup file to restore
        create_new_backup: If True, create a backup of current file before restore
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    
    if create_new_backup and TRAINING_CSV.exists():
        create_backup(TRAINING_CSV)
    
    shutil.copy2(backup_path, TRAINING_CSV)
    logger.info("Restored backup %s to %s", backup_path, TRAINING_CSV)


def export_training_data(csv_path: Path, output_path: Optional[Path] = None) -> Path:
    """
    Export training data to a specified path with versioning.
    
    Args:
        csv_path: Source CSV file path
        output_path: Optional output path (defaults to DATA_DIR with timestamp)
    
    Returns:
        Path to the exported file
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Training data not found at {csv_path}")
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = DATA_DIR / f"training_emails_export_{timestamp}.csv"
    
    shutil.copy2(csv_path, output_path)
    logger.info("Exported training data to: %s", output_path)
    return output_path


def import_training_data(source_path: Path, merge: bool = False) -> int:
    """
    Import training data from a CSV file.
    
    Args:
        source_path: Path to source CSV file
        merge: If True, merge with existing data; otherwise, replace
    
    Returns:
        Number of rows in the training data after import
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    
    # Validate CSV structure
    try:
        df = pd.read_csv(source_path)
    except Exception as exc:
        raise ValueError(f"Invalid CSV file: {exc}")
    
    required_columns = {"subject", "body", "sender", "label"}
    if not required_columns.issubset(df.columns):
        raise ValueError(f"CSV must contain columns: {required_columns}")
    
    if TRAINING_CSV.exists() and merge:
        # Backup current data
        create_backup()
        
        # Merge dataframes
        existing_df = pd.read_csv(TRAINING_CSV)
        merged_df = pd.concat([existing_df, df], ignore_index=True)
        
        # Remove duplicates based on subject+body
        merged_df = merged_df.drop_duplicates(subset=["subject", "body"], keep="last")
        
        merged_df.to_csv(TRAINING_CSV, index=False)
        logger.info("Merged %d rows from %s", len(df), source_path)
    else:
        # Backup and replace
        if TRAINING_CSV.exists():
            create_backup()
        
        shutil.copy2(source_path, TRAINING_CSV)
        logger.info("Imported %d rows from %s", len(df), source_path)
    
    # Return count after import
    final_df = pd.read_csv(TRAINING_CSV)
    return len(final_df)


def get_training_data_stats(csv_path: Optional[Path] = None) -> dict:
    """
    Get statistics about the training data.
    
    Args:
        csv_path: Path to CSV file (defaults to TRAINING_CSV)
    
    Returns:
        Dict with keys: total_rows, expense_count, not_expense_count, 
                       expense_pct, not_expense_pct, file_size_mb
    """
    path = csv_path or TRAINING_CSV
    
    if not path.exists():
        return {
            "total_rows": 0,
            "expense_count": 0,
            "not_expense_count": 0,
            "expense_pct": 0.0,
            "not_expense_pct": 0.0,
            "file_size_mb": 0.0
        }
    
    try:
        df = pd.read_csv(path)
        total = len(df)
        
        if total == 0:
            return {
                "total_rows": 0,
                "expense_count": 0,
                "not_expense_count": 0,
                "expense_pct": 0.0,
                "not_expense_pct": 0.0,
                "file_size_mb": round(path.stat().st_size / (1024 * 1024), 2)
            }
        
        expense_count = len(df[df["label"] == "EXPENSE"])
        not_expense_count = len(df[df["label"] == "NOT_EXPENSE"])
        
        return {
            "total_rows": total,
            "expense_count": expense_count,
            "not_expense_count": not_expense_count,
            "expense_pct": round(expense_count / total * 100, 1),
            "not_expense_pct": round(not_expense_count / total * 100, 1),
            "file_size_mb": round(path.stat().st_size / (1024 * 1024), 2)
        }
    except Exception as exc:
        logger.error("Failed to get training data stats: %s", exc)
        return {
            "total_rows": 0,
            "expense_count": 0,
            "not_expense_count": 0,
            "expense_pct": 0.0,
            "not_expense_pct": 0.0,
            "file_size_mb": 0.0
        }


def add_training_sample(subject: str, body: str, sender: str, label: str) -> int:
    """
    Add a single training sample to the training CSV.
    
    Args:
        subject: Email subject
        body: Email body text
        sender: Sender email address
        label: Classification label (EXPENSE or NOT_EXPENSE)
    
    Returns:
        New total row count
    """
    # Validate label
    if label not in ["EXPENSE", "NOT_EXPENSE"]:
        raise ValueError(f"Label must be EXPENSE or NOT_EXPENSE, got: {label}")
    
    # Create row
    row = {"subject": subject, "body": body, "sender": sender, "label": label}
    
    # Backup if file exists
    if TRAINING_CSV.exists():
        create_backup()
    else:
        # Write header
        TRAINING_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(TRAINING_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["subject", "body", "sender", "label"])
            writer.writeheader()
    
    # Append row
    with open(TRAINING_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["subject", "body", "sender", "label"])
        writer.writerow(row)
    
    logger.info("Added training sample: label=%s, sender=%s", label, sender)
    
    # Return new count
    df = pd.read_csv(TRAINING_CSV)
    return len(df)


def load_training_data(limit: int = 50, csv_path: Optional[Path] = None) -> list[dict]:
    """
    Load training data rows for preview.
    
    Args:
        limit: Maximum number of rows to load
        csv_path: Path to CSV file (defaults to TRAINING_CSV)
    
    Returns:
        List of dicts with training data rows
    """
    path = csv_path or TRAINING_CSV
    
    if not path.exists():
        return []
    
    try:
        df = pd.read_csv(path, nrows=limit)
        return df.to_dict("records")
    except Exception as exc:
        logger.error("Failed to load training data: %s", exc)
        return []


def export_database(db_path: Path, output_path: Optional[Path] = None) -> Path:
    """
    Export the full expenses database to a CSV file.
    
    Args:
        db_path: Path to SQLite database
        output_path: Optional output path (defaults to DATA_DIR with timestamp)
    
    Returns:
        Path to the exported file
    """
    import sqlite3
    
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = DATA_DIR / f"expenses_db_export_{timestamp}.csv"
    
    conn = sqlite3.connect(db_path)
    
    try:
        df = pd.read_sql_query("SELECT * FROM expenses ORDER BY email_date DESC", conn)
        df.to_csv(output_path, index=False)
        logger.info("Exported database with %d rows to: %s", len(df), output_path)
    finally:
        conn.close()
    
    return output_path
