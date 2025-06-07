"""
Quality Filter Widget

Advanced quality tier selector with icon indicators and filtering options.
Part of Task 13.3: Implement Date Range and Quality Filters
"""

from typing import List, Dict, Set, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QButtonGroup, QGroupBox, QScrollArea, QFrame,
    QSizePolicy, QSpacerItem, QToolTip
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPainter, QColor, QBrush

from ..mixins.language_support import LanguageSupport
from ..common.models import FilterConfig


class QualityTierButton(QCheckBox):
    """Custom checkbox button for quality tiers with icons"""
    
    def __init__(self, quality_name, icon_text, color, parent=None):
        super().__init__(parent)
        
        self.quality_name = quality_name
        self.icon_text = icon_text
        self.color = color
        self.video_count = 0
        
        self._setup_button()
    
    def _setup_button(self):
        """Setup button appearance"""
        self.setText(f"{self.icon_text} {self.quality_name}")
        self.setMinimumHeight(35)
        self.setStyleSheet(f"""
            QCheckBox {{
                font-size: 12px;
                padding: 5px 10px;
                border: 2px solid {self.color};
                border-radius: 8px;
                background-color: white;
                margin: 2px;
            }}
            QCheckBox:hover {{
                background-color: {self.color}22;
                border-color: {self.color};
            }}
            QCheckBox:checked {{
                background-color: {self.color}44;
                border-color: {self.color};
                font-weight: bold;
            }}
            QCheckBox::indicator {{
                width: 0px;
                height: 0px;
            }}
        """)
    
    def set_video_count(self, count):
        """Update video count for this quality"""
        self.video_count = count
        self.setText(f"{self.icon_text} {self.quality_name} ({count})")
        self.setEnabled(count > 0)
        
        # Update tooltip
        if count > 0:
            self.setToolTip(f"{count} videos available in {self.quality_name} quality")
        else:
            self.setToolTip(f"No videos available in {self.quality_name} quality")


class QualityFilterWidget(QWidget, LanguageSupport):
    """
    Advanced quality filter widget with icon indicators
    
    Features:
    - Quality tier selection with visual icons
    - Video count display for each quality
    - Preset selections (HD+, All, etc.)
    - Format-specific filtering
    - Real-time filter updates
    """
    
    # Signals
    filter_applied = pyqtSignal(FilterConfig)  # Applied filter configuration
    filter_cleared = pyqtSignal()
    selection_changed = pyqtSignal(list)  # List of selected qualities
    
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        LanguageSupport.__init__(self, component_name="QualityFilter")
        
        # Quality definitions with icons and colors
        self.quality_definitions = {
            '8K': {'icon': '🎦', 'color': '#FF6B35', 'order': 0},
            '4K': {'icon': '📺', 'color': '#FF8E35', 'order': 1},
            '2K': {'icon': '🖥️', 'color': '#FFB135', 'order': 2},
            '1080p': {'icon': '💻', 'color': '#0078d7', 'order': 3},
            '720p': {'icon': '📱', 'color': '#81C784', 'order': 4},
            '480p': {'icon': '📞', 'color': '#FFC107', 'order': 5},
            '360p': {'icon': '📱', 'color': '#FF9800', 'order': 6},
            '240p': {'icon': '⌚', 'color': '#795548', 'order': 7},
            'HD': {'icon': '🎬', 'color': '#2196F3', 'order': 8},
            'SD': {'icon': '📹', 'color': '#9E9E9E', 'order': 9},
            'Audio': {'icon': '🎵', 'color': '#9C27B0', 'order': 10},
            'Unknown': {'icon': '❓', 'color': '#607D8B', 'order': 11}
        }
        
        # State
        self.quality_buttons: Dict[str, QualityTierButton] = {}
        self.available_qualities: Set[str] = set()
        self.selected_qualities: Set[str] = set()
        self.video_counts: Dict[str, int] = {}
        
        # Setup
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the widget UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # Header
        self._setup_header(main_layout)
        
        # Preset buttons
        self._setup_presets(main_layout)
        
        # Quality tiers
        self._setup_quality_tiers(main_layout)
        
        # Action buttons
        self._setup_action_buttons(main_layout)
    
    def _setup_header(self, parent_layout):
        """Setup header section"""
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel(self.tr_("QUALITY_FILTER"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        # Spacer
        header_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        # Selection count
        self.selection_count_label = QLabel("0 selected")
        self.selection_count_label.setStyleSheet("color: #666666; font-size: 10px;")
        header_layout.addWidget(self.selection_count_label)
        
        parent_layout.addLayout(header_layout)
    
    def _setup_presets(self, parent_layout):
        """Setup preset selection buttons"""
        presets_group = QGroupBox(self.tr_("QUICK_SELECT"))
        presets_layout = QHBoxLayout(presets_group)
        
        # Preset buttons
        presets = [
            ("ALL", "Select All", None),
            ("HD_PLUS", "HD+", ["8K", "4K", "2K", "1080p", "720p", "HD"]),
            ("MOBILE", "Mobile", ["720p", "480p", "360p"]),
            ("AUDIO_ONLY", "Audio", ["Audio"]),
            ("CLEAR", "Clear", [])
        ]
        
        self.preset_buttons = {}
        for preset_id, preset_text, preset_qualities in presets:
            btn = QPushButton(preset_text)
            btn.setProperty("preset_id", preset_id)
            btn.setProperty("preset_qualities", preset_qualities)
            btn.clicked.connect(self._on_preset_clicked)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 4px 8px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    background-color: #f9f9f9;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #e9e9e9;
                }
                QPushButton:pressed {
                    background-color: #d9d9d9;
                }
            """)
            self.preset_buttons[preset_id] = btn
            presets_layout.addWidget(btn)
        
        parent_layout.addWidget(presets_group)
    
    def _setup_quality_tiers(self, parent_layout):
        """Setup quality tier selection"""
        qualities_group = QGroupBox(self.tr_("QUALITY_TIERS"))
        qualities_layout = QVBoxLayout(qualities_group)
        
        # Create scroll area for quality buttons
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(200)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarNever)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create quality buttons in order
        sorted_qualities = sorted(
            self.quality_definitions.items(),
            key=lambda x: x[1]['order']
        )
        
        for quality_name, quality_info in sorted_qualities:
            btn = QualityTierButton(
                quality_name,
                quality_info['icon'],
                quality_info['color']
            )
            btn.toggled.connect(self._on_quality_toggled)
            self.quality_buttons[quality_name] = btn
            scroll_layout.addWidget(btn)
        
        # Add stretch
        scroll_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        scroll_area.setWidget(scroll_widget)
        qualities_layout.addWidget(scroll_area)
        
        parent_layout.addWidget(qualities_group)
    
    def _setup_action_buttons(self, parent_layout):
        """Setup action buttons"""
        actions_layout = QHBoxLayout()
        
        # Apply button
        
        self.apply_btn = QPushButton(self.tr_("APPLY_FILTER")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #0078d7;
            }
            QPushButton:pressed {
                background-color: #0078d7;
            }
        """))
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0078d7;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.apply_btn.clicked.connect(self._apply_filter)
        self.apply_btn.setEnabled(False)
        
        # Clear button
        
        self.clear_btn = QPushButton(self.tr_("CLEAR_FILTER")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #0078d7;
            }
            QPushButton:pressed {
                background-color: #0078d7;
            }
        """))
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.clear_btn.clicked.connect(self._clear_filter)
        
        actions_layout.addWidget(self.apply_btn)
        actions_layout.addWidget(self.clear_btn)
        
        parent_layout.addLayout(actions_layout)
    
    def _connect_signals(self):
        """Connect internal signals"""
        pass  # Signals are connected in setup methods
    
    def _on_preset_clicked(self):
        """Handle preset button click"""
        btn = self.sender()
        preset_id = btn.property("preset_id")
        preset_qualities = btn.property("preset_qualities")
        
        if preset_id == "ALL":
            # Select all available qualities
            self._select_qualities(list(self.available_qualities))
        elif preset_id == "CLEAR":
            # Clear all selections
            self._select_qualities([])
        else:
            # Select specific preset qualities
            available_preset = [q for q in preset_qualities if q in self.available_qualities]
            self._select_qualities(available_preset)
    
    def _select_qualities(self, qualities: List[str]):
        """Select specific qualities"""
        # Update button states
        for quality_name, btn in self.quality_buttons.items():
            btn.setChecked(quality_name in qualities)
        
        # Update selected set
        self.selected_qualities = set(qualities)
        self._update_selection_display()
        self._update_apply_button()
    
    def _on_quality_toggled(self, checked):
        """Handle individual quality button toggle"""
        btn = self.sender()
        quality_name = btn.quality_name
        
        if checked:
            self.selected_qualities.add(quality_name)
        else:
            self.selected_qualities.discard(quality_name)
        
        self._update_selection_display()
        self._update_apply_button()
        
        # Emit selection changed
        self.selection_changed.emit(list(self.selected_qualities))
    
    def _update_selection_display(self):
        """Update selection count display"""
        count = len(self.selected_qualities)
        if count == 0:
            self.selection_count_label.setText("None selected")
        elif count == 1:
            self.selection_count_label.setText("1 selected")
        else:
            self.selection_count_label.setText(f"{count} selected")
    
    def _update_apply_button(self):
        """Update apply button state"""
        self.apply_btn.setEnabled(len(self.selected_qualities) > 0)
    
    def _apply_filter(self):
        """Apply the quality filter"""
        if not self.selected_qualities:
            return
        
        # Create filter config
        filter_config = FilterConfig(
            filter_type="in",
            values=list(self.selected_qualities),
            operator="OR"
        )
        
        self.filter_applied.emit(filter_config)
    
    def _clear_filter(self):
        """Clear the quality filter"""
        self._select_qualities([])
        self.filter_cleared.emit()
    
    def set_available_qualities(self, qualities: List[str], video_counts: Dict[str, int] = None):
        """
        Set available qualities and their video counts
        
        Args:
            qualities: List of available quality strings
            video_counts: Optional dict mapping quality -> video count
        """
        self.available_qualities = set(qualities)
        self.video_counts = video_counts or {}
        
        # Update button states
        for quality_name, btn in self.quality_buttons.items():
            if quality_name in self.available_qualities:
                count = self.video_counts.get(quality_name, 0)
                btn.set_video_count(count)
                btn.setVisible(True)
            else:
                btn.set_video_count(0)
                btn.setVisible(False)
                # Remove from selection if no longer available
                self.selected_qualities.discard(quality_name)
        
        self._update_selection_display()
        self._update_apply_button()
    
    def get_selected_qualities(self) -> List[str]:
        """Get currently selected qualities"""
        return list(self.selected_qualities)
    
    def set_selected_qualities(self, qualities: List[str]):
        """Set selected qualities programmatically"""
        # Filter to only available qualities
        valid_qualities = [q for q in qualities if q in self.available_qualities]
        self._select_qualities(valid_qualities)
    
    def clear_selection(self):
        """Clear all quality selections"""
        self._select_qualities([])
    
    def get_filter_config(self) -> Optional[FilterConfig]:
        """Get current filter configuration"""
        if not self.selected_qualities:
            return None
        
        return FilterConfig(
            filter_type="in",
            values=list(self.selected_qualities),
            operator="OR"
        )
    
    def update_language(self):
        """Update language for all UI elements"""
        super().update_language()
        
        # Update button texts
        for preset_id, btn in self.preset_buttons.items():
            if preset_id == "ALL":
                btn.setText(self.tr_("SELECT_ALL"))
            elif preset_id == "CLEAR":
                btn.setText(self.tr_("CLEAR"))
        
        self.apply_btn.setText(self.tr_("APPLY_FILTER"))
        self.clear_btn.setText(self.tr_("CLEAR_FILTER")) 