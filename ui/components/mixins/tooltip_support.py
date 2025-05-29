"""
Tooltip Support Mixin

Provides standardized tooltip formatting and display for UI components.
Extracted from downloaded_videos_tab.py and video_info_tab.py format_tooltip_text methods.
"""

import re
from typing import Optional, Tuple
from PyQt6.QtWidgets import QToolTip, QWidget
from PyQt6.QtCore import QPoint
from ..common.events import EventEmitter

class TooltipSupport(EventEmitter):
    """Mixin providing tooltip formatting and display"""
    
    def __init__(self, component_name: str):
        EventEmitter.__init__(self, component_name)
        self._tooltip_enabled = True
        self._max_tooltip_length = 500
    
    def format_tooltip_text(self, text: str) -> str:
        """Format tooltip text with line breaks for better readability"""
        if not text:
            return ""
        
        # Limit text length
        if len(text) > self._max_tooltip_length:
            text = text[:self._max_tooltip_length] + "..."
        
        # Add line breaks after periods, exclamation marks, question marks followed by a space
        formatted_text = re.sub(r'([.!?]) ', r'\1\n', text)
        
        # Add line breaks after commas followed by a space (but not too many)
        formatted_text = re.sub(r'([,]) ', r'\1\n', formatted_text)
        
        # Handle hashtags - one hashtag per line
        formatted_text = re.sub(r' (#[^\s#]+)', r'\n\1', formatted_text)
        
        # Clean up multiple consecutive newlines
        formatted_text = re.sub(r'\n\n+', '\n\n', formatted_text)
        
        return formatted_text.strip()
    
    def show_tooltip(self, text: str, position: Optional[Tuple[int, int]] = None, 
                     widget: Optional[QWidget] = None):
        """Show tooltip at specified position or widget"""
        if not self._tooltip_enabled or not text:
            return
            
        formatted_text = self.format_tooltip_text(text)
        
        if position:
            QToolTip.showText(QPoint(position[0], position[1]), formatted_text)
        elif widget:
            QToolTip.showText(widget.mapToGlobal(QPoint(0, 0)), formatted_text)
        elif hasattr(self, 'mapToGlobal'):
            # If this mixin is used on a QWidget
            QToolTip.showText(self.mapToGlobal(QPoint(0, 0)), formatted_text)
    
    def show_full_text_tooltip(self, row: int, column: int, table_widget=None):
        """Show full text tooltip for table cells - extracted from original implementations"""
        if not self._tooltip_enabled:
            return
            
        # Get the widget to work with
        widget = table_widget or getattr(self, 'downloads_table', None) or getattr(self, 'video_table', None)
        if not widget:
            return
            
        try:
            item = widget.item(row, column)
            if not item:
                return
                
            text = item.text()
            if not text or len(text) <= 50:  # Don't show tooltip for short text
                return
                
            # Get cell position
            cell_rect = widget.visualItemRect(item)
            global_pos = widget.mapToGlobal(cell_rect.center())
            
            self.show_tooltip(text, (global_pos.x(), global_pos.y()))
            
        except Exception as e:
            print(f"Error showing tooltip: {e}")
    
    def hide_tooltip(self):
        """Hide any currently displayed tooltip"""
        QToolTip.hideText()
    
    def set_tooltip_enabled(self, enabled: bool):
        """Enable or disable tooltips for this component"""
        self._tooltip_enabled = enabled
    
    def is_tooltip_enabled(self) -> bool:
        """Check if tooltips are enabled"""
        return self._tooltip_enabled
    
    def set_max_tooltip_length(self, length: int):
        """Set maximum tooltip text length"""
        self._max_tooltip_length = max(100, length)  # Minimum 100 characters
    
    def get_max_tooltip_length(self) -> int:
        """Get maximum tooltip text length"""
        return self._max_tooltip_length
    
    def create_rich_tooltip(self, title: str, content: str, 
                          additional_info: Optional[str] = None) -> str:
        """Create a rich tooltip with title and content"""
        tooltip_parts = []
        
        if title:
            tooltip_parts.append(f"<b>{title}</b>")
        
        if content:
            formatted_content = self.format_tooltip_text(content)
            tooltip_parts.append(formatted_content)
        
        if additional_info:
            tooltip_parts.append(f"<i>{additional_info}</i>")
        
        return "<br>".join(tooltip_parts)
    
    def setup_table_tooltips(self, table_widget):
        """Set up tooltip handling for a table widget"""
        if not table_widget:
            return
            
        # Enable mouse tracking for tooltip events
        table_widget.setMouseTracking(True)
        
        # You can connect mouse events here if needed
        # table_widget.cellEntered.connect(self._on_cell_entered)
    
    def _on_cell_entered(self, row: int, column: int):
        """Handle cell entered event for automatic tooltips"""
        self.show_full_text_tooltip(row, column) 