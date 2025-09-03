"""
ED2K下载设置对话框模块

该模块定义了ED2K下载的设置对话框，允许用户配置：
- 网络连接设置
- 端口配置
- 连接限制
- 下载速度限制
- 上传速度限制

主要类：
- ED2KSettingsDialog: ED2K下载设置对话框

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import os
from typing import Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QCheckBox, QSpinBox, QPushButton, QGroupBox, QFormLayout,
    QMessageBox, QTabWidget, QWidget, QSlider, QComboBox
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont, QIcon

from ..core.config import Config


class ED2KSettingsDialog(QDialog):
    """ED2K下载设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("MyCompany", "VideoDownloader")
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("ED2K下载设置")
        self.setFixedSize(600, 500)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QLineEdit, QSpinBox, QComboBox {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 6px;
                background-color: #ffffff;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border-color: #0078d4;
            }
        """)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 基本设置标签页
        basic_tab = self.create_basic_settings_tab()
        tab_widget.addTab(basic_tab, "基本设置")
        
        # 网络设置标签页
        network_tab = self.create_network_settings_tab()
        tab_widget.addTab(network_tab, "网络设置")
        
        # 高级设置标签页
        advanced_tab = self.create_advanced_settings_tab()
        tab_widget.addTab(advanced_tab, "高级设置")
        
        main_layout.addWidget(tab_widget)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 重置按钮
        reset_button = QPushButton("重置默认")
        reset_button.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_button)
        
        # 确定按钮
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def create_basic_settings_tab(self) -> QWidget:
        """创建基本设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 启用ED2K下载
        enable_group = QGroupBox("功能启用")
        enable_layout = QFormLayout()
        
        self.enable_ed2k_checkbox = QCheckBox("启用ED2K下载功能")
        self.enable_ed2k_checkbox.setToolTip("启用或禁用ED2K链接下载功能")
        enable_layout.addRow(self.enable_ed2k_checkbox)
        
        enable_group.setLayout(enable_layout)
        layout.addWidget(enable_group)
        
        # 下载设置
        download_group = QGroupBox("下载设置")
        download_layout = QFormLayout()
        
        self.download_timeout_spinbox = QSpinBox()
        self.download_timeout_spinbox.setRange(60, 1800)
        self.download_timeout_spinbox.setSuffix(" 秒")
        self.download_timeout_spinbox.setToolTip("ED2K下载超时时间")
        download_layout.addRow("下载超时时间:", self.download_timeout_spinbox)
        
        self.progress_interval_spinbox = QSpinBox()
        self.progress_interval_spinbox.setRange(1, 10)
        self.progress_interval_spinbox.setSuffix(" 秒")
        self.progress_interval_spinbox.setToolTip("进度更新间隔")
        download_layout.addRow("进度更新间隔:", self.progress_interval_spinbox)
        
        download_group.setLayout(download_layout)
        layout.addWidget(download_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_network_settings_tab(self) -> QWidget:
        """创建网络设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 端口设置
        port_group = QGroupBox("端口设置")
        port_layout = QFormLayout()
        
        self.tcp_port_spinbox = QSpinBox()
        self.tcp_port_spinbox.setRange(1024, 65535)
        self.tcp_port_spinbox.setValue(4662)
        self.tcp_port_spinbox.setToolTip("TCP端口号")
        port_layout.addRow("TCP端口:", self.tcp_port_spinbox)
        
        self.udp_port_spinbox = QSpinBox()
        self.udp_port_spinbox.setRange(1024, 65535)
        self.udp_port_spinbox.setValue(4672)
        self.udp_port_spinbox.setToolTip("UDP端口号")
        port_layout.addRow("UDP端口:", self.udp_port_spinbox)
        
        port_group.setLayout(port_layout)
        layout.addWidget(port_group)
        
        # 网络功能设置
        network_group = QGroupBox("网络功能")
        network_layout = QFormLayout()
        
        self.enable_kad_checkbox = QCheckBox("启用Kademlia DHT")
        self.enable_kad_checkbox.setToolTip("启用分布式哈希表网络，提高文件发现能力")
        network_layout.addRow(self.enable_kad_checkbox)
        
        self.enable_server_checkbox = QCheckBox("启用服务器连接")
        self.enable_server_checkbox.setToolTip("连接到ED2K服务器网络")
        network_layout.addRow(self.enable_server_checkbox)
        
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_advanced_settings_tab(self) -> QWidget:
        """创建高级设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 连接设置
        connection_group = QGroupBox("连接设置")
        connection_layout = QFormLayout()
        
        self.max_connections_spinbox = QSpinBox()
        self.max_connections_spinbox.setRange(10, 500)
        self.max_connections_spinbox.setToolTip("最大连接数")
        connection_layout.addRow("最大连接数:", self.max_connections_spinbox)
        
        self.max_downloads_spinbox = QSpinBox()
        self.max_downloads_spinbox.setRange(1, 20)
        self.max_downloads_spinbox.setToolTip("最大同时下载数")
        connection_layout.addRow("最大下载数:", self.max_downloads_spinbox)
        
        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)
        
        # 速度限制设置
        speed_group = QGroupBox("速度限制")
        speed_layout = QFormLayout()
        
        self.download_speed_spinbox = QSpinBox()
        self.download_speed_spinbox.setRange(0, 100000)
        self.download_speed_spinbox.setSuffix(" KB/s")
        self.download_speed_spinbox.setSpecialValueText("无限制")
        self.download_speed_spinbox.setToolTip("下载速度限制，0表示无限制")
        speed_layout.addRow("下载速度限制:", self.download_speed_spinbox)
        
        self.upload_speed_spinbox = QSpinBox()
        self.upload_speed_spinbox.setRange(0, 100000)
        self.upload_speed_spinbox.setSuffix(" KB/s")
        self.upload_speed_spinbox.setSpecialValueText("无限制")
        self.upload_speed_spinbox.setToolTip("上传速度限制，0表示无限制")
        speed_layout.addRow("上传速度限制:", self.upload_speed_spinbox)
        
        speed_group.setLayout(speed_layout)
        layout.addWidget(speed_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def load_settings(self):
        """加载设置"""
        try:
            # 基本设置
            self.enable_ed2k_checkbox.setChecked(
                self.settings.value("ed2k/enabled", Config.ED2K_DOWNLOAD_ENABLED, type=bool)
            )
            self.download_timeout_spinbox.setValue(
                self.settings.value("ed2k/download_timeout", Config.ED2K_DOWNLOAD_TIMEOUT, type=int)
            )
            self.progress_interval_spinbox.setValue(
                int(self.settings.value("ed2k/progress_interval", Config.ED2K_PROGRESS_UPDATE_INTERVAL, type=float))
            )
            
            # 网络设置
            self.tcp_port_spinbox.setValue(
                self.settings.value("ed2k/tcp_port", 4662, type=int)
            )
            self.udp_port_spinbox.setValue(
                self.settings.value("ed2k/udp_port", 4672, type=int)
            )
            self.enable_kad_checkbox.setChecked(
                self.settings.value("ed2k/kad_enabled", Config.ED2K_KAD_ENABLED, type=bool)
            )
            self.enable_server_checkbox.setChecked(
                self.settings.value("ed2k/server_enabled", Config.ED2K_SERVER_ENABLED, type=bool)
            )
            
            # 高级设置
            self.max_connections_spinbox.setValue(
                self.settings.value("ed2k/max_connections", Config.ED2K_MAX_CONNECTIONS, type=int)
            )
            self.max_downloads_spinbox.setValue(
                self.settings.value("ed2k/max_downloads", Config.ED2K_MAX_DOWNLOADS, type=int)
            )
            self.download_speed_spinbox.setValue(
                self.settings.value("ed2k/download_speed_limit", 0, type=int)
            )
            self.upload_speed_spinbox.setValue(
                self.settings.value("ed2k/upload_speed_limit", 0, type=int)
            )
            
        except Exception as e:
            print(f"加载ED2K下载设置失败: {e}")
    
    def save_settings(self):
        """保存设置"""
        try:
            # 基本设置
            self.settings.setValue("ed2k/enabled", self.enable_ed2k_checkbox.isChecked())
            self.settings.setValue("ed2k/download_timeout", self.download_timeout_spinbox.value())
            self.settings.setValue("ed2k/progress_interval", self.progress_interval_spinbox.value())
            
            # 网络设置
            self.settings.setValue("ed2k/tcp_port", self.tcp_port_spinbox.value())
            self.settings.setValue("ed2k/udp_port", self.udp_port_spinbox.value())
            self.settings.setValue("ed2k/kad_enabled", self.enable_kad_checkbox.isChecked())
            self.settings.setValue("ed2k/server_enabled", self.enable_server_checkbox.isChecked())
            
            # 高级设置
            self.settings.setValue("ed2k/max_connections", self.max_connections_spinbox.value())
            self.settings.setValue("ed2k/max_downloads", self.max_downloads_spinbox.value())
            self.settings.setValue("ed2k/download_speed_limit", self.download_speed_spinbox.value())
            self.settings.setValue("ed2k/upload_speed_limit", self.upload_speed_spinbox.value())
            
            # 同步到配置
            Config.ED2K_DOWNLOAD_ENABLED = self.enable_ed2k_checkbox.isChecked()
            Config.ED2K_KAD_ENABLED = self.enable_kad_checkbox.isChecked()
            Config.ED2K_SERVER_ENABLED = self.enable_server_checkbox.isChecked()
            Config.ED2K_MAX_CONNECTIONS = self.max_connections_spinbox.value()
            Config.ED2K_MAX_DOWNLOADS = self.max_downloads_spinbox.value()
            Config.ED2K_DOWNLOAD_TIMEOUT = self.download_timeout_spinbox.value()
            Config.ED2K_PROGRESS_UPDATE_INTERVAL = self.progress_interval_spinbox.value()
            
            self.settings.sync()
            
        except Exception as e:
            print(f"保存ED2K下载设置失败: {e}")
    
    def reset_to_defaults(self):
        """重置为默认设置"""
        try:
            reply = QMessageBox.question(
                self, 
                "确认重置", 
                "确定要重置所有ED2K下载设置为默认值吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 重置为默认值
                self.enable_ed2k_checkbox.setChecked(Config.ED2K_DOWNLOAD_ENABLED)
                self.download_timeout_spinbox.setValue(Config.ED2K_DOWNLOAD_TIMEOUT)
                self.progress_interval_spinbox.setValue(Config.ED2K_PROGRESS_UPDATE_INTERVAL)
                self.tcp_port_spinbox.setValue(4662)
                self.udp_port_spinbox.setValue(4672)
                self.enable_kad_checkbox.setChecked(Config.ED2K_KAD_ENABLED)
                self.enable_server_checkbox.setChecked(Config.ED2K_SERVER_ENABLED)
                self.max_connections_spinbox.setValue(Config.ED2K_MAX_CONNECTIONS)
                self.max_downloads_spinbox.setValue(Config.ED2K_MAX_DOWNLOADS)
                self.download_speed_spinbox.setValue(0)
                self.upload_speed_spinbox.setValue(0)
                
                QMessageBox.information(self, "重置完成", "设置已重置为默认值")
                
        except Exception as e:
            QMessageBox.critical(self, "重置失败", f"重置设置失败: {e}")
    
    def accept(self):
        """确认设置"""
        try:
            self.save_settings()
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存设置失败: {e}")
    
    def get_settings(self) -> Dict[str, Any]:
        """获取当前设置"""
        return {
            'enabled': self.enable_ed2k_checkbox.isChecked(),
            'download_timeout': self.download_timeout_spinbox.value(),
            'progress_interval': self.progress_interval_spinbox.value(),
            'tcp_port': self.tcp_port_spinbox.value(),
            'udp_port': self.udp_port_spinbox.value(),
            'kad_enabled': self.enable_kad_checkbox.isChecked(),
            'server_enabled': self.enable_server_checkbox.isChecked(),
            'max_connections': self.max_connections_spinbox.value(),
            'max_downloads': self.max_downloads_spinbox.value(),
            'download_speed_limit': self.download_speed_spinbox.value(),
            'upload_speed_limit': self.upload_speed_spinbox.value(),
        }
