"""
ED2K链接管理器模块

该模块负责ED2K链接的解析、验证和管理，包括：
- ED2K链接格式验证
- 文件信息解析
- ED2K链接缓存管理
- 文件健康度检查

主要类：
- ED2KManager: ED2K链接管理器
- ED2KInfo: ED2K链接信息类

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import re
import hashlib
import urllib.parse
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ED2KInfo:
    """ED2K链接信息类"""
    ed2k_url: str
    file_hash: str
    file_name: str
    file_size: int
    is_valid: bool = False
    
    def __post_init__(self):
        """后初始化处理"""
        if self.file_size < 0:
            self.file_size = 0


class ED2KManager:
    """ED2K链接管理器"""
    
    def __init__(self):
        """初始化ED2K链接管理器"""
        self.ed2k_cache: Dict[str, ED2KInfo] = {}
        self.max_cache_size = 100
        
    def is_ed2k_link(self, url: str) -> bool:
        """
        判断是否为ED2K链接
        
        Args:
            url: 待检查的URL
            
        Returns:
            bool: 是否为ED2K链接
        """
        if not url:
            return False
        
        # 检查是否以ed2k://开头
        if url.startswith('ed2k://'):
            return True
            
        # 检查是否包含ED2K链接特征
        ed2k_patterns = [
            r'ed2k://\|file\|[^|]+\|\d+\|[a-fA-F0-9]{32}\|/',
            r'ed2k://\|file\|[^|]+\|\d+\|[a-fA-F0-9]{32}\|',
        ]
        
        for pattern in ed2k_patterns:
            if re.search(pattern, url):
                return True
                
        return False
    
    def parse_ed2k_url(self, ed2k_url: str) -> Optional[ED2KInfo]:
        """
        解析ED2K链接URL
        
        Args:
            ed2k_url: ED2K链接URL
            
        Returns:
            ED2KInfo: 解析后的ED2K链接信息，解析失败返回None
        """
        try:
            if not self.is_ed2k_link(ed2k_url):
                logger.warning(f"无效的ED2K链接格式: {ed2k_url}")
                return None
            
            # 解析ED2K链接格式: ed2k://|file|filename.ext|filesize|hash|/
            # 移除末尾的斜杠
            clean_url = ed2k_url.rstrip('/')
            
            # 分割链接部分
            parts = clean_url.split('|')
            if len(parts) < 5:
                logger.error(f"ED2K链接格式错误，部分数量不足: {ed2k_url}")
                return None
            
            # 验证协议 - 处理ed2k://格式
            protocol_part = parts[0]
            if not protocol_part.startswith('ed2k:'):
                logger.error(f"无效的ED2K协议: {protocol_part}")
                return None
            
            # 验证文件标识
            if parts[1] != 'file':
                logger.error(f"无效的文件标识: {parts[1]}")
                return None
            
            # 提取文件名
            file_name = parts[2]
            if not file_name:
                logger.error("文件名为空")
                return None
            
            # 提取文件大小
            try:
                file_size = int(parts[3])
                if file_size < 0:
                    logger.warning(f"文件大小无效: {file_size}")
                    file_size = 0
            except ValueError:
                logger.error(f"无法解析文件大小: {parts[3]}")
                return None
            
            # 提取文件哈希
            file_hash = parts[4]
            if not self._is_valid_ed2k_hash(file_hash):
                logger.error(f"无效的ED2K哈希: {file_hash}")
                return None
            
            # 创建ED2K链接信息
            ed2k_info = ED2KInfo(
                ed2k_url=ed2k_url,
                file_hash=file_hash.lower(),
                file_name=file_name,
                file_size=file_size
            )
            
            # 验证ED2K链接
            ed2k_info.is_valid = self._validate_ed2k_info(ed2k_info)
            
            # 缓存结果
            self._cache_ed2k_info(ed2k_info)
            
            logger.info(f"成功解析ED2K链接: {file_name} ({file_size} bytes)")
            return ed2k_info
            
        except Exception as e:
            logger.error(f"解析ED2K链接失败: {e}")
            return None
    
    def _is_valid_ed2k_hash(self, hash_str: str) -> bool:
        """
        验证ED2K哈希的有效性
        
        Args:
            hash_str: 哈希字符串
            
        Returns:
            bool: 是否有效
        """
        try:
            # ED2K哈希应该是32位的十六进制字符串
            if len(hash_str) != 32:
                return False
            
            # 检查是否只包含十六进制字符
            if not re.match(r'^[a-fA-F0-9]{32}$', hash_str):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _validate_ed2k_info(self, ed2k_info: ED2KInfo) -> bool:
        """
        验证ED2K链接信息的有效性
        
        Args:
            ed2k_info: ED2K链接信息
            
        Returns:
            bool: 是否有效
        """
        try:
            # 验证文件名
            if not ed2k_info.file_name or len(ed2k_info.file_name.strip()) == 0:
                return False
            
            # 验证文件大小
            if ed2k_info.file_size < 0:
                return False
            
            # 验证哈希
            if not self._is_valid_ed2k_hash(ed2k_info.file_hash):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证ED2K链接信息失败: {e}")
            return False
    
    def _cache_ed2k_info(self, ed2k_info: ED2KInfo) -> None:
        """
        缓存ED2K链接信息
        
        Args:
            ed2k_info: ED2K链接信息
        """
        try:
            # 检查缓存大小
            if len(self.ed2k_cache) >= self.max_cache_size:
                # 移除最旧的缓存项
                oldest_key = next(iter(self.ed2k_cache))
                del self.ed2k_cache[oldest_key]
            
            # 添加新缓存项
            self.ed2k_cache[ed2k_info.file_hash] = ed2k_info
            
        except Exception as e:
            logger.error(f"缓存ED2K链接信息失败: {e}")
    
    def get_cached_ed2k_info(self, file_hash: str) -> Optional[ED2KInfo]:
        """
        获取缓存的ED2K链接信息
        
        Args:
            file_hash: 文件哈希
            
        Returns:
            ED2KInfo: 缓存的ED2K链接信息，不存在返回None
        """
        return self.ed2k_cache.get(file_hash.lower())
    
    def clear_cache(self) -> None:
        """清空ED2K链接缓存"""
        self.ed2k_cache.clear()
        logger.info("ED2K链接缓存已清空")
    
    def get_ed2k_stats(self) -> Dict[str, int]:
        """
        获取ED2K链接统计信息
        
        Returns:
            Dict: 统计信息字典
        """
        return {
            'total_cached': len(self.ed2k_cache),
            'max_cache_size': self.max_cache_size,
            'valid_count': sum(1 for info in self.ed2k_cache.values() if info.is_valid),
            'invalid_count': sum(1 for info in self.ed2k_cache.values() if not info.is_valid)
        }
    
    def get_file_info_from_hash(self, file_hash: str) -> Optional[ED2KInfo]:
        """
        从哈希获取文件信息（用于搜索）
        
        Args:
            file_hash: 文件哈希
            
        Returns:
            ED2KInfo: 文件信息，不存在返回None
        """
        return self.ed2k_cache.get(file_hash.lower())
    
    def search_files_by_name(self, search_term: str) -> List[ED2KInfo]:
        """
        根据文件名搜索文件
        
        Args:
            search_term: 搜索关键词
            
        Returns:
            List[ED2KInfo]: 匹配的文件列表
        """
        try:
            results = []
            search_term_lower = search_term.lower()
            
            for ed2k_info in self.ed2k_cache.values():
                if search_term_lower in ed2k_info.file_name.lower():
                    results.append(ed2k_info)
            
            return results
            
        except Exception as e:
            logger.error(f"搜索文件失败: {e}")
            return []


# 全局ED2K链接管理器实例
ed2k_manager = ED2KManager()
