"""
Thumbnail Widget

Widget for displaying and managing video thumbnails with loading states.
Extracted from thumbnail handling logic in downloaded_videos_tab.py and video_info_tab.py.
"""

from typing import Optional, Dict
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, QThread, QObject
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtGui import QPixmap, QMovie, QCursor
from PyQt6.QtCore import Qt

from ..common.interfaces import ComponentInterface, ThumbnailInterface
from ..common import QWidgetABCMeta
from ..mixins.language_support import LanguageSupport
from ..mixins.theme_support import ThemeSupport

class ThumbnailLoader(QObject):
    """Background thumbnail loader"""
    
    thumbnail_loaded = pyqtSignal(str, QPixmap)  # url, pixmap
    thumbnail_failed = pyqtSignal(str, str)  # url, error
    
    def __init__(self):
        super().__init__()
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self._on_download_finished)
        self._active_requests = {}
    
    def load_thumbnail(self, url: str):
        """Load thumbnail from URL"""
        if not url or url in self._active_requests:
            return
            
        request = QNetworkRequest(url)
        request.setRawHeader(b'User-Agent', b'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        reply = self.network_manager.get(request)
        self._active_requests[url] = reply
    
    def _on_download_finished(self, reply: QNetworkReply):
        """Handle download completion"""
        url = reply.url().toString()
        
        # Remove from active requests
        if url in self._active_requests:
            del self._active_requests[url]
        
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            
            if pixmap.loadFromData(data):
                self.thumbnail_loaded.emit(url, pixmap)
            else:
                self.thumbnail_failed.emit(url, "Failed to parse image data")
        else:
            self.thumbnail_failed.emit(url, reply.errorString())
        
        reply.deleteLater()
    
    def cancel_all_requests(self):
        """Cancel all active requests"""
        for reply in self._active_requests.values():
            reply.abort()
        self._active_requests.clear()

class ThumbnailWidget(QLabel, ComponentInterface, ThumbnailInterface, 
                     LanguageSupport, ThemeSupport, metaclass=QWidgetABCMeta):
    """Widget for displaying video thumbnails with loading states"""
    
    thumbnail_clicked = pyqtSignal(str)  # URL or path
    thumbnail_loaded = pyqtSignal(str, QPixmap)  # URL, pixmap
    thumbnail_failed = pyqtSignal(str, str)  # URL, error
    
    def __init__(self, parent=None, lang_manager=None, size=(120, 90)):
        QLabel.__init__(self, parent)
        ComponentInterface.__init__(self)
        ThumbnailInterface.__init__(self)
        LanguageSupport.__init__(self, "ThumbnailWidget", lang_manager)
        ThemeSupport.__init__(self, "ThumbnailWidget")
        
        self.thumbnail_size = size
        self.current_url = ""
        self.loading_state = False
        
        # Thumbnail loader
        self.loader = ThumbnailLoader()
        self.loader.thumbnail_loaded.connect(self._on_thumbnail_loaded)
        self.loader.thumbnail_failed.connect(self._on_thumbnail_failed)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize the thumbnail widget UI"""
        # Set fixed size
        self.setFixedSize(*self.thumbnail_size)
        
        # Set alignment
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Set cursor to pointer for clickable behavior
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Set placeholder
        self.set_placeholder()
        
        # Set border
        self.setStyleSheet("border: 1px solid #ccc; border-radius: 4px;")
    
    def update_language(self):
        """Update language-specific content"""
        if not self.current_url and not self.loading_state:
            self.set_placeholder()
    
    def apply_theme(self, theme: Dict):
        """Apply theme to thumbnail widget"""
        super().apply_theme(theme)
        
        if 'thumbnail_border_color' in theme:
            border_color = theme['thumbnail_border_color']
            self.setStyleSheet(f"border: 1px solid {border_color}; border-radius: 4px;")
    
    def load_thumbnail(self, url: str):
        """Load thumbnail from URL"""
        if not url:
            self.clear_thumbnail()
            return
        
        self.current_url = url
        self.set_loading_state()
        self.loader.load_thumbnail(url)
    
    def set_thumbnail(self, image_data: bytes):
        """Set thumbnail from image data"""
        pixmap = QPixmap()
        if pixmap.loadFromData(image_data):
            self.set_pixmap(pixmap)
        else:
            self.set_error_state()
    
    def set_pixmap(self, pixmap: QPixmap):
        """Set thumbnail pixmap"""
        if pixmap.isNull():
            self.set_error_state()
            return
        
        # Scale pixmap to fit widget while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            self.thumbnail_size[0], self.thumbnail_size[1],
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.setPixmap(scaled_pixmap)
        self.loading_state = False
    
    def clear_thumbnail(self):
        """Clear current thumbnail"""
        self.current_url = ""
        self.loading_state = False
        self.set_placeholder()
    
    def set_placeholder(self):
        """Set placeholder image/text"""
        self.clear()
        self.setText(self.tr_("THUMBNAIL_PLACEHOLDER") or "No Image")
        self.setStyleSheet(self.styleSheet() + "color: #999; font-size: 12px;")
    
    def set_loading_state(self):
        """Set loading state"""
        self.loading_state = True
        self.clear()
        self.setText(self.tr_("THUMBNAIL_LOADING") or "Loading...")
        self.setStyleSheet(self.styleSheet() + "color: #666; font-size: 12px;")
    
    def set_error_state(self):
        """Set error state"""
        self.loading_state = False
        self.clear()
        self.setText(self.tr_("THUMBNAIL_ERROR") or "Error")
        self.setStyleSheet(self.styleSheet() + "color: #f00; font-size: 12px;")
    
    def _on_thumbnail_loaded(self, url: str, pixmap: QPixmap):
        """Handle successful thumbnail load"""
        if url == self.current_url:
            self.set_pixmap(pixmap)
            self.thumbnail_loaded.emit(url, pixmap)
    
    def _on_thumbnail_failed(self, url: str, error: str):
        """Handle failed thumbnail load"""
        if url == self.current_url:
            self.set_error_state()
            self.thumbnail_failed.emit(url, error)
    
    def mousePressEvent(self, event):
        """Handle mouse press for click events"""
        if event.button() == Qt.MouseButton.LeftButton and self.current_url:
            self.thumbnail_clicked.emit(self.current_url)
        super().mousePressEvent(event)
    
    def get_current_url(self) -> str:
        """Get current thumbnail URL"""
        return self.current_url
    
    def is_loading(self) -> bool:
        """Check if thumbnail is currently loading"""
        return self.loading_state
    
    def set_size(self, width: int, height: int):
        """Set thumbnail size"""
        self.thumbnail_size = (width, height)
        self.setFixedSize(width, height)
        
        # Re-scale current pixmap if available
        if self.pixmap() and not self.pixmap().isNull():
            current_pixmap = self.pixmap()
            self.set_pixmap(current_pixmap)
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'loader'):
            self.loader.cancel_all_requests()

# Utility functions for common thumbnail sizes

def create_small_thumbnail(parent=None, lang_manager=None) -> ThumbnailWidget:
    """Create small thumbnail widget (80x60)"""
    return ThumbnailWidget(parent, lang_manager, size=(80, 60))

def create_medium_thumbnail(parent=None, lang_manager=None) -> ThumbnailWidget:
    """Create medium thumbnail widget (120x90)"""
    return ThumbnailWidget(parent, lang_manager, size=(120, 90))

def create_large_thumbnail(parent=None, lang_manager=None) -> ThumbnailWidget:
    """Create large thumbnail widget (160x120)"""
    return ThumbnailWidget(parent, lang_manager, size=(160, 120)) 