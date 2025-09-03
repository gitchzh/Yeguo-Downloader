#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨平台FFmpeg管理器

该模块提供跨平台的FFmpeg功能，包括：
- 自动检测系统FFmpeg
- Python原生库集成
- 多平台支持（Windows、macOS、Linux）
- 智能回退机制

主要类：
- FFmpegManager: FFmpeg管理器类

作者: 椰果IDM开发团队
版本: 1.0.0
"""

import os
import sys
import platform
import subprocess
import shutil
from typing import Optional, Dict, List, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

try:
    import ffmpeg
    FFMPEG_PYTHON_AVAILABLE = True
except ImportError:
    FFMPEG_PYTHON_AVAILABLE = False
    logger.warning("ffmpeg-python库未安装，将使用系统FFmpeg")

try:
    from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logger.warning("moviepy库未安装，将使用系统FFmpeg")


class FFmpegManager:
    """跨平台FFmpeg管理器"""
    
    def __init__(self):
        self.system_ffmpeg_path: Optional[str] = None
        self.ffmpeg_available = False
        self.ffmpeg_method = "none"  # "system", "python", "moviepy"
        self.ffmpeg_version: Optional[str] = None
        
        # 初始化FFmpeg检测
        self._detect_ffmpeg()
    
    def _detect_ffmpeg(self) -> None:
        """检测可用的FFmpeg"""
        # 优先级1: 检测系统FFmpeg
        if self._detect_system_ffmpeg():
            self.ffmpeg_method = "system"
            self.ffmpeg_available = True
            logger.info(f"使用系统FFmpeg: {self.system_ffmpeg_path}")
            return
        
        # 优先级2: 检测Python FFmpeg库
        if FFMPEG_PYTHON_AVAILABLE:
            self.ffmpeg_method = "python"
            self.ffmpeg_available = True
            logger.info("使用ffmpeg-python库")
            return
        
        # 优先级3: 检测MoviePy
        if MOVIEPY_AVAILABLE:
            self.ffmpeg_method = "moviepy"
            self.ffmpeg_available = True
            logger.info("使用MoviePy库")
            return
        
        # 无可用FFmpeg
        self.ffmpeg_available = False
        logger.warning("未找到可用的FFmpeg")
    
    def _detect_system_ffmpeg(self) -> bool:
        """检测系统FFmpeg"""
        try:
            # 检查PATH中的ffmpeg
            if shutil.which("ffmpeg"):
                self.system_ffmpeg_path = shutil.which("ffmpeg")
                return self._verify_ffmpeg(self.system_ffmpeg_path)
            
            # 检查常见安装路径
            common_paths = self._get_common_ffmpeg_paths()
            for path in common_paths:
                if os.path.exists(path) and self._verify_ffmpeg(path):
                    self.system_ffmpeg_path = path
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检测系统FFmpeg失败: {e}")
            return False
    
    def _get_common_ffmpeg_paths(self) -> List[str]:
        """获取常见FFmpeg安装路径"""
        system = platform.system().lower()
        paths = []
        
        if system == "windows":
            # Windows常见路径
            paths.extend([
                os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'ffmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'ffmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(os.environ.get('APPDATA', ''), 'ffmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(os.getcwd(), 'ffmpeg.exe'),
                os.path.join(os.getcwd(), 'resources', 'ffmpeg.exe'),
            ])
        elif system == "darwin":  # macOS
            paths.extend([
                '/usr/local/bin/ffmpeg',
                '/opt/homebrew/bin/ffmpeg',
                '/usr/bin/ffmpeg',
            ])
        else:  # Linux
            paths.extend([
                '/usr/bin/ffmpeg',
                '/usr/local/bin/ffmpeg',
                '/opt/ffmpeg/bin/ffmpeg',
            ])
        
        return paths
    
    def _verify_ffmpeg(self, ffmpeg_path: str) -> bool:
        """验证FFmpeg是否可用"""
        try:
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # 提取版本信息
                version_line = result.stdout.split('\n')[0]
                self.ffmpeg_version = version_line
                logger.info(f"FFmpeg版本: {version_line}")
                return True
            return False
        except Exception as e:
            logger.error(f"验证FFmpeg失败: {e}")
            return False
    
    def get_ffmpeg_path(self) -> Optional[str]:
        """获取FFmpeg路径（仅系统FFmpeg）"""
        if self.ffmpeg_method == "system":
            return self.system_ffmpeg_path
        return None
    
    def is_available(self) -> bool:
        """检查FFmpeg是否可用"""
        return self.ffmpeg_available
    
    def get_method(self) -> str:
        """获取FFmpeg使用方法"""
        return self.ffmpeg_method
    
    def get_version(self) -> Optional[str]:
        """获取FFmpeg版本"""
        return self.ffmpeg_version
    
    def convert_video(self, input_path: str, output_path: str, 
                     format_params: Dict = None) -> bool:
        """
        转换视频格式
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            format_params: 格式参数
            
        Returns:
            bool: 转换是否成功
        """
        try:
            if self.ffmpeg_method == "system":
                return self._convert_with_system_ffmpeg(input_path, output_path, format_params)
            elif self.ffmpeg_method == "python":
                return self._convert_with_python_ffmpeg(input_path, output_path, format_params)
            elif self.ffmpeg_method == "moviepy":
                return self._convert_with_moviepy(input_path, output_path, format_params)
            else:
                logger.error("没有可用的FFmpeg")
                return False
                
        except Exception as e:
            logger.error(f"视频转换失败: {e}")
            return False
    
    def _convert_with_system_ffmpeg(self, input_path: str, output_path: str, 
                                   format_params: Dict = None) -> bool:
        """使用系统FFmpeg转换"""
        try:
            cmd = [self.system_ffmpeg_path, '-i', input_path]
            
            # 添加格式参数
            if format_params:
                if 'codec' in format_params:
                    cmd.extend(['-c:v', format_params['codec']])
                if 'bitrate' in format_params:
                    cmd.extend(['-b:v', str(format_params['bitrate'])])
                if 'resolution' in format_params:
                    cmd.extend(['-s', format_params['resolution']])
            
            cmd.append(output_path)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"系统FFmpeg转换失败: {e}")
            return False
    
    def _convert_with_python_ffmpeg(self, input_path: str, output_path: str, 
                                   format_params: Dict = None) -> bool:
        """使用Python FFmpeg库转换"""
        try:
            if not FFMPEG_PYTHON_AVAILABLE:
                return False
            
            # 构建FFmpeg命令
            stream = ffmpeg.input(input_path)
            
            # 添加格式参数
            if format_params:
                if 'codec' in format_params:
                    stream = ffmpeg.output(stream, output_path, vcodec=format_params['codec'])
                else:
                    stream = ffmpeg.output(stream, output_path)
            else:
                stream = ffmpeg.output(stream, output_path)
            
            # 执行转换
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            return True
            
        except Exception as e:
            logger.error(f"Python FFmpeg转换失败: {e}")
            return False
    
    def _convert_with_moviepy(self, input_path: str, output_path: str, 
                             format_params: Dict = None) -> bool:
        """使用MoviePy转换"""
        try:
            if not MOVIEPY_AVAILABLE:
                return False
            
            # 加载视频
            clip = VideoFileClip(input_path)
            
            # 转换并保存
            clip.write_videofile(output_path, verbose=False, logger=None)
            clip.close()
            
            return True
            
        except Exception as e:
            logger.error(f"MoviePy转换失败: {e}")
            return False
    
    def extract_audio(self, video_path: str, audio_path: str, 
                     audio_format: str = "mp3") -> bool:
        """
        提取音频
        
        Args:
            video_path: 视频文件路径
            audio_path: 音频输出路径
            audio_format: 音频格式
            
        Returns:
            bool: 提取是否成功
        """
        try:
            if self.ffmpeg_method == "system":
                return self._extract_audio_with_system_ffmpeg(video_path, audio_path, audio_format)
            elif self.ffmpeg_method == "python":
                return self._extract_audio_with_python_ffmpeg(video_path, audio_path, audio_format)
            elif self.ffmpeg_method == "moviepy":
                return self._extract_audio_with_moviepy(video_path, audio_path, audio_format)
            else:
                return False
                
        except Exception as e:
            logger.error(f"音频提取失败: {e}")
            return False
    
    def _extract_audio_with_system_ffmpeg(self, video_path: str, audio_path: str, 
                                        audio_format: str) -> bool:
        """使用系统FFmpeg提取音频"""
        try:
            cmd = [
                self.system_ffmpeg_path, '-i', video_path,
                '-vn', '-acodec', audio_format, audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"系统FFmpeg音频提取失败: {e}")
            return False
    
    def _extract_audio_with_python_ffmpeg(self, video_path: str, audio_path: str, 
                                        audio_format: str) -> bool:
        """使用Python FFmpeg库提取音频"""
        try:
            if not FFMPEG_PYTHON_AVAILABLE:
                return False
            
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(stream, audio_path, vn=None, acodec=audio_format)
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            return True
            
        except Exception as e:
            logger.error(f"Python FFmpeg音频提取失败: {e}")
            return False
    
    def _extract_audio_with_moviepy(self, video_path: str, audio_path: str, 
                                   audio_format: str) -> bool:
        """使用MoviePy提取音频"""
        try:
            if not MOVIEPY_AVAILABLE:
                return False
            
            clip = VideoFileClip(video_path)
            clip.audio.write_audiofile(audio_path, verbose=False, logger=None)
            clip.close()
            return True
            
        except Exception as e:
            logger.error(f"MoviePy音频提取失败: {e}")
            return False
    
    def get_video_info(self, video_path: str) -> Optional[Dict]:
        """
        获取视频信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            Optional[Dict]: 视频信息字典
        """
        try:
            if self.ffmpeg_method == "system":
                return self._get_video_info_with_system_ffmpeg(video_path)
            elif self.ffmpeg_method == "python":
                return self._get_video_info_with_python_ffmpeg(video_path)
            elif self.ffmpeg_method == "moviepy":
                return self._get_video_info_with_moviepy(video_path)
            else:
                return None
                
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
            return None
    
    def _get_video_info_with_system_ffmpeg(self, video_path: str) -> Optional[Dict]:
        """使用系统FFmpeg获取视频信息"""
        try:
            cmd = [
                self.system_ffmpeg_path, '-i', video_path,
                '-f', 'null', '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # 解析输出获取视频信息
            info = {}
            for line in result.stderr.split('\n'):
                if 'Duration:' in line:
                    # 解析时长
                    duration_match = line.split('Duration:')[1].split(',')[0].strip()
                    info['duration'] = duration_match
                elif 'Stream' in line and 'Video:' in line:
                    # 解析视频流信息
                    parts = line.split(',')
                    for part in parts:
                        if 'x' in part and part.strip().replace('x', '').replace(' ', '').isdigit():
                            info['resolution'] = part.strip()
                        elif 'fps' in part:
                            info['fps'] = part.strip()
            
            return info
            
        except Exception as e:
            logger.error(f"系统FFmpeg获取视频信息失败: {e}")
            return None
    
    def _get_video_info_with_python_ffmpeg(self, video_path: str) -> Optional[Dict]:
        """使用Python FFmpeg库获取视频信息"""
        try:
            if not FFMPEG_PYTHON_AVAILABLE:
                return None
            
            probe = ffmpeg.probe(video_path)
            if 'streams' in probe:
                video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
                if video_stream:
                    return {
                        'duration': probe.get('format', {}).get('duration'),
                        'resolution': f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}",
                        'fps': video_stream.get('r_frame_rate', '0'),
                        'codec': video_stream.get('codec_name', 'unknown')
                    }
            return None
            
        except Exception as e:
            logger.error(f"Python FFmpeg获取视频信息失败: {e}")
            return None
    
    def _get_video_info_with_moviepy(self, video_path: str) -> Optional[Dict]:
        """使用MoviePy获取视频信息"""
        try:
            if not MOVIEPY_AVAILABLE:
                return None
            
            clip = VideoFileClip(video_path)
            info = {
                'duration': clip.duration,
                'resolution': f"{clip.w}x{clip.h}",
                'fps': clip.fps
            }
            clip.close()
            return info
            
        except Exception as e:
            logger.error(f"MoviePy获取视频信息失败: {e}")
            return None
    
    def get_installation_guide(self) -> str:
        """获取FFmpeg安装指导"""
        system = platform.system().lower()
        
        if system == "windows":
            return """
Windows FFmpeg安装方法：
1. 访问 https://ffmpeg.org/download.html
2. 下载Windows版本
3. 解压到任意目录
4. 将bin目录添加到系统PATH环境变量
5. 重启命令行或IDE
            """.strip()
        elif system == "darwin":
            return """
macOS FFmpeg安装方法：
1. 使用Homebrew: brew install ffmpeg
2. 或访问 https://ffmpeg.org/download.html 下载macOS版本
            """.strip()
        else:
            return """
Linux FFmpeg安装方法：
Ubuntu/Debian: sudo apt-get install ffmpeg
CentOS/RHEL: sudo yum install ffmpeg
Arch: sudo pacman -S ffmpeg
            """.strip()


# 全局FFmpeg管理器实例
ffmpeg_manager = FFmpegManager()
