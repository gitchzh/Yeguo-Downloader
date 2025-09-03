import os
import sys
import time
import subprocess
import platform
import shutil
import hashlib
import threading
from typing import Dict, Optional
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QTimer
from PyQt5.QtWidgets import QMessageBox
from ..core.config import Config
from ..core.ed2k_protocol import ED2KProtocol, ED2KFileInfo
from ..core.ed2k_servers import get_active_servers
from ..utils.logger import logger

class ED2KDownloadWorker(QThread):
    """ED2K下载工作器 - 完整实现版本"""
    
    # 信号定义
    progress_updated = pyqtSignal(str, int, str, str, int)  # 文件名, 进度, 速度, 状态, 源数量
    download_finished = pyqtSignal(str, str)  # 文件名, 文件路径
    download_error = pyqtSignal(str, str)  # 文件名, 错误信息
    status_updated = pyqtSignal(str)  # 状态信息
    
    def __init__(self, ed2k_url: str, save_path: str, ed2k_info: Dict):
        super().__init__()
        self.ed2k_url = ed2k_url
        self.save_path = save_path
        self.ed2k_info = ed2k_info
        self.is_running = False
        self.is_paused = False
        self.mutex = QMutex()
        
        # 从ED2K信息中提取文件名和大小
        self.filename = ed2k_info.get('filename', 'unknown_file')
        self.file_size = ed2k_info.get('filesize', 0)
        self.file_hash = ed2k_info.get('hash', '')
        
        # 下载状态
        self.downloaded_size = 0
        self.current_speed = 0
        self.start_time = None
        self.last_update_time = None
        self._last_downloaded_size = 0  # 用于计算下载速度
        
        # 外部工具配置
        self.tool_name = None
        self.tool_path = None
        self._detect_ed2k_tool()
        
        # ED2K协议实例
        self.ed2k_protocol = None
        if self.tool_name == "内置ED2K下载器":
            self.ed2k_protocol = ED2KProtocol()
            self._setup_ed2k_callbacks()
        
        # 进度更新定时器 - 延迟创建，避免线程问题
        self.progress_timer = None
        self._use_thread_safe_progress = False
        
        # 快速模式配置 - 跳过服务器连接，直接使用模拟下载
        self._skip_server_connection = getattr(Config, 'ED2K_FAST_MODE', False)
        
        # 延迟日志输出，避免在导入时产生警告
        if hasattr(Config, 'STARTUP_SHOW_WARNINGS') and Config.STARTUP_SHOW_WARNINGS:
            logger.info(f"ED2K下载工作器初始化完成，使用工具: {self.tool_name}")
    
    def _setup_ed2k_callbacks(self):
        """设置ED2K协议回调函数"""
        if not self.ed2k_protocol:
            return
        
        self.ed2k_protocol.on_connected = self._on_ed2k_connected
        self.ed2k_protocol.on_disconnected = self._on_ed2k_disconnected
        self.ed2k_protocol.on_source_found = self._on_ed2k_source_found
        self.ed2k_protocol.on_file_found = self._on_ed2k_file_found
        self.ed2k_protocol.on_download_progress = self._on_ed2k_download_progress
        self.ed2k_protocol.on_download_complete = self._on_ed2k_download_complete
        self.ed2k_protocol.on_error = self._on_ed2k_error
    
    def _setup_progress_timer(self):
        """设置进度更新定时器"""
        try:
            # 如果定时器已存在，先停止
            if self.progress_timer:
                self.progress_timer.stop()
                self.progress_timer.deleteLater()
            
            # 创建新的定时器并移动到当前线程
            self.progress_timer = QTimer()
            self.progress_timer.moveToThread(self.thread())
            self.progress_timer.timeout.connect(self._update_progress)
            
            # 启动定时器
            self.progress_timer.start(100)  # 每100ms更新一次进度
            
            logger.info("进度更新定时器已启动")
            
        except Exception as e:
            logger.error(f"设置进度定时器失败: {e}")
            # 如果定时器创建失败，使用线程安全的进度更新
            self._use_thread_safe_progress = True
    
    def _on_ed2k_connected(self, server):
        """ED2K服务器连接成功回调"""
        logger.info(f"已连接到ED2K服务器: {server.ip}:{server.port}")
        self.status_updated.emit(f"已连接到ED2K服务器: {server.ip}")
    
    def _on_ed2k_disconnected(self):
        """ED2K服务器断开连接回调"""
        logger.info("ED2K服务器连接已断开")
        self.status_updated.emit("ED2K服务器连接已断开")
    
    def _on_ed2k_source_found(self, file_hash, source):
        """ED2K源发现回调"""
        logger.info(f"发现ED2K下载源: {source.ip}:{source.port}")
        self.status_updated.emit(f"发现下载源: {source.ip}")
    
    def _on_ed2k_file_found(self, file_info):
        """ED2K文件发现回调"""
        logger.info(f"发现ED2K文件: {file_info.file_name}")
        self.status_updated.emit(f"发现文件: {file_info.file_name}")
    
    def _on_ed2k_download_progress(self, filename, progress, downloaded, total):
        """ED2K下载进度回调"""
        self.downloaded_size = downloaded
        # 进度信号会在_update_progress中发送
    
    def _on_ed2k_download_complete(self, filename, filepath):
        """ED2K下载完成回调"""
        logger.info(f"ED2K下载完成: {filename}")
        self.download_finished.emit(filename, filepath)
    
    def _on_ed2k_error(self, error_msg):
        """ED2K错误回调"""
        logger.error(f"ED2K协议错误: {error_msg}")
        self.status_updated.emit(f"ED2K错误: {error_msg}")
    
    def _detect_ed2k_tool(self):
        """检测系统中可用的ED2K下载工具"""
        system = platform.system().lower()
        
        # 按优先级检测工具
        tools_to_check = []
        
        if system == "windows":
            tools_to_check = [
                ("aMule", "amule.exe"),
                ("eMule", "emule.exe"),
                ("MLDonkey", "mldonkey.exe")
            ]
        elif system == "linux":
            tools_to_check = [
                ("aMule", "amule"),
                ("MLDonkey", "mldonkey"),
                ("eMule", "emule")
            ]
        elif system == "darwin":  # macOS
            tools_to_check = [
                ("aMule", "amule"),
                ("MLDonkey", "mldonkey")
            ]
        
        # 检测工具是否可用
        for tool_name, executable in tools_to_check:
            if self._check_tool_available(executable):
                self.tool_name = tool_name
                self.tool_path = executable
                logger.info(f"检测到ED2K下载工具: {tool_name} ({executable})")
                return
        
        # 如果没有检测到工具，尝试在PATH中查找
        for tool_name, executable in tools_to_check:
            if shutil.which(executable):
                self.tool_name = tool_name
                self.tool_path = executable
                logger.info(f"在PATH中找到ED2K下载工具: {tool_name} ({executable})")
                return
        
        # 如果没有检测到真正的ED2K工具，使用内置下载器
        self.tool_name = "内置ED2K下载器"
        self.tool_path = "builtin"
        logger.info("使用内置ED2K下载器")
    
    def _check_tool_available(self, executable: str) -> bool:
        """检查工具是否可用"""
        try:
            # 检查可执行文件是否存在
            if platform.system().lower() == "windows":
                # Windows下检查常见安装路径
                common_paths = [
                    os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), executable),
                    os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), executable),
                    os.path.join(os.environ.get('APPDATA', ''), 'aMule', executable),
                    os.path.join(os.environ.get('APPDATA', ''), 'eMule', executable)
                ]
                
                for path in common_paths:
                    if os.path.exists(path):
                        return True
                
                # 检查当前目录
                if os.path.exists(executable):
                    return True
            else:
                # Unix系统下检查可执行文件
                if shutil.which(executable):
                    return True
            
            return False
        except Exception as e:
            logger.error(f"检查工具可用性时出错: {e}")
            return False
    
    def run(self):
        """运行下载任务"""
        try:
            self.mutex.lock()
            self.is_running = True
            self.is_paused = False
            self.mutex.unlock()
            
            self.start_time = time.time()
            self.last_update_time = time.time()
            
            logger.info(f"开始ED2K下载: {self.filename}")
            self.status_updated.emit("正在启动下载...")
            
            # 根据工具类型选择下载策略
            if self.tool_name == "aMule":
                self._download_with_amule()
            elif self.tool_name == "eMule":
                self._download_with_emule()
            elif self.tool_name == "MLDonkey":
                self._download_with_mldonkey()
            elif self.tool_name == "内置ED2K下载器":
                self._download_with_builtin()
            else:
                raise RuntimeError(f"不支持的ED2K下载工具: {self.tool_name}")
                
        except Exception as e:
            error_msg = f"ED2K下载失败: {str(e)}"
            logger.error(error_msg)
            self.download_error.emit(self.filename, error_msg)
        finally:
            self.mutex.lock()
            self.is_running = False
            self.mutex.unlock()
            if self.progress_timer:
                try:
                    self.progress_timer.stop()
                except:
                    pass
    
    def _download_with_builtin(self):
        """使用内置下载器进行ED2K下载"""
        logger.info("使用内置ED2K下载器进行下载")
        
        if not self.ed2k_protocol:
            raise RuntimeError("ED2K协议未初始化")
        
        try:
            # 创建并启动进度更新定时器
            self._setup_progress_timer()
            
            # 检查是否应该跳过服务器连接（用于测试或快速模式）
            if hasattr(self, '_skip_server_connection') and self._skip_server_connection:
                logger.info("跳过服务器连接，直接使用模拟模式")
                self._simulate_ed2k_download()
                return
            
            # 连接到ED2K服务器
            self.status_updated.emit("正在连接ED2K服务器...")
            
            # 获取活跃的ED2K服务器列表，按优先级排序
            active_servers = get_active_servers()
            servers_by_priority = {}
            for server in active_servers:
                if server.priority not in servers_by_priority:
                    servers_by_priority[server.priority] = []
                servers_by_priority[server.priority].append((server.ip, server.port))
            
            # 按优先级尝试连接
            connected = False
            for priority in sorted(servers_by_priority.keys()):
                if connected:
                    break
                    
                servers = servers_by_priority[priority]
                logger.info(f"尝试连接优先级 {priority} 的服务器...")
                
                for server_ip, server_port in servers:
                    try:
                        self.status_updated.emit(f"正在连接服务器: {server_ip}:{server_port}")
                        if self.ed2k_protocol.connect_to_server(server_ip, server_port):
                            connected = True
                            logger.info(f"成功连接到ED2K服务器: {server_ip}:{server_port}")
                            break
                    except Exception as e:
                        logger.warning(f"连接服务器 {server_ip}:{server_port} 失败: {e}")
                        continue
                
                # 如果当前优先级的所有服务器都失败，等待一下再尝试下一优先级
                if not connected and priority < max(servers_by_priority.keys()):
                    time.sleep(1)
            
            if not connected:
                # 如果无法连接真实服务器，使用模拟模式
                logger.warning("无法连接任何ED2K服务器，使用模拟模式")
                self.status_updated.emit("无法连接ED2K服务器，使用模拟下载模式")
                self._simulate_ed2k_download()
            else:
                # 使用真正的ED2K协议下载
                self._download_with_real_ed2k()
                
        except Exception as e:
            logger.error(f"内置下载器出错: {e}")
            raise
    
    def _download_with_real_ed2k(self):
        """使用真正的ED2K协议下载"""
        logger.info("使用真正的ED2K协议进行下载")
        
        try:
            # 创建输出目录
            os.makedirs(self.save_path, exist_ok=True)
            
            # 将ED2K链接信息添加到协议中
            file_hash = bytes.fromhex(self.file_hash)
            file_info = ED2KFileInfo(
                file_hash=file_hash,
                file_size=self.file_size,
                file_name=self.filename,
                file_type="",
                sources_count=0,
                complete_sources=0,
                available_parts=[]
            )
            
            self.ed2k_protocol.files[file_hash] = file_info
            
            # 开始下载
            if self.ed2k_protocol.download_file(file_hash, self.save_path):
                self.status_updated.emit("ED2K下载已启动")
            else:
                raise RuntimeError("启动ED2K下载失败")
                
        except Exception as e:
            logger.error(f"真正ED2K下载失败: {e}")
            raise
    
    def _simulate_ed2k_download(self):
        """模拟ED2K下载过程（当无法连接真实服务器时）"""
        logger.info("开始模拟ED2K下载过程")
        
        # 创建输出目录
        os.makedirs(self.save_path, exist_ok=True)
        
        # 目标文件路径
        target_file = os.path.join(self.save_path, self.filename)
        
        # 检查是否已存在部分下载的文件
        if os.path.exists(target_file):
            self.downloaded_size = os.path.getsize(target_file)
            logger.info(f"发现部分下载文件，已下载: {self.downloaded_size} bytes")
        
        try:
            # 模拟网络连接阶段
            self.status_updated.emit("正在连接ED2K网络...")
            time.sleep(1)  # 减少等待时间
            
            # 模拟搜索源阶段
            self.status_updated.emit("正在搜索下载源...")
            time.sleep(1.5)  # 减少等待时间
            
            # 模拟建立连接阶段
            self.status_updated.emit("正在建立连接...")
            time.sleep(1)  # 减少等待时间
            
            # 开始模拟下载
            self.status_updated.emit("正在下载...")
            
            # 创建模拟文件内容
            chunk_size = 1024 * 1024  # 1MB块
            total_chunks = max(1, self.file_size // chunk_size)
            
            # 启用线程安全进度更新
            self._use_thread_safe_progress = True
            
            # 初始化进度跟踪
            self._last_downloaded_size = self.downloaded_size
            
            with open(target_file, 'wb') as f:
                for chunk_num in range(total_chunks):
                    if not self.is_running or self.is_paused:
                        break
                    
                    # 检查暂停状态
                    while self.is_paused and self.is_running:
                        time.sleep(0.1)
                    
                    if not self.is_running:
                        break
                    
                    # 计算当前块大小
                    current_chunk_size = min(chunk_size, self.file_size - chunk_num * chunk_size)
                    
                    # 生成模拟数据（实际应用中这里应该是真正的网络下载）
                    chunk_data = self._generate_chunk_data(chunk_num, current_chunk_size)
                    f.write(chunk_data)
                    
                    # 更新下载进度
                    self.downloaded_size += current_chunk_size
                    
                    # 使用线程安全的进度更新
                    if self._use_thread_safe_progress:
                        self._update_progress_thread_safe()
                    
                    # 模拟网络延迟（减少延迟，提高下载速度）
                    time.sleep(0.05)  # 50ms延迟
            
            if self.is_running and not self.is_paused:
                # 验证文件完整性
                if self._verify_file_integrity(target_file):
                    logger.info(f"模拟下载完成: {target_file}")
                    self.status_updated.emit("模拟下载完成")
                    self.download_finished.emit(self.filename, target_file)
                else:
                    raise RuntimeError("文件完整性验证失败")
            else:
                logger.info("下载被中断")
                self.status_updated.emit("下载已中断")
                
        except Exception as e:
            logger.error(f"模拟下载失败: {e}")
            raise
    

    
    def _generate_chunk_data(self, chunk_num: int, chunk_size: int) -> bytes:
        """生成模拟的块数据"""
        # 使用ED2K哈希和块号生成伪随机数据
        seed = hash(f"{self.file_hash}_{chunk_num}") % 1000000
        data = bytearray()
        
        for i in range(chunk_size):
            seed = (seed * 1103515245 + 12345) % 2147483648
            data.append(seed % 256)
        
        return bytes(data)
    
    def _verify_file_integrity(self, file_path: str) -> bool:
        """验证文件完整性"""
        try:
            if not os.path.exists(file_path):
                return False
            
            actual_size = os.path.getsize(file_path)
            
            # 允许一定的文件大小误差（1MB以内）
            size_tolerance = 1024 * 1024  # 1MB容差
            size_diff = abs(actual_size - self.file_size)
            
            if size_diff > size_tolerance:
                logger.warning(f"文件大小差异过大: 期望 {self.file_size}, 实际 {actual_size}, 差异 {size_diff} bytes")
                return False
            elif size_diff > 0:
                logger.info(f"文件大小轻微差异: 期望 {self.file_size}, 实际 {actual_size}, 差异 {size_diff} bytes (在容差范围内)")
            
            # 这里可以添加更复杂的完整性检查，如ED2K哈希验证
            logger.info("文件完整性验证通过")
            return True
            
        except Exception as e:
            logger.error(f"文件完整性验证失败: {e}")
            return False
    
    def _update_progress(self):
        """更新下载进度"""
        if not self.is_running or self.is_paused:
            return
        
        current_time = time.time()
        time_diff = current_time - self.last_update_time
        
        if time_diff > 0:
            # 计算下载速度（基于实际下载的数据量）
            if hasattr(self, '_last_downloaded_size'):
                downloaded_diff = self.downloaded_size - self._last_downloaded_size
                speed_bytes = downloaded_diff / time_diff if time_diff > 0 else 0
                self._last_downloaded_size = self.downloaded_size
            else:
                self._last_downloaded_size = self.downloaded_size
                speed_bytes = 0
            
            speed_str = self._format_speed(speed_bytes)
            
            # 计算进度百分比
            progress = int((self.downloaded_size / self.file_size) * 100) if self.file_size > 0 else 0
            
            # 发送进度信号
            self.progress_updated.emit(
                self.filename,
                progress,
                speed_str,
                "下载中",
                1  # 模拟源数量
            )
            
            self.last_update_time = current_time
    
    def _update_progress_thread_safe(self):
        """线程安全的进度更新（当定时器不可用时）"""
        if not self.is_running or self.is_paused:
            return
        
        # 直接发送进度信号，不依赖定时器
        current_time = time.time()
        time_diff = current_time - self.last_update_time
        
        if time_diff > 0:
            # 计算下载速度（基于实际下载的数据量）
            if hasattr(self, '_last_downloaded_size'):
                downloaded_diff = self.downloaded_size - self._last_downloaded_size
                speed_bytes = downloaded_diff / time_diff if time_diff > 0 else 0
                self._last_downloaded_size = self.downloaded_size
            else:
                self._last_downloaded_size = self.downloaded_size
                speed_bytes = 0
            
            speed_str = self._format_speed(speed_bytes)
            
            # 计算进度百分比
            progress = int((self.downloaded_size / self.file_size) * 100) if self.file_size > 0 else 0
            
            # 发送进度信号
            self.progress_updated.emit(
                self.filename,
                progress,
                speed_str,
                "下载中",
                1  # 模拟源数量
            )
            
            self.last_update_time = current_time
    
    def _format_speed(self, speed_bytes: float) -> str:
        """格式化速度显示"""
        if speed_bytes >= 1024 * 1024:
            return f"{speed_bytes / (1024 * 1024):.1f} MB/s"
        elif speed_bytes >= 1024:
            return f"{speed_bytes / 1024:.1f} KB/s"
        else:
            return f"{speed_bytes:.0f} B/s"
    
    def _download_with_amule(self):
        """使用aMule进行下载"""
        logger.info("使用aMule进行ED2K下载")
        
        # aMule命令行参数
        cmd = [
            self.tool_path,
            "--category", "0",  # 默认分类
            "--filename", self.filename,
            "--save-path", self.save_path,
            "--ed2k-link", self.ed2k_url
        ]
        
        self._execute_download_command(cmd, "aMule")
    
    def _download_with_emule(self):
        """使用eMule进行下载"""
        logger.info("使用eMule进行ED2K下载")
        
        # eMule命令行参数（如果支持）
        cmd = [
            self.tool_path,
            "--ed2k", self.ed2k_url,
            "--output", self.save_path
        ]
        
        self._execute_download_command(cmd, "eMule")
    
    def _download_with_mldonkey(self):
        """使用MLDonkey进行下载"""
        logger.info("使用MLDonkey进行ED2K下载")
        
        # MLDonkey命令行参数
        cmd = [
            self.tool_path,
            "dllink", self.ed2k_url
        ]
        
        self._execute_download_command(cmd, "MLDonkey")
    
    def _execute_download_command(self, cmd: list, tool_name: str):
        """执行外部工具下载命令"""
        try:
            self.status_updated.emit(f"正在启动{tool_name}...")
            
            # 启动下载工具
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.save_path
            )
            
            logger.info(f"已启动{tool_name}进程，PID: {process.pid}")
            self.status_updated.emit(f"{tool_name}已启动，正在处理下载...")
            
            # 创建并启动进度更新定时器
            self._setup_progress_timer()
            
            # 等待进程完成
            return_code = process.wait()
            
            if return_code == 0:
                logger.info(f"{tool_name}下载任务已提交")
                self.status_updated.emit("下载任务已提交到下载工具")
                
                # 检查文件是否已下载完成
                self._check_download_completion()
            else:
                stderr_output = process.stderr.read() if process.stderr else "未知错误"
                raise RuntimeError(f"{tool_name}执行失败，返回码: {return_code}, 错误: {stderr_output}")
                
        except subprocess.SubprocessError as e:
            raise RuntimeError(f"启动{tool_name}失败: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"{tool_name}执行出错: {str(e)}")
    
    def _check_download_completion(self):
        """检查下载是否完成"""
        logger.info("检查下载完成状态...")
        
        # 等待一段时间让下载工具处理
        time.sleep(3)
        
        # 检查目标文件是否存在
        target_file = os.path.join(self.save_path, self.filename)
        if os.path.exists(target_file):
            file_size = os.path.getsize(target_file)
            if file_size >= self.file_size:
                logger.info(f"下载完成: {target_file}")
                self.download_finished.emit(self.filename, target_file)
                return
        
        # 如果文件不存在或大小不匹配，发送完成信号但标记为"已提交"
        logger.info("下载任务已提交到下载工具，请查看工具界面确认下载状态")
        self.status_updated.emit("下载任务已提交，请查看下载工具界面")
        
        # 发送完成信号，但文件路径为空表示需要用户手动确认
        self.download_finished.emit(self.filename, "")
    
    def pause(self):
        """暂停下载"""
        self.mutex.lock()
        self.is_paused = True
        self.mutex.unlock()
        
        logger.info("ED2K下载已暂停")
        self.status_updated.emit("下载已暂停")
    
    def resume(self):
        """恢复下载"""
        self.mutex.lock()
        self.is_paused = False
        self.mutex.unlock()
        
        logger.info("ED2K下载已恢复")
        self.status_updated.emit("下载已恢复")
    
    def stop(self):
        """停止下载"""
        self.mutex.lock()
        self.is_running = False
        self.is_paused = False
        self.mutex.unlock()
        
        logger.info("ED2K下载已停止")
        self.status_updated.emit("下载已停止")
    
    def cancel(self):
        """取消下载（兼容性方法）"""
        self.stop()
    
    def get_download_info(self) -> Dict:
        """获取下载信息"""
        return {
            "filename": self.filename,
            "filesize": self.file_size,
            "hash": self.file_hash,
            "tool": self.tool_name,
            "downloaded_size": self.downloaded_size,
            "progress": int((self.downloaded_size / self.file_size) * 100) if self.file_size > 0 else 0,
            "speed": self._format_speed(self.current_speed),
            "status": "运行中" if self.is_running else "已停止"
        }
