


class inputManager():
    # TODO: 优化一下这个数据结构
    def __init__(self):
        self.fields = {}  # 用于存储所有控件
        self.show_keys = ["试验时间", "用户", "吊点代号", "出厂编号", "型号规格", "工作载荷", "位移方向", "总位移",
                     "工作位移", "操作员", "检验员", "位移起始点值", "位移终止点值", "实测位移值", "超载试验值",
                     "起始-终止时间", "超载试验保持时间", "恒定度", "锁定位置", "载荷偏差度", "测试结果"]
        self.db_keys = ["test_time", "user", "吊点代号", "出厂编号", "型号规格", "工作载荷", "位移方向", "总位移",
                   "工作位移", "操作员", "检验员", "位移起始点值", "位移终止点值", "实测位移值", "超载试验值",
                   "起始-终止时间", "超载试验保持时间", "恒定度", "锁定位置", "载荷偏差度", "测试结果"]
        self.keys_dict = dict(zip(self.db_keys, self.show_keys))
        for key in self.show_keys:
            self.fields[key] = None
    def set_value(self, key, value):
        self.fields[key] = value
    def get_value(self, key):
        if key in self.fields:
            return self.fields[key]
        elif key in self.db_keys:
            return self.fields[self.keys_dict[key]]