"""
Toast Notification System for Social Download Manager
Provides elegant, non-intrusive notifications for download completion and other events
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout, 
                           QGraphicsDropShadowEffect, QApplication, QPushButton)
from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPainter, QPalette
from typing import Optional, Dict, Any, List
import time
from enum import Enum

class ToastType(Enum):
    """Types of toast notifications"""
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"
    DOWNLOAD_COMPLETE = "download_complete"
    DOWNLOAD_STARTED = "download_started"

class ToastManager:
    """Manages multiple toast notifications to prevent collision"""
    
    def __init__(self):
        self.active_toasts: List['ToastNotification'] = []
        self.toast_spacing = 10
        self.max_toasts = 5
        
    def show_toast(self, parent_widget: QWidget, message: str, toast_type: ToastType = ToastType.INFO,
                   duration: int = 3000, data: Optional[Dict[str, Any]] = None) -> 'ToastNotification':
        """Show a new toast notification with collision prevention"""
        
        # Remove expired toasts
        self._cleanup_expired_toasts()
        
        # Limit number of simultaneous toasts
        if len(self.active_toasts) >= self.max_toasts:
            # Remove oldest toast
            oldest_toast = self.active_toasts[0]
            oldest_toast.hide_immediately()
            self.active_toasts.pop(0)
        
        # Calculate position for new toast
        position = self._calculate_toast_position(parent_widget)
        
        # Create new toast
        toast = ToastNotification(parent_widget, message, toast_type, duration, data)
        toast.move(position)
        
        # Connect cleanup signal
        toast.toast_closed.connect(lambda: self._remove_toast(toast))
        
        # Add to active list
        self.active_toasts.append(toast)
        
        # Show the toast
        toast.show_animated()
        
        return toast
    
    def _calculate_toast_position(self, parent_widget: QWidget) -> QPoint:
        """Calculate position for new toast to avoid collision"""
        if not parent_widget:
            return QPoint(20, 20)
        
        # Start from top-right corner
        parent_rect = parent_widget.rect()
        x = parent_rect.width() - 320 - 20  # Toast width + margin
        y = 20
        
        # Adjust for existing toasts
        for toast in self.active_toasts:
            if toast.isVisible():
                toast_rect = toast.geometry()
                if toast_rect.top() <= y + 80:  # Toast height + spacing
                    y = toast_rect.bottom() + self.toast_spacing
        
        return QPoint(max(x, 20), y)
    
    def _cleanup_expired_toasts(self):
        """Remove expired toasts from active list"""
        self.active_toasts = [toast for toast in self.active_toasts 
                            if toast.isVisible() and not toast.is_expired()]
    
    def _remove_toast(self, toast: 'ToastNotification'):
        """Remove toast from active list"""
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
        # Reposition remaining toasts
        self._reposition_toasts()
    
    def _reposition_toasts(self):
        """Reposition remaining toasts to fill gaps"""
        if not self.active_toasts:
            return
        
        # Get parent from first toast
        parent_widget = self.active_toasts[0].parent()
        if not parent_widget:
            return
        
        parent_rect = parent_widget.rect()
        x = parent_rect.width() - 320 - 20
        y = 20
        
        for i, toast in enumerate(self.active_toasts):
            if toast.isVisible():
                target_pos = QPoint(x, y)
                if toast.pos() != target_pos:
                    # Animate to new position
                    toast.animate_to_position(target_pos)
                y += 80 + self.toast_spacing

class ToastNotification(QWidget):
    """Individual toast notification widget"""
    
    toast_closed = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget], message: str, 
                 toast_type: ToastType = ToastType.INFO, 
                 duration: int = 3000,
                 data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        
        self.message = message
        self.toast_type = toast_type
        self.duration = duration
        self.data = data or {}
        self.creation_time = time.time()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 70)
        
        self.setup_ui()
        self.setup_animations()
        self.setup_auto_hide_timer()
    
    def setup_ui(self):
        """Setup the toast UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)
        
        # Icon label
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setScaledContents(True)
        
        # Message label
        self.message_label = QLabel(self.message)
        self.message_label.setWordWrap(True)
        font = QFont()
        font.setPointSize(9)
        font.setWeight(QFont.Weight.Medium)
        self.message_label.setFont(font)
        
        # Close button
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.clicked.connect(self.hide_animated)
        font = QFont()
        font.setPointSize(12)
        font.setWeight(QFont.Weight.Bold)
        self.close_btn.setFont(font)
        
        # Layout
        layout.addWidget(self.icon_label)
        layout.addWidget(self.message_label, 1)
        layout.addWidget(self.close_btn)
        
        # Apply styling based on type
        self.apply_styling()
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 3)
        shadow.setColor(Qt.GlobalColor.black)
        self.setGraphicsEffect(shadow)
    
    def apply_styling(self):
        """Apply styling based on toast type"""
        styles = {
            ToastType.SUCCESS: {
                'bg_color': '#4CAF50',
                'text_color': 'white',
                'icon': '✓'
            },
            ToastType.ERROR: {
                'bg_color': '#F44336', 
                'text_color': 'white',
                'icon': '✕'
            },
            ToastType.WARNING: {
                'bg_color': '#FF9800',
                'text_color': 'white', 
                'icon': '⚠'
            },
            ToastType.INFO: {
                'bg_color': '#2196F3',
                'text_color': 'white',
                'icon': 'ℹ'
            },
            ToastType.DOWNLOAD_COMPLETE: {
                'bg_color': '#4CAF50',
                'text_color': 'white',
                'icon': '⬇'
            },
            ToastType.DOWNLOAD_STARTED: {
                'bg_color': '#2196F3',
                'text_color': 'white', 
                'icon': '⬇'
            }
        }
        
        style = styles.get(self.toast_type, styles[ToastType.INFO])
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {style['bg_color']};
                border-radius: 8px;
                border: none;
            }}
            QLabel {{
                color: {style['text_color']};
                background: transparent;
                border: none;
            }}
            QPushButton {{
                background: rgba(255, 255, 255, 0.3);
                color: {style['text_color']};
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.5);
            }}
        """)
        
        # Set icon text
        self.icon_label.setText(style['icon'])
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        font.setWeight(QFont.Weight.Bold)
        self.icon_label.setFont(font)
    
    def setup_animations(self):
        """Setup show/hide animations"""
        self.show_animation = QPropertyAnimation(self, b"geometry")
        self.show_animation.setDuration(300)
        self.show_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.hide_animation = QPropertyAnimation(self, b"geometry") 
        self.hide_animation.setDuration(250)
        self.hide_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.hide_animation.finished.connect(self.hide)
        self.hide_animation.finished.connect(self.toast_closed.emit)
        
        self.move_animation = QPropertyAnimation(self, b"pos")
        self.move_animation.setDuration(200)
        self.move_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def setup_auto_hide_timer(self):
        """Setup timer to auto-hide toast"""
        if self.duration > 0:
            self.hide_timer = QTimer()
            self.hide_timer.setSingleShot(True)
            self.hide_timer.timeout.connect(self.hide_animated)
            
    def show_animated(self):
        """Show toast with slide-in animation"""
        self.show()
        
        # Start position (slide from right)
        start_rect = QRect(self.x() + 100, self.y(), self.width(), self.height())
        end_rect = QRect(self.x(), self.y(), self.width(), self.height())
        
        self.setGeometry(start_rect)
        
        self.show_animation.setStartValue(start_rect)
        self.show_animation.setEndValue(end_rect)
        self.show_animation.start()
        
        # Start auto-hide timer
        if hasattr(self, 'hide_timer'):
            self.hide_timer.start(self.duration)
    
    def hide_animated(self):
        """Hide toast with slide-out animation"""
        if hasattr(self, 'hide_timer'):
            self.hide_timer.stop()
        
        # End position (slide to right)
        start_rect = self.geometry()
        end_rect = QRect(self.x() + 100, self.y(), self.width(), self.height())
        
        self.hide_animation.setStartValue(start_rect)
        self.hide_animation.setEndValue(end_rect)
        self.hide_animation.start()
    
    def hide_immediately(self):
        """Hide toast immediately without animation"""
        if hasattr(self, 'hide_timer'):
            self.hide_timer.stop()
        self.hide()
        self.toast_closed.emit()
    
    def animate_to_position(self, target_pos: QPoint):
        """Animate toast to new position"""
        self.move_animation.setStartValue(self.pos())
        self.move_animation.setEndValue(target_pos)
        self.move_animation.start()
    
    def is_expired(self) -> bool:
        """Check if toast is expired"""
        if self.duration <= 0:
            return False
        return time.time() - self.creation_time > (self.duration / 1000)
    
    def mousePressEvent(self, event):
        """Handle click to dismiss"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.hide_animated()
        super().mousePressEvent(event)

# Global toast manager instance
_toast_manager = ToastManager()

def show_toast(parent_widget: QWidget, message: str, toast_type: ToastType = ToastType.INFO,
               duration: int = 3000, data: Optional[Dict[str, Any]] = None) -> ToastNotification:
    """Convenience function to show a toast notification"""
    return _toast_manager.show_toast(parent_widget, message, toast_type, duration, data)

def show_download_complete_toast(parent_widget: QWidget, title: str, file_path: str,
                               duration: int = 4000) -> ToastNotification:
    """Show a download completion toast"""
    import os
    filename = os.path.basename(file_path) if file_path else "Unknown"
    message = f"Download Complete\n{title[:40]}{'...' if len(title) > 40 else ''}"
    
    return show_toast(
        parent_widget, 
        message, 
        ToastType.DOWNLOAD_COMPLETE,
        duration,
        {'title': title, 'file_path': file_path, 'filename': filename}
    )

def show_download_started_toast(parent_widget: QWidget, title: str, 
                              duration: int = 2000) -> ToastNotification:
    """Show a download started toast"""
    message = f"Download Started\n{title[:40]}{'...' if len(title) > 40 else ''}"
    
    return show_toast(
        parent_widget,
        message,
        ToastType.DOWNLOAD_STARTED, 
        duration,
        {'title': title}
    ) 