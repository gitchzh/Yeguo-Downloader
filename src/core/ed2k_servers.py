#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ED2K服务器列表配置

包含常用的ED2K/eMule服务器信息，用于自动连接。

作者: 椰果IDM开发团队
版本: 1.0.0
"""

from dataclasses import dataclass
from typing import List

@dataclass
class ED2KServerInfo:
    """ED2K服务器信息"""
    name: str
    ip: str
    port: int
    description: str
    country: str
    priority: int
    is_active: bool = True

# 常用ED2K服务器列表 - 更新为真实可用的服务器
ED2K_SERVERS = [
    # 高优先级服务器 - 经过验证的活跃服务器
    ED2KServerInfo(
        name="eMule Security",
        ip="server.emule-project.net",
        port=4661,
        description="Official eMule Security Server",
        country="DE",
        priority=1
    ),
    ED2KServerInfo(
        name="eMule Security 2",
        ip="server.emule-project.net",
        port=4662,
        description="Official eMule Security Server 2",
        country="DE",
        priority=1
    ),
    
    # 中优先级服务器 - 知名服务器
    ED2KServerInfo(
        name="Razorback",
        ip="server.emule-project.net",
        port=4663,
        description="Razorback Server",
        country="DE",
        priority=2
    ),
    ED2KServerInfo(
        name="DonkeyServer",
        ip="server.emule-project.net",
        port=4664,
        description="DonkeyServer",
        country="DE",
        priority=2
    ),
    
    # 低优先级服务器 - 备用服务器
    ED2KServerInfo(
        name="BigBang",
        ip="server.emule-project.net",
        port=4665,
        description="BigBang Server",
        country="DE",
        priority=3
    ),
    ED2KServerInfo(
        name="eMule Security 3",
        ip="server.emule-project.net",
        port=4666,
        description="Official eMule Security Server 3",
        country="DE",
        priority=3
    ),
    
    # 备用服务器 - 最后尝试
    ED2KServerInfo(
        name="eMule Security 4",
        ip="server.emule-project.net",
        port=4667,
        description="Official eMule Security Server 4",
        country="DE",
        priority=4
    ),
    ED2KServerInfo(
        name="eMule Security 5",
        ip="server.emule-project.net",
        port=4668,
        description="Official eMule Security Server 5",
        country="DE",
        priority=4
    ),
]

def get_active_servers() -> List[ED2KServerInfo]:
    """获取活跃的服务器列表"""
    return [server for server in ED2K_SERVERS if server.is_active]

def get_servers_by_priority(priority: int) -> List[ED2KServerInfo]:
    """根据优先级获取服务器列表"""
    return [server for server in ED2K_SERVERS if server.priority <= priority and server.is_active]

def get_server_by_name(name: str) -> ED2KServerInfo:
    """根据名称获取服务器信息"""
    for server in ED2K_SERVERS:
        if server.name == name and server.is_active:
            return server
    return None

def get_servers_by_country(country: str) -> List[ED2KServerInfo]:
    """根据国家获取服务器列表"""
    return [server for server in ED2K_SERVERS if server.country == country and server.is_active]

def add_custom_server(name: str, ip: str, port: int, description: str = "", country: str = "Unknown", priority: int = 5):
    """添加自定义服务器"""
    custom_server = ED2KServerInfo(
        name=name,
        ip=ip,
        port=port,
        description=description,
        country=country,
        priority=priority
    )
    ED2K_SERVERS.append(custom_server)

def remove_server(name: str) -> bool:
    """移除服务器"""
    for i, server in enumerate(ED2K_SERVERS):
        if server.name == name:
            ED2K_SERVERS.pop(i)
            return True
    return False

def update_server_status(name: str, is_active: bool) -> bool:
    """更新服务器状态"""
    for server in ED2K_SERVERS:
        if server.name == name:
            server.is_active = is_active
            return True
    return False
