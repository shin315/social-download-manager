"""
PlatformSelector Component

Widget for selecting and detecting video platforms (YouTube, TikTok, etc.).
Implements PlatformSelectorInterface and integrates with BaseTab architecture.
"""

import re
from typing import Dict, List, Optional, Set
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QLabel, 
    QPushButton, QLineEdit, QFrame, QToolButton, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon

from ..common.interfaces import ComponentInterface
from ..common.component_interfaces import (
    PlatformSelectorInterface, PlatformType, PlatformInfo, 
    PlatformCapability, PlatformSelectorConfig
)
from ..mixins.language_support import LanguageSupport
from ..mixins.theme_support import ThemeSupport

class PlatformSelector(QWidget, ComponentInterface, PlatformSelectorInterface,
                      LanguageSupport, ThemeSupport):
    """Widget for selecting download platforms"""
    
    # Signals from PlatformSelectorInterface
    platform_selected = pyqtSignal(PlatformType)
    platform_auto_detected = pyqtSignal(PlatformType, str)
    url_validated = pyqtSignal(bool, PlatformType)
    
    # Additional convenience signals
    selection_changed = pyqtSignal(PlatformType, PlatformInfo)
    
    def __init__(self, config: Optional[PlatformSelectorConfig] = None, 
                 parent=None, lang_manager=None):
        # Initialize parent classes
        QWidget.__init__(self, parent)
        ComponentInterface.__init__(self)
        LanguageSupport.__init__(self, "PlatformSelector", lang_manager)
        ThemeSupport.__init__(self, "PlatformSelector")
        
        # Configuration
        self.config = config or PlatformSelectorConfig()
        
        # Current state
        self._current_platform: PlatformType = PlatformType.UNKNOWN
        self._last_detected_url: str = ""
        self._validation_timer = QTimer()
        self._validation_timer.setSingleShot(True)
        self._validation_timer.timeout.connect(self._validate_current_url)
        
        # Platform registry
        self._platform_registry = self._create_platform_registry()
        
        # Initialize state
        self._init_state()
        
        # Setup UI
        self.setup_ui()
        
        # Connect signals
        self._connect_signals()
    
    def _init_state(self):
        """Initialize component state"""
        # Set default platform if specified
        if self.config.default_platform != PlatformType.UNKNOWN:
            self._current_platform = self.config.default_platform
        else:
            self._current_platform = PlatformType.UNKNOWN
    
    def setup_ui(self):
        """Setup platform selector UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Platform label (optional)
        if self.config.show_label:
            self.platform_label = QLabel(self.tr_("LABEL_PLATFORM"))
            layout.addWidget(self.platform_label)
        
        # Platform selection method depends on config
        if self.config.selection_mode == "combo":
            self._setup_combo_selection(layout)
        elif self.config.selection_mode == "buttons":
            self._setup_button_selection(layout)
        else:  # auto
            self._setup_auto_selection(layout)
        
        # Status indicator
        if self.config.show_status:
            self._setup_status_indicator(layout)
        
        # Capability badges
        if self.config.show_capabilities:
            self._setup_capability_badges(layout)
    
    def _setup_combo_selection(self, parent_layout):
        """Setup combo box platform selection"""
        self.platform_combo = QComboBox()
        self.platform_combo.setMinimumWidth(120)
        
        # Populate platforms
        self._populate_combo()
        
        parent_layout.addWidget(self.platform_combo)
    
    def _setup_button_selection(self, parent_layout):
        """Setup button-based platform selection"""
        self.platform_buttons_layout = QHBoxLayout()
        self.platform_button_group = QButtonGroup(self)
        
        # Create buttons for each platform
        self._create_platform_buttons()
        
        parent_layout.addLayout(self.platform_buttons_layout)
    
    def _setup_auto_selection(self, parent_layout):
        """Setup auto-detection display"""
        # URL input for auto-detection
        if self.config.show_url_input:
            self.url_input = QLineEdit()
            self.url_input.setPlaceholderText(self.tr_("PLACEHOLDER_URL"))
            parent_layout.addWidget(self.url_input)
        
        # Current platform display
        self.current_platform_label = QLabel(self.tr_("PLATFORM_UNKNOWN"))
        font = QFont()
        font.setBold(True)
        self.current_platform_label.setFont(font)
        parent_layout.addWidget(self.current_platform_label)
    
    def _setup_status_indicator(self, parent_layout):
        """Setup status indicator"""
        self.status_label = QLabel()
        self.status_label.setMaximumWidth(20)
        parent_layout.addWidget(self.status_label)
        
        # Set initial status
        self._update_status_indicator(False)
    
    def _setup_capability_badges(self, parent_layout):
        """Setup capability badges display"""
        self.capabilities_layout = QHBoxLayout()
        self.capability_badges: Dict[str, QLabel] = {}
        
        # Create badge labels
        badge_configs = [
            ("download", "📥", self.tr_("CAPABILITY_DOWNLOAD")),
            ("metadata", "📊", self.tr_("CAPABILITY_METADATA")),
            ("search", "🔍", self.tr_("CAPABILITY_SEARCH")),
            ("playlist", "📋", self.tr_("CAPABILITY_PLAYLIST")),
        ]
        
        for capability, icon, tooltip in badge_configs:
            badge = QLabel(icon)
            badge.setToolTip(tooltip)
            badge.setVisible(False)  # Hidden by default
            self.capability_badges[capability] = badge
            self.capabilities_layout.addWidget(badge)
        
        parent_layout.addLayout(self.capabilities_layout)
    
    def _connect_signals(self):
        """Connect internal signals"""
        # Combo box selection
        if hasattr(self, 'platform_combo'):
            self.platform_combo.currentTextChanged.connect(self._on_combo_selection_changed)
        
        # Button selection
        if hasattr(self, 'platform_button_group'):
            self.platform_button_group.idClicked.connect(self._on_button_selection_changed)
        
        # URL input for auto-detection
        if hasattr(self, 'url_input'):
            self.url_input.textChanged.connect(self._on_url_input_changed)
        
        # Validation timer
        self._validation_timer.timeout.connect(self._validate_current_url)
    
    # =========================================================================
    # Platform Registry
    # =========================================================================
    
    def _create_platform_registry(self) -> Dict[PlatformType, PlatformInfo]:
        """Create platform information registry"""
        return {
            PlatformType.YOUTUBE: PlatformInfo(
                platform_type=PlatformType.YOUTUBE,
                name="YouTube",
                icon_path=":/icons/youtube.png",
                capabilities=PlatformCapability(
                    download=True, 
                    metadata=True, 
                    search=True, 
                    playlist=True
                ),
                url_patterns=[
                    r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
                    r'https?://youtu\.be/([a-zA-Z0-9_-]+)',
                    r'https?://(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
                    r'https?://(?:www\.)?youtube\.com/c/([a-zA-Z0-9_-]+)',
                    r'https?://(?:www\.)?youtube\.com/user/([a-zA-Z0-9_-]+)',
                ]
            ),
            PlatformType.TIKTOK: PlatformInfo(
                platform_type=PlatformType.TIKTOK,
                name="TikTok",
                icon_path=":/icons/tiktok.png",
                capabilities=PlatformCapability(
                    download=True, 
                    metadata=True, 
                    search=False, 
                    playlist=False
                ),
                url_patterns=[
                    r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+',
                    r'https?://(vm\.|vt\.)?tiktok\.com/\w+',
                    r'https?://tiktok\.com/t/\w+',
                ]
            ),
            PlatformType.INSTAGRAM: PlatformInfo(
                platform_type=PlatformType.INSTAGRAM,
                name="Instagram",
                icon_path=":/icons/instagram.png",
                capabilities=PlatformCapability(
                    download=True, 
                    metadata=True, 
                    search=False, 
                    playlist=False
                ),
                url_patterns=[
                    r'https?://(www\.)?instagram\.com/p/[\w\.-]+',
                    r'https?://(www\.)?instagram\.com/reel/[\w\.-]+',
                    r'https?://(www\.)?instagram\.com/tv/[\w\.-]+',
                ]
            ),
            PlatformType.TWITTER: PlatformInfo(
                platform_type=PlatformType.TWITTER,
                name="Twitter/X",
                icon_path=":/icons/twitter.png",
                capabilities=PlatformCapability(
                    download=True, 
                    metadata=True, 
                    search=False, 
                    playlist=False
                ),
                url_patterns=[
                    r'https?://(www\.)?(twitter|x)\.com/\w+/status/\d+',
                ]
            ),
        }
    
    # =========================================================================
    # PlatformSelectorInterface Implementation
    # =========================================================================
    
    def get_available_platforms(self) -> List[PlatformType]:
        """Get list of available platforms"""
        platforms = list(self._platform_registry.keys())
        if self.config.include_unknown:
            platforms.insert(0, PlatformType.UNKNOWN)
        return platforms
    
    def get_current_platform(self) -> PlatformType:
        """Get currently selected platform"""
        return self._current_platform
    
    def set_platform(self, platform: PlatformType) -> None:
        """Set current platform"""
        if platform == self._current_platform:
            return
        
        old_platform = self._current_platform
        self._current_platform = platform
        
        # Update UI
        self._update_ui_for_platform(platform)
        
        # Update capabilities
        self._update_capability_display(platform)
        
        # Emit signals
        platform_info = self._platform_registry.get(platform, None)
        self.platform_selected.emit(platform)
        if platform_info:
            self.selection_changed.emit(platform, platform_info)
    
    def detect_platform(self, url: str) -> Optional[PlatformType]:
        """Auto-detect platform from URL"""
        if not url.strip():
            return None
        
        # Try to match against each platform's patterns
        for platform_type, platform_info in self._platform_registry.items():
            for pattern in platform_info.url_patterns:
                if re.match(pattern, url.strip(), re.IGNORECASE):
                    detected_platform = platform_type
                    
                    # Auto-set if enabled
                    if self.config.auto_detect:
                        self.set_platform(detected_platform)
                    
                    # Emit detection signal
                    self.platform_auto_detected.emit(detected_platform, url)
                    
                    return detected_platform
        
        return PlatformType.UNKNOWN
    
    def validate_url(self, url: str) -> bool:
        """Validate URL for current platform"""
        if not url.strip() or self._current_platform == PlatformType.UNKNOWN:
            return False
        
        platform_info = self._platform_registry.get(self._current_platform)
        if not platform_info:
            return False
        
        # Check if URL matches current platform patterns
        for pattern in platform_info.url_patterns:
            if re.match(pattern, url.strip(), re.IGNORECASE):
                self.url_validated.emit(True, self._current_platform)
                return True
        
        self.url_validated.emit(False, self._current_platform)
        return False
    
    def get_platform_info(self, platform: PlatformType) -> Optional[PlatformInfo]:
        """Get platform information"""
        return self._platform_registry.get(platform)
    
    def get_platform_capabilities(self, platform: PlatformType) -> Optional[PlatformCapability]:
        """Get platform capabilities"""
        platform_info = self._platform_registry.get(platform)
        return platform_info.capabilities if platform_info else None
    
    # =========================================================================
    # UI Population and Updates
    # =========================================================================
    
    def _populate_combo(self):
        """Populate combo box with platforms"""
        self.platform_combo.clear()
        
        platforms = self.get_available_platforms()
        for platform in platforms:
            platform_info = self._platform_registry.get(platform)
            if platform == PlatformType.UNKNOWN:
                display_name = self.tr_("PLATFORM_UNKNOWN")
            elif platform_info:
                display_name = platform_info.name
            else:
                display_name = platform.value
            
            self.platform_combo.addItem(display_name, platform)
        
        # Set current selection
        self._update_combo_selection()
    
    def _create_platform_buttons(self):
        """Create platform selection buttons"""
        platforms = self.get_available_platforms()
        
        for i, platform in enumerate(platforms):
            platform_info = self._platform_registry.get(platform)
            
            if platform == PlatformType.UNKNOWN:
                button_text = self.tr_("PLATFORM_UNKNOWN")
                button_icon = None
            elif platform_info:
                button_text = platform_info.name
                button_icon = platform_info.icon_path
            else:
                button_text = platform.value
                button_icon = None
            
            button = QPushButton(button_text)
            button.setCheckable(True)
            
            # Set icon if available
            if button_icon and self.config.show_icons:
                # button.setIcon(QIcon(button_icon))
                pass
            
            self.platform_button_group.addButton(button, i)
            self.platform_buttons_layout.addWidget(button)
        
        # Set current selection
        self._update_button_selection()
    
    def _update_ui_for_platform(self, platform: PlatformType):
        """Update UI elements for selected platform"""
        # Update combo selection
        if hasattr(self, 'platform_combo'):
            self._update_combo_selection()
        
        # Update button selection
        if hasattr(self, 'platform_button_group'):
            self._update_button_selection()
        
        # Update auto-detection display
        if hasattr(self, 'current_platform_label'):
            platform_info = self._platform_registry.get(platform)
            if platform == PlatformType.UNKNOWN:
                display_text = self.tr_("PLATFORM_UNKNOWN")
            elif platform_info:
                display_text = platform_info.name
            else:
                display_text = platform.value
            
            self.current_platform_label.setText(display_text)
        
        # Update status
        if hasattr(self, 'status_label'):
            is_valid = platform != PlatformType.UNKNOWN
            self._update_status_indicator(is_valid)
    
    def _update_combo_selection(self):
        """Update combo box selection"""
        if not hasattr(self, 'platform_combo'):
            return
        
        for i in range(self.platform_combo.count()):
            platform = self.platform_combo.itemData(i)
            if platform == self._current_platform:
                self.platform_combo.setCurrentIndex(i)
                break
    
    def _update_button_selection(self):
        """Update button selection"""
        if not hasattr(self, 'platform_button_group'):
            return
        
        platforms = self.get_available_platforms()
        try:
            platform_index = platforms.index(self._current_platform)
            button = self.platform_button_group.button(platform_index)
            if button:
                button.setChecked(True)
        except ValueError:
            # Platform not found, clear all selections
            for button in self.platform_button_group.buttons():
                button.setChecked(False)
    
    def _update_capability_display(self, platform: PlatformType):
        """Update capability badges display"""
        if not self.config.show_capabilities or not hasattr(self, 'capability_badges'):
            return
        
        # Hide all badges first
        for badge in self.capability_badges.values():
            badge.setVisible(False)
        
        # Show badges for available capabilities
        capabilities = self.get_platform_capabilities(platform)
        if capabilities:
            if capabilities.download:
                self.capability_badges["download"].setVisible(True)
            if capabilities.metadata:
                self.capability_badges["metadata"].setVisible(True)
            if capabilities.search:
                self.capability_badges["search"].setVisible(True)
            if capabilities.playlist:
                self.capability_badges["playlist"].setVisible(True)
    
    def _update_status_indicator(self, is_valid: bool):
        """Update status indicator"""
        if not hasattr(self, 'status_label'):
            return
        
        if is_valid:
            self.status_label.setText("✅")
            self.status_label.setToolTip(self.tr_("STATUS_VALID_PLATFORM"))
        else:
            self.status_label.setText("❌")
            self.status_label.setToolTip(self.tr_("STATUS_INVALID_PLATFORM"))
    
    # =========================================================================
    # Event Handlers
    # =========================================================================
    
    def _on_combo_selection_changed(self, text: str):
        """Handle combo box selection change"""
        # Find platform by display name
        for i in range(self.platform_combo.count()):
            if self.platform_combo.itemText(i) == text:
                platform = self.platform_combo.itemData(i)
                if platform != self._current_platform:
                    self.set_platform(platform)
                break
    
    def _on_button_selection_changed(self, button_id: int):
        """Handle button selection change"""
        platforms = self.get_available_platforms()
        if 0 <= button_id < len(platforms):
            platform = platforms[button_id]
            if platform != self._current_platform:
                self.set_platform(platform)
    
    def _on_url_input_changed(self, url: str):
        """Handle URL input change for auto-detection"""
        self._last_detected_url = url
        
        # Debounce validation
        self._validation_timer.start(500)  # 500ms delay
    
    def _validate_current_url(self):
        """Validate current URL and auto-detect if enabled"""
        if not hasattr(self, 'url_input'):
            return
        
        url = self.url_input.text().strip()
        if not url:
            return
        
        # Try auto-detection
        detected_platform = self.detect_platform(url)
        
        if detected_platform and detected_platform != PlatformType.UNKNOWN:
            # Update status for successful detection
            self._update_status_indicator(True)
        else:
            # Update status for failed detection
            self._update_status_indicator(False)
    
    # =========================================================================
    # Public API Extensions
    # =========================================================================
    
    def add_platform(self, platform_info: PlatformInfo):
        """Add custom platform to registry"""
        self._platform_registry[platform_info.platform_type] = platform_info
        
        # Refresh UI if needed
        if hasattr(self, 'platform_combo'):
            self._populate_combo()
        elif hasattr(self, 'platform_button_group'):
            # Clear and recreate buttons
            for button in self.platform_button_group.buttons():
                self.platform_button_group.removeButton(button)
                button.deleteLater()
            self._create_platform_buttons()
    
    def remove_platform(self, platform: PlatformType):
        """Remove platform from registry"""
        if platform in self._platform_registry:
            del self._platform_registry[platform]
            
            # Update current selection if removed platform was selected
            if self._current_platform == platform:
                self.set_platform(PlatformType.UNKNOWN)
            
            # Refresh UI
            if hasattr(self, 'platform_combo'):
                self._populate_combo()
            elif hasattr(self, 'platform_button_group'):
                # Clear and recreate buttons
                for button in self.platform_button_group.buttons():
                    self.platform_button_group.removeButton(button)
                    button.deleteLater()
                self._create_platform_buttons()
    
    def get_url_input_text(self) -> str:
        """Get current URL input text"""
        if hasattr(self, 'url_input'):
            return self.url_input.text()
        return ""
    
    def set_url_input_text(self, url: str):
        """Set URL input text"""
        if hasattr(self, 'url_input'):
            self.url_input.setText(url)
    
    # =========================================================================
    # Language and Theme Support
    # =========================================================================
    
    def update_language(self):
        """Update UI for language changes"""
        super().update_language()
        
        # Update labels
        if hasattr(self, 'platform_label'):
            self.platform_label.setText(self.tr_("LABEL_PLATFORM"))
        
        # Update placeholders
        if hasattr(self, 'url_input'):
            self.url_input.setPlaceholderText(self.tr_("PLACEHOLDER_URL"))
        
        # Update combo box
        if hasattr(self, 'platform_combo'):
            self._populate_combo()
        
        # Update buttons
        if hasattr(self, 'platform_button_group'):
            # Recreate buttons with new text
            current_platform = self._current_platform
            for button in self.platform_button_group.buttons():
                self.platform_button_group.removeButton(button)
                button.deleteLater()
            self._create_platform_buttons()
            self.set_platform(current_platform)
        
        # Update current platform display
        if hasattr(self, 'current_platform_label'):
            self._update_ui_for_platform(self._current_platform)
        
        # Update capability tooltips
        if hasattr(self, 'capability_badges'):
            self.capability_badges["download"].setToolTip(self.tr_("CAPABILITY_DOWNLOAD"))
            self.capability_badges["metadata"].setToolTip(self.tr_("CAPABILITY_METADATA"))
            self.capability_badges["search"].setToolTip(self.tr_("CAPABILITY_SEARCH"))
            self.capability_badges["playlist"].setToolTip(self.tr_("CAPABILITY_PLAYLIST"))
    
    def apply_theme(self, theme: Dict):
        """Apply theme to component"""
        super().apply_theme(theme)
        
        # Get component-specific theme settings
        platform_theme = theme.get('platformselector', {})
        
        # Apply to combo box
        if hasattr(self, 'platform_combo') and 'combo_style' in platform_theme:
            self.platform_combo.setStyleSheet(platform_theme['combo_style'])
        
        # Apply to buttons
        if hasattr(self, 'platform_button_group') and 'button_style' in platform_theme:
            for button in self.platform_button_group.buttons():
                button.setStyleSheet(platform_theme['button_style'])
        
        # Apply to URL input
        if hasattr(self, 'url_input') and 'input_style' in platform_theme:
            self.url_input.setStyleSheet(platform_theme['input_style'])


# =============================================================================
# Factory Functions
# =============================================================================

def create_combo_platform_selector_config() -> PlatformSelectorConfig:
    """Create configuration for combo box platform selector"""
    return PlatformSelectorConfig(
        selection_mode="combo",
        show_label=True,
        show_status=True,
        show_capabilities=True,
        show_icons=True,
        auto_detect=False,
        include_unknown=True,
        default_platform=PlatformType.UNKNOWN
    )

def create_button_platform_selector_config() -> PlatformSelectorConfig:
    """Create configuration for button-based platform selector"""
    return PlatformSelectorConfig(
        selection_mode="buttons",
        show_label=False,
        show_status=False,
        show_capabilities=False,
        show_icons=True,
        auto_detect=False,
        include_unknown=False,
        default_platform=PlatformType.YOUTUBE
    )

def create_auto_detect_platform_selector_config() -> PlatformSelectorConfig:
    """Create configuration for auto-detecting platform selector"""
    return PlatformSelectorConfig(
        selection_mode="auto",
        show_label=True,
        show_url_input=True,
        show_status=True,
        show_capabilities=True,
        show_icons=False,
        auto_detect=True,
        include_unknown=True,
        default_platform=PlatformType.UNKNOWN
    ) 