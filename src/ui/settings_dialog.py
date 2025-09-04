"""
设置对话框模块

包含应用程序的设置界面和配置管理功能。
"""

import os
from typing import Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QSpinBox, QCheckBox,
    QComboBox, QGroupBox, QFormLayout, QFileDialog, QMessageBox,
    QDialogButtonBox, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont

from ..core.config import Config
from ..utils.logger import logger


class SettingsDialog(QDialog):
    """
    设置对话框类
    
    提供完整的应用程序配置界面，包括基本设置、下载设置、界面设置等。
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("MyCompany", "VideoDownloader")
        self.init_ui()
        self.load_settings()
        # 初始化完成
        
    def center_on_parent(self) -> None:
        """将对话框居中显示在父窗口上"""
        if self.parent():
            parent_rect = self.parent().geometry()
            dialog_rect = self.geometry()
            x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - dialog_rect.height()) // 2
            self.move(x, y)
        
    def init_ui(self) -> None:
        """初始化用户界面"""
        self.setWindowTitle("设置")
        self.setFixedSize(650, 550)  # 固定尺寸，紧凑布局，去掉下半部分空白
        self.setModal(True)
        
        # 设置窗口居中显示
        self.center_on_parent()
        
        # 应用与主界面一致的Cursor风格浅色主题样式表
        self.setStyleSheet("""
            /* 全局字体设置 - 统一微软雅黑 */
            * {
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
                font-weight: 400;
            }
            
            QDialog {
                background-color: #ffffff;
                color: #1e1e1e;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
            }
            
            QTabWidget::pane {
                border: 1px solid #e9ecef;
                background-color: #ffffff;
                border-radius: 8px;
            }
            
            QTabBar::tab {
                background-color: #f8f9fa;
                color: #1e1e1e;
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #e9ecef;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 400;
            }
            
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #007bff;
                border-bottom: 2px solid #007bff;
            }
            
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
            
            QGroupBox {
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
                font-weight: 400;
                color: #1e1e1e;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #f8f9fa;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px 0 6px;
                color: #1e1e1e;
            }
            
            /* 按钮样式 - 统一风格 */
            QPushButton {
                background-color: #fdfdfd;
                color: #000000;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                padding: 4px 8px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
                min-height: 20px;
                min-width: 50px;
                margin: 0px;
                font-weight: normal;
            }

            QPushButton:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }
            
            /* 输入框样式 - Cursor风格浅色主题 */
            QTextEdit, QLineEdit {
                font-size: 13px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                padding: 6px 12px;
                border: 1px solid #e9ecef;
                background-color: #ffffff;
                border-radius: 8px;
                color: #1e1e1e;
                selection-background-color: #007bff;
                margin: 0px;
            }

            QTextEdit:focus, QLineEdit:focus {
                border: 1px solid #007bff;
                outline: none;
                border-radius: 8px;
            }

            QTextEdit:hover, QLineEdit:hover {
                border: 1px solid #007bff;
                border-radius: 8px;
            }
            
            /* 标签样式 - Cursor风格浅色主题 */
            QLabel {
                font-size: 13px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                color: #1e1e1e;
                font-weight: 400;
            }
            
            /* 数字输入框和下拉框样式 - Cursor风格浅色主题 */
            QSpinBox, QComboBox {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                padding: 8px 12px;
                color: #1e1e1e;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
                border-radius: 8px;
            }
            
            QSpinBox:focus, QComboBox:focus {
                border: 1px solid #007bff;
                border-radius: 8px;
            }
            
            QSpinBox:hover, QComboBox:hover {
                border: 1px solid #007bff;
                border-radius: 8px;
            }
            
            /* 复选框样式 - Cursor风格浅色主题 */
            QCheckBox {
                color: #1e1e1e;
                font-size: 13px;
                spacing: 6px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            }
            
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                background-color: #ffffff;
            }
            
            QCheckBox::indicator:checked {
                background-color: #007bff;
                border: 1px solid #007bff;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDQuNUw0LjUgOEwxMSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+Cg==);
            }
            
            QCheckBox::indicator:hover {
                border: 1px solid #007bff;
            }
            
            QDialogButtonBox QPushButton {
                background-color: #fdfdfd;
                color: #000000;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                padding: 4px 8px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
                min-height: 20px;
                min-width: 50px;
                font-weight: normal;
            }
            
            QDialogButtonBox QPushButton:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }
            
            QDialogButtonBox QPushButton:pressed {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }
            
            QSpinBox, QComboBox {
                background-color: #ffffff;
                border: 1px solid #e1e1e1;
                padding: 4px 6px;
                color: #1e1e1e;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
                border-radius: 3px;
                min-height: 20px;
            }
            
            QCheckBox {
                color: #1e1e1e;
                font-size: 13px;
                spacing: 6px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                min-height: 20px;
            }
            
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #e1e1e1;
                border-radius: 2px;
                background-color: #ffffff;
            }
            
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border: 1px solid #0078d4;
            }
            
            QDialogButtonBox QPushButton {
                background-color: #fdfdfd;
                color: #000000;
                border: 1px solid #d5d5d5;
                border-radius: 3px;
                padding: 4px 8px;
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                font-size: 13px;
                min-height: 20px;
                min-width: 50px;
            }
            
            QDialogButtonBox QPushButton:hover {
                background-color: #cce4f7;
                border: 1px solid #2670ad;
            }
            
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #c1c1c1;
                min-height: 20px;
                border-radius: 6px;
                border: none;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #a8a8a8;
            }
        """)
        
        # 创建主布局
        layout = QVBoxLayout()
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        
        # 添加各个设置页面
        self.tab_widget.addTab(self.create_basic_tab(), "基本设置")
        self.tab_widget.addTab(self.create_download_tab(), "下载设置")
        self.tab_widget.addTab(self.create_interface_tab(), "界面设置")
        self.tab_widget.addTab(self.create_advanced_tab(), "高级设置")
        
        layout.addWidget(self.tab_widget)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        # 重置按钮
        reset_button = QPushButton("重置默认")
        reset_button.setFont(QFont("Microsoft YaHei", 11))
        reset_button.setFixedSize(80, 24)
        reset_button.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_button)
        
        button_layout.addStretch()
        
        # 标准对话框按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        
        # 设置按钮中文文本
        button_box.button(QDialogButtonBox.Ok).setText("确定")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        button_box.button(QDialogButtonBox.Apply).setText("应用")
        
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_scrollable_tab(self, content_widget: QWidget) -> QWidget:
        """创建可滚动的标签页"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidget(content_widget)
        scroll_area.setWidgetResizable(True)
        
        # 设置滚动条策略：水平滚动条根据需要显示，垂直滚动条始终显示
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 设置滚动区域的最小大小，确保有足够空间显示内容
        scroll_area.setMinimumSize(650, 600)  # 增加高度以容纳更多内容
        
        # 设置内容控件的最小大小策略，确保内容能够完整显示
        content_widget.setMinimumSize(600, 550)  # 增加高度以容纳更多内容
        
        # 应用滚动条样式，与界面设置保持一致
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
                margin: 0px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #c1c1c1;
                min-height: 20px;
                border-radius: 6px;
                border: none;
                margin: 0px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #a8a8a8;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background-color: transparent;
                border: none;
            }
            
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background-color: transparent;
                border: none;
            }
            
            QScrollBar:horizontal {
                background-color: #f0f0f0;
                height: 12px;
                border-radius: 6px;
                margin: 0px;
            }
            
            QScrollBar::handle:horizontal {
                background-color: #c1c1c1;
                min-width: 20px;
                border-radius: 6px;
                border: none;
                margin: 0px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background-color: #a8a8a8;
            }
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background-color: transparent;
                border: none;
            }
            
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background-color: transparent;
                border: none;
            }
        """)
        
        return scroll_area
        
    def create_basic_tab(self) -> QWidget:
        """创建基本设置页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 下载路径设置
        path_group = QGroupBox("下载路径")
        path_layout = QFormLayout()
        
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setPlaceholderText("选择默认下载路径")
        
        self.browse_path_button = QPushButton("浏览...")
        self.browse_path_button.setFont(QFont("Microsoft YaHei", 11))  # 统一使用微软雅黑字体
        self.browse_path_button.setFixedSize(60, 24)  # 与反馈页面按钮保持一致
        self.browse_path_button.clicked.connect(self.browse_save_path)
        
        path_button_layout = QHBoxLayout()
        path_button_layout.addWidget(self.save_path_edit)
        path_button_layout.addWidget(self.browse_path_button)
        
        path_layout.addRow("默认保存路径:", path_button_layout)
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)
        
        # 文件命名设置
        naming_group = QGroupBox("文件命名")
        naming_layout = QFormLayout()
        
        self.filename_template = QLineEdit()
        self.filename_template.setPlaceholderText("%(title)s_%(id)s.%(ext)s")
        naming_layout.addRow("文件名模板:", self.filename_template)
        
        self.auto_rename = QCheckBox("自动重命名重复文件")
        naming_layout.addRow("", self.auto_rename)
        
        naming_group.setLayout(naming_layout)
        layout.addWidget(naming_group)
        
        # 后台运行设置
        background_group = QGroupBox("后台运行")
        background_layout = QFormLayout()
        
        # 后台运行设置已迁移到高级设置页面的高级选项组
        
        background_group.setLayout(background_layout)
        layout.addWidget(background_group)
        
        # 日志设置
        log_group = QGroupBox("日志设置")
        log_layout = QFormLayout()
        
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level.setCurrentText("INFO")
        self.log_level.setFixedHeight(30)  # 固定高度为30px
        log_layout.addRow("日志级别:", self.log_level)
        
        self.auto_clear_log = QCheckBox("自动清理旧日志")
        self.auto_clear_log.setFixedHeight(30)  # 固定高度为30px
        log_layout.addRow("", self.auto_clear_log)
        
        self.log_retention_days = QSpinBox()
        self.log_retention_days.setRange(1, 365)
        self.log_retention_days.setValue(30)
        self.log_retention_days.setSuffix(" 天")
        self.log_retention_days.setFixedHeight(30)  # 固定高度为30px
        log_layout.addRow("日志保留天数:", self.log_retention_days)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        widget.setLayout(layout)
        return widget
        
    def create_download_tab(self) -> QWidget:
        """创建下载设置页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 下载控制设置
        control_group = QGroupBox("下载控制")
        control_layout = QFormLayout()
        
        self.max_concurrent = QSpinBox()
        self.max_concurrent.setRange(1, 10)
        self.max_concurrent.setValue(3)
        control_layout.addRow("最大并发下载数:", self.max_concurrent)
        
        self.speed_limit = QSpinBox()
        self.speed_limit.setRange(0, 10000)
        self.speed_limit.setSuffix(" KB/s")
        self.speed_limit.setSpecialValueText("无限制")
        control_layout.addRow("下载速度限制:", self.speed_limit)
        
        self.retry_count = QSpinBox()
        self.retry_count.setRange(0, 10)
        self.retry_count.setValue(3)
        control_layout.addRow("重试次数:", self.retry_count)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 格式设置
        format_group = QGroupBox("格式设置")
        format_layout = QFormLayout()
        
        self.default_format = QComboBox()
        self.default_format.addItems(["mp4", "mkv", "webm"])
        format_layout.addRow("默认输出格式:", self.default_format)
        
        self.auto_merge = QCheckBox("自动合并视频和音频")
        self.auto_merge.setChecked(True)
        format_layout.addRow("", self.auto_merge)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        widget.setLayout(layout)
        return widget
        
    def create_interface_tab(self) -> QWidget:
        """创建界面设置页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 外观设置
        appearance_group = QGroupBox("外观")
        appearance_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色主题", "深色主题", "跟随系统"])
        appearance_layout.addRow("主题:", self.theme_combo)
        
        self.font_size = QSpinBox()
        self.font_size.setRange(10, 20)
        self.font_size.setValue(13)
        self.font_size.setSuffix(" px")
        appearance_layout.addRow("字体大小:", self.font_size)
        
        self.auto_hide_progress = QCheckBox("下载完成后自动隐藏进度条")
        appearance_layout.addRow("", self.auto_hide_progress)
        
        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)
        
        # 通知设置
        notification_group = QGroupBox("通知")
        notification_layout = QFormLayout()
        
        self.show_completion_dialog = QCheckBox("下载完成后显示对话框")
        self.show_completion_dialog.setChecked(True)
        notification_layout.addRow("", self.show_completion_dialog)
        
        self.play_sound = QCheckBox("下载完成时播放提示音")
        notification_layout.addRow("", self.play_sound)
        
        notification_group.setLayout(notification_layout)
        layout.addWidget(notification_group)
        
        widget.setLayout(layout)
        return widget
        
    def create_advanced_tab(self) -> QWidget:
        """创建高级设置页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # FFmpeg设置
        ffmpeg_group = QGroupBox("FFmpeg设置")
        ffmpeg_group.setMinimumHeight(80)  # 减少最小高度，减少空白空间
        ffmpeg_layout = QFormLayout()
        ffmpeg_layout.setSpacing(8)  # 减少表单项间距，紧凑布局
        
        self.ffmpeg_path_edit = QLineEdit()
        self.ffmpeg_path_edit.setPlaceholderText("FFmpeg可执行文件路径")
        self.ffmpeg_path_edit.setFixedHeight(36)  # 增加高度到36px，确保提示文字完全显示
        self.browse_ffmpeg_button = QPushButton("浏览...")
        self.browse_ffmpeg_button.setFont(QFont("Microsoft YaHei", 11))  # 统一使用微软雅黑字体
        self.browse_ffmpeg_button.setFixedSize(60, 24)  # 与反馈页面按钮保持一致
        self.browse_ffmpeg_button.clicked.connect(self.browse_ffmpeg_path)
        
        ffmpeg_button_layout = QHBoxLayout()
        ffmpeg_button_layout.addWidget(self.ffmpeg_path_edit)
        ffmpeg_button_layout.addWidget(self.browse_ffmpeg_button)
        
        ffmpeg_layout.addRow("FFmpeg路径:", ffmpeg_button_layout)
        
        ffmpeg_group.setLayout(ffmpeg_layout)
        layout.addWidget(ffmpeg_group)
        
        # 网络设置
        network_group = QGroupBox("网络设置")
        network_group.setMinimumHeight(120)  # 减少最小高度，紧凑布局
        network_layout = QFormLayout()
        network_layout.setSpacing(10)  # 减少表单项间距，紧凑布局
        
        self.proxy_enabled = QCheckBox("启用代理")
        self.proxy_enabled.setFixedHeight(30)  # 固定高度为30px
        network_layout.addRow("", self.proxy_enabled)
        
        self.proxy_url = QLineEdit()
        self.proxy_url.setPlaceholderText("http://proxy:port")
        self.proxy_url.setFixedHeight(36)  # 增加高度到36px，确保提示文字完全显示
        network_layout.addRow("代理地址:", self.proxy_url)
        
        self.user_agent = QLineEdit()
        self.user_agent.setPlaceholderText("自定义User-Agent")
        self.user_agent.setFixedHeight(36)  # 增加高度到36px，确保提示文字完全显示
        network_layout.addRow("User-Agent:", self.user_agent)
        
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        # 高级选项设置
        advanced_options_group = QGroupBox("高级选项")
        advanced_options_group.setMinimumHeight(120)  # 两列布局更紧凑，减少高度
        advanced_options_layout = QVBoxLayout()
        advanced_options_layout.setSpacing(10)  # 减少表单项间距，紧凑布局
        
        # 创建两列布局
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)  # 两列之间的间距
        
        # 左列：2个设置项
        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        
        self.enable_debug_mode = QCheckBox("启用调试模式")
        self.enable_debug_mode.setToolTip("启用后将显示详细的调试信息")
        self.enable_debug_mode.setFixedHeight(30)  # 固定高度为30px
        left_column.addWidget(self.enable_debug_mode)
        
        self.remember_window_position = QCheckBox("记住窗口位置")
        self.remember_window_position.setChecked(True)
        self.remember_window_position.setToolTip("下次启动时恢复上次的窗口位置和大小")
        self.remember_window_position.setFixedHeight(30)  # 固定高度为30px
        left_column.addWidget(self.remember_window_position)
        
        # 右列：2个设置项，与左列完全对齐
        right_column = QVBoxLayout()
        right_column.setSpacing(10)
        
        # 后台运行设置
        self.minimize_to_tray = QCheckBox("关闭时最小化到系统托盘")
        self.minimize_to_tray.setToolTip("启用后，关闭程序时会最小化到系统托盘而不是完全退出")
        self.minimize_to_tray.setFixedHeight(30)  # 固定高度为30px
        right_column.addWidget(self.minimize_to_tray)
        
        self.start_minimized = QCheckBox("启动时最小化到系统托盘")
        self.start_minimized.setToolTip("启用后，程序启动时会直接最小化到系统托盘")
        self.start_minimized.setFixedHeight(30)  # 固定高度为30px
        right_column.addWidget(self.start_minimized)
        
        # 将两列添加到水平布局中，确保对齐
        columns_layout.addLayout(left_column)
        columns_layout.addLayout(right_column)
        
        # 将两列布局添加到主布局中
        advanced_options_layout.addLayout(columns_layout)
        
        advanced_options_group.setLayout(advanced_options_layout)
        layout.addWidget(advanced_options_group)
        
        widget.setLayout(layout)
        return widget
        
    def browse_save_path(self) -> None:
        """浏览保存路径"""
        folder = QFileDialog.getExistingDirectory(
            self, "选择默认下载路径", self.save_path_edit.text()
        )
        if folder:
            self.save_path_edit.setText(folder)
            
    def browse_ffmpeg_path(self) -> None:
        """浏览FFmpeg路径"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择FFmpeg可执行文件", "", "可执行文件 (*.exe);;所有文件 (*)"
        )
        if file_path:
            self.ffmpeg_path_edit.setText(file_path)
            

            
    def detect_ffmpeg(self) -> None:
        """检测FFmpeg状态（简化版本）"""
        try:
            from ..core.ffmpeg_manager import FFmpegManager
            ffmpeg_manager = FFmpegManager()
            
            # 检测FFmpeg状态
            method, path, version = ffmpeg_manager.get_ffmpeg_status()
            
            if method and path:
                # 如果检测到FFmpeg，自动设置路径
                if method == "system" and path:
                    self.ffmpeg_path_edit.setText(path)
                    
        except Exception as e:
            logger.error(f"FFmpeg检测失败: {e}")
            
    def load_settings(self) -> None:
        """加载设置"""
        try:
            # 基本设置
            self.save_path_edit.setText(self.settings.value("save_path", os.getcwd()))
            self.filename_template.setText(self.settings.value("filename_template", "%(title)s_%(id)s.%(ext)s"))
            self.auto_rename.setChecked(self.settings.value("auto_rename", True, type=bool))
            
            # 后台运行设置
            self.minimize_to_tray.setChecked(self.settings.value("minimize_to_tray", False, type=bool))
            self.start_minimized.setChecked(self.settings.value("start_minimized", False, type=bool))
            
            # 下载设置
            self.max_concurrent.setValue(self.settings.value("max_concurrent", 3, type=int))
            self.speed_limit.setValue(self.settings.value("speed_limit", 0, type=int))
            self.retry_count.setValue(self.settings.value("retry_count", 3, type=int))
            self.default_format.setCurrentText(self.settings.value("default_format", "mp4"))
            self.auto_merge.setChecked(self.settings.value("auto_merge", True, type=bool))
            
            # 界面设置
            theme_index = self.settings.value("theme", 0, type=int)
            self.theme_combo.setCurrentIndex(theme_index)
            self.font_size.setValue(self.settings.value("font_size", 13, type=int))
            self.auto_hide_progress.setChecked(self.settings.value("auto_hide_progress", False, type=bool))
            self.show_completion_dialog.setChecked(self.settings.value("show_completion_dialog", True, type=bool))
            self.play_sound.setChecked(self.settings.value("play_sound", False, type=bool))
            
            # 高级设置
            self.ffmpeg_path_edit.setText(self.settings.value("ffmpeg_path", ""))
            self.proxy_enabled.setChecked(self.settings.value("proxy_enabled", False, type=bool))
            self.proxy_url.setText(self.settings.value("proxy_url", ""))
            self.user_agent.setText(self.settings.value("user_agent", ""))
            self.log_level.setCurrentText(self.settings.value("log_level", "INFO"))
            self.auto_clear_log.setChecked(self.settings.value("auto_clear_log", False, type=bool))
            self.log_retention_days.setValue(self.settings.value("log_retention_days", 30, type=int))
            
            # 高级选项设置
            self.enable_debug_mode.setChecked(self.settings.value("enable_debug_mode", False, type=bool))
            self.remember_window_position.setChecked(self.settings.value("remember_window_position", True, type=bool))
            
        except Exception as e:
            logger.error(f"加载设置失败: {str(e)}")
            
    def save_settings(self) -> None:
        """保存设置"""
        try:
            # 基本设置
            self.settings.setValue("save_path", self.save_path_edit.text())
            self.settings.setValue("filename_template", self.filename_template.text())
            self.settings.setValue("auto_rename", self.auto_rename.isChecked())
            
            # 后台运行设置
            self.settings.setValue("minimize_to_tray", self.minimize_to_tray.isChecked())
            self.settings.setValue("start_minimized", self.start_minimized.isChecked())
            
            # 下载设置
            self.settings.setValue("max_concurrent", self.max_concurrent.value())
            self.settings.setValue("speed_limit", self.speed_limit.value())
            self.settings.setValue("retry_count", self.retry_count.value())
            self.settings.setValue("default_format", self.default_format.currentText())
            self.settings.setValue("auto_merge", self.auto_merge.isChecked())
            
            # 界面设置
            self.settings.setValue("theme", self.theme_combo.currentIndex())
            self.settings.setValue("font_size", self.font_size.value())
            self.settings.setValue("auto_hide_progress", self.auto_hide_progress.isChecked())
            self.settings.setValue("show_completion_dialog", self.show_completion_dialog.isChecked())
            self.settings.setValue("play_sound", self.play_sound.isChecked())
            
            # 高级设置
            self.settings.setValue("ffmpeg_path", self.ffmpeg_path_edit.text())
            self.settings.setValue("proxy_enabled", self.proxy_enabled.isChecked())
            self.settings.setValue("proxy_url", self.proxy_url.text())
            self.settings.setValue("user_agent", self.user_agent.text())
            self.settings.setValue("log_level", self.log_level.currentText())
            self.settings.setValue("auto_clear_log", self.auto_clear_log.isChecked())
            self.settings.setValue("log_retention_days", self.log_retention_days.value())
            
            # 高级选项设置
            self.settings.setValue("enable_debug_mode", self.enable_debug_mode.isChecked())
            self.settings.setValue("remember_window_position", self.remember_window_position.isChecked())
            
            self.settings.sync()
            logger.info("设置已保存")
            
        except Exception as e:
            logger.error(f"保存设置失败: {str(e)}")
            
    def apply_settings(self) -> None:
        """应用设置"""
        self.save_settings()
        QMessageBox.information(self, "成功", "设置已保存")
        
    def reset_to_defaults(self) -> None:
        """重置为默认设置"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("确认重置")
        msg_box.setText("是否要重置所有设置为默认值？")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        # 设置按钮中文文本
        msg_box.button(QMessageBox.Yes).setText("是")
        msg_box.button(QMessageBox.No).setText("否")
        reply = msg_box.exec_()
        
        if reply == QMessageBox.Yes:
            self.settings.clear()
            self.load_settings()
            QMessageBox.information(self, "成功", "设置已重置为默认值")
            
    def accept(self) -> None:
        """确认设置"""
        self.save_settings()
        super().accept()
        
    def get_settings_dict(self) -> Dict[str, Any]:
        """获取设置字典"""
        return {
            "save_path": self.save_path_edit.text(),
            "filename_template": self.filename_template.text(),
            "auto_rename": self.auto_rename.isChecked(),
            "max_concurrent": self.max_concurrent.value(),
            "speed_limit": self.speed_limit.value(),
            "retry_count": self.retry_count.value(),
            "default_format": self.default_format.currentText(),
            "auto_merge": self.auto_merge.isChecked(),
            "theme": self.theme_combo.currentIndex(),
            "font_size": self.font_size.value(),
            "auto_hide_progress": self.auto_hide_progress.isChecked(),
            "show_completion_dialog": self.show_completion_dialog.isChecked(),
            "play_sound": self.play_sound.isChecked(),
            "ffmpeg_path": self.ffmpeg_path_edit.text(),
            "proxy_enabled": self.proxy_enabled.isChecked(),
            "proxy_url": self.proxy_url.text(),
            "user_agent": self.user_agent.text(),
            "log_level": self.log_level.currentText(),
            "auto_clear_log": self.auto_clear_log.isChecked(),
            "log_retention_days": self.log_retention_days.value(),
            "enable_debug_mode": self.enable_debug_mode.isChecked(),

            "remember_window_position": self.remember_window_position.isChecked(),
        }
