from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QStackedLayout, QLabel, QDockWidget, QTextEdit, \
    QApplication, QDialog, QMessageBox
from PyQt5.QtCore import Qt, QTimer
#from boto import connect_sns

from widgets.dialog.ConfigDialog import ConfigDialog
from widgets.header import HeaderWidget
from widgets.data_display import DataDisplayWidget
from widgets.footer import FooterWidget
from widgets.sub_widgets.test_widget_1 import TestViewWidget_1
# from widgets.sub_widgets.test_widget_2 import TestViewWidget_2  # 算法2已注释
from widgets.sub_widgets.search_history_widget import SearchHistoryWidget
from widgets.toolbar import ToolBarWidget
from utils.data_manager import DataManager
from utils.system_logger import get_logger

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from utils.print_doc import print_doc, PrintCancelled

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("变力弹簧支吊架性能测试系统")
        self.init_ui()
        self.load_styles()
        # 预期恒定度
        self.target_constancy_value = 5
        # 正在处理的表单数据id，默认-1，打印用
        self.now_handle_data_id = -1

    def init_ui(self):
        """初始化主界面布局"""
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        dock_width = (avail.width() // 5) if avail else 400  # 1/5 可用宽度

        central_widget = QWidget()

        # 主垂直布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # 中部：使用 QStackedLayout
        self.stack = QStackedLayout()
        # 中部页面1：背景文字
        self.text_label = QLabel("变力弹簧支吊架性能测试系统")
        self.stack.addWidget(self.text_label)
        # 中部页面2：图表计算1
        self.chart_widget1 = TestViewWidget_1()
        self.stack.addWidget(self.chart_widget1)
        self.current_index = 0

        # 添加各个组件
        self.header = HeaderWidget()
        self.data_display = DataDisplayWidget()

        self.chart_widget1.received_data_changed.connect(self.data_display.update_data)
        self.toolbar = ToolBarWidget()
        self.toolbar.history_visible.connect(self.history_visible)
        self.toolbar.clear_panel_clicked.connect(self.on_clear_panel)
        self.toolbar.print_btn.clicked.connect(self.handle_print_doc)
        self.toolbar.menu_btn.print_doc_signal.connect(lambda _: self.handle_print_doc())  # 菜单打印与工具栏打印同功能
        self.toolbar.menu_btn.config_clicked.connect(self.show_config_dialog)

        main_layout.addWidget(self.toolbar, alignment=Qt.AlignTop)
        main_layout.addLayout(self.stack)
        main_layout.addWidget(self.data_display, alignment=Qt.AlignBottom)

        self.setCentralWidget(central_widget)

        # 创建查询侧边栏
        self.dock = QDockWidget("查询栏", self)
        self.search_history_widget = SearchHistoryWidget()
        self.search_history_widget.set_main_window(self)
        self.dock.setWidget(self.search_history_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.setMinimumWidth(dock_width)
        self.dock.setMaximumWidth(dock_width)
        self.dock.setVisible(False)

        # 默认展示算法1界面
        self.stack.setCurrentIndex(1)
        self.current_index = 1

        self.showMaximized()

    def closeEvent(self, event):
        try:
            self.chart_widget1.persist_test_widget_comboboxes()
        except Exception:
            pass
        super().closeEvent(event)

    def handle_print_doc(self):
        # 1. 无效记录检查
        if self.now_handle_data_id <= 0:
            QMessageBox.warning(self, "提示", "无法打印：请先入库后再打印。")
            return
        # 2. 测试数据（x、y）非空检查
        x_list, y_list, highlight = DataManager.queryTestDataByFormId(self.now_handle_data_id)
        if not x_list or not y_list:
            QMessageBox.warning(self, "提示", "无法打印：该记录没有测试数据（x、y 坐标点为空），无法生成报表。")
            return
        try:
            print_doc(self.now_handle_data_id, self.chart_widget1._existing_file_path)
            # 3. 打印成功提示
            QMessageBox.information(self, "提示", "打印成功！")
        except PrintCancelled:
            pass  # 用户取消，不提示
        except Exception as e:
            QMessageBox.warning(self, "提示", f"打印失败：{e}")

    def load_styles(self):
        """加载样式表"""
        try:
            with open('resources/styles.qss', 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            # print("未找到样式表文件")
            # pass
            get_logger().warning("未找到样式表文件")

    def create_chart(self):
        fig = Figure(figsize=(4, 3))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.plot([0, 1, 2, 3], [10, 1, 20, 3])
        ax.set_title("简单折线图")
        return canvas

    # def switch_chart_2(self):  # 算法2已注释
    #     self.stack.setCurrentIndex(2)
    #
    def history_visible(self):
        opening = not self.dock.isVisible()
        if opening:
            self.search_history_widget.apply_current_year_and_search()
        self.dock.setVisible(opening)

    def on_clear_panel(self):
        """处理清空面板按钮点击：由测试页控件自身恢复初始状态。"""
        self.now_handle_data_id = -1
        self.chart_widget1.reset_panel_to_initial_state()

    def show_config_dialog(self):
        dialog = ConfigDialog(self)
        dialog.exec_()

    def calculate_constancy(self, points):
        maxP = max(points)
        minP = min(points)
        return (maxP - minP) * 100 / (maxP + minP)