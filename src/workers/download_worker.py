"""下载工作线程模块"""

from typing import Dict, Optional
from PyQt5.QtCore import QThread, pyqtSignal
import yt_dlp

class DownloadWorker(QThread):
    """视频下载工作线程"""
    
    progress_signal = pyqtSignal(dict)
    log_signal = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    class DownloadCancelled(Exception):
        pass

    class DownloadPaused(Exception):
        pass

    def __init__(self, url: str, ydl_opts: Dict):
        super().__init__()
        self.url = url
        self.ydl_opts = ydl_opts
        self._is_cancelled = False
        self._is_paused = False
        self.last_filename: Optional[str] = None

    def cancel(self) -> None:
        self._is_cancelled = True

    def pause(self) -> None:
        self._is_paused = True

    def resume(self) -> None:
        self._is_paused = False

    def progress_hook(self, d: Dict) -> None:
        if self._is_cancelled:
            raise self.DownloadCancelled("下载已取消")
        
        if self._is_paused:
            raise self.DownloadPaused("下载已暂停")
        
        if d["status"] == "finished":
            self.last_filename = d.get("filename", "")
        
        self.progress_signal.emit(d)

    def run(self) -> None:
        try:
            self.ydl_opts["progress_hooks"] = [self.progress_hook]
            
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                while True:
                    try:
                        if self._is_cancelled:
                            break
                        
                        if self._is_paused:
                            self.msleep(500)
                            continue
                        
                        ydl.download([self.url])
                        break
                        
                    except self.DownloadPaused:
                        self.log_signal.emit("下载暂停...")
                        self.msleep(500)
                        continue
                        
                    except self.DownloadCancelled:
                        self.log_signal.emit("下载已取消")
                        break
                
                if not self._is_cancelled:
                    self.finished.emit(self.last_filename or "")
                    
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))
