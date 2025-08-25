#!/usr/bin/env python3
"""
邮件配置测试脚本

用于测试邮件发送功能是否正常工作。
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def test_email_config():
    """测试邮件配置"""
    print("=" * 50)
    print("椰果视频下载器 - 邮件配置测试")
    print("=" * 50)
    print()
    
    # 获取环境变量
    sender_email = os.getenv("FEEDBACK_EMAIL")
    sender_password = os.getenv("FEEDBACK_PASSWORD")
    receiver_email = os.getenv("RECEIVER_EMAIL")
    
    print("当前配置：")
    print(f"发送邮箱: {sender_email}")
    print(f"接收邮箱: {receiver_email}")
    print(f"密码: {'*' * len(sender_password) if sender_password else '未设置'}")
    print()
    
    if not all([sender_email, sender_password, receiver_email]):
        print("❌ 环境变量未完全设置")
        print("请运行 'python setup_email.py' 进行配置")
        return False
    
    try:
        # 创建测试邮件
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = "[椰果下载器测试] 邮件配置测试"
        
        body = f"""
这是一封测试邮件，用于验证椰果视频下载器的邮件配置是否正确。

发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
发送邮箱：{sender_email}
接收邮箱：{receiver_email}

如果您收到这封邮件，说明邮件配置成功！

---
此邮件由椰果视频下载器自动发送
        """
        
        message.attach(MIMEText(body, "plain", "utf-8"))
        
        print("正在测试邮件发送...")
        
        # 根据邮箱类型选择SMTP服务器
        if "@qq.com" in sender_email:
            print("使用QQ邮箱SMTP服务器...")
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.qq.com", 465, context=context) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, receiver_email, message.as_string())
        else:
            print("使用Gmail SMTP服务器...")
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, receiver_email, message.as_string())
        
        print("✅ 邮件发送成功！")
        print(f"请检查邮箱 {receiver_email} 是否收到测试邮件")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        print()
        print("可能的解决方案：")
        print("1. 检查邮箱地址是否正确")
        print("2. 检查应用密码/授权码是否正确")
        print("3. 确认已开启SMTP服务")
        print("4. 检查网络连接")
        return False

def main():
    """主函数"""
    try:
        if test_email_config():
            print()
            print("🎉 邮件配置测试成功！")
            print("现在可以在程序中使用反馈功能了。")
        else:
            print()
            print("❌ 邮件配置测试失败")
            print("请检查配置并重新测试。")
    except KeyboardInterrupt:
        print()
        print("\n⚠️  测试已取消")
    except Exception as e:
        print()
        print(f"❌ 测试过程中出现错误: {e}")

if __name__ == "__main__":
    main()
