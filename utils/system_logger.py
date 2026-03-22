"""系统日志：记录到配置选项中的根目录下，按年份分文件，文件名 System_Log_年份.log"""
import logging
import os
from datetime import datetime

_logger_cache = {}
_file_handler_cache = {}


def _get_log_dir():
    """从配置获取日志根目录"""
    try:
        from utils.config_manager import get_print_save_path
        root = get_print_save_path()
        return root if root else os.getcwd()
    except Exception:
        return os.getcwd()


def _get_log_path():
    """返回当前年份的日志文件完整路径"""
    log_dir = _get_log_dir()
    year = datetime.now().year
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, f"System_Log_{year}.log")


def get_logger(name="tension"):
    """获取系统日志 logger，日志写入配置根目录下的 System_Log_年份.log"""
    global _logger_cache, _file_handler_cache
    year = datetime.now().year
    cache_key = f"{name}_{year}"

    if cache_key in _logger_cache:
        return _logger_cache[cache_key]

    logger = logging.getLogger(name if name != "tension" else f"tension_{year}")
    logger.setLevel(logging.DEBUG)

    # 避免重复添加 handler（例如年份切换时可能重复）
    if logger.handlers:
        return logger

    try:
        log_path = _get_log_path()
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        _file_handler_cache[cache_key] = fh
    except Exception:
        # 配置加载失败时使用 NullHandler 避免报错
        logger.addHandler(logging.NullHandler())

    _logger_cache[cache_key] = logger
    return logger
