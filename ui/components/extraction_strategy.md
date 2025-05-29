# Component Extraction Strategy - Task 15.3

## Overview
This document outlines the detailed plan for extracting components from the large UI files with minimal disruption to the application.

## Extraction Phases

### Phase 1: Low-Risk Mixins (1-2 days)
**Risk Level**: ⭐ Low
**Dependencies**: Minimal external dependencies

#### 1.1 LanguageSupport Mixin
**Source Code Locations:**
- `downloaded_videos_tab.py`: lines 94-100 (`tr_()` method)
- `video_info_tab.py`: lines 1202-1207 (`tr_()` method)
- Both files: `update_language()` methods

**Extraction Plan:**
```python
# ui/components/mixins/language_support.py
class LanguageSupport:
    """Mixin providing standardized language management"""
    
    def init_language_support(self, lang_manager=None):
        self._lang_manager = lang_manager
        
    def tr_(self, key: str) -> str:
        if hasattr(self, '_lang_manager') and self._lang_manager:
            return self._lang_manager.tr(key)
        return key
        
    def update_language(self):
        # To be implemented by subclasses
        raise NotImplementedError
```

**Migration Steps:**
1. Create mixin class
2. Update both tabs to inherit from mixin
3. Remove duplicate `tr_()` methods
4. Test language switching functionality

#### 1.2 ThemeSupport Mixin
**Source Code Locations:**
- `downloaded_videos_tab.py`: lines 1814-1991 (`apply_theme_colors()`)
- `video_info_tab.py`: lines 1272-1379 (`apply_theme_colors()`)

**Extraction Plan:**
```python
# ui/components/mixins/theme_support.py
class ThemeSupport:
    """Mixin providing standardized theme management"""
    
    def apply_theme_colors(self, theme):
        # Extract common theme application logic
        self._apply_base_theme(theme)
        self._apply_component_theme(theme)
        
    def _apply_base_theme(self, theme):
        # Common theme elements
        pass
        
    def _apply_component_theme(self, theme):
        # Override in subclasses for specific components
        pass
```

#### 1.3 TooltipSupport Mixin
**Source Code Locations:**
- `downloaded_videos_tab.py`: lines 100-114 (`format_tooltip_text()`)
- `video_info_tab.py`: lines 1208-1222 (`format_tooltip_text()`)
- Both files: `show_full_text_tooltip()` methods

**Extraction Plan:**
```python
# ui/components/mixins/tooltip_support.py
class TooltipSupport:
    """Mixin providing tooltip formatting and display"""
    
    def format_tooltip_text(self, text: str) -> str:
        # Extract common tooltip formatting logic
        
    def show_full_text_tooltip(self, row: int, column: int):
        # Extract tooltip display logic
```

### Phase 2: Medium-Risk Widgets (3-4 days)
**Risk Level**: ⭐⭐ Medium
**Dependencies**: Moderate external dependencies, self-contained functionality

#### 2.1 ActionButtonGroup Widget
**Source Code Locations:**
- Both tabs have similar button groups: Select All, Delete Selected, Delete All
- `downloaded_videos_tab.py`: lines 248-278 (button creation in `init_ui()`)
- `video_info_tab.py`: lines 146-185 (button creation in `setup_ui()`)

**Extraction Plan:**
```python
# ui/components/widgets/action_button_group.py
class ActionButtonGroup(QWidget):
    """Reusable button group for common actions"""
    
    # Signals
    select_all_clicked = pyqtSignal()
    delete_selected_clicked = pyqtSignal()
    delete_all_clicked = pyqtSignal()
    
    def __init__(self, buttons_config: List[ButtonConfig], parent=None):
        self.buttons_config = buttons_config
        self.setup_ui()
        
    def setup_ui(self):
        # Create buttons based on config
        
    def update_button_states(self, state_dict: Dict[str, bool]):
        # Update button enabled/disabled states
```

#### 2.2 StatisticsWidget
**Source Code Locations:**
- `downloaded_videos_tab.py`: lines 1789-1813 (`update_statistics()`)
- Statistics display: lines 220-247 in `init_ui()`

**Extraction Plan:**
```python
# ui/components/widgets/statistics_widget.py
class StatisticsWidget(QWidget):
    """Widget for displaying video statistics"""
    
    def __init__(self, parent=None):
        self.setup_ui()
        
    def update_statistics(self, videos: List[VideoInfo]):
        # Extract statistics calculation and display
        
    def setup_ui(self):
        # Create statistics display layout
```

#### 2.3 ThumbnailWidget
**Source Code Locations:**
- `downloaded_videos_tab.py`: lines 1585-1632 (`check_and_update_thumbnails()`)
- `video_info_tab.py`: thumbnail handling in network_manager

**Extraction Plan:**
```python
# ui/components/widgets/thumbnail_widget.py
class ThumbnailWidget(QLabel):
    """Widget for displaying and managing video thumbnails"""
    
    thumbnail_clicked = pyqtSignal(str)  # URL or path
    
    def __init__(self, parent=None):
        self.network_manager = QNetworkAccessManager()
        self.setup_ui()
        
    def load_thumbnail(self, url: str):
        # Load thumbnail from URL
        
    def set_thumbnail(self, pixmap: QPixmap):
        # Set thumbnail image
```

#### 2.4 ProgressTracker Widget
**Source Code Locations:**
- `video_info_tab.py`: progress handling in `handle_progress()` method
- Progress bars in table cells

**Extraction Plan:**
```python
# ui/components/widgets/progress_tracker.py
class ProgressTracker(QWidget):
    """Widget for tracking download progress"""
    
    def __init__(self, parent=None):
        self.progress_bar = QProgressBar()
        self.speed_label = QLabel()
        self.setup_ui()
        
    def update_progress(self, progress: int, speed: str):
        # Update progress display
```

### Phase 3: High-Risk Core Components (5-7 days)
**Risk Level**: ⭐⭐⭐ High
**Dependencies**: Complex functionality, many external dependencies

#### 3.1 VideoTable Base Component
**Source Code Locations:**
- `downloaded_videos_tab.py`: lines 280-424 (`create_downloads_table()`)
- `video_info_tab.py`: lines 356-418 (`create_video_table()`)

**Extraction Plan:**
```python
# ui/components/tables/video_table.py
class VideoTable(QTableWidget):
    """Base video table with common functionality"""
    
    # Signals
    selection_changed = pyqtSignal(list)
    item_action_requested = pyqtSignal(str, object)
    
    def __init__(self, config: TableConfig, parent=None):
        self.config = config
        self.setup_table()
        
    def setup_table(self):
        # Common table setup
        
    def set_data(self, videos: List[VideoInfo]):
        # Populate table with video data
        
    def get_selected_items(self) -> List[VideoInfo]:
        # Get currently selected items
```

#### 3.2 FilterableVideoTable Component
**Source Code Locations:**
- `downloaded_videos_tab.py`: extensive filtering logic
  - lines 721-827 (`filter_videos()`)
  - lines 3357-3385 (`apply_column_filter()`)
  - lines 3195-3219 (`show_header_context_menu()`)

**Extraction Plan:**
```python
# ui/components/tables/filterable_video_table.py
class FilterableVideoTable(VideoTable):
    """Video table with filtering capabilities"""
    
    # Signals
    filter_changed = pyqtSignal(dict)
    
    def __init__(self, config: TableConfig, parent=None):
        super().__init__(config, parent)
        self.active_filters = {}
        self.setup_filtering()
        
    def setup_filtering(self):
        # Setup filter UI and logic
        
    def apply_text_filter(self, text: str):
        # Apply text search filter
        
    def apply_column_filter(self, column: int, values: List):
        # Apply column-specific filter
```

## Extraction Order and Dependencies

### Week 1: Phase 1 - Mixins
```
Day 1-2: LanguageSupport + ThemeSupport
Day 3: TooltipSupport + Testing
```

### Week 2: Phase 2 - Widgets  
```
Day 1: ActionButtonGroup
Day 2: StatisticsWidget
Day 3: ThumbnailWidget
Day 4: ProgressTracker + Integration Testing
```

### Week 3: Phase 3 - Core Tables
```
Day 1-3: VideoTable base class
Day 4-5: FilterableVideoTable
Day 6-7: Integration and testing
```

## Risk Mitigation Strategies

### Low-Risk Mitigation (Phase 1)
- **Backup Strategy**: Create backup copies before modification
- **Gradual Replacement**: Replace one method at a time
- **Fallback Plan**: Keep original methods as deprecated until fully tested

### Medium-Risk Mitigation (Phase 2)  
- **Interface Compatibility**: Ensure new components have same public interface
- **Signal Compatibility**: Maintain existing signal names and signatures
- **Incremental Integration**: Test each widget individually before full integration

### High-Risk Mitigation (Phase 3)
- **Feature Flags**: Use configuration to toggle between old/new implementations
- **Parallel Implementation**: Keep old table code until new version is fully tested
- **Comprehensive Testing**: Unit tests, integration tests, and manual testing
- **Rollback Plan**: Quick rollback to original implementation if issues arise

## Testing Strategy

### Unit Testing
```python
# Example test structure
class TestLanguageSupport(unittest.TestCase):
    def test_tr_method(self):
        # Test translation functionality
        
    def test_fallback_behavior(self):
        # Test behavior when no language manager
```

### Integration Testing
```python
class TestComponentIntegration(unittest.TestCase):
    def test_mixin_combination(self):
        # Test multiple mixins working together
        
    def test_widget_in_tab(self):
        # Test widgets working in actual tabs
```

### Manual Testing Checklist
- [ ] Language switching works correctly
- [ ] Theme changes apply properly  
- [ ] Button states update correctly
- [ ] Table functionality unchanged
- [ ] Performance not degraded

## File Organization

### Directory Structure
```
ui/components/
├── __init__.py
├── mixins/
│   ├── __init__.py
│   ├── language_support.py
│   ├── theme_support.py
│   └── tooltip_support.py
├── widgets/
│   ├── __init__.py
│   ├── action_button_group.py
│   ├── statistics_widget.py
│   ├── thumbnail_widget.py
│   └── progress_tracker.py
├── tables/
│   ├── __init__.py
│   ├── video_table.py
│   └── filterable_video_table.py
├── dialogs/
│   ├── __init__.py
│   ├── filter_popup.py
│   ├── copy_dialog.py
│   └── confirmation_dialog.py
└── common/
    ├── __init__.py
    ├── interfaces.py
    ├── events.py
    └── models.py
```

## Configuration and Interfaces

### Component Configuration
```python
# ui/components/common/models.py
@dataclass
class TableConfig:
    columns: List[ColumnConfig]
    sortable: bool = True
    filterable: bool = False
    multi_select: bool = True

@dataclass  
class ColumnConfig:
    index: int
    name: str
    width: int
    resizable: bool = True
    sortable: bool = True
```

### Event System
```python
# ui/components/common/events.py
class ComponentEvent:
    def __init__(self, event_type: str, data: dict):
        self.event_type = event_type
        self.data = data
        self.timestamp = datetime.now()

class ComponentBus(QObject):
    event_emitted = pyqtSignal(ComponentEvent)
    
    def emit_event(self, event_type: str, data: dict):
        event = ComponentEvent(event_type, data)
        self.event_emitted.emit(event)
```

## Performance Considerations

### Memory Management
- Use weak references where appropriate
- Proper cleanup in component destructors
- Avoid memory leaks in signal/slot connections

### Rendering Performance
- Lazy loading for heavy components
- Efficient table updates (update only changed rows)
- Optimize thumbnail loading

### Startup Performance
- Lazy initialization of components
- Async loading where possible
- Minimal startup dependencies

## Success Criteria

### Phase 1 Success
- [ ] All mixins extracted and working
- [ ] No regression in language/theme functionality
- [ ] Code duplication reduced by 30%

### Phase 2 Success  
- [ ] All widgets extracted and reusable
- [ ] UI responsiveness maintained
- [ ] Component isolation achieved

### Phase 3 Success
- [ ] Table components fully extracted
- [ ] Original functionality preserved
- [ ] Code maintainability improved
- [ ] Components easily testable

## Rollback Strategy

### Emergency Rollback
1. **Git Reset**: Revert to last known good commit
2. **File Restore**: Restore original files from backup
3. **Configuration Reset**: Reset any configuration changes

### Partial Rollback
1. **Component Disabling**: Use feature flags to disable new components
2. **Method Restoration**: Restore original methods alongside new ones
3. **Gradual Reversion**: Remove components one by one if needed

## Documentation Requirements

### Component Documentation
- Purpose and usage examples
- Public API documentation  
- Signal/slot documentation
- Configuration options

### Migration Guide
- Step-by-step migration instructions
- Before/after code examples
- Common issues and solutions
- Performance comparison

This extraction strategy provides a comprehensive plan for breaking down the large UI files while minimizing risk and maintaining application functionality. 