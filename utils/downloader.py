import logging
import time
from PyQt6.QtCore import QObject, pyqtSignal

from .platform_factory import PlatformFactory
from .video_info import VideoInfo
from .download_utils import check_ytdlp_version, check_ffmpeg_installed

logger = logging.getLogger(__name__)

class Downloader(QObject):
    """
    Main downloader class that uses PlatformFactory to handle different platforms.
    """
    
    # Signals for the UI
    progress_signal = pyqtSignal(str, float, str)  # url, progress percentage, speed
    finished_signal = pyqtSignal(str, bool, str)   # url, success, file_path
    info_signal = pyqtSignal(str, object)          # url, video_info (as object)
    api_error_signal = pyqtSignal(str, str)        # url, error_message
    
    def __init__(self):
        super().__init__()
        self.output_dir = ""
        self.downloads = {}  # Store information about downloaded videos
        
        # Validate yt-dlp version
        is_current, latest = check_ytdlp_version()
        if not is_current:
            logger.warning(f"Using outdated yt-dlp version. Latest available: {latest}")
        
        # Connect signals from platform handlers
        self._connect_platform_signals()
    
    def _connect_platform_signals(self):
        """Connect signals from all platform handlers to our own signals"""
        for platform_name, handler in PlatformFactory.get_all_platforms().items():
            # Connect signals to forward them
            handler.progress_signal.connect(self.progress_signal)
            handler.finished_signal.connect(self.finished_signal)
            handler.info_signal.connect(self.info_signal)
            handler.api_error_signal.connect(self.api_error_signal)
            
            # Set the output directory
            if self.output_dir:
                handler.set_output_dir(self.output_dir)
    
    def set_output_dir(self, directory):
        """Set the output directory for all platform handlers"""
        self.output_dir = directory
        PlatformFactory.set_output_dir_for_all(directory)
    
    def get_video_info(self, url):
        """
        Get video information from URL by using the appropriate platform handler
        
        Args:
            url: Video URL
            
        Returns:
            VideoInfo object with video details
        """
        # Get the appropriate handler for this URL
        handler = PlatformFactory.get_handler_for_url(url)
        
        if handler:
            # Use the handler to get video info
            return handler.get_video_info(url)
        else:
            # No handler found for this URL
            info = VideoInfo()
            info.url = url
            info.title = "Unsupported URL"
            self.api_error_signal.emit(url, "No handler found for URL. Supported platforms: " + 
                                       ", ".join(PlatformFactory.get_supported_platforms()))
            self.info_signal.emit(url, info)
            return info
    
    def download_video(self, url, format_id=None, output_template=None, audio_only=False, force_overwrite=False):
        """
        Download video from URL using the appropriate platform handler
        
        Args:
            url: Video URL
            format_id: Format ID to download (if None, best quality will be chosen)
            output_template: Output filename template
            audio_only: Whether to download audio only
            force_overwrite: Overwrite if file exists
        """
        # Get the appropriate handler for this URL
        handler = PlatformFactory.get_handler_for_url(url)
        
        if handler:
            # Use the handler to download the video
            handler.download_video(url, format_id, output_template, audio_only, force_overwrite)
        else:
            # No handler found for this URL
            self.api_error_signal.emit(url, "No handler found for URL. Supported platforms: " + 
                                      ", ".join(PlatformFactory.get_supported_platforms()))
            self.finished_signal.emit(url, False, "")
    
    @staticmethod
    def check_ffmpeg_installed():
        """
        Check if FFmpeg is installed and accessible
        
        Returns:
            tuple: (bool, str) - True if FFmpeg is installed, error message if not
        """
        return check_ffmpeg_installed()
    
    def get_supported_platforms(self):
        """
        Get a list of all supported platform names
        
        Returns:
            list: Platform names
        """
        return PlatformFactory.get_supported_platforms()
    
    def is_valid_url(self, url):
        """
        Check if URL is valid for any supported platform
        
        Args:
            url: URL to check
            
        Returns:
            tuple: (bool, str) - Is valid, platform name if valid
        """
        handler = PlatformFactory.get_handler_for_url(url)
        if handler:
            return True, handler.get_platform_name()
        return False, "" 