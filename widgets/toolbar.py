from enum import auto

from PyQt5.QtWidgets import QToolBar, QPushButton, QMenu, QAction, QButtonGroup, QWidget, QSizePolicy, QLabel
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from datetime import datetime
from component.buttons import MenuButton, ChartButton1  # ChartButton2 算法2已注释


class ToolBarWidget(QToolBar):

    from enum import Enum, auto
    class TestStatus(Enum):
        no_test= auto()  # 自动分配值(从1开始)
        on_retest = auto()

    history_visible = pyqtSignal()
    clear_panel_clicked = pyqtSignal()
    # 用于打印的信号量
    print_doc_signal = pyqtSignal(int) 

    status = TestStatus.no_test

    def __init__(self):
        super().__init__()
        self.setMovable(False)
        self.init_ui()

    def init_ui(self):
        self.menu_btn = MenuButton()
        self.addWidget(self.menu_btn)

        self._add_separator()

        self.print_btn = QPushButton("打印")
        self.addWidget(self.print_btn)

        self._add_separator()

        # 查询历史
        history_btn = QPushButton("查询历史")
        history_btn.setCursor(Qt.PointingHandCursor)
        history_btn.clicked.connect(self.on_get_history)
        self.addWidget(history_btn)

        # 清空面板
        self.clear_import_btn = QPushButton("清空面板")
        self.clear_import_btn.setCursor(Qt.PointingHandCursor)
        self.clear_import_btn.clicked.connect(self.clear_panel_clicked.emit)
        self.addWidget(self.clear_import_btn)

        self._add_separator()

        # 帮助
        help_btn = QPushButton("帮助")
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.clicked.connect(self.on_help)
        self.addWidget(help_btn)

        # 右侧动态时间显示（只读），与左侧按钮留 50px 间距
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(spacer)
        gap = QWidget()
        gap.setFixedWidth(50)
        self.addWidget(gap)
        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("background-color: black; color: #00FF00; padding: 2px 6px;")
        self._update_time()
        self._time_timer = QTimer(self)
        self._time_timer.timeout.connect(self._update_time)
        self._time_timer.start(1000)  # 每秒更新
        self.addWidget(self.time_label)

        # 互斥选中：仅算法1按钮（算法2已注释）
        self._chart_button_group = QButtonGroup(self)
        self._chart_button_group.setExclusive(True)

    def _update_time(self):
        """更新时间显示"""
        self.time_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def _add_separator(self):
        """添加加粗灰色竖线分隔符（4px宽），左右间隔 margin 0 32px"""
        sep = QWidget()
        sep.setFixedWidth(4)
        sep.setStyleSheet("background-color: gray; margin: 0 32px;")
        sep.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.addWidget(sep)

    def on_print(self):
        # 发射打印信号量
        self.print_doc_signal.emit(self._now_handle_data_id) 


    def on_get_history(self):
        # print("查询历史按钮点击")
        self.history_visible.emit()

    def on_help(self):
        from widgets.dialog.HelpDialog import HelpDialog
        dialog = HelpDialog(self)
        dialog.exec_()

    def get_show_buttons(self):
        return self._show_buttons