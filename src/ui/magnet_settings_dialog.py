"""
磁力下载设置对话框模块

该模块定义了磁力下载的设置对话框，允许用户配置：
- DHT网络设置
- 端口配置
- 连接限制
- 下载速度限制
- 上传速度限制

主要类：
- MagnetSettingsDialog: 磁力下载设置对话框

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


class MagnetSettingsDialog(QDialog):
    """磁力下载设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("MyCompany", "VideoDownloader")
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("磁力下载设置")
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
        
        # 启用磁力下载
        enable_group = QGroupBox("功能启用")
        enable_layout = QFormLayout()
        
        self.enable_magnet_checkbox = QCheckBox("启用磁力下载功能")
        self.enable_magnet_checkbox.setToolTip("启用或禁用磁力链接下载功能")
        enable_layout.addRow(self.enable_magnet_checkbox)
        
        enable_group.setLayout(enable_layout)
        layout.addWidget(enable_group)
        
        # 下载设置
        download_group = QGroupBox("下载设置")
        download_layout = QFormLayout()
        
        self.download_timeout_spinbox = QSpinBox()
        self.download_timeout_spinbox.setRange(60, 1800)
        self.download_timeout_spinbox.setSuffix(" 秒")
        self.download_timeout_spinbox.setToolTip("磁力下载超时时间")
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
        
        # DHT设置
        dht_group = QGroupBox("DHT网络设置")
        dht_layout = QFormLayout()
        
        self.enable_dht_checkbox = QCheckBox("启用DHT网络")
        self.enable_dht_checkbox.setToolTip("启用分布式哈希表网络，提高磁力链接发现能力")
        dht_layout.addRow(self.enable_dht_checkbox)
        
        self.enable_lsd_checkbox = QCheckBox("启用本地服务发现")
        self.enable_lsd_checkbox.setToolTip("启用本地网络服务发现")
        dht_layout.addRow(self.enable_lsd_checkbox)
        
        dht_group.setLayout(dht_layout)
        layout.addWidget(dht_group)
        
        # 端口映射设置
        port_group = QGroupBox("端口映射设置")
        port_layout = QFormLayout()
        
        self.enable_upnp_checkbox = QCheckBox("启用UPnP端口映射")
        self.enable_upnp_checkbox.setToolTip("自动配置路由器端口映射")
        port_layout.addRow(self.enable_upnp_checkbox)
        
        self.enable_nat_pmp_checkbox = QCheckBox("启用NAT-PMP端口映射")
        self.enable_nat_pmp_checkbox.setToolTip("使用NAT-PMP协议配置端口映射")
        port_layout.addRow(self.enable_nat_pmp_checkbox)
        
        port_group.setLayout(port_layout)
        layout.addWidget(port_group)
        
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
        self.max_connections_spinbox.setRange(10, 1000)
        self.max_connections_spinbox.setToolTip("每个种子的最大连接数")
        connection_layout.addRow("最大连接数:", self.max_connections_spinbox)
        
        self.max_uploads_spinbox = QSpinBox()
        self.max_uploads_spinbox.setRange(1, 100)
        self.max_uploads_spinbox.setToolTip("每个种子的最大上传数")
        connection_layout.addRow("最大上传数:", self.max_uploads_spinbox)
        
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
            self.enable_magnet_checkbox.setChecked(
                self.settings.value("magnet/enabled", Config.MAGNET_DOWNLOAD_ENABLED, type=bool)
            )
            self.download_timeout_spinbox.setValue(
                self.settings.value("magnet/download_timeout", Config.MAGNET_DOWNLOAD_TIMEOUT, type=int)
            )
            self.progress_interval_spinbox.setValue(
                self.settings.value("magnet/progress_interval", Config.MAGNET_PROGRESS_UPDATE_INTERVAL, type=float)
            )
            
            # 网络设置
            self.enable_dht_checkbox.setChecked(
                self.settings.value("magnet/dht_enabled", Config.MAGNET_DHT_ENABLED, type=bool)
            )
            self.enable_lsd_checkbox.setChecked(
                self.settings.value("magnet/lsd_enabled", Config.MAGNET_LSD_ENABLED, type=bool)
            )
            self.enable_upnp_checkbox.setChecked(
                self.settings.value("magnet/upnp_enabled", Config.MAGNET_UPNP_ENABLED, type=bool)
            )
            self.enable_nat_pmp_checkbox.setChecked(
                self.settings.value("magnet/nat_pmp_enabled", Config.MAGNET_NAT_PMP_ENABLED, type=bool)
            )
            
            # 高级设置
            self.max_connections_spinbox.setValue(
                self.settings.value("magnet/max_connections", Config.MAGNET_MAX_CONNECTIONS, type=int)
            )
            self.max_uploads_spinbox.setValue(
                self.settings.value("magnet/max_uploads", Config.MAGNET_MAX_UPLOADS, type=int)
            )
            self.download_speed_spinbox.setValue(
                self.settings.value("magnet/download_speed_limit", 0, type=int)
            )
            self.upload_speed_spinbox.setValue(
                self.settings.value("magnet/upload_speed_limit", 0, type=int)
            )
            
        except Exception as e:
            print(f"加载磁力下载设置失败: {e}")
    
    def save_settings(self):
        """保存设置"""
        try:
            # 基本设置
            self.settings.setValue("magnet/enabled", self.enable_magnet_checkbox.isChecked())
            self.settings.setValue("magnet/download_timeout", self.download_timeout_spinbox.value())
            self.settings.setValue("magnet/progress_interval", self.progress_interval_spinbox.value())
            
            # 网络设置
            self.settings.setValue("magnet/dht_enabled", self.enable_dht_checkbox.isChecked())
            self.settings.setValue("magnet/lsd_enabled", self.enable_lsd_checkbox.isChecked())
            self.settings.setValue("magnet/upnp_enabled", self.enable_upnp_checkbox.isChecked())
            self.settings.setValue("magnet/nat_pmp_enabled", self.enable_nat_pmp_checkbox.isChecked())
            
            # 高级设置
            self.settings.setValue("magnet/max_connections", self.max_connections_spinbox.value())
            self.settings.setValue("magnet/max_uploads", self.max_uploads_spinbox.value())
            self.settings.setValue("magnet/download_speed_limit", self.download_speed_spinbox.value())
            self.settings.setValue("magnet/upload_speed_limit", self.upload_speed_spinbox.value())
            
            # 同步到配置
            Config.MAGNET_DOWNLOAD_ENABLED = self.enable_magnet_checkbox.isChecked()
            Config.MAGNET_DHT_ENABLED = self.enable_dht_checkbox.isChecked()
            Config.MAGNET_LSD_ENABLED = self.enable_lsd_checkbox.isChecked()
            Config.MAGNET_UPNP_ENABLED = self.enable_upnp_checkbox.isChecked()
            Config.MAGNET_NAT_PMP_ENABLED = self.enable_nat_pmp_checkbox.isChecked()
            Config.MAGNET_MAX_CONNECTIONS = self.max_connections_spinbox.value()
            Config.MAGNET_MAX_UPLOADS = self.max_uploads_spinbox.value()
            Config.MAGNET_DOWNLOAD_TIMEOUT = self.download_timeout_spinbox.value()
            Config.MAGNET_PROGRESS_UPDATE_INTERVAL = self.progress_interval_spinbox.value()
            
            self.settings.sync()
            
        except Exception as e:
            print(f"保存磁力下载设置失败: {e}")
    
    def reset_to_defaults(self):
        """重置为默认设置"""
        try:
            reply = QMessageBox.question(
                self, 
                "确认重置", 
                "确定要重置所有磁力下载设置为默认值吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 重置为默认值
                self.enable_magnet_checkbox.setChecked(Config.MAGNET_DOWNLOAD_ENABLED)
                self.download_timeout_spinbox.setValue(Config.MAGNET_DOWNLOAD_TIMEOUT)
                self.progress_interval_spinbox.setValue(Config.MAGNET_PROGRESS_UPDATE_INTERVAL)
                self.enable_dht_checkbox.setChecked(Config.MAGNET_DHT_ENABLED)
                self.enable_lsd_checkbox.setChecked(Config.MAGNET_LSD_ENABLED)
                self.enable_upnp_checkbox.setChecked(Config.MAGNET_UPNP_ENABLED)
                self.enable_nat_pmp_checkbox.setChecked(Config.MAGNET_NAT_PMP_ENABLED)
                self.max_connections_spinbox.setValue(Config.MAGNET_MAX_CONNECTIONS)
                self.max_uploads_spinbox.setValue(Config.MAGNET_MAX_UPLOADS)
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
            'enabled': self.enable_magnet_checkbox.isChecked(),
            'download_timeout': self.download_timeout_spinbox.value(),
            'progress_interval': self.progress_interval_spinbox.value(),
            'dht_enabled': self.enable_dht_checkbox.isChecked(),
            'lsd_enabled': self.enable_lsd_checkbox.isChecked(),
            'upnp_enabled': self.enable_upnp_checkbox.isChecked(),
            'nat_pmp_enabled': self.enable_nat_pmp_checkbox.isChecked(),
            'max_connections': self.max_connections_spinbox.value(),
            'max_uploads': self.max_uploads_spinbox.value(),
            'download_speed_limit': self.download_speed_spinbox.value(),
            'upload_speed_limit': self.upload_speed_spinbox.value(),
        }
