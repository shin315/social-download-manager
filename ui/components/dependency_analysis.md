# UI Component Dependency Analysis - Task 15.2

## Data Flow Analysis

### 1. State Management Comparison

#### DownloadedVideosTab State Variables
```python
self.parent = parent  # MainWindow reference
self.lang_manager = parent.lang_manager  # Language manager from parent
self.all_videos = []  # List of all downloaded videos
self.filtered_videos = []  # List of filtered videos  
self.selected_video = None  # Currently selected video
self.sort_column = 7  # Default sort column
self.sort_order = Qt.SortOrder.DescendingOrder  # Sort order
self.active_filters = {}  # {column_index: [allowed_values]}

# Column indices constants
self.select_col = 0
self.title_col = 1
# ... etc
```

#### VideoInfoTab State Variables
```python
self.parent = parent  # MainWindow reference
self.lang_manager = get_language_manager()  # Direct language manager
self.video_info_dict = {}  # Dictionary with URL as key, VideoInfo as value
self.processing_count = 0  # Videos being processed
self.downloading_count = 0  # Videos being downloaded
self.all_selected = False  # Selection state
self.downloader = TikTokDownloader()  # Downloader instance
self.network_manager = QNetworkAccessManager()  # Network manager
self.last_clipboard_text = ""  # Clipboard monitoring
```

### 2. Shared Dependencies

#### External Dependencies
1. **Language Management**
   - `localization.get_language_manager()`
   - `self.lang_manager.tr(key)` - Translation method
   - Both tabs depend on parent's language_manager

2. **Database Operations**
   - `utils.db_manager.DatabaseManager` - Database access
   - Used in `load_downloaded_videos()`, `add_downloaded_video()`

3. **Download Operations**
   - `utils.downloader.TikTokDownloader` - Download functionality
   - Signal connections: info_signal, progress_signal, finished_signal

4. **PyQt6 Components**
   - Extensive use of Qt widgets, layouts, signals/slots
   - QNetworkAccessManager for thumbnail loading

### 3. Component Communication Patterns

#### Parent-Child Communication
```
MainWindow (parent)
├── language_changed signal → Tab widgets
├── theme changes → apply_theme_colors()
├── config updates → load/save operations
└── shared language_manager reference
```

#### Signal-Slot Patterns
```python
# Common pattern in both tabs
self.downloader.info_signal.connect(self.handle_video_info)
self.downloader.progress_signal.connect(self.handle_progress)
self.downloader.finished_signal.connect(self.handle_download_finished)

# Table interactions
self.downloads_table.selectionModel().selectionChanged.connect(self.handle_selection_changed)
self.search_input.textChanged.connect(self.filter_videos)
```

### 4. Data Flow Diagrams

#### Video Information Flow
```
User Input (URL) 
    ↓
get_video_info() 
    ↓
TikTokDownloader.get_info()
    ↓
info_signal emission
    ↓
handle_video_info() 
    ↓
update video_info_dict/all_videos
    ↓
display_videos()/update table
    ↓
UI Refresh
```

#### Filter/Search Flow
```
User Input (search text/filter)
    ↓
filter_videos()/apply_column_filter()
    ↓
Process all_videos → filtered_videos
    ↓
display_videos(filtered_videos)
    ↓
Update table display
    ↓
Update statistics/counts
```

#### Selection Management Flow
```
User Selection (checkbox/click)
    ↓
checkbox_state_changed()/handle_selection_changed()
    ↓
Update internal selection state
    ↓
update_select_toggle_button()
    ↓
update_button_states()
    ↓
UI state refresh
```

### 5. Shared State Dependencies

#### Critical Shared State
1. **Language State** - Both tabs depend on language_manager
2. **Theme State** - Both tabs need theme updates
3. **Configuration State** - Output folders, settings
4. **Parent Window State** - Reference to MainWindow

#### Component-Specific State
1. **VideoInfoTab**: video_info_dict, processing_count, downloading_count
2. **DownloadedVideosTab**: all_videos, filtered_videos, active_filters, sort state

### 6. Circular Dependencies Identified

#### High Risk Dependencies
1. **Parent Window References**
   - Both tabs store `self.parent` reference
   - Parent also maintains references to tabs
   - **Resolution**: Use event system instead of direct references

2. **Language Manager Access**
   - VideoInfoTab: `get_language_manager()` directly
   - DownloadedVideosTab: `parent.lang_manager`
   - **Resolution**: Standardize language manager access

3. **Database Access**
   - Both tabs directly access DatabaseManager
   - No centralized data management
   - **Resolution**: Repository pattern through app controller

#### Medium Risk Dependencies
1. **Downloader Instance**
   - VideoInfoTab creates its own TikTokDownloader
   - DownloadedVideosTab may need download capability
   - **Resolution**: Shared downloader service

2. **Network Manager**
   - VideoInfoTab creates QNetworkAccessManager
   - DownloadedVideosTab might need network access
   - **Resolution**: Shared network service

### 7. Component Dependency Graph

```
MainWindow
├── LanguageManager ←── VideoInfoTab
├── ThemeManager ←── DownloadedVideosTab
├── ConfigManager ←── Both tabs
└── DatabaseManager ←── Both tabs (direct access)

VideoInfoTab
├── TikTokDownloader (owns instance)
├── QNetworkAccessManager (owns instance)
└── ClipboardMonitoring (direct access)

DownloadedVideosTab
├── DatabaseManager (direct access)
├── File system operations (direct access)
└── Video player integration (subprocess)
```

### 8. Interface Requirements for Components

#### VideoTable Interface
```python
class VideoTable:
    # Data management
    def set_data(self, videos: List[VideoInfo]) -> None
    def get_selected_items(self) -> List[VideoInfo]
    def clear_selection(self) -> None
    
    # Signals
    selection_changed = pyqtSignal(list)  # Selected items
    item_action_requested = pyqtSignal(str, object)  # Action, item
    
    # Configuration
    def set_columns(self, columns: List[ColumnConfig]) -> None
    def set_context_menu(self, menu: QMenu) -> None
```

#### FilterableVideoTable Interface
```python
class FilterableVideoTable(VideoTable):
    # Filtering
    def apply_text_filter(self, text: str) -> None
    def apply_column_filter(self, column: int, values: List) -> None
    def clear_filters(self) -> None
    
    # Signals
    filter_changed = pyqtSignal(dict)  # Current filters
```

#### Component Communication Interface
```python
class ComponentBus:
    # Event system for component communication
    def emit_event(self, event_type: str, data: dict) -> None
    def subscribe(self, event_type: str, callback: callable) -> None
    def unsubscribe(self, event_type: str, callback: callable) -> None
```

### 9. State Management Strategy

#### Centralized State Management
```python
class TabState:
    def __init__(self):
        self.videos: List[VideoInfo] = []
        self.selected_items: Set[int] = set()
        self.filters: Dict[str, Any] = {}
        self.sort_config: SortConfig = SortConfig()
        
    # State change events
    state_changed = pyqtSignal(str, object)  # field_name, new_value
```

#### State Synchronization
```python
class StateSynchronizer:
    def __init__(self, tabs: List[Widget]):
        self.tabs = tabs
        self.shared_state = SharedState()
        
    def sync_language_change(self, new_language: str) -> None
    def sync_theme_change(self, new_theme: Theme) -> None
    def sync_config_change(self, key: str, value: Any) -> None
```

### 10. Resolution Strategy

#### Phase 1: Extract Helper Classes (Low Risk)
1. **LanguageSupport Mixin** - Standardize language access
2. **ThemeSupport Mixin** - Standardize theme handling
3. **TooltipSupport Mixin** - Common tooltip functionality

#### Phase 2: Create Shared Services (Medium Risk)
1. **DownloaderService** - Centralized download management
2. **NetworkService** - Shared network operations
3. **ConfigService** - Centralized configuration

#### Phase 3: Component Extraction (High Risk)
1. **VideoTable Base Class** - Core table functionality
2. **FilterableVideoTable** - Extended with filtering
3. **Event System** - Replace direct parent references

### 11. Migration Path

#### Step 1: Service Layer Creation
```python
# Create service interfaces
class DownloaderService(QObject):
    info_received = pyqtSignal(str, object)  # url, video_info
    progress_updated = pyqtSignal(str, int, str)  # url, progress, speed
    download_finished = pyqtSignal(str, bool, str)  # url, success, path

class LanguageService(QObject):
    language_changed = pyqtSignal(str)  # new_language
    
    def tr(self, key: str) -> str
    def set_language(self, language: str) -> None
```

#### Step 2: Component Interface Definition
```python
class VideoTableComponent(QWidget):
    def __init__(self, config: TableConfig, parent=None):
        self.config = config
        self.data_model = VideoTableModel()
        self.setup_ui()
        
    def set_data_source(self, source: DataSource) -> None
    def get_selected_items(self) -> List[Any]
```

#### Step 3: Gradual Migration
1. Replace helper methods with mixins
2. Introduce service layer
3. Extract components one by one
4. Update parent tabs to use components

## Summary

The dependency analysis reveals significant coupling between components, primarily through:
- Direct parent window references
- Shared language/theme management
- Direct database access
- Embedded download functionality

The resolution strategy focuses on introducing service layers and event-driven communication to reduce coupling while maintaining functionality. 