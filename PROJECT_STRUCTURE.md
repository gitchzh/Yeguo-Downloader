# 椰果视频下载器 - 项目结构

## 📁 项目目录结构

```
Yeguo-Downloader/
├── main.py                    # 程序入口文件
├── requirements.txt           # Python依赖包列表
├── README.md                 # 项目说明文档
├── LICENSE                   # 开源许可证
├── .gitignore               # Git忽略文件配置
├── QUICK_SETUP.md           # 快速配置指南
├── EMAIL_SETUP.md           # 邮件配置详细说明
├── PROJECT_STRUCTURE.md     # 项目结构说明（本文件）
├── setup_email.py           # 邮件配置脚本
├── test_email.py            # 邮件配置测试脚本
├── src/                     # 源代码目录
│   ├── __init__.py          # 包初始化文件
│   ├── core/                # 核心模块
│   │   └── config.py        # 配置管理
│   ├── ui/                  # 用户界面模块
│   │   ├── __init__.py      # UI包初始化
│   │   ├── main_window.py   # 主窗口界面
│   │   ├── main_window_methods.py # 主窗口方法
│   │   ├── settings_dialog.py # 设置对话框
│   │   └── feedback_dialog.py # 反馈对话框
│   ├── workers/             # 工作线程模块
│   │   ├── __init__.py      # 工作线程包初始化
│   │   ├── parse_worker.py  # 解析工作线程
│   │   └── download_worker.py # 下载工作线程
│   └── utils/               # 工具模块
│       ├── __init__.py      # 工具包初始化
│       ├── logger.py        # 日志管理
│       └── file_utils.py    # 文件工具
└── resources/               # 资源文件目录
    └── logo.ico             # 应用程序图标
```

## 🗂️ 模块说明

### 核心模块 (core/)
- **config.py**: 全局配置管理，包含应用程序版本、默认设置等

### 用户界面模块 (ui/)
- **main_window.py**: 主窗口界面定义，包含菜单栏、工具栏、状态栏等
- **main_window_methods.py**: 主窗口的业务逻辑方法，如解析、下载、设置等
- **settings_dialog.py**: 设置对话框，提供应用程序配置界面
- **feedback_dialog.py**: 反馈对话框，支持用户提交问题反馈

### 工作线程模块 (workers/)
- **parse_worker.py**: 视频解析工作线程，负责解析视频信息和格式
- **download_worker.py**: 下载工作线程，负责文件下载和进度管理

### 工具模块 (utils/)
- **logger.py**: 日志管理工具，提供统一的日志记录功能
- **file_utils.py**: 文件操作工具，包含文件路径处理、文件名清理等

## 📄 配置文件说明

### 主要配置文件
- **requirements.txt**: Python依赖包列表，用于环境搭建
- **.gitignore**: Git版本控制忽略文件配置
- **LICENSE**: 开源许可证文件

### 文档文件
- **README.md**: 项目主要说明文档
- **QUICK_SETUP.md**: 快速配置指南
- **EMAIL_SETUP.md**: 邮件功能配置详细说明
- **PROJECT_STRUCTURE.md**: 项目结构说明（本文件）

### 配置脚本
- **setup_email.py**: 邮件配置向导脚本，帮助用户设置邮箱环境变量
- **test_email.py**: 邮件配置测试脚本，用于验证邮件发送功能是否正常

## 📧 邮件反馈功能

### 功能说明
- **反馈对话框**: 用户可以通过界面提交问题反馈
- **邮件发送**: 自动将反馈信息发送到指定邮箱
- **多邮箱支持**: 支持Gmail和QQ邮箱
- **安全配置**: 使用环境变量存储敏感信息

### 配置流程
1. 运行 `python setup_email.py` 进行配置
2. 按照提示输入邮箱信息
3. 运行 `python test_email.py` 测试配置
4. 在程序中使用"帮助" → "问题反馈"功能

## 🔧 开发规范

### 文件命名
- 使用小写字母和下划线命名
- 类名使用大驼峰命名法
- 函数和变量使用小写字母和下划线

### 代码组织
- 每个模块都有明确的职责
- 使用类型注解提高代码可读性
- 添加详细的文档字符串
- 遵循PEP 8代码规范

### 版本控制
- 不提交敏感信息（如邮箱密码）
- 不提交临时文件和日志文件
- 不提交大型二进制文件（如FFmpeg）

## 🚀 部署说明

### 环境要求
- Python 3.8+
- PyQt5
- yt-dlp
- 其他依赖见requirements.txt

### 快速启动
1. 安装依赖：`pip install -r requirements.txt`
2. 运行程序：`python main.py`
3. 配置邮件（可选）：参考QUICK_SETUP.md

### 发布准备
- 确保所有文档完整
- 测试所有功能正常
- 清理临时文件和日志
- 检查.gitignore配置
