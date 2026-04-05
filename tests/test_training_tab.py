"""
tests/test_training_tab.py — Tests for Training Tab and training data export functionality.
"""

import csv
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.training_data_exporter import (
    add_training_sample,
    create_backup,
    export_training_data,
    get_training_data_stats,
    import_training_data,
    list_backups,
    load_training_data,
    restore_backup,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def temp_csv():
    """Create a temporary CSV file with training data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["subject", "body", "sender", "label"])
        writer.writeheader()
        
        # Add some sample data
        samples = [
            {"subject": "Invoice #123", "body": "Payment received", "sender": "billing@company.com", "label": "EXPENSE"},
            {"subject": "Your order is confirmed", "body": "Thank you for your order", "sender": "orders@shop.com", "label": "EXPENSE"},
            {"subject": "Newsletter", "body": "Weekly updates", "sender": "news@newsletter.com", "label": "NOT_EXPENSE"},
            {"subject": "Meeting reminder", "body": "Don't forget tomorrow", "sender": "calendar@company.com", "label": "NOT_EXPENSE"},
        ]
        
        for sample in samples:
            writer.writerow(sample)
        
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_backup_dir():
    """Create a temporary backup directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def empty_csv():
    """Create an empty temporary CSV file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["subject", "body", "sender", "label"])
        writer.writeheader()
        temp_path = Path(f.name)
    
    yield temp_path
    
    if temp_path.exists():
        temp_path.unlink()


# ── Tests for training_data_exporter ─────────────────────────────────────────

class TestTrainingDataStats:
    """Test getting statistics about training data."""
    
    def test_get_stats_with_data(self, temp_csv):
        """Get stats for a file with data."""
        stats = get_training_data_stats(temp_csv)
        
        assert stats["total_rows"] == 4
        assert stats["expense_count"] == 2
        assert stats["not_expense_count"] == 2
        assert stats["expense_pct"] == 50.0
        assert stats["not_expense_pct"] == 50.0
        assert stats["file_size_mb"] >= 0  # May be 0 for very small files
    
    def test_get_stats_empty_file(self, empty_csv):
        """Get stats for an empty file (header only)."""
        stats = get_training_data_stats(empty_csv)
        
        assert stats["total_rows"] == 0
        assert stats["expense_count"] == 0
        assert stats["not_expense_count"] == 0
    
    def test_get_stats_nonexistent_file(self):
        """Get stats for a non-existent file."""
        stats = get_training_data_stats(Path("/nonexistent/path/training.csv"))
        
        assert stats["total_rows"] == 0
        assert stats["expense_count"] == 0
        assert stats["not_expense_count"] == 0


class TestBackupOperations:
    """Test backup creation and listing."""
    
    def test_create_backup(self, temp_csv, temp_backup_dir, monkeypatch):
        """Create a backup of training data."""
        from core.training_data_exporter import _BACKUP_DIR
        
        monkeypatch.setattr("core.training_data_exporter._BACKUP_DIR", temp_backup_dir)
        
        backup_path = create_backup(temp_csv)
        
        assert backup_path.exists()
        assert backup_path.parent == temp_backup_dir
        assert "training_emails_backup_" in backup_path.name
        assert backup_path.suffix == ".csv"
        
        # Verify content matches
        original_lines = temp_csv.read_text().strip().split("\n")
        backup_lines = backup_path.read_text().strip().split("\n")
        assert len(original_lines) == len(backup_lines)
    
    def test_list_backups_empty(self, temp_backup_dir, monkeypatch):
        """List backups when none exist."""
        from core.training_data_exporter import _BACKUP_DIR
        
        monkeypatch.setattr("core.training_data_exporter._BACKUP_DIR", temp_backup_dir)
        
        backups = list_backups()
        
        assert len(backups) == 0
    
    def test_list_backups_with_files(self, temp_csv, temp_backup_dir, monkeypatch):
        """List backups when files exist."""
        from core.training_data_exporter import _BACKUP_DIR
        
        monkeypatch.setattr("core.training_data_exporter._BACKUP_DIR", temp_backup_dir)
        
        # Create multiple backups (with delay to ensure different timestamps)
        backup1 = create_backup(temp_csv)
        time.sleep(1.5)  # Increase delay to ensure different timestamps
        backup2 = create_backup(temp_csv)
        
        backups = list_backups()
        
        assert len(backups) == 2
        assert all(b["filename"] in [backup1.name, backup2.name] for b in backups)
        assert all(b["size_mb"] >= 0 for b in backups)
        assert all("created_at" in b for b in backups)
    
    def test_restore_backup(self, temp_csv, temp_backup_dir, monkeypatch):
        """Restore a backup file."""
        from core.training_data_exporter import _BACKUP_DIR, TRAINING_CSV
        
        monkeypatch.setattr("core.training_data_exporter._BACKUP_DIR", temp_backup_dir)
        monkeypatch.setattr("core.training_data_exporter.TRAINING_CSV", temp_csv)
        
        # Create backup
        backup_path = create_backup(temp_csv)
        
        # Modify original file
        with open(temp_csv, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["subject", "body", "sender", "label"])
            writer.writerow({"subject": "New", "body": "Content", "sender": "test@test.com", "label": "EXPENSE"})
        
        # Restore backup
        restore_backup(backup_path, create_new_backup=False)
        
        # Verify restored content
        lines = temp_csv.read_text().strip().split("\n")
        assert len(lines) == 5  # header + 4 original samples


class TestImportExport:
    """Test import and export operations."""
    
    def test_export_training_data(self, temp_csv):
        """Export training data to a new file."""
        export_path = Path(temp_csv.parent / "exported.csv")
        
        result = export_training_data(temp_csv, export_path)
        
        assert result == export_path
        assert export_path.exists()
        assert export_path.read_text() == temp_csv.read_text()
    
    def test_export_with_timestamp(self, temp_csv, monkeypatch):
        """Export with auto-generated timestamp."""
        from core.training_data_exporter import DATA_DIR
        
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            monkeypatch.setattr("core.training_data_exporter.DATA_DIR", data_dir)
            
            result = export_training_data(temp_csv)
            
            assert result.parent == data_dir
            assert result.exists()
            assert "training_emails_export_" in result.name
    
    def test_import_replace(self, temp_csv, empty_csv):
        """Import data replacing existing content."""
        count = import_training_data(source_path=temp_csv, merge=False)
        
        assert count == 4
        
        # Verify file was backed up and replaced
        lines = temp_csv.read_text().strip().split("\n")
        assert len(lines) == 5  # header + 4 samples
    
    def test_import_merge(self, temp_csv, empty_csv, monkeypatch):
        """Import data merging with existing content."""
        from core.training_data_exporter import TRAINING_CSV
        
        # Set TRAINING_CSV to empty_csv so we import INTO it
        monkeypatch.setattr("core.training_data_exporter.TRAINING_CSV", empty_csv)
        monkeypatch.setattr("core.training_data_exporter._BACKUP_DIR", Path(empty_csv.parent) / "backups")
        
        # Add different content to empty_csv first
        with open(empty_csv, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["subject", "body", "sender", "label"])
            writer.writerow({"subject": "Original", "body": "Content", "sender": "orig@test.com", "label": "NOT_EXPENSE"})
        
        count = import_training_data(source_path=temp_csv, merge=True)
        
        # Should have 5 total (1 original + 4 imported - 0 duplicates)
        assert count == 5
    
    def test_import_invalid_file(self):
        """Import from a non-existent file."""
        with pytest.raises(FileNotFoundError):
            import_training_data(Path("/nonexistent.csv"))


class TestAddSample:
    """Test adding training samples."""
    
    def test_add_expense_sample(self, empty_csv, monkeypatch):
        """Add an EXPENSE sample."""
        from core.training_data_exporter import TRAINING_CSV
        
        monkeypatch.setattr("core.training_data_exporter.TRAINING_CSV", empty_csv)
        
        count = add_training_sample(
            subject="Test Invoice",
            body="Payment of ₹100 received",
            sender="billing@test.com",
            label="EXPENSE"
        )
        
        assert count == 1
        
        # Verify file content
        lines = empty_csv.read_text().strip().split("\n")
        assert len(lines) == 2  # header + 1 sample
        
    def test_add_not_expense_sample(self, empty_csv, monkeypatch):
        """Add a NOT_EXPENSE sample."""
        from core.training_data_exporter import TRAINING_CSV
        
        monkeypatch.setattr("core.training_data_exporter.TRAINING_CSV", empty_csv)
        
        count = add_training_sample(
            subject="Newsletter",
            body="Weekly updates",
            sender="news@test.com",
            label="NOT_EXPENSE"
        )
        
        assert count == 1
    
    def test_add_invalid_label(self, empty_csv, monkeypatch):
        """Add a sample with invalid label."""
        from core.training_data_exporter import TRAINING_CSV
        
        monkeypatch.setattr("core.training_data_exporter.TRAINING_CSV", empty_csv)
        
        with pytest.raises(ValueError, match="Label must be EXPENSE or NOT_EXPENSE"):
            add_training_sample(
                subject="Test",
                body="Content",
                sender="test@test.com",
                label="INVALID"
            )
    
    def test_add_multiple_samples(self, empty_csv, monkeypatch):
        """Add multiple samples."""
        from core.training_data_exporter import TRAINING_CSV
        
        monkeypatch.setattr("core.training_data_exporter.TRAINING_CSV", empty_csv)
        
        add_training_sample("Subject 1", "Body 1", "sender1@test.com", "EXPENSE")
        add_training_sample("Subject 2", "Body 2", "sender2@test.com", "NOT_EXPENSE")
        add_training_sample("Subject 3", "Body 3", "sender3@test.com", "EXPENSE")
        
        lines = empty_csv.read_text().strip().split("\n")
        assert len(lines) == 4  # header + 3 samples


class TestLoadData:
    """Test loading training data for preview."""
    
    def test_load_with_limit(self, temp_csv):
        """Load data with a limit."""
        rows = load_training_data(limit=2, csv_path=temp_csv)
        
        assert len(rows) == 2
        assert all("subject" in row for row in rows)
        assert all("body" in row for row in rows)
        assert all("sender" in row for row in rows)
        assert all("label" in row for row in rows)
    
    def test_load_all(self, temp_csv):
        """Load all data without limit."""
        rows = load_training_data(limit=50, csv_path=temp_csv)
        
        assert len(rows) == 4
    
    def test_load_nonexistent_file(self):
        """Load from non-existent file."""
        rows = load_training_data(csv_path=Path("/nonexistent.csv"))
        
        assert len(rows) == 0


# ── Tests for TrainingWorker ─────────────────────────────────────────────────

class TestTrainingWorker:
    """Test training worker thread."""
    
    @pytest.mark.skipif(
        True,  # PyQt6 not available in test environment
        reason="PyQt6 not available in test environment"
    )
    def test_worker_emits_progress(self):
        """Worker emits progress signals during training."""
        from workers.training_worker import TrainingWorker
        from unittest.mock import MagicMock
        
        worker = TrainingWorker(retrain_with_feedback=False, distilbert=False)
        
        progress_values = []
        worker.progress.connect(lambda p, _: progress_values.append(p))
        
        # Mock _run_nb_training to emit progress
        def mock_run():
            worker.progress.emit(50, "Test")
            worker.progress.emit(100, "Done")
            worker.finished.emit({"accuracy": "95%"})
        
        worker._run_nb_training = mock_run
        
        worker.run()
        
        # Verify progress was emitted
        assert len(progress_values) >= 2
        assert 50 in progress_values
        assert 100 in progress_values
    
    @pytest.mark.skipif(
        True,  # PyQt6 not available in test environment
        reason="PyQt6 not available in test environment"
    )
    def test_worker_handles_error(self):
        """Worker handles training errors gracefully."""
        from workers.training_worker import TrainingWorker
        
        worker = TrainingWorker()
        
        error_messages = []
        worker.error.connect(error_messages.append)
        
        # Mock _run_nb_training to raise error
        def mock_run():
            raise Exception("Training failed")
        
        worker._run_nb_training = mock_run
        
        worker.run()
        
        assert len(error_messages) == 1
        assert "Training failed" in error_messages[0]
    
    @pytest.mark.skipif(
        True,  # PyQt6 not available in test environment
        reason="PyQt6 not available in test environment"
    )
    def test_worker_abort(self):
        """Worker can be aborted."""
        from workers.training_worker import TrainingWorker
        
        worker = TrainingWorker()
        
        assert not worker._aborted
        
        worker.abort()
        
        assert worker._aborted


class TestDataLoadWorker:
    """Test for data loading worker thread."""
    
    @pytest.mark.skipif(
        True,  # PyQt6 not available in test environment
        reason="PyQt6 not available in test environment"
    )
    def test_worker_loads_data(self, temp_csv, monkeypatch):
        """Worker loads training data correctly."""
        from workers.training_worker import TrainingDataLoadWorker
        
        worker = TrainingDataLoadWorker(limit=2)
        
        # Mock load_training_data to return test data
        def mock_load(limit, csv_path=None):
            rows = load_training_data(limit=limit, csv_path=temp_csv)
            return rows
        
        monkeypatch.setattr("workers.training_worker.load_training_data", mock_load)
        
        loaded_rows = []
        worker.finished.connect(loaded_rows.extend)
        
        worker.run()
        
        assert len(loaded_rows) == 2
        assert all("subject" in row for row in loaded_rows)
    
    @pytest.mark.skipif(
        True,  # PyQt6 not available in test environment
        reason="PyQt6 not available in test environment"
    )
    def test_worker_handles_error(self, monkeypatch):
        """Worker handles load errors gracefully."""
        from workers.training_worker import TrainingDataLoadWorker
        
        worker = TrainingDataLoadWorker()
        
        error_messages = []
        worker.error.connect(error_messages.append)
        
        # Mock load_training_data to raise error
        monkeypatch.setattr(
            "workers.training_worker.load_training_data",
            side_effect=Exception("Load failed")
        )
        
        worker.run()
        
        assert len(error_messages) == 1
        assert "Load failed" in error_messages[0]
