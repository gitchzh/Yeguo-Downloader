# 椰果下载器 - 快速配置指南

## 🚀 快速开始

### 1. 运行配置脚本
```bash
python setup_email.py
```

### 2. 按照提示输入信息
- 您的邮箱地址（支持QQ邮箱和Gmail）
- 邮箱应用密码/授权码
- 接收反馈的邮箱地址

### 3. 激活配置
- **Windows**: 在PowerShell中运行生成的命令
- **Linux/Mac**: 运行 `./setup_email.sh`

### 4. 测试配置
```bash
python test_email.py
```

### 5. 启动程序
```bash
python main.py
```

### 6. 使用反馈功能
在程序中点击"帮助" → "问题反馈"即可使用

## 📧 邮箱配置说明

### QQ邮箱配置
1. 登录QQ邮箱：https://mail.qq.com/
2. 点击"设置" -> "账户"
3. 找到"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"
4. 开启"POP3/SMTP服务"
5. 按照提示验证身份
6. 获取授权码（不是登录密码）

### Gmail配置
1. 登录Google账户：https://myaccount.google.com/
2. 进入"安全性"
3. 开启"2步验证"
4. 创建"应用专用密码"
5. 选择"邮件"和"Windows计算机"
6. 复制生成的16位密码

## 🔧 故障排除

### 常见问题
1. **连接失败**
   - 检查网络连接
   - 确认防火墙设置
   - 验证邮箱地址格式

2. **认证失败**
   - 检查应用密码/授权码
   - 确认已开启SMTP服务
   - 验证邮箱地址

3. **SSL错误**
   - 更新Python版本
   - 检查系统时间
   - 更新SSL证书

### 测试步骤
1. 运行 `python test_email.py`
2. 检查是否收到测试邮件
3. 如果失败，查看错误信息
4. 根据错误信息调整配置

## 📞 获取帮助

如果遇到问题，请：
1. 查看 [EMAIL_SETUP.md](EMAIL_SETUP.md) 详细文档
2. 运行 `python test_email.py` 进行诊断
3. 检查邮箱服务商的状态页面
4. 联系技术支持

## ✅ 成功标志

配置成功后，您应该能够：
1. 运行 `python test_email.py` 看到"邮件发送成功"
2. 在接收邮箱中收到测试邮件
3. 在程序中正常使用"问题反馈"功能
