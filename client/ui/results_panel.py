"""Results display panel with video/species table."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QPushButton,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Slot
from typing import List, Tuple

from client.database.repository import (
    VideoRepository, FrameRepository, DetectionRepository,
    ClassificationRepository,
)


class ResultsPanel(QWidget):
    def __init__(
        self,
        video_repo: VideoRepository,
        classification_repo: ClassificationRepository,
        parent=None,
    ):
        super().__init__(parent)
        self._video_repo = video_repo
        self._classification_repo = classification_repo
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel("结果"))
        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.clicked.connect(self.refresh)
        header.addStretch()
        header.addWidget(self._refresh_btn)
        layout.addLayout(header)

        # Video table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["视频", "状态", "检测数", "物种"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table)

        # Species summary
        self._summary_label = QLabel("")
        layout.addWidget(self._summary_label)

    @Slot()
    def refresh(self):
        videos = self._video_repo.list_all()
        self._table.setRowCount(len(videos))

        for row, video in enumerate(videos):
            self._table.setItem(row, 0, QTableWidgetItem(video.file_name))

            status_item = QTableWidgetItem(video.status)
            colors = {"completed": "#2e7d32", "error": "#c62828", "processing": "#1565c0", "pending": "#757575"}
            color = colors.get(video.status, "#000")
            status_item.setForeground(Qt.GlobalColor.white if video.status in ("completed", "error") else Qt.GlobalColor.black)
            self._table.setItem(row, 1, status_item)

            self._table.setItem(row, 2, QTableWidgetItem(""))
            self._table.setItem(row, 3, QTableWidgetItem(""))

        species = self._classification_repo.species_summary()
        if species:
            top = species[:5]
            parts = [f"{s[0]} ({s[1] or '?'}) x{s[2]}" for s in top]
            self._summary_label.setText(f"主要物种：{', '.join(parts)}")
        else:
            self._summary_label.setText("")
