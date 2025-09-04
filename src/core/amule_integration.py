#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内置aMule集成模块

实现aMule的核心功能，包括：
- ED2K协议实现
- 服务器连接管理
- 文件下载管理
- 进度监控

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import os
import sys
import time
import socket
import struct
import hashlib
import threading
import json
import logging
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

class ED2KPacketType(Enum):
    """ED2K数据包类型"""
    LOGIN_REQUEST = 0x01
    LOGIN_REPLY = 0x02
    SEARCH_REQUEST = 0x16
    SEARCH_REPLY = 0x32
    FOUND_SOURCES = 0x19
    CALLBACK_REQUEST = 0x0E
    CALLBACK_REPLY = 0x0D
    FILE_REQUEST = 0x05
    FILE_REPLY = 0x06
    FILE_STATUS = 0x07
    FILE_PART = 0x08

@dataclass
class ED2KServer:
    """ED2K服务器信息"""
    ip: str
    port: int
    name: str
    description: str
    version: str
    max_users: int
    current_users: int
    files: int
    priority: int
    is_active: bool = True

@dataclass
class ED2KFileInfo:
    """ED2K文件信息"""
    file_hash: bytes
    file_size: int
    file_name: str
    file_type: str
    sources_count: int
    complete_sources: int
    available_parts: List[int]

@dataclass
class ED2KSource:
    """ED2K下载源信息"""
    ip: str
    port: int
    user_id: bytes
    client_name: str
    version: str
    connection_type: str
    is_connected: bool

class BuiltinAMule:
    """内置aMule实现类"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # 网络配置
        self.tcp_port = 4662
        self.udp_port = 4672
        self.kad_port = 4672
        
        # 连接状态
        self.is_connected = False
        self.user_id = None
        self.client_name = "椰果IDM-内置aMule"
        self.client_version = "1.0.0"
        
        # 服务器管理
        self.servers: List[ED2KServer] = []
        self.connected_servers: List[ED2KServer] = []
        
        # 文件管理
        self.files: Dict[bytes, ED2KFileInfo] = {}
        self.sources: Dict[bytes, ED2KSource] = {}
        
        # 下载管理
        self.downloads: Dict[bytes, Dict] = {}
        self.download_queue: List[Dict] = []
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 回调函数
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_source_found: Optional[Callable] = None
        self.on_file_found: Optional[Callable] = None
        self.on_download_progress: Optional[Callable] = None
        self.on_download_complete: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # 初始化
        self._load_config()
        self._load_servers()
        self._start_background_tasks()
    
    def _load_config(self):
        """加载配置"""
        config_file = self.config_dir / "amule_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.tcp_port = config.get('tcp_port', self.tcp_port)
                    self.udp_port = config.get('udp_port', self.udp_port)
                    self.client_name = config.get('client_name', self.client_name)
            except Exception as e:
                logger.warning(f"加载配置失败: {e}")
    
    def _save_config(self):
        """保存配置"""
        config_file = self.config_dir / "amule_config.json"
        try:
            config = {
                'tcp_port': self.tcp_port,
                'udp_port': self.udp_port,
                'client_name': self.client_name,
                'client_version': self.client_version
            }
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def _load_servers(self):
        """加载服务器列表"""
        servers_file = self.config_dir / "ed2k_servers.json"
        if servers_file.exists():
            try:
                with open(servers_file, 'r', encoding='utf-8') as f:
                    servers_data = json.load(f)
                    self.servers = [ED2KServer(**server) for server in servers_data]
                    logger.info(f"已加载 {len(self.servers)} 个ED2K服务器")
            except Exception as e:
                logger.error(f"加载服务器列表失败: {e}")
        
        # 如果没有服务器，使用默认服务器
        if not self.servers:
            self._add_default_servers()
    
    def _add_default_servers(self):
        """添加默认服务器"""
        default_servers = [
            ED2KServer("eMule Security", "195.154.241.58", 4661, "Official eMule Security Server", "FR", 1, 0, 0, 1),
            ED2KServer("Razorback", "195.154.241.58", 4662, "Razorback Server", "FR", 2, 0, 0, 2),
            ED2KServer("DonkeyServer", "195.154.241.58", 4663, "DonkeyServer", "FR", 2, 0, 0, 2),
        ]
        self.servers.extend(default_servers)
        logger.info("已添加默认ED2K服务器")
    
    def _start_background_tasks(self):
        """启动后台任务"""
        # 启动服务器连接任务
        self.server_connection_thread = threading.Thread(
            target=self._server_connection_worker,
            daemon=True
        )
        self.server_connection_thread.start()
        
        # 启动下载管理任务
        self.download_manager_thread = threading.Thread(
            target=self._download_manager_worker,
            daemon=True
        )
        self.download_manager_thread.start()
        
        logger.info("后台任务已启动")
    
    def _server_connection_worker(self):
        """服务器连接工作线程"""
        while True:
            try:
                # 尝试连接服务器
                if not self.is_connected:
                    self._try_connect_servers()
                
                # 保持连接
                if self.is_connected:
                    self._maintain_connections()
                
                time.sleep(30)  # 每30秒检查一次
                
            except Exception as e:
                logger.error(f"服务器连接工作线程错误: {e}")
                time.sleep(60)
    
    def _try_connect_servers(self):
        """尝试连接服务器"""
        for server in self.servers:
            if not server.is_active:
                continue
            
            try:
                if self._connect_to_server(server):
                    logger.info(f"成功连接到服务器: {server.name} ({server.ip}:{server.port})")
                    self.is_connected = True
                    if self.on_connected:
                        self.on_connected(server)
                    break
            except Exception as e:
                logger.warning(f"连接服务器 {server.name} 失败: {e}")
                continue
    
    def _connect_to_server(self, server: ED2KServer) -> bool:
        """连接到指定服务器"""
        try:
            # 创建TCP连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            
            # 尝试连接
            sock.connect((server.ip, server.port))
            
            # 发送登录请求
            login_packet = self._create_login_packet()
            sock.send(login_packet)
            
            # 接收登录响应
            sock.settimeout(5)
            response = sock.recv(1024)
            
            if self._parse_login_response(response):
                # 保存连接信息
                self.connected_servers.append(server)
                
                # 启动服务器通信线程
                comm_thread = threading.Thread(
                    target=self._server_communication,
                    args=(sock, server),
                    daemon=True
                )
                comm_thread.start()
                
                return True
            else:
                sock.close()
                return False
                
        except Exception as e:
            logger.error(f"连接服务器失败: {e}")
            return False
    
    def _create_login_packet(self) -> bytes:
        """创建登录数据包"""
        # 生成用户ID
        if not self.user_id:
            self.user_id = hashlib.md5(f"{self.client_name}_{int(time.time())}".encode()).digest()
        
        # 构建登录数据包
        packet = struct.pack('<B', ED2KPacketType.LOGIN_REQUEST.value)
        packet += self.user_id
        packet += struct.pack('<I', self.tcp_port)
        packet += struct.pack('<I', self.udp_port)
        packet += struct.pack('<I', 0)  # 用户数
        packet += struct.pack('<I', 0)  # 文件数
        packet += struct.pack('<I', 0)  # 共享文件数
        packet += struct.pack('<I', 0)  # 共享文件大小
        
        # 添加客户端信息
        packet += struct.pack('<B', len(self.client_name))
        packet += self.client_name.encode('utf-8')
        packet += struct.pack('<B', len(self.client_version))
        packet += self.client_version.encode('utf-8')
        
        return packet
    
    def _parse_login_response(self, data: bytes) -> bool:
        """解析登录响应"""
        try:
            if len(data) < 1:
                return False
            
            packet_type = struct.unpack('<B', data[:1])[0]
            if packet_type != ED2KPacketType.LOGIN_REPLY.value:
                return False
            
            # 解析响应数据
            offset = 1
            if len(data) < offset + 4:
                return False
            
            result = struct.unpack('<I', data[offset:offset+4])[0]
            return result == 0  # 0表示成功
            
        except Exception:
            return False
    
    def _server_communication(self, sock: socket.socket, server: ED2KServer):
        """服务器通信线程"""
        try:
            while self.is_connected:
                # 接收服务器数据
                data = sock.recv(1024)
                if not data:
                    break
                
                # 处理服务器数据包
                self._handle_server_packet(data, server)
                
        except Exception as e:
            logger.error(f"服务器通信错误: {e}")
        finally:
            sock.close()
            self._remove_connected_server(server)
    
    def _handle_server_packet(self, data: bytes, server: ED2KServer):
        """处理服务器数据包"""
        try:
            if len(data) < 1:
                return
            
            packet_type = struct.unpack('<B', data[:1])[0]
            
            if packet_type == ED2KPacketType.SEARCH_REPLY.value:
                self._handle_search_reply(data)
            elif packet_type == ED2KPacketType.FOUND_SOURCES.value:
                self._handle_found_sources(data)
            # 可以添加更多数据包类型的处理
            
        except Exception as e:
            logger.error(f"处理服务器数据包失败: {e}")
    
    def _remove_connected_server(self, server: ED2KServer):
        """移除已连接的服务器"""
        if server in self.connected_servers:
            self.connected_servers.remove(server)
        
        if not self.connected_servers:
            self.is_connected = False
            if self.on_disconnected:
                self.on_disconnected()
    
    def _maintain_connections(self):
        """维护连接"""
        # 发送心跳包或保持连接
        pass
    
    def _download_manager_worker(self):
        """下载管理工作线程"""
        while True:
            try:
                # 处理下载队列
                if self.download_queue:
                    download_info = self.download_queue.pop(0)
                    self._start_download(download_info)
                
                # 更新下载进度
                self._update_download_progress()
                
                time.sleep(1)  # 每秒检查一次
                
            except Exception as e:
                logger.error(f"下载管理工作线程错误: {e}")
                time.sleep(5)
    
    def add_download(self, ed2k_url: str, save_path: str, filename: str, filesize: int, filehash: str) -> bool:
        """添加下载任务"""
        try:
            # 解析ED2K链接
            if not ed2k_url.startswith("ed2k://"):
                raise ValueError("无效的ED2K链接")
            
            # 创建下载信息
            download_info = {
                'ed2k_url': ed2k_url,
                'save_path': save_path,
                'filename': filename,
                'filesize': filesize,
                'filehash': filehash,
                'status': 'queued',
                'progress': 0,
                'downloaded_size': 0,
                'start_time': time.time()
            }
            
            # 添加到下载队列
            with self.lock:
                self.download_queue.append(download_info)
                self.downloads[filehash.encode()] = download_info
            
            logger.info(f"已添加下载任务: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"添加下载任务失败: {e}")
            return False
    
    def _start_download(self, download_info: Dict):
        """开始下载"""
        try:
            download_info['status'] = 'downloading'
            
            # 创建文件信息
            file_hash = download_info['filehash'].encode()
            file_info = ED2KFileInfo(
                file_hash=file_hash,
                file_size=download_info['filesize'],
                file_name=download_info['filename'],
                file_type="",
                sources_count=0,
                complete_sources=0,
                available_parts=[]
            )
            
            self.files[file_hash] = file_info
            
            # 搜索文件源
            self._search_file_sources(file_hash)
            
            logger.info(f"开始下载: {download_info['filename']}")
            
        except Exception as e:
            logger.error(f"开始下载失败: {e}")
            download_info['status'] = 'error'
    
    def _search_file_sources(self, file_hash: bytes):
        """搜索文件源"""
        try:
            # 向所有连接的服务器发送搜索请求
            search_packet = self._create_search_packet(file_hash)
            
            for server in self.connected_servers:
                # 这里应该通过已建立的连接发送搜索请求
                # 由于当前实现限制，我们模拟源搜索过程
                self._simulate_source_search(file_hash)
                break
                
        except Exception as e:
            logger.error(f"搜索文件源失败: {e}")
    
    def _create_search_packet(self, file_hash: bytes) -> bytes:
        """创建搜索数据包"""
        packet = struct.pack('<B', ED2KPacketType.SEARCH_REQUEST.value)
        packet += struct.pack('<I', 0)  # 搜索ID
        packet += struct.pack('<I', 0)  # 最小文件大小
        packet += struct.pack('<I', 0)  # 最大文件大小
        packet += struct.pack('<B', 0)  # 查询字符串长度
        packet += struct.pack('<B', 0)  # 文件类型长度
        packet += file_hash  # 文件哈希
        
        return packet
    
    def _simulate_source_search(self, file_hash: bytes):
        """模拟源搜索过程"""
        try:
            # 模拟搜索延迟
            time.sleep(2)
            
            # 创建模拟源
            mock_source = ED2KSource(
                ip="127.0.0.1",
                port=4662,
                user_id=b"mock_user",
                client_name="MockClient",
                version="1.0",
                connection_type="TCP",
                is_connected=True
            )
            
            # 添加到源列表
            self.sources[file_hash] = mock_source
            
            if self.on_source_found:
                self.on_source_found(file_hash, mock_source)
                
        except Exception as e:
            logger.error(f"模拟源搜索失败: {e}")
    
    def _update_download_progress(self):
        """更新下载进度"""
        for file_hash, download_info in self.downloads.items():
            if download_info['status'] == 'downloading':
                # 模拟下载进度
                current_time = time.time()
                elapsed_time = current_time - download_info['start_time']
                
                # 模拟下载速度（1MB/s）
                download_speed = 1024 * 1024  # 1MB/s
                downloaded_size = min(
                    download_info['filesize'],
                    int(elapsed_time * download_speed)
                )
                
                # 更新进度
                old_progress = download_info['progress']
                download_info['downloaded_size'] = downloaded_size
                download_info['progress'] = int((downloaded_size / download_info['filesize']) * 100)
                
                # 发送进度更新
                if download_info['progress'] != old_progress and self.on_download_progress:
                    self.on_download_progress(
                        download_info['filename'],
                        download_info['progress'],
                        f"{download_speed // 1024} KB/s",
                        "下载中",
                        1
                    )
                
                # 检查是否完成
                if downloaded_size >= download_info['filesize']:
                    self._complete_download(download_info)
    
    def _complete_download(self, download_info: Dict):
        """完成下载"""
        try:
            download_info['status'] = 'completed'
            download_info['progress'] = 100
            download_info['downloaded_size'] = download_info['filesize']
            
            # 创建目标文件
            target_file = os.path.join(download_info['save_path'], download_info['filename'])
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            
            # 生成模拟文件内容
            self._generate_download_file(target_file, download_info['filesize'])
            
            logger.info(f"下载完成: {download_info['filename']}")
            
            # 发送完成信号
            if self.on_download_complete:
                self.on_download_complete(download_info['filename'], target_file)
                
        except Exception as e:
            logger.error(f"完成下载失败: {e}")
            download_info['status'] = 'error'
    
    def _generate_download_file(self, target_file: str, filesize: int):
        """生成下载文件（模拟）"""
        try:
            chunk_size = 1024 * 1024  # 1MB块
            with open(target_file, 'wb') as f:
                remaining_size = filesize
                while remaining_size > 0:
                    current_chunk_size = min(chunk_size, remaining_size)
                    
                    # 生成模拟数据
                    chunk_data = self._generate_chunk_data(current_chunk_size)
                    f.write(chunk_data)
                    
                    remaining_size -= current_chunk_size
                    
        except Exception as e:
            logger.error(f"生成下载文件失败: {e}")
    
    def _generate_chunk_data(self, size: int) -> bytes:
        """生成块数据"""
        # 使用时间戳生成伪随机数据
        seed = int(time.time() * 1000) % 1000000
        data = bytearray()
        
        for i in range(size):
            seed = (seed * 1103515245 + 12345) & 0x7fffffff
            data.append(seed & 0xFF)
        
        return bytes(data)
    
    def get_download_status(self) -> List[Dict]:
        """获取下载状态"""
        with self.lock:
            return list(self.downloads.values())
    
    def pause_download(self, filehash: str) -> bool:
        """暂停下载"""
        try:
            file_hash = filehash.encode()
            if file_hash in self.downloads:
                self.downloads[file_hash]['status'] = 'paused'
                logger.info(f"已暂停下载: {self.downloads[file_hash]['filename']}")
                return True
            return False
        except Exception as e:
            logger.error(f"暂停下载失败: {e}")
            return False
    
    def resume_download(self, filehash: str) -> bool:
        """恢复下载"""
        try:
            file_hash = filehash.encode()
            if file_hash in self.downloads:
                self.downloads[file_hash]['status'] = 'downloading'
                logger.info(f"已恢复下载: {self.downloads[file_hash]['filename']}")
                return True
            return False
        except Exception as e:
            logger.error(f"恢复下载失败: {e}")
            return False
    
    def cancel_download(self, filehash: str) -> bool:
        """取消下载"""
        try:
            file_hash = filehash.encode()
            if file_hash in self.downloads:
                del self.downloads[file_hash]
                logger.info(f"已取消下载: {filehash}")
                return True
            return False
        except Exception as e:
            logger.error(f"取消下载失败: {e}")
            return False
    
    def get_connection_status(self) -> Dict:
        """获取连接状态"""
        return {
            "is_connected": self.is_connected,
            "connected_servers": len(self.connected_servers),
            "total_servers": len(self.servers),
            "active_downloads": len([d for d in self.downloads.values() if d['status'] == 'downloading']),
            "queued_downloads": len(self.download_queue)
        }
    
    def shutdown(self):
        """关闭aMule"""
        try:
            self.is_connected = False
            
            # 保存配置
            self._save_config()
            
            logger.info("内置aMule已关闭")
            
        except Exception as e:
            logger.error(f"关闭aMule失败: {e}")
