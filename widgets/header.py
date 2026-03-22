from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont




class HeaderWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 主标题
        title = QLabel("恒力吊架性能测试系统")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(30)
        title_font.setBold(True)
        title.setFont(title_font)

        layout.addWidget(title)