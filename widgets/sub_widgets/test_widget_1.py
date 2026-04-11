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
from utils.config_manager import get_serial_port, get_test_widget_1_combobox, save_test_widget_1_comboboxes
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

    # 记录表单控件
    inputs = {}
    input_manager = inputManager()
    # 数据库
    DataManager = DataManager()
    
    # ！！！！！！！！！！！！需要重点关注的地方：！！！！！！！！！！！！！ - 0410
    # 这里记录的所有传感器的值都是绝对值；
    # 只有在展示图上，是减掉了去零的，但是那边到底是否要减，还要和客户确认。

    # 最新读取的传感器的值
    _latest_x_value = None
    _latest_y_value = None
    # 归零记录的传感器的值
    _zzgl_x_value = None
    _wzgl_y_value = None
    _wzgl_x_value_hezai_min = None

    #冷态的相关数值：位移和载荷
    _lt_x_value_hezai_zhengding = None
    _lt_y_value_weiyi = None

    #最大位移：载荷
    _zdwy_x_value_hezai_max = None

    #热态的相关数值：位移和载荷
    _rt_x_value_hezai_shice = None
    _rt_y_value_weiyi = None

    _display_point = False
    _recorded_x_values = []
    _recorded_y_values = []
    _recorded_highlight = []
    _previous_highlight_y = None
    _highlight_threshold = 15

    _existing_file_path = None

    # 与 create_left_form 一致，供重置面板时恢复默认值
    PANEL_TABLE_ROWS = (
        ("工程名称", "工程名称", "combobox", {}),
        ("出厂编号", "出厂编号", "lineedit", "20260322001"),
        ("试验日期", "试验日期", "label", "2026-03-22"),
        ("管系名称", "管系名称", "lineedit", "测试管系"),
        ("管线号-支吊点号：", "管线号-支吊点号", "combobox", {}),
        ("规格型号", "规格型号", "lineedit", "测试规格"),
        ("位移方向", "位移方向", "combobox", {}),
        ("工作/热态载荷（N）", "工作载荷", "lineedit", "1223"),
        ("安装/冷态载荷（N）", "安装冷态载荷", "lineedit", "3233"),
        ("安装/冷态位置（mm）", "安装冷态位置", "lineedit", "200"),
        ("螺纹尺寸（M）", "螺纹尺寸", "lineedit", "0.3"),
        ("弹簧刚度", "弹簧刚度", "lineedit", "2000"),
        ("试验人员", "试验人员", "combobox", {}),
        ("批准人员", "批准人员", "combobox", {}),
        ("整定载荷实测值（N）", "整定载荷实测值", "label", None),
        ("载荷偏差度", "载荷偏差度", "label", None),
        ("最小位移（mm）", "最小位移", "label", None),
        ("最小位移实测载荷（N）", "最小位移实测载荷", "label", None),
        ("最大位移（mm）", "最大位移", "label", None),
        ("最大位移实测载荷（N）", "最大位移实测载荷", "label", None),
        ("测试结论", "测试结论", "label", None),
    )

    def __init__(self):
        super().__init__()
        self._has_saved = False
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
        self.cold_step_btn = QPushButton("冷态踩点")
        self.max_step_btn = QPushButton("最大位移踩点")
        self.hot_step_btn = QPushButton("热态踩点")
        self.save_data_btn = QPushButton("入库")
        for btn in (
                self.zz_zero_btn,
                self.wz_zero_btn,
                self.cold_step_btn,
                self.max_step_btn,
                self.hot_step_btn,
                self.save_data_btn,
        ):
            btn.setFont(font)
            btn.setFixedHeight(30)
        self.zz_zero_btn.setMinimumSize(90, 40)
        self.wz_zero_btn.setMinimumSize(90, 40)
        self.cold_step_btn.setMinimumSize(110, 40)
        self.max_step_btn.setMinimumSize(130, 40)
        self.hot_step_btn.setMinimumSize(110, 40)
        self.save_data_btn.setMinimumSize(90, 40)
        button_layout.addWidget(self.zz_zero_btn)
        button_layout.addWidget(self.wz_zero_btn)
        button_layout.addWidget(self.cold_step_btn)
        button_layout.addWidget(self.max_step_btn)
        button_layout.addWidget(self.hot_step_btn)
        button_layout.addWidget(self.save_data_btn)
        form_layout.addLayout(button_layout)

        self.wz_zero_btn.setEnabled(False)
        self.cold_step_btn.setEnabled(False)
        self.max_step_btn.setEnabled(False)
        self.hot_step_btn.setEnabled(False)
        self.save_data_btn.setEnabled(False)

        # 绑定槽函数
        self.wz_zero_btn.clicked.connect(self.on_wz_zero_reset)
        self.cold_step_btn.clicked.connect(self.on_cold_step_clicked)
        self.max_step_btn.clicked.connect(self.on_max_step_clicked)
        self.hot_step_btn.clicked.connect(self.on_hot_step_clicked)
        self.zz_zero_btn.clicked.connect(self.on_zz_zero_reset)
        self.save_data_btn.clicked.connect(self.on_save_data_clicked)

        # 初始化串口监听（端口从配置读取，下次启动测试时生效）
        self.listening = True  # 状态变量：是否正在监听串口
        self.serial_reader = SerialReader(port=get_serial_port(), baudrate=9600)
        self.serial_reader.data_received.connect(self.handle_data)

        # 所有表单字段统一放入表格（两列：名称 + 值）
        # 每项: (标签文本, 存储key, 控件类型, 可选配置)
        table_rows = self.PANEL_TABLE_ROWS
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
                items, default_text = get_test_widget_1_combobox(key)
                value_widget.addItems(items)
                value_widget.setCurrentText(default_text)
                value_widget.setEditable(True)
                value_widget.lineEdit().setAlignment(Qt.AlignCenter)
                inputManager.set_value(self.input_manager, key, default_text)
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

    def _apply_panel_field_defaults(self):
        """将表单控件与 input_manager 恢复为 PANEL_TABLE_ROWS 中的初始值。"""
        for item in self.PANEL_TABLE_ROWS:
            _, key, widget_type, cfg = item if len(item) == 4 else (*item[:3], None)
            w = self.inputs.get(key)
            if w is None:
                continue
            if widget_type == "lineedit":
                text = str(cfg) if cfg is not None else ""
                w.setText(text)
                inputManager.set_value(self.input_manager, key, text)
            elif widget_type == "combobox":
                items, default_text = get_test_widget_1_combobox(key)
                w.clear()
                w.addItems(items)
                w.setCurrentText(default_text)
                if w.lineEdit():
                    w.lineEdit().setAlignment(Qt.AlignCenter)
                inputManager.set_value(self.input_manager, key, default_text)
            else:
                w.setText("")
                inputManager.set_value(self.input_manager, key, "")

    def reset_panel_to_initial_state(self):
        """清空面板：将表单、绘图区与测试流程相关变量恢复为与新建界面一致。"""
        self._has_saved = False
        self._existing_file_path = None

        self._latest_x_value = None
        self._latest_y_value = None
        self._zzgl_x_value = None
        self._wzgl_y_value = None
        self._wzgl_x_value_hezai_min = None
        self._lt_x_value_hezai_zhengding = None
        self._lt_y_value_weiyi = None
        self._zdwy_x_value_hezai_max = None
        self._rt_x_value_hezai_shice = None
        self._rt_y_value_weiyi = None

        self._display_point = False
        self._recorded_x_values = []
        self._recorded_y_values = []
        self._recorded_highlight = []
        self._previous_highlight_y = None

        self._rewrite_chart_highlight_items = []

        self.current_x_min = 0
        self.current_x_max = 200
        self.current_y_min = 0
        self.current_y_max = 500

        if hasattr(self, "plot_widget"):
            self.plot_widget.clear()
            self.curve = self.plot_widget.plot(
                [], [],
                pen='b',
                symbol='o',
                symbolSize=0.5,
                symbolBrush='b'
            )
            self.plot_widget.setXRange(self.current_x_min, self.current_x_max)
            self.plot_widget.setYRange(self.current_y_min, self.current_y_max)

        self.zz_zero_btn.setEnabled(True)
        self.wz_zero_btn.setEnabled(False)
        self.cold_step_btn.setEnabled(False)
        self.max_step_btn.setEnabled(False)
        self.hot_step_btn.setEnabled(False)
        self.save_data_btn.setEnabled(False)

        self._apply_panel_field_defaults()

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
            self._wzgl_x_value_hezai_min = self._latest_x_value
            QMessageBox.information(self, "提示", f"成功将位置归零值设置为：{self._wzgl_y_value}")
        else:
            QMessageBox.warning(self, "提示", "读取位置清零位置值失败，请重新读取。")
            return
        
        self._display_point = True

        self.wz_zero_btn.setEnabled(False)
        self.cold_step_btn.setEnabled(True)
        # 归零成功后，踩点按钮链路开始，禁用位置归零按钮（避免重复归零破坏链路）
        self.max_step_btn.setEnabled(False)
        self.hot_step_btn.setEnabled(False)
        self.save_data_btn.setEnabled(False)
        
    def persist_test_widget_comboboxes(self):
        """将当前所有 combobox 的下拉项与当前文本写入 app_config.json。"""
        data = {}
        for key, w in self.inputs.items():
            if isinstance(w, QComboBox):
                items = [w.itemText(i) for i in range(w.count())]
                data[key] = {"items": items, "value": w.currentText().strip()}
        save_test_widget_1_comboboxes(data)

    def on_cold_step_clicked(self):
        if self._latest_x_value is not None and self._latest_y_value is not None:
            # 冷态踩点：整定载荷与位移
            self._lt_x_value_hezai_zhengding = self._latest_x_value
            self._lt_y_value_weiyi = self._latest_y_value
        else:
            QMessageBox.warning(self, "提示", "读取冷态踩点位置值失败，请重新读取。")
            return

        # 显示到面板 label（整定载荷实测值）
        w = self.inputs.get("整定载荷实测值")
        if isinstance(w, QLabel):
            w.setText(str(self._lt_x_value_hezai_zhengding))
        # 同步到 input_manager，便于后续入库/打印等逻辑统一取值
        try:
            self.input_manager.set_value("整定载荷实测值", str(self._lt_x_value_hezai_zhengding))
        except Exception:
            pass

        self.cold_step_btn.setEnabled(False)
        self.max_step_btn.setEnabled(True)

    # TODO：最大位移是哪里来的？是输入的冷态位置还是这里记录热态位置？- 0410
    def on_max_step_clicked(self):
        if self._latest_x_value is not None and self._latest_y_value is not None:
            # 冷态踩点：整定载荷与位移
            self._zdwy_x_value_hezai_max = self._latest_x_value
        else:
            QMessageBox.warning(self, "提示", "读取最大位移踩点载荷值失败，请重新读取。")
            return
        # 显示到面板 label（最大位移实测载荷）
        w = self.inputs.get("最大位移实测载荷")
        if isinstance(w, QLabel):
            w.setText(str(self._zdwy_x_value_hezai_max))
        # 同步到 input_manager，便于后续入库/打印等逻辑统一取值
        try:
            self.input_manager.set_value("最大位移实测载荷", str(self._zdwy_x_value_hezai_max))
        except Exception:
            pass
        self.max_step_btn.setEnabled(False)
        self.hot_step_btn.setEnabled(True)
    
    # TODO：每次点击热态踩点后表示测试结束，则需要计算所有需要的结果，并得到最终的测试结论 - 0411
    def on_hot_step_clicked(self):
        if self._latest_x_value is not None and self._latest_y_value is not None:
            self._rt_x_value_hezai_shice = self._latest_x_value
            self._rt_y_value_weiyi = self._latest_y_value
        else:
            QMessageBox.warning(self, "提示", "读取热态踩点数据失败，请重新读取。")
            return

        test_date_str = datetime.now().strftime("%Y-%m-%d, %H:%M:%S")
        w_date = self.inputs.get("试验日期")
        if isinstance(w_date, QLabel):
            w_date.setText(test_date_str)
        try:
            self.input_manager.set_value("试验日期", test_date_str)
        except Exception:
            pass

        w_load = self.inputs.get("最大位移实测载荷")
        if isinstance(w_load, QLabel):
            w_load.setText(str(self._rt_x_value_hezai_shice))
        w_travel = self.inputs.get("最大位移")
        if isinstance(w_travel, QLabel):
            w_travel.setText(str(self._rt_y_value_weiyi))
        try:
            self.input_manager.set_value("最大位移实测载荷", str(self._rt_x_value_hezai_shice))
            self.input_manager.set_value("最大位移", str(self._rt_y_value_weiyi))
        except Exception:
            pass

        # TODO: 占位计算，待确定真实公式后替换
        computed_load_deviation = "0"
        computed_spring_stiffness = "2000"
        w_dev = self.inputs.get("载荷偏差度")
        if isinstance(w_dev, QLabel):
            w_dev.setText(computed_load_deviation)
        w_spring = self.inputs.get("弹簧刚度")
        if isinstance(w_spring, QLineEdit):
            w_spring.setText(computed_spring_stiffness)
        try:
            self.input_manager.set_value("载荷偏差度", computed_load_deviation)
            self.input_manager.set_value("弹簧刚度", computed_spring_stiffness)
        except Exception:
            pass

        self._display_point = False
        self.hot_step_btn.setEnabled(False)
        self.save_data_btn.setEnabled(True)
        self.persist_test_widget_comboboxes()

    def _sync_panel_to_input_manager(self):
        """把面板上与入库相关的字段同步到 input_manager（与 DataManager.TEST_DETAIL_COLUMNS 一致）。"""
        for _, input_key in DataManager.TEST_DETAIL_COLUMNS:
            w = self.inputs.get(input_key)
            if isinstance(w, QLineEdit):
                val = w.text()
            elif isinstance(w, QComboBox):
                val = w.currentText()
            elif isinstance(w, QLabel):
                val = w.text()
            else:
                val = self.input_manager.get_value(input_key) or ""
            self.input_manager.set_value(input_key, val)

    def get_all_data(self):
        """返回 (input_manager, x_list, y_list, highlight)，供入库与检查。"""
        return (
            self.input_manager,
            list(self._recorded_x_values),
            list(self._recorded_y_values),
            list(self._recorded_highlight),
        )

    def is_data_saved(self):
        return self._has_saved

    def mark_as_saved(self):
        self._has_saved = True

    def on_save_data_clicked(self):
        if self.is_data_saved():
            QMessageBox.warning(
                self,
                "提示",
                "当前测试数据已入库，请勿重复入库。\n如需保存新数据，请先完成新一轮测试流程。",
            )
            return

        self._sync_panel_to_input_manager()
        x_list, y_list, highlight = (
            self._recorded_x_values,
            self._recorded_y_values,
            self._recorded_highlight,
        )
        if not x_list or not y_list:
            QMessageBox.warning(
                self,
                "提示",
                "无法入库：测试数据为空。\n请先完成归零与踩点采集曲线后再入库。",
            )
            return
        if len(x_list) != len(y_list) or len(x_list) == 0:
            QMessageBox.warning(self, "提示", "无法入库：x、y 坐标点数据异常，请检查测试数据。")
            return
        if any(v is None for v in x_list) or any(v is None for v in y_list):
            QMessageBox.warning(self, "提示", "无法入库：x、y 坐标点不能为空或包含无效值。")
            return

        last_id = DataManager.save_detail(self.input_manager)
        DataManager.save_test_data(last_id, x_list, y_list, highlight)
        self.mark_as_saved()
        self.save_data_btn.setEnabled(False)
        self.zz_zero_btn.setEnabled(True)
        self.save_high_res_chart()

        mw = self.window()
        if mw is not None and hasattr(mw, "now_handle_data_id"):
            mw.now_handle_data_id = last_id

        QMessageBox.information(self, "提示", "入库成功！可以打印或者重新测试。")

    # 在测试过程中，用来创建图表
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

    # 在测试过程中，用来更新图上的点数据
    def update_chart(self, x: list, y: list):
        if hasattr(self, 'curve'):
            self.curve.setData(x, y)


    def _create_highlight_plot_items(self, x: float, y: float):
        """创建与 highlight_plot 相同样式的散点与标签（由调用方 addItem）。"""
        scatter = pg.ScatterPlotItem(
            [x], [y],
            symbol='o',
            size=7,
            brush='r',
            pen='k'
        )
        view_range = self.plot_widget.getViewBox().viewRange()
        x_range = view_range[0]
        y_range = view_range[1]
        x_offset = (x_range[1] - x_range[0]) * 0.03
        y_offset = (y_range[1] - y_range[0]) * 0.03
        label_x = x + x_offset
        label_y = y + y_offset
        label = TextItem(f"{x:.3f}", anchor=(0.5, 1), color=(0, 0, 0))
        label.setPos(label_x, label_y)
        return scatter, label

    # 在测试过程中，用来在图上绘制高亮的点以及它的标签
    def highlight_plot(self, x: float, y: float):
        scatter, label = self._create_highlight_plot_items(x, y)
        self.plot_widget.addItem(scatter)
        self.plot_widget.addItem(label)
    
    # 在导入数据的时候调用，用来在界面上绘制所有点，包括高亮的点
    def rewrite_chart(self):
        if not hasattr(self, 'plot_widget'):
            return

        # 清空散点、标签等所有项，否则会保留上一次高亮
        self.plot_widget.clear()
        self.curve = self.plot_widget.plot(
            [], [],
            pen='b',
            symbol='o',
            symbolSize=0.5,
            symbolBrush='b'
        )

        if not self._recorded_x_values or not self._recorded_y_values or len(self._recorded_x_values) != len(self._recorded_y_values):
            return

        self.curve.setData(self._recorded_x_values, self._recorded_y_values)
        
        hl = self._recorded_highlight if self._recorded_highlight is not None else []
        n = len(self._recorded_x_values)
        if len(hl) < n:
            hl = list(hl) + [False] * (n - len(hl))
        else:
            hl = hl[:n]
        
        for i in range(n):
            if hl[i]:
                scatter, label = self._create_highlight_plot_items(float(self._recorded_x_values[i]), float(self._recorded_y_values[i]))
                self.plot_widget.addItem(scatter)
                self.plot_widget.addItem(label)

    def save_high_res_chart(self):
        """使用matplotlib重新绘制图表并保存为高质量PNG"""
        # 设置matplotlib支持中文显示（按平台选择已安装字体，避免 findfont 警告）
        if sys.platform.startswith("win"):
            plt.rcParams["font.family"] = ["SimHei", "SimSun", "Microsoft YaHei"]
        else:
            plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]

        # 创建matplotlib图表
        fig, ax = plt.subplots(figsize=(10, 8), dpi=300)  # 设置高DPI以获得更高质量

        # 绘制连线
        ax.plot(self._recorded_x_values, self._recorded_y_values, color='blue', linewidth=0.8, alpha=0.7)
        # 绘制数据点
        ax.scatter(self._recorded_x_values, self._recorded_y_values, color='blue', s=0.5, alpha=0.7)

        hl = self._recorded_highlight if self._recorded_highlight is not None else []
        n = len(self._recorded_x_values)
        if len(hl) < n:
            hl = list(hl) + [False] * (n - len(hl))
        else:
            hl = hl[:n]
        
        for i in range(n):
            if hl[i]:
                ax.scatter(self._recorded_x_values[i], self._recorded_y_values[i], color='red', s=15, edgecolor='black', alpha=1.0)
                ax.text(self._recorded_x_values[i], self._recorded_y_values[i], f'{self._recorded_x_values[i]:.3f}', fontsize=14, ha='center', va='top', color='black')
        
        # 设置坐标轴标签和标题（增大字号确保打印可读）
        ax.set_title("载荷-位移特性曲线图\nLoad-Travel Performance Curve", color='purple', fontsize=16)
        ax.set_xlabel('载荷Load(kN)', fontsize=14)
        ax.set_ylabel('位移Travel(mm)', fontsize=14)
        ax.tick_params(axis='both', labelsize=14)
        # 将x轴移到上方
        ax.xaxis.tick_top()
        ax.xaxis.set_label_position('top')
        ax.tick_params(axis='x', bottom=False, top=True, labelbottom=False, labeltop=True)
        
        # 设置坐标轴范围
        ax.set_xlim(self.current_x_min, self.current_x_max)
        ax.set_ylim(self.current_y_min, self.current_y_max)
        
        # 设置y轴为0在上（反转y轴）
        ax.invert_yaxis()
        
        # 添加网格线
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存为PNG文件
        plt.savefig('./resources/png.png', dpi=300, bbox_inches='tight')
        plt.close(fig)  # 关闭图表以释放内存
        
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
            