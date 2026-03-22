import ast
import statistics
import sys
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox, QHBoxLayout, QVBoxLayout,
    QGridLayout, QPushButton, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal
import pyqtgraph as pg
from pyqtgraph import TextItem

from utils.serial_reader import SerialReader
from utils.config_manager import get_serial_port, get_overload_factor, get_combobox_history, save_combobox_item
from utils.data_manager import DataManager
from PO.input_data import inputManager
from pyqtgraph import InfiniteLine
from utils.calculate import *
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np
import random


class TestViewWidget_1(QWidget):
    received_data_changed = pyqtSignal(object)
    save_data_requested = pyqtSignal()

    # 记录表单控件
    inputs = {}
    _history_combobox_keys = set()
    input_manager = inputManager()
    # 数据库
    DataManager = DataManager()
    # 最新读取的传感器的值
    _latest_x_value = None
    _latest_y_value = None
    # 归零记录的传感器的值
    _zzgl_x_value = None
    _wzgl_y_value = None

    _display_point = False
    _recorded_x_values = []
    _recorded_y_values = []
    _recorded_highlight = []
    _previous_highlight_y = None
    _highlight_threshold = 15

    def __init__(self):
        super().__init__()
        self.plot_widget = pg.PlotWidget()
        # 轴范围变量
        self.current_x_min = 0
        self.current_x_max = 200
        self.current_y_min = 0
        self.current_y_max = 500

        # 整体布局：上方左右 + 下方表格
        main_layout = QHBoxLayout()
        left_panel = self.create_left_form()
        # 创建图表
        self.create_chart([], [])
        right_panel = self.plot_widget

        main_layout.addLayout(left_panel, 2)
        main_layout.addWidget(right_panel, 5)

        # bottom_panel = self.create_bottom_grid()

        layout = QVBoxLayout()
        layout.addLayout(main_layout)
        # layout.addLayout(bottom_panel)

        self.setLayout(layout)

    def create_left_form(self):
        form_layout = QVBoxLayout()
        font = QFont()
        font.setPointSize(12)
        # 记录初始值、开始、结束 三个按钮放在一排，记录初始值在第一位
        button_layout = QHBoxLayout()
        self.zz_zero_btn = QPushButton("自重归零")
        self.wz_zero_btn = QPushButton("位置归零")
        self.finish_test_btn = QPushButton("结束")
        self.save_data_btn = QPushButton("入库")
        for btn in (self.zz_zero_btn, self.wz_zero_btn, self.finish_test_btn, self.save_data_btn):
            btn.setFont(font)
            btn.setFixedHeight(30)
        self.zz_zero_btn.setMinimumSize(90, 40)
        self.wz_zero_btn.setMinimumSize(90, 40)
        self.finish_test_btn.setMinimumSize(90, 40)
        self.save_data_btn.setMinimumSize(90, 40)
        button_layout.addWidget(self.zz_zero_btn)
        button_layout.addWidget(self.wz_zero_btn)
        button_layout.addWidget(self.finish_test_btn)
        button_layout.addWidget(self.save_data_btn)
        form_layout.addLayout(button_layout)

        self.wz_zero_btn.setEnabled(False)
        self.finish_test_btn.setEnabled(False)
        self.save_data_btn.setEnabled(False)

        # 绑定槽函数
        self.wz_zero_btn.clicked.connect(self.on_wz_zero_reset)
        self.finish_test_btn.clicked.connect(self.on_finish_clicked)
        self.zz_zero_btn.clicked.connect(self.on_zz_zero_reset)
        self.save_data_btn.clicked.connect(self.on_save_data_clicked)

        # 初始化串口监听（端口从配置读取，下次启动测试时生效）
        self.listening = True  # 状态变量：是否正在监听串口
        self.serial_reader = SerialReader(port=get_serial_port(), baudrate=9600)
        self.serial_reader.data_received.connect(self.handle_data)

        # 所有表单字段统一放入表格（两列：名称 + 值）
        # 每项: (标签文本, 存储key, 控件类型, 可选配置)
        table_rows = [
            ("工程名称：", "工程名称", "combobox", {"items": ["测试工程"], "default": "测试工程", "save_history": True}),
            ("出厂编号：", "出厂编号", "lineedit", "20260322001"),
            ("试验日期：", "试验日期", "label", "2026-03-22"),
            ("管系名称：", "管系名称", "lineedit", "测试管系"),
            ("管线号-支吊点号：", "管线号-支吊点号", "combobox", {"items": ["测试吊点号"], "default": "测试吊点号", "save_history": True}),
            ("规格型号：", "规格型号", "lineedit", "测试规格"),
            ("位移方向：", "位移方向", "combobox", {"items": ["+", "-"], "default": "+"}),
            ("工作/热态载荷（N）：", "工作载荷", "lineedit", "1223"),
            ("安装/冷态载荷（N）：", "安装冷态载荷", "lineedit", "3233"),
            ("安装/冷态位置（mm）：", "安装冷态位置", "lineedit", "200"),
            ("螺纹尺寸（M）：", "螺纹尺寸", "lineedit", "0.3"),
            ("弹簧刚度：", "弹簧刚度", "lineedit", "2000"),
            ("试验人员：", "试验人员", "combobox", {"items": ["刘云佳", "张三", "李四"], "default": "刘云佳"}),
            ("批准人员：", "批准人员", "combobox", {"items": ["陈广春", "王五", "赵六"], "default": "陈广春"}),
            ("整定载荷实测值（N）：", "整定载荷实测值", "label", None),
            ("载荷偏差度：", "载荷偏差度", "label", None),
            ("最小位移（mm）：", "最小位移", "label", None),
            ("最小位移实测载荷（N）：", "最小位移实测载荷", "label", None),
            ("最大位移（mm）：", "最大位移", "label", None),
            ("最大位移实测载荷（N）：", "最大位移实测载荷", "label", None),
            ("测试结论：", "测试结论", "label", None),
        ]
        result_table = QTableWidget(len(table_rows), 2)
        result_table.horizontalHeader().setVisible(False)
        result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        result_table.verticalHeader().setVisible(False)
        result_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        result_table.setShowGrid(True)
        result_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        result_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        result_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid black;
                gridline-color: black;
            }
            QTableWidget::item {
                border: 1px solid black;
            }
            QTableWidget QLabel {
                font-size: 15px;
            }
            QTableWidget QLineEdit,
            QTableWidget QComboBox {
                font-size: 15px;
            }
        """)
        for row, item in enumerate(table_rows):
            label_text, key, widget_type, cfg = item if len(item) == 4 else (*item[:3], None)
            # 左列：名称
            label_widget = QLabel(label_text)
            label_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            result_table.setCellWidget(row, 0, label_widget)
            # 右列：值
            if widget_type == "lineedit":
                value_widget = QLineEdit()
                value_widget.setAlignment(Qt.AlignCenter)
                value_widget.setText(cfg)
                inputManager.set_value(self.input_manager, key, cfg)
            elif widget_type == "combobox":
                value_widget = QComboBox()
                value_widget.addItems(cfg["items"])
                value_widget.setCurrentText(cfg["default"])
                value_widget.setEditable(True)
                value_widget.lineEdit().setAlignment(Qt.AlignCenter)
                if cfg.get("save_history"):
                    self._history_combobox_keys.add(key)
                inputManager.set_value(self.input_manager, key, cfg["default"])
            else:
                value_widget = QLabel()
                value_widget.setStyleSheet("background-color: #F0F0F0;")
            value_widget.setMinimumHeight(28)
            if isinstance(value_widget, QLabel):
                value_widget.setAlignment(Qt.AlignCenter)
            result_table.setCellWidget(row, 1, value_widget)
            self.inputs[key] = value_widget
        self.time_input = self.inputs["试验日期"]
        form_layout.addWidget(result_table, 1)
        self.bind_signals()

        return form_layout

    # 记录表单内容
    def bind_signals(self):
        for key, widget in self.inputs.items():
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda val, k=key: self.on_input_changed(k, val))
            elif isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(lambda val, k=key: self.on_input_changed(k, val))

    def on_input_changed(self, key, value):
        self.input_manager.set_value(key.split("(")[0], value)

    def on_zz_zero_reset(self):
        if self._latest_x_value is not None:
            self._zzgl_x_value = self._latest_x_value
            QMessageBox.information(self, "提示", f"已记录自重值为：{self._zzgl_x_value}")
            self.zz_zero_btn.setEnabled(False)
            self.wz_zero_btn.setEnabled(True)
        else:
            QMessageBox.warning(self, "提示", "自重数据读取异常，请检查传感器连接。")

    def _get_input_value(self, key):
        """从控件获取当前值"""
        w = self.inputs.get(key)
        if w is None:
            return self.input_manager.get_value(key)
        if isinstance(w, QLineEdit):
            return w.text()
        if isinstance(w, QComboBox):
            return w.currentText()
        return ""

    def _validate_wz_zero_inputs(self):
        """检查位置归零所需的必填项，返回遗漏或无效的项列表"""
        errors = []
        # 必填项（字符串）
        str_fields = [
            ("工程名称", "工程名称"),
            ("出厂编号", "出厂编号"),
            ("管系名称", "管系名称"),
            ("管线号-支吊点号", "管线号-支吊点号"),
            ("规格型号", "规格型号"),
            ("位移方向", "位移方向"),
        ]
        for name, key in str_fields:
            val = self._get_input_value(key)
            if not val or not str(val).strip():
                errors.append(name + "（必填）")
        # 必填且必须为数字的项
        num_fields = [
            ("工作/热态载荷（N）", "工作载荷"),
            ("安装/冷态载荷", "安装冷态载荷"),
            ("安装/冷态位置（mm）", "安装冷态位置"),
            ("螺纹尺寸（M）", "螺纹尺寸"),
            ("弹簧刚度", "弹簧刚度"),
        ]
        for name, key in num_fields:
            val = self._get_input_value(key)
            if not val or not str(val).strip():
                errors.append(name + "（必填）")
            else:
                try:
                    float(str(val).strip())
                except (ValueError, TypeError):
                    errors.append(name + "（必须为数字）")
        return errors

    def on_wz_zero_reset(self):
        missing = self._validate_wz_zero_inputs()
        if missing:
            QMessageBox.warning(self, "提示", "以下内容未填写或填写有误，请补充完善：\n\n" + "\n".join(missing))
            return
        if self._latest_y_value is not None and self._zzgl_x_value is not None:
            self._wzgl_y_value = self._latest_y_value
            QMessageBox.information(self, "提示", f"成功将位置归零值设置为：{self._wzgl_y_value}")
        else:
            QMessageBox.warning(self, "提示", "读取位置清零位置值失败，请重新读取。")
            return
        
        base = float(self.input_manager.get_value("工作载荷"))/1000
        line1 = InfiniteLine(pos=base * 1.06, angle=90, pen='r')
        line2 = InfiniteLine(pos=base * 0.94, angle=90, pen='g')
        self.plot_widget.addItem(line1)
        self.plot_widget.addItem(line2)
        self._display_point = True

        self.wz_zero_btn.setEnabled(False)
        self.finish_test_btn.setEnabled(True)
        
    def on_finish_clicked(self):
        self._display_point = False
        self.finish_test_btn.setEnabled(False)
        self.save_data_btn.setEnabled(True)

    def on_save_data_clicked(self):
        self.save_data_requested.emit()

    def reanalyze_and_rearrange_labels(self):
        return

    def create_chart(self, x: list, y: list, x_center=5000, y_center=5000):
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setTitle("载荷-位移特性曲线图\nLoad-Travel Performance Curve", color='purple', size='14pt')
        self.plot_widget.setLabel('left', '位移Travel(mm)', **{'color': '#000', 'font-size': '12pt'})
        self.plot_widget.setLabel('top', '载荷Load(kN)', **{'color': '#000', 'font-size': '12pt'})
        self.plot_widget.showGrid(x=True, y=True)

        # 把 curve 存起来，以便后续更新
        self.curve = self.plot_widget.plot(
            x, y,
            pen='b',
            symbol='o',
            symbolSize=0.5,
            symbolBrush='b'
        )
        # 设置移动获取坐标
        self.plot_widget.getViewBox().invertY(True)
        self.plot_widget.getViewBox().setMouseEnabled(x=False, y=False)  # 禁用拖拽平移，固定图表
        self.plot_widget.setXRange(self.current_x_min, self.current_x_max)
        self.plot_widget.setYRange(self.current_y_min, self.current_y_max)


    def update_chart(self, x: list, y: list):
        if hasattr(self, 'curve'):
            self.curve.setData(x, y)


    def highlight_plot(self, x: float, y: float):
        highlight = pg.ScatterPlotItem(
            [x], [y],
            symbol='o',
            size=7,
            brush='r',
            pen='k'
        )
        self.plot_widget.addItem(highlight)

        # 获取当前视图范围
        view_range = self.plot_widget.getViewBox().viewRange()
        x_range = view_range[0]
        y_range = view_range[1]
        x_offset = (x_range[1] - x_range[0]) * 0.03  # 3%的x轴范围
        y_offset = (y_range[1] - y_range[0]) * 0.03
        label_x = x + x_offset
        label_y = y + y_offset

        label = TextItem(f"{x:.3f}", anchor=(0.5, 1), color=(0, 0, 0))
        label.setPos(label_x, label_y)
        self.plot_widget.addItem(label)

    def rewrite_chart(self, x: list, y: list, highlight: list, side_right: list):
        return

    def save_high_res_chart(self):
        return
        
    def set_x_range(self, x_min, x_max):
        self.current_x_min = x_min
        self.current_x_max = x_max
        if hasattr(self, 'plot_widget'):
            self.plot_widget.setXRange(x_min, x_max)

    def set_y_range(self, y_min, y_max):
        self.current_y_min = y_min
        self.current_y_max = y_max
        if hasattr(self, 'plot_widget'):
            self.plot_widget.setYRange(y_min, y_max)

    def handle_data(self, data):
        x, y, status = ast.literal_eval(data)
        self._latest_x_value = x
        self._latest_y_value = y

        if self._display_point:
            x = x - self._zzgl_x_value
            if x < 0:
                x = 0
            y = y - self._wzgl_y_value
            if y < 0:
                y = 0
            should_highlight = False
            if self._previous_highlight_y is not None:
                if abs(y - self._previous_highlight_y) >= self._highlight_threshold:
                    should_highlight = True
                    self._previous_highlight_y = y
                    self.highlight_plot(x, y)
            else:
                should_highlight = True
                self._previous_highlight_y = y
                self.highlight_plot(x, y)

            self._recorded_highlight.append(should_highlight)
            self._recorded_x_values.append(x)
            self._recorded_y_values.append(y)
            self.update_chart(self._recorded_x_values, self._recorded_y_values)
            