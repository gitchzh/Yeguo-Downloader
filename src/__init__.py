"""
Yeguo-Downloader - 视频下载器应用程序

一个基于 PyQt5 和 yt-dlp 的图形界面工具，用于从 YouTube 和 Bilibili 下载视频。
支持多线程下载、批量处理、格式选择等功能。

作者: mrchzh
邮箱: gmrchzh@gmail.com
开发日期: 2025年8月25日
版本号: 1.5.9
"""

__version__ = "1.5.9"
__author__ = "mrchzh"
__email__ = "gmrchzh@gmail.com"

from .core.config import Config
from .ui.main_window import VideoDownloader
from .workers.parse_worker import ParseWorker
from .workers.download_worker import DownloadWorker

__all__ = [
    "Config",
    "VideoDownloader", 
    "ParseWorker",
    "DownloadWorker",
    "__version__",
    "__author__",
    "__email__"
]
