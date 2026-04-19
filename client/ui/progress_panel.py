"""Progress display panel with log output."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QProgressBar,
    QLabel, QTextEdit, QPushButton,
)
from PySide6.QtCore import Qt, Slot


class ProgressPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Progress bar row
        progress_row = QHBoxLayout()
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_label = QLabel("就绪")
        progress_row.addWidget(self._progress_bar, 1)
        progress_row.addWidget(self._progress_label)
        layout.addLayout(progress_row)

        # Stage label
        self._stage_label = QLabel("")
        self._stage_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self._stage_label)

        # Log area
        self._log_area = QTextEdit()
        self._log_area.setReadOnly(True)
        self._log_area.setMaximumHeight(150)
        self._log_area.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(self._log_area)

    @Slot(int, int)
    def set_progress(self, current: int, total: int):
        if total > 0:
            pct = int(current / total * 100)
            self._progress_bar.setValue(pct)
            self._progress_label.setText(f"{current}/{total}")
        else:
            self._progress_bar.setValue(0)
            self._progress_label.setText("0/0")

    @Slot(str)
    def set_stage(self, stage: str):
        self._stage_label.setText(stage)

    @Slot(str)
    def append_log(self, message: str):
        self._log_area.append(message)
        self._log_area.verticalScrollBar().setValue(
            self._log_area.verticalScrollBar().maximum()
        )

    def reset(self):
        self._progress_bar.setValue(0)
        self._progress_label.setText("就绪")
        self._stage_label.setText("")
        self._log_area.clear()
