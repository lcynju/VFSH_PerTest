"""配置管理：打印机名称、打印文件保存地址、串口端口"""
import os
import json
from datetime import datetime

CONFIG_FILENAME = "app_config.json"
DEFAULT_PRINTER = "Canon iP1188 series"
DEFAULT_SAVE_PATH = ""
DEFAULT_SERIAL_PORT = "COM7"
DEFAULT_OVERLOAD_FACTOR = 2.5


def _config_path():
    """配置文件路径（与主程序同目录）"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, CONFIG_FILENAME)


def load_config():
    """加载配置，返回 dict"""
    path = _config_path()
    if not os.path.exists(path):
        return {
            "printer_name": DEFAULT_PRINTER,
            "print_save_path": DEFAULT_SAVE_PATH or os.getcwd(),
            "serial_port": DEFAULT_SERIAL_PORT,
            "overload_factor": DEFAULT_OVERLOAD_FACTOR,
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # 兼容旧配置：若只有 overload_factor_min/max，取其平均值
        if "overload_factor" in cfg:
            of = float(cfg["overload_factor"])
        elif "overload_factor_min" in cfg and "overload_factor_max" in cfg:
            of = (float(cfg["overload_factor_min"]) + float(cfg["overload_factor_max"])) / 2
        else:
            of = DEFAULT_OVERLOAD_FACTOR
        return {
            "printer_name": cfg.get("printer_name", DEFAULT_PRINTER),
            "print_save_path": cfg.get("print_save_path") or os.getcwd(),
            "serial_port": cfg.get("serial_port", DEFAULT_SERIAL_PORT),
            "overload_factor": of,
        }
    except Exception:
        return {
            "printer_name": DEFAULT_PRINTER,
            "print_save_path": os.getcwd(),
            "serial_port": DEFAULT_SERIAL_PORT,
            "overload_factor": DEFAULT_OVERLOAD_FACTOR,
        }


def save_config(printer_name=None, print_save_path=None, serial_port=None,
                overload_factor=None):
    """保存配置（仅更新传入的字段）"""
    path = _config_path()
    cfg = load_config()
    if printer_name is not None:
        cfg["printer_name"] = str(printer_name).strip()
    if print_save_path is not None:
        cfg["print_save_path"] = str(print_save_path).strip() or os.getcwd()
    if serial_port is not None:
        cfg["serial_port"] = str(serial_port).strip() or DEFAULT_SERIAL_PORT
    if overload_factor is not None:
        cfg["overload_factor"] = float(overload_factor)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_printer_name():
    return load_config()["printer_name"]


def get_print_save_path():
    p = load_config()["print_save_path"]
    return p if p else os.getcwd()


def get_print_save_dir_for_today():
    """返回今日打印文件保存目录：根目录/年份/月份/，自动创建不存在的目录"""
    root = get_print_save_path()
    now = datetime.now()
    year_dir = str(now.year)
    month_dir = f"{now.month:02d}"
    save_dir = os.path.join(root, year_dir, month_dir)
    os.makedirs(save_dir, exist_ok=True)
    return save_dir


def get_serial_port():
    return load_config()["serial_port"]


def get_overload_factor():
    return load_config()["overload_factor"]


def get_combobox_history(key):
    """获取某个 combobox 的历史输入列表"""
    path = _config_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        history = cfg.get("combobox_history", {})
        return history.get(key, [])
    except Exception:
        return []


def save_combobox_item(key, value):
    """将 combobox 值追加到历史记录末尾（已存在则移到末尾，保证最后一项是最近使用的）"""
    value = str(value).strip()
    if not value:
        return
    path = _config_path()
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        else:
            cfg = {}
        history = cfg.setdefault("combobox_history", {})
        items = history.get(key, [])
        if value in items:
            items.remove(value)
        items.append(value)
        history[key] = items
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
