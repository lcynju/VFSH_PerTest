import json
import sqlite3
from PO.input_data import inputManager

class DataManager:
    DB_FILE = "form_data.db"

    # test_detail: 按 test_widget_1 表格字段存储（列名用英文，避免中文列名带来的SQL引用问题）
    TEST_DETAIL_COLUMNS = [
        ("project_name", "工程名称"),
        ("factory_number", "出厂编号"),
        ("test_date", "试验日期"),
        ("pipeline_name", "管系名称"),
        ("line_hanger_no", "管线号-支吊点号"),
        ("spec_model", "规格型号"),
        ("travel_direction", "位移方向"),
        ("working_load_n", "工作载荷"),
        ("install_cold_load_n", "安装冷态载荷"),
        ("install_cold_pos_mm", "安装冷态位置"),
        ("thread_size_m", "螺纹尺寸"),
        ("spring_stiffness", "弹簧刚度"),
        ("tester", "试验人员"),
        ("approver", "批准人员"),
        ("set_load_actual_n", "整定载荷实测值"),
        ("load_deviation", "载荷偏差度"),
        ("min_travel_mm", "最小位移"),
        ("min_travel_load_n", "最小位移实测载荷"),
        ("max_travel_mm", "最大位移"),
        ("max_travel_load_n", "最大位移实测载荷"),
        ("test_conclusion", "测试结论"),
    ]
    # 固定 SELECT 顺序，供 UI/打印模块按索引取值
    TEST_DETAIL_SELECT_COLS = ["test_id"] + [c for c, _ in TEST_DETAIL_COLUMNS] + ["file_path"]

    @staticmethod
    def queryTestDataByFormId(form_id):
        """查询指定 form_id 的测试数据，返回 (x_list, y_list, highlight)"""
        conn = sqlite3.connect(DataManager.DB_FILE)
        cursor = conn.cursor()
        sql = '''
            SELECT x_json, y_json, highlight_json
            FROM test_points
            WHERE test_id = ?
        '''
        cursor.execute(sql, (form_id,))
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return [], [], []
        try:
            raw_x = json.loads(row[0]) if isinstance(row[0], str) else [row[0]]
            raw_y = json.loads(row[1]) if isinstance(row[1], str) else [row[1]]
            raw_hl = json.loads(row[2]) if len(row) > 2 and row[2] is not None else []

            x_list = [float(v) for v in raw_x]
            y_list = [float(v) for v in raw_y]
            highlight = [bool(v) for v in raw_hl]
        except (json.JSONDecodeError, TypeError, ValueError):
            return [], [], []
        return x_list, y_list, highlight

    def __init__(self):
        self.init_db()


    def init_db(self):
        conn = sqlite3.connect(DataManager.DB_FILE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        detail_cols_sql = ",\n                ".join(
            [f"{col_name} TEXT" for col_name, _ in DataManager.TEST_DETAIL_COLUMNS]
        )

        cursor.execute(
            f'''
            CREATE TABLE IF NOT EXISTS test_detail (
                test_id INTEGER PRIMARY KEY AUTOINCREMENT,
                {detail_cols_sql},
                file_path TEXT
            )
            '''
        )

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS test_points (
                test_id INTEGER PRIMARY KEY,
                x_json TEXT NOT NULL,
                y_json TEXT NOT NULL,
                highlight_json TEXT NOT NULL,
                FOREIGN KEY (test_id) REFERENCES test_detail(test_id) ON DELETE CASCADE
            )
            '''
        )
        conn.commit()
        conn.close()

    @staticmethod
    def queryById(data_id):
        conn = sqlite3.connect(DataManager.DB_FILE)
        cursor = conn.cursor()
        select_cols = ", ".join(DataManager.TEST_DETAIL_SELECT_COLS)
        sql = f'''SELECT {select_cols} FROM test_detail WHERE test_id = ?'''
        cursor.execute(sql, (data_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    @staticmethod
    def save_detail(data: inputManager):
        conn = sqlite3.connect(DataManager.DB_FILE)
        cursor = conn.cursor()

        col_names = [c for c, _ in DataManager.TEST_DETAIL_COLUMNS]
        placeholders = ", ".join(["?"] * len(col_names))
        insert_cols = ", ".join(col_names)
        values = [data.get_value(input_key) for _, input_key in DataManager.TEST_DETAIL_COLUMNS]

        cursor.execute(
            f'''
            INSERT INTO test_detail ({insert_cols})
            VALUES ({placeholders})
            ''',
            tuple(values),
        )

        conn.commit()
        conn.close()
        return cursor.lastrowid

    @staticmethod
    def update_file_path(form_id: int, file_path: str):
        """更新记录的打印文件完整路径"""
        conn = sqlite3.connect(DataManager.DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE test_detail SET file_path = ? WHERE test_id = ?", (file_path, form_id))
        conn.commit()
        conn.close()

    @staticmethod
    def save_test_data(form_id: int, x_list: list, y_list: list, highlight: list):
        """保存测试数据（每次测试的所有点存为一条记录，x/y/highlight 用 JSON 列表存储）"""
        if len(x_list) != len(y_list):
            raise ValueError("x_list 和 y_list 长度不一致")

        conn = sqlite3.connect(DataManager.DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT OR REPLACE INTO test_points (test_id, x_json, y_json, highlight_json)
            VALUES (?, ?, ?, ?)
            ''',
            (
                form_id,
                json.dumps([float(x) for x in x_list], ensure_ascii=False),
                json.dumps([float(y) for y in y_list], ensure_ascii=False),
                json.dumps([bool(h) for h in (highlight or [])], ensure_ascii=False),
            )
        )
        conn.commit()
        conn.close()

    @staticmethod
    def queryByYear(year):
        conn = sqlite3.connect(DataManager.DB_FILE)
        cursor = conn.cursor()
        # 构建SQL(通过年份查找)
        select_cols = ", ".join(DataManager.TEST_DETAIL_SELECT_COLS)
        sql = f'''
               SELECT {select_cols}
               FROM test_detail
               WHERE test_date LIKE ?
               ORDER BY test_id DESC
           '''
        params = [f"{year}%"]
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        return results

    @staticmethod
    def queryByYearAndUser(year, user):
        conn = sqlite3.connect(DataManager.DB_FILE)
        cursor = conn.cursor()
        # 构建SQL(通过年份查找)
        select_cols = ", ".join(DataManager.TEST_DETAIL_SELECT_COLS)
        sql = f'''
               SELECT {select_cols}
               FROM test_detail
               WHERE test_date LIKE ?
               AND tester LIKE ?
               ORDER BY test_id DESC
           '''
        params = [f"{year}%", f"%{user}%"]
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        return results

    @staticmethod
    def queryByYearAndFactoryNum(year, number):
        conn = sqlite3.connect(DataManager.DB_FILE)
        # print(number == None)
        cursor = conn.cursor()
        # 构建SQL(通过年份查找)
        select_cols = ", ".join(DataManager.TEST_DETAIL_SELECT_COLS)
        sql = f'''
               SELECT {select_cols}
               FROM test_detail
               WHERE test_date LIKE ?
               AND factory_number LIKE ?
               ORDER BY test_id DESC
           '''
        params = [f"{year}%", f"%{number}%"]
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        return results






