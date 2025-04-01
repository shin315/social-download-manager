from PyQt6.QtCore import QThread, pyqtSignal
from datetime import datetime
import os

class DownloadThread(QThread):
    progress_updated = pyqtSignal(int)
    download_finished = pyqtSignal(dict)
    download_error = pyqtSignal(str)
    
    def __init__(self, video_url, output_folder, quality, format, no_watermark, video_info):
        super().__init__()
        self.video_url = video_url
        self.output_folder = output_folder
        self.quality = quality
        self.format = format
        self.no_watermark = no_watermark
        self.video_info = video_info
        
    def run(self):
        try:
            # Simulate the actual download process
            # Replace with your actual download code
            self.progress_updated.emit(50)
            
            # When download completes, emit download info
            download_info = {
                'url': self.video_url,
                'title': self.video_info.title,
                'filepath': os.path.join(self.output_folder, f"{self.video_info.title}.{self.format.lower()}"),
                'quality': self.quality,
                'format': self.format,
                'duration': self.video_info.duration,
                'filesize': self.calculate_size(),  # Calculate size based on quality
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'description': self.video_info.description if hasattr(self.video_info, 'description') else '',
                'hashtags': self.video_info.hashtags if hasattr(self.video_info, 'hashtags') else []
            }
            
            self.progress_updated.emit(100)
            self.download_finished.emit(download_info)
            
        except Exception as e:
            self.download_error.emit(str(e))
            
    def calculate_size(self):
        """Calculate file size based on quality"""
        # Define average file size per minute for different quality levels
        size_per_minute = {
            '1080p': 60,  # MB/minute
            '720p': 30,   # MB/minute
            '480p': 15,   # MB/minute
            '360p': 10    # MB/minute
        }
        
        # Get duration in minutes
        duration_minutes = self.video_info.duration / 60 if hasattr(self.video_info, 'duration') else 1
        
        # Calculate size based on quality
        quality_size = size_per_minute.get(self.quality, 30)  # Default to 30MB/minute if quality not found
        
        # If audio format, size will be much smaller
        if self.format.lower() == 'mp3':
            quality_size = 2  # 2MB/minute for audio
            
        estimated_size = round(duration_minutes * quality_size, 2)
        return estimated_size 