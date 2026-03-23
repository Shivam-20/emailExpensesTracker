"""
workers/training_worker.py — Background Thread for running classifier training as a subprocess.

Callbacks (passed at construction)
-------
on_log_line(str)        one line of stdout/stderr output
on_progress(int)        estimated progress 0-100
on_finished(bool, str)  (success, message)
"""

import logging
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class TrainingWorker(threading.Thread):
    """Background thread: run train_classifier.sh and stream output."""

    def __init__(
        self,
        project_dir: Path,
        model: str,   # "nb_tfidf" | "distilbert" | "both"
        mode: str,    # "train" | "retrain"
        on_log_line: Optional[Callable] = None,
        on_progress: Optional[Callable] = None,
        on_finished: Optional[Callable] = None,
        ui_ref=None,
    ) -> None:
        super().__init__(daemon=True)
        self._project_dir  = project_dir
        self._model        = model
        self._mode         = mode
        self._abort        = False
        self._ui           = ui_ref
        self._on_log_line  = on_log_line or (lambda *_: None)
        self._on_progress  = on_progress or (lambda *_: None)
        self._on_finished  = on_finished or (lambda *_: None)

    def abort(self) -> None:
        self._abort = True

    def is_running(self) -> bool:
        return self.is_alive()

    def _dispatch(self, fn: Callable, *args) -> None:
        if self._ui and self._ui.winfo_exists():
            self._ui.after(0, lambda: fn(*args))
        else:
            fn(*args)

    def run(self) -> None:
        script = self._project_dir / "scripts" / "train_classifier.sh"
        if not script.exists():
            self._dispatch(self._on_finished, False, f"Training script not found: {script}")
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
                self._dispatch(self._on_finished, False, "Training aborted by user.")
                return

            self._dispatch(self._on_log_line, f"$ {' '.join(cmd[2:])}")
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
                        self._dispatch(self._on_finished, False, "Training aborted by user.")
                        return
                    line = line.rstrip()
                    if line:
                        self._dispatch(self._on_log_line, line)
                    base = int(job_idx / total_jobs * 80) + 10
                    self._dispatch(self._on_progress, min(base + 5, 90))

                proc.wait()
                if proc.returncode != 0:
                    self._dispatch(
                        self._on_finished,
                        False, f"Training failed (exit code {proc.returncode})"
                    )
                    return
                self._dispatch(self._on_progress, int((job_idx + 1) / total_jobs * 100))

            except Exception as exc:
                logger.error("Training subprocess error: %s", exc)
                self._dispatch(self._on_finished, False, str(exc))
                return

        self._dispatch(self._on_progress, 100)
        self._dispatch(self._on_finished, True, "Training completed successfully.")
