from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QGroupBox
from PyQt5.QtCore import Qt




class DataDisplayWidget(QGroupBox):
    def __init__(self):
        super().__init__("实时数据监测")
        self.data_labels = []
        self.label_mm = None
        self.label_kg = None
        self.label_N = None
        self.init_ui()

    def init_ui(self):
        self.setLayout(QHBoxLayout())
        self.layout().setSpacing(20)
        self.layout().setContentsMargins(15, 15, 15, 15)

        # 初始化三个数据标签

        self.label_mm = QLabel("数据mm")
        self.label_mm.setAlignment(Qt.AlignCenter)
        self.label_mm.setMinimumWidth(180)
        self.label_mm.setMinimumHeight(60)
        self.layout().addWidget(self.label_mm)
        self.data_labels.append(self.label_mm)


        self.label_kg = QLabel("数据kg")
        self.label_kg.setAlignment(Qt.AlignCenter)
        self.label_kg.setMinimumWidth(180)
        self.label_kg.setMinimumHeight(60)
        self.layout().addWidget(self.label_kg)
        self.data_labels.append(self.label_kg)


        self.label_N = QLabel("数据N")
        self.label_N.setAlignment(Qt.AlignCenter)
        self.label_N.setMinimumWidth(180)
        self.label_N.setMinimumHeight(60)
        self.layout().addWidget(self.label_N)
        self.data_labels.append(self.label_N)


        # 设置初始数据
        self.update_data([0.0, 0.0, 0.0])

    def update_data(self, values):
        """更新数据显示"""
        # TODO：mm的第一个参数减一下初始位置
        
        self.label_mm.setText(f"{values[1]:.2f} | {values[2]:.2f}")
        self.label_kg.setText(f"{values[0]:.2f}")
        self.label_N.setText(f"{values[0] * 9.8:.2f}")
