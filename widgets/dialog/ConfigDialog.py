"""综合配置对话框：打印机名称、打印文件保存地址、串口端口"""
import os
import sys
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QFormLayout, QDialogButtonBox,
    QComboBox
)
from PyQt5.QtCore import Qt

from utils.config_manager import load_config, save_config


def _get_system_printers():
    """获取系统已连接的打印机列表（Windows）"""
    if not sys.platform.startswith("win"):
        return []
    try:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        printers = win32print.EnumPrinters(flags)
        # level 1 返回 (flags, description, name, comment)
        return [p[2] for p in printers] if printers else []
    except Exception:
        return []


def _get_available_serial_ports():
    """获取系统可用的串口端口列表"""
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        return sorted([p.device for p in ports])
    except Exception:
        return []


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统配置")
        self.setMinimumWidth(840)
        self._init_ui()
        self._load_values()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setSpacing(12)

        # 打印机名称：下拉选择系统打印机，也可手动输入
        self.printer_edit = QComboBox()
        self.printer_edit.setEditable(True)
        self.printer_edit.setMinimumWidth(300)
        printer_layout = QHBoxLayout()
        printer_layout.addWidget(self.printer_edit)
        refresh_btn = QPushButton("刷新")
        refresh_btn.setToolTip("重新获取系统打印机列表")
        refresh_btn.clicked.connect(self._refresh_printers)
        printer_layout.addWidget(refresh_btn)
        form.addRow("打印机名称：", printer_layout)

        # 打印文件保存地址
        save_layout = QHBoxLayout()
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setPlaceholderText("留空则使用程序当前目录；将按年/月子目录自动归档")
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_save_path)
        save_layout.addWidget(self.save_path_edit)
        save_layout.addWidget(browse_btn)
        form.addRow("打印文件保存根目录：", save_layout)

        # 串口端口：下拉选择系统可用端口，也可手动输入
        self.port_edit = QComboBox()
        self.port_edit.setEditable(True)
        self.port_edit.setMinimumWidth(200)
        port_layout = QHBoxLayout()
        port_layout.addWidget(self.port_edit)
        port_refresh_btn = QPushButton("刷新")
        port_refresh_btn.setToolTip("重新获取可用串口列表")
        port_refresh_btn.clicked.connect(self._refresh_ports)
        port_layout.addWidget(port_refresh_btn)
        form.addRow("数据读取端口：", port_layout)

        layout.addLayout(form)

        tip = QLabel("提示：串口配置在下次开始测试时生效。")
        tip.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(tip)

        # 按钮
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _refresh_printers(self):
        """从系统获取打印机列表并填充下拉框"""
        printers = _get_system_printers()
        current = self.printer_edit.currentText().strip()
        self.printer_edit.clear()
        self.printer_edit.addItems(printers)
        if current:
            idx = self.printer_edit.findText(current)
            if idx >= 0:
                self.printer_edit.setCurrentIndex(idx)
            else:
                self.printer_edit.setCurrentText(current)

    def _refresh_ports(self):
        """从系统获取可用串口列表并填充下拉框"""
        ports = _get_available_serial_ports()
        current = self.port_edit.currentText().strip()
        self.port_edit.clear()
        self.port_edit.addItems(ports)
        if current:
            idx = self.port_edit.findText(current)
            if idx >= 0:
                self.port_edit.setCurrentIndex(idx)
            else:
                self.port_edit.setCurrentText(current)

    def _load_values(self):
        cfg = load_config()
        printers = _get_system_printers()
        self.printer_edit.clear()
        self.printer_edit.addItems(printers)
        saved_name = cfg["printer_name"]
        idx = self.printer_edit.findText(saved_name)
        if idx >= 0:
            self.printer_edit.setCurrentIndex(idx)
        else:
            self.printer_edit.setCurrentText(saved_name)
        self.save_path_edit.setText(cfg["print_save_path"])
        ports = _get_available_serial_ports()
        self.port_edit.clear()
        self.port_edit.addItems(ports)
        saved_port = cfg["serial_port"]
        idx = self.port_edit.findText(saved_port)
        if idx >= 0:
            self.port_edit.setCurrentIndex(idx)
        else:
            self.port_edit.setCurrentText(saved_port)

    def _browse_save_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择保存目录", self.save_path_edit.text())
        if path:
            self.save_path_edit.setText(path)

    def _on_accept(self):
        printer = self.printer_edit.currentText().strip()
        save_path = self.save_path_edit.text().strip()
        port = self.port_edit.currentText().strip()
        if not printer:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "提示", "请输入打印机名称。")
            return
        save_config(printer_name=printer, print_save_path=save_path or None, serial_port=port or None)
        self.accept()
