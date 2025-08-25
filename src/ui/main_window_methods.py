"""主窗口方法模块"""

import os
import re
from typing import Dict, List, Optional, Tuple, Any
from collections import OrderedDict

from PyQt5.QtWidgets import (
    QMessageBox, QFileDialog, QTreeWidgetItem, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu
)
from PyQt5.QtCore import Qt, QUrl, QPoint
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtGui import QDesktopServices

from ..core.config import Config
from ..utils.logger import logger
from ..utils.file_utils import sanitize_filename, format_size, check_ffmpeg
from ..workers.parse_worker import ParseWorker
from ..workers.download_worker import DownloadWorker


def is_standard_resolution(resolution: str) -> bool:
    """
    判断是否为标准分辨率
    
    Args:
        resolution: 分辨率字符串，如 "1920x1080", "1280x720" 等
        
    Returns:
        bool: 是否为标准分辨率
    """
    # 标准分辨率列表 - 扩展支持更多常见分辨率
    standard_resolutions = {
        # 4K
        "3840x2160", "4096x2160",
        # 2K
        "2560x1440", "2048x1080",
        # 1080P
        "1920x1080", "1920x1088", "1440x1080",  # 添加1440x1080（4:3比例1080P）
        # 720P
        "1280x720", "1280x736", "960x720",  # 添加960x720（4:3比例720P）
        # 480P - 添加更多变体
        "854x480", "848x480", "832x480", "852x480", "850x480", "856x480", "858x480", "860x480", "862x480", "864x480", "866x480", "868x480", "870x480", "872x480", "874x480", "876x480", "878x480", "880x480",
        # 360P
        "640x360", "640x368", "640x480",  # 添加640x480（4:3比例480P）
        # 240P
        "426x240", "424x240", "480x360",  # 添加480x360（4:3比例360P）
        # 144P
        "256x144", "256x160"
    }
    
    # 清理分辨率字符串，移除空格和特殊字符
    clean_resolution = resolution.strip().lower()
    
    # 检查是否在标准分辨率列表中
    if clean_resolution in standard_resolutions:
        return True
    
    # 检查是否为音频格式（没有分辨率）
    if clean_resolution in ["audio only", "audio_only", "audio"]:
        return True
    
    # 检查是否为标准P格式（如1080p, 720p等）
    if re.match(r"^\d+p$", clean_resolution):
        p_value = int(clean_resolution[:-1])
        if p_value in [144, 240, 360, 480, 720, 1080, 1440, 2160]:
            return True
    
    # 检查是否为接近标准分辨率的格式（允许±1像素的误差）
    if "x" in clean_resolution:
        try:
            width, height = clean_resolution.split("x")
            width, height = int(width), int(height)
            
            # 检查是否接近标准分辨率
            for std_res in standard_resolutions:
                if "x" in std_res:
                    std_width, std_height = std_res.split("x")
                    std_width, std_height = int(std_width), int(std_height)
                    
                    # 允许±4像素的误差，以包含更多变体
                    if abs(width - std_width) <= 4 and abs(height - std_height) <= 4:
                        return True
        except (ValueError, IndexError):
            pass
    
    return False


def filter_formats(formats: List[Dict]) -> List[Dict]:
    """
    过滤格式列表，只保留标准分辨率的格式
    
    Args:
        formats: 原始格式列表
        
    Returns:
        List[Dict]: 过滤后的格式列表
    """
    filtered_formats = []
    
    for format_info in formats:
        # 获取分辨率信息
        resolution = format_info.get("resolution", "")
        format_note = format_info.get("format_note", "")
        width = format_info.get("width")
        height = format_info.get("height")
        
        # 构建完整的分辨率字符串
        resolution_str = resolution
        if not resolution_str and width and height:
            resolution_str = f"{width}x{height}"
        elif not resolution_str and format_note:
            resolution_str = format_note
        
        # 检查是否为音频格式
        acodec = format_info.get("acodec", "none")
        vcodec = format_info.get("vcodec", "none")
        if acodec != "none" and vcodec == "none":
            # 音频格式，保留
            filtered_formats.append(format_info)
            continue
        
        # 只保留标准分辨率的格式
        if is_standard_resolution(resolution_str):
            filtered_formats.append(format_info)
        else:
            logger.info(f"过滤掉非标准分辨率: {resolution_str} (原始: {resolution}, 说明: {format_note}, 宽高: {width}x{height})")
    
    return filtered_formats


class VideoDownloaderMethods:
    """主窗口类的方法实现"""
    
    def load_settings(self) -> None:
        """加载保存的设置"""
        self.save_path = self.settings.value("save_path", os.getcwd())
        self.path_label.setText(f"保存路径: {self.save_path}")

    def choose_save_path(self) -> None:
        """选择保存路径"""
        folder = QFileDialog.getExistingDirectory(self, "选择保存路径", self.save_path)
        if folder:
            self.save_path = folder
            self.path_label.setText(f"保存路径: {self.save_path}")

    def validate_url(self, url: str) -> bool:
        """验证 URL 是否有效"""
        return bool(re.match(r"^https?://.*", url))

    def toggle_checkbox(self, item: QTreeWidgetItem, column: int) -> None:
        """双击切换复选框状态"""
        if item and column == 0:
            current_state = item.checkState(0)
            new_state = Qt.Checked if current_state == Qt.Unchecked else Qt.Unchecked
            item.setCheckState(0, new_state)
            self.on_item_changed(item, 0)

    def select_all_formats(self) -> None:
        """全选所有格式"""
        for i in range(self.format_tree.topLevelItemCount()):
            root_item = self.format_tree.topLevelItem(i)
            # 选择分辨率节点，会自动选择其子项
            root_item.setCheckState(0, Qt.Checked)
        self.update_selection_count()
        self.update_smart_select_button_text()

    def deselect_all_formats(self) -> None:
        """取消全选所有格式"""
        for i in range(self.format_tree.topLevelItemCount()):
            root_item = self.format_tree.topLevelItem(i)
            # 取消选择分辨率节点，会自动取消选择其子项
            root_item.setCheckState(0, Qt.Unchecked)
        self.update_selection_count()
        self.update_smart_select_button_text()

    def invert_selection(self) -> None:
        """反选所有格式"""
        for i in range(self.format_tree.topLevelItemCount()):
            root_item = self.format_tree.topLevelItem(i)
            # 反选分辨率节点，会自动反选其子项
            current_state = root_item.checkState(0)
            new_state = Qt.Checked if current_state == Qt.Unchecked else Qt.Unchecked
            root_item.setCheckState(0, new_state)
        self.update_selection_count()
        self.update_smart_select_button_text()

    def update_selection_count(self) -> None:
        """更新选择计数"""
        selected_count = 0
        for i in range(self.format_tree.topLevelItemCount()):
            root_item = self.format_tree.topLevelItem(i)
            # 统计子项的选择状态（复选框在第1列）
            for j in range(root_item.childCount()):
                if root_item.child(j).checkState(1) == Qt.Checked:
                    selected_count += 1
        self.selection_count_label.setText(f"已选择: {selected_count} 项")
        
        # 根据选择状态启用/禁用下载按钮
        self.smart_download_button.setEnabled(selected_count > 0)
        
        # 更新状态栏文件信息
        if self.formats:
            self.update_status_bar(
                self.status_label_main.text(),
                self.status_label_progress.text(),
                f"已选择: {selected_count} / {len(self.formats)} 项"
            )

    def parse_video(self) -> None:
        """解析视频链接"""
        urls = [url.strip() for url in self.url_input.toPlainText().split("\n") if url.strip()]
        if not urls:
            QMessageBox.warning(self, "错误", "请输入至少一个有效的视频链接！")
            return

        invalid_urls = [url for url in urls if not self.validate_url(url)]
        if invalid_urls:
            QMessageBox.warning(self, "错误", f"以下链接格式无效:\n" + "\n".join(invalid_urls))
            return

        self.format_tree.clear()
        self.formats = []
        self.smart_download_button.setEnabled(False)
        
        # 禁用选择按钮
        self.smart_select_button.setEnabled(False)
        
        # 重置选择计数
        self.selection_count_label.setText("已选择: 0 项")
        
        logger.info("开始解析视频...")
        self.update_status_bar("正在解析视频...", "", "")
        self.status_scroll_label.setText("")  # 清空滚动状态

        self.parse_button.setEnabled(False)
        self.parse_workers = []
        self.total_urls = len(urls)
        self.parsed_count = 0
        for url in urls:
            worker = ParseWorker(url)
            worker.status_signal.connect(self.update_scroll_status)  # 连接状态信号
            worker.finished.connect(lambda info, u=url: self.cache_and_finish(info, u))
            worker.error.connect(self.on_parse_error)
            worker.start()
            self.parse_workers.append(worker)

    def cache_and_finish(self, info: Dict, url: str) -> None:
        """缓存解析结果并完成解析"""
        try:
            self.parse_cache[info.get("webpage_url", url)] = info
            if len(self.parse_cache) > Config.CACHE_LIMIT:
                self.parse_cache.popitem(last=False)

            # 立即处理并显示当前视频的解析结果
            self.on_parse_finished(info)

            self.parsed_count += 1
            
            # 实时更新状态栏显示解析进度
            progress_text = f"解析进度: {self.parsed_count}/{self.total_urls}"
            self.update_status_bar(progress_text, "", "")
            
            # 如果所有视频都解析完成，执行最终处理
            if self.parsed_count == self.total_urls and all(not w.isRunning() for w in self.parse_workers):
                self.finalize_parse()
                if hasattr(self, "video_root"):
                    del self.video_root
        except Exception as e:
            logger.error(f"缓存解析结果失败: {str(e)}")
            self.update_status_bar(f"解析失败: {str(e)}", "", "")
            self.parse_button.setEnabled(True)

    def finalize_parse(self) -> None:
        """完成解析并更新 UI"""
        if self.formats:
            # 启用选择按钮
            self.smart_select_button.setEnabled(True)
            
            # 更新选择计数
            self.update_selection_count()
            
            # 刷新下载状态显示
            self.refresh_download_status()
            
            logger.info("所有视频解析完成")
            self.update_status_bar("解析完成，请选择下载格式", "", f"共找到 {len(self.formats)} 个格式")
            self.status_scroll_label.setText("解析完成 ✓")  # 清空滚动状态
            # 确保列宽设置正确
            self.ensure_column_widths()
            QMessageBox.information(self, "成功", "视频解析完成，请选择下载格式")
        else:
            logger.warning("未找到任何可用格式")
            self.update_status_bar("未找到可用格式", "", "")
            self.status_scroll_label.setText("解析失败 ✗")  # 清空滚动状态
            QMessageBox.warning(self, "错误", "未找到可用格式！")
        self.parse_button.setEnabled(True)



    def get_resolution(self, f: Dict) -> str:
        """从格式信息中提取分辨率并标准化"""
        # 首先检查 resolution 字段
        resolution = f.get("resolution", "")
        if resolution and resolution != "audio only" and "x" in resolution:
            return self.standardize_resolution(resolution)
            
        # 检查 width 和 height 字段
        width = f.get("width")
        height = f.get("height")
        if width and height:
            return self.standardize_resolution(f"{width}x{height}")
        elif height:
            return f"{height}p"
            
        # 检查 format_note 字段
        format_note = f.get("format_note", "")
        if format_note and format_note != "unknown":
            # 尝试从 format_note 中提取分辨率
            if "x" in format_note:
                return self.standardize_resolution(format_note)
            elif format_note.isdigit():
                return f"{format_note}p"
                
        # 检查 format 字段
        format_str = f.get("format", "")
        if "x" in format_str:
            match = re.search(r"(\d+)x(\d+)", format_str)
            if match:
                return self.standardize_resolution(f"{match.group(1)}x{match.group(2)}")
                
        # 检查是否为音频格式
        if f.get("acodec", "none") != "none" and f.get("vcodec", "none") == "none":
            return "audio only"
            
        # 如果都找不到，返回未知
        return "未知"

    def standardize_resolution(self, resolution: str) -> str:
        """标准化分辨率到主流分辨率"""
        if not resolution or "x" not in resolution:
            return resolution
            
        try:
            width, height = resolution.split("x")
            width, height = int(width), int(height)
            
            # 1080P 变体 → 1920x1080 或 1440x1080
            if abs(height - 1080) <= 4:
                if abs(width - 1920) <= 4:
                    return "1920x1080"
                elif abs(width - 1440) <= 4:
                    return "1440x1080"
            # 720P 变体 → 1280x720 或 960x720
            elif abs(height - 720) <= 4:
                if abs(width - 1280) <= 4:
                    return "1280x720"
                elif abs(width - 960) <= 4:
                    return "960x720"
            # 480P 变体 → 852x480 或 640x480
            elif abs(height - 480) <= 4:
                if abs(width - 852) <= 4:
                    return "852x480"
                elif abs(width - 640) <= 4:
                    return "640x480"
            # 360P 变体 → 640x360 或 480x360
            elif abs(height - 360) <= 4:
                if abs(width - 640) <= 4:
                    return "640x360"
                elif abs(width - 480) <= 4:
                    return "480x360"
            # 240P 变体 → 426x240
            elif abs(height - 240) <= 4:
                if abs(width - 426) <= 4:
                    return "426x240"
            else:
                return resolution
        except (ValueError, IndexError):
            return resolution

    def on_parse_finished(
        self,
        info: Dict
    ) -> None:
        """处理解析完成的数据"""
        video_title = info.get("title", "未知标题")
        video_id = info.get("id", "unknown")
        audio_format = None
        audio_filesize = 0
        video_formats: Dict[str, Dict] = {}

        # 处理视频标题格式 - 去掉自动编号
        match = re.search(r"p\d+\s*(.+?)(?:_\w+)?$", video_title)
        if match:
            # 提取标题内容，去掉p01、p02等编号
            part_title = match.group(1).strip()
            formatted_title = part_title
        else:
            formatted_title = video_title
            if f"_{video_id}" in formatted_title:
                formatted_title = formatted_title.replace(f"_{video_id}", "")
            formatted_title = f"[{formatted_title}]"

        # 不再创建视频根节点，直接使用分辨率分组
        video_root = None

        formats = info.get("formats", [])
        logger.info(f"解析条目 '{video_title}'，共有 {len(formats)} 个格式")

        # 过滤格式，只保留标准分辨率
        filtered_formats = filter_formats(formats)
        logger.info(f"过滤后剩余 {len(filtered_formats)} 个标准格式")

        # 处理格式信息
        for f in filtered_formats:
            format_id = f.get("format_id")
            resolution = self.get_resolution(f)
            ext = f.get("ext", "")
            acodec = f.get("acodec", "none")
            filesize = f.get("filesize") or f.get("filesize_approx")
            vbr = f.get("vbr", 0)
            
            # 调试信息：记录每个格式的详细信息
            logger.info(f"格式 {format_id}: resolution={resolution}, ext={ext}, acodec={acodec}, vbr={vbr}, filesize={filesize}, width={f.get('width')}, height={f.get('height')}, format_note={f.get('format_note')}")

            # 计算文件大小
            if not filesize:
                duration = info.get("duration", 0)
                abr = f.get("abr", 0)
                total_br = (abr or 0) + (vbr or 0)
                if duration and total_br:
                    filesize = (total_br * duration * 1000) / 8

            # 查找最佳音频格式
            if "audio only" in f.get("format", "") and ext in ["m4a", "mp3"] and not audio_format:
                audio_format = format_id
                audio_filesize = filesize if filesize else 0
                
            # 收集视频格式 - 放宽条件，确保所有视频格式都被收集
            elif resolution != "未知" and f.get("vcodec", "none") != "none":
                # 对于每个分辨率，只保留一个最佳格式（通常是最高比特率的）
                if resolution not in video_formats or (filesize and filesize > video_formats[resolution].get("filesize", 0)):
                    video_formats[resolution] = {
                        "format_id": format_id,
                        "ext": ext,
                        "filesize": filesize if filesize else 0
                    }
                    logger.info(f"添加视频格式: {resolution} -> {format_id}")
            else:
                logger.info(f"跳过格式 {format_id}: resolution={resolution}, vbr={vbr}, vcodec={f.get('vcodec', 'none')}")

        # 创建分辨率分组和视频项
        logger.info(f"视频 '{formatted_title}' 将被添加到以下分辨率: {list(video_formats.keys())}")
        
        # 统计每个分辨率分类下的视频数量
        resolution_counts = {}
        for i in range(self.format_tree.topLevelItemCount()):
            item = self.format_tree.topLevelItem(i)
            res_name = item.text(1)
            resolution_counts[res_name] = item.childCount()
        
        for res, v_format in sorted(video_formats.items(), key=lambda x: x[0], reverse=True):
            # 查找或创建分辨率分组（直接作为根节点）
            res_group = None
            for i in range(self.format_tree.topLevelItemCount()):
                if self.format_tree.topLevelItem(i).text(1) == res:
                    res_group = self.format_tree.topLevelItem(i)
                    break
            if not res_group:
                res_group = QTreeWidgetItem(self.format_tree)
                res_group.setText(1, res)
                res_group.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)  # 分辨率节点可选择
                res_group.setCheckState(0, Qt.Unchecked)  # 初始未选中
                res_group.setIcon(1, self.style().standardIcon(self.style().SP_DirIcon))  # 添加文件夹图标
                res_group.setExpanded(True)

            # 创建视频项（自动包含音频）
            filename = sanitize_filename(formatted_title, self.save_path)
            video_item = QTreeWidgetItem(res_group)
            
            # 计算总大小（视频+音频）
            total_size = v_format["filesize"]
            if audio_format:
                total_size += audio_filesize
                
            # 添加视频项到树形控件
            self._add_tree_item(video_item, filename, "mp4", res, total_size)
            
            # 添加到格式列表
            format_id = v_format["format_id"]
            if audio_format:
                format_id = f"{format_id}+{audio_format}"
                
            self.formats.append({
                "video_id": video_id,
                "format_id": format_id,
                "description": f"{filename}.mp4",
                "type": "video_audio",
                "ext": "mp4",
                "filesize": total_size,
                "url": info.get("webpage_url", ""),
                "item": video_item
            })
        
        # 记录当前分辨率分类的统计信息
        current_counts = {}
        for i in range(self.format_tree.topLevelItemCount()):
            item = self.format_tree.topLevelItem(i)
            res_name = item.text(1)
            current_counts[res_name] = item.childCount()
        
        logger.info(f"当前分辨率分类统计: {current_counts}")
        
        # 实时更新UI - 每个视频解析完成后立即启用选择按钮
        if self.formats:
            self.smart_select_button.setEnabled(True)
            self.update_selection_count()

    def _add_tree_item(
        self,
        item: QTreeWidgetItem,
        filename: str,
        file_type: str,
        resolution: str,
        filesize: Optional[int]
    ) -> None:
        """添加树形控件项"""
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        item.setCheckState(1, Qt.Unchecked)  # 复选框在第1列
        item.setText(1, filename)
        item.setText(2, file_type)
        item.setText(3, str(resolution))
        item.setText(4, format_size(filesize))
        
        # 检查文件是否已下载，设置状态列
        file_path = os.path.join(self.save_path, f"{filename}.{file_type}")
        if os.path.exists(file_path):
            # 文件已下载，显示绿色对勾
            item.setText(5, "已下载✓")
            item.setForeground(5, Qt.green)
        else:
            # 文件未下载，显示"未下载"
            item.setText(5, "未下载")
            item.setForeground(5, Qt.black)

    def on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """处理树形控件项状态变化"""
        # 处理分辨率节点的复选框变化（第0列）
        if column == 0 and item.parent() is None:
            def set_check_state_recursive(tree_item: QTreeWidgetItem, state: Qt.CheckState) -> None:
                for i in range(tree_item.childCount()):
                    child = tree_item.child(i)
                    child.setCheckState(1, state)  # 子节点复选框在第1列
                    set_check_state_recursive(child, state)
            
            checked = item.checkState(0) == Qt.Checked
            set_check_state_recursive(item, Qt.Checked if checked else Qt.Unchecked)
        
        # 处理视频文件节点的复选框变化（第1列）
        elif column == 1 and item.parent() is not None:
            parent = item.parent()
            if parent:
                all_checked = all(parent.child(i).checkState(1) == Qt.Checked for i in range(parent.childCount()))
                parent.setCheckState(0, Qt.Checked if all_checked else Qt.Unchecked)
        
        # 更新选择计数
        self.update_selection_count()

    def on_parse_error(self, error_msg: str) -> None:
        """处理解析错误"""
        QMessageBox.critical(self, "错误", error_msg)
        logger.error(error_msg)
        self.update_status_bar(f"解析错误: {error_msg}", "", "")
        self.parse_button.setEnabled(True)

    def download_progress_hook(self, d: Dict) -> None:
        """下载进度回调"""
        if d["status"] == "downloading":
            filename = d.get("filename", "")
            percent_str = d.get("_percent_str", "0%").strip("%")
            speed = d.get("_speed_str", "未知速率")
            try:
                percent = float(percent_str)
            except ValueError:
                percent = 0
            self.download_progress[filename] = (percent, speed)
        elif d["status"] == "finished":
            filename = d.get("filename", "")
            # 标记为已完成，但不立即删除，让 on_download_finished 处理
            self.download_progress[filename] = (100, "已完成")
            logger.info(f"文件下载完成: {filename}")

    def update_download_progress(self) -> None:
        """更新下载进度"""
        # 检查是否所有下载都已完成
        if not self.is_downloading or (not self.download_progress and not self.download_workers):
            self.smart_download_button.setText("下载选中项")
            self.smart_download_button.setStyleSheet(self.default_style)
            self.setWindowTitle(f"椰果视频下载器-v{Config.APP_VERSION}")
            self.update_status_bar("就绪", "", "")
            return

        # 检查是否所有下载都已完成（没有活动下载且没有队列）
        if self.active_downloads <= 0 and not self.download_queue:
            # 所有下载完成，显示100%进度
            self.setWindowTitle(f"椰果视频下载器-v{Config.APP_VERSION} - 下载中 (100.0%)")
            self.update_status_bar("下载中 (100.0%)", "已完成", "")
            return

        # 计算总体进度：已完成文件 + 当前下载进度
        total_files = len(self.download_progress) + len([w for w in self.download_workers if not w.isRunning()])
        if total_files == 0:
            return
            
        # 当前下载进度总和
        current_percent = sum(percent for percent, _ in self.download_progress.values())
        # 已完成文件数（每个算100%）
        completed_files = len([w for w in self.download_workers if not w.isRunning()])
        completed_percent = completed_files * 100
        
        # 总进度 = (已完成进度 + 当前进度) / 总文件数
        total_percent = completed_percent + current_percent
        avg_percent = total_percent / total_files
        
        # 确保进度不超过100%
        avg_percent = min(avg_percent, 100.0)
        
        total_speed = [speed for _, speed in self.download_progress.values()]
        speed_text = ", ".join(total_speed) if total_speed else "已完成"
        active_count = len([w for w in self.download_workers if w.isRunning()])
        
        # 更新窗口标题
        self.setWindowTitle(f"椰果视频下载器-v{Config.APP_VERSION} - 下载中 ({avg_percent:.1f}%)")
        
        # 更新状态栏
        self.update_status_bar(
            f"下载中 ({avg_percent:.1f}%)", 
            f"{speed_text} | 活动: {active_count}/{Config.MAX_CONCURRENT_DOWNLOADS}",
            f"文件: {total_files}"
        )

        while self.active_downloads < Config.MAX_CONCURRENT_DOWNLOADS and self.download_queue:
            url, fmt = self.download_queue.popleft()
            self.start_download(url, fmt)

    def download_selected(self, item: Optional[QTreeWidgetItem] = None, column: Optional[int] = None) -> None:
        """下载选中的格式"""
        selected_formats = []

        try:
            def collect_checked_items(tree_item: QTreeWidgetItem) -> List[Dict]:
                checked_items = []
                for i in range(tree_item.childCount()):
                    child = tree_item.child(i)
                    if child.checkState(1) == Qt.Checked and child.childCount() == 0:  # 复选框在第1列
                        for fmt in self.formats:
                            if fmt["item"] == child:
                                checked_items.append(fmt)
                                break
                    elif child.childCount() > 0:
                        checked_items.extend(collect_checked_items(child))
                return checked_items

            for i in range(self.format_tree.topLevelItemCount()):
                top_item = self.format_tree.topLevelItem(i)
                selected_formats.extend(collect_checked_items(top_item))

            if not selected_formats:
                QMessageBox.warning(self, "提示", "请先勾选至少一个格式或分类！")
                return

            if not check_ffmpeg(self.ffmpeg_path, self):
                self.update_status_bar("错误: 请安装 FFmpeg 并放入保存路径", "", "")
                self.reset_download_state()
                return

            self.is_downloading = True
            self.download_progress.clear()
            self.smart_download_button.setEnabled(False)
            self.parse_button.setEnabled(False)
            self.smart_pause_button.setEnabled(True)
            # 隐藏进度条和状态标签，只在状态栏显示
            self.progress_bar.setVisible(False)
            self.status_label.setVisible(False)
            self.smart_download_button.setText("取消下载")
            logger.info("开始下载...")
            self.update_status_bar("开始下载...", "准备中", f"选中: {len(selected_formats)} 个文件")

            for fmt in selected_formats:
                if self.active_downloads < Config.MAX_CONCURRENT_DOWNLOADS:
                    self.start_download(fmt["url"], fmt)
                else:
                    self.download_queue.append((fmt["url"], fmt))

        except Exception as e:
            logger.error(f"下载选中项失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "错误", f"下载过程中发生错误: {str(e)}")
            self.update_status_bar(f"下载失败: {str(e)}", "", "")
            self.reset_download_state()

    def start_download(self, url: str, selected_format: Dict) -> None:
        """启动下载任务"""
        try:
            output_file = os.path.join(self.save_path, selected_format["description"])
            self.download_progress[output_file] = (0, "未知速率")
            logger.info(f"开始下载: {output_file}")

            ydl_opts = {
                "outtmpl": os.path.join(self.save_path, "%(title)s_%(id)s.%(ext)s"),
                "quiet": False,
                "ffmpeg_location": self.ffmpeg_path,
            }

            speed_limit = self.speed_limit_input.text().strip()
            if speed_limit.isdigit():
                ydl_opts["ratelimit"] = int(speed_limit) * 1024

            # 所有格式都是视频格式，自动包含音频
            ydl_opts.update({
                "format": selected_format["format_id"],
                "merge_output_format": "mp4",
            })

            worker = DownloadWorker(url, ydl_opts)
            worker.progress_signal.connect(self.download_progress_hook)
            worker.finished.connect(lambda filename: self.on_download_finished(filename, url, selected_format))
            worker.error.connect(self.on_download_error)
            worker.start()
            self.download_workers.append(worker)
            self.active_downloads += 1
        except Exception as e:
            logger.error(f"启动下载失败: {str(e)}", exc_info=True)
            self.update_status_bar(f"下载失败: {selected_format['description']} - {str(e)}", "", "")
            self.reset_download_state()

    def on_download_finished(self, filename: str, url: str, selected_format: Optional[Dict] = None) -> None:
        """处理下载完成"""
        self.active_downloads -= 1
        
        # 从下载进度中移除已完成的文件
        if filename and filename in self.download_progress:
            del self.download_progress[filename]
        
        logger.info(f"下载完成: {filename}")
        
        # 更新下载状态显示
        self.update_download_status(filename)
        
        # 清理已完成的下载工作线程
        self.download_workers = [w for w in self.download_workers if w.isRunning()]
        
        # 检查是否所有下载都完成了
        if self.active_downloads <= 0 and not self.download_queue:
            # 所有下载完成，显示100%进度
            self.setWindowTitle(f"椰果视频下载器-v{Config.APP_VERSION} - 下载中 (100.0%)")
            self.update_status_bar("下载中 (100.0%)", "已完成", "")
            # 强制更新状态栏显示
            self.status_label_main.setText("下载中 (100.0%)")
            self.status_label_progress.setText("已完成")
            logger.info("所有下载已完成，显示完成对话框")
            self.show_completion_dialog()
        else:
            # 还有文件在下载，更新状态
            self.update_status_bar(f"下载完成: {os.path.basename(filename) if filename else '未知文件'}", "", "")

    def show_completion_dialog(self) -> None:
        """显示下载完成对话框"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("下载完成")
            dialog.setFixedSize(400, 150)
            dialog.setModal(True)
            
            layout = QVBoxLayout()
            
            # 成功图标和标题
            title_label = QLabel("✓ 下载完成")
            title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #28a745; margin: 10px;")
            title_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(title_label)
            
            # 路径信息
            path_label = QLabel(f"所有文件已下载到:\n{self.save_path}")
            path_label.setAlignment(Qt.AlignCenter)
            path_label.setStyleSheet("margin: 10px;")
            layout.addWidget(path_label)
            
            # 按钮布局
            button_layout = QHBoxLayout()
            button_layout.addStretch(1)
            
            # 确定按钮
            ok_button = QPushButton("确定", dialog)
            ok_button.setFixedSize(80, 30)
            ok_button.clicked.connect(dialog.accept)
            button_layout.addWidget(ok_button)
            
            # 打开文件夹按钮
            open_button = QPushButton("打开文件夹", dialog)
            open_button.setFixedSize(80, 30)
            open_button.clicked.connect(lambda: self.open_save_path_and_close(dialog))
            button_layout.addWidget(open_button)
            
            button_layout.addStretch(1)
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            
            # 显示对话框
            logger.info("显示下载完成对话框")
            dialog.exec_()
            
            # 重置下载状态
            self.reset_download_state()
            
            # 刷新下载状态显示
            self.refresh_download_status()
            
        except Exception as e:
            logger.error(f"显示完成对话框失败: {str(e)}")
            # 如果对话框显示失败，至少重置状态
            self.reset_download_state()

    def open_save_path_and_close(self, dialog: QDialog) -> None:
        """打开保存路径并关闭对话框"""
        self.open_save_path()
        dialog.accept()

    def open_save_path(self) -> None:
        """打开保存路径"""
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.save_path))
        except Exception as e:
            logger.error(f"打开文件夹失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"无法打开文件夹: {str(e)}")

    def on_download_error(self, error_msg: str) -> None:
        """处理下载错误"""
        self.active_downloads -= 1
        QMessageBox.critical(self, "错误", f"下载失败: {error_msg}")
        logger.error(f"下载错误: {error_msg}")
        self.update_status_bar(f"下载错误: {error_msg}", "", "")
        self.reset_download_state()

    def pause_downloads(self) -> None:
        """暂停下载"""
        for worker in self.download_workers:
            if worker.isRunning():
                worker.pause()
        self.smart_pause_button.setText("恢复下载")
        self.update_status_bar("下载已暂停", "", "")
        logger.info("下载已暂停")

    def cancel_downloads(self) -> None:
        """取消所有下载"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("确认")
        msg_box.setText("确定要取消所有下载吗？")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        # 设置按钮中文文本
        msg_box.button(QMessageBox.Yes).setText("是")
        msg_box.button(QMessageBox.No).setText("否")
        reply = msg_box.exec_()
        if reply == QMessageBox.Yes:
            for worker in self.download_workers:
                if worker.isRunning():
                    worker.cancel()
            self.download_queue.clear()
            self.reset_download_state()
            logger.info("下载已取消")
            self.update_status_bar("下载已取消", "", "")

    def reset_download_state(self) -> None:
        """重置下载状态"""
        self.download_progress.clear()
        self.is_downloading = False
        self.active_downloads = 0
        self.download_workers.clear()
        self.smart_download_button.setEnabled(True)
        self.parse_button.setEnabled(True)
        self.smart_pause_button.setEnabled(False)
        # 确保进度条和状态标签保持隐藏
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        self.smart_download_button.setText("下载选中项")
        self.smart_download_button.setStyleSheet(self.default_style)
        self.smart_pause_button.setText("暂停下载")

    def show_context_menu(self, pos: "QPoint") -> None:
        """显示右键菜单"""
        from PyQt5.QtWidgets import QApplication
        menu = QMenu(self)
        copy_action = menu.addAction("复制文件名")
        action = menu.exec_(self.format_tree.mapToGlobal(pos))
        if action == copy_action:
            item = self.format_tree.currentItem()
            if item and item.childCount() == 0:
                filename = item.text(1)
                QApplication.clipboard().setText(filename)

    def smart_select_action(self) -> None:
        """智能选择按钮动作"""
        if not self.formats:
            return
            
        # 统计当前选择状态
        selected_count = 0
        total_count = 0
        
        for i in range(self.format_tree.topLevelItemCount()):
            root_item = self.format_tree.topLevelItem(i)
            for j in range(root_item.childCount()):
                total_count += 1
                if root_item.child(j).checkState(1) == Qt.Checked:
                    selected_count += 1
        
        # 根据当前状态决定动作
        if selected_count == 0:
            # 没有选中任何项，执行全选
            self.select_all_formats()
            self.smart_select_button.setText("取消全选")
        elif selected_count == total_count:
            # 全部选中，执行取消全选
            self.deselect_all_formats()
            self.smart_select_button.setText("全选")
        else:
            # 部分选中，执行反选
            self.invert_selection()
            # 反选后重新判断状态
            self.update_smart_select_button_text()
    
    def update_smart_select_button_text(self) -> None:
        """更新智能选择按钮文本"""
        if not self.formats:
            return
            
        selected_count = 0
        total_count = 0
        
        for i in range(self.format_tree.topLevelItemCount()):
            root_item = self.format_tree.topLevelItem(i)
            for j in range(root_item.childCount()):
                total_count += 1
                if root_item.child(j).checkState(1) == Qt.Checked:
                    selected_count += 1
        
        if selected_count == 0:
            self.smart_select_button.setText("全选")
        elif selected_count == total_count:
            self.smart_select_button.setText("取消全选")
        else:
            self.smart_select_button.setText("反选")
    
    def update_download_status(self, filename: str) -> None:
        """更新下载状态显示"""
        try:
            # 遍历所有树形项目，找到对应的文件并更新状态
            for i in range(self.format_tree.topLevelItemCount()):
                root_item = self.format_tree.topLevelItem(i)
                for j in range(root_item.childCount()):
                    child_item = root_item.child(j)
                    item_filename = child_item.text(1)  # 文件名在第1列
                    item_type = child_item.text(2)      # 文件类型在第2列
                    
                    # 构建完整的文件路径
                    file_path = os.path.join(self.save_path, f"{item_filename}.{item_type}")
                    
                    # 检查文件是否存在
                    if os.path.exists(file_path):
                        # 文件已下载，显示绿色对勾
                        child_item.setText(5, "已下载✓")
                        child_item.setForeground(5, Qt.green)
                    else:
                        # 文件未下载，显示"未下载"
                        child_item.setText(5, "未下载")
                        child_item.setForeground(5, Qt.black)
                        
        except Exception as e:
            logger.error(f"更新下载状态失败: {str(e)}")
    
    def refresh_download_status(self) -> None:
        """刷新所有文件的下载状态"""
        """刷新所有文件的下载状态"""
        try:
            # 遍历所有树形项目，更新状态
            for i in range(self.format_tree.topLevelItemCount()):
                root_item = self.format_tree.topLevelItem(i)
                for j in range(root_item.childCount()):
                    child_item = root_item.child(j)
                    item_filename = child_item.text(1)  # 文件名在第1列
                    item_type = child_item.text(2)      # 文件类型在第2列
                    
                    # 构建完整的文件路径
                    file_path = os.path.join(self.save_path, f"{item_filename}.{item_type}")
                    
                    # 检查文件是否存在
                    if os.path.exists(file_path):
                        # 文件已下载，显示绿色对勾
                        child_item.setText(5, "已下载✓")
                        child_item.setForeground(5, Qt.green)
                    else:
                        # 文件未下载，显示"未下载"
                        child_item.setText(5, "未下载")
                        child_item.setForeground(5, Qt.black)
                        
        except Exception as e:
            logger.error(f"刷新下载状态失败: {str(e)}")
    
    def smart_download_action(self) -> None:
        """智能下载按钮动作"""
        if self.is_downloading:
            # 如果正在下载，执行取消操作
            self.cancel_downloads()
        else:
            # 如果未下载，执行下载操作
            self.download_selected()
    
    def smart_pause_action(self) -> None:
        """智能暂停按钮动作"""
        if self.smart_pause_button.text() == "暂停下载":
            # 当前是暂停状态，执行暂停操作
            self.pause_downloads()
        else:
            # 当前是恢复状态，执行恢复操作
            self.resume_downloads()
    
    def resume_downloads(self) -> None:
        """恢复下载"""
        for worker in self.download_workers:
            if worker.isRunning():
                worker.resume()
        self.smart_pause_button.setText("暂停下载")
        self.update_status_bar("下载已恢复", "", "")
        logger.info("下载已恢复")
    
    def clear_input(self) -> None:
        """清空输入框"""
        self.url_input.clear()
        
    def new_session(self) -> None:
        """新建会话"""
        self.url_input.clear()
        self.format_tree.clear()
        self.formats = []
        self.smart_download_button.setEnabled(False)
        self.smart_select_button.setEnabled(False)
        self.selection_count_label.setText("已选择: 0 项")
        self.update_status_bar("就绪", "", "")
        self.status_scroll_label.setText("")
        
    
        
    def show_settings_dialog(self) -> None:
        """显示设置对话框"""
        from .settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # 应用设置到主窗口
            self.apply_settings_from_dialog(dialog.get_settings_dict())
            
    def apply_settings_from_dialog(self, settings_dict: Dict[str, Any]) -> None:
        """从设置对话框应用设置到主窗口"""
        try:
            # 应用基本设置
            if settings_dict.get("save_path"):
                self.save_path = settings_dict["save_path"]
                self.path_label.setText(f"保存路径: {self.save_path}")
                
            # 应用下载设置
            if "max_concurrent" in settings_dict:
                Config.MAX_CONCURRENT_DOWNLOADS = settings_dict["max_concurrent"]
                
            if "speed_limit" in settings_dict:
                speed_limit = settings_dict["speed_limit"]
                if speed_limit > 0:
                    self.speed_limit_input.setText(str(speed_limit))
                else:
                    self.speed_limit_input.clear()
                    
            # 应用界面设置
            if "font_size" in settings_dict:
                font_size = settings_dict["font_size"]
                # 更新全局字体大小
                self.update_font_size(font_size)
                
            # 应用高级设置
            if settings_dict.get("ffmpeg_path"):
                self.ffmpeg_path = settings_dict["ffmpeg_path"]
                
            logger.info("设置已应用到主窗口")
            
        except Exception as e:
            logger.error(f"应用设置失败: {str(e)}")
            
    def update_font_size(self, font_size: int) -> None:
        """更新全局字体大小"""
        try:
            # 更新样式表中的字体大小
            current_style = self.styleSheet()
            # 这里可以添加动态更新字体大小的逻辑
            logger.info(f"字体大小已更新为: {font_size}px")
        except Exception as e:
            logger.error(f"更新字体大小失败: {str(e)}")
        
    
        
    def show_log_dialog(self) -> None:
        """显示日志查看对话框"""
        from PyQt5.QtWidgets import QTextEdit, QVBoxLayout, QHBoxLayout, QPushButton, QDialog, QLabel
        from PyQt5.QtCore import Qt
        import os
        
        # 创建日志对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("日志查看器")
        dialog.setGeometry(200, 200, 800, 600)
        dialog.setModal(True)
        
        # 创建布局
        layout = QVBoxLayout()
        
        # 添加标题标签
        title_label = QLabel("应用程序日志")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; margin: 5px;")
        layout.addWidget(title_label)
        
        # 创建日志显示区域
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-family: "Consolas", "Monaco", "Courier New", monospace;
                font-size: 12px;
                padding: 8px;
            }
        """)
        layout.addWidget(log_text)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        # 刷新按钮
        refresh_button = QPushButton("刷新(&R)")
        refresh_button.clicked.connect(lambda: self.load_log_content(log_text))
        button_layout.addWidget(refresh_button)
        
        # 导出按钮
        export_button = QPushButton("导出(&E)")
        export_button.clicked.connect(lambda: self.export_log())
        button_layout.addWidget(export_button)
        
        button_layout.addStretch()
        
        # 关闭按钮
        close_button = QPushButton("关闭(&C)")
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # 加载日志内容
        self.load_log_content(log_text)
        
        # 显示对话框
        dialog.exec_()
        
    def load_log_content(self, log_text) -> None:
        """加载日志内容到文本控件"""
        try:
            # 获取日志文件路径
            log_file = os.path.join(os.getcwd(), "app.log")
            
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                log_text.setText(content)
                # 滚动到底部
                cursor = log_text.textCursor()
                cursor.movePosition(cursor.End)
                log_text.setTextCursor(cursor)
            else:
                log_text.setText("日志文件不存在或为空")
        except Exception as e:
            log_text.setText(f"读取日志文件失败: {str(e)}")
            
    def export_log(self) -> None:
        """导出日志文件"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            # 获取日志文件路径
            log_file = os.path.join(os.getcwd(), "app.log")
            
            if not os.path.exists(log_file):
                QMessageBox.warning(self, "警告", "日志文件不存在")
                return
                
            # 选择保存路径
            save_path, _ = QFileDialog.getSaveFileName(
                self, 
                "导出日志", 
                os.path.join(self.save_path, "椰果视频下载器日志.txt"),
                "文本文件 (*.txt);;所有文件 (*)"
            )
            
            if save_path:
                import shutil
                shutil.copy2(log_file, save_path)
                QMessageBox.information(self, "成功", f"日志已导出到:\n{save_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出日志失败: {str(e)}")
            
    def clear_log(self) -> None:
        """清空日志"""
        try:
            msg_box = QMessageBox()
            msg_box.setWindowTitle("确认清空")
            msg_box.setText("确定要清空所有日志吗？此操作不可恢复！")
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.No)
            # 设置按钮中文文本
            msg_box.button(QMessageBox.Yes).setText("是")
            msg_box.button(QMessageBox.No).setText("否")
            reply = msg_box.exec_()
            
            if reply == QMessageBox.Yes:
                log_file = os.path.join(os.getcwd(), "app.log")
                
                if os.path.exists(log_file):
                    # 清空日志文件
                    with open(log_file, 'w', encoding='utf-8') as f:
                        f.write("")
                    
                    # 重新初始化日志记录器
                    from utils.logger import setup_logger
                    setup_logger()
                    
                    QMessageBox.information(self, "成功", "日志已清空")
                    logger.info("日志已清空")
                else:
                    QMessageBox.information(self, "提示", "日志文件不存在")
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"清空日志失败: {str(e)}")
            logger.error(f"清空日志失败: {str(e)}")
        
    def show_help_dialog(self) -> None:
        """显示使用说明对话框"""
        help_text = """
        <h3>椰果视频下载器使用说明</h3>
        <p><b>基本操作流程：</b></p>
        <ol>
            <li>在输入框中粘贴视频链接（支持YouTube和B站）</li>
            <li>点击"解析"按钮获取可用格式</li>
            <li>在格式列表中选择需要的分辨率</li>
            <li>点击"下载选中项"开始下载</li>
        </ol>
        <p><b>支持功能：</b></p>
        <ul>
            <li>批量下载多个视频</li>
            <li>多种分辨率选择</li>
            <li>下载速度限制</li>
            <li>暂停/恢复/取消下载</li>
        </ul>
        """
        QMessageBox.information(self, "使用说明", help_text)
        
    def show_shortcuts_dialog(self) -> None:
        """显示快捷键帮助对话框"""
        shortcuts_text = """
        <h3>快捷键说明</h3>
        <table>
            <tr><td><b>Ctrl+N</b></td><td>新建会话</td></tr>
            <tr><td><b>Ctrl+O</b></td><td>选择保存路径</td></tr>
            <tr><td><b>Ctrl+Shift+O</b></td><td>打开保存文件夹</td></tr>
            <tr><td><b>Ctrl+A</b></td><td>全选</td></tr>
            <tr><td><b>Ctrl+D</b></td><td>取消全选</td></tr>
            <tr><td><b>Ctrl+I</b></td><td>反选</td></tr>
            <tr><td><b>Ctrl+L</b></td><td>清空输入</td></tr>
            <tr><td><b>F5</b></td><td>解析视频</td></tr>
            <tr><td><b>F6</b></td><td>开始下载</td></tr>
            <tr><td><b>F7</b></td><td>暂停下载</td></tr>
            <tr><td><b>F8</b></td><td>取消下载</td></tr>
            <tr><td><b>Ctrl+,</b></td><td>设置</td></tr>
            <tr><td><b>Ctrl+Shift+L</b></td><td>查看日志</td></tr>
            <tr><td><b>F1</b></td><td>使用说明</td></tr>
            <tr><td><b>Ctrl+F1</b></td><td>快捷键帮助</td></tr>
            <tr><td><b>Ctrl+Shift+F</b></td><td>问题反馈</td></tr>
            <tr><td><b>Ctrl+Q</b></td><td>退出程序</td></tr>
        </table>
        """
        QMessageBox.information(self, "快捷键帮助", shortcuts_text)
        
    def show_feedback_dialog(self) -> None:
        """显示问题反馈对话框"""
        try:
            from .feedback_dialog import FeedbackDialog
            dialog = FeedbackDialog(self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开反馈对话框失败: {str(e)}")
            logger.error(f"打开反馈对话框失败: {str(e)}")
        
    def show_about_dialog(self) -> None:
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于椰果视频下载器",
            f"""<h3>椰果视频下载器 v{Config.APP_VERSION}</h3>
            <p>一个简单、免费、无套路的视频下载工具</p>
            <p>支持从 YouTube 和 Bilibili（B站）下载视频</p>
            <br>
            <p><b>作者：</b>mrchzh</p>
            <p><b>邮箱：</b>gmrchzh@gmail.com</p>
            <p><b>创建日期：</b>2025年8月25日</p>
            <br>
            <p>本项目采用 MIT 许可证</p>"""
        )
        
    

    def closeEvent(self, event: "QCloseEvent") -> None:
        """处理窗口关闭事件"""
        self.timer.stop()
        for worker in self.download_workers:
            if worker.isRunning():
                worker.cancel()
        for worker in self.parse_workers:
            if worker.isRunning():
                worker.quit()
                worker.wait()
        self.settings.setValue("save_path", self.save_path)
        event.accept()
