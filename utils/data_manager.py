import json
import sqlite3
from PO.input_data import inputManager
from utils.system_logger import get_logger

class DataManager:
    @staticmethod
    def queryTestDataByFormId(form_id):
        """查询指定 form_id 的测试数据，返回 (x_list, y_list, highlight, highlight_side_right)"""
        conn = sqlite3.connect("form_data.db")
        cursor = conn.cursor()
        sql = '''SELECT displacement, force, highlight, highlight_side_right FROM test_data WHERE form_id = ?'''
        cursor.execute(sql, (form_id,))
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return [], [], [], []
        try:
            raw_y = json.loads(row[0]) if isinstance(row[0], str) else [row[0]]
            raw_x = json.loads(row[1]) if isinstance(row[1], str) else [row[1]]
            raw_hl = json.loads(row[2]) if len(row) > 2 and row[2] is not None else []
            raw_side = json.loads(row[3]) if len(row) > 3 and row[3] is not None else []

            x_list = [float(v) for v in raw_x]
            y_list = [float(v) for v in raw_y]
            highlight = [bool(v) for v in raw_hl]
            highlight_side_right = [bool(v) for v in raw_side]
        except (json.JSONDecodeError, TypeError, ValueError):
            return [], [], [], []
        return x_list, y_list, highlight, highlight_side_right

    def __init__(self):
        self.init_db()


    def init_db(self):
        conn = sqlite3.connect("form_data.db")
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_detail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_time TEXT,
                user TEXT,
                吊点代号 TEXT,
                出厂编号 TEXT,
                型号规格 TEXT,
                工作荷载 TEXT,
                位移方向 TEXT,
                总位移 TEXT,
                工作位移 TEXT,
                操作员 TEXT,
                检验员 TEXT,
                位移起始点值 TEXT,
                位移终止点值 TEXT,
                实测位移值 TEXT,
                超载试验值 TEXT,
                起止时间 TEXT,
                保持时间 TEXT,
                恒定度 TEXT,
                锁定位置 TEXT,
                载荷偏差度 TEXT,
                测试结果 TEXT,
                file_path TEXT
            )
        ''')

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS test_data (
                test_id INTEGER PRIMARY KEY AUTOINCREMENT,
                form_id INTEGER UNIQUE,
                displacement TEXT,
                force TEXT,
                highlight TEXT,
                highlight_side_right TEXT,
                FOREIGN KEY(form_id) REFERENCES test_detail(id) ON DELETE CASCADE
            )
            '''
        )
        conn.commit()
        conn.close()

    @staticmethod
    def queryById(data_id):
        conn = sqlite3.connect("form_data.db")
        cursor = conn.cursor()
        sql = '''SELECT * FROM test_detail WHERE id = ?'''
        cursor.execute(sql, (data_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    @staticmethod
    def save_detail(data: inputManager):
        conn = sqlite3.connect("form_data.db")
        cursor = conn.cursor()
        # print("first get and save", data)

        cursor.execute('''
            INSERT INTO test_detail (
                test_time, user, 吊点代号, 出厂编号, 型号规格, 工作荷载, 位移方向,
                总位移, 工作位移, 操作员, 检验员,
                位移起始点值, 位移终止点值, 实测位移值,
                超载试验值, 起止时间, 保持时间,
                恒定度, 锁定位置, 载荷偏差度, 测试结果
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get_value("test_time"),
            data.get_value("user"),
            data.get_value("吊点代号"),
            data.get_value("出厂编号"),
            data.get_value("型号规格"),
            data.get_value("工作载荷"),
            data.get_value("位移方向"),
            data.get_value("总位移"),
            data.get_value("工作位移"),
            data.get_value("操作员"),
            data.get_value("检验员"),
            data.get_value("位移起始点值"),
            data.get_value("位移终止点值"),
            data.get_value("实测位移值"),
            data.get_value("超载试验值"),
            data.get_value("起始-终止时间"),
            data.get_value("超载试验保持时间"),
            data.get_value("恒定度"),
            data.get_value("锁定位置"),
            data.get_value("载荷偏差度"),
            data.get_value("测试结果")
        ))

        conn.commit()
        conn.close()
        return cursor.lastrowid

    @staticmethod
    def update_file_path(form_id: int, file_path: str):
        """更新记录的打印文件完整路径"""
        conn = sqlite3.connect("form_data.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE test_detail SET file_path = ? WHERE id = ?", (file_path, form_id))
        conn.commit()
        conn.close()

    @staticmethod
    def save_test_data(form_id: int, x_list: list, y_list: list, highlight: list, highlight_side_right: list):
        """保存测试数据，displacement/force 以 JSON 列表形式存储"""
        if len(x_list) != len(y_list):
            raise ValueError("x_list 和 y_list 长度不一致")

        conn = sqlite3.connect("form_data.db")
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT OR REPLACE INTO test_data (form_id, displacement, force, highlight, highlight_side_right)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (form_id, json.dumps([float(y) for y in y_list]), json.dumps([float(x) for x in x_list]), json.dumps([bool(h) for h in highlight]), json.dumps([bool(sr) for sr in highlight_side_right]))
        )
        conn.commit()
        conn.close()

    @staticmethod
    def queryByYear(year):
        conn = sqlite3.connect("form_data.db")
        cursor = conn.cursor()
        # 构建SQL(通过年份查找)
        sql = f'''
               SELECT *
               FROM test_detail
               WHERE test_time LIKE ?
           '''
        params = [f"{year}%"]
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        return results

    @staticmethod
    def queryByYearAndUser(year, user):
        conn = sqlite3.connect("form_data.db")
        cursor = conn.cursor()
        # 构建SQL(通过年份查找)
        sql = f'''
               SELECT *
               FROM test_detail
               WHERE test_time LIKE ?
               AND user LIKE ?
           '''
        params = [f"{year}%", f"{user}%"]
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        return results

    @staticmethod
    def queryByYearAndFactoryNum(year, number):
        conn = sqlite3.connect("form_data.db")
        # print(number == None)
        cursor = conn.cursor()
        # 构建SQL(通过年份查找)
        sql = f'''
               SELECT *
               FROM test_detail
               WHERE test_time LIKE ?
               AND 出厂编号 LIKE ?
           '''
        params = [f"{year}%", f"{number}%"]
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        return results






