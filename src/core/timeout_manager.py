#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能超时管理器

该模块提供智能超时管理功能，包括：
- 动态超时时间调整
- 网络状况自适应
- 超时统计和分析
- 智能重试策略

主要类：
- TimeoutManager: 智能超时管理器

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import time
import statistics
from typing import Dict, List, Optional, Tuple
from collections import deque
from ..core.config import Config
from ..utils.logger import logger


class TimeoutManager:
    """智能超时管理器"""
    
    def __init__(self):
        self.timeout_history = deque(maxlen=100)  # 保存最近100次超时记录
        self.success_history = deque(maxlen=100)  # 保存最近100次成功记录
        self.network_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'timeout_requests': 0,
            'average_response_time': 0.0,
            'timeout_rate': 0.0
        }
        self.last_adaptation = time.time()
        self.adaptation_interval = 300  # 5分钟调整一次超时时间
    
    def get_optimal_timeout(self, operation_type: str = "default", 
                           base_timeout: Optional[int] = None) -> int:
        """
        获取最优超时时间
        
        Args:
            operation_type: 操作类型（parse, download, etc.）
            base_timeout: 基础超时时间
            
        Returns:
            int: 最优超时时间（秒）
        """
        try:
            # 如果没有基础超时时间，使用配置中的默认值
            if base_timeout is None:
                base_timeout = Config.NETWORK_TIMEOUTS['socket_timeout']
            
            # 如果启用了智能超时，进行动态调整
            if Config.SMART_TIMEOUT_ENABLED:
                adjusted_timeout = self._calculate_adaptive_timeout(
                    base_timeout, operation_type
                )
                return self._clamp_timeout(adjusted_timeout)
            
            return base_timeout
            
        except Exception as e:
            logger.error(f"获取最优超时时间失败: {e}")
            return base_timeout or Config.NETWORK_TIMEOUTS['socket_timeout']
    
    def _calculate_adaptive_timeout(self, base_timeout: int, 
                                  operation_type: str) -> int:
        """
        计算自适应超时时间
        
        Args:
            base_timeout: 基础超时时间
            operation_type: 操作类型
            
        Returns:
            int: 自适应超时时间
        """
        try:
            # 基于网络状况调整
            network_factor = self._get_network_factor()
            
            # 基于操作类型调整
            operation_factor = self._get_operation_factor(operation_type)
            
            # 基于历史成功率调整
            success_factor = self._get_success_factor()
            
            # 计算最终超时时间
            adjusted_timeout = int(base_timeout * network_factor * 
                                 operation_factor * success_factor)
            
            logger.debug(f"超时时间调整: 基础={base_timeout}s, "
                        f"网络因子={network_factor:.2f}, "
                        f"操作因子={operation_factor:.2f}, "
                        f"成功因子={success_factor:.2f}, "
                        f"最终={adjusted_timeout}s")
            
            return adjusted_timeout
            
        except Exception as e:
            logger.error(f"计算自适应超时时间失败: {e}")
            return base_timeout
    
    def _get_network_factor(self) -> float:
        """获取网络状况因子"""
        try:
            if len(self.timeout_history) < 5:
                return 1.0
            
            # 计算最近超时率
            recent_timeouts = len([t for t in list(self.timeout_history)[-10:] 
                                 if t['timeout']])
            recent_total = min(10, len(self.timeout_history))
            recent_timeout_rate = recent_timeouts / recent_total if recent_total > 0 else 0
            
            # 基于超时率调整
            if recent_timeout_rate > 0.5:  # 超时率超过50%
                return Config.TIMEOUT_ADAPTATION_FACTOR
            elif recent_timeout_rate > 0.2:  # 超时率超过20%
                return 1.2
            elif recent_timeout_rate < 0.05:  # 超时率低于5%
                return 0.8
            else:
                return 1.0
                
        except Exception as e:
            logger.error(f"获取网络状况因子失败: {e}")
            return 1.0
    
    def _get_operation_factor(self, operation_type: str) -> float:
        """获取操作类型因子"""
        try:
            # 不同操作类型的超时因子
            operation_factors = {
                'parse': 1.0,      # 解析操作
                'download': 1.2,   # 下载操作
                'metadata': 0.8,   # 元数据获取
                'thumbnail': 0.6,  # 缩略图下载
                'subtitle': 0.7,   # 字幕下载
                'default': 1.0     # 默认
            }
            
            return operation_factors.get(operation_type, 1.0)
            
        except Exception as e:
            logger.error(f"获取操作类型因子失败: {e}")
            return 1.0
    
    def _get_success_factor(self) -> float:
        """获取成功率因子"""
        try:
            if self.network_stats['total_requests'] == 0:
                return 1.0
            
            success_rate = (self.network_stats['successful_requests'] / 
                           self.network_stats['total_requests'])
            
            # 基于成功率调整
            if success_rate > 0.9:  # 成功率超过90%
                return 0.9
            elif success_rate > 0.7:  # 成功率超过70%
                return 1.0
            elif success_rate > 0.5:  # 成功率超过50%
                return 1.1
            else:  # 成功率低于50%
                return Config.TIMEOUT_ADAPTATION_FACTOR
                
        except Exception as e:
            logger.error(f"获取成功率因子失败: {e}")
            return 1.0
    
    def _clamp_timeout(self, timeout: int) -> int:
        """
        限制超时时间在合理范围内
        
        Args:
            timeout: 原始超时时间
            
        Returns:
            int: 限制后的超时时间
        """
        return max(Config.MIN_TIMEOUT, 
                  min(timeout, Config.MAX_TIMEOUT))
    
    def record_request(self, operation_type: str, timeout: int, 
                      response_time: float, success: bool) -> None:
        """
        记录请求信息
        
        Args:
            operation_type: 操作类型
            timeout: 使用的超时时间
            response_time: 响应时间
            success: 是否成功
        """
        try:
            current_time = time.time()
            
            # 更新网络统计
            self.network_stats['total_requests'] += 1
            if success:
                self.network_stats['successful_requests'] += 1
                self.success_history.append({
                    'time': current_time,
                    'operation_type': operation_type,
                    'response_time': response_time,
                    'timeout': timeout
                })
            else:
                self.network_stats['timeout_requests'] += 1
                self.timeout_history.append({
                    'time': current_time,
                    'operation_type': operation_type,
                    'response_time': response_time,
                    'timeout': timeout,
                    'timeout': True
                })
            
            # 更新平均响应时间
            if len(self.success_history) > 0:
                response_times = [r['response_time'] for r in self.success_history]
                self.network_stats['average_response_time'] = statistics.mean(response_times)
            
            # 更新超时率
            if self.network_stats['total_requests'] > 0:
                self.network_stats['timeout_rate'] = (
                    self.network_stats['timeout_requests'] / 
                    self.network_stats['total_requests']
                )
            
            # 定期调整超时策略
            if current_time - self.last_adaptation > self.adaptation_interval:
                self._adapt_timeout_strategy()
                self.last_adaptation = current_time
                
        except Exception as e:
            logger.error(f"记录请求信息失败: {e}")
    
    def _adapt_timeout_strategy(self) -> None:
        """调整超时策略"""
        try:
            logger.info("开始调整超时策略...")
            
            # 分析网络状况
            if self.network_stats['timeout_rate'] > 0.3:
                logger.info("网络状况较差，建议增加超时时间")
            elif self.network_stats['timeout_rate'] < 0.1:
                logger.info("网络状况良好，可以考虑减少超时时间")
            
            # 记录调整日志
            logger.info(f"超时策略调整完成 - "
                       f"总请求: {self.network_stats['total_requests']}, "
                       f"成功率: {1 - self.network_stats['timeout_rate']:.2%}, "
                       f"平均响应时间: {self.network_stats['average_response_time']:.2f}s")
            
        except Exception as e:
            logger.error(f"调整超时策略失败: {e}")
    
    def get_network_stats(self) -> Dict:
        """获取网络统计信息"""
        return self.network_stats.copy()
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        try:
            self.timeout_history.clear()
            self.success_history.clear()
            self.network_stats = {
                'total_requests': 0,
                'successful_requests': 0,
                'timeout_requests': 0,
                'average_response_time': 0.0,
                'timeout_rate': 0.0
            }
            self.last_adaptation = time.time()
            logger.info("网络统计信息已重置")
            
        except Exception as e:
            logger.error(f"重置统计信息失败: {e}")


# 全局超时管理器实例
timeout_manager = TimeoutManager()
