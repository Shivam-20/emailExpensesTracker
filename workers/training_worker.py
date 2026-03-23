"""
workers/training_worker.py — QThread for running classifier training as a subprocess.

Signals
-------
log_line(str)        one line of stdout/stderr output
progress(int)        estimated progress 0-100
finished(bool, str)  (success, message)
"""

import logging
import subprocess
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class TrainingWorker(QThread):
    """Background thread: run train_classifier.sh and stream output."""

    log_line = pyqtSignal(str)        # one line of output
    progress = pyqtSignal(int)        # 0-100 estimated
    finished = pyqtSignal(bool, str)  # (success, message)

    def __init__(
        self,
        project_dir: Path,
        model: str,   # "nb_tfidf" | "distilbert" | "both"
        mode: str,    # "train" | "retrain"
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._project_dir = project_dir
        self._model = model
        self._mode = mode
        self._abort = False

    def abort(self) -> None:
        self._abort = True

    def run(self) -> None:
        script = self._project_dir / "scripts" / "train_classifier.sh"
        if not script.exists():
            self.finished.emit(False, f"Training script not found: {script}")
            return

        jobs: list[list[str]] = []
        if self._model in ("nb_tfidf", "both"):
            cmd = ["bash", str(script)]
            if self._mode == "retrain":
                cmd.append("--retrain")
            jobs.append(cmd)
        if self._model in ("distilbert", "both"):
            cmd = ["bash", str(script), "--distilbert"]
            if self._mode == "retrain":
                cmd.append("--retrain")
            jobs.append(cmd)

        total_jobs = len(jobs)
        for job_idx, cmd in enumerate(jobs):
            if self._abort:
                self.finished.emit(False, "Training aborted by user.")
                return

            self.log_line.emit(f"$ {' '.join(cmd[2:])}")  # show args, skip "bash script"
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(self._project_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                for line in proc.stdout:
                    if self._abort:
                        proc.terminate()
                        self.finished.emit(False, "Training aborted by user.")
                        return
                    line = line.rstrip()
                    if line:
                        self.log_line.emit(line)
                    base = int(job_idx / total_jobs * 80) + 10
                    self.progress.emit(min(base + 5, 90))

                proc.wait()
                if proc.returncode != 0:
                    self.finished.emit(
                        False, f"Training failed (exit code {proc.returncode})"
                    )
                    return
                self.progress.emit(int((job_idx + 1) / total_jobs * 100))

            except Exception as exc:
                logger.error("Training subprocess error: %s", exc)
                self.finished.emit(False, str(exc))
                return

        self.progress.emit(100)
        self.finished.emit(True, "Training completed successfully.")
