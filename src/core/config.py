"""
配置管理模块

包含应用程序的全局配置参数。
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
    CACHE_LIMIT = 10
    
    # 默认下载速度限制（KB/s），None 表示无限制
    DEFAULT_SPEED_LIMIT: Optional[int] = None
    
    # 应用程序版本号
    APP_VERSION = "1.0.1"
    
    # 文件名最大长度限制，避免系统文件名过长问题
    MAX_FILENAME_LENGTH = 200
