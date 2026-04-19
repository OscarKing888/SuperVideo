"""Settings dialog for server connection and processing parameters."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QPushButton, QLabel, QGroupBox,
    QFileDialog, QDoubleSpinBox, QMessageBox,
)
from PySide6.QtCore import Qt

from client.ui.settings import AppSettings
from client.api.client import SuperVideoAPIClient


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("设置")
        self.setMinimumWidth(500)
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Server settings
        server_group = QGroupBox("中心服务器")
        server_form = QFormLayout()
        self._host_edit = QLineEdit()
        self._port_spin = QSpinBox()
        self._port_spin.setRange(1, 65535)
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        server_form.addRow("主机：", self._host_edit)
        server_form.addRow("端口：", self._port_spin)
        server_form.addRow("API 密钥：", self._api_key_edit)

        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self._test_connection)
        server_form.addRow("", test_btn)
        server_group.setLayout(server_form)
        layout.addWidget(server_group)

        # Processing settings
        proc_group = QGroupBox("处理")
        proc_form = QFormLayout()
        self._frames_edit = QLineEdit()
        self._frames_edit.setPlaceholderText("例如 5,10,30")
        self._ffmpeg_edit = QLineEdit()

        ffmpeg_row = QHBoxLayout()
        ffmpeg_row.addWidget(self._ffmpeg_edit)
        ffmpeg_browse = QPushButton("浏览")
        ffmpeg_browse.clicked.connect(self._browse_ffmpeg)
        ffmpeg_row.addWidget(ffmpeg_browse)

        self._confidence_spin = QDoubleSpinBox()
        self._confidence_spin.setRange(0.0, 1.0)
        self._confidence_spin.setSingleStep(0.05)
        self._confidence_spin.setDecimals(2)

        proc_form.addRow("帧:", self._frames_edit)
        proc_form.addRow("FFmpeg:", ffmpeg_row)
        proc_form.addRow("置信度:", self._confidence_spin)
        proc_group.setLayout(proc_form)
        layout.addWidget(proc_group)

        # Model paths
        model_group = QGroupBox("AI 模型")
        model_form = QFormLayout()
        self._yolo_edit = QLineEdit()
        self._osea_edit = QLineEdit()

        for edit, label in [(self._yolo_edit, "YOLO 模型："), (self._osea_edit, "OSEA 模型：")]:
            row = QHBoxLayout()
            row.addWidget(edit)
            btn = QPushButton("浏览")
            btn.clicked.connect(lambda _, e=edit: self._browse_model(e))
            row.addWidget(btn)
            model_form.addRow(label, row)

        model_group.setLayout(model_form)
        layout.addWidget(model_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _load_values(self):
        self._host_edit.setText(self.settings.server_host)
        self._port_spin.setValue(self.settings.server_port)
        self._api_key_edit.setText(self.settings.api_key)
        self._frames_edit.setText(self.settings.frames_to_extract)
        self._ffmpeg_edit.setText(self.settings.ffmpeg_binary)
        self._confidence_spin.setValue(self.settings.confidence_threshold)
        self._yolo_edit.setText(self.settings.yolo_model_path)
        self._osea_edit.setText(self.settings.osea_model_path)

    def get_settings(self) -> AppSettings:
        self.settings.server_host = self._host_edit.text()
        self.settings.server_port = self._port_spin.value()
        self.settings.api_key = self._api_key_edit.text()
        self.settings.frames_to_extract = self._frames_edit.text()
        self.settings.ffmpeg_binary = self._ffmpeg_edit.text()
        self.settings.confidence_threshold = self._confidence_spin.value()
        self.settings.yolo_model_path = self._yolo_edit.text()
        self.settings.osea_model_path = self._osea_edit.text()
        return self.settings

    def _test_connection(self):
        url = f"http://{self._host_edit.text()}:{self._port_spin.value()}"
        client = SuperVideoAPIClient(url, self._api_key_edit.text())
        if client.test_connection():
            QMessageBox.information(self, "成功", "连接成功！")
        else:
            QMessageBox.warning(self, "失败", "无法连接到服务器。")

    def _browse_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 FFmpeg 可执行文件")
        if path:
            self._ffmpeg_edit.setText(path)

    def _browse_model(self, edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, "选择模型文件", "", "模型文件 (*.pt *.pth);;所有文件 (*)")
        if path:
            edit.setText(path)
