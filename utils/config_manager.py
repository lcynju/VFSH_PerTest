"""配置管理：打印机名称、打印文件保存地址、串口端口"""
import os
import json
from datetime import datetime

CONFIG_FILENAME = "app_config.json"
DEFAULT_PRINTER = "Canon iP1188 series"
DEFAULT_SAVE_PATH = ""
DEFAULT_SERIAL_PORT = "COM7"
DEFAULT_OVERLOAD_FACTOR = 2.5

# 配置文件中尚无 test_widget_1_comboboxes 时的回退（与原先界面默认值一致）
DEFAULT_TEST_WIDGET_1_COMBOS = {
    "工程名称": {"items": ["测试工程"], "value": "测试工程"},
    "管线号-支吊点号": {"items": ["测试吊点号"], "value": "测试吊点号"},
    "位移方向": {"items": ["+", "-"], "value": "+"},
    "试验人员": {"items": ["刘云佳", "张三", "李四"], "value": "刘云佳"},
    "批准人员": {"items": ["陈广春", "王五", "赵六"], "value": "陈广春"},
}


def _config_path():
    """配置文件路径（与主程序同目录）"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, CONFIG_FILENAME)


def _default_raw_config():
    return {
        "printer_name": DEFAULT_PRINTER,
        "print_save_path": DEFAULT_SAVE_PATH or os.getcwd(),
        "serial_port": DEFAULT_SERIAL_PORT,
        "overload_factor": DEFAULT_OVERLOAD_FACTOR,
        "combobox_history": {},
        "test_widget_1_comboboxes": {},
    }


def _overload_factor_from_raw(cfg):
    if "overload_factor" in cfg:
        return float(cfg["overload_factor"])
    if "overload_factor_min" in cfg and "overload_factor_max" in cfg:
        return (float(cfg["overload_factor_min"]) + float(cfg["overload_factor_max"])) / 2
    return DEFAULT_OVERLOAD_FACTOR


def _load_raw_config():
    """读取完整 JSON，与默认键合并，保留文件中额外字段。"""
    path = _config_path()
    base = _default_raw_config()
    if not os.path.exists(path):
        return dict(base)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return dict(base)
        merged = dict(base)
        merged.update(data)
        if not isinstance(merged.get("combobox_history"), dict):
            merged["combobox_history"] = {}
        if not isinstance(merged.get("test_widget_1_comboboxes"), dict):
            merged["test_widget_1_comboboxes"] = {}
        return merged
    except Exception:
        return dict(base)


def load_config():
    """加载配置，返回常用字段 dict"""
    cfg = _load_raw_config()
    of = _overload_factor_from_raw(cfg)
    return {
        "printer_name": cfg.get("printer_name", DEFAULT_PRINTER),
        "print_save_path": cfg.get("print_save_path") or os.getcwd(),
        "serial_port": cfg.get("serial_port", DEFAULT_SERIAL_PORT),
        "overload_factor": of,
    }


def save_config(printer_name=None, print_save_path=None, serial_port=None,
                overload_factor=None):
    """保存配置（仅更新传入的字段，保留 test_widget_1_comboboxes 等扩展键）"""
    path = _config_path()
    cfg = _load_raw_config()
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


def get_test_widget_1_combobox(key):
    """读取测试页 combobox：返回 (items 列表, 当前选中/输入文本)。"""
    raw = _load_raw_config()
    tw = raw.get("test_widget_1_comboboxes") or {}
    fb = DEFAULT_TEST_WIDGET_1_COMBOS.get(key, {"items": [], "value": ""})
    entry = tw.get(key)
    if not entry or not isinstance(entry, dict):
        items = list(fb["items"])
        value = (fb.get("value") or "").strip()
        if not value and items:
            value = items[0]
        return items, value
    items = list(entry.get("items") or []) or list(fb["items"])
    value = str(entry.get("value", "") or fb.get("value", "")).strip()
    if not items:
        items = list(fb["items"])
    if value and value not in items:
        items = [value] + list(items)
    elif not value and items:
        value = items[0]
    elif value and value in items and items[0] != value:
        items = [value] + [x for x in items if x != value]
    return items, value


def save_test_widget_1_comboboxes(combo_states):
    """
    将各 combobox 的下拉项与当前值写入 app_config.json。
    当前选中项（本次使用值）排在 items 最前，其余项按原下拉顺序去重跟随，
    下次启动时第一项即为上次刚用过的值。
    combo_states: { key: {"items": [...], "value": "..."} }
    """
    path = _config_path()
    cfg = _load_raw_config()
    tw = cfg.setdefault("test_widget_1_comboboxes", {})
    for key, state in combo_states.items():
        if not isinstance(state, dict):
            continue
        raw_items = state.get("items") or []
        value = str(state.get("value", "")).strip()
        seen = set()
        norm_items = []
        if value:
            norm_items.append(value)
            seen.add(value)
        for x in raw_items:
            s = str(x).strip()
            if s and s not in seen:
                seen.add(s)
                norm_items.append(s)
        if not value and norm_items:
            value = norm_items[0]
        tw[key] = {"items": norm_items, "value": value}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_combobox_history(key):
    """获取某个 combobox 的历史输入列表"""
    cfg = _load_raw_config()
    history = cfg.get("combobox_history", {})
    return history.get(key, []) if isinstance(history, dict) else []


def save_combobox_item(key, value):
    """将 combobox 值追加到历史记录末尾（已存在则移到末尾，保证最后一项是最近使用的）"""
    value = str(value).strip()
    if not value:
        return
    path = _config_path()
    try:
        cfg = _load_raw_config()
        history = cfg.setdefault("combobox_history", {})
        items = list(history.get(key, []))
        if value in items:
            items.remove(value)
        items.append(value)
        history[key] = items
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
