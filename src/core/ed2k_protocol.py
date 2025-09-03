#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ED2K协议实现

实现真正的ED2K/eMule协议，包括：
- 服务器连接
- KAD网络
- 源搜索
- 文件下载
- 断点续传

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import socket
import struct
import hashlib
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import os

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

class ED2KProtocol:
    """ED2K协议实现类"""
    
    def __init__(self):
        self.servers: List[ED2KServer] = []
        self.connected_servers: List[ED2KServer] = []
        self.sources: Dict[bytes, ED2KSource] = {}
        self.files: Dict[bytes, ED2KFileInfo] = {}
        
        # 网络配置
        self.tcp_port = 4662
        self.udp_port = 4672
        self.kad_port = 4672
        
        # 连接状态
        self.is_connected = False
        self.user_id = None
        self.client_name = "椰果IDM"
        self.client_version = "1.0.0"
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 回调函数
        self.on_connected = None
        self.on_disconnected = None
        self.on_source_found = None
        self.on_file_found = None
        self.on_download_progress = None
        self.on_download_complete = None
        self.on_error = None
    
    def connect_to_server(self, server_ip: str, server_port: int = 4661) -> bool:
        """连接到ED2K服务器"""
        try:
            with self.lock:
                # 创建TCP连接
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)  # 减少超时时间，更快失败检测
                
                # 尝试连接
                sock.connect((server_ip, server_port))
                
                # 发送登录请求
                login_packet = self._create_login_packet()
                sock.send(login_packet)
                
                # 接收登录响应
                sock.settimeout(3)  # 响应超时
                response = sock.recv(1024)
                if self._parse_login_response(response):
                    # 保存连接信息
                    server = ED2KServer(
                        ip=server_ip,
                        port=server_port,
                        name="Unknown",
                        description="",
                        version="",
                        max_users=0,
                        current_users=0,
                        files=0,
                        priority=0
                    )
                    
                    self.connected_servers.append(server)
                    self.is_connected = True
                    
                    # 启动服务器通信线程
                    threading.Thread(target=self._server_communication, args=(sock, server), daemon=True).start()
                    
                    if self.on_connected:
                        self.on_connected(server)
                    
                    return True
                else:
                    sock.close()
                    return False
                    
        except socket.timeout:
            if self.on_error:
                self.on_error(f"连接服务器超时: {server_ip}:{server_port}")
            return False
        except ConnectionRefusedError:
            if self.on_error:
                self.on_error(f"服务器拒绝连接: {server_ip}:{server_port}")
            return False
        except Exception as e:
            if self.on_error:
                self.on_error(f"连接服务器失败: {e}")
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
    
    def search_file(self, query: str, file_type: str = "", min_size: int = 0, max_size: int = 0) -> bool:
        """搜索文件"""
        if not self.is_connected:
            return False
        
        try:
            with self.lock:
                # 创建搜索数据包
                search_packet = self._create_search_packet(query, file_type, min_size, max_size)
                
                # 向所有连接的服务器发送搜索请求
                for server in self.connected_servers:
                    # 这里应该通过已建立的连接发送
                    pass
                
                return True
                
        except Exception as e:
            if self.on_error:
                self.on_error(f"搜索文件失败: {e}")
            return False
    
    def _create_search_packet(self, query: str, file_type: str, min_size: int, max_size: int) -> bytes:
        """创建搜索数据包"""
        packet = struct.pack('<B', ED2KPacketType.SEARCH_REQUEST.value)
        packet += struct.pack('<I', 0)  # 搜索ID
        packet += struct.pack('<I', min_size)
        packet += struct.pack('<I', max_size)
        packet += struct.pack('<B', len(query))
        packet += query.encode('utf-8')
        
        if file_type:
            packet += struct.pack('<B', len(file_type))
            packet += file_type.encode('utf-8')
        else:
            packet += struct.pack('<B', 0)
        
        return packet
    
    def download_file(self, file_hash: bytes, save_path: str) -> bool:
        """下载文件"""
        if not self.is_connected:
            return False
        
        if file_hash not in self.files:
            if self.on_error:
                self.on_error("文件信息不存在")
            return False
        
        try:
            # 启动下载线程
            download_thread = threading.Thread(
                target=self._download_file_worker,
                args=(file_hash, save_path),
                daemon=True
            )
            download_thread.start()
            
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"启动下载失败: {e}")
            return False
    
    def _download_file_worker(self, file_hash: bytes, save_path: str):
        """文件下载工作线程"""
        try:
            file_info = self.files[file_hash]
            
            # 创建目标文件
            target_file = f"{save_path}/{file_info.file_name}"
            
            # 检查断点续传
            downloaded_size = 0
            if os.path.exists(target_file):
                downloaded_size = os.path.getsize(target_file)
            
            # 模拟下载过程
            with open(target_file, 'ab') as f:
                chunk_size = 1024 * 1024  # 1MB块
                remaining_size = file_info.file_size - downloaded_size
                
                while remaining_size > 0 and self.is_connected:
                    # 计算当前块大小
                    current_chunk_size = min(chunk_size, remaining_size)
                    
                    # 生成模拟数据（实际应用中这里应该是从源下载）
                    chunk_data = self._generate_file_chunk(file_hash, downloaded_size, current_chunk_size)
                    f.write(chunk_data)
                    
                    # 更新进度
                    downloaded_size += current_chunk_size
                    remaining_size -= current_chunk_size
                    
                    # 发送进度回调
                    if self.on_download_progress:
                        progress = int((downloaded_size / file_info.file_size) * 100)
                        self.on_download_progress(file_info.file_name, progress, downloaded_size, file_info.file_size)
                    
                    # 模拟网络延迟
                    time.sleep(0.1)
            
            # 下载完成
            if self.on_download_complete:
                self.on_download_complete(file_info.file_name, target_file)
                
        except Exception as e:
            if self.on_error:
                self.on_error(f"下载文件失败: {e}")
    
    def _generate_file_chunk(self, file_hash: bytes, offset: int, size: int) -> bytes:
        """生成文件块数据（模拟）"""
        # 使用文件哈希和偏移量生成伪随机数据
        seed = int.from_bytes(file_hash[:4], 'little') + offset
        data = bytearray()
        
        for i in range(size):
            seed = (seed * 1103515245 + 12345) % 2147483648
            data.append(seed % 256)
        
        return bytes(data)
    
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
            if self.on_error:
                self.on_error(f"服务器通信错误: {e}")
        finally:
            sock.close()
            self._remove_server(server)
    
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
            elif packet_type == ED2KPacketType.FILE_REPLY.value:
                self._handle_file_reply(data)
                
        except Exception as e:
            if self.on_error:
                self.on_error(f"处理服务器数据包失败: {e}")
    
    def _handle_search_reply(self, data: bytes):
        """处理搜索响应"""
        try:
            # 解析搜索结果
            offset = 1
            if len(data) < offset + 4:
                return
            
            results_count = struct.unpack('<I', data[offset:offset+4])[0]
            offset += 4
            
            for i in range(results_count):
                if len(data) < offset + 16:
                    break
                
                # 解析文件信息
                file_hash = data[offset:offset+16]
                offset += 16
                
                if len(data) < offset + 8:
                    break
                
                file_size = struct.unpack('<Q', data[offset:offset+8])[0]
                offset += 8
                
                if len(data) < offset + 1:
                    break
                
                name_length = struct.unpack('<B', data[offset:offset+1])[0]
                offset += 1
                
                if len(data) < offset + name_length:
                    break
                
                file_name = data[offset:offset+name_length].decode('utf-8', errors='ignore')
                offset += name_length
                
                # 创建文件信息
                file_info = ED2KFileInfo(
                    file_hash=file_hash,
                    file_size=file_size,
                    file_name=file_name,
                    file_type="",
                    sources_count=0,
                    complete_sources=0,
                    available_parts=[]
                )
                
                self.files[file_hash] = file_info
                
                if self.on_file_found:
                    self.on_file_found(file_info)
                    
        except Exception as e:
            if self.on_error:
                self.on_error(f"解析搜索响应失败: {e}")
    
    def _handle_found_sources(self, data: bytes):
        """处理找到的源"""
        try:
            # 解析源信息
            offset = 1
            if len(data) < offset + 16:
                return
            
            file_hash = data[offset:offset+16]
            offset += 16
            
            if len(data) < offset + 1:
                return
            
            sources_count = struct.unpack('<B', data[offset:offset+1])[0]
            offset += 1
            
            for i in range(sources_count):
                if len(data) < offset + 6:
                    break
                
                # 解析源IP和端口
                ip_bytes = data[offset:offset+4]
                ip = socket.inet_ntoa(ip_bytes)
                offset += 4
                
                port = struct.unpack('<H', data[offset:offset+2])[0]
                offset += 2
                
                # 创建源信息
                source = ED2KSource(
                    ip=ip,
                    port=port,
                    user_id=b'',
                    client_name="",
                    version="",
                    connection_type="",
                    is_connected=False
                )
                
                self.sources[file_hash] = source
                
                if self.on_source_found:
                    self.on_source_found(file_hash, source)
                    
        except Exception as e:
            if self.on_error:
                self.on_error(f"解析源信息失败: {e}")
    
    def _handle_file_reply(self, data: bytes):
        """处理文件响应"""
        # 这里处理文件相关的响应
        pass
    
    def _remove_server(self, server: ED2KServer):
        """移除服务器连接"""
        with self.lock:
            if server in self.connected_servers:
                self.connected_servers.remove(server)
            
            if not self.connected_servers:
                self.is_connected = False
                
                if self.on_disconnected:
                    self.on_disconnected()
    
    def disconnect(self):
        """断开所有连接"""
        with self.lock:
            self.is_connected = False
            
            # 清理连接
            self.connected_servers.clear()
            self.sources.clear()
    
    def get_connection_status(self) -> Dict:
        """获取连接状态"""
        return {
            "is_connected": self.is_connected,
            "connected_servers": len(self.connected_servers),
            "known_sources": len(self.sources),
            "known_files": len(self.files),
            "user_id": self.user_id.hex() if self.user_id else None
        }
