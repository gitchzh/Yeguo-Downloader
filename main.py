#!/usr/bin/env python3
"""
Yeguo-Downloader 主程序入口

这是一个视频下载器应用程序的主入口文件。
支持从各种视频平台下载视频，提供图形用户界面。

作者: mrchzh
邮箱: gmrchzh@gmail.com
版本: 1.5.9
"""

import sys
import os

# 添加src目录到Python路径，以便导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PyQt5.QtWidgets import QApplication
from src.ui.main_window import VideoDownloader
from src.utils.logger import logger


def main() -> None:
    """
    主程序入口函数
    
    初始化Qt应用程序，创建主窗口并启动事件循环。
    """
    try:
        # 创建Qt应用程序实例
        app = QApplication(sys.argv)
        
        # 设置应用程序信息
        app.setApplicationName("Yeguo-Downloader")
        app.setApplicationVersion("1.5.9")
        app.setOrganizationName("mrchzh")
        
        # 创建主窗口
        window = VideoDownloader()
        window.show()
        
        # 启动应用程序事件循环
        logger.info("应用程序启动成功")
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"应用程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
