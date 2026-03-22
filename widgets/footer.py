from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt


class FooterWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 状态信息
        self.status_label = QLabel("系统就绪")
        self.status_label.setAlignment(Qt.AlignLeft)

        # 版权信息
        copyright = QLabel("© 2025 恒力吊架测试系统")
        copyright.setAlignment(Qt.AlignRight)

        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(copyright)