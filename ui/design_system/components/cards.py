"""
Card-Based Layout Components

Modern card system for transforming flat UI into contemporary card-based layouts
with proper elevation, shadows, visual grouping, and content hierarchy.
"""

import enum
from typing import Dict, List, Optional, Union, Any
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from ..styles.style_manager import StyleManager


class ElevationLevel(enum.Enum):
    """
    Material Design inspired elevation levels for cards
    
    Each level corresponds to different shadow depths and visual prominence.
    """
    FLAT = 0          # No shadow - flush with background
    SUBTLE = 1        # Very light shadow - for content grouping
    RAISED = 2        # Default card elevation - most common
    ELEVATED = 3      # Prominent cards - important content
    FLOATING = 4      # Modal/overlay cards - highest prominence
    

class CardComponent(QFrame):
    """
    Modern card component with elevation, rounded corners, and visual hierarchy
    
    Features:
    - Material Design elevation levels
    - Theme-aware styling using design tokens
    - Smooth hover interactions
    - Customizable content padding and margins
    - Built-in content hierarchy support
    """
    
    # Signals
    clicked = pyqtSignal()
    hovered = pyqtSignal(bool)  # True when entering, False when leaving
    
    def __init__(self, 
                 elevation: ElevationLevel = ElevationLevel.RAISED,
                 clickable: bool = False,
                 hover_elevation: Optional[ElevationLevel] = None,
                 title: Optional[str] = None,
                 parent: Optional[QWidget] = None):
        """
        Initialize a modern card component
        
        Args:
            elevation: Visual elevation level for the card
            clickable: Whether the card responds to clicks
            hover_elevation: Elevation level when hovered (if different)
            title: Optional title for the card
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.elevation = elevation
        self.hover_elevation = hover_elevation or elevation
        self.clickable = clickable
        self.style_manager = StyleManager()
        
        self._is_hovered = False
        self._setup_layout()
        self._setup_animations()
        self._apply_card_styling()
        
        if title:
            self.set_title(title)
    
    def _setup_layout(self):
        """Set up the card's internal layout structure"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Title area (optional)
        self.title_widget = None
        
        # Content area
        self.content_frame = QFrame()
        self.content_frame.setObjectName("card_content")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(16, 16, 16, 16)  # Using spacing tokens
        self.content_layout.setSpacing(12)
        
        self.main_layout.addWidget(self.content_frame)
    
    def _setup_animations(self):
        """Set up smooth animations for elevation changes"""
        self.elevation_animation = QPropertyAnimation(self, b"geometry")
        self.elevation_animation.setDuration(200)  # 200ms for smooth transition
        self.elevation_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def _apply_card_styling(self):
        """Apply theme-aware styling using design tokens"""
        # Get design token values
        bg_color = self.style_manager.get_token_value('color-background-primary', '#FFFFFF')
        border_color = self.style_manager.get_token_value('color-border-default', '#E2E8F0')
        border_radius = self.style_manager.get_token_value('sizing-border-radius-md', '8px')
        
        # Build elevation-specific styles
        shadow_styles = self._get_elevation_styles(self.elevation)
        
        card_styles = f"""
        CardComponent {{
            background-color: {bg_color};
            border: 1px solid {border_color};
            border-radius: {border_radius};
            {shadow_styles}
        }}
        
        CardComponent:hover {{
            {self._get_elevation_styles(self.hover_elevation)}
        }}
        
        #card_content {{
            background-color: transparent;
            border: none;
        }}
        """
        
        self.setStyleSheet(card_styles)
    
    def _get_elevation_styles(self, elevation: ElevationLevel) -> str:
        """
        Generate CSS shadow styles for different elevation levels
        
        Based on Material Design elevation guidelines adapted for desktop UI
        """
        elevation_shadows = {
            ElevationLevel.FLAT: "",
            ElevationLevel.SUBTLE: """
                box-shadow: 0px 1px 2px rgba(0, 0, 0, 0.05);
            """,
            ElevationLevel.RAISED: """
                box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.1),
                           0px 1px 2px rgba(0, 0, 0, 0.06);
            """,
            ElevationLevel.ELEVATED: """
                box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.12),
                           0px 2px 4px rgba(0, 0, 0, 0.08);
            """,
            ElevationLevel.FLOATING: """
                box-shadow: 0px 8px 16px rgba(0, 0, 0, 0.15),
                           0px 4px 8px rgba(0, 0, 0, 0.10);
            """
        }
        
        return elevation_shadows.get(elevation, elevation_shadows[ElevationLevel.RAISED])
    
    def set_title(self, title: str):
        """Add or update card title"""
        if not self.title_widget:
            self.title_widget = QLabel()
            self.title_widget.setObjectName("card_title")
            
            # Apply title styling using design tokens
            title_color = self.style_manager.get_token_value('color-text-primary', '#0F172A')
            title_size = self.style_manager.get_token_value('typography-heading-h4-size', '18px')
            title_weight = self.style_manager.get_token_value('typography-heading-weight', '600')
            
            title_styles = f"""
            #card_title {{
                color: {title_color};
                font-size: {title_size};
                font-weight: {title_weight};
                padding: 16px 16px 8px 16px;
                background-color: transparent;
                border: none;
            }}
            """
            self.title_widget.setStyleSheet(title_styles)
            
            # Insert title at the top
            self.main_layout.insertWidget(0, self.title_widget)
        
        self.title_widget.setText(title)
    
    def add_content(self, widget: QWidget):
        """Add content widget to the card"""
        self.content_layout.addWidget(widget)
    
    def add_content_layout(self, layout):
        """Add a layout to the card content area"""
        self.content_layout.addLayout(layout)
    
    def set_elevation(self, elevation: ElevationLevel):
        """Change card elevation level"""
        self.elevation = elevation
        self._apply_card_styling()
    
    def enterEvent(self, event):
        """Handle mouse enter for hover effects"""
        if self.clickable:
            self._is_hovered = True
            self.hovered.emit(True)
            self._apply_card_styling()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave for hover effects"""
        if self.clickable:
            self._is_hovered = False
            self.hovered.emit(False)
            self._apply_card_styling()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle card clicks"""
        if self.clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class CardContainer(QScrollArea):
    """
    Container for managing multiple cards with automatic layout
    
    Provides:
    - Automatic card grid/list layouts
    - Scroll support for large card collections
    - Responsive card sizing
    - Consistent spacing using design tokens
    """
    
    def __init__(self, layout_type: str = "grid", parent: Optional[QWidget] = None):
        """
        Initialize card container
        
        Args:
            layout_type: "grid" or "list" layout style
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.layout_type = layout_type
        self.style_manager = StyleManager()
        self.cards: List[CardComponent] = []
        
        self._setup_container()
        self._apply_container_styling()
    
    def _setup_container(self):
        """Set up the scrollable container with proper layout"""
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create scrollable content widget
        self.content_widget = QWidget()
        self.setWidget(self.content_widget)
        
        # Choose layout based on type
        if self.layout_type == "grid":
            # Grid layout will be implemented as flow layout
            self.content_layout = QVBoxLayout(self.content_widget)
        else:
            # List layout
            self.content_layout = QVBoxLayout(self.content_widget)
        
        # Apply spacing using design tokens
        spacing = int(self.style_manager.get_token_value('spacing-md', '16px').replace('px', ''))
        self.content_layout.setSpacing(spacing)
        self.content_layout.setContentsMargins(spacing, spacing, spacing, spacing)
    
    def _apply_container_styling(self):
        """Apply theme-aware styling to the container"""
        bg_color = self.style_manager.get_token_value('color-background-secondary', '#F8FAFC')
        
        container_styles = f"""
        CardContainer {{
            background-color: {bg_color};
            border: none;
        }}
        
        CardContainer QScrollBar:vertical {{
            background-color: transparent;
            width: 8px;
            border-radius: 4px;
        }}
        
        CardContainer QScrollBar::handle:vertical {{
            background-color: rgba(0, 0, 0, 0.2);
            border-radius: 4px;
            min-height: 20px;
        }}
        
        CardContainer QScrollBar::handle:vertical:hover {{
            background-color: rgba(0, 0, 0, 0.3);
        }}
        """
        
        self.setStyleSheet(container_styles)
    
    def add_card(self, card: CardComponent):
        """Add a card to the container"""
        self.cards.append(card)
        self.content_layout.addWidget(card)
    
    def remove_card(self, card: CardComponent):
        """Remove a card from the container"""
        if card in self.cards:
            self.cards.remove(card)
            self.content_layout.removeWidget(card)
            card.deleteLater()
    
    def clear_cards(self):
        """Remove all cards from the container"""
        for card in self.cards[:]:  # Create copy to avoid modification during iteration
            self.remove_card(card)
    
    def get_card_count(self) -> int:
        """Get the number of cards in the container"""
        return len(self.cards)


class CardLayout:
    """
    Utility class for creating common card-based layout patterns
    
    Provides factory methods for:
    - Video info cards
    - Download progress cards
    - Settings/configuration cards
    - Status/notification cards
    """
    
    @staticmethod
    def create_video_info_card(title: str, 
                              url: str, 
                              duration: Optional[str] = None,
                              thumbnail_path: Optional[str] = None) -> CardComponent:
        """
        Create a video information card
        
        Args:
            title: Video title
            url: Video URL
            duration: Video duration string
            thumbnail_path: Path to video thumbnail
            
        Returns:
            Configured CardComponent for video info
        """
        card = CardComponent(
            elevation=ElevationLevel.RAISED,
            clickable=True,
            hover_elevation=ElevationLevel.ELEVATED,
            title="Video Information"
        )
        
        # Video details layout
        details_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setObjectName("video_title")
        details_layout.addWidget(title_label)
        
        # URL
        url_label = QLabel(f"URL: {url}")
        url_label.setObjectName("video_url")
        details_layout.addWidget(url_label)
        
        # Duration (if available)
        if duration:
            duration_label = QLabel(f"Duration: {duration}")
            duration_label.setObjectName("video_duration")
            details_layout.addWidget(duration_label)
        
        card.add_content_layout(details_layout)
        
        return card
    
    @staticmethod
    def create_download_progress_card(filename: str, 
                                    progress: float,
                                    status: str = "downloading") -> CardComponent:
        """
        Create a download progress card
        
        Args:
            filename: Name of file being downloaded
            progress: Download progress (0.0 to 1.0)
            status: Download status string
            
        Returns:
            Configured CardComponent for download progress
        """
        card = CardComponent(
            elevation=ElevationLevel.RAISED,
            title="Download Progress"
        )
        
        # Progress details
        progress_layout = QVBoxLayout()
        
        # Filename
        filename_label = QLabel(filename)
        filename_label.setObjectName("download_filename")
        progress_layout.addWidget(filename_label)
        
        # Status and progress
        status_label = QLabel(f"Status: {status}")
        progress_label = QLabel(f"Progress: {progress * 100:.1f}%")
        
        progress_layout.addWidget(status_label)
        progress_layout.addWidget(progress_label)
        
        card.add_content_layout(progress_layout)
        
        return card
    
    @staticmethod
    def create_settings_card(title: str, description: str) -> CardComponent:
        """
        Create a settings/configuration card
        
        Args:
            title: Settings section title
            description: Settings description
            
        Returns:
            Configured CardComponent for settings
        """
        card = CardComponent(
            elevation=ElevationLevel.SUBTLE,
            clickable=True,
            hover_elevation=ElevationLevel.RAISED
        )
        
        # Settings layout
        settings_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel(title)
        title_label.setObjectName("settings_title")
        settings_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setObjectName("settings_description")
        settings_layout.addWidget(desc_label)
        
        card.add_content_layout(settings_layout)
        
        return card 