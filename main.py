#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频下载器应用程序

作者: mrchzh@outlook.com
开发日期: 2025-03-02
版本号: 1.5.9
用途: 一个基于 PyQt5 和 yt_dlp 的图形界面工具，用于从 YouTube 和 Bilibili 下载视频、音频或字幕。
"""

import sys
import os
import re
import webbrowser
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import OrderedDict, deque
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QFileDialog, QProgressBar, QTextEdit, QMenu, QDialog
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings, QUrl
from PyQt5.QtGui import QIcon, QDesktopServices
import yt_dlp

# 配置类
class Config:
    """应用程序全局配置"""
    MAX_CONCURRENT_DOWNLOADS = 2
    CACHE_LIMIT = 10
    DEFAULT_SPEED_LIMIT: Optional[int] = None  # KB/s
    APP_VERSION = "1.5.9"
    MAX_FILENAME_LENGTH = 200

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("VideoDownloader")

class DebugLogger:
    """yt_dlp 日志记录器"""
    def __init__(self, signal: pyqtSignal):
        self.signal = signal

    def debug(self, msg: str) -> None:
        self.signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def warning(self, msg: str) -> None:
        self.signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] [警告] {msg}")

    def error(self, msg: str) -> None:
        self.signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] [错误] {msg}")

class ParseWorker(QThread):
    """视频解析工作线程"""
    log_signal = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self) -> None:
        try:
            ydl_opts = {
                "quiet": False,
                "no_warnings": False,
                "logger": DebugLogger(self.log_signal),
                "format_sort": ["+size"],
                "merge_output_format": "mp4",
                "format": "bestvideo+bestaudio/best[ext=mp4]/bestaudio[ext=m4a]/bestaudio[ext=mp3]",
                "listsubtitles": True,
                "subtitleslangs": ["all"],
                "writesubtitles": True,
                "extract_flat": False,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                if info is None:
                    raise ValueError("无法提取视频信息")
                if "entries" in info:
                    logger.info(f"检测到合集，共有 {len(info['entries'])} 个条目")
                    for entry in info["entries"]:
                        if entry:
                            if "formats" not in entry or not entry["formats"]:
                                entry["formats"] = info.get("formats", [])
                            self.finished.emit(entry)
                else:
                    self.finished.emit(info)
        except Exception as e:
            error_msg = f"解析 {self.url} 失败: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)

class DownloadWorker(QThread):
    """视频下载工作线程"""
    progress_signal = pyqtSignal(dict)
    log_signal = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    class DownloadCancelled(Exception):
        pass

    class DownloadPaused(Exception):
        pass

    def __init__(self, url: str, ydl_opts: Dict):
        super().__init__()
        self.url = url
        self.ydl_opts = ydl_opts
        self._is_cancelled = False
        self._is_paused = False
        self.last_filename: Optional[str] = None

    def cancel(self) -> None:
        self._is_cancelled = True

    def pause(self) -> None:
        self._is_paused = True

    def resume(self) -> None:
        self._is_paused = False

    def progress_hook(self, d: Dict) -> None:
        if self._is_cancelled:
            raise self.DownloadCancelled("下载已取消")
        if self._is_paused:
            raise self.DownloadPaused("下载已暂停")
        if d["status"] == "finished":
            self.last_filename = d.get("filename", "")
        self.progress_signal.emit(d)

    def run(self) -> None:
        try:
            self.ydl_opts["logger"] = DebugLogger(self.log_signal)
            self.ydl_opts["progress_hooks"] = [self.progress_hook]
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                while True:
                    try:
                        if self._is_cancelled:
                            break
                        if self._is_paused:
                            self.msleep(500)
                            continue
                        ydl.download([self.url])
                        break
                    except self.DownloadPaused:
                        self.log_signal.emit("下载暂停...")
                        self.msleep(500)
                        continue
                    except self.DownloadCancelled:
                        self.log_signal.emit("下载已取消")
                        break
            if not self._is_cancelled:
                self.finished.emit(self.last_filename or "")
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))

class VideoDownloader(QMainWindow):
    """主窗口类"""
    def __init__(self):
        super().__init__()
        self.save_path: str = os.getcwd()
        self.parse_cache: OrderedDict = OrderedDict()
        self.formats: List[Dict] = []
        self.download_progress: Dict[str, Tuple[float, str]] = {}
        self.is_downloading: bool = False
        self.download_workers: List[DownloadWorker] = []
        self.parse_workers: List[ParseWorker] = []
        self.download_queue: deque = deque()
        self.active_downloads: int = 0
        self.total_urls: int = 0
        self.parsed_count: int = 0
        self.ffmpeg_path: Optional[str] = self.get_ffmpeg_path()
        self.settings = QSettings("MyCompany", "VideoDownloader")

        self.init_ui()
        self.load_settings()

        icon_path = (
            os.path.join(os.path.dirname(__file__), "app_icon.ico")
            if not getattr(sys, "frozen", False)
            else os.path.join(sys._MEIPASS, "app_icon.ico")
        )
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            logger.warning(f"图标文件未找到: {icon_path}")

    def init_ui(self) -> None:
        """初始化用户界面"""
        self.setWindowTitle(f"椰果视频下载器-v{Config.APP_VERSION} - 就绪")
        self.setGeometry(100, 100, 600, 600)

        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout()

        # 输入布局
        input_layout = QHBoxLayout()
        self.url_input = QTextEdit(self)
        self.url_input.setPlaceholderText("请输入YouTube或B站视频链接，每行一个")
        self.url_input.setFixedHeight(60)
        input_layout.addWidget(QLabel("视频链接:"))
        input_layout.addWidget(self.url_input)
        self.parse_button = QPushButton("解析", self)
        self.parse_button.clicked.connect(self.parse_video)
        self.parse_button.setFixedSize(80, 30)
        input_layout.addWidget(self.parse_button)
        layout.addLayout(input_layout)

        # 保存路径布局
        path_layout = QHBoxLayout()
        self.path_label = QLabel(f"保存路径: {self.save_path}")
        path_layout.addWidget(self.path_label)
        self.path_button = QPushButton("选择路径", self)
        self.path_button.clicked.connect(self.choose_save_path)
        self.path_button.setFixedSize(80, 30)
        path_layout.addWidget(self.path_button)
        layout.addLayout(path_layout)

        # 速度限制布局
        speed_layout = QHBoxLayout()
        self.speed_limit_input = QLineEdit(self)
        self.speed_limit_input.setPlaceholderText("下载速度限制 (KB/s，留空为无限制)")
        self.speed_limit_input.setFixedWidth(200)
        speed_layout.addWidget(QLabel("速度限制:"))
        speed_layout.addWidget(self.speed_limit_input)
        layout.addLayout(speed_layout)

        # 格式树
        self.format_tree = QTreeWidget(self)
        self.format_tree.setHeaderLabels(["选择", "文件名称", "文件类型", "分辨率/语言", "文件大小"])
        self.format_tree.itemDoubleClicked.connect(self.toggle_checkbox)
        self.format_tree.setColumnWidth(0, 50)
        self.format_tree.setColumnWidth(1, 250)
        self.format_tree.setColumnWidth(4, 120)
        self.format_tree.setAlternatingRowColors(True)
        self.format_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.format_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.format_tree.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.format_tree, stretch=3)

        # 进度布局
        self.progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("就绪", self)
        self.status_label.setVisible(False)
        self.progress_layout.addWidget(self.status_label)
        layout.addLayout(self.progress_layout)

        # 按钮布局
        button_layout = QHBoxLayout()
        self.download_button = QPushButton("下载选中项", self)
        self.download_button.clicked.connect(self.download_selected)
        self.download_button.setEnabled(False)
        self.default_style = self.download_button.styleSheet()
        button_layout.addWidget(self.download_button)
        self.pause_button = QPushButton("暂停下载", self)
        self.pause_button.clicked.connect(self.pause_downloads)
        self.pause_button.setEnabled(False)
        button_layout.addWidget(self.pause_button)
        self.cancel_button = QPushButton("取消下载", self)
        self.cancel_button.clicked.connect(self.cancel_downloads)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        # 下载输出
        self.download_output = QTextEdit(self)
        self.download_output.setReadOnly(True)
        self.download_output.setVisible(False)
        layout.addWidget(self.download_output, stretch=2)

        widget.setLayout(layout)

        self.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; border-radius: 5px; padding: 5px; }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
            QTreeWidget { border: 1px solid #ddd; border-radius: 4px; background-color: #f9f9f9; }
            QProgressBar { border: 1px solid grey; border-radius: 5px; text-align: center; }
            QProgressBar::chunk { background-color: #2196F3; width: 20px; }
            QLineEdit, QTextEdit { border: 1px solid #ccc; border-radius: 4px; padding: 2px; }
        """)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_download_progress)
        self.timer.start(500)

    def load_settings(self) -> None:
        """加载保存的设置"""
        self.save_path = self.settings.value("save_path", os.getcwd())
        self.path_label.setText(f"保存路径: {self.save_path}")

    def choose_save_path(self) -> None:
        """选择保存路径"""
        folder = QFileDialog.getExistingDirectory(self, "选择保存路径", self.save_path)
        if folder:
            self.save_path = folder
            self.path_label.setText(f"保存路径: {self.save_path}")

    def sanitize_filename(self, filename: str) -> str:
        """清理文件名，确保合法性"""
        filename = re.sub(r'[<>:"/\\|?*]', "", filename)
        filename = filename[:Config.MAX_FILENAME_LENGTH]
        base, ext = os.path.splitext(filename)
        counter = 1
        new_filename = filename
        while os.path.exists(os.path.join(self.save_path, new_filename)):
            new_filename = f"{base}_{counter}{ext}"
            counter += 1
        return new_filename

    def format_size(self, bytes_size: Optional[int]) -> str:
        """格式化文件大小"""
        if not bytes_size or bytes_size <= 0:
            return "未知"
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_size < 1024:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.2f} GB"

    def get_ffmpeg_path(self) -> Optional[str]:
        """获取 FFmpeg 路径"""
        if getattr(sys, "frozen", False):
            ffmpeg_exe = os.path.join(sys._MEIPASS, "ffmpeg.exe")
            if os.path.exists(ffmpeg_exe):
                return ffmpeg_exe
        ffmpeg_path = os.path.join(self.save_path, "ffmpeg.exe")
        if os.path.exists(ffmpeg_path):
            return ffmpeg_path
        logger.warning("FFmpeg 未找到")
        return None

    def check_ffmpeg(self) -> bool:
        """检查 FFmpeg 是否可用"""
        if not self.ffmpeg_path:
            reply = QMessageBox.question(
                self, "FFmpeg 未找到",
                "FFmpeg 未找到，是否打开官网下载？\n请将 ffmpeg.exe 放入保存路径后重试。",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                webbrowser.open("https://ffmpeg.org/download.html")
            return False
        return True

    def validate_url(self, url: str) -> bool:
        """验证 URL 是否有效"""
        return bool(re.match(r"^https?://.*", url))

    def toggle_checkbox(self, item: QTreeWidgetItem, column: int) -> None:
        """双击切换复选框状态"""
        if item and column == 0:
            current_state = item.checkState(0)
            new_state = Qt.Checked if current_state == Qt.Unchecked else Qt.Unchecked
            item.setCheckState(0, new_state)
            self.on_item_changed(item, 0)

    def parse_video(self) -> None:
        """解析视频链接"""
        urls = [url.strip() for url in self.url_input.toPlainText().split("\n") if url.strip()]
        if not urls:
            QMessageBox.warning(self, "错误", "请输入至少一个有效的视频链接！")
            return

        invalid_urls = [url for url in urls if not self.validate_url(url)]
        if invalid_urls:
            QMessageBox.warning(self, "错误", f"以下链接格式无效:\n" + "\n".join(invalid_urls))
            return

        self.format_tree.clear()
        self.formats = []
        self.download_button.setEnabled(False)
        self.download_output.clear()
        self.download_output.setVisible(True)
        logger.info("开始解析视频...")
        self.download_output.append("开始解析视频...")

        self.parse_button.setEnabled(False)
        self.parse_workers = []
        self.total_urls = len(urls)
        self.parsed_count = 0
        for url in urls:
            worker = ParseWorker(url)
            worker.log_signal.connect(self.download_output.append)
            worker.finished.connect(lambda info, u=url: self.cache_and_finish(info, u))
            worker.error.connect(self.on_parse_error)
            worker.start()
            self.parse_workers.append(worker)

    def cache_and_finish(self, info: Dict, url: str) -> None:
        """缓存解析结果并完成解析"""
        try:
            self.parse_cache[info.get("webpage_url", url)] = info
            if len(self.parse_cache) > Config.CACHE_LIMIT:
                self.parse_cache.popitem(last=False)

            if not hasattr(self, "video_root"):
                self.video_root, self.audio_root, self.subtitle_root = self.on_parse_finished(info)
            else:
                self.on_parse_finished(info, self.video_root, self.audio_root, self.subtitle_root)

            self.parsed_count += 1
            if self.parsed_count == self.total_urls and all(not w.isRunning() for w in self.parse_workers):
                self.finalize_parse()
                if hasattr(self, "video_root"):
                    del self.video_root
                if hasattr(self, "audio_root"):
                    del self.audio_root
                if hasattr(self, "subtitle_root"):
                    del self.subtitle_root
        except Exception as e:
            logger.error(f"缓存解析结果失败: {str(e)}")
            self.download_output.append(f"错误: 缓存解析结果失败: {str(e)}")
            self.parse_button.setEnabled(True)

    def finalize_parse(self) -> None:
        """完成解析并更新 UI"""
        if self.formats:
            self.download_button.setEnabled(True)
            logger.info("所有视频解析完成")
            self.download_output.append("所有视频解析完成")
            QMessageBox.information(self, "成功", "视频解析完成，请选择下载格式")
        else:
            logger.warning("未找到任何可用格式")
            self.download_output.append("未找到任何可用格式")
            QMessageBox.warning(self, "错误", "未找到可用格式！")
        self.parse_button.setEnabled(True)

    def get_resolution(self, f: Dict) -> str:
        """从格式信息中提取分辨率"""
        resolution = f.get("resolution", "")
        if resolution and resolution != "audio only" and "x" in resolution:
            return resolution
        width = f.get("width")
        height = f.get("height")
        if width and height:
            return f"{width}x{height}"
        elif height:
            return f"{height}p"
        format_note = f.get("format_note", "")
        if format_note and format_note != "unknown":
            return format_note
        format_str = f.get("format", "")
        if "x" in format_str:
            match = re.search(r"(\d+)x(\d+)", format_str)
            if match:
                return f"{match.group(1)}x{match.group(2)}"
        return "未知"

    def on_parse_finished(
        self,
        info: Dict,
        video_root: Optional[QTreeWidgetItem] = None,
        audio_root: Optional[QTreeWidgetItem] = None,
        subtitle_root: Optional[QTreeWidgetItem] = None
    ) -> Tuple[QTreeWidgetItem, QTreeWidgetItem, QTreeWidgetItem]:
        """处理解析完成的数据"""
        video_title = info.get("title", "未知标题")
        video_id = info.get("id", "unknown")
        audio_format = None
        audio_filesize = 0
        video_formats: Dict[str, Dict] = {}

        match = re.search(r"(p\d+)\s*(.+?)(?:_\w+)?$", video_title)
        if match:
            part_number, part_title = match.group(1), match.group(2).strip()
            formatted_title = f"{part_number} {part_title}"
        else:
            formatted_title = video_title
            if f"_{video_id}" in formatted_title:
                formatted_title = formatted_title.replace(f"_{video_id}", "")
            formatted_title = f"[{formatted_title}]"

        if not video_root:
            video_root = QTreeWidgetItem(self.format_tree)
            video_root.setText(1, "视频")
            video_root.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            video_root.setCheckState(0, Qt.Unchecked)
            video_root.setExpanded(True)

        if not audio_root:
            audio_root = QTreeWidgetItem(self.format_tree)
            audio_root.setText(1, "音频")
            audio_root.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            audio_root.setCheckState(0, Qt.Unchecked)
            audio_root.setExpanded(True)

        if not subtitle_root:
            subtitle_root = QTreeWidgetItem(self.format_tree)
            subtitle_root.setText(1, "字幕")
            subtitle_root.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            subtitle_root.setCheckState(0, Qt.Unchecked)
            subtitle_root.setExpanded(True)

            timed_subtitle_group = QTreeWidgetItem(subtitle_root)
            timed_subtitle_group.setText(1, "带时间戳")
            timed_subtitle_group.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            timed_subtitle_group.setCheckState(0, Qt.Unchecked)
            timed_subtitle_group.setExpanded(True)

            no_timed_subtitle_group = QTreeWidgetItem(subtitle_root)
            no_timed_subtitle_group.setText(1, "不带时间戳")
            no_timed_subtitle_group.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            no_timed_subtitle_group.setCheckState(0, Qt.Unchecked)
            no_timed_subtitle_group.setExpanded(True)
        else:
            timed_subtitle_group = None
            no_timed_subtitle_group = None
            for i in range(subtitle_root.childCount()):
                child = subtitle_root.child(i)
                if child.text(1) == "带时间戳":
                    timed_subtitle_group = child
                elif child.text(1) == "不带时间戳":
                    no_timed_subtitle_group = child

        formats = info.get("formats", [])
        logger.info(f"解析条目 '{video_title}'，共有 {len(formats)} 个格式")

        for f in formats:
            format_id = f.get("format_id")
            resolution = self.get_resolution(f)
            ext = f.get("ext", "")
            acodec = f.get("acodec", "none")
            filesize = f.get("filesize") or f.get("filesize_approx")
            vbr = f.get("vbr", 0)

            if not filesize:
                duration = info.get("duration", 0)
                abr = f.get("abr", 0)
                total_br = (abr or 0) + (vbr or 0)
                if duration and total_br:
                    filesize = (total_br * duration * 1000) / 8

            logger.debug(f"Format ID: {format_id}, Resolution: {resolution}, Ext: {ext}, Acodec: {acodec}")

            if "audio only" in f.get("format", "") and ext in ["m4a", "mp3"] and not audio_format:
                audio_format = format_id
                audio_filesize = filesize if filesize else 0
                filename = self.sanitize_filename(formatted_title)
                audio_item = QTreeWidgetItem(audio_root)
                self._add_tree_item(audio_item, filename, "mp3", "", audio_filesize)
                self.formats.append({
                    "video_id": video_id,
                    "format_id": format_id,
                    "description": f"{filename}.mp3",
                    "type": "audio",
                    "ext": "mp3",
                    "filesize": audio_filesize,
                    "url": info.get("webpage_url", ""),
                    "item": audio_item
                })
            elif ext == "mp4" and resolution != "未知" and vbr:
                if resolution not in video_formats:
                    video_formats[resolution] = {
                        "format_id": format_id,
                        "ext": ext,
                        "filesize": filesize if filesize else 0
                    }

        for res, v_format in sorted(video_formats.items(), key=lambda x: x[0], reverse=True):
            res_group = None
            for i in range(video_root.childCount()):
                if video_root.child(i).text(1) == res:
                    res_group = video_root.child(i)
                    break
            if not res_group:
                res_group = QTreeWidgetItem(video_root)
                res_group.setText(1, res)
                res_group.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                res_group.setCheckState(0, Qt.Unchecked)
                res_group.setExpanded(True)

            filename = self.sanitize_filename(formatted_title)
            if audio_format:
                video_audio_item = QTreeWidgetItem(res_group)
                total_size = v_format["filesize"] + audio_filesize
                self._add_tree_item(video_audio_item, filename, "mp4（有音频）", res, total_size)
                self.formats.append({
                    "video_id": video_id,
                    "format_id": f"{v_format['format_id']}+{audio_format}",
                    "description": f"{filename}.mp4",
                    "type": "video_audio",
                    "ext": "mp4",
                    "filesize": total_size,
                    "url": info.get("webpage_url", ""),
                    "item": video_audio_item
                })

        subtitles = info.get("subtitles", {}) or info.get("automatic_captions", {})
        for lang, sub_list in subtitles.items():
            for sub in sub_list:
                ext = sub.get("ext", "srt")
                filename = self.sanitize_filename(f"{formatted_title}_{lang}")
                sub_item = QTreeWidgetItem(timed_subtitle_group)
                self._add_tree_item(sub_item, f"{filename}.{ext}", "字幕", lang, 0)
                self.formats.append({
                    "video_id": video_id,
                    "format_id": None,
                    "description": f"{filename}.{ext}",
                    "type": "subtitle",
                    "lang": lang,
                    "ext": ext,
                    "filesize": 0,
                    "url": info.get("webpage_url", ""),
                    "item": sub_item
                })

                no_ts_filename = self.sanitize_filename(f"{formatted_title}_{lang}_no_timestamp")
                no_ts_item = QTreeWidgetItem(no_timed_subtitle_group)
                self._add_tree_item(no_ts_item, f"{no_ts_filename}.{ext}", "字幕", f"{lang}（无时间戳）", 0)
                self.formats.append({
                    "video_id": video_id,
                    "format_id": None,
                    "description": f"{no_ts_filename}.{ext}",
                    "type": "subtitle_no_timestamp",
                    "lang": lang,
                    "ext": ext,
                    "filesize": 0,
                    "url": info.get("webpage_url", ""),
                    "item": no_ts_item
                })

        return video_root, audio_root, subtitle_root

    def _add_tree_item(
        self,
        item: QTreeWidgetItem,
        filename: str,
        file_type: str,
        resolution: str,
        filesize: Optional[int]
    ) -> None:
        """添加树形控件项"""
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Unchecked)
        item.setText(1, filename)
        item.setText(2, file_type)
        item.setText(3, str(resolution))
        item.setText(4, self.format_size(filesize))

    def on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """处理树形控件项状态变化"""
        if column != 0:
            return

        def set_check_state_recursive(tree_item: QTreeWidgetItem, state: Qt.CheckState) -> None:
            tree_item.setCheckState(0, state)
            for i in range(tree_item.childCount()):
                set_check_state_recursive(tree_item.child(i), state)

        if item.childCount() > 0:
            checked = item.checkState(0) == Qt.Checked
            for i in range(item.childCount()):
                set_check_state_recursive(item.child(i), Qt.Checked if checked else Qt.Unchecked)
        else:
            parent = item.parent()
            if parent:
                all_checked = all(parent.child(i).checkState(0) == Qt.Checked for i in range(parent.childCount()))
                parent.setCheckState(0, Qt.Checked if all_checked else Qt.Unchecked)
                grandparent = parent.parent()
                while grandparent:
                    all_checked = all(grandparent.child(i).checkState(0) == Qt.Checked for i in range(grandparent.childCount()))
                    grandparent.setCheckState(0, Qt.Checked if all_checked else Qt.Unchecked)
                    grandparent = grandparent.parent()

    def on_parse_error(self, error_msg: str) -> None:
        """处理解析错误"""
        QMessageBox.critical(self, "错误", error_msg)
        logger.error(error_msg)
        self.download_output.append(error_msg)
        self.parse_button.setEnabled(True)

    def download_progress_hook(self, d: Dict) -> None:
        """下载进度回调"""
        if d["status"] == "downloading":
            filename = d.get("filename", "")
            percent_str = d.get("_percent_str", "0%").strip("%")
            speed = d.get("_speed_str", "未知速率")
            try:
                percent = float(percent_str)
            except ValueError:
                percent = 0
            self.download_progress[filename] = (percent, speed)
        elif d["status"] == "finished":
            filename = d.get("filename", "")
            self.download_progress[filename] = (100, "已完成")

    def update_download_progress(self) -> None:
        """更新下载进度"""
        if not self.is_downloading or not self.download_progress:
            if self.progress_bar.isVisible():
                self.progress_bar.setVisible(False)
                self.status_label.setVisible(False)
                self.download_button.setText("下载选中项")
                self.download_button.setStyleSheet(self.default_style)
                self.setWindowTitle(f"椰果视频下载器-v{Config.APP_VERSION} - 就绪")
            return

        total_percent = sum(percent for percent, _ in self.download_progress.values())
        total_speed = [speed for _, speed in self.download_progress.values()]
        avg_percent = total_percent / len(self.download_progress)
        speed_text = ", ".join(total_speed)
        active_count = len([w for w in self.download_workers if w.isRunning()])
        self.progress_bar.setValue(int(avg_percent))
        self.progress_bar.setVisible(True)
        self.status_label.setText(f"下载中: {avg_percent:.1f}% - {speed_text} (活动: {active_count}/{Config.MAX_CONCURRENT_DOWNLOADS})")
        self.status_label.setVisible(True)
        self.setWindowTitle(f"椰果视频下载器-v{Config.APP_VERSION} - 下载中 ({avg_percent:.1f}%)")

        while self.active_downloads < Config.MAX_CONCURRENT_DOWNLOADS and self.download_queue:
            url, fmt = self.download_queue.popleft()
            self.start_download(url, fmt)

    def download_selected(self, item: Optional[QTreeWidgetItem] = None, column: Optional[int] = None) -> None:
        """下载选中的格式"""
        selected_formats = []

        try:
            def collect_checked_items(tree_item: QTreeWidgetItem) -> List[Dict]:
                checked_items = []
                for i in range(tree_item.childCount()):
                    child = tree_item.child(i)
                    if child.checkState(0) == Qt.Checked and child.childCount() == 0:
                        for fmt in self.formats:
                            if fmt["item"] == child:
                                checked_items.append(fmt)
                                break
                    elif child.childCount() > 0:
                        checked_items.extend(collect_checked_items(child))
                return checked_items

            for i in range(self.format_tree.topLevelItemCount()):
                top_item = self.format_tree.topLevelItem(i)
                selected_formats.extend(collect_checked_items(top_item))

            if not selected_formats:
                QMessageBox.warning(self, "提示", "请先勾选至少一个格式或分类！")
                return

            if not self.check_ffmpeg():
                self.download_output.append("错误: 请安装 FFmpeg 并放入保存路径")
                self.reset_download_state()
                return

            self.is_downloading = True
            self.download_progress.clear()
            self.download_button.setEnabled(False)
            self.parse_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            self.status_label.setText("下载中: 0% - 未知速率")
            self.status_label.setVisible(True)
            logger.info("开始下载...")

            for fmt in selected_formats:
                if self.active_downloads < Config.MAX_CONCURRENT_DOWNLOADS:
                    self.start_download(fmt["url"], fmt)
                else:
                    self.download_queue.append((fmt["url"], fmt))

        except Exception as e:
            logger.error(f"下载选中项失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "错误", f"下载过程中发生错误: {str(e)}")
            self.reset_download_state()

    def start_download(self, url: str, selected_format: Dict) -> None:
        """启动下载任务"""
        try:
            output_file = os.path.join(self.save_path, selected_format["description"])
            self.download_progress[output_file] = (0, "未知速率")
            logger.info(f"开始下载: {output_file}")

            ydl_opts = {
                "outtmpl": os.path.join(self.save_path, "%(title)s_%(id)s.%(ext)s"),
                "quiet": False,
                "ffmpeg_location": self.ffmpeg_path,
            }

            speed_limit = self.speed_limit_input.text().strip()
            if speed_limit.isdigit():
                ydl_opts["ratelimit"] = int(speed_limit) * 1024

            if selected_format["type"] == "audio":
                ydl_opts.update({
                    "format": selected_format["format_id"],
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                })
            elif selected_format["type"] == "video_audio":
                ydl_opts.update({
                    "format": selected_format["format_id"],
                    "merge_output_format": "mp4",
                })
            elif selected_format["type"] == "subtitle":
                ydl_opts.update({
                    "skip_download": True,
                    "writesubtitles": True,
                    "subtitleslangs": [selected_format["lang"]],
                    "subtitle_format": "srt",
                    "outtmpl": output_file,
                })
            elif selected_format["type"] == "subtitle_no_timestamp":
                ydl_opts.update({
                    "skip_download": True,
                    "writesubtitles": True,
                    "subtitleslangs": [selected_format["lang"]],
                    "subtitle_format": "srt",
                    "outtmpl": output_file,
                })

            worker = DownloadWorker(url, ydl_opts)
            worker.progress_signal.connect(self.download_progress_hook)
            worker.log_signal.connect(self.download_output.append)
            worker.finished.connect(lambda filename: self.on_download_finished(filename, url, selected_format))
            worker.error.connect(self.on_download_error)
            worker.start()
            self.download_workers.append(worker)
            self.active_downloads += 1
        except Exception as e:
            logger.error(f"启动下载失败: {str(e)}", exc_info=True)
            self.download_output.append(f"错误: 下载 {selected_format['description']} 失败: {str(e)}")
            self.reset_download_state()

    def remove_timestamps(self, subtitle_path: str) -> str:
        """移除字幕时间戳"""
        try:
            if not os.path.exists(subtitle_path):
                logger.error(f"字幕文件不存在: {subtitle_path}")
                return subtitle_path
            with open(subtitle_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            output_content = re.sub(
                r"^\d+\n\d{2}:\d{2}:\d{2}[.,]\d{1,3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{1,3}\n|\n\n",
                "\n",
                content
            ).strip()
            if not output_content:
                logger.warning(f"无有效字幕文本: {subtitle_path}")
                return subtitle_path
            new_path = os.path.splitext(subtitle_path)[0] + "_no_timestamp.srt"
            with open(new_path, "w", encoding="utf-8") as f:
                f.write(output_content)
            logger.info(f"无时间戳字幕生成: {new_path}")
            return new_path
        except Exception as e:
            logger.error(f"处理字幕失败: {str(e)}")
            return subtitle_path

    def on_download_finished(self, filename: str, url: str, selected_format: Optional[Dict] = None) -> None:
        """处理下载完成"""
        self.active_downloads -= 1
        if not filename:
            logger.warning("未获取到下载文件名")
            actual_filename = os.path.join(self.save_path, selected_format["description"]) if selected_format else ""
        else:
            actual_filename = filename

        if selected_format and selected_format["type"] == "subtitle_no_timestamp":
            new_filename = self.remove_timestamps(actual_filename)
            logger.info(f"无时间戳字幕生成: {new_filename}")
            self.download_output.append(f"无时间戳字幕生成: {new_filename}")
        else:
            logger.info(f"下载完成: {actual_filename}")
            self.download_output.append(f"下载完成: {actual_filename}")

        self.download_workers = [w for w in self.download_workers if w.isRunning()]
        if not self.download_workers and not self.download_queue:
            self.show_completion_dialog()

    def show_completion_dialog(self) -> None:
        """显示下载完成对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("成功")
        dialog.setFixedSize(300, 100)
        layout = QVBoxLayout()
        label = QLabel(f"所有文件已下载到:\n{self.save_path}")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        ok_button = QPushButton("确定", dialog)
        ok_button.setFixedSize(80, 30)
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)
        open_button = QPushButton("打开文件夹", dialog)
        open_button.setFixedSize(80, 30)
        open_button.clicked.connect(lambda: self.open_save_path_and_close(dialog))
        button_layout.addWidget(open_button)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec_()
        self.reset_download_state()

    def open_save_path_and_close(self, dialog: QDialog) -> None:
        """打开保存路径并关闭对话框"""
        self.open_save_path()
        dialog.accept()

    def open_save_path(self) -> None:
        """打开保存路径"""
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.save_path))
        except Exception as e:
            logger.error(f"打开文件夹失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"无法打开文件夹: {str(e)}")

    def on_download_error(self, error_msg: str) -> None:
        """处理下载错误"""
        self.active_downloads -= 1
        QMessageBox.critical(self, "错误", f"下载失败: {error_msg}")
        logger.error(f"下载错误: {error_msg}")
        self.download_output.append(f"错误: {error_msg}")
        self.reset_download_state()

    def pause_downloads(self) -> None:
        """暂停或恢复下载"""
        if self.pause_button.text() == "暂停下载":
            for worker in self.download_workers:
                if worker.isRunning():
                    worker.pause()
            self.pause_button.setText("恢复下载")
            self.download_output.append("下载已暂停")
            logger.info("下载已暂停")
        else:
            for worker in self.download_workers:
                if worker.isRunning():
                    worker.resume()
            self.pause_button.setText("暂停下载")
            self.download_output.append("下载已恢复")
            logger.info("下载已恢复")

    def cancel_downloads(self) -> None:
        """取消所有下载"""
        reply = QMessageBox.question(
            self, "确认", "确定要取消所有下载吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            for worker in self.download_workers:
                if worker.isRunning():
                    worker.cancel()
            self.download_queue.clear()
            self.reset_download_state()
            logger.info("下载已取消")
            self.download_output.append("下载已取消")

    def reset_download_state(self) -> None:
        """重置下载状态"""
        self.download_progress.clear()
        self.is_downloading = False
        self.active_downloads = 0
        self.download_workers.clear()
        self.download_button.setEnabled(True)
        self.parse_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        self.download_button.setText("下载选中项")
        self.download_button.setStyleSheet(self.default_style)
        self.pause_button.setText("暂停下载")

    def show_context_menu(self, pos: "QPoint") -> None:
        """显示右键菜单"""
        menu = QMenu(self)
        copy_action = menu.addAction("复制文件名")
        action = menu.exec_(self.format_tree.mapToGlobal(pos))
        if action == copy_action:
            item = self.format_tree.currentItem()
            if item and item.childCount() == 0:
                filename = item.text(1)
                QApplication.clipboard().setText(filename)

    def closeEvent(self, event: "QCloseEvent") -> None:
        """处理窗口关闭事件"""
        self.timer.stop()
        for worker in self.download_workers:
            if worker.isRunning():
                worker.cancel()
        for worker in self.parse_workers:
            if worker.isRunning():
                worker.quit()
                worker.wait()
        self.settings.setValue("save_path", self.save_path)
        event.accept()

def main() -> None:
    """程序入口"""
    app = QApplication(sys.argv)
    window = VideoDownloader()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()