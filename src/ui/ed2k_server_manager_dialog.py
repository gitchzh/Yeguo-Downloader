#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ED2K服务器管理对话框

提供用户友好的界面来管理ED2K服务器列表，包括添加、删除、更新服务器等功能。

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import sys
import time
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QSpinBox, QComboBox, QMessageBox,
    QProgressBar, QGroupBox, QFormLayout, QHeaderView, QTabWidget,
    QTextEdit, QSplitter, QFrame, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QIcon

from src.core.ed2k_servers import get_server_manager, ED2KServerInfo
import logging

logger = logging.getLogger(__name__)

class ServerUpdateWorker(QThread):
    """服务器更新工作线程"""
    progress_updated = pyqtSignal(str)
    update_finished = pyqtSignal(bool, str)
    
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
    
    def run(self):
        try:
            self.progress_updated.emit("正在从网络源更新服务器列表...")
            self.manager.update_servers_from_sources()
            self.update_finished.emit(True, "服务器列表更新完成")
        except Exception as e:
            self.update_finished.emit(False, f"更新失败: {e}")

class ED2KServerManagerDialog(QDialog):
    """ED2K服务器管理对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.server_manager = get_server_manager()
        self.init_ui()
        self.load_servers()
        
        # 设置回调
        self.server_manager.on_server_added = self.on_server_added
        self.server_manager.on_server_removed = self.on_server_removed
        self.server_manager.on_server_updated = self.on_server_updated
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("ED2K服务器管理")
        self.setMinimumSize(800, 600)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 服务器列表标签页
        self.init_server_list_tab(tab_widget)
        
        # 添加服务器标签页
        self.init_add_server_tab(tab_widget)
        
        # 服务器源标签页
        self.init_server_sources_tab(tab_widget)
        
        main_layout.addWidget(tab_widget)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新列表")
        self.refresh_btn.clicked.connect(self.refresh_server_list)
        
        self.force_update_btn = QPushButton("强制更新")
        self.force_update_btn.clicked.connect(self.force_update_servers)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        
        bottom_layout.addWidget(self.refresh_btn)
        bottom_layout.addWidget(self.force_update_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(bottom_layout)
        
        self.setLayout(main_layout)
    
    def init_server_list_tab(self, tab_widget):
        """初始化服务器列表标签页"""
        server_tab = QWidget()
        layout = QVBoxLayout()
        
        # 服务器统计信息
        stats_layout = QHBoxLayout()
        self.total_label = QLabel("总服务器数: 0")
        self.active_label = QLabel("活跃服务器: 0")
        self.auto_update_label = QLabel("自动更新: 已启用")
        
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.active_label)
        stats_layout.addWidget(self.auto_update_label)
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        
        # 服务器表格
        self.server_table = QTableWidget()
        self.server_table.setColumnCount(8)
        self.server_table.setHorizontalHeaderLabels([
            "名称", "IP地址", "端口", "国家", "优先级", "状态", "成功率", "最后连接"
        ])
        
        # 设置表格属性
        header = self.server_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        
        self.server_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.server_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.server_table)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.test_selected_server)
        
        self.remove_btn = QPushButton("删除服务器")
        self.remove_btn.clicked.connect(self.remove_selected_server)
        
        btn_layout.addWidget(self.test_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        server_tab.setLayout(layout)
        tab_widget.addTab(server_tab, "服务器列表")
    
    def init_add_server_tab(self, tab_widget):
        """初始化添加服务器标签页"""
        add_tab = QWidget()
        layout = QVBoxLayout()
        
        # 服务器信息表单
        form_group = QGroupBox("服务器信息")
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("服务器名称")
        
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("IP地址 (如: 192.168.1.1)")
        
        self.port_edit = QSpinBox()
        self.port_edit.setRange(1, 65535)
        self.port_edit.setValue(4661)
        
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("服务器描述")
        
        self.country_combo = QComboBox()
        self.country_combo.addItems(["Unknown", "CN", "US", "DE", "FR", "JP", "KR", "RU", "GB"])
        
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 10)
        self.priority_spin.setValue(5)
        
        form_layout.addRow("名称:", self.name_edit)
        form_layout.addRow("IP地址:", self.ip_edit)
        form_layout.addRow("端口:", self.port_edit)
        form_layout.addRow("描述:", self.description_edit)
        form_layout.addRow("国家:", self.country_combo)
        form_layout.addRow("优先级:", self.priority_spin)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # 添加按钮
        add_btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("添加服务器")
        self.add_btn.clicked.connect(self.add_server)
        
        self.clear_btn = QPushButton("清空表单")
        self.clear_btn.clicked.connect(self.clear_form)
        
        add_btn_layout.addWidget(self.add_btn)
        add_btn_layout.addWidget(self.clear_btn)
        add_btn_layout.addStretch()
        
        layout.addLayout(add_btn_layout)
        
        layout.addStretch()
        add_tab.setLayout(layout)
        tab_widget.addTab(add_tab, "添加服务器")
    
    def init_server_sources_tab(self, tab_widget):
        """初始化服务器源标签页"""
        sources_tab = QWidget()
        layout = QVBoxLayout()
        
        # 自动更新设置
        auto_group = QGroupBox("自动更新设置")
        auto_layout = QFormLayout()
        
        self.auto_update_check = QCheckBox("启用自动更新")
        self.auto_update_check.setChecked(True)
        self.auto_update_check.stateChanged.connect(self.toggle_auto_update)
        
        self.update_interval_spin = QSpinBox()
        self.update_interval_spin.setRange(300, 86400)  # 5分钟到24小时
        self.update_interval_spin.setValue(3600)  # 1小时
        self.update_interval_spin.setSuffix(" 秒")
        self.update_interval_spin.valueChanged.connect(self.change_update_interval)
        
        auto_layout.addRow("自动更新:", self.auto_update_check)
        auto_layout.addRow("更新间隔:", self.update_interval_spin)
        
        auto_group.setLayout(auto_layout)
        layout.addWidget(auto_group)
        
        # 服务器源列表
        sources_group = QGroupBox("服务器源")
        sources_layout = QVBoxLayout()
        
        self.sources_text = QTextEdit()
        self.sources_text.setPlaceholderText("每行一个服务器源URL")
        self.sources_text.setMaximumHeight(150)
        
        # 加载当前源
        current_sources = self.server_manager.server_sources
        self.sources_text.setPlainText("\n".join(current_sources))
        
        sources_btn_layout = QHBoxLayout()
        
        self.save_sources_btn = QPushButton("保存源列表")
        self.save_sources_btn.clicked.connect(self.save_server_sources)
        
        self.reset_sources_btn = QPushButton("重置为默认")
        self.reset_sources_btn.clicked.connect(self.reset_server_sources)
        
        sources_btn_layout.addWidget(self.save_sources_btn)
        sources_btn_layout.addWidget(self.reset_sources_btn)
        sources_btn_layout.addStretch()
        
        sources_layout.addWidget(self.sources_text)
        sources_layout.addLayout(sources_btn_layout)
        
        sources_group.setLayout(sources_layout)
        layout.addWidget(sources_group)
        
        # 更新状态
        status_group = QGroupBox("更新状态")
        status_layout = QVBoxLayout()
        
        self.update_progress = QProgressBar()
        self.update_progress.setVisible(False)
        
        self.status_label = QLabel("就绪")
        
        status_layout.addWidget(self.update_progress)
        status_layout.addWidget(self.status_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        layout.addStretch()
        sources_tab.setLayout(layout)
        tab_widget.addTab(sources_tab, "服务器源")
    
    def load_servers(self):
        """加载服务器列表到表格"""
        try:
            servers = self.server_manager.get_active_servers()
            
            self.server_table.setRowCount(len(servers))
            
            for row, server in enumerate(servers):
                # 名称
                name_item = QTableWidgetItem(server.name)
                name_item.setData(Qt.UserRole, server)
                self.server_table.setItem(row, 0, name_item)
                
                # IP地址
                self.server_table.setItem(row, 1, QTableWidgetItem(server.ip))
                
                # 端口
                self.server_table.setItem(row, 2, QTableWidgetItem(str(server.port)))
                
                # 国家
                self.server_table.setItem(row, 3, QTableWidgetItem(server.country))
                
                # 优先级
                priority_item = QTableWidgetItem(str(server.priority))
                priority_item.setTextAlignment(Qt.AlignCenter)
                self.server_table.setItem(row, 4, priority_item)
                
                # 状态
                status_text = "活跃" if server.is_active else "禁用"
                status_item = QTableWidgetItem(status_text)
                status_item.setTextAlignment(Qt.AlignCenter)
                self.server_table.setItem(row, 5, status_item)
                
                # 成功率
                total_attempts = server.success_count + server.fail_count
                if total_attempts > 0:
                    success_rate = (server.success_count / total_attempts) * 100
                    success_text = f"{success_rate:.1f}%"
                else:
                    success_text = "N/A"
                
                success_item = QTableWidgetItem(success_text)
                success_item.setTextAlignment(Qt.AlignCenter)
                self.server_table.setItem(row, 6, success_item)
                
                # 最后连接
                if server.last_seen > 0:
                    last_seen = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(server.last_seen))
                else:
                    last_seen = "从未"
                
                last_item = QTableWidgetItem(last_seen)
                self.server_table.setItem(row, 7, last_item)
            
            # 更新统计信息
            self.update_statistics()
            
        except Exception as e:
            logger.error(f"加载服务器列表失败: {e}")
            QMessageBox.warning(self, "错误", f"加载服务器列表失败: {e}")
    
    def update_statistics(self):
        """更新统计信息"""
        try:
            total_servers = len(self.server_manager.servers)
            active_servers = len([s for s in self.server_manager.servers if s.is_active])
            
            self.total_label.setText(f"总服务器数: {total_servers}")
            self.active_label.setText(f"活跃服务器: {active_servers}")
            
            if self.server_manager.running:
                self.auto_update_label.setText("自动更新: 已启用")
            else:
                self.auto_update_label.setText("自动更新: 已禁用")
                
        except Exception as e:
            logger.error(f"更新统计信息失败: {e}")
    
    def add_server(self):
        """添加服务器"""
        try:
            name = self.name_edit.text().strip()
            ip = self.ip_edit.text().strip()
            port = self.port_edit.value()
            description = self.description_edit.text().strip()
            country = self.country_combo.currentText()
            priority = self.priority_spin.value()
            
            if not name or not ip:
                QMessageBox.warning(self, "警告", "请填写服务器名称和IP地址")
                return
            
            # 验证IP地址格式
            import re
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, ip):
                QMessageBox.warning(self, "警告", "IP地址格式不正确")
                return
            
            # 验证端口范围
            if port < 1 or port > 65535:
                QMessageBox.warning(self, "警告", "端口号必须在1-65535之间")
                return
            
            # 添加服务器
            success = self.server_manager.add_custom_server(
                name, ip, port, description, country, priority
            )
            
            if success:
                QMessageBox.information(self, "成功", f"已添加服务器: {name}")
                self.clear_form()
                self.load_servers()
            else:
                QMessageBox.warning(self, "警告", "添加服务器失败，可能已存在相同IP和端口的服务器")
                
        except Exception as e:
            logger.error(f"添加服务器失败: {e}")
            QMessageBox.critical(self, "错误", f"添加服务器失败: {e}")
    
    def clear_form(self):
        """清空表单"""
        self.name_edit.clear()
        self.ip_edit.clear()
        self.port_edit.setValue(4661)
        self.description_edit.clear()
        self.country_combo.setCurrentText("Unknown")
        self.priority_spin.setValue(5)
    
    def test_selected_server(self):
        """测试选中的服务器"""
        current_row = self.server_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "提示", "请先选择一个服务器")
            return
        
        try:
            server_item = self.server_table.item(current_row, 0)
            server = server_item.data(Qt.UserRole)
            
            QMessageBox.information(self, "测试连接", 
                                  f"正在测试服务器: {server.name}\n{server.ip}:{server.port}")
            
            # 这里可以添加实际的连接测试逻辑
            
        except Exception as e:
            logger.error(f"测试服务器失败: {e}")
            QMessageBox.critical(self, "错误", f"测试服务器失败: {e}")
    
    def remove_selected_server(self):
        """删除选中的服务器"""
        current_row = self.server_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "提示", "请先选择一个服务器")
            return
        
        try:
            server_item = self.server_table.item(current_row, 0)
            server = server_item.data(Qt.UserRole)
            
            reply = QMessageBox.question(self, "确认删除", 
                                       f"确定要删除服务器 {server.name} ({server.ip}:{server.port}) 吗？",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                success = self.server_manager.remove_server(server.ip, server.port)
                if success:
                    QMessageBox.information(self, "成功", "服务器已删除")
                    self.load_servers()
                else:
                    QMessageBox.warning(self, "警告", "删除服务器失败")
                    
        except Exception as e:
            logger.error(f"删除服务器失败: {e}")
            QMessageBox.critical(self, "错误", f"删除服务器失败: {e}")
    
    def refresh_server_list(self):
        """刷新服务器列表"""
        self.load_servers()
        QMessageBox.information(self, "刷新完成", "服务器列表已刷新")
    
    def force_update_servers(self):
        """强制更新服务器列表"""
        try:
            self.update_progress.setVisible(True)
            self.status_label.setText("正在更新...")
            self.force_update_btn.setEnabled(False)
            
            # 启动更新线程
            self.update_worker = ServerUpdateWorker(self.server_manager)
            self.update_worker.progress_updated.connect(self.status_label.setText)
            self.update_worker.update_finished.connect(self.on_update_finished)
            self.update_worker.start()
            
        except Exception as e:
            logger.error(f"强制更新失败: {e}")
            QMessageBox.critical(self, "错误", f"强制更新失败: {e}")
            self.reset_update_ui()
    
    def on_update_finished(self, success: bool, message: str):
        """更新完成回调"""
        self.reset_update_ui()
        
        if success:
            QMessageBox.information(self, "更新完成", message)
            self.load_servers()
        else:
            QMessageBox.warning(self, "更新失败", message)
    
    def reset_update_ui(self):
        """重置更新界面状态"""
        self.update_progress.setVisible(False)
        self.status_label.setText("就绪")
        self.force_update_btn.setEnabled(True)
    
    def toggle_auto_update(self, state):
        """切换自动更新状态"""
        try:
            if state == Qt.Checked:
                self.server_manager.running = True
                self.server_manager._start_auto_update()
                logger.info("ED2K服务器自动更新已启用")
            else:
                self.server_manager.running = False
                logger.info("ED2K服务器自动更新已禁用")
                
            self.update_statistics()
            
        except Exception as e:
            logger.error(f"切换自动更新状态失败: {e}")
    
    def change_update_interval(self, value):
        """更改更新间隔"""
        try:
            self.server_manager.auto_update_interval = value
            logger.info(f"ED2K服务器更新间隔已设置为 {value} 秒")
        except Exception as e:
            logger.error(f"更改更新间隔失败: {e}")
    
    def save_server_sources(self):
        """保存服务器源列表"""
        try:
            sources_text = self.sources_text.toPlainText().strip()
            if not sources_text:
                QMessageBox.warning(self, "警告", "请输入服务器源")
                return
            
            sources = [line.strip() for line in sources_text.split('\n') if line.strip()]
            self.server_manager.server_sources = sources
            
            QMessageBox.information(self, "成功", f"已保存 {len(sources)} 个服务器源")
            
        except Exception as e:
            logger.error(f"保存服务器源失败: {e}")
            QMessageBox.critical(self, "错误", f"保存服务器源失败: {e}")
    
    def reset_server_sources(self):
        """重置为默认服务器源"""
        try:
            default_sources = [
                "https://raw.githubusercontent.com/emule-security/emule-security-list/master/serverlist.met",
                "https://www.emule-project.net/home/perl/general.cgi?l=1&rm=download&rm=serverlist",
                "https://ed2k-server-list.com/servers.json"
            ]
            
            self.sources_text.setPlainText("\n".join(default_sources))
            self.server_manager.server_sources = default_sources
            
            QMessageBox.information(self, "成功", "已重置为默认服务器源")
            
        except Exception as e:
            logger.error(f"重置服务器源失败: {e}")
            QMessageBox.critical(self, "错误", f"重置服务器源失败: {e}")
    
    def on_server_added(self, server: ED2KServerInfo):
        """服务器添加回调"""
        logger.info(f"服务器已添加: {server.name} ({server.ip}:{server.port})")
    
    def on_server_removed(self, server: ED2KServerInfo):
        """服务器移除回调"""
        logger.info(f"服务器已移除: {server.name} ({server.ip}:{server.port})")
    
    def on_server_updated(self, server: ED2KServerInfo):
        """服务器更新回调"""
        logger.info(f"服务器已更新: {server.name} ({server.ip}:{server.port})")
    
    def closeEvent(self, event):
        """关闭事件"""
        try:
            # 保存当前设置
            self.server_manager._save_servers()
            event.accept()
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            event.accept()
