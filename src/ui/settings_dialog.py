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
    QSlider, QTextEdit, QDialogButtonBox
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
        
    def init_ui(self) -> None:
        """初始化用户界面"""
        self.setWindowTitle("设置")
        self.setGeometry(200, 200, 600, 500)
        self.setModal(True)
        
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
        
        layout.addStretch()
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
        
        layout.addStretch()
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
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
        
    def create_advanced_tab(self) -> QWidget:
        """创建高级设置页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # FFmpeg设置
        ffmpeg_group = QGroupBox("FFmpeg设置")
        ffmpeg_layout = QFormLayout()
        
        self.ffmpeg_path_edit = QLineEdit()
        self.ffmpeg_path_edit.setPlaceholderText("FFmpeg可执行文件路径")
        self.browse_ffmpeg_button = QPushButton("浏览...")
        self.browse_ffmpeg_button.clicked.connect(self.browse_ffmpeg_path)
        
        ffmpeg_button_layout = QHBoxLayout()
        ffmpeg_button_layout.addWidget(self.ffmpeg_path_edit)
        ffmpeg_button_layout.addWidget(self.browse_ffmpeg_button)
        
        ffmpeg_layout.addRow("FFmpeg路径:", ffmpeg_button_layout)
        ffmpeg_group.setLayout(ffmpeg_layout)
        layout.addWidget(ffmpeg_group)
        
        # 网络设置
        network_group = QGroupBox("网络设置")
        network_layout = QFormLayout()
        
        self.proxy_enabled = QCheckBox("启用代理")
        network_layout.addRow("", self.proxy_enabled)
        
        self.proxy_url = QLineEdit()
        self.proxy_url.setPlaceholderText("http://proxy:port")
        network_layout.addRow("代理地址:", self.proxy_url)
        
        self.user_agent = QLineEdit()
        self.user_agent.setPlaceholderText("自定义User-Agent")
        network_layout.addRow("User-Agent:", self.user_agent)
        
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        # 日志设置
        log_group = QGroupBox("日志设置")
        log_layout = QFormLayout()
        
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level.setCurrentText("INFO")
        log_layout.addRow("日志级别:", self.log_level)
        
        self.auto_clear_log = QCheckBox("自动清理旧日志")
        log_layout.addRow("", self.auto_clear_log)
        
        self.log_retention_days = QSpinBox()
        self.log_retention_days.setRange(1, 365)
        self.log_retention_days.setValue(30)
        self.log_retention_days.setSuffix(" 天")
        log_layout.addRow("日志保留天数:", self.log_retention_days)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        layout.addStretch()
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
            
    def load_settings(self) -> None:
        """加载设置"""
        try:
            # 基本设置
            self.save_path_edit.setText(self.settings.value("save_path", os.getcwd()))
            self.filename_template.setText(self.settings.value("filename_template", "%(title)s_%(id)s.%(ext)s"))
            self.auto_rename.setChecked(self.settings.value("auto_rename", True, type=bool))
            
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
            
        except Exception as e:
            logger.error(f"加载设置失败: {str(e)}")
            
    def save_settings(self) -> None:
        """保存设置"""
        try:
            # 基本设置
            self.settings.setValue("save_path", self.save_path_edit.text())
            self.settings.setValue("filename_template", self.filename_template.text())
            self.settings.setValue("auto_rename", self.auto_rename.isChecked())
            
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
            
            self.settings.sync()
            logger.info("设置已保存")
            
        except Exception as e:
            logger.error(f"保存设置失败: {str(e)}")
            
    def apply_settings(self) -> None:
        """应用设置"""
        self.save_settings()
        QMessageBox.information(self, "成功", "设置已应用")
        
    def reset_to_defaults(self) -> None:
        """重置为默认设置"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("确认重置")
        msg_box.setText("确定要重置所有设置为默认值吗？")
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
        }
