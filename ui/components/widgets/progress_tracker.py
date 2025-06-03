"""
Progress Tracker Widget

Widget for tracking download progress with speed and status indicators.
Extracted from progress handling logic in video_info_tab.py.
"""

from typing import Dict, Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtCore import Qt

from ..common.interfaces import ComponentInterface, ProgressInterface
from ..common import QWidgetABCMeta
from ..mixins.language_support import LanguageSupport
from ..mixins.theme_support import ThemeSupport

class ProgressTracker(QWidget, ComponentInterface, ProgressInterface, 
                     LanguageSupport, ThemeSupport, metaclass=QWidgetABCMeta):
    """Widget for tracking download progress"""
    
    progress_updated = pyqtSignal(int, str)  # progress, speed
    progress_completed = pyqtSignal()
    progress_failed = pyqtSignal(str)  # error message
    progress_cancelled = pyqtSignal()
    
    def __init__(self, parent=None, lang_manager=None, show_speed=True, 
                 show_status=True, compact_mode=False):
        QWidget.__init__(self, parent)
        ComponentInterface.__init__(self)
        ProgressInterface.__init__(self)
        LanguageSupport.__init__(self, "ProgressTracker", lang_manager)
        ThemeSupport.__init__(self, "ProgressTracker")
        
        self.show_speed = show_speed
        self.show_status = show_status
        self.compact_mode = compact_mode
        
        # Progress state
        self._current_progress = 0
        self._current_speed = ""
        self._current_status = ""
        self._is_indeterminate = False
        self._is_completed = False
        self._is_failed = False
        
        # Speed calculation
        self._last_update_time = None
        self._speed_history = []
        self._speed_timer = QTimer()
        self._speed_timer.timeout.connect(self._update_speed_display)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize the progress tracker UI"""
        if self.compact_mode:
            self.layout = QHBoxLayout(self)
            self.layout.setContentsMargins(0, 0, 0, 0)
            self.layout.setSpacing(5)
        else:
            self.layout = QVBoxLayout(self)
            self.layout.setContentsMargins(5, 5, 5, 5)
            self.layout.setSpacing(3)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        
        if self.compact_mode:
            self.progress_bar.setMaximumHeight(20)
        else:
            self.progress_bar.setMaximumHeight(25)
        
        self.layout.addWidget(self.progress_bar)
        
        # Status and speed layout
        if self.show_status or self.show_speed:
            if self.compact_mode:
                info_layout = QVBoxLayout()
                info_layout.setContentsMargins(0, 0, 0, 0)
                info_layout.setSpacing(1)
            else:
                info_layout = QHBoxLayout()
                info_layout.setContentsMargins(0, 0, 0, 0)
                info_layout.setSpacing(10)
            
            # Status label
            if self.show_status:
                self.status_label = QLabel()
                self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                if self.compact_mode:
                    self.status_label.setMaximumHeight(15)
                    self.status_label.setStyleSheet("font-size: 11px;")
                info_layout.addWidget(self.status_label)
            
            # Speed label
            if self.show_speed:
                self.speed_label = QLabel()
                if self.compact_mode:
                    self.speed_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    self.speed_label.setMaximumHeight(15)
                    self.speed_label.setStyleSheet("font-size: 11px; color: #666;")
                else:
                    self.speed_label.setAlignment(Qt.AlignmentFlag.AlignRight)
                info_layout.addWidget(self.speed_label)
            
            if not self.compact_mode and self.show_status and self.show_speed:
                info_layout.addStretch(1)
            
            self.layout.addLayout(info_layout)
        
        # Initialize display
        self.reset_progress()
    
    def update_language(self):
        """Update labels for language changes"""
        self._update_status_display()
        self._update_speed_display()
    
    def apply_theme(self, theme: Dict):
        """Apply theme to progress tracker"""
        super().apply_theme(theme)
        
        # Apply theme to progress bar
        if 'progress_bar_style' in theme:
            self.progress_bar.setStyleSheet(theme['progress_bar_style'])
        
        # Apply theme to labels
        if 'progress_label_style' in theme:
            if hasattr(self, 'status_label'):
                self.status_label.setStyleSheet(theme['progress_label_style'])
            if hasattr(self, 'speed_label'):
                self.speed_label.setStyleSheet(theme['progress_label_style'])
    
    def update_progress(self, progress: int, message: str = ""):
        """Update progress value and message"""
        self._current_progress = max(0, min(100, progress))
        self._current_status = message or ""
        
        # Update progress bar
        if not self._is_indeterminate:
            self.progress_bar.setValue(self._current_progress)
        
        # Update status
        self._update_status_display()
        
        # Check for completion
        if self._current_progress >= 100 and not self._is_completed:
            self._mark_completed()
        
        # Emit signal
        self.progress_updated.emit(self._current_progress, self._current_speed)
    
    def set_indeterminate(self, indeterminate: bool):
        """Set progress bar to indeterminate state"""
        self._is_indeterminate = indeterminate
        
        if indeterminate:
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(0)
        else:
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(self._current_progress)
    
    def reset_progress(self):
        """Reset progress to initial state"""
        self._current_progress = 0
        self._current_speed = ""
        self._current_status = ""
        self._is_indeterminate = False
        self._is_completed = False
        self._is_failed = False
        
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        
        self._update_status_display()
        self._update_speed_display()
        
        # Stop speed timer
        self._speed_timer.stop()
        self._speed_history.clear()
    
    def set_speed(self, speed: str):
        """Set download speed"""
        self._current_speed = speed
        self._update_speed_display()
        
        # Start speed timer if not running
        if speed and not self._speed_timer.isActive():
            self._speed_timer.start(1000)  # Update every second
    
    def set_status(self, status: str):
        """Set status message"""
        self._current_status = status
        self._update_status_display()
    
    def set_error(self, error_message: str):
        """Set error state"""
        self._is_failed = True
        self._current_status = error_message
        self._update_status_display()
        
        # Set progress bar to error style
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff0000; }")
        
        self.progress_failed.emit(error_message)
    
    def set_completed(self):
        """Mark progress as completed"""
        self._mark_completed()
    
    def _mark_completed(self):
        """Internal method to mark as completed"""
        self._is_completed = True
        self._current_progress = 100
        self.progress_bar.setValue(100)
        
        if not self._current_status:
            self._current_status = self.tr_("PROGRESS_COMPLETED") or "Completed"
        
        self._update_status_display()
        
        # Set progress bar to completed style
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #00aa00; }")
        
        # Stop speed timer
        self._speed_timer.stop()
        
        self.progress_completed.emit()
    
    def _update_status_display(self):
        """Update status label display"""
        if not hasattr(self, 'status_label') or not self.show_status:
            return
        
        if self._is_failed:
            status_text = f"❌ {self._current_status}"
        elif self._is_completed:
            status_text = f"✅ {self._current_status}"
        elif self._current_status:
            if self._current_progress > 0:
                status_text = f"⏳ {self._current_status} ({self._current_progress}%)"
            else:
                status_text = f"⏳ {self._current_status}"
        else:
            if self._current_progress > 0:
                status_text = f"{self._current_progress}%"
            else:
                status_text = self.tr_("PROGRESS_READY") or "Ready"
        
        self.status_label.setText(status_text)
    
    def _update_speed_display(self):
        """Update speed label display"""
        if not hasattr(self, 'speed_label') or not self.show_speed:
            return
        
        if self._current_speed and not self._is_completed and not self._is_failed:
            speed_text = f"🚀 {self._current_speed}"
        else:
            speed_text = ""
        
        self.speed_label.setText(speed_text)
    
    def get_progress(self) -> int:
        """Get current progress value"""
        return self._current_progress
    
    def get_speed(self) -> str:
        """Get current speed"""
        return self._current_speed
    
    def get_status(self) -> str:
        """Get current status"""
        return self._current_status
    
    def is_completed(self) -> bool:
        """Check if progress is completed"""
        return self._is_completed
    
    def is_failed(self) -> bool:
        """Check if progress failed"""
        return self._is_failed
    
    def is_active(self) -> bool:
        """Check if progress is active (not completed or failed)"""
        return not self._is_completed and not self._is_failed and self._current_progress > 0

# Factory functions for common progress tracker configurations

def create_download_progress_tracker(parent=None, lang_manager=None) -> ProgressTracker:
    """Create progress tracker for downloads with speed and status"""
    return ProgressTracker(parent, lang_manager, show_speed=True, show_status=True)

def create_simple_progress_tracker(parent=None, lang_manager=None) -> ProgressTracker:
    """Create simple progress tracker without speed/status"""
    return ProgressTracker(parent, lang_manager, show_speed=False, show_status=False)

def create_compact_progress_tracker(parent=None, lang_manager=None) -> ProgressTracker:
    """Create compact progress tracker for table cells"""
    return ProgressTracker(parent, lang_manager, show_speed=True, 
                         show_status=True, compact_mode=True) 