# UI Component Design Patterns - Task 17.2

## Overview
This document defines consistent design patterns and implementation guidelines for all UI components in the Social Download Manager application.

## Design Date
**Completed:** 2025-01-29  
**Task:** 17.2 - Interface Design for Component API  
**Status:** ✅ COMPLETED

---

## 🏗️ **COMMON DESIGN PATTERNS**

### **1. Base Component Structure**
All components must follow this standard pattern:

```python
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal

from ..common.interfaces import ComponentInterface
from ..common.component_interfaces import [SpecificInterface]
from ..mixins.language_support import LanguageSupport
from ..mixins.theme_support import ThemeSupport

class ComponentName(QWidget, ComponentInterface, SpecificInterface, 
                   LanguageSupport, ThemeSupport):
    """Component description"""
    
    # Define signals first
    component_signal = pyqtSignal(...)
    
    def __init__(self, config: ComponentConfig, parent=None, lang_manager=None):
        # Initialize parent classes
        QWidget.__init__(self, parent)
        ComponentInterface.__init__(self)
        SpecificInterface.__init__(self)
        LanguageSupport.__init__(self, "ComponentName", lang_manager)
        ThemeSupport.__init__(self, "ComponentName")
        
        # Store configuration
        self.config = config
        
        # Initialize state
        self._init_state()
        
        # Setup UI
        self.setup_ui()
        
        # Connect signals
        self._connect_signals()
    
    def _init_state(self):
        """Initialize component state"""
        pass
    
    def setup_ui(self):
        """Setup component UI"""
        pass
    
    def _connect_signals(self):
        """Connect internal signals"""
        pass
    
    # Implement interface methods...
    
    def update_language(self):
        """Update UI for language changes"""
        super().update_language()
        # Update component-specific text
    
    def apply_theme(self, theme: Dict):
        """Apply theme to component"""
        super().apply_theme(theme)
        # Apply component-specific styling
```

---

## 📋 **TABLE COMPONENTS DESIGN**

### **VideoTable Base Component**

```python
from PyQt6.QtWidgets import QTableWidget, QHeaderView, QAbstractItemView
from ..common.component_interfaces import TableInterface

class VideoTable(QTableWidget, ComponentInterface, TableInterface, 
                LanguageSupport, ThemeSupport):
    """Base video table with common functionality"""
    
    # Signals
    selection_changed = pyqtSignal(list)
    item_action_requested = pyqtSignal(str, object)
    sort_changed = pyqtSignal(SortConfig)
    
    def __init__(self, config: TableConfig, parent=None, lang_manager=None):
        # Standard initialization...
        
    def setup_table(self, config: TableConfig) -> None:
        """Initialize table with configuration"""
        self.setColumnCount(len(config.columns))
        self.setRowCount(0)
        
        # Configure headers
        self._setup_headers(config.columns)
        
        # Configure table behavior
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection if config.multi_select 
            else QAbstractItemView.SelectionMode.SingleSelection
        )
        
        # Configure sorting
        if config.sortable:
            self.setSortingEnabled(True)
            self.sortByColumn(config.default_sort_column, config.default_sort_order)
    
    def _setup_headers(self, columns: List[ColumnConfig]):
        """Setup table headers"""
        header_labels = []
        for col in columns:
            header_labels.append(self.tr_(col.key))
        
        self.setHorizontalHeaderLabels(header_labels)
        
        # Configure column properties
        horizontal_header = self.horizontalHeader()
        for i, col in enumerate(columns):
            if col.width > 0:
                self.setColumnWidth(i, col.width)
            if not col.resizable:
                horizontal_header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            if not col.visible:
                self.hideColumn(i)
    
    # Implement required interface methods...
```

### **FilterableVideoTable Component**

```python
class FilterableVideoTable(VideoTable, FilterableTableInterface):
    """Video table with advanced filtering capabilities"""
    
    # Additional signals
    filter_changed = pyqtSignal(dict)
    filter_applied = pyqtSignal(FilterConfig)
    filter_cleared = pyqtSignal(int)
    
    def __init__(self, config: TableConfig, parent=None, lang_manager=None):
        super().__init__(config, parent, lang_manager)
        
        # Filter state
        self._active_filters: Dict[int, FilterConfig] = {}
        self._original_data: List[Any] = []
        self._filtered_data: List[Any] = []
        
        # Search state
        self._search_query: str = ""
        self._search_columns: List[int] = []
    
    def apply_filter(self, column: int, filter_config: FilterConfig) -> None:
        """Apply filter to specific column"""
        self._active_filters[column] = filter_config
        self._apply_all_filters()
        self.filter_applied.emit(filter_config)
        self.filter_changed.emit(self._active_filters.copy())
    
    def _apply_all_filters(self):
        """Apply all active filters to data"""
        filtered_data = self._original_data.copy()
        
        # Apply each filter
        for column, filter_config in self._active_filters.items():
            filtered_data = self._apply_single_filter(filtered_data, column, filter_config)
        
        # Apply search if active
        if self._search_query:
            filtered_data = self._apply_search(filtered_data, self._search_query)
        
        self._filtered_data = filtered_data
        self._update_table_display()
    
    # Implement FilterableTableInterface methods...
```

---

## 🎛️ **PLATFORM SELECTOR DESIGN**

```python
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QComboBox, QLabel
from ..common.component_interfaces import PlatformSelectorInterface, PlatformType

class PlatformSelector(QWidget, ComponentInterface, PlatformSelectorInterface,
                      LanguageSupport, ThemeSupport):
    """Widget for selecting download platforms"""
    
    # Signals
    platform_selected = pyqtSignal(PlatformType)
    platform_auto_detected = pyqtSignal(PlatformType, str)
    url_validated = pyqtSignal(bool, PlatformType)
    
    def __init__(self, config: PlatformSelectorConfig, parent=None, lang_manager=None):
        # Standard initialization...
        
        # Platform registry
        self._platform_registry = {
            PlatformType.YOUTUBE: PlatformInfo(
                platform_type=PlatformType.YOUTUBE,
                name="YouTube",
                icon_path=":/icons/youtube.png",
                capabilities=PlatformCapability(download=True, metadata=True, search=True),
                url_patterns=[
                    r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
                    r'https?://youtu\.be/([a-zA-Z0-9_-]+)',
                ]
            ),
            PlatformType.TIKTOK: PlatformInfo(
                platform_type=PlatformType.TIKTOK,
                name="TikTok",
                icon_path=":/icons/tiktok.png",
                capabilities=PlatformCapability(download=True, metadata=True),
                url_patterns=[
                    r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+',
                    r'https?://(vm\.|vt\.)?tiktok\.com/\w+',
                ]
            )
        }
    
    def setup_ui(self):
        """Setup platform selector UI"""
        layout = QHBoxLayout(self)
        
        # Platform label
        self.platform_label = QLabel(self.tr_("LABEL_PLATFORM"))
        layout.addWidget(self.platform_label)
        
        # Platform combo box
        self.platform_combo = QComboBox()
        self._populate_platforms()
        self.platform_combo.currentTextChanged.connect(self._on_platform_changed)
        layout.addWidget(self.platform_combo)
        
        # Status indicator
        if self.config.show_status:
            self.status_label = QLabel()
            layout.addWidget(self.status_label)
        
        # Capability badges
        if self.config.show_capabilities:
            self.capabilities_layout = QHBoxLayout()
            layout.addLayout(self.capabilities_layout)
    
    def detect_platform(self, url: str) -> Optional[PlatformType]:
        """Auto-detect platform from URL"""
        import re
        
        for platform_type, platform_info in self._platform_registry.items():
            for pattern in platform_info.url_patterns:
                if re.match(pattern, url):
                    if self.config.auto_detect:
                        self.set_platform(platform_type)
                    self.platform_auto_detected.emit(platform_type, url)
                    return platform_type
        
        return PlatformType.UNKNOWN
    
    # Implement PlatformSelectorInterface methods...
```

---

## 📊 **PROGRESS TRACKER DESIGN**

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QLabel
from ..common.component_interfaces import ProgressTrackerInterface

class ProgressTracker(QWidget, ComponentInterface, ProgressTrackerInterface,
                     LanguageSupport, ThemeSupport):
    """Widget for tracking download progress"""
    
    # Signals
    progress_updated = pyqtSignal(int, str)
    progress_completed = pyqtSignal()
    progress_failed = pyqtSignal(str)
    progress_cancelled = pyqtSignal()
    
    def __init__(self, config: Optional[dict] = None, parent=None, lang_manager=None):
        # Standard initialization...
        
        # Progress state
        self._current_progress = 0
        self._current_speed = ""
        self._current_status = ""
        self._is_indeterminate = False
        self._is_completed = False
        self._is_failed = False
    
    def setup_ui(self):
        """Setup progress tracker UI"""
        layout = QVBoxLayout(self)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status and speed layout
        info_layout = QHBoxLayout()
        
        # Status label
        self.status_label = QLabel()
        info_layout.addWidget(self.status_label)
        
        # Speed label
        self.speed_label = QLabel()
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        info_layout.addWidget(self.speed_label)
        
        layout.addLayout(info_layout)
    
    # Implement ProgressTrackerInterface methods...
```

---

## 🔍 **SEARCH AND FILTER DESIGN**

### **SearchWidget**

```python
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from PyQt6.QtCore import QTimer
from ..common.component_interfaces import SearchInterface

class SearchWidget(QWidget, ComponentInterface, SearchInterface,
                  LanguageSupport, ThemeSupport):
    """Advanced search widget with filters"""
    
    # Signals
    search_query_changed = pyqtSignal(str)
    search_executed = pyqtSignal(str, list)
    search_cleared = pyqtSignal()
    
    def __init__(self, config: SearchConfig, parent=None, lang_manager=None):
        # Standard initialization...
        
        # Search state
        self._search_query = ""
        self._search_columns = config.search_columns or []
        
        # Debounce timer
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._execute_search)
    
    def setup_ui(self):
        """Setup search widget UI"""
        layout = QHBoxLayout(self)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr_(self.config.placeholder_text))
        self.search_input.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self.search_input)
        
        # Clear button
        self.clear_button = QPushButton("×")
        self.clear_button.setFixedSize(25, 25)
        self.clear_button.clicked.connect(self.clear_search)
        layout.addWidget(self.clear_button)
    
    def _on_search_text_changed(self, text: str):
        """Handle search text changes with debouncing"""
        self._search_query = text
        self._debounce_timer.start(self.config.debounce_delay)
        self.search_query_changed.emit(text)
    
    # Implement SearchInterface methods...
```

---

## 🎨 **STYLING AND THEMING PATTERNS**

### **Theme Integration Pattern**

```python
def apply_theme(self, theme: Dict):
    """Apply theme to component"""
    super().apply_theme(theme)
    
    # Get component-specific theme settings
    component_theme = theme.get(f"{self.__class__.__name__.lower()}", {})
    
    # Apply background color
    if 'background_color' in component_theme:
        self.setStyleSheet(f"background-color: {component_theme['background_color']};")
    
    # Apply to child widgets
    if hasattr(self, 'search_input') and 'input_style' in component_theme:
        self.search_input.setStyleSheet(component_theme['input_style'])
    
    if hasattr(self, 'progress_bar') and 'progress_style' in component_theme:
        self.progress_bar.setStyleSheet(component_theme['progress_style'])
```

### **Language Support Pattern**

```python
def update_language(self):
    """Update UI for language changes"""
    super().update_language()
    
    # Update labels
    if hasattr(self, 'platform_label'):
        self.platform_label.setText(self.tr_("LABEL_PLATFORM"))
    
    # Update placeholders
    if hasattr(self, 'search_input'):
        self.search_input.setPlaceholderText(self.tr_("PLACEHOLDER_SEARCH"))
    
    # Update combo box items
    if hasattr(self, 'platform_combo'):
        self._update_combo_text()
```

---

## 🔗 **SIGNAL CONNECTION PATTERNS**

### **Internal Signal Connections**

```python
def _connect_signals(self):
    """Connect internal signals"""
    # Widget to widget connections
    if hasattr(self, 'search_input'):
        self.search_input.textChanged.connect(self._on_search_changed)
    
    # Timer connections
    if hasattr(self, '_debounce_timer'):
        self._debounce_timer.timeout.connect(self._execute_search)
    
    # State change notifications
    self.selection_changed.connect(self._on_selection_changed)
```

### **External Integration Pattern**

```python
def connect_to_tab(self, tab):
    """Connect component to parent tab"""
    # Connect to tab signals
    tab.tab_activated.connect(self._on_tab_activated)
    tab.tab_deactivated.connect(self._on_tab_deactivated)
    
    # Connect to component bus
    if hasattr(tab, 'component_bus'):
        self._connect_to_component_bus(tab.component_bus)

def _connect_to_component_bus(self, bus):
    """Connect to component event bus"""
    # Subscribe to relevant events
    bus.subscribe('LANGUAGE_CHANGED', self.update_language)
    bus.subscribe('THEME_CHANGED', self.apply_theme)
    
    # Publish own events
    self.selection_changed.connect(
        lambda items: bus.publish('SELECTION_CHANGED', {'component': self, 'items': items})
    )
```

---

## 📝 **CONFIGURATION PATTERNS**

### **Configuration Validation**

```python
def _validate_config(self, config):
    """Validate component configuration"""
    if not isinstance(config, self.expected_config_type):
        raise TypeError(f"Expected {self.expected_config_type.__name__}, got {type(config)}")
    
    # Validate required fields
    required_fields = getattr(config, '_required_fields', [])
    for field in required_fields:
        if not hasattr(config, field):
            raise ValueError(f"Missing required field: {field}")
    
    return config
```

### **Default Configuration Factory**

```python
@classmethod
def create_default_config(cls) -> ComponentConfig:
    """Create default configuration for component"""
    return ComponentConfig(
        # Set sensible defaults
        auto_detect=True,
        show_capabilities=True,
        # ... other defaults
    )

@classmethod
def create_compact_config(cls) -> ComponentConfig:
    """Create compact mode configuration"""
    config = cls.create_default_config()
    config.compact_mode = True
    config.show_capabilities = False
    return config
```

---

## ✅ **DESIGN PATTERNS SUMMARY**

### **Must-Follow Patterns:**
1. **Standard Initialization** - All components follow the same init pattern
2. **Interface Implementation** - All components implement appropriate interfaces
3. **Mixin Integration** - Language and theme support through mixins
4. **Signal Consistency** - Standard signal naming and emission patterns
5. **Configuration Management** - Typed configuration with validation
6. **State Management** - Consistent state initialization and updates

### **Best Practices:**
1. **Separation of Concerns** - UI setup, signal connection, and business logic separated
2. **Error Handling** - Graceful handling of configuration and runtime errors  
3. **Performance** - Debouncing for search, efficient filtering, lazy loading
4. **Accessibility** - Proper tab order, keyboard shortcuts, screen reader support
5. **Testing** - Interface compliance, signal emission, state management

---

**Design Patterns Completed ✅**  
**Ready for Task 17.3 - Implementation Strategy** 