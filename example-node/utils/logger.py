"""
日志工具：控制台 + 文件双输出，按年/月/日自动分目录
"""
import logging
import os
from datetime import datetime


def get_logger(name: str, log_dir: str = "logs", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # 控制台
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    ))
    logger.addHandler(console)

    # 文件：logs/年/月/日.log
    now = datetime.now()
    file_dir = os.path.join(log_dir, str(now.year), f"{now.month:02d}")
    os.makedirs(file_dir, exist_ok=True)
    filepath = os.path.join(file_dir, f"{now.day:02d}.log")

    file_handler = logging.FileHandler(filepath, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(file_handler)

    return logger
