# UI Module
# Lazy imports to avoid circular dependencies
# Import classes when needed rather than automatically

__all__ = ['MainWindow', 'VideoInfoTab', 'DownloadedVideosTab']

def get_main_window():
    """Lazy import for MainWindow"""
    from ui.main_window import MainWindow
    return MainWindow

def get_video_info_tab():
    """Lazy import for VideoInfoTab"""  
    from ui.video_info_tab import VideoInfoTab
    return VideoInfoTab

def get_downloaded_videos_tab():
    """Lazy import for DownloadedVideosTab"""
    from ui.downloaded_videos_tab import DownloadedVideosTab
    return DownloadedVideosTab 