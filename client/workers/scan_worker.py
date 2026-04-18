"""Worker thread for scanning video directories."""

import os
from pathlib import Path
from typing import List

from PySide6.QtCore import QThread, Signal

from client.database.models import Video
from client.database.repository import VideoRepository, compute_file_hash

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".3gp", ".ts"}


class ScanWorker(QThread):
    progress = Signal(int, int)  # current, total
    video_found = Signal(str)
    finished = Signal(int)  # total videos found
    error = Signal(str)

    def __init__(self, directory: str, video_repo: VideoRepository, parent=None):
        super().__init__(parent)
        self._directory = directory
        self._video_repo = video_repo
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            video_files = self._scan_directory(self._directory)
            total = len(video_files)

            added = 0
            for i, path in enumerate(video_files):
                if self._cancelled:
                    break

                existing = self._video_repo.get_by_path(path)
                if existing is None:
                    video = Video(
                        file_path=path,
                        file_name=os.path.basename(path),
                        file_size=os.path.getsize(path),
                        status="pending",
                    )
                    self._video_repo.create(video)
                    added += 1
                    self.video_found.emit(path)

                self.progress.emit(i + 1, total)

            self.finished.emit(added)
        except Exception as e:
            self.error.emit(str(e))

    @staticmethod
    def _scan_directory(directory: str) -> List[str]:
        files = []
        for root, _, filenames in os.walk(directory):
            for fname in filenames:
                if Path(fname).suffix.lower() in VIDEO_EXTENSIONS:
                    files.append(os.path.join(root, fname))
        files.sort()
        return files
