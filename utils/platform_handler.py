from abc import ABC, ABCMeta, abstractmethod
from PyQt6.QtCore import QObject, pyqtSignal

# Tạo metaclass kết hợp
class ABCQObjectMeta(type(QObject), ABCMeta):
    pass

class PlatformHandler(QObject, ABC, metaclass=ABCQObjectMeta):
    """
    Abstract base class for all platform handlers.
    Defines the interface that all platform-specific handlers must implement.
    """
    
    # Common signals for all platforms
    progress_signal = pyqtSignal(str, float, str)  # url, progress percentage, speed
    finished_signal = pyqtSignal(str, bool, str)   # url, success, file_path
    info_signal = pyqtSignal(str, object)          # url, video_info (as object)
    api_error_signal = pyqtSignal(str, str)        # url, error_message
    
    def __init__(self):
        super().__init__()
        self.output_dir = ""
        self.downloads = {}
        self.downloading_urls = set()
    
    def set_output_dir(self, directory):
        """Set the output directory"""
        self.output_dir = directory
    
    @abstractmethod
    def get_video_info(self, url):
        """
        Get video information from URL
        
        Args:
            url: Video URL
            
        Returns:
            VideoInfo object with video details
        """
        pass
    
    @abstractmethod
    def download_video(self, url, format_id=None, output_template=None, audio_only=False, force_overwrite=False):
        """
        Download video from URL
        
        Args:
            url: Video URL
            format_id: Format ID to download (if None, best quality will be chosen)
            output_template: Output filename template
            audio_only: Whether to download audio only
            force_overwrite: Overwrite if file exists
        """
        pass
    
    @abstractmethod
    def is_valid_url(self, url):
        """
        Check if URL is valid for this platform
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if URL is valid for this platform, False otherwise
        """
        pass
    
    @staticmethod
    @abstractmethod
    def get_platform_name():
        """
        Get the name of the platform
        
        Returns:
            str: Platform name
        """
        pass
    
    @staticmethod
    @abstractmethod
    def get_platform_icon():
        """
        Get the path to the platform icon
        
        Returns:
            str: Path to platform icon
        """
        pass 