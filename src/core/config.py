"""
配置管理模块

该模块包含应用程序的全局配置参数，负责：
- 应用程序版本信息管理
- 下载和解析的配置参数
- 系统限制和性能参数
- 全局常量和默认值

主要类：
- Config: 应用程序全局配置类

作者: 椰果IDM开发团队
版本: 1.0.2
"""

from typing import Optional


class Config:
    """
    应用程序全局配置类
    
    包含应用程序运行所需的各种配置参数，如并发下载数、缓存限制等。
    所有配置项都集中在此类中管理，便于维护和修改。
    """
    
    # 最大并发下载数量，避免过多线程影响系统性能
    MAX_CONCURRENT_DOWNLOADS = 2
    
    # 解析结果缓存限制，避免内存占用过多
    CACHE_LIMIT = 20  # 增加缓存限制，但添加内存监控
    
    # 内存使用监控阈值（MB）
    MEMORY_WARNING_THRESHOLD = 500  # 500MB警告阈值
    MEMORY_CRITICAL_THRESHOLD = 1000  # 1GB临界阈值
    
    # 默认下载速度限制（KB/s），None 表示无限制
    DEFAULT_SPEED_LIMIT: Optional[int] = None
    
    # 应用程序版本号
    APP_VERSION = "1.5.0"
    
    # 文件名最大长度限制，避免系统文件名过长问题
    MAX_FILENAME_LENGTH = 200
    
    # 线程安全配置
    MAX_THREAD_WAIT_TIME = 30  # 线程最大等待时间（秒）
    THREAD_CLEANUP_INTERVAL = 60  # 线程清理间隔（秒）
    
    # 错误处理配置
    MAX_RETRY_ATTEMPTS = 3  # 最大重试次数
    RETRY_DELAY = 2  # 重试延迟（秒）
    
    # 超时配置
    DEFAULT_TIMEOUT = 60  # 默认超时时间（秒）
    YOUTUBE_TIMEOUT = 90  # YouTube超时时间（秒）
    BILIBILI_TIMEOUT = 180  # B站超时时间（秒）
    
    # 磁力下载配置
    MAGNET_DOWNLOAD_ENABLED = True  # 是否启用磁力下载
    MAGNET_DHT_ENABLED = True       # 是否启用DHT
    MAGNET_LSD_ENABLED = True       # 是否启用本地服务发现
    MAGNET_UPNP_ENABLED = True      # 是否启用UPnP端口映射
    MAGNET_NAT_PMP_ENABLED = True   # 是否启用NAT-PMP端口映射
    MAGNET_MAX_CONNECTIONS = 200    # 每个种子的最大连接数
    MAGNET_MAX_UPLOADS = 10         # 每个种子的最大上传数
    MAGNET_DOWNLOAD_TIMEOUT = 300   # 磁力下载超时时间（秒）
    MAGNET_PROGRESS_UPDATE_INTERVAL = 1.0  # 进度更新间隔（秒）

    # ED2K下载配置
    ED2K_DOWNLOAD_ENABLED = True    # 是否启用ED2K下载
    ED2K_KAD_ENABLED = True         # 是否启用Kademlia DHT
    ED2K_SERVER_ENABLED = True      # 是否启用服务器连接
    ED2K_MAX_CONNECTIONS = 50       # 最大连接数
    ED2K_MAX_DOWNLOADS = 5          # 最大同时下载数
    ED2K_DOWNLOAD_TIMEOUT = 300     # ED2K下载超时时间（秒）
    ED2K_PROGRESS_UPDATE_INTERVAL = 1.0  # 进度更新间隔（秒）
    ED2K_FAST_MODE = True  # 快速模式：跳过服务器连接，直接使用模拟下载
    
    # 启动配置
    STARTUP_SHOW_WARNINGS = False   # 启动时是否显示警告信息

    
    @classmethod
    def validate_config(cls) -> bool:
        """验证配置参数的有效性"""
        try:
            # 验证数值配置
            if cls.MAX_CONCURRENT_DOWNLOADS <= 0:
                return False
            if cls.CACHE_LIMIT <= 0:
                return False
            if cls.MEMORY_WARNING_THRESHOLD <= 0:
                return False
            if cls.MEMORY_CRITICAL_THRESHOLD <= cls.MEMORY_WARNING_THRESHOLD:
                return False
            if cls.MAX_FILENAME_LENGTH <= 0:
                return False
            if cls.MAX_THREAD_WAIT_TIME <= 0:
                return False
            if cls.THREAD_CLEANUP_INTERVAL <= 0:
                return False
            if cls.MAX_RETRY_ATTEMPTS <= 0:
                return False
            if cls.RETRY_DELAY < 0:
                return False
            if cls.DEFAULT_TIMEOUT <= 0:
                return False
            
            return True
        except Exception:
            return False
