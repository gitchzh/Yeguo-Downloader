"""
主窗口模块

包含应用程序的主窗口类。
"""

import os
import re
import sys
from typing import Dict, List, Optional, Tuple
from collections import OrderedDict, deque

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QFileDialog, QProgressBar, QTextEdit, QMenu, QDialog
)
from PyQt5.QtCore import Qt, QTimer, QSettings, QUrl
from PyQt5.QtGui import QIcon, QDesktopServices

from ..core.config import Config
from ..utils.logger import logger
from ..utils.file_utils import sanitize_filename, format_size, get_ffmpeg_path, check_ffmpeg
from ..workers.parse_worker import ParseWorker
from ..workers.download_worker import DownloadWorker
from .main_window_methods import VideoDownloaderMethods


class VideoDownloader(QMainWindow, VideoDownloaderMethods):
    """
    视频下载器主窗口类
    
    负责管理整个应用程序的用户界面、状态管理和业务逻辑。
    包含视频解析、格式选择、下载管理、进度显示等功能。
    """
    
    def __init__(self):
        """
        初始化主窗口
        
        设置窗口属性、初始化成员变量、加载设置、创建用户界面。
        """
        QMainWindow.__init__(self)
        VideoDownloaderMethods.__init__(self)
        
        # 基础配置
        self.save_path: str = os.getcwd()                    # 文件保存路径
        self.parse_cache: OrderedDict = OrderedDict()        # 解析结果缓存
        self.formats: List[Dict] = []                        # 可用格式列表
        self.download_progress: Dict[str, Tuple[float, str]] = {}  # 下载进度信息
        self.is_downloading: bool = False                    # 下载状态标志
        
        # 工作线程管理
        self.download_workers: List[DownloadWorker] = []     # 下载工作线程列表
        self.parse_workers: List[ParseWorker] = []           # 解析工作线程列表
        self.download_queue: deque = deque()                 # 下载队列
        
        # 状态计数
        self.active_downloads: int = 0                       # 活动下载数量
        self.total_urls: int = 0                             # 总URL数量
        self.parsed_count: int = 0                           # 已解析数量
        
        # 外部依赖
        self.ffmpeg_path: Optional[str] = get_ffmpeg_path(self.save_path)  # FFmpeg路径
        self.settings = QSettings("MyCompany", "VideoDownloader")  # 设置管理器

        self.init_ui()
        self.load_settings()

        # 设置应用图标
        icon_path = (
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resources", "logo.ico")
            if not getattr(sys, "frozen", False)
            else os.path.join(sys._MEIPASS, "logo.ico")
        )
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            logger.info(f"应用图标已设置: {icon_path}")
        else:
            logger.warning(f"图标文件未找到: {icon_path}")

    def init_ui(self) -> None:
        """
        初始化用户界面
        
        创建和配置所有UI组件，包括菜单栏、输入区域、格式选择树、进度条、按钮等。
        设置布局、样式和事件连接。
        """
        # 设置窗口基本属性
        self.setWindowTitle(f"椰果视频下载器-v{Config.APP_VERSION}")
        self.setGeometry(100, 100, 800, 600)  # 设置默认宽高为800*600
        
        # 创建菜单栏
        self.create_menu_bar()

        # 创建中央部件和主布局
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout()

        # ==================== 输入区域 ====================
        input_layout = QHBoxLayout()
        
        # URL输入框
        self.url_input = QTextEdit(self)
        self.url_input.setPlaceholderText("请输入YouTube或B站视频链接，每行一个")
        self.url_input.setFixedHeight(60)
        input_layout.addWidget(QLabel("视频链接:"))
        input_layout.addWidget(self.url_input)
        
        # 解析按钮
        self.parse_button = QPushButton("解析", self)
        self.parse_button.clicked.connect(self.parse_video)
        self.parse_button.setFixedSize(100, 35)
        input_layout.addWidget(self.parse_button)
        layout.addLayout(input_layout)

        # ==================== 配置区域 ====================
        
        # 保存路径选择
        path_layout = QHBoxLayout()
        self.path_label = QLabel(f"保存路径: {self.save_path}")
        path_layout.addWidget(self.path_label)
        self.path_button = QPushButton("选择路径", self)
        self.path_button.clicked.connect(self.choose_save_path)
        self.path_button.setFixedSize(100, 35)
        path_layout.addWidget(self.path_button)
        layout.addLayout(path_layout)

        # 下载速度限制设置
        speed_layout = QHBoxLayout()
        self.speed_limit_input = QLineEdit(self)
        self.speed_limit_input.setPlaceholderText("下载速度限制 (KB/s，留空为无限制)")
        self.speed_limit_input.setFixedWidth(200)
        speed_layout.addWidget(QLabel("速度限制:"))
        speed_layout.addWidget(self.speed_limit_input)
        layout.addLayout(speed_layout)

        # ==================== 格式选择区域 ====================
        
        # 选择控制按钮
        select_layout = QHBoxLayout()
        
        # 智能选择按钮（整合全选、取消全选、反选功能）
        self.smart_select_button = QPushButton("全选", self)
        self.smart_select_button.clicked.connect(self.smart_select_action)
        self.smart_select_button.setFixedSize(100, 35)
        self.smart_select_button.setEnabled(False)  # 初始禁用
        select_layout.addWidget(self.smart_select_button)
        
        # 添加分隔符
        select_layout.addSpacing(20)
        
        # 智能下载按钮（整合下载和取消功能）
        self.smart_download_button = QPushButton("下载选中项", self)
        self.smart_download_button.clicked.connect(self.smart_download_action)
        self.smart_download_button.setEnabled(False)  # 初始禁用
        self.smart_download_button.setFixedSize(120, 35)  # 固定大小
        self.default_style = self.smart_download_button.styleSheet()  # 保存默认样式
        select_layout.addWidget(self.smart_download_button)
        
        # 智能暂停按钮（整合暂停和恢复功能）
        self.smart_pause_button = QPushButton("暂停下载", self)
        self.smart_pause_button.clicked.connect(self.smart_pause_action)
        self.smart_pause_button.setEnabled(False)  # 初始禁用
        self.smart_pause_button.setFixedSize(120, 35)  # 固定大小
        select_layout.addWidget(self.smart_pause_button)
        
        # 添加弹性空间
        select_layout.addStretch()
        
        # 选择统计标签
        self.selection_count_label = QLabel("已选择: 0 项", self)
        select_layout.addWidget(self.selection_count_label)
        
        layout.addLayout(select_layout)
        
        # 格式选择树形控件
        self.format_tree = QTreeWidget(self)
        self.format_tree.setHeaderLabels(["选择", "文件名称", "文件类型", "分辨率/语言", "文件大小", "状态"])
        self.format_tree.itemDoubleClicked.connect(self.toggle_checkbox)  # 双击切换选择状态
        
        # 设置列宽，确保"选择"列有足够空间显示完整复选框
        self.format_tree.setColumnWidth(0, 80)   # 选择列宽度 - 增加宽度确保复选框完整显示
        self.format_tree.setColumnWidth(1, 250)  # 文件名列宽度
        self.format_tree.setColumnWidth(4, 120)  # 文件大小列宽度
        self.format_tree.setColumnWidth(5, 80)   # 状态列宽度
        
        # 设置"选择"列的最小宽度，防止被压缩
        self.format_tree.header().setMinimumSectionSize(80)
        self.format_tree.header().setStretchLastSection(False)  # 最后一列不自动拉伸
        self.format_tree.setAlternatingRowColors(True)  # 交替行颜色
        self.format_tree.setContextMenuPolicy(Qt.CustomContextMenu)  # 自定义右键菜单
        self.format_tree.customContextMenuRequested.connect(self.show_context_menu)  # 右键菜单事件
        self.format_tree.itemChanged.connect(self.on_item_changed)  # 项目状态变化事件
        
        # 设置表头样式（灰色背景）
        self.format_tree.setStyleSheet("""
            QTreeWidget::item {
                padding: 6px;
                border: none;
                font-size: 14px;
                font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                color: #333333;
                padding: 6px 8px;
                border: 1px solid #e0e0e0;
                font-weight: bold;
                font-size: 14px;
                font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
            }
            QHeaderView::section:hover {
                background-color: #eeeeee;
            }
        """)
        
        layout.addWidget(self.format_tree, stretch=3)  # 占据3倍空间

        # ==================== 进度显示区域 ====================
        
        self.progress_layout = QVBoxLayout()
        
        # 进度条
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # 初始隐藏
        self.progress_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪", self)
        self.status_label.setVisible(False)  # 初始隐藏
        self.progress_layout.addWidget(self.status_label)
        layout.addLayout(self.progress_layout)



        # 设置布局
        widget.setLayout(layout)

        # ==================== 状态栏设置 ====================
        
        # 创建状态栏
        self.statusBar = self.statusBar()
        self.statusBar.setStyleSheet("""
            QStatusBar {
                background-color: #e3f2fd;
                border-top: 1px solid #bbdefb;
                color: #1976d2;
                font-size: 14px;
                font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
                padding: 6px 8px;
            }
            
            QStatusBar::item {
                border: none;
                background: transparent;
            }
            
            QStatusBar QLabel {
                color: #1976d2;
                font-size: 14px;
                font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
                padding: 0px 6px;
            }
        """)
        
        # 创建状态栏标签
        self.status_label_main = QLabel("就绪")
        self.status_label_progress = QLabel("")
        self.status_label_files = QLabel("")
        
        # 创建滚动状态显示区域
        self.status_scroll_label = QLabel("")
        self.status_scroll_label.setMinimumWidth(300)
        self.status_scroll_label.setMaximumWidth(400)
        self.status_scroll_label.setStyleSheet("""
            QLabel {
                color: #007acc;
                font-weight: 500;
                font-size: 14px;
                font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
                padding: 0px 8px;
            }
        """)
        
        # 添加到状态栏
        self.statusBar.addWidget(self.status_label_main)
        self.statusBar.addWidget(self.status_scroll_label)
        self.statusBar.addPermanentWidget(self.status_label_files)
        self.statusBar.addPermanentWidget(self.status_label_progress)
        
        # 初始化状态
        self.update_status_bar("就绪", "", "")
        
        # 确保列宽设置生效
        self.ensure_column_widths()

        # ==================== 样式设置 ====================
        
        # 应用Cursor风格的浅色主题样式表
        self.setStyleSheet("""
             /* 全局字体设置 - 优化字体大小和字体 */
             * {
                 font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
                 font-size: 14px;
                 font-weight: 400;
             }
             
             /* 主窗口样式 */
             QMainWindow {
                 background-color: #ffffff;
                 color: #2c3e50;
                 font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
                 font-size: 14px;
                 font-weight: 400;
             }
             
             /* 菜单栏样式 */
             QMenuBar {
                 background-color: #f8f9fa;
                 border-bottom: 1px solid #e9ecef;
                 color: #495057;
                 font-weight: 500;
                 padding: 4px;
                 font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
                 font-size: 14px;
             }
             
             QMenuBar::item {
                 background-color: transparent;
                 padding: 6px 12px;
                 border-radius: 4px;
                 font-size: 14px;
             }
             
             QMenuBar::item:selected {
                 background-color: #e3f2fd;
                 color: #1976d2;
             }
             
             QMenuBar::item:pressed {
                 background-color: #bbdefb;
             }
             
             /* 菜单样式 */
             QMenu {
                 background-color: #ffffff;
                 border: 1px solid #e0e0e0;
                 border-radius: 6px;
                 padding: 4px;
                 color: #2c3e50;
                 font-size: 14px;
                 font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
             }
             
             QMenu::item {
                 padding: 8px 24px 8px 16px;
                 border-radius: 4px;
                 margin: 1px;
                 font-size: 14px;
             }
             
             QMenu::item:selected {
                 background-color: #e3f2fd;
                 color: #1976d2;
             }
             
             QMenu::separator {
                 height: 1px;
                 background-color: #e0e0e0;
                 margin: 4px 8px;
             }
             
                           /* 按钮样式 */
              QPushButton {
                  background-color: #007acc;
                  color: white;
                  border: none;
                  border-radius: 6px;
                  padding: 8px 16px;
                  font-weight: 500;
                  font-size: 14px;
                  min-height: 24px;
                  min-width: 80px;
                  font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
              }
              
              QPushButton:hover {
                  background-color: #005a9e;
              }
              
              QPushButton:pressed {
                  background-color: #004578;
              }
              
                           QPushButton:disabled {
                 background-color: #e0e0e0;
                 color: #9e9e9e;
             }
             
             /* 输入框样式优化 */
             QTextEdit, QLineEdit {
                 font-size: 14px;
                 font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
                 padding: 8px;
                 border: 1px solid #e0e0e0;
                 border-radius: 4px;
                 background-color: #ffffff;
             }
             
             QTextEdit:focus, QLineEdit:focus {
                 border: 2px solid #007acc;
                 outline: none;
             }
             
             /* 标签样式优化 */
             QLabel {
                 font-size: 14px;
                 font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
                 color: #2c3e50;
             }
             
             /* 进度条样式优化 */
             QProgressBar {
                 font-size: 14px;
                 font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
                 border: 1px solid #e0e0e0;
                 border-radius: 4px;
                 text-align: center;
                 background-color: #f5f5f5;
             }
             
             QProgressBar::chunk {
                 background-color: #007acc;
                 border-radius: 3px;
             }
              
                             /* 智能选择按钮样式 */
               QPushButton[text="全选"],
               QPushButton[text="取消全选"],
               QPushButton[text="反选"] {
                   background-color: #28a745;
                   border: 1px solid #28a745;
               }
               
               QPushButton[text="全选"]:hover,
               QPushButton[text="取消全选"]:hover,
               QPushButton[text="反选"]:hover {
                   background-color: #218838;
                   border-color: #1e7e34;
               }
               
               QPushButton[text="全选"]:pressed,
               QPushButton[text="取消全选"]:pressed,
               QPushButton[text="反选"]:pressed {
                   background-color: #1e7e34;
                   border-color: #1c7430;
               }
               
               /* 智能下载按钮样式 */
               QPushButton[text="下载选中项"] {
                   background-color: #007acc;
                   border: 1px solid #007acc;
               }
               
               QPushButton[text="下载选中项"]:hover {
                   background-color: #005a9e;
                   border-color: #005a9e;
               }
               
               QPushButton[text="下载选中项"]:pressed {
                   background-color: #004578;
                   border-color: #004578;
               }
               
               QPushButton[text="取消下载"] {
                   background-color: #dc3545;
                   border: 1px solid #dc3545;
               }
               
               QPushButton[text="取消下载"]:hover {
                   background-color: #c82333;
                   border-color: #bd2130;
               }
               
               QPushButton[text="取消下载"]:pressed {
                   background-color: #bd2130;
                   border-color: #b21f2a;
               }
               
               /* 智能暂停按钮样式 */
               QPushButton[text="暂停下载"] {
                   background-color: #ffc107;
                   border: 1px solid #ffc107;
                   color: #212529;
               }
               
               QPushButton[text="暂停下载"]:hover {
                   background-color: #e0a800;
                   border-color: #d39e00;
               }
               
               QPushButton[text="暂停下载"]:pressed {
                   background-color: #d39e00;
                   border-color: #c69500;
               }
               
               QPushButton[text="恢复下载"] {
                   background-color: #17a2b8;
                   border: 1px solid #17a2b8;
                   color: white;
               }
               
               QPushButton[text="恢复下载"]:hover {
                   background-color: #138496;
                   border-color: #117a8b;
               }
               
               QPushButton[text="恢复下载"]:pressed {
                   background-color: #117a8b;
                   border-color: #10707f;
               }
             
             /* 树形控件样式 */
             QTreeWidget {
                 background-color: #ffffff;
                 border: 1px solid #e0e0e0;
                 border-radius: 6px;
                 gridline-color: #f5f5f5;
                 selection-background-color: #e3f2fd;
                 selection-color: #1976d2;
                 font-size: 13px;
                 font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
             }
             
             QTreeWidget::item {
                 padding: 4px;
                 border-radius: 4px;
                 margin: 1px;
                 font-size: 13px;
             }
             
             QTreeWidget::item:selected {
                 background-color: #e3f2fd;
                 color: #1976d2;
             }
             
             QTreeWidget::item:hover {
                 background-color: #f5f5f5;
             }
             
             QTreeWidget::branch {
                 background-color: transparent;
             }
             
             QTreeWidget::branch:has-children:!has-siblings:closed,
             QTreeWidget::branch:closed:has-children:has-siblings {
                 image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQgNkw4IDZMOSA2TDkgN0w4IDdMOCA4TDkgOEw5IDlMOCA5TDggMTBMOSAxMEw5IDExTDggMTFMOCAxMkw5IDEyTDkgMTNMNyAxM0w3IDEyTDggMTJMNyAxMkw3IDExTDggMTFMNyAxMUw3IDEwTDggMTBMNyAxMEw3IDlMOCA5TDcgOUw3IDhMOCA4TDcgOEw3IDdMOCA3TDcgN0w3IDZMNCA2WiIgZmlsbD0iIzY2NjY2NiIvPgo8L3N2Zz4K);
             }
             
             QTreeWidget::branch:open:has-children:!has-siblings,
             QTreeWidget::branch:open:has-children:has-siblings {
                 image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTYgNEw2IDhMNiAxMkw2IDE2TDYgMjBMNiAyNEw2IDI4TDYgMzJMNiAzNkw2IDQwTDYgNDRMNiA0OEw2IDUyTDYgNTZMNyA1Nkw3IDUyTDcgNDhMNyA0NEw3IDQwTDcgMzZMNyAzMkw3IDI4TDcgMjRMNyAyMEw3IDE2TDcgMTJMNyA4TDcgNEw2IDRaIiBmaWxsPSIjNjY2NjY2Ii8+Cjwvc3ZnPgo=);
             }
             
             /* 进度条样式 */
             QProgressBar {
                 border: 1px solid #e0e0e0;
                 border-radius: 6px;
                 text-align: center;
                 background-color: #f5f5f5;
                 color: #2c3e50;
                 font-weight: 500;
                 font-size: 13px;
                 font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
             }
             
             QProgressBar::chunk {
                 background-color: #007acc;
                 border-radius: 5px;
                 margin: 1px;
             }
             
             /* 输入框样式 */
             QLineEdit, QTextEdit {
                 background-color: #ffffff;
                 border: 1px solid #e0e0e0;
                 border-radius: 6px;
                 padding: 8px;
                 color: #2c3e50;
                 font-size: 13px;
                 selection-background-color: #e3f2fd;
                 font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
             }
             
             QLineEdit:focus, QTextEdit:focus {
                 border-color: #007acc;
                 outline: none;
             }
             
             QLineEdit:hover, QTextEdit:hover {
                 border-color: #bdbdbd;
             }
             
             /* 标签样式 */
             QLabel {
                 color: #2c3e50;
                 font-size: 13px;
                 font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
             }
             
             /* 滚动条样式 */
             QScrollBar:vertical {
                 background-color: #f5f5f5;
                 width: 12px;
                 border-radius: 6px;
             }
             
             QScrollBar::handle:vertical {
                 background-color: #c0c0c0;
                 border-radius: 6px;
                 min-height: 20px;
             }
             
             QScrollBar::handle:vertical:hover {
                 background-color: #a0a0a0;
             }
             
             QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                 height: 0px;
             }
             
             /* 复选框样式 */
             QCheckBox {
                 color: #2c3e50;
                 font-size: 13px;
                 spacing: 8px;
                 font-family: "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", sans-serif;
             }
             
             QCheckBox::indicator {
                 width: 16px;
                 height: 16px;
                 border: 2px solid #e0e0e0;
                 border-radius: 3px;
                 background-color: #ffffff;
             }
             
             QCheckBox::indicator:checked {
                 background-color: #007acc;
                 border-color: #007acc;
                 image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDZMMSA3TDMuNSA5LjVMMTEgMkwxMCAzWiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cg==);
             }
             
             QCheckBox::indicator:hover {
                 border-color: #007acc;
             }
         """)

        # ==================== 定时器设置 ====================
        
        # 创建定时器用于更新下载进度
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_download_progress)
        self.timer.start(500)  # 每500毫秒更新一次

    def update_status_bar(self, main_status: str, progress_info: str = "", file_info: str = "") -> None:
        """
        更新状态栏信息
        
        Args:
            main_status: 主要状态信息
            progress_info: 进度信息
            file_info: 文件信息
        """
        self.status_label_main.setText(main_status)
        self.status_label_progress.setText(progress_info)
        self.status_label_files.setText(file_info)

    def update_scroll_status(self, status_text: str) -> None:
        """
        更新滚动状态显示
        
        Args:
            status_text: 状态文本
        """
        # 简单的滚动效果：新状态追加到现有状态后面
        current_text = self.status_scroll_label.text()
        if current_text:
            # 如果文本太长，移除前面的部分
            if len(current_text) > 50:
                current_text = current_text[20:]  # 移除前面的20个字符
            new_text = current_text + " → " + status_text
        else:
            new_text = status_text
        
        self.status_scroll_label.setText(new_text)
        
        # 强制更新显示
        self.status_scroll_label.repaint()

    def create_menu_bar(self) -> None:
        """
        创建菜单栏
        
        包含文件、编辑、工具、帮助等传统菜单项。
        """
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件(&F)')
        
        # 新建会话
        new_action = file_menu.addAction('新建会话(&N)')
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_session)
        
        file_menu.addSeparator()
        
        # 选择保存路径
        select_path_action = file_menu.addAction('选择保存路径(&O)')
        select_path_action.setShortcut('Ctrl+O')
        select_path_action.triggered.connect(self.choose_save_path)
        
        # 打开保存文件夹
        open_folder_action = file_menu.addAction('打开保存文件夹(&F)')
        open_folder_action.setShortcut('Ctrl+Shift+O')
        open_folder_action.triggered.connect(self.open_save_path)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = file_menu.addAction('退出(&X)')
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑(&E)')
        
        # 全选
        select_all_action = edit_menu.addAction('全选(&A)')
        select_all_action.setShortcut('Ctrl+A')
        select_all_action.triggered.connect(self.select_all_formats)
        
        # 取消全选
        deselect_all_action = edit_menu.addAction('取消全选(&D)')
        deselect_all_action.setShortcut('Ctrl+D')
        deselect_all_action.triggered.connect(self.deselect_all_formats)
        
        # 反选
        invert_selection_action = edit_menu.addAction('反选(&I)')
        invert_selection_action.setShortcut('Ctrl+I')
        invert_selection_action.triggered.connect(self.invert_selection)
        
        edit_menu.addSeparator()
        
        # 清空输入
        clear_input_action = edit_menu.addAction('清空输入(&L)')
        clear_input_action.setShortcut('Ctrl+L')
        clear_input_action.triggered.connect(self.clear_input)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具(&T)')
        
        # 解析视频
        parse_action = tools_menu.addAction('解析视频(&P)')
        parse_action.setShortcut('F5')
        parse_action.triggered.connect(self.parse_video)
        
        # 开始下载
        download_action = tools_menu.addAction('开始下载(&D)')
        download_action.setShortcut('F6')
        download_action.triggered.connect(self.download_selected)
        
        # 暂停/恢复下载
        pause_action = tools_menu.addAction('暂停下载(&P)')
        pause_action.setShortcut('F7')
        pause_action.triggered.connect(self.pause_downloads)
        
        # 取消下载
        cancel_action = tools_menu.addAction('取消下载(&C)')
        cancel_action.setShortcut('F8')
        cancel_action.triggered.connect(self.cancel_downloads)
        
        tools_menu.addSeparator()
        
        # 设置
        settings_action = tools_menu.addAction('设置(&S)')
        settings_action.setShortcut('Ctrl+,')
        settings_action.triggered.connect(self.show_settings_dialog)
        
        tools_menu.addSeparator()
        
        # 日志管理
        log_menu = tools_menu.addMenu('日志管理(&L)')
        
        # 查看日志
        view_log_action = log_menu.addAction('查看日志(&V)')
        view_log_action.setShortcut('Ctrl+Shift+L')
        view_log_action.triggered.connect(self.show_log_dialog)
        
        # 清空日志
        clear_log_action = log_menu.addAction('清空日志(&C)')
        clear_log_action.triggered.connect(self.clear_log)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助(&H)')
        
        # 使用说明
        help_action = help_menu.addAction('使用说明(&H)')
        help_action.setShortcut('F1')
        help_action.triggered.connect(self.show_help_dialog)
        
        # 快捷键帮助
        shortcuts_action = help_menu.addAction('快捷键帮助(&K)')
        shortcuts_action.setShortcut('Ctrl+F1')
        shortcuts_action.triggered.connect(self.show_shortcuts_dialog)
        
        help_menu.addSeparator()
        
        # 问题反馈
        feedback_action = help_menu.addAction('问题反馈(&F)')
        feedback_action.setShortcut('Ctrl+Shift+F')
        feedback_action.triggered.connect(self.show_feedback_dialog)
        
        help_menu.addSeparator()
        
        # 关于
        about_action = help_menu.addAction('关于(&A)')
        about_action.triggered.connect(self.show_about_dialog)
    
    def ensure_column_widths(self) -> None:
        """确保列宽设置正确，特别是选择列的宽度"""
        # 确保"选择"列有足够的宽度显示完整复选框
        self.format_tree.setColumnWidth(0, 80)
        
        # 设置最小列宽，防止被压缩
        header = self.format_tree.header()
        header.setMinimumSectionSize(80)
        
        # 确保其他列的合理宽度
        if self.format_tree.columnWidth(1) < 200:  # 文件名列
            self.format_tree.setColumnWidth(1, 250)
        if self.format_tree.columnWidth(4) < 100:  # 文件大小列
            self.format_tree.setColumnWidth(4, 120)
        if self.format_tree.columnWidth(5) < 60:   # 状态列
            self.format_tree.setColumnWidth(5, 80)
