from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QLabel, QComboBox, QCheckBox, QLineEdit, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QHBoxLayout, QPushButton, QDockWidget,
    QHeaderView
)
from PyQt5.QtCore import Qt
from utils import data_manager
from utils.data_manager import DataManager


class SearchHistoryWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # 查询方式
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("查询方式："))
        self.query_mode = QComboBox()
        self.query_mode.addItems(["试验日期", "用户", "出厂编号"])
        row1.addWidget(self.query_mode)
        layout.addLayout(row1)

        # 查询年份（默认当前年份）
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("查询年份："))
        self.year_box = QComboBox()
        current_year = datetime.now().year
        years = [str(y) for y in range(current_year - 2, current_year + 6)]
        self.year_box.addItems(years)
        idx = years.index(str(current_year))
        self.year_box.setCurrentIndex(idx)
        row2.addWidget(self.year_box)
        layout.addLayout(row2)

        # 复选框：全部数据 / 自动隐藏
        # row3 = QHBoxLayout()
        # self.checkbox_all = QCheckBox("全部数据")
        # self.checkbox_auto_hide = QCheckBox("自动隐藏")
        # row3.addWidget(self.checkbox_all)
        # row3.addWidget(self.checkbox_auto_hide)
        # layout.addLayout(row3)

        # 查询框（例如筛选框）
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("输入用户或者出厂编号")
        layout.addWidget(self.search_box)

        # 表格控件
        self.table = QTableWidget(5, 5)  # 修改为5列，添加导入按钮列
        self.table.setHorizontalHeaderLabels(["试验日期", "用户", "出场编号", "文件链接", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        # 连接单元格点击信号以处理链接点击
        self.table.cellClicked.connect(self.handle_cell_click)
        layout.addWidget(self.table)

        # # 删除按钮 + 输出标记复选框
        # row4 = QHBoxLayout()
        # self.delete_button = QPushButton("删除")
        # self.delete_button.setEnabled(False)
        # self.mark_checkbox = QCheckBox("输出标记")
        # row4.addWidget(self.delete_button)
        # row4.addWidget(self.mark_checkbox)
        # layout.addLayout(row4)

        # 搜索框回车触发搜索
        self.search_box.returnPressed.connect(self.handle_search)
        self.year_box.currentIndexChanged.connect(self.handle_search)
        self.handle_search()
        
        # 存储主窗口的引用，用于访问test_widget_1
        self.main_window = None

    def apply_current_year_and_search(self):
        """侧边栏每次打开时：年份对齐系统当前年、按试验日期查全年数据，并刷新表格。"""
        y = str(datetime.now().year)
        idx = self.year_box.findText(y)
        if idx < 0:
            self.year_box.insertItem(0, y)
            idx = 0
        self.year_box.blockSignals(True)
        self.year_box.setCurrentIndex(idx)
        self.year_box.blockSignals(False)
        self.query_mode.setCurrentIndex(0)
        self.search_box.clear()
        self.handle_search()

    def handle_cell_click(self, row, column):
        """处理单元格点击事件，若点击的是文件链接列，则打开文件所在目录"""
        if column == 3:  # 文件链接列
            item = self.table.item(row, column)
            if item is not None:
                file_path = item.data(Qt.UserRole)
                if file_path:
                    import os
                    import sys
                    try:
                        dir_path = os.path.dirname(file_path)
                        if os.path.isdir(dir_path):
                            if sys.platform.startswith('win'):
                                os.startfile(dir_path)
                            else:
                                import subprocess
                                opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
                                subprocess.call([opener, dir_path])
                        else:
                            from PyQt5.QtWidgets import QMessageBox
                            QMessageBox.warning(self, "提示", "文件所在目录不存在。")
                    except Exception as e:
                        # print(f"无法打开目录: {e}")
                        from PyQt5.QtWidgets import QMessageBox
                        QMessageBox.warning(self, "提示", f"无法打开目录：{e}")


    def handle_search(self):
        """执行搜索并刷新表格"""
        mode = self.query_mode.currentText()
        year = self.year_box.currentText()
        keyword = self.search_box.text().strip()

        results = self.query_records(mode, year, keyword)  # 返回 list[tuple]

        self.table.setRowCount(0)

        for row_data in results:
            row_index = self.table.rowCount()
            self.table.insertRow(row_index)
            
            # 添加基本信息列（试验日期、用户、出厂编号）
            for col_index, value in enumerate(row_data[:3]):
                self.table.setItem(row_index, col_index, QTableWidgetItem(str(value) if value else ""))
            
            # 添加文件链接列：使用数据库中的 file_path，点击打开文件所在目录
            file_path = row_data[4] if len(row_data) > 4 else None
            link_item = QTableWidgetItem("打开目录" if file_path else "未生成")
            link_item.setTextAlignment(Qt.AlignCenter)
            if file_path:
                link_item.setForeground(Qt.blue)
                link_item.setData(Qt.UserRole, file_path)
            else:
                link_item.setForeground(Qt.gray)
                link_item.setData(Qt.UserRole, None)
            self.table.setItem(row_index, 3, link_item)
            
            # 添加导入按钮列
            import_btn = QPushButton("导入")
            import_btn.setProperty("data_id", str(row_data[3]))  # 存储数据ID
            import_btn.clicked.connect(self.on_import_clicked)
            # 创建单元格小部件容器
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.addWidget(import_btn)
            btn_layout.setAlignment(Qt.AlignCenter)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row_index, 4, btn_widget)

    def query_records(self, mode, year, keyword):
        if mode == "试验日期":
            result = DataManager.queryByYear(year)
        elif mode == "用户" and len(keyword) != 0:
            result = DataManager.queryByYearAndUser(year, keyword)
        elif mode == "出厂编号" and len(keyword) != 0:
            result = DataManager.queryByYearAndFactoryNum(year, keyword)
        else:
            result = DataManager.queryByYear(year)

        # test_detail SELECT 顺序见 DataManager.TEST_DETAIL_SELECT_COLS:
        # 0 test_id
        # 1 project_name
        # 2 factory_number
        # 3 test_date
        # 4 pipeline_name
        # 5 line_hanger_no
        # 6 spec_model
        # 7 travel_direction
        # 8 working_load_n
        # 9 install_cold_load_n
        # 10 install_cold_pos_mm
        # 11 thread_size_m
        # 12 spring_stiffness
        # 13 tester
        # 14 approver
        # 15 set_load_actual_n
        # 16 load_deviation
        # 17 min_travel_mm
        # 18 min_travel_load_n
        # 19 max_travel_mm
        # 20 max_travel_load_n
        # 21 test_conclusion
        # 22 file_path
        # 返回 [试验日期, 试验人员, 出厂编号, test_id, file_path]
        return [[row[3], row[13], row[2], row[0], row[22]] for row in result]
        
    def on_import_clicked(self):
        """处理导入按钮点击事件"""
        # 获取按钮的属性，得到数据ID
        sender = self.sender()
        data_id = sender.property("data_id")
        
        if data_id:
            try:
                # 从数据库查询该ID的详细数据
                detail_data = DataManager.queryById(int(data_id))
                # 查询该ID的测试数据
                x_list, y_list, highlight = DataManager.queryTestDataByFormId(int(data_id))
                
                # 显示导入成功的提示
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "导入成功", f"已成功导入ID为{data_id}的数据")
                
                # 这里需要将数据传递给chart_widget1
                # 如果能够获取到main_window的引用，可以直接调用chart_widget1的方法
                if self.main_window and hasattr(self.main_window, 'chart_widget1'):
                    # 将数据传递给chart_widget1
                    test_widget = self.main_window.chart_widget1
                    
                    # 填充表单数据
                    if detail_data:
                        mapped = {
                            "工程名称": detail_data[1],
                            "出厂编号": detail_data[2],
                            "试验日期": detail_data[3],
                            "管系名称": detail_data[4],
                            "管线号-支吊点号": detail_data[5],
                            "规格型号": detail_data[6],
                            "位移方向": detail_data[7],
                            "工作载荷": detail_data[8],
                            "安装冷态载荷": detail_data[9],
                            "安装冷态位置": detail_data[10],
                            "螺纹尺寸": detail_data[11],
                            "弹簧刚度": detail_data[12],
                            "试验人员": detail_data[13],
                            "批准人员": detail_data[14],
                            "整定载荷实测值": detail_data[15],
                            "载荷偏差度": detail_data[16],
                            "最小位移": detail_data[17],
                            "最小位移实测载荷": detail_data[18],
                            "最大位移": detail_data[19],
                            "最大位移实测载荷": detail_data[20],
                            "测试结论": detail_data[21],
                        }
                        for k, v in mapped.items():
                            if k not in test_widget.inputs:
                                continue
                            w = test_widget.inputs[k]
                            if v is None:
                                v = ""
                            try:
                                from PyQt5.QtWidgets import QLineEdit, QComboBox, QLabel
                                if isinstance(w, QLineEdit):
                                    w.setText(str(v))
                                elif isinstance(w, QComboBox):
                                    w.setCurrentText(str(v))
                                elif isinstance(w, QLabel):
                                    w.setText(str(v))
                            except Exception:
                                pass

                        # 传入导入数据的文件路径，便于直接打印文件
                        test_widget._existing_file_path = detail_data[22]
                    
                    if (detail_data is not None) and (detail_data[22] is None):
                        test_widget._record_dot_x = x_list
                        test_widget._record_dot_y = y_list
                        test_widget._record_dot_highlight = highlight
                        test_widget.save_high_res_chart()
                        
                    # 更新图表数据
                    if hasattr(test_widget, 'rewrite_chart'):
                        test_widget.rewrite_chart(x_list, y_list, highlight)
                        
                    # 设置当前处理的数据ID，便于后续打印
                    self.main_window.now_handle_data_id = int(data_id)
                    # 导入的是已有数据，禁用测试入库按钮并标记为已入库
                    test_widget.mark_as_saved()
                    # 导入后禁用开始按钮，需点击清空面板后再启用
                    test_widget.wz_zero_btn.setEnabled(False)

            except Exception as e:
                # print(f"导入数据时出错: {e}")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "导入失败", f"导入数据时出错: {str(e)}")
                
    def set_main_window(self, main_window):
        """设置主窗口引用，用于访问test_widget_1"""
        self.main_window = main_window






