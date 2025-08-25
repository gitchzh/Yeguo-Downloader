"""解析工作线程模块"""

from PyQt5.QtCore import QThread, pyqtSignal
import yt_dlp

class ParseWorker(QThread):
    """视频解析工作线程"""
    
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)  # 新增状态信号
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self) -> None:
        try:
            self.status_signal.emit("开始解析视频...")
            
            ydl_opts = {
                "quiet": False,
                "no_warnings": False,
                "format_sort": ["+size"],
                "merge_output_format": "mp4",
            }
            
            self.status_signal.emit("初始化下载器...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.status_signal.emit("正在获取视频信息...")
                info = ydl.extract_info(self.url, download=False)
                
                if info is None:
                    raise ValueError("无法提取视频信息")
                
                self.status_signal.emit("处理视频格式...")
                
                if "entries" in info:
                    for entry in info["entries"]:
                        if entry:
                            if "formats" not in entry or not entry["formats"]:
                                entry["formats"] = info.get("formats", [])
                            self.finished.emit(entry)
                else:
                    self.finished.emit(info)
                    
        except Exception as e:
            error_msg = f"解析 {self.url} 失败: {str(e)}"
            self.error.emit(error_msg)
