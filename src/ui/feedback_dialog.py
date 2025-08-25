"""
反馈对话框模块

提供用户反馈问题的界面，支持发送邮件反馈。
"""

import smtplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QMessageBox, QLineEdit, QFormLayout,
    QGroupBox, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

from src.core.config import Config
from src.utils.logger import logger


class EmailSender(QThread):
    """邮件发送线程"""
    
    success = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, subject: str, content: str, user_email: str):
        super().__init__()
        self.subject = subject
        self.content = content
        self.user_email = user_email
        
    def run(self):
        """发送邮件"""
        try:
            # 邮件配置 - 从环境变量读取，如果没有设置则使用默认值
            sender_email = os.getenv("FEEDBACK_EMAIL", "yeguo.feedback@gmail.com")
            sender_password = os.getenv("FEEDBACK_PASSWORD", "your_app_password")
            receiver_email = os.getenv("RECEIVER_EMAIL", "gmrchzh@gmail.com")
            
            # 检查是否配置了正确的邮箱信息
            if sender_password == "your_app_password":
                raise Exception("邮件配置未完成，请按照 EMAIL_SETUP.md 文档配置邮箱信息")
            
            # 创建邮件
            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = receiver_email
            message["Subject"] = f"[椰果下载器反馈] {self.subject}"
            
            # 邮件内容
            body = f"""
用户反馈信息：

反馈时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
用户邮箱：{self.user_email}
软件版本：{Config.APP_VERSION}

问题描述：
{self.content}

---
此邮件由椰果视频下载器自动发送
            """
            
            message.attach(MIMEText(body, "plain", "utf-8"))
            
            # 发送邮件 - 支持QQ邮箱和Gmail
            if "@qq.com" in sender_email:
                # QQ邮箱配置
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.qq.com", 465, context=context) as server:
                    server.login(sender_email, sender_password)
                    server.sendmail(sender_email, receiver_email, message.as_string())
            else:
                # Gmail配置
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                    server.login(sender_email, sender_password)
                    server.sendmail(sender_email, receiver_email, message.as_string())
                
            self.success.emit()
            
        except Exception as e:
            logger.error(f"发送反馈邮件失败: {e}")
            self.error.emit(str(e))


class FeedbackDialog(QDialog):
    """反馈对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.email_sender = None
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("问题反馈")
        self.setFixedSize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 设置图标
        try:
            icon_path = "resources/logo.ico"
            self.setWindowIcon(QIcon(icon_path))
        except:
            pass
            
        # 主布局
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("问题反馈")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 说明文字
        desc_label = QLabel("请详细描述您遇到的问题，我们会尽快处理您的反馈。")
        desc_label.setFont(QFont("Microsoft YaHei", 10))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; margin: 10px 0;")
        layout.addWidget(desc_label)
        
        # 表单组
        form_group = QGroupBox("反馈信息")
        form_layout = QFormLayout()
        
        # 用户邮箱
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("请输入您的邮箱地址（可选）")
        self.email_edit.setFont(QFont("Microsoft YaHei", 10))
        form_layout.addRow("联系邮箱:", self.email_edit)
        
        # 问题标题
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("请简要描述问题（必填）")
        self.title_edit.setFont(QFont("Microsoft YaHei", 10))
        form_layout.addRow("问题标题:", self.title_edit)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # 问题描述
        desc_group = QGroupBox("问题描述")
        desc_layout = QVBoxLayout()
        
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("请详细描述您遇到的问题，包括：\n1. 问题发生的具体步骤\n2. 错误信息（如果有）\n3. 您的系统环境\n4. 其他相关信息")
        self.content_edit.setFont(QFont("Microsoft YaHei", 10))
        self.content_edit.setMinimumHeight(150)
        desc_layout.addWidget(self.content_edit)
        
        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.submit_button = QPushButton("提交反馈")
        self.submit_button.setFont(QFont("Microsoft YaHei", 10))
        self.submit_button.setMinimumHeight(35)
        self.submit_button.clicked.connect(self.submit_feedback)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setFont(QFont("Microsoft YaHei", 10))
        self.cancel_button.setFont(QFont("Microsoft YaHei", 10))
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.submit_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-family: "Microsoft YaHei";
                font-size: 12px;
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 2px solid #0078d4;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton#cancel {
                background-color: #6c757d;
            }
            QPushButton#cancel:hover {
                background-color: #5a6268;
            }
        """)
        
        self.cancel_button.setObjectName("cancel")
        
    def submit_feedback(self):
        """提交反馈"""
        # 验证输入
        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText().strip()
        user_email = self.email_edit.text().strip()
        
        if not title:
            QMessageBox.warning(self, "提示", "请输入问题标题")
            self.title_edit.setFocus()
            return
            
        if not content:
            QMessageBox.warning(self, "提示", "请输入问题描述")
            self.content_edit.setFocus()
            return
            
        # 显示确认对话框
        msg_box = QMessageBox()
        msg_box.setWindowTitle("确认提交")
        msg_box.setText("确定要提交反馈吗？")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        msg_box.button(QMessageBox.Yes).setText("是")
        msg_box.button(QMessageBox.No).setText("否")
        
        if msg_box.exec_() != QMessageBox.Yes:
            return
            
        # 开始发送
        self.start_sending(title, content, user_email)
        
    def start_sending(self, title: str, content: str, user_email: str):
        """开始发送反馈"""
        # 禁用界面
        self.submit_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        
        # 创建发送线程
        self.email_sender = EmailSender(title, content, user_email)
        self.email_sender.success.connect(self.on_send_success)
        self.email_sender.error.connect(self.on_send_error)
        self.email_sender.start()
        
    def on_send_success(self):
        """发送成功"""
        self.progress_bar.setVisible(False)
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle("提交成功")
        msg_box.setText("感谢您的反馈！我们会尽快处理您的问题。")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.button(QMessageBox.Ok).setText("确定")
        msg_box.exec_()
        
        self.accept()
        
    def on_send_error(self, error_msg: str):
        """发送失败"""
        self.progress_bar.setVisible(False)
        self.submit_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle("发送失败")
        msg_box.setText(f"发送反馈失败，请稍后重试。\n\n错误信息：{error_msg}")
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.button(QMessageBox.Ok).setText("确定")
        msg_box.exec_()
        
    def closeEvent(self, event):
        """关闭事件"""
        if self.email_sender and self.email_sender.isRunning():
            self.email_sender.terminate()
            self.email_sender.wait()
        event.accept()
