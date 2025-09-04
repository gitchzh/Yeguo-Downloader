#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ED2K服务器动态管理系统

包含动态服务器发现、更新和验证功能，支持从网络获取最新的服务器列表。

作者: 椰果IDM开发团队
版本: 2.0.0
"""

import json
import time
import threading
import requests
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Callable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

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
    last_seen: float = 0.0
    response_time: float = 0.0
    success_count: int = 0
    fail_count: int = 0
    user_count: int = 0
    file_count: int = 0

class ED2KServerManager:
    """ED2K服务器管理器 - 动态管理服务器列表"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.servers_file = self.config_dir / "ed2k_servers.json"
        self.backup_file = self.config_dir / "ed2k_servers_backup.json"
        
        # 服务器列表
        self.servers: List[ED2KServerInfo] = []
        self.server_lock = threading.Lock()
        
        # 服务器源 - 使用一些真实可访问的源
        self.server_sources = [
            "https://www.emule-project.net/home/perl/general.cgi?l=1&rm=download&rm=serverlist",
            "https://ed2k-server-list.com/servers.json"
        ]
        
        # 默认服务器（备用）
        self.default_servers = [
            ED2KServerInfo("eMule Security", "195.154.241.58", 4661, "Official eMule Security Server", "FR", 1),
            ED2KServerInfo("eMule Security 2", "195.154.241.58", 4662, "Official eMule Security Server 2", "FR", 1),
            ED2KServerInfo("Razorback", "195.154.241.58", 4663, "Razorback Server", "FR", 2),
            ED2KServerInfo("DonkeyServer", "195.154.241.58", 4664, "DonkeyServer", "FR", 2),
        ]
        
        # 自动更新设置
        self.auto_update_interval = 3600  # 1小时
        self.last_update = 0
        self.update_thread = None
        self.running = False
        
        # 回调函数
        self.on_server_added: Optional[Callable] = None
        self.on_server_removed: Optional[Callable] = None
        self.on_server_updated: Optional[Callable] = None
        
        # 初始化
        self._load_servers()
        self._start_auto_update()
    
    def _load_servers(self):
        """从配置文件加载服务器列表"""
        try:
            if self.servers_file.exists():
                with open(self.servers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.servers = [ED2KServerInfo(**server_data) for server_data in data]
                    logger.info(f"已加载 {len(self.servers)} 个ED2K服务器")
            else:
                # 使用默认服务器
                self.servers = self.default_servers.copy()
                self._save_servers()
                logger.info("使用默认ED2K服务器列表")
        except Exception as e:
            logger.error(f"加载服务器列表失败: {e}")
            self.servers = self.default_servers.copy()
    
    def _save_servers(self):
        """保存服务器列表到配置文件"""
        try:
            with self.server_lock:
                data = [asdict(server) for server in self.servers]
                with open(self.servers_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # 创建备份
                with open(self.backup_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    
            logger.info(f"已保存 {len(self.servers)} 个ED2K服务器")
        except Exception as e:
            logger.error(f"保存服务器列表失败: {e}")
    
    def _start_auto_update(self):
        """启动自动更新线程"""
        if self.update_thread and self.update_thread.is_alive():
            return
        
        self.running = True
        self.update_thread = threading.Thread(target=self._auto_update_worker, daemon=True)
        self.update_thread.start()
        logger.info("ED2K服务器自动更新线程已启动")
    
    def _auto_update_worker(self):
        """自动更新工作线程"""
        while self.running:
            try:
                current_time = time.time()
                if current_time - self.last_update >= self.auto_update_interval:
                    logger.info("开始自动更新ED2K服务器列表...")
                    self.update_servers_from_sources()
                    self.last_update = current_time
                
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"自动更新线程错误: {e}")
                time.sleep(300)  # 出错后等待5分钟
    
    def update_servers_from_sources(self):
        """从多个源更新服务器列表"""
        new_servers = []
        
        for source in self.server_sources:
            try:
                servers = self._fetch_servers_from_source(source)
                if servers:
                    new_servers.extend(servers)
                    logger.info(f"从 {source} 获取到 {len(servers)} 个服务器")
            except Exception as e:
                logger.warning(f"从 {source} 获取服务器失败: {e}")
        
        if new_servers:
            self._merge_servers(new_servers)
            self._save_servers()
            logger.info(f"服务器列表更新完成，当前共有 {len(self.servers)} 个服务器")
    
    def _fetch_servers_from_source(self, source: str) -> List[ED2KServerInfo]:
        """从指定源获取服务器列表"""
        try:
            if source.endswith('.met'):
                return self._parse_met_file(source)
            elif source.endswith('.json'):
                return self._parse_json_file(source)
            else:
                return self._parse_html_file(source)
        except Exception as e:
            logger.error(f"解析源 {source} 失败: {e}")
            return []
    
    def _parse_met_file(self, url: str) -> List[ED2KServerInfo]:
        """解析.met格式的服务器文件"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # 简单的.met文件解析（实际实现需要更复杂的解析逻辑）
            servers = []
            lines = response.text.split('\n')
            
            for line in lines:
                if line.startswith('server'):
                    parts = line.split('|')
                    if len(parts) >= 4:
                        try:
                            name = parts[1]
                            ip = parts[2]
                            port = int(parts[3])
                            
                            server = ED2KServerInfo(
                                name=name,
                                ip=ip,
                                port=port,
                                description=f"从 {url} 获取",
                                country="Unknown",
                                priority=5
                            )
                            servers.append(server)
                        except (ValueError, IndexError):
                            continue
            
            return servers
        except Exception as e:
            logger.error(f"解析.met文件失败: {e}")
            return []
    
    def _parse_json_file(self, url: str) -> List[ED2KServerInfo]:
        """解析JSON格式的服务器文件"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            servers = []
            
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        try:
                            server = ED2KServerInfo(
                                name=item.get('name', 'Unknown'),
                                ip=item.get('ip', ''),
                                port=int(item.get('port', 4661)),
                                description=item.get('description', f'从 {url} 获取'),
                                country=item.get('country', 'Unknown'),
                                priority=int(item.get('priority', 5))
                            )
                            servers.append(server)
                        except (ValueError, KeyError):
                            continue
            
            return servers
        except Exception as e:
            logger.error(f"解析JSON文件失败: {e}")
            return []
    
    def _parse_html_file(self, url: str) -> List[ED2KServerInfo]:
        """解析HTML格式的服务器文件"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # 简单的HTML解析（实际实现需要更复杂的解析逻辑）
            servers = []
            content = response.text.lower()
            
            # 查找服务器信息模式
            import re
            patterns = [
                r'(\d+\.\d+\.\d+\.\d+):(\d+)',  # IP:PORT
                r'(\d+\.\d+\.\d+\.\d+)\s+(\d+)',  # IP PORT
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    try:
                        ip = match[0]
                        port = int(match[1])
                        
                        server = ED2KServerInfo(
                            name=f"从 {url} 发现",
                            ip=ip,
                            port=port,
                            description=f"从 {url} 自动发现",
                            country="Unknown",
                            priority=6
                        )
                        servers.append(server)
                    except (ValueError, IndexError):
                        continue
            
            return servers
        except Exception as e:
            logger.error(f"解析HTML文件失败: {e}")
            return []
    
    def _merge_servers(self, new_servers: List[ED2KServerInfo]):
        """合并新旧服务器列表"""
        with self.server_lock:
            # 创建现有服务器的IP:PORT映射
            existing_map = {(server.ip, server.port): server for server in self.servers}
            
            for new_server in new_servers:
                key = (new_server.ip, new_server.port)
                if key in existing_map:
                    # 更新现有服务器信息
                    existing = existing_map[key]
                    existing.name = new_server.name or existing.name
                    existing.description = new_server.description or existing.description
                    existing.country = new_server.country or existing.country
                    existing.priority = min(existing.priority, new_server.priority)
                    existing.last_seen = time.time()
                    
                    if self.on_server_updated:
                        self.on_server_updated(existing)
                else:
                    # 添加新服务器
                    new_server.last_seen = time.time()
                    self.servers.append(new_server)
                    
                    if self.on_server_added:
                        self.on_server_added(new_server)
            
            # 按优先级和活跃度排序
            self.servers.sort(key=lambda x: (x.priority, -x.success_count, -x.last_seen))
    
    def add_custom_server(self, name: str, ip: str, port: int, description: str = "", 
                         country: str = "Unknown", priority: int = 5) -> bool:
        """添加自定义服务器"""
        try:
            server = ED2KServerInfo(
                name=name,
                ip=ip,
                port=port,
                description=description,
                country=country,
                priority=priority,
                last_seen=time.time()
            )
            
            with self.server_lock:
                # 检查是否已存在
                for existing in self.servers:
                    if existing.ip == ip and existing.port == port:
                        logger.warning(f"服务器 {ip}:{port} 已存在")
                        return False
                
                self.servers.append(server)
                self.servers.sort(key=lambda x: (x.priority, -x.success_count, -x.last_seen))
            
            self._save_servers()
            
            if self.on_server_added:
                self.on_server_added(server)
            
            logger.info(f"已添加自定义服务器: {name} ({ip}:{port})")
            return True
            
        except Exception as e:
            logger.error(f"添加自定义服务器失败: {e}")
            return False
    
    def remove_server(self, ip: str, port: int) -> bool:
        """移除服务器"""
        try:
            with self.server_lock:
                for i, server in enumerate(self.servers):
                    if server.ip == ip and server.port == port:
                        removed = self.servers.pop(i)
                        
                        if self.on_server_removed:
                            self.on_server_removed(removed)
                        
                        self._save_servers()
                        logger.info(f"已移除服务器: {removed.name} ({ip}:{port})")
                        return True
            
            logger.warning(f"未找到服务器: {ip}:{port}")
            return False
            
        except Exception as e:
            logger.error(f"移除服务器失败: {e}")
            return False
    
    def update_server_status(self, ip: str, port: int, success: bool, response_time: float = 0.0):
        """更新服务器状态"""
        try:
            with self.server_lock:
                for server in self.servers:
                    if server.ip == ip and server.port == port:
                        if success:
                            server.success_count += 1
                            server.response_time = response_time
                            server.last_seen = time.time()
                        else:
                            server.fail_count += 1
                        
                        # 根据成功率调整优先级
                        total_attempts = server.success_count + server.fail_count
                        if total_attempts >= 10:
                            success_rate = server.success_count / total_attempts
                            if success_rate < 0.3:
                                server.priority = min(server.priority + 1, 10)
                            elif success_rate > 0.8:
                                server.priority = max(server.priority - 1, 1)
                        
                        break
        except Exception as e:
            logger.error(f"更新服务器状态失败: {e}")
    
    def get_active_servers(self) -> List[ED2KServerInfo]:
        """获取活跃的服务器列表"""
        with self.server_lock:
            return [server for server in self.servers if server.is_active]
    
    def get_servers_by_priority(self, priority: int) -> List[ED2KServerInfo]:
        """根据优先级获取服务器列表"""
        with self.server_lock:
            return [server for server in self.servers if server.priority <= priority and server.is_active]
    
    def get_server_by_name(self, name: str) -> Optional[ED2KServerInfo]:
        """根据名称获取服务器信息"""
        with self.server_lock:
            for server in self.servers:
                if server.name == name and server.is_active:
                    return server
        return None
    
    def get_servers_by_country(self, country: str) -> List[ED2KServerInfo]:
        """根据国家获取服务器列表"""
        with self.server_lock:
            return [server for server in self.servers if server.country == country and server.is_active]
    
    def get_best_servers(self, count: int = 5) -> List[ED2KServerInfo]:
        """获取最佳服务器列表"""
        with self.server_lock:
            # 按优先级、成功率和响应时间排序
            sorted_servers = sorted(
                [s for s in self.servers if s.is_active],
                key=lambda x: (x.priority, -x.success_count, x.response_time if x.response_time > 0 else float('inf'))
            )
            return sorted_servers[:count]
    
    def force_update(self):
        """强制更新服务器列表"""
        logger.info("强制更新ED2K服务器列表...")
        self.update_servers_from_sources()
    
    def stop(self):
        """停止服务器管理器"""
        self.running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5)
        logger.info("ED2K服务器管理器已停止")

# 全局服务器管理器实例
_server_manager: Optional[ED2KServerManager] = None

def get_server_manager(config_dir: str = "config") -> ED2KServerManager:
    """获取全局服务器管理器实例"""
    global _server_manager
    if _server_manager is None:
        _server_manager = ED2KServerManager(config_dir)
    return _server_manager

# 向后兼容的函数
def get_active_servers() -> List[ED2KServerInfo]:
    """获取活跃的服务器列表（向后兼容）"""
    return get_server_manager().get_active_servers()

def get_servers_by_priority(priority: int) -> List[ED2KServerInfo]:
    """根据优先级获取服务器列表（向后兼容）"""
    return get_server_manager().get_servers_by_priority(priority)

def get_server_by_name(name: str) -> Optional[ED2KServerInfo]:
    """根据名称获取服务器信息（向后兼容）"""
    return get_server_manager().get_server_by_name(name)

def get_servers_by_country(country: str) -> List[ED2KServerInfo]:
    """根据国家获取服务器列表（向后兼容）"""
    return get_server_manager().get_servers_by_country(country)

def add_custom_server(name: str, ip: str, port: int, description: str = "", country: str = "Unknown", priority: int = 5):
    """添加自定义服务器（向后兼容）"""
    return get_server_manager().add_custom_server(name, ip, port, description, country, priority)

def remove_server(name: str) -> bool:
    """移除服务器（向后兼容）"""
    # 注意：这里需要根据名称查找IP和端口
    manager = get_server_manager()
    server = manager.get_server_by_name(name)
    if server:
        return manager.remove_server(server.ip, server.port)
    return False

def update_server_status(name: str, is_active: bool) -> bool:
    """更新服务器状态（向后兼容）"""
    # 注意：这里只更新is_active状态
    manager = get_server_manager()
    server = manager.get_server_by_name(name)
    if server:
        server.is_active = is_active
        return True
    return False

# 保持原有的ED2K_SERVERS列表用于向后兼容
ED2K_SERVERS = get_active_servers()
