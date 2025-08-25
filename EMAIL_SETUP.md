# 邮件配置说明

## 概述

椰果视频下载器的反馈功能需要配置邮件发送服务才能正常工作。本文档将指导您如何配置邮件发送功能。

## 配置步骤

### 方法一：使用配置脚本（推荐）

1. **运行配置脚本**
   ```bash
   python setup_email.py
   ```

2. **按照提示输入信息**
   - 您的邮箱地址（支持QQ邮箱和Gmail）
   - 邮箱应用密码/授权码
   - 接收反馈的邮箱地址

3. **激活配置**
   - Windows: 在PowerShell中运行生成的命令
   - Linux/Mac: 运行 `./setup_email.sh`

4. **测试配置**
   ```bash
   python test_email.py
   ```

5. **启动程序**
   ```bash
   python main.py
   ```

### 方法二：手动配置

#### 1. 创建邮箱应用密码

**Gmail用户：**

1. 登录您的Gmail账户
2. 进入 [Google账户设置](https://myaccount.google.com/)
3. 点击"安全性"
4. 在"登录Google"部分，点击"2步验证"
5. 启用2步验证（如果尚未启用）
6. 返回安全性页面，点击"应用专用密码"
7. 选择"邮件"和"Windows计算机"
8. 点击"生成"
9. 复制生成的16位应用密码

**QQ邮箱用户：**

1. 登录您的QQ邮箱
2. 进入 [QQ邮箱设置](https://mail.qq.com/)
3. 点击"设置" -> "账户"
4. 找到"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"
5. 开启"POP3/SMTP服务"
6. 按照提示验证身份
7. 获取授权码（不是登录密码）
8. 复制生成的授权码

1. 登录您的Gmail账户
2. 进入 [Google账户设置](https://myaccount.google.com/)
3. 点击"安全性"
4. 在"登录Google"部分，点击"2步验证"
5. 启用2步验证（如果尚未启用）
6. 返回安全性页面，点击"应用专用密码"
7. 选择"邮件"和"Windows计算机"
8. 点击"生成"
9. 复制生成的16位应用密码

### 2. 修改邮件配置

打开 `src/ui/feedback_dialog.py` 文件，找到以下代码段：

```python
# 邮件配置
sender_email = "yeguo.feedback@gmail.com"  # 发送邮箱
sender_password = "your_app_password"      # 应用密码
receiver_email = "gmrchzh@gmail.com"       # 接收邮箱
```

修改为您的实际配置：

```python
# 邮件配置
sender_email = "your_email@gmail.com"      # 您的Gmail邮箱
sender_password = "your_16_digit_password" # 您的16位应用密码
receiver_email = "gmrchzh@gmail.com"       # 接收反馈的邮箱
```

### 3. 测试配置

1. 运行程序
2. 点击"帮助" → "问题反馈"
3. 填写测试反馈信息
4. 点击"提交反馈"
5. 检查是否收到反馈邮件

## 安全注意事项

1. **不要将应用密码提交到版本控制系统**
   - 将 `feedback_dialog.py` 添加到 `.gitignore`
   - 或使用环境变量存储敏感信息

2. **使用环境变量（推荐）**
   
   修改代码以使用环境变量：
   
   ```python
   import os
   
   sender_email = os.getenv("FEEDBACK_EMAIL", "your_email@gmail.com")
   sender_password = os.getenv("FEEDBACK_PASSWORD", "your_app_password")
   receiver_email = os.getenv("RECEIVER_EMAIL", "gmrchzh@gmail.com")
   ```
   
   然后设置环境变量：
   
   ```bash
   # Windows
   set FEEDBACK_EMAIL=your_email@gmail.com
   set FEEDBACK_PASSWORD=your_16_digit_password
   set RECEIVER_EMAIL=gmrchzh@gmail.com
   
   # Linux/Mac
   export FEEDBACK_EMAIL=your_email@gmail.com
   export FEEDBACK_PASSWORD=your_16_digit_password
   export RECEIVER_EMAIL=gmrchzh@gmail.com
   ```

## 故障排除

### 常见错误

1. **Authentication failed**
   - 检查应用密码是否正确
   - 确认2步验证已启用

2. **SMTP connection failed**
   - 检查网络连接
   - 确认防火墙未阻止SMTP连接

3. **SSL certificate error**
   - 更新Python的SSL证书
   - 检查系统时间是否正确

### 调试模式

在 `feedback_dialog.py` 中添加调试信息：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 在EmailSender.run()方法中添加
logger.debug(f"尝试连接到SMTP服务器...")
logger.debug(f"登录邮箱: {sender_email}")
```

## 替代方案

如果Gmail配置困难，可以考虑以下替代方案：

1. **使用其他邮件服务商**
   - QQ邮箱：`smtp.qq.com:587`
   - 163邮箱：`smtp.163.com:25`
   - Outlook：`smtp-mail.outlook.com:587`

2. **使用第三方邮件服务**
   - SendGrid
   - Mailgun
   - Amazon SES

3. **本地邮件服务器**
   - 配置本地SMTP服务器
   - 使用Postfix或类似软件

## 联系支持

如果您在配置过程中遇到问题，请通过以下方式联系：

- 邮箱：gmrchzh@gmail.com
- 在GitHub上提交Issue
