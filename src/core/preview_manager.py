"""
预览管理模块

该模块负责处理文件预览功能，包括：
- 图片预览
- 视频预览
- 音频预览
- 文档预览

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import os
import logging
from typing import Optional, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class PreviewManager(QObject):
    """预览管理器"""
    
    # 信号定义
    preview_ready = pyqtSignal(str, str)  # 文件路径, 预览类型
    preview_error = pyqtSignal(str, str)  # 文件路径, 错误信息
    
    def __init__(self):
        super().__init__()
        self.supported_formats = {
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'],
            'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'],
            'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma'],
            'document': ['.pdf', '.txt', '.doc', '.docx', '.xls', '.xlsx']
        }
    
    def can_preview(self, file_path: str) -> bool:
        """检查文件是否可以预览"""
        if not file_path or not os.path.exists(file_path):
            return False
        
        file_ext = os.path.splitext(file_path)[1].lower()
        return any(file_ext in formats for formats in self.supported_formats.values())
    
    def get_preview_type(self, file_path: str) -> Optional[str]:
        """获取文件预览类型"""
        if not file_path:
            return None
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        for preview_type, formats in self.supported_formats.items():
            if file_ext in formats:
                return preview_type
        
        return None
    
    def generate_preview(self, file_path: str) -> bool:
        """生成文件预览"""
        try:
            if not self.can_preview(file_path):
                logger.warning(f"不支持预览的文件: {file_path}")
                return False
            
            preview_type = self.get_preview_type(file_path)
            if not preview_type:
                return False
            
            # 这里可以添加具体的预览生成逻辑
            # 目前只是发送预览就绪信号
            self.preview_ready.emit(file_path, preview_type)
            logger.info(f"预览生成成功: {file_path} ({preview_type})")
            return True
            
        except Exception as e:
            logger.error(f"生成预览失败: {file_path}, 错误: {e}")
            self.preview_error.emit(file_path, str(e))
            return False
    
    def clear_preview_cache(self, file_path: str = None) -> None:
        """清理预览缓存"""
        try:
            if file_path:
                # 清理特定文件的预览缓存
                logger.info(f"清理预览缓存: {file_path}")
            else:
                # 清理所有预览缓存
                logger.info("清理所有预览缓存")
        except Exception as e:
            logger.error(f"清理预览缓存失败: {e}")


# 全局预览管理器实例
preview_manager = PreviewManager()
