"""
磁力链接管理器模块

该模块负责磁力链接的解析、验证和管理，包括：
- 磁力链接格式验证
- 种子信息解析
- 磁力链接缓存管理
- 种子健康度检查

主要类：
- MagnetManager: 磁力链接管理器
- MagnetInfo: 磁力链接信息类

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import re
import hashlib
import urllib.parse
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)


@dataclass
class MagnetInfo:
    """磁力链接信息类"""
    magnet_url: str
    info_hash: str
    display_name: Optional[str] = None
    file_size: Optional[int] = None
    file_count: Optional[int] = None
    tracker_list: List[str] = None
    is_valid: bool = False
    
    def __post_init__(self):
        if self.tracker_list is None:
            self.tracker_list = []


class MagnetManager:
    """磁力链接管理器"""
    
    def __init__(self):
        """初始化磁力链接管理器"""
        self.magnet_cache: Dict[str, MagnetInfo] = {}
        self.max_cache_size = 100
        
    def is_magnet_link(self, url: str) -> bool:
        """
        判断是否为磁力链接
        
        Args:
            url: 待检查的URL
            
        Returns:
            bool: 是否为磁力链接
        """
        if not url:
            return False
        
        # 检查是否以magnet:开头
        if url.startswith('magnet:'):
            return True
            
        # 检查是否包含磁力链接特征
        magnet_patterns = [
            r'magnet:\?xt=urn:btih:[a-fA-F0-9]{40}',
            r'urn:btih:[a-fA-F0-9]{40}',
            r'btih:[a-fA-F0-9]{40}'
        ]
        
        for pattern in magnet_patterns:
            if re.search(pattern, url):
                return True
                
        return False
    
    def parse_magnet_url(self, magnet_url: str) -> Optional[MagnetInfo]:
        """
        解析磁力链接URL
        
        Args:
            magnet_url: 磁力链接URL
            
        Returns:
            MagnetInfo: 解析后的磁力链接信息，解析失败返回None
        """
        try:
            if not self.is_magnet_link(magnet_url):
                logger.warning(f"无效的磁力链接格式: {magnet_url}")
                return None
            
            # 解析URL参数
            parsed = urlparse(magnet_url)
            if parsed.scheme != 'magnet':
                logger.warning(f"无效的磁力链接协议: {magnet_url}")
                return None
            
            # 解析查询参数
            query_params = parse_qs(parsed.query)
            
            # 提取info hash
            xt_params = query_params.get('xt', [])
            info_hash = None
            
            for xt in xt_params:
                if xt.startswith('urn:btih:'):
                    info_hash = xt[9:]  # 移除'urn:btih:'前缀
                    break
            
            if not info_hash or len(info_hash) != 40:
                logger.error(f"无法提取有效的info hash: {magnet_url}")
                return None
            
            # 创建磁力链接信息
            magnet_info = MagnetInfo(
                magnet_url=magnet_url,
                info_hash=info_hash.lower(),
                display_name=query_params.get('dn', [None])[0],
                tracker_list=query_params.get('tr', [])
            )
            
            # 验证磁力链接
            magnet_info.is_valid = self._validate_magnet_info(magnet_info)
            
            # 缓存结果
            self._cache_magnet_info(magnet_info)
            
            logger.info(f"成功解析磁力链接: {info_hash}")
            return magnet_info
            
        except Exception as e:
            logger.error(f"解析磁力链接失败: {e}")
            return None
    
    def _validate_magnet_info(self, magnet_info: MagnetInfo) -> bool:
        """
        验证磁力链接信息的有效性
        
        Args:
            magnet_info: 磁力链接信息
            
        Returns:
            bool: 是否有效
        """
        try:
            # 验证info hash格式
            if not re.match(r'^[a-f0-9]{40}$', magnet_info.info_hash):
                return False
            
            # 验证tracker列表
            if magnet_info.tracker_list:
                for tracker in magnet_info.tracker_list:
                    if not self._is_valid_tracker(tracker):
                        logger.warning(f"无效的tracker: {tracker}")
            
            return True
            
        except Exception as e:
            logger.error(f"验证磁力链接信息失败: {e}")
            return False
    
    def _is_valid_tracker(self, tracker: str) -> bool:
        """
        验证tracker URL的有效性
        
        Args:
            tracker: tracker URL
            
        Returns:
            bool: 是否有效
        """
        try:
            parsed = urlparse(tracker)
            return parsed.scheme in ['http', 'https', 'udp']
        except Exception:
            return False
    
    def _cache_magnet_info(self, magnet_info: MagnetInfo) -> None:
        """
        缓存磁力链接信息
        
        Args:
            magnet_info: 磁力链接信息
        """
        try:
            # 检查缓存大小
            if len(self.magnet_cache) >= self.max_cache_size:
                # 移除最旧的缓存项
                oldest_key = next(iter(self.magnet_cache))
                del self.magnet_cache[oldest_key]
            
            # 添加新缓存项
            self.magnet_cache[magnet_info.info_hash] = magnet_info
            
        except Exception as e:
            logger.error(f"缓存磁力链接信息失败: {e}")
    
    def get_cached_magnet_info(self, info_hash: str) -> Optional[MagnetInfo]:
        """
        获取缓存的磁力链接信息
        
        Args:
            info_hash: info hash
            
        Returns:
            MagnetInfo: 缓存的磁力链接信息，不存在返回None
        """
        return self.magnet_cache.get(info_hash.lower())
    
    def clear_cache(self) -> None:
        """清空磁力链接缓存"""
        self.magnet_cache.clear()
        logger.info("磁力链接缓存已清空")
    
    def get_magnet_stats(self) -> Dict[str, int]:
        """
        获取磁力链接统计信息
        
        Returns:
            Dict: 统计信息字典
        """
        return {
            'total_cached': len(self.magnet_cache),
            'max_cache_size': self.max_cache_size,
            'valid_count': sum(1 for info in self.magnet_cache.values() if info.is_valid),
            'invalid_count': sum(1 for info in self.magnet_cache.values() if not info.is_valid)
        }


# 全局磁力链接管理器实例
magnet_manager = MagnetManager()
