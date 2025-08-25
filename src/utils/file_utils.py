"""
文件工具模块

包含文件操作相关的工具函数。
"""

import os
import re
import sys
import webbrowser
from typing import Optional
from PyQt5.QtWidgets import QMessageBox

from ..core.config import Config
from .logger import logger


def sanitize_filename(filename: str, save_path: str) -> str:
    """
    清理文件名，确保合法性
    
    移除文件名中的非法字符，限制长度，并处理重复文件名。
    
    Args:
        filename: 原始文件名
        save_path: 保存路径
        
    Returns:
        str: 清理后的合法文件名
    """
    # 移除Windows文件系统不允许的字符
    filename = re.sub(r'[<>:"/\\|?*]', "", filename)
    
    # 限制文件名长度
    filename = filename[:Config.MAX_FILENAME_LENGTH]
    
    # 处理重复文件名
    base, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    
    # 如果文件已存在，添加数字后缀
    while os.path.exists(os.path.join(save_path, new_filename)):
        new_filename = f"{base}_{counter}{ext}"
        counter += 1
        
    return new_filename


def format_size(bytes_size: Optional[int]) -> str:
    """
    格式化文件大小显示
    
    将字节数转换为人类可读的文件大小格式（B、KB、MB、GB）。
    
    Args:
        bytes_size: 文件大小（字节）
        
    Returns:
        str: 格式化后的文件大小字符串
    """
    if not bytes_size or bytes_size <= 0:
        return "未知"
        
    # 按1024进制转换单位
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
        
    return f"{bytes_size:.2f} GB"


def get_ffmpeg_path(save_path: str) -> Optional[str]:
    """
    获取 FFmpeg 可执行文件路径
    
    按优先级查找FFmpeg：
    1. 打包后的可执行文件
    2. resources目录中的FFmpeg
    3. 保存路径中的FFmpeg
    
    Args:
        save_path: 保存路径
        
    Returns:
        Optional[str]: FFmpeg路径，如果未找到则返回None
    """
    # 检查是否为打包后的可执行文件
    if getattr(sys, "frozen", False):
        ffmpeg_exe = os.path.join(sys._MEIPASS, "ffmpeg.exe")
        if os.path.exists(ffmpeg_exe):
            return ffmpeg_exe
    
    # 检查resources目录中是否有FFmpeg
    resources_ffmpeg = os.path.join("resources", "ffmpeg.exe")
    if os.path.exists(resources_ffmpeg):
        return resources_ffmpeg
            
    # 检查保存路径中是否有FFmpeg
    ffmpeg_path = os.path.join(save_path, "ffmpeg.exe")
    if os.path.exists(ffmpeg_path):
        return ffmpeg_path
        
    logger.warning("FFmpeg 未找到")
    return None


def check_ffmpeg(ffmpeg_path: Optional[str], parent_widget=None) -> bool:
    """
    检查 FFmpeg 是否可用
    
    如果FFmpeg未找到，提示用户并提供下载链接。
    
    Args:
        ffmpeg_path: FFmpeg路径
        parent_widget: 父窗口部件
        
    Returns:
        bool: FFmpeg是否可用
    """
    if not ffmpeg_path:
        msg_box = QMessageBox()
        msg_box.setWindowTitle("FFmpeg 未找到")
        msg_box.setText("FFmpeg 未找到，是否打开官网下载？\n请将 ffmpeg.exe 放入保存路径后重试。")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        # 设置按钮中文文本
        msg_box.button(QMessageBox.Yes).setText("是")
        msg_box.button(QMessageBox.No).setText("否")
        reply = msg_box.exec_()
        if reply == QMessageBox.Yes:
            webbrowser.open("https://ffmpeg.org/download.html")
        return False
    return True
