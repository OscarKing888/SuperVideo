"""Main window for the SuperVideo client application."""

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QFileDialog,
    QGroupBox, QStatusBar, QMessageBox, QApplication,
)
from PySide6.QtCore import Qt, Slot

from client.database.migrations import init_database
from client.database.repository import (
    VideoRepository, FrameRepository, DetectionRepository,
    ClassificationRepository, UploadQueueRepository,
)
from client.ui.settings import AppSettings
from client.ui.settings_dialog import SettingsDialog
from client.ui.progress_panel import ProgressPanel
from client.ui.results_panel import ResultsPanel
from client.workers.scan_worker import ScanWorker
from client.workers.classify_worker import ClassifyWorker
from client.workers.upload_worker import UploadWorker
from client.api.client import SuperVideoAPIClient


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("超级视频客户端")
        self.setMinimumSize(800, 600)

        self._settings_path = os.path.join(
            os.path.expanduser("~"), ".supervideo", "settings.json"
        )
        self._settings = AppSettings.load(self._settings_path)

        if not self._settings.db_path:
            self._settings.db_path = os.path.join(
                os.path.expanduser("~"), ".supervideo", "local.db"
            )

        self._db = init_database(self._settings.db_path)
        self._video_repo = VideoRepository(self._db)
        self._frame_repo = FrameRepository(self._db)
        self._detection_repo = DetectionRepository(self._db)
        self._classification_repo = ClassificationRepository(self._db)
        self._upload_repo = UploadQueueRepository(self._db)

        self._scan_worker = None
        self._classify_worker = None
        self._upload_worker = None

        self._build_ui()
        self._update_status()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Directory selection row
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("视频目录："))
        self._dir_edit = QLineEdit(self._settings.video_directory)
        self._dir_edit.setPlaceholderText("选择包含视频文件的目录...")
        dir_row.addWidget(self._dir_edit, 1)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_directory)
        dir_row.addWidget(browse_btn)
        layout.addLayout(dir_row)

        # Server settings group
        server_group = QGroupBox("服务器连接")
        server_layout = QHBoxLayout()
        self._server_label = QLabel(
            f"{self._settings.server_host}:{self._settings.server_port}"
        )
        server_layout.addWidget(self._server_label)
        server_layout.addStretch()
        settings_btn = QPushButton("设置...")
        settings_btn.clicked.connect(self._open_settings)
        server_layout.addWidget(settings_btn)
        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self._test_connection)
        server_layout.addWidget(test_btn)
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)

        # Action buttons
        btn_row = QHBoxLayout()
        self._scan_btn = QPushButton("扫描目录")
        self._scan_btn.clicked.connect(self._start_scan)
        btn_row.addWidget(self._scan_btn)

        self._process_btn = QPushButton("开始处理")
        self._process_btn.clicked.connect(self._start_processing)
        btn_row.addWidget(self._process_btn)

        self._upload_btn = QPushButton("上传到服务器")
        self._upload_btn.clicked.connect(self._start_upload)
        btn_row.addWidget(self._upload_btn)

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel_operation)
        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)

        # Progress panel
        self._progress = ProgressPanel()
        layout.addWidget(self._progress)

        # Results panel
        self._results = ResultsPanel(self._video_repo, self._classification_repo)
        layout.addWidget(self._results, 1)

        # Status bar
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

    def _update_status(self):
        counts = self._video_repo.count_by_status()
        total = sum(counts.values())
        completed = counts.get("completed", 0)

        device_info = "CPU"
        try:
            from supervideo_bird_classifier.device import get_device_info
            info = get_device_info()
            device_info = info.get("name", info.get("device", "CPU"))
        except Exception:
            pass

        self._statusbar.showMessage(
            f"视频：{total} | 已完成：{completed} | GPU：{device_info} | 数据库：本地"
        )

    @Slot()
    def _browse_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, "选择视频目录", self._dir_edit.text()
        )
        if directory:
            self._dir_edit.setText(directory)
            self._settings.video_directory = directory

    @Slot()
    def _open_settings(self):
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec():
            self._settings = dialog.get_settings()
            self._settings.save(self._settings_path)
            self._server_label.setText(
                f"{self._settings.server_host}:{self._settings.server_port}"
            )

    @Slot()
    def _test_connection(self):
        client = SuperVideoAPIClient(self._settings.server_url, self._settings.api_key)
        if client.test_connection():
            QMessageBox.information(self, "成功", "已连接到服务器！")
        else:
            QMessageBox.warning(self, "失败", "无法连接到服务器。")

    @Slot()
    def _start_scan(self):
        directory = self._dir_edit.text()
        if not directory or not os.path.isdir(directory):
            QMessageBox.warning(self, "错误", "请选择有效的目录。")
            return

        self._settings.video_directory = directory
        self._settings.save(self._settings_path)

        self._progress.reset()
        self._set_buttons_busy(True)

        self._scan_worker = ScanWorker(directory, self._video_repo)
        self._scan_worker.progress.connect(self._progress.set_progress)
        self._scan_worker.video_found.connect(
            lambda p: self._progress.append_log(f"已找到：{os.path.basename(p)}")
        )
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_error)
        self._scan_worker.start()

    @Slot(int)
    def _on_scan_finished(self, count: int):
        self._set_buttons_busy(False)
        self._progress.append_log(f"扫描完成：发现 {count} 个新视频。")
        self._progress.set_stage("扫描完成")
        self._results.refresh()
        self._update_status()

    @Slot()
    def _start_processing(self):
        self._progress.reset()
        self._set_buttons_busy(True)

        self._classify_worker = ClassifyWorker(
            video_repo=self._video_repo,
            frame_repo=self._frame_repo,
            detection_repo=self._detection_repo,
            classification_repo=self._classification_repo,
            frames_to_extract=self._settings.frames_to_extract,
            ffmpeg_binary=self._settings.ffmpeg_binary,
            yolo_model_path=self._settings.yolo_model_path or None,
            osea_model_path=self._settings.osea_model_path or None,
        )
        self._classify_worker.progress.connect(self._progress.set_progress)
        self._classify_worker.stage.connect(self._progress.set_stage)
        self._classify_worker.log.connect(self._progress.append_log)
        self._classify_worker.video_done.connect(
            lambda vid, s: self._results.refresh()
        )
        self._classify_worker.finished.connect(self._on_process_finished)
        self._classify_worker.error.connect(self._on_error)
        self._classify_worker.start()

    @Slot()
    def _on_process_finished(self):
        self._set_buttons_busy(False)
        self._progress.set_stage("处理完成")
        self._progress.append_log("已处理所有视频。")
        self._results.refresh()
        self._update_status()

    @Slot()
    def _start_upload(self):
        videos = [v for v in self._video_repo.list_all() if v.status == "completed"]
        if not videos:
            QMessageBox.information(self, "提示", "没有可上传的已完成视频。")
            return

        for v in videos:
            self._upload_repo.enqueue(v.id, self._settings.server_url)

        self._progress.reset()
        self._set_buttons_busy(True)

        api_client = SuperVideoAPIClient(self._settings.server_url, self._settings.api_key)
        self._upload_worker = UploadWorker(
            video_repo=self._video_repo,
            frame_repo=self._frame_repo,
            detection_repo=self._detection_repo,
            classification_repo=self._classification_repo,
            upload_repo=self._upload_repo,
            api_client=api_client,
        )
        self._upload_worker.progress.connect(self._progress.set_progress)
        self._upload_worker.log.connect(self._progress.append_log)
        self._upload_worker.finished.connect(self._on_upload_finished)
        self._upload_worker.error.connect(self._on_error)
        self._upload_worker.start()

    @Slot(int)
    def _on_upload_finished(self, count: int):
        self._set_buttons_busy(False)
        self._progress.append_log(f"上传完成：已上传 {count} 个视频。")
        self._progress.set_stage("上传完成")

    @Slot()
    def _cancel_operation(self):
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.cancel()
        if self._classify_worker and self._classify_worker.isRunning():
            self._classify_worker.cancel()
        if self._upload_worker and self._upload_worker.isRunning():
            self._upload_worker.cancel()
        self._set_buttons_busy(False)
        self._progress.set_stage("已取消")

    @Slot(str)
    def _on_error(self, message: str):
        self._set_buttons_busy(False)
        self._progress.append_log(f"错误：{message}")
        QMessageBox.critical(self, "错误", message)

    def _set_buttons_busy(self, busy: bool):
        self._scan_btn.setEnabled(not busy)
        self._process_btn.setEnabled(not busy)
        self._upload_btn.setEnabled(not busy)
        self._cancel_btn.setEnabled(busy)

    def closeEvent(self, event):
        self._settings.save(self._settings_path)
        if self._db:
            self._db.close()
        super().closeEvent(event)
