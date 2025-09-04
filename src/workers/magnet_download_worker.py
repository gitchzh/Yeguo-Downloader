"""
磁力下载工作线程模块

该模块包含磁力链接下载的工作线程类，负责：
- 磁力链接的种子下载
- BitTorrent协议支持
- 实时下载进度监控
- 种子健康度检查
- 下载速度控制

主要类：
- MagnetDownloadWorker: 磁力下载工作线程类

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import os
import time
import threading
from typing import Dict, Optional, List
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
import logging

logger = logging.getLogger(__name__)

try:
    import libtorrent as lt
    LIBTORRENT_AVAILABLE = True
except ImportError:
    LIBTORRENT_AVAILABLE = False
    # 根据配置决定是否显示警告
    try:
        from ..core.config import Config
        if Config.STARTUP_SHOW_WARNINGS:
            logger.warning("libtorrent库未安装，磁力下载功能将不可用")
    except ImportError:
        # 如果配置模块还未导入，静默处理
        logger.debug("配置模块未导入，跳过libtorrent检查")


class MagnetDownloadWorker(QThread):
    """磁力下载工作线程"""
    
    # 信号定义
    progress_signal = pyqtSignal(dict)  # 下载进度信息
    status_signal = pyqtSignal(str)     # 状态信息
    log_signal = pyqtSignal(str)        # 日志信息
    finished = pyqtSignal(str)          # 下载完成信号
    error = pyqtSignal(str)             # 错误信号
    
    def __init__(self, magnet_url: str, save_path: str, magnet_info: Dict):
        super().__init__()
        self.magnet_url = magnet_url
        self.save_path = save_path
        self.magnet_info = magnet_info
        
        # 线程控制
        self._is_cancelled = False
        self._is_paused = False
        self._mutex = QMutex()
        self._condition = QWaitCondition()
        
        # libtorrent相关
        self.session: Optional[lt.session] = None
        self.torrent_handle: Optional[lt.torrent_handle] = None
        self.add_torrent_params: Optional[lt.add_torrent_params] = None
        
        # 下载状态
        self.download_start_time = time.time()
        self.last_progress_update = time.time()
        self.progress_update_interval = 1.0  # 进度更新间隔（秒）
        
        # 检查libtorrent可用性
        if not LIBTORRENT_AVAILABLE:
            raise RuntimeError("libtorrent库未安装，无法使用磁力下载功能")
    
    def run(self) -> None:
        """运行下载线程"""
        try:
            self.status_signal.emit("初始化磁力下载...")
            self._check_cancelled()
            
            # 初始化libtorrent会话
            self._init_session()
            self._check_cancelled()
            
            # 添加磁力链接到会话
            self._add_magnet_link()
            self._check_cancelled()
            
            # 开始下载循环
            self._download_loop()
            
        except Exception as e:
            error_msg = f"磁力下载失败: {e}"
            logger.error(error_msg)
            # 只有在非暂停和非取消状态下才发送错误信号
            if not self._is_cancelled and not self._is_paused:
                self.error.emit(error_msg)
        finally:
            self._cleanup()
    
    def _init_session(self) -> None:
        """初始化libtorrent会话"""
        try:
            self.status_signal.emit("配置下载会话...")
            
            # 创建会话
            self.session = lt.session()
            
            # 配置会话参数
            settings = {
                'enable_dht': True,
                'enable_lsd': True,
                'enable_upnp': True,
                'enable_nat_pmp': True,
                'anonymous_mode': False,
                'download_rate_limit': 0,  # 无限制
                'upload_rate_limit': 0,    # 无限制
                'max_connections_per_torrent': 200,
                'max_uploads_per_torrent': 10,
                'max_connections_global': 500,
                'max_uploads_global': 50,
            }
            
            self.session.apply_settings(settings)
            
            # 添加DHT路由器
            dht_routers = [
                ('router.bittorrent.com', 6881),
                ('router.utorrent.com', 6881),
                ('dht.transmissionbt.com', 6881),
            ]
            
            for router, port in dht_routers:
                self.session.add_dht_router(router, port)
            
            self.status_signal.emit("会话初始化完成")
            
        except Exception as e:
            raise RuntimeError(f"初始化会话失败: {e}")
    
    def _add_magnet_link(self) -> None:
        """添加磁力链接到会话"""
        try:
            self.status_signal.emit("添加磁力链接...")
            
            # 创建添加种子参数
            self.add_torrent_params = lt.add_magnet_link_params()
            self.add_torrent_params.url = self.magnet_url
            self.add_torrent_params.save_path = self.save_path
            
            # 添加到会话
            self.torrent_handle = self.session.add_torrent(self.add_torrent_params)
            
            # 设置种子优先级
            self.torrent_handle.set_sequential_download(False)
            self.torrent_handle.set_priority(0)  # 最高优先级
            
            self.status_signal.emit("磁力链接添加成功，等待连接...")
            
        except Exception as e:
            raise RuntimeError(f"添加磁力链接失败: {e}")
    
    def _download_loop(self) -> None:
        """下载主循环"""
        try:
            while not self._is_cancelled:
                # 检查暂停状态
                if self._is_paused:
                    self._wait_for_resume()
                    continue
                
                # 获取种子状态
                status = self.torrent_handle.status()
                
                # 检查是否完成
                if status.is_seeding:
                    self.status_signal.emit("下载完成，正在做种...")
                    self._emit_progress(status)
                    break
                
                # 检查错误
                if status.has_metadata and status.error:
                    raise RuntimeError(f"种子错误: {status.error}")
                
                # 发送进度信号
                self._emit_progress(status)
                
                # 检查连接状态
                if not status.has_metadata:
                    self.status_signal.emit("正在获取种子信息...")
                elif status.num_peers == 0:
                    self.status_signal.emit("等待连接...")
                else:
                    self.status_signal.emit(f"下载中... 连接数: {status.num_peers}")
                
                # 等待一段时间
                time.sleep(0.5)
                
                # 检查超时
                if time.time() - self.download_start_time > 300:  # 5分钟超时
                    if not status.has_metadata:
                        raise RuntimeError("获取种子信息超时")
                    elif status.download_payload_rate == 0:
                        raise RuntimeError("下载速度过慢，可能没有可用连接")
            
            # 下载完成
            if not self._is_cancelled:
                self._handle_download_complete()
                
        except Exception as e:
            raise RuntimeError(f"下载循环失败: {e}")
    
    def _emit_progress(self, status) -> None:
        """发送进度信号"""
        try:
            current_time = time.time()
            if current_time - self.last_progress_update >= self.progress_update_interval:
                # 计算进度信息
                progress_data = {
                    'status': 'downloading',
                    'total_size': status.total_wanted,
                    'downloaded_size': status.total_wanted - status.total_wanted_remaining,
                    'download_rate': status.download_payload_rate,
                    'upload_rate': status.upload_payload_rate,
                    'num_peers': status.num_peers,
                    'num_seeds': status.num_seeds,
                    'progress': 0.0,
                    'eta': 0,
                    'has_metadata': status.has_metadata,
                    'state': str(status.state)
                }
                
                # 计算进度百分比
                if status.total_wanted > 0:
                    progress_data['progress'] = (
                        (status.total_wanted - status.total_wanted_remaining) / 
                        status.total_wanted * 100
                    )
                
                # 计算剩余时间
                if status.download_payload_rate > 0:
                    remaining_bytes = status.total_wanted_remaining
                    progress_data['eta'] = int(remaining_bytes / status.download_payload_rate)
                
                self.progress_signal.emit(progress_data)
                self.last_progress_update = current_time
                
        except Exception as e:
            logger.error(f"发送进度信号失败: {e}")
    
    def _handle_download_complete(self) -> None:
        """处理下载完成"""
        try:
            status = self.torrent_handle.status()
            
            if status.has_metadata:
                # 获取文件名
                info = status.torrent_file
                if info:
                    filename = info.name()
                    filepath = os.path.join(self.save_path, filename)
                    
                    self.status_signal.emit(f"下载完成: {filename}")
                    self.finished.emit(filepath)
                else:
                    self.finished.emit(self.save_path)
            else:
                self.finished.emit(self.save_path)
                
        except Exception as e:
            logger.error(f"处理下载完成失败: {e}")
            self.finished.emit(self.save_path)
    
    def _wait_for_resume(self) -> None:
        """等待恢复下载"""
        try:
            self._mutex.lock()
            self._condition.wait(self._mutex, 100)  # 等待100ms
        finally:
            self._mutex.unlock()
    
    def _check_cancelled(self) -> None:
        """检查是否被取消"""
        if self._is_cancelled:
            raise RuntimeError("下载已取消")
    
    def _cleanup(self) -> None:
        """清理资源"""
        try:
            if self.torrent_handle:
                self.session.remove_torrent(self.torrent_handle)
            
            if self.session:
                self.session.pause()
                
        except Exception as e:
            logger.error(f"清理资源失败: {e}")
    
    def cancel(self) -> None:
        """取消下载"""
        self._is_cancelled = True
        self.status_signal.emit("正在取消下载...")
    
    def pause(self) -> None:
        """暂停下载"""
        self._is_paused = True
        if self.torrent_handle:
            self.torrent_handle.pause()
        self.status_signal.emit("下载已暂停")
    
    def resume(self) -> None:
        """恢复下载"""
        self._is_paused = False
        if self.torrent_handle:
            self.torrent_handle.resume()
        self.status_signal.emit("下载已恢复")
        self._condition.wakeAll()
    
    def get_download_info(self) -> Dict:
        """获取下载信息"""
        if not self.torrent_handle:
            return {}
        
        try:
            status = self.torrent_handle.status()
            return {
                'name': status.name if status.has_metadata else '未知',
                'size': status.total_wanted,
                'progress': status.progress,
                'download_rate': status.download_payload_rate,
                'upload_rate': status.upload_payload_rate,
                'num_peers': status.num_peers,
                'num_seeds': status.num_seeds,
                'state': str(status.state),
                'has_metadata': status.has_metadata
            }
        except Exception as e:
            logger.error(f"获取下载信息失败: {e}")
            return {}
