"""
Modern Icon System

Scalable icon components with SVG support, theme integration,
and consistent sizing. Provides Feather/Lucide style icons
for professional visual communication.
"""

import enum
from typing import Dict, Optional, Tuple, Union
from PyQt6.QtWidgets import QLabel, QWidget, QPushButton
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon, QFont, QFont
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtSvg import QSvgRenderer
from ..styles.style_manager import StyleManager


class IconSize(enum.Enum):
    """Standard icon sizes following design system scale"""
    XS = 12       # Extra small - for inline text
    SM = 16       # Small - for buttons, form elements
    MD = 20       # Medium - default size
    LG = 24       # Large - for headers, prominent actions
    XL = 32       # Extra large - for hero sections
    XXL = 48      # Super large - for empty states, illustrations


class IconStyle(enum.Enum):
    """Icon style variants"""
    OUTLINE = "outline"        # Stroke-based icons (default)
    FILLED = "filled"          # Filled icons for active states
    DUOTONE = "duotone"        # Two-tone icons
    MINIMAL = "minimal"        # Ultra-minimal icons


class IconComponent(QLabel):
    """
    Modern icon component with SVG support and theme integration
    
    Features:
    - Scalable SVG icons
    - Theme-aware coloring
    - Multiple sizes and styles
    - Interactive states (hover, active)
    - Accessibility support
    """
    
    clicked = pyqtSignal()
    
    def __init__(self, 
                 icon_name: str,
                 size: IconSize = IconSize.MD,
                 style: IconStyle = IconStyle.OUTLINE,
                 color: Optional[str] = None,
                 clickable: bool = False,
                 parent: Optional[QWidget] = None):
        """
        Initialize icon component
        
        Args:
            icon_name: Name of the icon (e.g., 'download', 'play', 'settings')
            size: Icon size from IconSize enum
            style: Icon style variant
            color: Custom color (hex) or None for theme default
            clickable: Whether icon responds to clicks
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.icon_name = icon_name
        self.size = size
        self.style = style
        self.custom_color = color
        self.clickable = clickable
        self.style_manager = StyleManager()
        
        self._is_hovered = False
        self._setup_icon()
        self._apply_styling()
    
    def _setup_icon(self):
        """Set up the icon display"""
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(QSize(self.size.value, self.size.value))
        
        # Enable mouse tracking for hover effects if clickable
        if self.clickable:
            self.setMouseTracking(True)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Load and display icon
        self._load_icon()
    
    def _load_icon(self):
        """Load icon based on name, style, and theme"""
        # Get theme-appropriate color
        icon_color = self.custom_color or self._get_theme_icon_color()
        
        # Generate SVG content for the icon
        svg_content = self._generate_icon_svg(self.icon_name, icon_color)
        
        if svg_content:
            # Create pixmap from SVG
            pixmap = self._svg_to_pixmap(svg_content, self.size.value)
            self.setPixmap(pixmap)
        else:
            # Fallback to text representation
            self._create_fallback_icon()
    
    def _get_theme_icon_color(self) -> str:
        """Get appropriate icon color from current theme"""
        if self._is_hovered and self.clickable:
            return self.style_manager.get_token_value('color-text-primary', '#0F172A')
        else:
            return self.style_manager.get_token_value('color-text-secondary', '#64748B')
    
    def _generate_icon_svg(self, icon_name: str, color: str) -> Optional[str]:
        """
        Generate SVG content for common icons
        
        This is a simplified icon library. In production, you would
        typically use a proper icon library like Feather Icons.
        """
        icons = {
            # Media & Playback
            'play': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <polygon points="5,3 19,12 5,21" fill="{color if self.style == IconStyle.FILLED else 'none'}"/>
                </svg>
            ''',
            'pause': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <rect x="6" y="4" width="4" height="16" fill="{color if self.style == IconStyle.FILLED else 'none'}"/>
                    <rect x="14" y="4" width="4" height="16" fill="{color if self.style == IconStyle.FILLED else 'none'}"/>
                </svg>
            ''',
            'stop': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <rect x="5" y="5" width="14" height="14" rx="2" fill="{color if self.style == IconStyle.FILLED else 'none'}"/>
                </svg>
            ''',
            
            # Download & Transfer
            'download': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7,10 12,15 17,10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
            ''',
            'upload': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17,8 12,3 7,8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
            ''',
            
            # Navigation & Actions
            'settings': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <circle cx="12" cy="12" r="3"/>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1 1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                </svg>
            ''',
            'menu': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <line x1="3" y1="6" x2="21" y2="6"/>
                    <line x1="3" y1="12" x2="21" y2="12"/>
                    <line x1="3" y1="18" x2="21" y2="18"/>
                </svg>
            ''',
            'close': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
            ''',
            
            # Status & Feedback
            'check': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <polyline points="20,6 9,17 4,12"/>
                </svg>
            ''',
            'error': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="15" y1="9" x2="9" y2="15"/>
                    <line x1="9" y1="9" x2="15" y2="15"/>
                </svg>
            ''',
            'warning': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                    <line x1="12" y1="9" x2="12" y2="13"/>
                    <circle cx="12" cy="17" r="1"/>
                </svg>
            ''',
            'info': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="16" x2="12" y2="12"/>
                    <circle cx="12" cy="8" r="1"/>
                </svg>
            ''',
            
            # Platforms
            'youtube': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z"/>
                    <polygon points="9.75,15.02 15.5,11.75 9.75,8.48" fill="{color if self.style == IconStyle.FILLED else 'none'}"/>
                </svg>
            ''',
            'tiktok': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <path d="M9 12a4 4 0 1 0 4 4V4a5 5 0 0 0 5 5" fill="{color if self.style == IconStyle.FILLED else 'none'}"/>
                </svg>
            ''',
            
            # File & Folder
            'folder': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" fill="{color if self.style == IconStyle.FILLED else 'none'}"/>
                </svg>
            ''',
            'file': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2Z" fill="{color if self.style == IconStyle.FILLED else 'none'}"/>
                    <polyline points="14,2 14,8 20,8"/>
                </svg>
            ''',
            
            # Theme
            'sun': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <circle cx="12" cy="12" r="5" fill="{color if self.style == IconStyle.FILLED else 'none'}"/>
                    <line x1="12" y1="1" x2="12" y2="3"/>
                    <line x1="12" y1="21" x2="12" y2="23"/>
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                    <line x1="1" y1="12" x2="3" y2="12"/>
                    <line x1="21" y1="12" x2="23" y2="12"/>
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                </svg>
            ''',
            'moon': f'''
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" fill="{color if self.style == IconStyle.FILLED else 'none'}"/>
                </svg>
            ''',
        }
        
        return icons.get(icon_name)
    
    def _svg_to_pixmap(self, svg_content: str, size: int) -> QPixmap:
        """Convert SVG content to QPixmap"""
        renderer = QSvgRenderer()
        renderer.load(svg_content.encode('utf-8'))
        
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        return pixmap
    
    def _create_fallback_icon(self):
        """Create text-based fallback icon"""
        # Use first letter of icon name as fallback
        fallback_text = self.icon_name[0].upper() if self.icon_name else "?"
        
        self.setText(fallback_text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Style as circular icon
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {self.style_manager.get_token_value('color-background-secondary', '#f0f0f0')};
                color: {self._get_theme_icon_color()};
                border-radius: {self.size.value // 2}px;
                font-weight: bold;
                font-size: {max(8, self.size.value // 2)}px;
            }}
        """)
    
    def _apply_styling(self):
        """Apply component styling"""
        if self.clickable:
            self.setProperty("clickable", True)
    
    def set_color(self, color: str):
        """Update icon color"""
        self.custom_color = color
        self._load_icon()
    
    def set_size(self, size: IconSize):
        """Update icon size"""
        self.size = size
        self.setFixedSize(QSize(size.value, size.value))
        self._load_icon()
    
    def set_style(self, style: IconStyle):
        """Update icon style"""
        self.style = style
        self._load_icon()
    
    def enterEvent(self, event):
        """Handle mouse enter for hover effects"""
        if self.clickable:
            self._is_hovered = True
            self._load_icon()  # Reload with hover color
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave"""
        if self.clickable:
            self._is_hovered = False
            self._load_icon()  # Reload with normal color
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse clicks"""
        if self.clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class IconButton(QPushButton):
    """
    Button component with integrated icon support
    
    Combines modern icons with standard button functionality
    """
    
    def __init__(self, 
                 icon_name: str,
                 text: str = "",
                 icon_size: IconSize = IconSize.SM,
                 icon_position: str = "left",
                 parent: Optional[QWidget] = None):
        """
        Initialize icon button
        
        Args:
            icon_name: Name of icon to display
            text: Button text (optional)
            icon_size: Size of icon
            icon_position: Icon position ("left", "right", "top", "bottom")
            parent: Parent widget
        """
        super().__init__(text, parent)
        
        self.icon_name = icon_name
        self.icon_size = icon_size
        self.icon_position = icon_position
        self.style_manager = StyleManager()
        
        self._setup_icon_button()
    
    def _setup_icon_button(self):
        """Set up the icon button with proper layout"""
        # Create icon component
        icon = IconComponent(
            self.icon_name,
            size=self.icon_size,
            clickable=False  # Button handles clicks
        )
        
        # Convert icon to QIcon for button
        qicon = QIcon(icon.pixmap())
        self.setIcon(qicon)
        self.setIconSize(QSize(self.icon_size.value, self.icon_size.value))
        
        # Apply modern button styling
        self._apply_modern_styling()
    
    def _apply_modern_styling(self):
        """Apply modern styling to icon button"""
        button_styles = f"""
            IconButton {{
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
                background-color: {self.style_manager.get_token_value('color-button-primary-background', '#3B82F6')};
                color: {self.style_manager.get_token_value('color-button-primary-text', '#FFFFFF')};
            }}
            
            IconButton:hover {{
                background-color: {self.style_manager.get_token_value('color-button-primary-background-hover', '#2563EB')};
                transform: translateY(-1px);
            }}
            
            IconButton:pressed {{
                transform: translateY(0px);
            }}
        """
        
        self.setStyleSheet(button_styles)


def create_icon(icon_name: str, 
               size: IconSize = IconSize.MD,
               style: IconStyle = IconStyle.OUTLINE,
               color: Optional[str] = None,
               clickable: bool = False) -> IconComponent:
    """
    Factory function to create icon components
    
    Args:
        icon_name: Name of the icon
        size: Icon size
        style: Icon style variant
        color: Custom color (optional)
        clickable: Whether icon is clickable
        
    Returns:
        Configured IconComponent
    """
    return IconComponent(icon_name, size, style, color, clickable)


def create_icon_button(icon_name: str,
                      text: str = "",
                      icon_size: IconSize = IconSize.SM) -> IconButton:
    """
    Factory function to create icon buttons
    
    Args:
        icon_name: Name of the icon
        text: Button text
        icon_size: Size of the icon
        
    Returns:
        Configured IconButton
    """
    return IconButton(icon_name, text, icon_size) 