"""
日志工具模块

包含日志记录相关的工具类和函数。
"""

import logging
import os
from datetime import datetime
from PyQt5.QtCore import pyqtSignal

def setup_logger():
    """设置日志记录器"""
    # 创建日志目录
    log_dir = os.getcwd()
    log_file = os.path.join(log_dir, "app.log")
    
    # 配置日志格式
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 创建文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加新的处理器
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

# 初始化日志系统
setup_logger()
logger = logging.getLogger("VideoDownloader")


class DebugLogger:
    """
    yt-dlp 日志记录器适配器
    
    将 yt-dlp 的日志输出转换为 PyQt5 信号，实现日志信息在界面上的实时显示。
    支持 debug、warning、error 三种日志级别。
    """
    
    def __init__(self, signal: pyqtSignal):
        """
        初始化日志记录器
        
        Args:
            signal: PyQt5 信号对象，用于向界面发送日志信息
        """
        self.signal = signal

    def debug(self, msg: str) -> None:
        """
        发送调试级别日志
        
        Args:
            msg: 调试信息内容
        """
        self.signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def warning(self, msg: str) -> None:
        """
        发送警告级别日志
        
        Args:
            msg: 警告信息内容
        """
        self.signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] [警告] {msg}")

    def error(self, msg: str) -> None:
        """
        发送错误级别日志
        
        Args:
            msg: 错误信息内容
        """
        self.signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] [错误] {msg}")
