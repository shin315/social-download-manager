"""
Lazy Video Table Delegate for Custom Widget Rendering

Custom QStyledItemDelegate providing:
- Checkbox widgets for selection column
- Action buttons for operations (Open, Delete)
- Progress indicators for loading states
- Thumbnail integration with caching system
- Optimized rendering for large datasets

Part of Task 15.1 - Lazy Loading Implementation
"""

from typing import Optional, Dict, Any
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal, QModelIndex
from PyQt6.QtGui import QPainter, QPixmap, QIcon, QPalette, QFont
from PyQt6.QtWidgets import (
    QStyledItemDelegate, QWidget, QCheckBox, QPushButton, 
    QHBoxLayout, QStyleOptionButton, QApplication, QStyle,
    QStyleOptionViewItem, QVBoxLayout, QLabel
)

# from ui.components.common.performance_monitor import PerformanceMonitor


class VideoSelectionDelegate(QStyledItemDelegate):
    """Delegate for selection checkbox column"""
    
    selection_changed = pyqtSignal(int, bool)  # row, checked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # self.performance_monitor = PerformanceMonitor()
        
    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, 
                     index: QModelIndex) -> QWidget:
        """Create checkbox widget"""
        checkbox = QCheckBox(parent)
        checkbox.setChecked(False)
        return checkbox
    
    def setEditorData(self, editor: QWidget, index: QModelIndex):
        """Set checkbox state from model"""
        if isinstance(editor, QCheckBox):
            # Get selection state from model (stored in UserRole+1)
            checked = index.data(Qt.ItemDataRole.UserRole + 1) or False
            editor.setChecked(checked)
    
    def setModelData(self, editor: QWidget, model, index: QModelIndex):
        """Update model with checkbox state"""
        if isinstance(editor, QCheckBox):
            checked = editor.isChecked()
            # Store selection state in model
            model.setData(index, checked, Qt.ItemDataRole.UserRole + 1)
            self.selection_changed.emit(index.row(), checked)
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Paint checkbox"""
        # Get checkbox state
        checked = index.data(Qt.ItemDataRole.UserRole + 1) or False
        
        # Create style option for checkbox
        checkbox_option = QStyleOptionButton()
        checkbox_option.rect = option.rect
        checkbox_option.state = QStyle.StateFlag.State_Enabled
        
        if checked:
            checkbox_option.state |= QStyle.StateFlag.State_On
        else:
            checkbox_option.state |= QStyle.StateFlag.State_Off
        
        # Paint checkbox
        QApplication.style().drawControl(
            QStyle.ControlElement.CE_CheckBox, checkbox_option, painter
        )
    
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return size hint for checkbox"""
        return QSize(50, 30)


class VideoActionsDelegate(QStyledItemDelegate):
    """Delegate for action buttons column"""
    
    open_requested = pyqtSignal(int)    # row
    delete_requested = pyqtSignal(int)  # row
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # self.performance_monitor = PerformanceMonitor()
        self._cached_widgets: Dict[int, QWidget] = {}
        
    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, 
                     index: QModelIndex) -> QWidget:
        """Create action buttons widget"""
        widget = QWidget(parent)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        
        # Open button
        open_btn = QPushButton("Open")
        open_btn.setMinimumWidth(60)
        open_btn.setMaximumHeight(25)
        open_btn.clicked.connect(lambda: self.open_requested.emit(index.row()))
        layout.addWidget(open_btn)
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setMinimumWidth(60)
        delete_btn.setMaximumHeight(25)
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(index.row()))
        layout.addWidget(delete_btn)
        
        widget.setLayout(layout)
        return widget
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Paint action buttons"""
        # Get video data to check file existence
        video_data = index.data(Qt.ItemDataRole.UserRole)
        
        # Create temporary widget for painting
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        
        # Style based on video status
        open_enabled = True
        delete_enabled = True
        
        if video_data:
            status = video_data.get('status', '')
            if status.lower() != 'successful':
                open_enabled = False
        
        # Paint button representations
        button_rect = QRect(option.rect.x() + 2, option.rect.y() + 2, 60, 25)
        
        # Open button
        painter.fillRect(button_rect, Qt.GlobalColor.lightGray if open_enabled else Qt.GlobalColor.gray)
        painter.drawText(button_rect, Qt.AlignmentFlag.AlignCenter, "Open")
        
        # Delete button
        button_rect.translate(64, 0)
        painter.fillRect(button_rect, Qt.GlobalColor.lightGray if delete_enabled else Qt.GlobalColor.gray)
        painter.drawText(button_rect, Qt.AlignmentFlag.AlignCenter, "Delete")
    
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return size hint for action buttons"""
        return QSize(130, 30)


class VideoThumbnailDelegate(QStyledItemDelegate):
    """Delegate for thumbnail rendering with caching"""
    
    def __init__(self, thumbnail_cache=None, parent=None):
        super().__init__(parent)
        self.thumbnail_cache = thumbnail_cache
        # self.performance_monitor = PerformanceMonitor()
        
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Paint thumbnail if available"""
        video_data = index.data(Qt.ItemDataRole.UserRole)
        
        if not video_data:
            # Paint placeholder
            painter.fillRect(option.rect, Qt.GlobalColor.lightGray)
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "Loading...")
            return
        
        # Try to get thumbnail from cache
        video_id = video_data.get('id')
        thumbnail = None
        
        if self.thumbnail_cache and video_id:
            thumbnail = self.thumbnail_cache.get_thumbnail(video_id)
        
        if thumbnail and not thumbnail.isNull():
            # Scale thumbnail to fit
            scaled_pixmap = thumbnail.scaled(
                option.rect.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Center the pixmap
            x = option.rect.x() + (option.rect.width() - scaled_pixmap.width()) // 2
            y = option.rect.y() + (option.rect.height() - scaled_pixmap.height()) // 2
            
            painter.drawPixmap(x, y, scaled_pixmap)
        else:
            # Paint placeholder with video info
            painter.fillRect(option.rect, Qt.GlobalColor.lightGray)
            
            # Draw text info
            title = video_data.get('title', 'Unknown')
            if len(title) > 20:
                title = title[:17] + "..."
            
            painter.drawText(
                option.rect, 
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter, 
                title
            )
    
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return size hint for thumbnail"""
        return QSize(80, 60)


class VideoProgressDelegate(QStyledItemDelegate):
    """Delegate for progress indicators during loading"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # self.performance_monitor = PerformanceMonitor()
        
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Paint progress indicator"""
        # Get loading state from model
        is_loading = index.data(Qt.ItemDataRole.UserRole + 2) or False
        
        if is_loading:
            # Paint loading indicator
            painter.fillRect(option.rect, Qt.GlobalColor.yellow)
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, "Loading...")
        else:
            # Paint normal cell content
            super().paint(painter, option, index)
    
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return standard size hint"""
        return QSize(100, 30)


class VideoStatusDelegate(QStyledItemDelegate):
    """Delegate for status column with color coding"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # self.performance_monitor = PerformanceMonitor()
        
        # Status color mapping
        self.status_colors = {
            'successful': Qt.GlobalColor.green,
            'failed': Qt.GlobalColor.red,
            'pending': Qt.GlobalColor.yellow,
            'downloading': Qt.GlobalColor.blue,
            'processing': Qt.GlobalColor.cyan
        }
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Paint status with color coding"""
        status_text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        status_lower = status_text.lower()
        
        # Get background color based on status
        bg_color = self.status_colors.get(status_lower, Qt.GlobalColor.lightGray)
        
        # Paint background
        painter.fillRect(option.rect, bg_color)
        
        # Paint text with contrasting color
        text_color = Qt.GlobalColor.white if bg_color in [Qt.GlobalColor.red, Qt.GlobalColor.blue] else Qt.GlobalColor.black
        painter.setPen(text_color)
        
        # Set font weight for better visibility
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        
        painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, status_text)
    
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return size hint for status"""
        return QSize(90, 30)


class VideoDateDelegate(QStyledItemDelegate):
    """Delegate for date column with multi-line format"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # self.performance_monitor = PerformanceMonitor()
        
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Paint date in multi-line format"""
        date_text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        
        if '\n' in date_text:
            # Split date and time
            lines = date_text.split('\n')
            
            # Calculate line positions
            line_height = option.rect.height() // len(lines)
            
            for i, line in enumerate(lines):
                line_rect = QRect(
                    option.rect.x(),
                    option.rect.y() + i * line_height,
                    option.rect.width(),
                    line_height
                )
                painter.drawText(line_rect, Qt.AlignmentFlag.AlignCenter, line)
        else:
            # Single line date
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, date_text)
    
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return size hint for date (taller for multi-line)"""
        return QSize(120, 35) 