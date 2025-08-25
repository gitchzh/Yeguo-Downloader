#!/usr/bin/env python3
"""
邮件配置脚本

帮助用户设置反馈功能的邮件配置。
"""

import os
import sys

def setup_email_config():
    """设置邮件配置"""
    print("=" * 50)
    print("椰果视频下载器 - 邮件配置向导")
    print("=" * 50)
    print()
    
    print("此脚本将帮助您配置反馈功能的邮件发送设置。")
    print("请按照以下步骤操作：")
    print()
    
    # 获取用户输入
    print("1. 发送邮箱配置")
    sender_email = input("请输入您的Gmail邮箱地址: ").strip()
    if not sender_email:
        print("❌ 邮箱地址不能为空")
        return False
        
    print()
    print("2. 应用密码配置")
    print("注意：您需要先创建邮箱应用密码")
    print()
    print("Gmail用户：")
    print("  请访问：https://myaccount.google.com/apppasswords")
    print("  选择'邮件'和'Windows计算机'，然后生成16位应用密码")
    print()
    print("QQ邮箱用户：")
    print("  请访问：https://mail.qq.com/")
    print("  设置 -> 账户 -> 开启SMTP服务")
    print("  获取授权码（不是登录密码）")
    print()
    
    sender_password = input("请输入您的Gmail应用密码: ").strip()
    if not sender_password:
        print("❌ 应用密码不能为空")
        return False
        
    print()
    print("3. 接收邮箱配置")
    receiver_email = input("请输入接收反馈的邮箱地址 (默认: gmrchzh@gmail.com): ").strip()
    if not receiver_email:
        receiver_email = "gmrchzh@gmail.com"
        
    # 创建环境变量设置脚本
    create_env_scripts(sender_email, sender_password, receiver_email)
    
    print()
    print("✅ 配置完成！")
    print()
    print("请按照以下步骤激活配置：")
    print("1. 关闭当前终端窗口")
    print("2. 重新打开终端窗口")
    print("3. 运行 'python main.py' 启动程序")
    print("4. 测试反馈功能")
    
    return True

def create_env_scripts(sender_email, sender_password, receiver_email):
    """创建环境变量设置脚本"""
    
    # Windows批处理脚本
    bat_content = f"""@echo off
REM 椰果下载器邮件配置脚本
echo 设置邮件配置环境变量...

set FEEDBACK_EMAIL={sender_email}
set FEEDBACK_PASSWORD={sender_password}
set RECEIVER_EMAIL={receiver_email}

echo 环境变量设置完成！
echo 现在可以运行 python main.py 启动程序
pause
"""
    
    # Linux/Mac shell脚本
    shell_content = f"""#!/bin/bash
# 椰果下载器邮件配置脚本
echo "设置邮件配置环境变量..."

export FEEDBACK_EMAIL="{sender_email}"
export FEEDBACK_PASSWORD="{sender_password}"
export RECEIVER_EMAIL="{receiver_email}"

echo "环境变量设置完成！"
echo "现在可以运行 python main.py 启动程序"
"""
    
    # 写入文件
    with open("setup_email.bat", "w", encoding="utf-8") as f:
        f.write(bat_content)
        
    with open("setup_email.sh", "w", encoding="utf-8") as f:
        f.write(shell_content)
        
    # 设置shell脚本可执行权限
    if sys.platform != "win32":
        os.chmod("setup_email.sh", 0o755)
    
    print("📁 已创建配置文件：")
    print("   - setup_email.bat (Windows)")
    print("   - setup_email.sh (Linux/Mac)")
    print()

def main():
    """主函数"""
    try:
        if setup_email_config():
            print()
            print("🎉 配置成功！请按照上述步骤激活配置。")
        else:
            print()
            print("❌ 配置失败，请重新运行脚本。")
    except KeyboardInterrupt:
        print()
        print("\n⚠️  配置已取消")
    except Exception as e:
        print()
        print(f"❌ 配置过程中出现错误: {e}")

if __name__ == "__main__":
    main()
