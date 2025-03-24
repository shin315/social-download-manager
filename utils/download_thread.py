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
            # Giả sử đây là quá trình tải xuống thực tế
            # Thay thế bằng code tải xuống thực của bạn
            self.progress_updated.emit(50)
            
            # Khi tải xong, emit thông tin download
            download_info = {
                'url': self.video_url,
                'title': self.video_info.title,
                'filepath': os.path.join(self.output_folder, f"{self.video_info.title}.{self.format.lower()}"),
                'quality': self.quality,
                'format': self.format,
                'duration': self.video_info.duration,
                'filesize': self.calculate_size(),  # Tính toán size dựa trên quality
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'description': self.video_info.description if hasattr(self.video_info, 'description') else '',
                'hashtags': self.video_info.hashtags if hasattr(self.video_info, 'hashtags') else []
            }
            
            self.progress_updated.emit(100)
            self.download_finished.emit(download_info)
            
        except Exception as e:
            self.download_error.emit(str(e))
            
    def calculate_size(self):
        """Tính toán dung lượng file dựa trên chất lượng"""
        # Định nghĩa dung lượng trung bình cho mỗi phút video ở các chất lượng khác nhau
        size_per_minute = {
            '1080p': 60,  # MB/phút
            '720p': 30,   # MB/phút
            '480p': 15,   # MB/phút
            '360p': 10    # MB/phút
        }
        
        # Lấy duration tính bằng phút
        duration_minutes = self.video_info.duration / 60 if hasattr(self.video_info, 'duration') else 1
        
        # Tính dung lượng dựa trên chất lượng
        quality_size = size_per_minute.get(self.quality, 30)  # Mặc định 30MB/phút nếu không tìm thấy
        
        # Nếu là audio, dung lượng sẽ nhỏ hơn nhiều
        if self.format.lower() == 'mp3':
            quality_size = 2  # 2MB/phút cho audio
            
        estimated_size = round(duration_minutes * quality_size, 2)
        return estimated_size 