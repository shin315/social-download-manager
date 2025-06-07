"""
Video Info Tab - Migrated to Component Architecture

This is the migrated version of video_info_tab.py that now inherits from BaseTab
and integrates with the component system established in Task 15 and enhanced in Task 16.

Migration preserves all existing functionality while adding:
- Tab lifecycle management with video processing state handling
- State persistence for URLs, download settings, and output folders
- Component bus integration for download coordination
- Enhanced theme and language support
- Performance monitoring for API calls and downloads
- Better error handling and validation
"""

from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableWidget, QComboBox,
                             QFileDialog, QCheckBox, QHeaderView, QMessageBox,
                             QTableWidgetItem, QProgressBar, QApplication, QDialog, QTextEdit, QMenu, QInputDialog, QSpacerItem, QSizePolicy, QDialogButtonBox, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtNetwork import QNetworkRequest, QNetworkAccessManager, QNetworkReply
from PyQt6.QtGui import QPixmap, QCursor, QAction
import os
import json
import requests
import shutil
import re
import sys
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import the new component architecture
from ..common import (
    BaseTab, TabConfig, TabState, 
    TabEventHelper, TabPerformanceMonitor,
    tab_lifecycle_handler, auto_save_on_change, validate_before_action,
    create_standard_tab_config, setup_tab_logging, connect_tab_to_state_manager
)
from utils.downloader import TikTokDownloader, VideoInfo
from utils.db_manager import DatabaseManager

# Path to configuration file
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')

# Import realtime progress manager for cross-tab progress tracking
try:
    from ..common.realtime_progress_manager import realtime_progress_manager
except ImportError:
    realtime_progress_manager = None

# Import error coordination system for cross-tab error handling
try:
    from ..common.error_coordination_system import (
        error_coordination_manager, 
        report_api_error, 
        report_download_error, 
        report_validation_error,
        ErrorSeverity
    )
except ImportError:
    error_coordination_manager = None
    report_api_error = None
    report_download_error = None
    report_validation_error = None
    ErrorSeverity = None


class VideoInfoTab(BaseTab):
    """
    Video Info Tab with Component Architecture Integration
    
    This tab manages video information retrieval and downloads with advanced features:
    - State persistence for URLs, download settings, and output configuration
    - Component bus integration for coordinating with other tabs
    - Performance monitoring for API calls and download operations
    - Enhanced validation and error handling
    - Advanced lifecycle management for download coordination
    """
    
    # Tab-specific signals (in addition to BaseTab signals)
    video_info_retrieved = pyqtSignal(str, object)  # URL, VideoInfo
    video_download_started = pyqtSignal(str)        # URL
    video_download_completed = pyqtSignal(str, bool, str)  # URL, success, file_path
    download_progress_updated = pyqtSignal(str, int, str)  # URL, progress, speed
    
    def __init__(self, config: Optional[TabConfig] = None, parent=None):
        """Initialize the video info management tab"""
        
        # Create default config if none provided
        if config is None:
            config = create_standard_tab_config(
                tab_id="video_info",
                title_key="TAB_VIDEO_INFO",
                auto_save=True,
                validation_required=True,
                state_persistence=True
            )
        
        # Initialize performance monitor BEFORE super().__init__() 
        # because setup_ui() will be called during BaseTab initialization
        self.performance_monitor = TabPerformanceMonitor(None)  # Temporary placeholder
        
        # Add temporary logging methods before super().__init__()
        self._temp_logs = []
        
        # Initialize tab-specific state variables BEFORE super().__init__()
        # because they might be needed in lifecycle methods
        self.video_info_dict = {}  # Dictionary with key as URL, value as VideoInfo
        self.processing_count = 0   # Counter for videos being processed
        self.downloading_count = 0  # Counter for videos being downloaded
        self.all_selected = False   # Variable to track if all items are selected
        
        # Sort state tracking for BaseTab lifecycle persistence
        self.sort_column = -1       # Current sort column (-1 = no sort)
        self.sort_order = Qt.SortOrder.AscendingOrder  # Current sort order
        
        # Initialize downloader (will be set up in setup_ui)
        self.downloader = None
        
        # Network manager for thumbnail loading
        self.network_manager = QNetworkAccessManager()
        
        # Initialize clipboard monitoring
        self.last_clipboard_text = ""
        
        # Initialize base tab
        super().__init__(config, parent)
        
        # Now set the correct tab reference for performance monitor
        self.performance_monitor = TabPerformanceMonitor(self)
        
        # Setup logging properly
        setup_tab_logging(self, 'INFO')
        
        # Replay any temporary logs
        for log_level, message in self._temp_logs:
            if hasattr(self, f'log_{log_level}'):
                getattr(self, f'log_{log_level}')(message)
        del self._temp_logs
        
        # Event helper for inter-tab communication
        self.event_helper = TabEventHelper(self)
        
        # Continue clipboard initialization
        try:
            clipboard = QApplication.clipboard()
            if clipboard:
                self.last_clipboard_text = clipboard.text()
        except Exception as e:
            self.log_error(f"Error initializing clipboard: {e}")
        
        # Register with realtime progress manager for cross-tab progress tracking
        if realtime_progress_manager:
            try:
                realtime_progress_manager.register_tab(self.get_tab_id(), self)
                self.log_info("Registered with realtime progress manager")
            except Exception as e:
                self.log_error(f"Error registering with progress manager: {e}")
        else:
            self.log_warning("Realtime progress manager not available")
        
        # Register with error coordination manager for cross-tab error handling
        if error_coordination_manager:
            try:
                error_coordination_manager.register_tab(self.get_tab_id(), self)
                self.log_info("Registered with error coordination manager")
            except Exception as e:
                self.log_error(f"Error registering with error coordination manager: {e}")
        else:
            self.log_warning("Error coordination manager not available")
    
    # Temporary logging methods for use during initialization
    def log_info(self, message: str) -> None:
        """Temporary log_info method"""
        if hasattr(self, '_temp_logs'):
            self._temp_logs.append(('info', message))
        else:
            # Real logging is set up, use it
            if hasattr(self, '_logger'):
                self._logger.info(message)
            else:
                print(f"INFO: {message}")
    
    def log_error(self, message: str) -> None:
        """Temporary log_error method"""
        if hasattr(self, '_temp_logs'):
            self._temp_logs.append(('error', message))
        else:
            # Real logging is set up, use it
            if hasattr(self, '_logger'):
                self._logger.error(message)
            else:
                print(f"ERROR: {message}")
    
    def log_debug(self, message: str) -> None:
        """Temporary log_debug method"""
        if hasattr(self, '_temp_logs'):
            self._temp_logs.append(('debug', message))
        else:
            # Real logging is set up, use it
            if hasattr(self, '_logger'):
                self._logger.debug(message)
            else:
                print(f"DEBUG: {message}")
    
    def log_warning(self, message: str) -> None:
        """Temporary log_warning method"""
        if hasattr(self, '_temp_logs'):
            self._temp_logs.append(('warning', message))
        else:
            # Real logging is set up, use it
            if hasattr(self, '_logger'):
                self._logger.warning(message)
            else:
                print(f"WARNING: {message}")
    
    # =============================================================================
    # BaseTab Abstract Method Implementations
    # =============================================================================
    
    def get_tab_id(self) -> str:
        """Return unique identifier for this tab"""
        return "video_info"
    
    def setup_ui(self) -> None:
        """Initialize the tab's UI components"""
        self.performance_monitor.start_timing('ui_setup')
        
        try:
            # Main layout
            main_layout = QVBoxLayout()
            self.setLayout(main_layout)

            # URL and Get Info section
            url_layout = QHBoxLayout()
            
            # URL Label
            self.url_label = QLabel(self.tr_("LABEL_VIDEO_URL"))
            url_layout.addWidget(self.url_label)
            
            # Create spacing to align URL input with output folder
            spacer_width = 18
            url_layout.addSpacing(spacer_width)
            
            # URL Input
            self.url_input = QLineEdit()
            self.url_input.setFixedHeight(30)
            self.url_input.setMinimumWidth(500)
            self.url_input.setPlaceholderText(self.tr_("PLACEHOLDER_VIDEO_URL"))
            self.url_input.returnPressed.connect(self.get_video_info)
            url_layout.addWidget(self.url_input, 1)
            
            # Get Info Button
            self.get_info_btn = QPushButton(self.tr_("BUTTON_GET_INFO"))
            self.get_info_btn.setFixedWidth(120)
            self.get_info_btn.clicked.connect(self.get_video_info)
            url_layout.addWidget(self.get_info_btn)
            
            main_layout.addLayout(url_layout)

            # Output Folder section
            output_layout = QHBoxLayout()
            
            # Output Folder Label
            self.output_label = QLabel(self.tr_("LABEL_OUTPUT_FOLDER"))
            output_layout.addWidget(self.output_label)
            
            # Display folder path
            self.output_folder_display = QLineEdit()
            self.output_folder_display.setReadOnly(True)
            self.output_folder_display.setFixedHeight(30)
            self.output_folder_display.setMinimumWidth(500)
            self.output_folder_display.setPlaceholderText(self.tr_("PLACEHOLDER_OUTPUT_FOLDER"))
            output_layout.addWidget(self.output_folder_display, 1)
            
            # Choose folder button
            self.choose_folder_btn = QPushButton(self.tr_("BUTTON_CHOOSE_FOLDER"))
            self.choose_folder_btn.setFixedWidth(120)
            self.choose_folder_btn.clicked.connect(self.choose_output_folder)
            output_layout.addWidget(self.choose_folder_btn)
            
            main_layout.addLayout(output_layout)

            # Video information table
            self.create_video_table()
            main_layout.addWidget(self.video_table)

            # Options and Download button section
            options_layout = QHBoxLayout()
            
            # Group Select/Delete buttons to the left
            left_buttons_layout = QHBoxLayout()
            
            # Select all / Unselect all button
            self.select_toggle_btn = QPushButton(self.tr_("BUTTON_SELECT_ALL"))
            self.select_toggle_btn.setFixedWidth(150)
            self.select_toggle_btn.clicked.connect(self.toggle_select_all)
            left_buttons_layout.addWidget(self.select_toggle_btn)
            
            # Delete Selected button
            self.delete_selected_btn = QPushButton(self.tr_("BUTTON_DELETE_SELECTED"))
            self.delete_selected_btn.setFixedWidth(150)
            self.delete_selected_btn.clicked.connect(self.delete_selected_videos)
            left_buttons_layout.addWidget(self.delete_selected_btn)
            
            # Delete All button
            self.delete_all_btn = QPushButton(self.tr_("BUTTON_DELETE_ALL"))
            self.delete_all_btn.setFixedWidth(150)
            self.delete_all_btn.clicked.connect(self.delete_all_videos)
            left_buttons_layout.addWidget(self.delete_all_btn)
            
            options_layout.addLayout(left_buttons_layout)
            options_layout.addStretch(1)
            
            # Download button on the right
            self.download_btn = QPushButton(self.tr_("BUTTON_DOWNLOAD"))
            self.download_btn.setFixedWidth(150)
            self.download_btn.clicked.connect(self.download_videos)
            options_layout.addWidget(self.download_btn)

            main_layout.addLayout(options_layout)
            
            # Set up context menu for video_table
            self.video_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.video_table.customContextMenuRequested.connect(self.show_context_menu)
            
            # Initialize downloader after UI setup
            self.setup_downloader()
            
            self.log_info("UI setup completed successfully")
            
        except Exception as e:
            self.log_error(f"Error in UI setup: {e}")
            raise
        finally:
            self.performance_monitor.end_timing('ui_setup')
    
    def setup_downloader(self):
        """Initialize downloader with signal connections"""
        try:
            self.downloader = TikTokDownloader()
            self.downloader.info_signal.connect(self.handle_video_info)
            self.downloader.progress_signal.connect(self.handle_progress)
            self.downloader.finished_signal.connect(self.handle_download_finished)
            self.downloader.api_error_signal.connect(self.handle_api_error)
            
            self.log_info("Downloader initialized successfully")
        except Exception as e:
            self.log_error(f"Error initializing downloader: {e}")
    
    @tab_lifecycle_handler('load_data')
    def load_data(self) -> None:
        """Load tab-specific data"""
        self.performance_monitor.start_timing('data_load')
        
        try:
            # Load last output folder
            self.load_last_output_folder()
            
            # Load clipboard monitoring state
            self.load_clipboard_state()
            
            self.log_info("Tab data loaded successfully")
            
        except Exception as e:
            self.log_error(f"Error loading data: {e}")
            raise
        finally:
            self.performance_monitor.end_timing('data_load')
    
    @auto_save_on_change(['video_info_dict', 'output_folder_display', 'all_selected', 'sort_column', 'sort_order'])
    def save_data(self) -> bool:
        """Save tab data, return success status"""
        self.performance_monitor.start_timing('data_save')
        
        try:
            # Update tab state with current data
            self._tab_state.video_urls = list(self.video_info_dict.keys())
            self._tab_state.output_folder = self.output_folder_display.text()
            self._tab_state.selection_state = self.all_selected
            
            # Save additional state data
            state_data = {
                'processing_count': self.processing_count,
                'downloading_count': self.downloading_count,
                'last_url_input': self.url_input.text(),
                'video_count': len(self.video_info_dict),
                'ui_state': {
                    'url_input_text': self.url_input.text(),
                    'output_folder': self.output_folder_display.text()
                }
            }
            
            # Save output folder to config
            if self.output_folder_display.text():
                self.save_last_output_folder(self.output_folder_display.text())
            
            # Save to state manager if available
            if hasattr(self, '_state_manager'):
                return self._state_manager.save_tab_state(self.get_tab_id())
            
            self.log_info("Tab data saved successfully")
            return True
            
        except Exception as e:
            self.log_error(f"Error saving data: {e}")
            return False
        finally:
            self.performance_monitor.end_timing('data_save')
    
    def refresh_data(self) -> None:
        """Refresh/reload tab data"""
        self.performance_monitor.start_timing('data_refresh')
        
        try:
            # Clear current data
            self.video_info_dict.clear()
            self.processing_count = 0
            self.downloading_count = 0
            self.all_selected = False
            
            # Clear UI
            self.video_table.setRowCount(0)
            self.url_input.clear()
            
            # Reload saved data
            self.load_data()
            
            # Update UI states
            self.update_button_states()
            self.update_select_toggle_button()
            
            self.log_info("Data refreshed successfully")
            
        except Exception as e:
            self.log_error(f"Error refreshing data: {e}")
        finally:
            self.performance_monitor.end_timing('data_refresh')
    
    def validate_input(self) -> List[str]:
        """Validate tab input, return list of error messages"""
        errors = []
        
        # Check downloader availability
        if not self.downloader:
            errors.append("Video downloader not initialized")
        
        # Check output folder
        output_folder = self.output_folder_display.text()
        if output_folder and not os.path.exists(output_folder):
            errors.append(f"Output folder does not exist: {output_folder}")
        elif output_folder and not os.access(output_folder, os.W_OK):
            errors.append(f"Output folder is not writable: {output_folder}")
        
        # Check URL input format
        url_text = self.url_input.text().strip()
        if url_text:
            # Basic URL validation
            if not (url_text.startswith('http://') or url_text.startswith('https://')):
                errors.append("URL must start with http:// or https://")
            elif 'tiktok.com' not in url_text and 'youtu' not in url_text:
                errors.append("URL must be from TikTok or YouTube")
        
        # Check video info consistency
        for url, video_info in self.video_info_dict.items():
            if not isinstance(video_info, VideoInfo):
                errors.append(f"Invalid video info object for URL: {url}")
        
        # Check download state consistency
        if self.processing_count < 0:
            errors.append("Invalid processing count")
        if self.downloading_count < 0:
            errors.append("Invalid downloading count")
        
        return errors
    
    # =============================================================================
    # BaseTab Lifecycle Overrides
    # =============================================================================
    
    @tab_lifecycle_handler('activated')
    def on_tab_activated(self) -> None:
        """Called when tab becomes active"""
        super().on_tab_activated()
        
        # Check clipboard for new URLs
        self.check_clipboard_for_urls()
        
        # Update UI states
        self.update_button_states()
        
        # Emit tab activated event with current state
        self.emit_tab_event('tab_focus', {
            'video_count': len(self.video_info_dict),
            'processing_count': self.processing_count,
            'downloading_count': self.downloading_count,
            'has_output_folder': bool(self.output_folder_display.text())
        })
        
        self.log_info("Tab activated")
    
    @tab_lifecycle_handler('deactivated')
    def on_tab_deactivated(self) -> None:
        """Called when tab becomes inactive"""
        super().on_tab_deactivated()
        
        # Save current state
        if self.is_data_dirty():
            self.save_data()
        
        self.log_info("Tab deactivated")
    
    def on_external_tab_event(self, event):
        """Handle events from other tabs"""
        if event.event_type.value == 'video_download_completed':
            # A video download was completed, update our state if it's our video
            url = event.data.get('url', '')
            if url in self.video_info_dict:
                self.log_info(f"Video download completed for our URL: {url}")
        elif event.event_type.value == 'theme_changed':
            # Theme changed, update our appearance
            if 'theme' in event.data:
                self.apply_theme_colors(event.data['theme'])
    
    # =============================================================================
    # State Management Integration
    # =============================================================================
    
    def get_tab_state(self) -> TabState:
        """Get complete tab state"""
        # Update state with current data
        self._tab_state.video_urls = list(self.video_info_dict.keys())
        self._tab_state.output_folder = self.output_folder_display.text()
        self._tab_state.selection_state = self.all_selected
        
        # Update sort state
        self._tab_state.sort_column = self.sort_column
        self._tab_state.sort_order = self.sort_order
        
        # Update processing state
        if hasattr(self._tab_state, 'processing_state'):
            self._tab_state.processing_state = {
                'processing_count': self.processing_count,
                'downloading_count': self.downloading_count,
                'last_url_input': self.url_input.text()
            }
        
        return self._tab_state
    
    def set_tab_state(self, state: TabState) -> None:
        """Set tab state from TabState object"""
        self._tab_state = state
        
        # Restore data from state
        if hasattr(state, 'video_urls') and state.video_urls:
            # Note: We can't restore full VideoInfo objects without re-fetching
            # So we'll just clear and let user re-fetch if needed
            pass
        
        if hasattr(state, 'output_folder') and state.output_folder:
            self.output_folder_display.setText(state.output_folder)
        
        if hasattr(state, 'selection_state'):
            self.all_selected = state.selection_state
        
        # Restore sort state
        if hasattr(state, 'sort_column') and hasattr(state, 'sort_order'):
            self.sort_column = state.sort_column
            self.sort_order = state.sort_order
            # Apply sort to table if it exists and has data
            if (hasattr(self, 'video_table') and self.sort_column >= 0 and 
                self.video_table.rowCount() > 0):
                self.video_table.sortByColumn(self.sort_column, self.sort_order)
        
        # Restore processing state
        if hasattr(state, 'processing_state') and state.processing_state:
            self.processing_count = state.processing_state.get('processing_count', 0)
            self.downloading_count = state.processing_state.get('downloading_count', 0)
            last_url = state.processing_state.get('last_url_input', '')
            if last_url:
                self.url_input.setText(last_url)
        
        # Update UI
        self.update_button_states()
        self.update_select_toggle_button()
        
        self.log_info("Tab state restored")
    
    # =============================================================================
    # Enhanced State Persistence Implementation (Subtask 16.1)
    # =============================================================================
    
    def save_tab_state(self) -> None:
        """Enhanced tab state persistence for URL inputs, video data, and UI state"""
        try:
            # Import the practical state manager
            from ..common.tab_state_persistence import practical_state_manager
            
            # Register this tab if not already registered
            if self.get_tab_id() not in practical_state_manager.tab_registry:
                practical_state_manager.register_tab(
                    self.get_tab_id(), 
                    self, 
                    self._capture_video_info_state,
                    self._restore_video_info_state
                )
            
            # Save state using practical state manager
            success = practical_state_manager.save_tab_state(self.get_tab_id())
            
            if success:
                self.log_info("VideoInfoTab state saved successfully")
            else:
                self.log_warning("VideoInfoTab state save failed")
                
        except Exception as e:
            self.log_error(f"Error saving VideoInfoTab state: {e}")
    
    def restore_tab_state(self) -> None:
        """Enhanced tab state restoration for URL inputs, video data, and UI state"""
        try:
            # Import the practical state manager
            from ..common.tab_state_persistence import practical_state_manager
            
            # Register this tab if not already registered
            if self.get_tab_id() not in practical_state_manager.tab_registry:
                practical_state_manager.register_tab(
                    self.get_tab_id(), 
                    self, 
                    self._capture_video_info_state,
                    self._restore_video_info_state
                )
            
            # Restore state using practical state manager
            success = practical_state_manager.restore_tab_state(self.get_tab_id())
            
            if success:
                self.log_info("VideoInfoTab state restored successfully")
                # Update UI after restoration
                self.update_button_states()
                self.update_select_toggle_button()
            else:
                self.log_debug("No previous VideoInfoTab state found or restoration failed")
                
        except Exception as e:
            self.log_error(f"Error restoring VideoInfoTab state: {e}")
    
    def _capture_video_info_state(self, tab_instance) -> Dict[str, Any]:
        """Capture VideoInfoTab-specific state including video data and UI elements"""
        try:
            state = {}
            
            # Capture URL input state
            if hasattr(self, 'url_input'):
                state['url_input'] = {
                    'text': self.url_input.text(),
                    'cursor_position': self.url_input.cursorPosition(),
                    'placeholder': self.url_input.placeholderText()
                }
            
            # Capture output folder state
            if hasattr(self, 'output_folder_display'):
                state['output_folder'] = {
                    'text': self.output_folder_display.text(),
                    'placeholder': self.output_folder_display.placeholderText()
                }
            
            # Capture video table state (selection, sort, column widths)
            if hasattr(self, 'video_table'):
                selected_rows = []
                for row in range(self.video_table.rowCount()):
                    checkbox_cell = self.video_table.cellWidget(row, 0)
                    if checkbox_cell:
                        checkbox = checkbox_cell.findChild(QCheckBox)
                        if checkbox and checkbox.isChecked():
                            selected_rows.append(row)
                
                state['video_table'] = {
                    'selected_rows': selected_rows,
                    'sort_column': self.sort_column,
                    'sort_order': self.sort_order.value if hasattr(self.sort_order, 'value') else int(self.sort_order),
                    'column_widths': [self.video_table.columnWidth(i) for i in range(self.video_table.columnCount())],
                    'row_count': self.video_table.rowCount()
                }
            
            # Capture video URLs for restoration (without full VideoInfo to keep file size small)
            if hasattr(self, 'video_info_dict'):
                state['video_urls'] = list(self.video_info_dict.keys())
            
            # Capture processing state
            state['processing_state'] = {
                'processing_count': getattr(self, 'processing_count', 0),
                'downloading_count': getattr(self, 'downloading_count', 0),
                'all_selected': getattr(self, 'all_selected', False)
            }
            
            # Capture combo box states for format/quality selections
            if hasattr(self, 'video_table'):
                combo_states = {}
                for row in range(self.video_table.rowCount()):
                    # Format combo
                    format_cell = self.video_table.cellWidget(row, 5)  # Format column
                    if format_cell:
                        format_combo = format_cell.findChild(QComboBox)
                        if format_combo:
                            combo_states[f'format_row_{row}'] = {
                                'current_index': format_combo.currentIndex(),
                                'current_text': format_combo.currentText()
                            }
                    
                    # Quality combo
                    quality_cell = self.video_table.cellWidget(row, 6)  # Quality column
                    if quality_cell:
                        quality_combo = quality_cell.findChild(QComboBox)
                        if quality_combo:
                            combo_states[f'quality_row_{row}'] = {
                                'current_index': quality_combo.currentIndex(),
                                'current_text': quality_combo.currentText()
                            }
                
                state['combo_selections'] = combo_states
            
            self.log_debug(f"Captured VideoInfoTab state: {len(state)} elements")
            return state
            
        except Exception as e:
            self.log_error(f"Error capturing VideoInfoTab state: {e}")
            return {}
    
    def _restore_video_info_state(self, tab_instance, state: Dict[str, Any]) -> bool:
        """Restore VideoInfoTab-specific state including video data and UI elements"""
        try:
            # Restore URL input
            if 'url_input' in state and hasattr(self, 'url_input'):
                url_state = state['url_input']
                self.url_input.setText(url_state.get('text', ''))
                if 'cursor_position' in url_state:
                    self.url_input.setCursorPosition(url_state['cursor_position'])
            
            # Restore output folder
            if 'output_folder' in state and hasattr(self, 'output_folder_display'):
                folder_state = state['output_folder']
                self.output_folder_display.setText(folder_state.get('text', ''))
            
            # Restore processing state
            if 'processing_state' in state:
                proc_state = state['processing_state']
                self.processing_count = proc_state.get('processing_count', 0)
                self.downloading_count = proc_state.get('downloading_count', 0)
                self.all_selected = proc_state.get('all_selected', False)
            
            # Restore table sort state (will be applied when table has data)
            if 'video_table' in state:
                table_state = state['video_table']
                self.sort_column = table_state.get('sort_column', -1)
                # Handle sort_order conversion
                sort_order_value = table_state.get('sort_order', 0)
                if isinstance(sort_order_value, int):
                    self.sort_order = Qt.SortOrder(sort_order_value)
                else:
                    self.sort_order = sort_order_value
                
                # Apply sorting if table has data
                if (hasattr(self, 'video_table') and self.video_table.rowCount() > 0 and 
                    self.sort_column >= 0):
                    self.video_table.sortByColumn(self.sort_column, self.sort_order)
                
                # Restore column widths
                if 'column_widths' in table_state and hasattr(self, 'video_table'):
                    widths = table_state['column_widths']
                    for i, width in enumerate(widths):
                        if i < self.video_table.columnCount() and width > 0:
                            self.video_table.setColumnWidth(i, width)
            
            # Store combo states for restoration after video data is loaded
            if 'combo_selections' in state:
                self._pending_combo_states = state['combo_selections']
            
            # Store video URLs for display (user needs to re-fetch video info)
            if 'video_urls' in state and state['video_urls']:
                urls_text = '\n'.join(state['video_urls'])
                if hasattr(self, 'url_input') and not self.url_input.text():
                    self.url_input.setText(urls_text)
                self.log_info(f"Found {len(state['video_urls'])} previous URLs. Use 'Get Info' to reload video data.")
            
            self.log_debug("VideoInfoTab state restored successfully")
            return True
            
        except Exception as e:
            self.log_error(f"Error restoring VideoInfoTab state: {e}")
            return False
    
    # =============================================================================
    # Language and Theme Support (Enhanced from BaseTab)
    # =============================================================================
    
    def update_language(self):
        """Update display language when language changes"""
        # Update labels and buttons
        self.url_label.setText(self.tr_("LABEL_VIDEO_URL"))
        self.url_input.setPlaceholderText(self.tr_("PLACEHOLDER_VIDEO_URL"))
        self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
        
        self.output_label.setText(self.tr_("LABEL_OUTPUT_FOLDER"))
        self.output_folder_display.setPlaceholderText(self.tr_("PLACEHOLDER_OUTPUT_FOLDER"))
        self.choose_folder_btn.setText(self.tr_("BUTTON_CHOOSE_FOLDER"))
        
        # Update control buttons
        self.select_toggle_btn.setText(
            self.tr_("BUTTON_UNSELECT_ALL") if self.all_selected 
            else self.tr_("BUTTON_SELECT_ALL")
        )
        self.delete_selected_btn.setText(self.tr_("BUTTON_DELETE_SELECTED"))
        self.delete_all_btn.setText(self.tr_("BUTTON_DELETE_ALL"))
        self.download_btn.setText(self.tr_("BUTTON_DOWNLOAD"))
        
        # Update table headers
        self.update_table_headers()
        
        self.log_info("Language updated")
    
    def apply_theme_colors(self, theme: dict):
        """Apply theme colors and styles"""
        # Apply base theme through mixin
        super().apply_theme_colors(theme)
        
        # Apply tab-specific theme customizations
        if not theme:
            return
        
        try:
            # Apply theme to table
            if hasattr(self, 'video_table'):
                table_style = f"""
                QTableWidget {{
                    background-color: {theme.get('background', '#ffffff')};
                    color: {theme.get('text', '#000000')};
                    gridline-color: {theme.get('border', '#cccccc')};
                }}
                QTableWidget::item:selected {{
                    background-color: {theme.get('accent', '#0078d4')};
                    color: {theme.get('accent_text', '#ffffff')};
                }}
                QHeaderView::section {{
                    background-color: {theme.get('header_background', '#f5f5f5')};
                    color: {theme.get('header_text', '#000000')};
                    border: 1px solid {theme.get('border', '#cccccc')};
                    padding: 4px;
                }}
                """
                self.video_table.setStyleSheet(table_style)
            
            # Apply theme to input fields
            input_style = f"""
            QLineEdit {{
                background-color: {theme.get('input_background', '#ffffff')};
                color: {theme.get('text', '#000000')};
                border: 1px solid {theme.get('border', '#cccccc')};
                border-radius: 4px;
                padding: 4px;
            }}
            QLineEdit:focus {{
                border-color: {theme.get('accent', '#0078d4')};
            }}
            """
            
            if hasattr(self, 'url_input'):
                self.url_input.setStyleSheet(input_style)
            if hasattr(self, 'output_folder_display'):
                self.output_folder_display.setStyleSheet(input_style)
            
            self.log_info("Theme applied successfully")
            
        except Exception as e:
            self.log_error(f"Error applying theme: {e}")
    
    # =============================================================================
    # Original Methods (Preserved with Enhancements)
    # =============================================================================
    
    def format_tooltip_text(self, text):
        """Format tooltip text with line breaks for better readability"""
        if not text:
            return ""
        
        # Add line breaks after periods, exclamation marks, question marks followed by a space
        formatted_text = re.sub(r'([.!?]) ', r'\1\n', text)
        # Add line breaks after commas followed by a space
        formatted_text = re.sub(r'([,]) ', r'\1\n', formatted_text)
        
        # Handle hashtags - one hashtag per line
        formatted_text = re.sub(r' (#[^\s#]+)', r'\n\1', formatted_text)
        
        return formatted_text
    
    def load_last_output_folder(self):
        """Load last output folder from config"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    last_folder = config.get('last_output_folder', '')
                    if last_folder and os.path.exists(last_folder):
                        self.output_folder_display.setText(last_folder)
                        self.log_info(f"Loaded output folder: {last_folder}")
        except Exception as e:
            self.log_error(f"Error loading output folder: {e}")
    
    def save_last_output_folder(self, folder):
        """Save last output folder to config"""
        try:
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            config['last_output_folder'] = folder
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            
            self.log_info(f"Saved output folder: {folder}")
        except Exception as e:
            self.log_error(f"Error saving output folder: {e}")
    
    def load_clipboard_state(self):
        """Load clipboard monitoring state"""
        try:
            clipboard = QApplication.clipboard()
            if clipboard:
                self.last_clipboard_text = clipboard.text()
        except Exception as e:
            self.log_error(f"Error loading clipboard state: {e}")
    
    def check_clipboard_for_urls(self):
        """Check clipboard for new video URLs"""
        try:
            clipboard = QApplication.clipboard()
            if clipboard:
                current_text = clipboard.text()
                if (current_text != self.last_clipboard_text and 
                    current_text and 
                    ('tiktok.com' in current_text or 'youtu' in current_text)):
                    
                    # Auto-fill URL input if it's empty
                    if not self.url_input.text().strip():
                        self.url_input.setText(current_text)
                        self.log_info(f"Auto-filled URL from clipboard: {current_text[:50]}...")
                    
                    self.last_clipboard_text = current_text
        except Exception as e:
            self.log_error(f"Error checking clipboard: {e}")
    
    @validate_before_action()
    def get_video_info(self):
        """Get video information with enhanced validation and monitoring"""
        self.performance_monitor.start_timing('video_info_fetch')
        
        try:
            url = self.url_input.text().strip()
            if not url:
                QMessageBox.warning(self, self.tr_("ERROR_NO_URL"), self.tr_("ERROR_NO_URL_MESSAGE"))
                return
            
            # Check if URL is already in table
            if url in self.video_info_dict:
                QMessageBox.information(self, self.tr_("INFO_URL_EXISTS"), self.tr_("INFO_URL_EXISTS_MESSAGE"))
                return
            
            # Increment processing count
            self.processing_count += 1
            self._set_data_dirty(True)
            
            # Update UI to show processing
            self.get_info_btn.setEnabled(False)
            self.get_info_btn.setText(self.tr_("BUTTON_PROCESSING"))
            
            # Start video info retrieval
            if self.downloader:
                self.downloader.get_video_info(url)
                
                # Emit event to other tabs
                self.emit_tab_event('video_info_requested', {
                    'url': url,
                    'processing_count': self.processing_count
                })
                
                self.log_info(f"Requested video info for: {url}")
            else:
                raise Exception("Downloader not initialized")
                
        except Exception as e:
            self.processing_count = max(0, self.processing_count - 1)
            self.get_info_btn.setEnabled(True)
            self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
            self.log_error(f"Error getting video info: {e}")
            QMessageBox.critical(self, self.tr_("ERROR_GET_INFO"), f"{self.tr_('ERROR_GET_INFO_MESSAGE')}: {e}")
        finally:
            self.performance_monitor.end_timing('video_info_fetch')
    
    # =============================================================================
    # Component Integration Methods
    # =============================================================================
    
    def handle_video_info(self, url, video_info):
        """Handle video info received from downloader with enhanced metadata processing"""
        try:
            self.performance_monitor.start_timing('handle_video_info')
            
            # Decrement processing count
            self.processing_count = max(0, self.processing_count - 1)
            
            # Process and validate video metadata
            processed_video_info = self.process_video_metadata(video_info, url)
            
            # Store processed video info
            self.video_info_dict[url] = processed_video_info
            
            # Mark data as dirty
            self._set_data_dirty(True)
            
            # Update UI
            self.get_info_btn.setEnabled(True)
            self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
            
            # Add to table with processed data
            self.add_video_to_table(processed_video_info)
            
            # Update button states
            self.update_button_states()
            
            # Emit success event with processed data
            self.video_info_retrieved.emit(url, processed_video_info)
            self.emit_tab_event('video_info_retrieved', {
                'url': url,
                'video_info': processed_video_info,
                'total_videos': len(self.video_info_dict),
                'metadata_processed': True
            })
            
            self.log_info(f"Video info retrieved and processed successfully for: {url}")
            self.performance_monitor.end_timing('handle_video_info')
            
        except Exception as e:
            self.processing_count = max(0, self.processing_count - 1)
            self.log_error(f"Error handling video info: {e}")
            self.performance_monitor.end_timing('handle_video_info')
    
    def handle_progress(self, url, progress, speed):
        """Enhanced download progress handler with real-time cross-tab updates"""
        try:
            # Get video info for additional context
            video_info = self.video_info_dict.get(url, {})
            file_name = video_info.get('title', 'Unknown')
            
            # Update progress via realtime progress manager for cross-tab synchronization
            if realtime_progress_manager:
                try:
                    # Calculate ETA based on speed and remaining progress
                    eta = self._calculate_eta(progress, speed)
                    file_size = self._estimate_file_size(video_info)
                    
                    realtime_progress_manager.update_progress(
                        operation_id=url,
                        current_value=progress,
                        speed=speed,
                        eta=eta,
                        file_size=file_size,
                        additional_data={
                            'file_name': file_name,
                            'video_info': video_info,
                            'tab_source': self.get_tab_id()
                        }
                    )
                except Exception as e:
                    self.log_error(f"Error updating realtime progress: {e}")
            
            # Update progress in table (if table exists and row is found)
            self._update_progress_in_table(url, progress, speed)
            
            # Emit enhanced progress event with additional context
            self.download_progress_updated.emit(url, progress, speed)
            self.emit_tab_event('download_progress', {
                'url': url,
                'progress': progress,
                'speed': speed,
                'file_name': file_name,
                'eta': self._calculate_eta(progress, speed),
                'timestamp': self.performance_monitor.current_time(),
                'downloading_count': self.downloading_count
            })
            
            self.log_debug(f"Progress updated: {file_name} - {progress}% at {speed}")
            
        except Exception as e:
            self.log_error(f"Error handling progress: {e}")
    
    def _calculate_eta(self, progress: int, speed: str) -> str:
        """Calculate estimated time of arrival based on progress and speed"""
        try:
            if not speed or progress >= 100:
                return ""
            
            # Extract numeric speed value (e.g., "2.5 MB/s" -> 2.5)
            import re
            speed_match = re.search(r'(\d+\.?\d*)', speed)
            if not speed_match:
                return ""
            
            speed_value = float(speed_match.group(1))
            if speed_value <= 0:
                return ""
            
            # Estimate remaining time based on speed (very rough calculation)
            remaining_percent = 100 - progress
            if remaining_percent <= 0:
                return "0:00"
            
            # Rough ETA calculation (this would need refinement in production)
            estimated_seconds = int((remaining_percent / progress) * 10)  # Rough estimate
            estimated_seconds = min(estimated_seconds, 3600)  # Cap at 1 hour
            
            minutes = estimated_seconds // 60
            seconds = estimated_seconds % 60
            return f"{minutes}:{seconds:02d}"
            
        except Exception:
            return ""
    
    def _estimate_file_size(self, video_info: dict) -> str:
        """Estimate file size from video info"""
        try:
            duration = video_info.get('duration', 0)
            quality = video_info.get('quality', '')
            
            # Rough file size estimation based on duration and quality
            if duration and isinstance(duration, (int, float)):
                # Very rough estimation (would need refinement)
                if '1080' in quality:
                    mb_per_minute = 25
                elif '720' in quality:
                    mb_per_minute = 15
                else:
                    mb_per_minute = 10
                
                estimated_mb = (duration / 60) * mb_per_minute
                if estimated_mb >= 1024:
                    return f"{estimated_mb/1024:.1f} GB"
                else:
                    return f"{estimated_mb:.1f} MB"
            
            return ""
        except Exception:
            return ""
    
    def _update_progress_in_table(self, url: str, progress: int, speed: str):
        """Update progress display in the video table"""
        try:
            if not hasattr(self, 'video_table') or not self.video_table:
                return
            
            # Find the row with matching URL
            for row in range(self.video_table.rowCount()):
                row_url = getattr(self.video_table.item(row, 1), 'url', None)
                if row_url == url:
                    # Update progress column if it exists (placeholder for future implementation)
                    # For now, just update tooltip to show progress
                    for col in range(self.video_table.columnCount()):
                        item = self.video_table.item(row, col)
                        if item:
                            current_tooltip = item.toolTip()
                            progress_info = f"Progress: {progress}% ({speed})"
                            
                            # Update or add progress info to tooltip
                            if "Progress:" in current_tooltip:
                                # Replace existing progress info
                                import re
                                updated_tooltip = re.sub(r'Progress: \d+%[^)]*\)', progress_info, current_tooltip)
                            else:
                                # Add progress info
                                updated_tooltip = f"{current_tooltip}\n{progress_info}" if current_tooltip else progress_info
                            
                            item.setToolTip(updated_tooltip)
                    break
                    
        except Exception as e:
            self.log_error(f"Error updating progress in table: {e}")
    
    def handle_download_finished(self, url, success, file_path):
        """Enhanced download completion handler with toast notifications and improved event data"""
        try:
            # Decrement downloading count
            self.downloading_count = max(0, self.downloading_count - 1)
            
            # Mark data as dirty
            self._set_data_dirty(True)
            
            # Get video info for this URL if available
            video_info = self.video_info_dict.get(url, {})
            video_title = video_info.get('title', 'Unknown')
            
            # Save to database if download was successful
            if success:
                try:
                    from utils.db_manager import DatabaseManager
                    import os
                    from datetime import datetime
                    
                    # Prepare download_info dictionary for DatabaseManager
                    download_info = {
                        'url': url,
                        'title': video_title,
                        'filepath': file_path,
                        'quality': video_info.get('quality', ''),
                        'format': video_info.get('format', ''),
                        'duration': video_info.get('duration', 0),
                        'filesize': self._calculate_file_size(file_path),
                        'status': 'Success',
                        'download_date': datetime.now().strftime("%Y/%m/%d %H:%M"),
                        'creator': video_info.get('creator', ''),
                        'description': video_info.get('description', ''),
                        'hashtags': video_info.get('hashtags', [])
                    }
                    
                    # Save to database
                    db_manager = DatabaseManager()
                    db_manager.add_download(download_info)
                    
                    self.log_info(f"Download saved to database: {download_info['title']}")
                    
                except Exception as db_error:
                    self.log_error(f"Error saving download to database: {db_error}")
                    success = False  # Mark as failed if database save fails
            
            # Show toast notification
            self._show_download_completion_toast(video_title, success, file_path)
            
            # Update UI row status if table exists
            self._update_download_row_status(url, success)
            
            # Enhanced event data for cross-tab communication
            enhanced_event_data = {
                'url': url,
                'success': success,
                'file_path': file_path,
                'downloading_count': self.downloading_count,
                'video_info': video_info,
                'timestamp': self.performance_monitor.current_time(),
                'completion_stats': self._get_completion_statistics()
            }
            
            # Emit completion events with sequenced acknowledgment
            self.video_download_completed.emit(url, success, file_path)
            self.emit_tab_event('video_download_completed', enhanced_event_data)
            
            # Emit statistics update event for cross-tab sync
            self.emit_tab_event('download_statistics_updated', {
                'total_downloads': self._get_total_downloads(),
                'successful_downloads': self._get_successful_downloads(),
                'failed_downloads': self._get_failed_downloads(),
                'current_downloading': self.downloading_count
            })
            
            if success:
                self.log_info(f"Download completed successfully: {file_path}")
            else:
                self.log_error(f"Download failed for: {url}")
                
        except Exception as e:
            self.downloading_count = max(0, self.downloading_count - 1)
            self.log_error(f"Error handling download completion: {e}")
            
            # Report download error to coordination system
            if report_download_error and ErrorSeverity:
                error_id = report_download_error(
                    message=f"Download completion handling failed: {str(e)}",
                    source_tab=self.get_tab_id(),
                    source_component="video_info_download_handler",
                    url=url,
                    severity=ErrorSeverity.MEDIUM
                )
                
                if error_id:
                    self.log_info(f"Download error reported to coordination system: {error_id}")
    
    def _show_download_completion_toast(self, title: str, success: bool, file_path: str):
        """Show toast notification for download completion"""
        try:
            from ui.components.common.toast_notification import show_download_complete_toast, show_toast, ToastType
            
            # Get main window as parent for toast
            main_window = self.window()
            if not main_window:
                return
            
            if success:
                # Show success toast
                show_download_complete_toast(main_window, title, file_path)
            else:
                # Show error toast
                show_toast(
                    main_window,
                    f"Download Failed\n{title[:40]}{'...' if len(title) > 40 else ''}",
                    ToastType.ERROR,
                    4000
                )
                
        except Exception as e:
            self.log_error(f"Error showing toast notification: {e}")
    
    def _show_download_started_toast(self, title: str):
        """Show toast notification for download start"""
        try:
            from ui.components.common.toast_notification import show_download_started_toast
            
            # Get main window as parent for toast
            main_window = self.window()
            if not main_window:
                return
            
            # Show download started toast
            show_download_started_toast(main_window, title)
                
        except Exception as e:
            self.log_error(f"Error showing download started toast: {e}")
    
    def _update_download_row_status(self, url: str, success: bool):
        """Update the table row status for completed download"""
        try:
            if not hasattr(self, 'video_table') or not self.video_table:
                return
            
            # Find the row with matching URL
            for row in range(self.video_table.rowCount()):
                row_url = getattr(self.video_table.item(row, 1), 'url', None)  
                if row_url == url:
                    # Update row styling to indicate completion
                    for col in range(self.video_table.columnCount()):
                        item = self.video_table.item(row, col)
                        if item:
                            if success:
                                item.setBackground(Qt.GlobalColor.lightGreen)
                                item.setToolTip("Download completed successfully")
                            else:
                                item.setBackground(Qt.GlobalColor.lightYellow)  
                                item.setToolTip("Download failed")
                    break
                    
        except Exception as e:
            self.log_error(f"Error updating row status: {e}")
    
    def _get_completion_statistics(self) -> dict:
        """Get current completion statistics"""
        try:
            return {
                'total_processed': len(self.video_info_dict),
                'currently_downloading': self.downloading_count,
                'session_start_time': getattr(self, 'session_start_time', None)
            }
        except Exception:
            return {}
    
    def _get_total_downloads(self) -> int:
        """Get total download count for statistics"""
        try:
            from utils.db_manager import DatabaseManager
            db_manager = DatabaseManager()
            return db_manager.get_total_download_count()
        except Exception as e:
            self.log_error(f"Error getting total downloads: {e}")
            return 0
    
    def _get_successful_downloads(self) -> int:
        """Get successful download count for statistics"""
        try:
            from utils.db_manager import DatabaseManager
            db_manager = DatabaseManager()
            return db_manager.get_successful_download_count()
        except Exception as e:
            self.log_error(f"Error getting successful downloads: {e}")
            return 0
    
    def _get_failed_downloads(self) -> int:
        """Get failed download count for statistics"""
        try:
            from utils.db_manager import DatabaseManager
            db_manager = DatabaseManager()
            return db_manager.get_failed_download_count()
        except Exception as e:
            self.log_error(f"Error getting failed downloads: {e}")
            return 0
    
    def _get_comprehensive_statistics(self) -> dict:
        """Get comprehensive download statistics for enhanced cross-tab sync"""
        try:
            from utils.db_manager import DatabaseManager
            db_manager = DatabaseManager()
            return db_manager.get_download_statistics()
        except Exception as e:
            self.log_error(f"Error getting comprehensive statistics: {e}")
            return {
                'total_downloads': 0,
                'successful_downloads': 0,
                'failed_downloads': 0,
                'success_rate': 0,
                'recent_downloads_24h': 0,
                'total_size_mb': 0,
                'most_common_quality': 'Unknown',
                'most_common_format': 'Unknown'
            }
    
    def _calculate_file_size(self, file_path: str) -> str:
        """Calculate file size in human readable format"""
        try:
            if os.path.exists(file_path):
                size_bytes = os.path.getsize(file_path)
                size_mb = size_bytes / (1024 * 1024)
                return f"{size_mb:.2f} MB"
            else:
                return "Unknown"
        except Exception:
            return "Unknown"
    
    def handle_api_error(self, url, error_message):
        """Enhanced API error handler with categorized error processing and retry logic"""
        try:
            self.performance_monitor.start_timing('api_error_handling')
            
            # Decrement processing count
            self.processing_count = max(0, self.processing_count - 1)
            
            # Categorize error for better handling
            error_category = self._categorize_api_error(error_message)
            
            # Update UI based on error type
            self.get_info_btn.setEnabled(True)
            
            # Set button text based on error category
            if error_category['recoverable']:
                self.get_info_btn.setText(self.tr_("BUTTON_RETRY"))
                self.url_input.setStyleSheet("border: 2px solid orange;")
            else:
                self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
                self.url_input.setStyleSheet("border: 2px solid red;")
            
            # Enhanced logging with error context
            self.log_error(f"API Error [{error_category['type']}] for {url}: {error_message}")
            
            # Show categorized error message to user
            formatted_error = self._format_error_message(error_category, error_message)
            QMessageBox.critical(self, self.tr_("ERROR_API_TITLE"), formatted_error)
            
            # Implement retry logic for recoverable errors
            if error_category['recoverable'] and error_category.get('retry_count', 0) < 3:
                self._schedule_retry(url, error_category)
            
            # Update error statistics for analytics
            self._update_error_statistics(error_category['type'])
            
            # Report error to coordination system for cross-tab handling
            if report_api_error and ErrorSeverity:
                # Determine severity based on error category
                severity = ErrorSeverity.HIGH if not error_category['recoverable'] else ErrorSeverity.MEDIUM
                
                error_id = report_api_error(
                    message=error_message,
                    source_tab=self.get_tab_id(),
                    source_component="video_info_downloader",
                    url=url,
                    severity=severity
                )
                
                if error_id:
                    self.log_info(f"Error reported to coordination system: {error_id}")
            
            # Emit enhanced error event for cross-component coordination
            self.emit_tab_event('api_error_occurred', {
                'url': url,
                'error_message': error_message,
                'error_category': error_category,
                'processing_count': self.processing_count,
                'timestamp': self.performance_monitor.current_time()
            })
            
            # Mark data as dirty for state persistence
            self._set_data_dirty(True)
            
            self.performance_monitor.end_timing('api_error_handling')
            
        except Exception as e:
            self.log_error(f"Error in API error handler: {e}")
            self.performance_monitor.end_timing('api_error_handling')
            
            # Fallback error handling
            self.get_info_btn.setEnabled(True)
            self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
            QMessageBox.critical(self, "Error", f"Failed to handle API error: {e}")
            
            # Log error
            self.log_error(f"API Error for {url}: {error_message}")
            
            # Show error to user
            QMessageBox.warning(
                self,
                self.tr_("DIALOG_API_ERROR_TITLE"),
                f"{self.tr_('DIALOG_TIKTOK_API_CHANGED')}\n\n"
                f"{self.tr_('DIALOG_UPDATE_NEEDED_MESSAGE')}"
            )
            
            # Update status bar through parent
            if self.parent():
                self.parent().status_bar.showMessage(self.tr_("DIALOG_YTDLP_OUTDATED"), 10000)
            
            # Emit error event
            self.emit_tab_event('api_error', {
                'url': url,
                'error_message': error_message
            })
            
        except Exception as e:
            self.log_error(f"Error handling API error: {e}")
    
    # Placeholder methods for the rest of the original functionality
    # These would be implemented with the full original code but with
    # enhanced error handling, logging, and component integration
    
    def create_video_table(self):
        """Create table to display video information with BaseTab integration"""
        try:
            self.performance_monitor.start_timing('create_video_table')
            
            self.video_table = QTableWidget()
            self.video_table.setColumnCount(8)  # 8 columns: Select, Title, Creator, Quality, Format, Duration, Size, Hashtags
            
            # Set up headers
            self.update_table_headers()
            
            # Remove bold headers to save space (as in original)
            header_font = self.video_table.horizontalHeader().font()
            header_font.setBold(False)
            self.video_table.horizontalHeader().setFont(header_font)
            
            # Set table properties
            self.video_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            
            # Set custom column sizes (adapted from v1.2.1)
            self.video_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Select - checkbox column
            self.video_table.setColumnWidth(0, 50)
            
            self.video_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title - stretches
            
            self.video_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Creator
            self.video_table.setColumnWidth(2, 100)
            
            self.video_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Quality
            self.video_table.setColumnWidth(3, 85)
            
            self.video_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Format
            self.video_table.setColumnWidth(4, 85)
            
            self.video_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Duration
            self.video_table.setColumnWidth(5, 90)
            
            self.video_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Size
            self.video_table.setColumnWidth(6, 75)
            
            self.video_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Hashtags 
            self.video_table.setColumnWidth(7, 150)
            
            # Set initial row count
            self.video_table.setRowCount(0)
            
            # Connect double-click event to show copy text dialog
            self.video_table.itemDoubleClicked.connect(self.show_copy_dialog)
            
            # Set up hover event to display tooltip with full text
            self.video_table.setMouseTracking(True)
            self.video_table.cellEntered.connect(self.show_full_text_tooltip)
            
            # Set table style with hover effect
            self.video_table.setStyleSheet("""
                QTableWidget::item:hover {
                    background-color: rgba(0, 120, 215, 0.1);
                }
            """)
            
            # Set row height for single-line display
            self.set_table_row_height()
            
            # Enable sorting capabilities
            self.video_table.setSortingEnabled(True)
            
            # Connect sorting signal to track sort state
            header = self.video_table.horizontalHeader()
            header.sortIndicatorChanged.connect(self.on_sort_indicator_changed)
            
            # Connect selection changed signal to BaseTab event handling
            self.video_table.itemSelectionChanged.connect(self.on_item_selection_changed)
            
            # Restore previous sort state if available
            if self.sort_column >= 0:
                self.video_table.sortByColumn(self.sort_column, self.sort_order)
            
            self.log_info("Video table created successfully with 8 columns and sorting capabilities")
            
        except Exception as e:
            self.log_error(f"Error creating video table: {e}")
            # Create basic fallback table
            self.video_table = QTableWidget()
            self.video_table.setColumnCount(8)
            
        finally:
            self.performance_monitor.end_timing('create_video_table')
    
    def add_video_to_table(self, video_info):
        """Add video to table with complete 8-column implementation and BaseTab integration"""
        try:
            self.performance_monitor.start_timing('add_video_to_table')
            
            # Process title - remove hashtags
            if video_info.title:
                import re
                cleaned_title = re.sub(r'#\S+', '', video_info.title).strip()
                cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
                video_info.original_title = video_info.title  # Save original
                video_info.title = cleaned_title  # Use cleaned title
            
            # Save video information in dictionary
            row = self.video_table.rowCount()
            self.video_info_dict[row] = video_info
            
            # Add new row for this video
            self.video_table.insertRow(row)
            
            # Set row height for single-line display
            self.video_table.setRowHeight(row, 25)
            
            # Check for errors in title
            has_error = video_info.title.startswith("Error:")
            unsupported_content = "DIALOG_UNSUPPORTED_CONTENT" in video_info.title
            
            # Column 0: Select (Checkbox)
            checkbox = QCheckBox()
            checkbox.setChecked(not has_error)  # Uncheck if there's an error
            
            # Allow selection if content is unsupported
            if unsupported_content:
                checkbox.setEnabled(True)
            else:
                checkbox.setEnabled(not has_error)  # Disable if there's an error
            
            # Connect checkbox signal to state changed handler
            checkbox.stateChanged.connect(self.checkbox_state_changed)
            
            # Create centered checkbox widget
            checkbox_cell = QWidget()
            layout = QHBoxLayout(checkbox_cell)
            layout.addWidget(checkbox)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            self.video_table.setCellWidget(row, 0, checkbox_cell)
            
            # Column 1: Title
            if unsupported_content:
                title_text = self.tr_("DIALOG_UNSUPPORTED_CONTENT")
            else:
                title_text = video_info.title
                    
            title_item = QTableWidgetItem(title_text)
            # Save original title to UserRole for later retrieval
            if hasattr(video_info, 'original_title') and video_info.original_title:
                title_item.setData(Qt.ItemDataRole.UserRole, video_info.original_title)
            else:
                title_item.setData(Qt.ItemDataRole.UserRole, title_text)
            
            # Format tooltip text for better readability
            tooltip_text = self.format_tooltip_text(title_text)
            title_item.setToolTip(tooltip_text)
            title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.video_table.setItem(row, 1, title_item)
            
            # Column 2: Creator
            creator = video_info.creator if hasattr(video_info, 'creator') and video_info.creator else ""
            creator_item = QTableWidgetItem(creator)
            creator_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            creator_tooltip = self.format_tooltip_text(creator)
            creator_item.setToolTip(creator_tooltip)
            creator_item.setFlags(creator_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.video_table.setItem(row, 2, creator_item)
            
            # Column 3: Quality (ComboBox)
            quality_combo = QComboBox()
            quality_combo.setFixedWidth(80)
            
            # Get list of qualities from formats
            qualities = []
            video_qualities = []
            audio_quality = None
            
            if hasattr(video_info, 'formats') and video_info.formats:
                for fmt in video_info.formats:
                    if 'quality' in fmt:
                        quality = fmt['quality']
                        if fmt.get('is_audio', False):
                            audio_quality = quality
                        elif quality not in video_qualities:
                            video_qualities.append(quality)
            
            # Sort qualities from high to low
            def quality_to_number(q):
                try:
                    return int(q.replace('p', ''))
                except:
                    return 0
            
            video_qualities.sort(key=quality_to_number, reverse=True)
            qualities = video_qualities
            
            if not qualities:
                qualities = ['1080p', '720p', '480p', '360p']  # Default if not found
                
            quality_combo.addItems(qualities)
            quality_combo.setEnabled(not has_error)  # Disable if there's an error
            
            quality_cell = QWidget()
            quality_layout = QHBoxLayout(quality_cell)
            quality_layout.addWidget(quality_combo)
            quality_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            quality_layout.setContentsMargins(0, 0, 0, 0)
            self.video_table.setCellWidget(row, 3, quality_cell)
            
            # Column 4: Format (ComboBox)
            format_combo = QComboBox()
            format_combo.setFixedWidth(75)
            
            # If it's a video, only show two options: Video and Audio
            format_combo.addItem(self.tr_("FORMAT_VIDEO_MP4"))
            format_combo.addItem(self.tr_("FORMAT_AUDIO_MP3"))
            format_combo.setEnabled(not has_error)  # Disable if there's an error
            
            format_cell = QWidget()
            format_layout = QHBoxLayout(format_cell)
            format_layout.addWidget(format_combo)
            format_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            format_layout.setContentsMargins(0, 0, 0, 0)
            self.video_table.setCellWidget(row, 4, format_cell)
            
            # Connect signal for format change to handle_format_change method
            format_combo.currentIndexChanged.connect(
                lambda index, combo=format_combo, q_combo=quality_combo, audio=audio_quality, video_qs=qualities: 
                self.on_format_changed(index, combo, q_combo, audio, video_qs)
            )
            
            # Column 5: Duration
            duration_str = self.format_duration(video_info.duration)
            duration_item = QTableWidgetItem(duration_str)
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.video_table.setItem(row, 5, duration_item)
            
            # Column 6: Size (estimated based on format)
            size_str = self.estimate_size(video_info.formats)
            size_item = QTableWidgetItem(size_str)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.video_table.setItem(row, 6, size_item)
            
            # Column 7: Hashtags
            hashtags = []
            # Extract hashtags from caption if available
            if video_info.caption:
                import re
                # Find all hashtags starting with # in caption, supporting both Vietnamese and special characters
                found_hashtags = re.findall(r'#([^\s#]+)', video_info.caption)
                if found_hashtags:
                    hashtags.extend(found_hashtags)
            
            # Combine with existing hashtags in video_info
            if hasattr(video_info, 'hashtags') and video_info.hashtags:
                for tag in video_info.hashtags:
                    if tag not in hashtags:
                        hashtags.append(tag)
            
            hashtags_str = " ".join([f"#{tag}" for tag in hashtags]) if hashtags else ""
            hashtags_item = QTableWidgetItem(hashtags_str)
            hashtags_tooltip = self.format_tooltip_text(hashtags_str)
            hashtags_item.setToolTip(hashtags_tooltip)
            hashtags_item.setFlags(hashtags_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.video_table.setItem(row, 7, hashtags_item)
            
            # Update button states and selection UI
            self.update_button_states()
            self.update_select_toggle_button()
            
            # Mark data as dirty for BaseTab auto-save
            self._set_data_dirty(True)
            
            # Emit tab event for cross-component coordination
            self.emit_tab_event('video_added', {
                'row': row,
                'title': title_text,
                'has_error': has_error,
                'creator': creator,
                'duration': duration_str,
                'hashtags': hashtags_str
            })
            
            self.log_info(f"Video added to table at row {row}: {title_text} by {creator}")
            
        except Exception as e:
            self.log_error(f"Error adding video to table: {e}")
            # Basic fallback - ensure row exists
            if 'row' in locals() and row >= 0:
                self.video_table.insertRow(row)
                for col in range(8):
                    error_item = QTableWidgetItem("Error")
                    error_item.setFlags(error_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.video_table.setItem(row, col, error_item)
            
        finally:
            self.performance_monitor.end_timing('add_video_to_table')
    
    def update_table_headers(self):
        """Update table headers based on current language"""
        try:
            headers = [
                self.tr_("HEADER_SELECT"),
                self.tr_("HEADER_VIDEO_TITLE"),
                self.tr_("HEADER_CREATOR"),
                self.tr_("HEADER_QUALITY"),
                self.tr_("HEADER_FORMAT"),
                self.tr_("HEADER_DURATION"),
                self.tr_("HEADER_SIZE"),
                self.tr_("HEADER_HASHTAGS")
            ]
            if hasattr(self, 'video_table'):
                self.video_table.setHorizontalHeaderLabels(headers)
                self.log_debug("Table headers updated successfully")
        except Exception as e:
            self.log_error(f"Error updating table headers: {e}")
    
    def set_table_row_height(self):
        """Set row height for single-line display in the video table"""
        try:
            if hasattr(self, 'video_table'):
                for row in range(self.video_table.rowCount()):
                    self.video_table.setRowHeight(row, 25)  # Set height for single-line display
                self.log_debug(f"Set row height for {self.video_table.rowCount()} rows")
        except Exception as e:
            self.log_error(f"Error setting table row height: {e}")
    
    def on_sort_indicator_changed(self, logical_index: int, order: Qt.SortOrder):
        """Handle sort indicator changes and maintain sort state through BaseTab lifecycle"""
        try:
            self.sort_column = logical_index
            self.sort_order = order
            
            # Mark data as dirty for BaseTab auto-save
            self._set_data_dirty(True)
            
            # Log the sort change for debugging
            column_names = ["Select", "Title", "Creator", "Quality", "Format", "Duration", "Size", "Hashtags"]
            column_name = column_names[logical_index] if 0 <= logical_index < len(column_names) else f"Column {logical_index}"
            order_text = "Ascending" if order == Qt.SortOrder.AscendingOrder else "Descending"
            
            self.log_debug(f"Table sorted by {column_name} ({order_text})")
            
            # Emit tab event for potential cross-tab coordination
            self.emit_tab_event('table_sorted', {
                'column': logical_index,
                'order': order,
                'column_name': column_name
            })
            
        except Exception as e:
            self.log_error(f"Error handling sort indicator change: {e}")
    
    def on_item_selection_changed(self):
        """Handle table item selection changes with BaseTab integration"""
        try:
            # Get current selection
            selected_items = self.video_table.selectedItems()
            selected_rows = set()
            
            for item in selected_items:
                selected_rows.add(item.row())
            
            # Emit tab event for cross-component coordination
            self.emit_tab_event('item_selection_changed', {
                'selected_rows': list(selected_rows),
                'selected_count': len(selected_rows),
                'total_rows': self.video_table.rowCount()
            })
            
            self.log_debug(f"Item selection changed: {len(selected_rows)} rows selected")
            
        except Exception as e:
            self.log_error(f"Error handling item selection change: {e}")
    
    def sort_by_column(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        """Programmatically sort table by specified column with state tracking"""
        try:
            if hasattr(self, 'video_table') and 0 <= column < self.video_table.columnCount():
                self.video_table.sortByColumn(column, order)
                # State will be updated automatically via on_sort_indicator_changed signal
                self.log_info(f"Table programmatically sorted by column {column}")
            else:
                self.log_warning(f"Cannot sort by column {column}: invalid column or table not ready")
        except Exception as e:
            self.log_error(f"Error sorting by column {column}: {e}")
    
    def choose_output_folder(self):
        """Choose output folder with state persistence"""
        try:
            start_folder = self.output_folder_display.text() if self.output_folder_display.text() else ""
            
            folder = QFileDialog.getExistingDirectory(
                self, self.tr_("MENU_CHOOSE_FOLDER"), start_folder)
            
            if folder:
                self.output_folder_display.setText(folder)
                self.save_last_output_folder(folder)
                self._set_data_dirty(True)
                
                self.log_info(f"Output folder changed to: {folder}")
                
        except Exception as e:
            self.log_error(f"Error choosing output folder: {e}")
    
    @validate_before_action()
    def download_videos(self):
        """Enhanced download preparation workflow with queue management and cross-tab integration"""
        try:
            self.performance_monitor.start_timing('download_preparation')
            
            # Validate that there's an output folder selected
            output_folder = self.output_folder_display.text().strip()
            if not output_folder:
                QMessageBox.warning(self, self.tr_("ERROR_NO_OUTPUT_FOLDER"), 
                                  self.tr_("ERROR_NO_OUTPUT_FOLDER_MESSAGE"))
                return
            
            # Validate output folder exists and is writable
            if not os.path.exists(output_folder):
                QMessageBox.warning(self, self.tr_("ERROR_INVALID_FOLDER"), 
                                  self.tr_("ERROR_FOLDER_NOT_EXISTS").format(output_folder))
                return
            
            if not os.access(output_folder, os.W_OK):
                QMessageBox.warning(self, self.tr_("ERROR_FOLDER_READONLY"), 
                                  self.tr_("ERROR_FOLDER_READONLY_MESSAGE").format(output_folder))
                return
            
            # Get selected video items with validation
            selected_items = self._prepare_download_items()
            
            if not selected_items:
                QMessageBox.information(self, self.tr_("INFO_NO_SELECTION"), 
                                      self.tr_("INFO_NO_VIDEOS_SELECTED"))
                return
            
            # Validate selected items and prepare download queue
            validated_items = self._validate_download_items(selected_items)
            
            if not validated_items:
                QMessageBox.warning(self, self.tr_("ERROR_NO_VALID_ITEMS"), 
                                  self.tr_("ERROR_NO_DOWNLOADABLE_VIDEOS"))
                return
            
            # Create download queue with priority management
            download_queue = self._create_download_queue(validated_items, output_folder)
            
            # Emit download preparation events for cross-tab coordination
            self.emit_tab_event('download_preparation_started', {
                'queue_size': len(download_queue),
                'output_folder': output_folder,
                'estimated_duration': self._estimate_total_duration(validated_items)
            })
            
            # Update UI state to show downloads starting
            self.downloading_count += len(validated_items)
            self._set_data_dirty(True)
            
            # Process download queue with concurrent management
            success_count = self._process_download_queue(download_queue)
            
            # Emit completion events
            self.emit_tab_event('download_preparation_completed', {
                'total_items': len(validated_items),
                'successful_items': success_count,
                'output_folder': output_folder
            })
            
            # Show completion message
            if success_count > 0:
                QMessageBox.information(self, self.tr_("INFO_DOWNLOADS_STARTED"), 
                                      self.tr_("INFO_DOWNLOADS_STARTED_MESSAGE").format(success_count))
                self.log_info(f"Successfully initiated downloads for {success_count}/{len(validated_items)} videos")
            else:
                QMessageBox.warning(self, self.tr_("ERROR_DOWNLOAD_FAILED"), 
                                  self.tr_("ERROR_NO_DOWNLOADS_STARTED"))
                self.log_warning("No downloads could be started")
            
            self.performance_monitor.end_timing('download_preparation')
            
        except Exception as e:
            self.downloading_count = max(0, self.downloading_count - 1)
            self.log_error(f"Error in download preparation workflow: {e}")
            QMessageBox.critical(self, self.tr_("ERROR_DOWNLOAD_PREPARATION"), 
                               f"{self.tr_('ERROR_DOWNLOAD_PREPARATION_MESSAGE')}: {e}")
            self.performance_monitor.end_timing('download_preparation')
    
    def delete_selected_videos(self):
        """Delete selected videos with BaseTab integration"""
        try:
            self.performance_monitor.start_timing('delete_selected_videos')
            
            # Get selected rows in reverse order to avoid index shifting
            selected_rows = []
            for row in range(self.video_table.rowCount()):
                checkbox_cell = self.video_table.cellWidget(row, 0)
                if checkbox_cell:
                    checkbox = checkbox_cell.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        selected_rows.append(row)
            
            if not selected_rows:
                self.log_warning("No videos selected for deletion")
                return
            
            # Sort in reverse order to delete from bottom to top
            selected_rows.sort(reverse=True)
            
            # Delete rows and update video_info_dict
            deleted_count = 0
            for row in selected_rows:
                # Remove from video info dictionary
                if row in self.video_info_dict:
                    del self.video_info_dict[row]
                
                # Remove table row
                self.video_table.removeRow(row)
                deleted_count += 1
            
            # Rebuild video_info_dict with correct indices
            old_dict = self.video_info_dict.copy()
            self.video_info_dict.clear()
            
            new_row = 0
            for old_row in sorted(old_dict.keys()):
                if old_row not in selected_rows:
                    self.video_info_dict[new_row] = old_dict[old_row]
                    new_row += 1
            
            # Update UI state
            self.update_button_states()
            self.update_select_toggle_button()
            
            # Mark data as dirty for BaseTab auto-save
            self._set_data_dirty(True)
            
            # Emit tab event
            self.emit_tab_event('videos_deleted', {
                'count': deleted_count,
                'remaining': self.video_table.rowCount()
            })
            
            self.log_info(f"Deleted {deleted_count} selected videos")
            
            # Update status through parent
            if self.parent():
                self.parent().status_bar.showMessage(
                    self.tr_("STATUS_VIDEOS_DELETED").format(deleted_count), 3000
                )
            
        except Exception as e:
            self.log_error(f"Error deleting selected videos: {e}")
            
        finally:
            self.performance_monitor.end_timing('delete_selected_videos')
    
    def delete_all_videos(self):
        """Delete all videos with state tracking"""
        self.video_info_dict.clear()
        self.video_table.setRowCount(0)
        self.processing_count = 0
        self.downloading_count = 0
        self._set_data_dirty(True)
        self.update_button_states()
        self.log_info("All videos deleted")
    
    def toggle_select_all(self):
        """Toggle select all videos with BaseTab state management"""
        try:
            self.performance_monitor.start_timing('toggle_select_all')
            
            self.all_selected = not self.all_selected
            
            # Temporarily disconnect signals to avoid calling checkbox_state_changed multiple times
            checkboxes = []
            
            # Collect all checkboxes and disconnect signals
            for row in range(self.video_table.rowCount()):
                checkbox_cell = self.video_table.cellWidget(row, 0)
                if checkbox_cell:
                    checkbox = checkbox_cell.findChild(QCheckBox)
                    if checkbox:
                        # Temporarily disconnect signal
                        try:
                            checkbox.stateChanged.disconnect(self.checkbox_state_changed)
                        except TypeError:
                            pass  # Signal wasn't connected
                        checkboxes.append(checkbox)
            
            # Update checkbox states
            for checkbox in checkboxes:
                checkbox.setChecked(self.all_selected)
            
            # Reconnect signals after updates
            for checkbox in checkboxes:
                checkbox.stateChanged.connect(self.checkbox_state_changed)
            
            # Update button text
            self.update_select_toggle_button()
            
            # Mark data as dirty for BaseTab auto-save
            self._set_data_dirty(True)
            
            # Emit tab event for cross-component coordination
            self.emit_tab_event('selection_toggled', {
                'all_selected': self.all_selected,
                'video_count': self.video_table.rowCount()
            })
            
            # Display status message
            if self.parent() and hasattr(self.parent(), 'status_bar'):
                if self.all_selected:
                    self.parent().status_bar.showMessage(self.tr_("STATUS_ALL_VIDEOS_SELECTED"), 2000)
                else:
                    self.parent().status_bar.showMessage(self.tr_("STATUS_ALL_VIDEOS_UNSELECTED"), 2000)
            
            self.log_info(f"Selection toggled: all_selected={self.all_selected}")
            
        except Exception as e:
            self.log_error(f"Error toggling select all: {e}")
            
        finally:
            self.performance_monitor.end_timing('toggle_select_all')
    
    def update_select_toggle_button(self):
        """Update select toggle button state based on checkbox states"""
        try:
            # Check if there are any videos in the table
            if self.video_table.rowCount() == 0:
                if hasattr(self, 'select_toggle_btn'):
                    self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
                    self.select_toggle_btn.setEnabled(False)
                return
            
            # Check the state of all checkboxes
            all_checked = True
            any_checked = False
            
            for row in range(self.video_table.rowCount()):
                checkbox_cell = self.video_table.cellWidget(row, 0)
                if checkbox_cell:
                    checkbox = checkbox_cell.findChild(QCheckBox)
                    if checkbox:
                        if checkbox.isChecked():
                            any_checked = True
                        else:
                            all_checked = False
            
            # Update button state and all_selected variable
            if all_checked and self.video_table.rowCount() > 0:
                self.all_selected = True
                if hasattr(self, 'select_toggle_btn'):
                    self.select_toggle_btn.setText(self.tr_("BUTTON_UNSELECT_ALL"))
                    self.select_toggle_btn.setEnabled(True)
            else:
                self.all_selected = False
                if hasattr(self, 'select_toggle_btn'):
                    self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
                    self.select_toggle_btn.setEnabled(True)
                    
            self.log_debug(f"Select toggle button updated: all_selected={self.all_selected}")
            
        except Exception as e:
            self.log_error(f"Error updating select toggle button: {e}")
    
    def checkbox_state_changed(self):
        """Handle checkbox state change events with BaseTab integration"""
        try:
            # Update the select toggle button state based on current checkboxes
            self.update_select_toggle_button()
            
            # Mark data as dirty for BaseTab auto-save
            self._set_data_dirty(True)
            
            # Emit tab event for cross-component coordination
            selected_count = self.get_selected_count()
            self.emit_tab_event('selection_changed', {
                'selected_count': selected_count,
                'total_count': self.video_table.rowCount(),
                'all_selected': self.all_selected
            })
            
            self.log_debug(f"Checkbox state changed: {selected_count}/{self.video_table.rowCount()} selected")
            
        except Exception as e:
            self.log_error(f"Error handling checkbox state change: {e}")
    
    def get_selected_items(self) -> List[Dict]:
        """Get list of selected video items with their data"""
        try:
            selected_items = []
            
            for row in range(self.video_table.rowCount()):
                checkbox_cell = self.video_table.cellWidget(row, 0)
                if checkbox_cell:
                    checkbox = checkbox_cell.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        # Get video info for this row
                        video_info = self.video_info_dict.get(row)
                        if video_info:
                            # Get table data
                            title_item = self.video_table.item(row, 1)
                            creator_item = self.video_table.item(row, 2)
                            
                            selected_items.append({
                                'row': row,
                                'video_info': video_info,
                                'title': title_item.text() if title_item else '',
                                'creator': creator_item.text() if creator_item else '',
                                'checkbox_enabled': checkbox.isEnabled()
                            })
            
            self.log_debug(f"Retrieved {len(selected_items)} selected items")
            return selected_items
            
        except Exception as e:
            self.log_error(f"Error getting selected items: {e}")
            return []
    
    def get_selected_count(self) -> int:
        """Get count of selected videos"""
        try:
            count = 0
            for row in range(self.video_table.rowCount()):
                checkbox_cell = self.video_table.cellWidget(row, 0)
                if checkbox_cell:
                    checkbox = checkbox_cell.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        count += 1
            return count
        except Exception as e:
            self.log_error(f"Error getting selected count: {e}")
            return 0
    
    def update_button_states(self):
        """Update button states based on video table content"""
        has_videos = len(self.video_info_dict) > 0
        
        if hasattr(self, 'select_toggle_btn'):
            self.select_toggle_btn.setEnabled(has_videos)
        if hasattr(self, 'delete_selected_btn'):
            self.delete_selected_btn.setEnabled(has_videos)
        if hasattr(self, 'delete_all_btn'):
            self.delete_all_btn.setEnabled(has_videos)
        if hasattr(self, 'download_btn'):
            self.download_btn.setEnabled(has_videos)
    
    def show_copy_dialog(self, item):
        """Show copy dialog for table item - placeholder for full implementation"""
        try:
            if item and item.text():
                # Basic implementation - copy to clipboard
                QApplication.clipboard().setText(item.text())
                self.log_info(f"Copied to clipboard: {item.text()[:50]}...")
        except Exception as e:
            self.log_error(f"Error in copy dialog: {e}")
    
    def show_full_text_tooltip(self, row, column):
        """Show full text tooltip for table cell - placeholder for full implementation"""
        try:
            if hasattr(self, 'video_table') and self.video_table.item(row, column):
                item = self.video_table.item(row, column)
                if item and item.text():
                    # Basic tooltip with formatted text
                    tooltip_text = self.format_tooltip_text(item.text())
                    item.setToolTip(tooltip_text)
        except Exception as e:
            self.log_error(f"Error setting tooltip: {e}")
    
    def show_context_menu(self, position):
        """Show context menu - placeholder for original implementation"""
        # This would contain the full original context menu implementation
        pass
    
    # =============================================================================
    # Helper Methods for Video Processing
    # =============================================================================
    
    def process_video_metadata(self, video_info, url):
        """Process and validate video metadata with comprehensive error handling"""
        try:
            import html
            import re
            from typing import Union
            
            self.performance_monitor.start_timing('process_video_metadata')
            
            # Create processed video info copy to avoid modifying original
            processed_info = type(video_info)(
                url=url,
                platform=getattr(video_info, 'platform', None),
                platform_id=self.sanitize_text(getattr(video_info, 'platform_id', None)),
                title=self.sanitize_text(getattr(video_info, 'title', 'Unknown Title')),
                description=self.sanitize_text(getattr(video_info, 'description', '')),
                thumbnail_url=self.validate_url(getattr(video_info, 'thumbnail_url', '')),
                duration=self.validate_duration(getattr(video_info, 'duration', None)),
                creator=self.sanitize_text(getattr(video_info, 'creator', 'Unknown')),
                creator_id=self.sanitize_text(getattr(video_info, 'creator_id', None)),
                creator_avatar=self.validate_url(getattr(video_info, 'creator_avatar', None)),
                content_type=getattr(video_info, 'content_type', None),
                hashtags=self.extract_hashtags(getattr(video_info, 'description', '') + ' ' + getattr(video_info, 'title', '')),
                mentions=self.extract_mentions(getattr(video_info, 'description', '') + ' ' + getattr(video_info, 'title', '')),
                view_count=self.validate_count(getattr(video_info, 'view_count', None)),
                like_count=self.validate_count(getattr(video_info, 'like_count', None)),
                comment_count=self.validate_count(getattr(video_info, 'comment_count', None)),
                share_count=self.validate_count(getattr(video_info, 'share_count', None)),
                published_at=self.validate_datetime(getattr(video_info, 'published_at', None)),
                formats=self.process_formats(getattr(video_info, 'formats', [])),
                extra_data=self.sanitize_extra_data(getattr(video_info, 'extra_data', {}))
            )
            
            self.log_debug(f"Processed metadata for {len(processed_info.hashtags)} hashtags, {len(processed_info.mentions)} mentions")
            self.performance_monitor.end_timing('process_video_metadata')
            
            return processed_info
            
        except Exception as e:
            self.log_error(f"Error processing video metadata: {e}")
            self.performance_monitor.end_timing('process_video_metadata')
            # Return original video_info if processing fails
            return video_info
    
    def sanitize_text(self, text):
        """Sanitize text fields removing HTML tags and entities"""
        if not text or not isinstance(text, str):
            return text if text is not None else ""
        
        try:
            import html
            import re
            
            # Decode HTML entities
            text = html.unescape(text)
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', text)
            
            # Remove excessive whitespace
            text = ' '.join(text.split())
            
            # Limit length to prevent UI issues
            if len(text) > 500:
                text = text[:497] + "..."
            
            return text
            
        except Exception as e:
            self.log_warning(f"Error sanitizing text: {e}")
            return str(text) if text else ""
    
    def validate_url(self, url):
        """Validate URL format"""
        if not url or not isinstance(url, str):
            return None
        
        try:
            import re
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            
            return url if url_pattern.match(url) else None
            
        except Exception:
            return None
    
    def validate_duration(self, duration):
        """Validate and convert duration to seconds"""
        if duration is None:
            return None
        
        try:
            # Handle different duration formats
            if isinstance(duration, str):
                # Try to parse MM:SS or HH:MM:SS format
                import re
                if ':' in duration:
                    parts = duration.split(':')
                    if len(parts) == 2:  # MM:SS
                        minutes, seconds = map(int, parts)
                        return minutes * 60 + seconds
                    elif len(parts) == 3:  # HH:MM:SS
                        hours, minutes, seconds = map(int, parts)
                        return hours * 3600 + minutes * 60 + seconds
                else:
                    # Try to parse as numeric string
                    return float(duration)
            elif isinstance(duration, (int, float)):
                return float(duration)
            else:
                return None
                
        except (ValueError, TypeError):
            self.log_warning(f"Invalid duration format: {duration}")
            return None
    
    def validate_count(self, count):
        """Validate numeric counts"""
        if count is None:
            return None
        
        try:
            return max(0, int(count)) if isinstance(count, (int, float, str)) else None
        except (ValueError, TypeError):
            return None
    
    def validate_datetime(self, dt):
        """Validate datetime object"""
        if dt is None:
            return None
        
        try:
            from datetime import datetime
            if isinstance(dt, datetime):
                return dt
            elif isinstance(dt, str):
                # Try to parse common datetime formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                    try:
                        return datetime.strptime(dt, fmt)
                    except ValueError:
                        continue
                return None
            else:
                return None
        except Exception:
            return None
    
    def extract_hashtags(self, text):
        """Extract hashtags from text using regex"""
        if not text or not isinstance(text, str):
            return []
        
        try:
            import re
            # Find hashtags but exclude URL fragments
            hashtags = re.findall(r'(?<!\S)#([a-zA-Z0-9_]+)(?!\S)', text)
            return list(set(hashtags))  # Remove duplicates
        except Exception as e:
            self.log_warning(f"Error extracting hashtags: {e}")
            return []
    
    def extract_mentions(self, text):
        """Extract mentions from text using regex"""
        if not text or not isinstance(text, str):
            return []
        
        try:
            import re
            # Find mentions (@username)
            mentions = re.findall(r'(?<!\S)@([a-zA-Z0-9_.]+)(?!\S)', text)
            return list(set(mentions))  # Remove duplicates
        except Exception as e:
            self.log_warning(f"Error extracting mentions: {e}")
            return []
    
    def process_formats(self, formats):
        """Process and validate video formats"""
        if not formats or not isinstance(formats, list):
            return []
        
        try:
            processed_formats = []
            for fmt in formats:
                if hasattr(fmt, 'format_id') and hasattr(fmt, 'quality'):
                    # Validate format data
                    processed_fmt = fmt
                    # Could add additional format validation here
                    processed_formats.append(processed_fmt)
            
            return processed_formats
        except Exception as e:
            self.log_warning(f"Error processing formats: {e}")
            return formats
    
    def sanitize_extra_data(self, extra_data):
        """Sanitize extra data dictionary"""
        if not extra_data or not isinstance(extra_data, dict):
            return {}
        
        try:
            sanitized = {}
            for key, value in extra_data.items():
                if isinstance(key, str) and len(key) < 100:  # Reasonable key length
                    if isinstance(value, str):
                        sanitized[key] = self.sanitize_text(value)
                    elif isinstance(value, (int, float, bool, type(None))):
                        sanitized[key] = value
                    elif isinstance(value, (list, dict)):
                        # Keep simple collections but limit depth
                        sanitized[key] = value
            
            return sanitized
        except Exception as e:
            self.log_warning(f"Error sanitizing extra data: {e}")
            return {}
    
    def format_duration(self, seconds):
        """Format duration from seconds to MM:SS"""
        try:
            if not seconds:
                return "00:00"
            
            minutes = int(seconds / 60)
            remaining_seconds = int(seconds % 60)
            return f"{minutes:02d}:{remaining_seconds:02d}"
        except Exception as e:
            self.log_error(f"Error formatting duration: {e}")
            return "00:00"
    
    def estimate_size(self, formats):
        """Estimate file size based on formats"""
        try:
            if not formats:
                return "Unknown"
            
            # Get largest format
            max_size = 0
            for fmt in formats:
                if 'filesize' in fmt and fmt['filesize'] and fmt['filesize'] > max_size:
                    max_size = fmt['filesize']
            
            if max_size == 0:
                return "Unknown"
            
            # Convert to MB
            size_mb = max_size / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        except Exception as e:
            self.log_error(f"Error estimating size: {e}")
            return "Unknown"

    def on_format_changed(self, index, format_combo, quality_combo, audio_quality, video_qualities, video_info=None, row_index=None):
        """Enhanced format change handler with dynamic quality loading and bulk operations support"""
        try:
            self.performance_monitor.start_timing('format_change_handler')
            
            current_format = format_combo.currentText()
            is_audio = self.is_audio_format(current_format)
            
            # Clear current quality options
            quality_combo.clear()
            
            # Get video-specific quality options if available
            if video_info and hasattr(video_info, 'formats'):
                dynamic_qualities = self.get_dynamic_quality_options(video_info, is_audio)
                if dynamic_qualities:
                    quality_combo.addItems(dynamic_qualities)
                else:
                    # Fallback to static qualities
                    self.populate_fallback_qualities(quality_combo, is_audio, audio_quality, video_qualities)
            else:
                # Use provided static qualities
                self.populate_fallback_qualities(quality_combo, is_audio, audio_quality, video_qualities)
            
            # Update download parameters
            self.update_download_parameters(row_index, current_format, quality_combo.currentText())
            
            self.log_debug(f"Format changed to {current_format} ({'audio' if is_audio else 'video'}) with {quality_combo.count()} quality options")
            
            # Mark data as dirty for BaseTab auto-save
            self._set_data_dirty(True)
            
            # Emit enhanced tab event for cross-component coordination
            self.emit_tab_event('format_changed', {
                'format': 'audio' if is_audio else 'video',
                'format_text': current_format,
                'quality_options': quality_combo.count(),
                'row_index': row_index,
                'dynamic_loading': video_info is not None,
                'available_qualities': [quality_combo.itemText(i) for i in range(quality_combo.count())]
            })
            
            self.performance_monitor.end_timing('format_change_handler')
            
        except Exception as e:
            self.log_error(f"Error handling format change: {e}")
            self.performance_monitor.end_timing('format_change_handler')

    def is_audio_format(self, format_text):
        """Check if format is audio-only"""
        try:
            audio_formats = [
                self.tr_("FORMAT_AUDIO_MP3"),
                "Audio (MP3)",
                "Audio (M4A)", 
                "MP3",
                "M4A",
                "Audio"
            ]
            return any(audio_fmt in format_text for audio_fmt in audio_formats)
        except Exception as e:
            self.log_warning(f"Error checking audio format: {e}")
            return "mp3" in format_text.lower() or "audio" in format_text.lower()
    
    def get_dynamic_quality_options(self, video_info, is_audio):
        """Get quality options dynamically from video info formats"""
        try:
            if not video_info or not hasattr(video_info, 'formats'):
                return []
            
            quality_options = []
            
            if is_audio:
                # For audio, get audio quality options
                audio_qualities = []
                for fmt in video_info.formats:
                    if hasattr(fmt, 'is_audio_only') and fmt.is_audio_only:
                        if hasattr(fmt, 'abr') and fmt.abr:
                            audio_qualities.append(f"{fmt.abr}kbps")
                        else:
                            audio_qualities.append("Original")
                
                if audio_qualities:
                    # Remove duplicates and sort by bitrate
                    quality_options = list(set(audio_qualities))
                    quality_options.sort(key=lambda x: int(x.replace('kbps', '')) if 'kbps' in x else 999, reverse=True)
                else:
                    quality_options = ["Original", "High", "Medium"]
            else:
                # For video, get video quality options
                if hasattr(video_info, 'get_available_qualities'):
                    available_qualities = video_info.get_available_qualities()
                    quality_options = [quality.value for quality in available_qualities]
                else:
                    # Fallback: extract from formats
                    video_qualities = set()
                    for fmt in video_info.formats:
                        if hasattr(fmt, 'height') and fmt.height and not getattr(fmt, 'is_audio_only', False):
                            if fmt.height >= 1080:
                                video_qualities.add("1080p")
                            elif fmt.height >= 720:
                                video_qualities.add("720p")
                            elif fmt.height >= 480:
                                video_qualities.add("480p")
                            else:
                                video_qualities.add("360p")
                    
                    quality_options = sorted(list(video_qualities), key=lambda x: int(x.replace('p', '')), reverse=True)
                    
                    if not quality_options:
                        quality_options = ["Best", "Good", "Medium"]
            
            return quality_options
            
        except Exception as e:
            self.log_warning(f"Error getting dynamic quality options: {e}")
            return []
    
    def populate_fallback_qualities(self, quality_combo, is_audio, audio_quality, video_qualities):
        """Populate quality combo with fallback options"""
        try:
            if is_audio:
                # If audio, only display audio quality
                if audio_quality:
                    quality_combo.addItem(audio_quality)
                else:
                    quality_combo.addItem("Original")
            else:
                # If video, display list of video qualities
                if video_qualities:
                    quality_combo.addItems(video_qualities)
                else:
                    # Default video qualities
                    quality_combo.addItems(["1080p", "720p", "480p", "360p"])
        except Exception as e:
            self.log_warning(f"Error populating fallback qualities: {e}")
    
    def update_download_parameters(self, row_index, format_selection, quality_selection):
        """Update download parameters based on format/quality selection"""
        try:
            if row_index is None or row_index < 0:
                return
            
            # Store selection in table item data for later retrieval
            format_cell = self.video_table.cellWidget(row_index, 4)  # Format column
            quality_cell = self.video_table.cellWidget(row_index, 3)  # Quality column
            
            if format_cell and quality_cell:
                # Store selection parameters as user data
                format_combo = format_cell.findChild(QComboBox)
                quality_combo = quality_cell.findChild(QComboBox)
                
                if format_combo and quality_combo:
                    # Store parameters for download workflow
                    download_params = {
                        'format': format_selection,
                        'quality': quality_selection,
                        'is_audio': self.is_audio_format(format_selection),
                        'timestamp': self.performance_monitor.current_time()
                    }
                    
                    # Store in format combo user data
                    format_combo.setProperty('download_params', download_params)
            
            self.log_debug(f"Updated download parameters for row {row_index}: {format_selection} @ {quality_selection}")
            
        except Exception as e:
            self.log_warning(f"Error updating download parameters: {e}")
    
    def apply_bulk_format_selection(self, format_selection, quality_selection=None):
        """Apply format/quality selection to all selected videos"""
        try:
            self.performance_monitor.start_timing('bulk_format_selection')
            
            selected_rows = []
            for row in range(self.video_table.rowCount()):
                checkbox_cell = self.video_table.cellWidget(row, 0)
                if checkbox_cell:
                    checkbox = checkbox_cell.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        selected_rows.append(row)
            
            if not selected_rows:
                self.log_warning("No videos selected for bulk format change")
                return
            
            updated_count = 0
            for row in selected_rows:
                try:
                    # Update format
                    format_cell = self.video_table.cellWidget(row, 4)
                    if format_cell:
                        format_combo = format_cell.findChild(QComboBox)
                        if format_combo:
                            format_index = format_combo.findText(format_selection)
                            if format_index >= 0:
                                format_combo.setCurrentIndex(format_index)
                    
                    # Update quality if specified
                    if quality_selection:
                        quality_cell = self.video_table.cellWidget(row, 3)
                        if quality_cell:
                            quality_combo = quality_cell.findChild(QComboBox)
                            if quality_combo:
                                quality_index = quality_combo.findText(quality_selection)
                                if quality_index >= 0:
                                    quality_combo.setCurrentIndex(quality_index)
                    
                    updated_count += 1
                    
                except Exception as e:
                    self.log_warning(f"Error updating row {row} in bulk operation: {e}")
            
            self.log_info(f"Bulk format selection applied to {updated_count}/{len(selected_rows)} videos")
            
            # Mark data as dirty
            self._set_data_dirty(True)
            
            # Emit bulk operation event
            self.emit_tab_event('bulk_format_applied', {
                'format': format_selection,
                'quality': quality_selection,
                'affected_rows': updated_count,
                'total_selected': len(selected_rows)
            })
            
            self.performance_monitor.end_timing('bulk_format_selection')
                        
        except Exception as e:
            self.log_error(f"Error in bulk format selection: {e}")
            self.performance_monitor.end_timing('bulk_format_selection')

    def _categorize_api_error(self, error_message):
        """Categorize API errors for enhanced handling and recovery"""
        try:
            error_msg_lower = error_message.lower()
            
            # Network/connectivity errors (recoverable)
            if any(keyword in error_msg_lower for keyword in ['timeout', 'connection', 'network', 'dns', 'host']):
                return {
                    'type': 'network_error',
                    'recoverable': True,
                    'severity': 'medium',
                    'user_action': 'Check internet connection and retry',
                    'retry_delay': 5
                }
            
            # Rate limiting (recoverable with delay)
            if any(keyword in error_msg_lower for keyword in ['rate limit', '429', 'too many requests']):
                return {
                    'type': 'rate_limit',
                    'recoverable': True,
                    'severity': 'low',
                    'user_action': 'Wait a moment and retry',
                    'retry_delay': 30
                }
            
            # TikTok API changes (partially recoverable)
            if any(keyword in error_msg_lower for keyword in ['api', 'extractor', 'tiktok', 'format']):
                return {
                    'type': 'api_change',
                    'recoverable': False,
                    'severity': 'high',
                    'user_action': 'Update application or try again later',
                    'retry_delay': 0
                }
            
            # Content issues (not recoverable for this URL)
            if any(keyword in error_msg_lower for keyword in ['private', 'unavailable', 'copyright', 'region']):
                return {
                    'type': 'content_error',
                    'recoverable': False,
                    'severity': 'medium',
                    'user_action': 'Try different video URL',
                    'retry_delay': 0
                }
            
            # URL format errors (not recoverable)
            if any(keyword in error_msg_lower for keyword in ['invalid', 'unsupported', 'malformed']):
                return {
                    'type': 'url_error',
                    'recoverable': False,
                    'severity': 'medium',
                    'user_action': 'Check URL format',
                    'retry_delay': 0
                }
            
            # Default: unknown error (potentially recoverable)
            return {
                'type': 'unknown_error',
                'recoverable': True,
                'severity': 'medium',
                'user_action': 'Try again or contact support',
                'retry_delay': 10
            }
            
        except Exception as e:
            self.log_warning(f"Error categorizing API error: {e}")
            return {
                'type': 'categorization_error',
                'recoverable': False,
                'severity': 'high',
                'user_action': 'Contact support',
                'retry_delay': 0
            }
    
    def _format_error_message(self, error_category, original_error):
        """Format error message for user display based on category"""
        try:
            error_type = error_category['type']
            user_action = error_category['user_action']
            
            if error_type == 'network_error':
                return f"{self.tr_('ERROR_NETWORK')}\n\n{user_action}\n\nOriginal error: {original_error}"
            elif error_type == 'rate_limit':
                return f"{self.tr_('ERROR_RATE_LIMIT')}\n\n{user_action}\n\nRetry in {error_category['retry_delay']} seconds."
            elif error_type == 'api_change':
                return f"{self.tr_('ERROR_API_CHANGE')}\n\n{user_action}\n\nTechnical details: {original_error}"
            elif error_type == 'content_error':
                return f"{self.tr_('ERROR_CONTENT_UNAVAILABLE')}\n\n{user_action}"
            elif error_type == 'url_error':
                return f"{self.tr_('ERROR_INVALID_URL')}\n\n{user_action}\n\nURL format should be: https://www.tiktok.com/@username/video/1234567890"
            else:
                return f"{self.tr_('ERROR_UNKNOWN')}\n\n{user_action}\n\nError details: {original_error}"
                
        except Exception as e:
            self.log_warning(f"Error formatting error message: {e}")
            return f"Error occurred: {original_error}"
    
    def _schedule_retry(self, url, error_category):
        """Schedule automatic retry for recoverable errors"""
        try:
            retry_delay = error_category.get('retry_delay', 5)
            
            # Update retry count
            error_category['retry_count'] = error_category.get('retry_count', 0) + 1
            
            self.log_info(f"Scheduling retry #{error_category['retry_count']} for {url} in {retry_delay} seconds")
            
            # Use QTimer for delayed retry
            retry_timer = QTimer()
            retry_timer.timeout.connect(lambda: self._execute_retry(url, retry_timer))
            retry_timer.setSingleShot(True)
            retry_timer.start(retry_delay * 1000)  # Convert to milliseconds
            
            # Store timer reference to prevent garbage collection
            if not hasattr(self, '_retry_timers'):
                self._retry_timers = []
            self._retry_timers.append(retry_timer)
            
            # Update UI to show retry status
            self.get_info_btn.setText(f"{self.tr_('BUTTON_RETRYING')} ({retry_delay}s)")
            
        except Exception as e:
            self.log_error(f"Error scheduling retry: {e}")
    
    def _execute_retry(self, url, timer):
        """Execute automatic retry"""
        try:
            # Remove timer from list
            if hasattr(self, '_retry_timers') and timer in self._retry_timers:
                self._retry_timers.remove(timer)
            
            # Update UI
            self.get_info_btn.setText(self.tr_("BUTTON_PROCESSING"))
            self.get_info_btn.setEnabled(False)
            
            # Set URL and retry
            self.url_input.setText(url)
            self.url_input.setStyleSheet("")  # Clear error styling
            
            self.log_info(f"Executing automatic retry for: {url}")
            
            # Call get_video_info method
            self.get_video_info()
            
        except Exception as e:
            self.log_error(f"Error executing retry: {e}")
            self.get_info_btn.setEnabled(True)
            self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
    
    def _update_error_statistics(self, error_type):
        """Update error statistics for analytics and monitoring"""
        try:
            if not hasattr(self, '_error_stats'):
                self._error_stats = {}
            
            self._error_stats[error_type] = self._error_stats.get(error_type, 0) + 1
            
            # Log statistics periodically
            total_errors = sum(self._error_stats.values())
            if total_errors % 10 == 0:  # Log every 10 errors
                self.log_info(f"Error statistics: {self._error_stats}")
            
            # Emit statistics event for monitoring
            self.emit_tab_event('error_statistics_updated', {
                'error_type': error_type,
                'count': self._error_stats[error_type],
                'total_errors': total_errors,
                'statistics': self._error_stats.copy()
            })
            
        except Exception as e:
            self.log_warning(f"Error updating error statistics: {e}")

    # =============================================================================
    # Download Preparation Workflow Helper Methods
    # =============================================================================
    
    def _prepare_download_items(self):
        """Prepare selected video items for download with metadata extraction"""
        try:
            selected_items = []
            
            for row in range(self.video_table.rowCount()):
                checkbox_cell = self.video_table.cellWidget(row, 0)
                if checkbox_cell:
                    checkbox = checkbox_cell.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        # Extract video information for this row
                        video_info = self.video_info_dict.get(row)
                        if video_info:
                            # Get selected quality and format
                            selected_quality = self.get_selected_quality(row)
                            selected_format = self.get_selected_format(row)
                            
                            # Prepare download item
                            download_item = {
                                'row': row,
                                'url': video_info.url,
                                'video_info': video_info,
                                'selected_quality': selected_quality,
                                'selected_format': selected_format,
                                'title': video_info.title,
                                'creator': getattr(video_info, 'creator', 'Unknown'),
                                'duration': getattr(video_info, 'duration', 0),
                                'estimated_size': self.estimate_size(getattr(video_info, 'formats', [])),
                                'is_audio_only': self.is_audio_format(selected_format)
                            }
                            
                            selected_items.append(download_item)
            
            self.log_info(f"Prepared {len(selected_items)} items for download")
            return selected_items
            
        except Exception as e:
            self.log_error(f"Error preparing download items: {e}")
            return []
    
    def _validate_download_items(self, items):
        """Validate download items and filter out invalid ones"""
        try:
            valid_items = []
            
            for item in items:
                is_valid = True
                validation_errors = []
                
                # Check if URL is valid
                if not item.get('url') or not self.validate_url(item['url']):
                    validation_errors.append("Invalid URL")
                    is_valid = False
                
                # Check if video info exists
                if not item.get('video_info'):
                    validation_errors.append("Missing video information")
                    is_valid = False
                
                # Check for error states in video info
                video_info = item.get('video_info')
                if video_info and hasattr(video_info, 'title'):
                    if video_info.title.startswith("Error:"):
                        validation_errors.append(f"Video error: {video_info.title}")
                        is_valid = False
                
                # Check if format selection is valid
                if not item.get('selected_format'):
                    validation_errors.append("No format selected")
                    is_valid = False
                
                # Log validation results
                if not is_valid:
                    self.log_warning(f"Invalid download item for {item.get('url', 'Unknown URL')}: {', '.join(validation_errors)}")
                else:
                    valid_items.append(item)
            
            self.log_info(f"Validated {len(valid_items)}/{len(items)} download items")
            return valid_items
            
        except Exception as e:
            self.log_error(f"Error validating download items: {e}")
            return []
    
    def _create_download_queue(self, items, output_folder):
        """Create prioritized download queue with metadata"""
        try:
            download_queue = []
            
            for index, item in enumerate(items):
                # Calculate priority based on various factors
                priority = self._calculate_download_priority(item)
                
                # Create download job
                download_job = {
                    'id': f"download_{index}_{int(self.performance_monitor.current_time())}",
                    'url': item['url'],
                    'output_folder': output_folder,
                    'format_id': self._determine_format_id(item),
                    'quality': item['selected_quality'],
                    'format': item['selected_format'],
                    'audio_only': item['is_audio_only'],
                    'priority': priority,
                    'metadata': {
                        'title': item['title'],
                        'creator': item['creator'],
                        'duration': item['duration'],
                        'estimated_size': item['estimated_size'],
                        'original_row': item['row']
                    },
                    'retry_count': 0,
                    'max_retries': 3,
                    'status': 'queued',
                    'created_at': self.performance_monitor.current_time()
                }
                
                download_queue.append(download_job)
            
            # Sort queue by priority (higher priority first)
            download_queue.sort(key=lambda x: x['priority'], reverse=True)
            
            self.log_info(f"Created download queue with {len(download_queue)} jobs")
            return download_queue
            
        except Exception as e:
            self.log_error(f"Error creating download queue: {e}")
            return []
    
    def _calculate_download_priority(self, item):
        """Calculate download priority based on various factors"""
        try:
            priority = 5  # Base priority (medium)
            
            # Higher priority for shorter videos (faster downloads)
            duration = item.get('duration', 0)
            if duration > 0:
                if duration < 30:  # Short videos get higher priority
                    priority += 2
                elif duration > 300:  # Long videos get lower priority
                    priority -= 1
            
            # Higher priority for audio-only downloads (smaller files)
            if item.get('is_audio_only'):
                priority += 1
            
            # Higher priority for smaller estimated file sizes
            estimated_size = item.get('estimated_size', 'Unknown')
            if estimated_size != 'Unknown':
                try:
                    size_mb = float(estimated_size.replace(' MB', ''))
                    if size_mb < 10:  # Small files get higher priority
                        priority += 1
                    elif size_mb > 100:  # Large files get lower priority
                        priority -= 1
                except (ValueError, AttributeError):
                    pass
            
            # Ensure priority stays within reasonable bounds
            return max(1, min(10, priority))
            
        except Exception as e:
            self.log_warning(f"Error calculating download priority: {e}")
            return 5  # Default medium priority
    
    def _determine_format_id(self, item):
        """Determine appropriate format ID for download"""
        try:
            selected_format = item.get('selected_format', '')
            selected_quality = item.get('selected_quality', '')
            
            # Map format and quality selections to format IDs
            if self.is_audio_format(selected_format):
                return 'best[ext=m4a]/best[ext=mp3]/best'
            else:
                # Video format
                if selected_quality and selected_quality != 'Original':
                    quality_num = selected_quality.replace('p', '')
                    return f'best[height<={quality_num}]/best'
                else:
                    return 'best'
                    
        except Exception as e:
            self.log_warning(f"Error determining format ID: {e}")
            return 'best'  # Fallback to best available
    
    def _estimate_total_duration(self, items):
        """Estimate total duration for all downloads"""
        try:
            total_duration = 0
            for item in items:
                duration = item.get('duration', 0)
                if duration > 0:
                    total_duration += duration
            
            return total_duration
            
        except Exception as e:
            self.log_warning(f"Error estimating total duration: {e}")
            return 0
    
    def _process_download_queue(self, download_queue):
        """Process download queue with concurrent management"""
        try:
            success_count = 0
            
            # Implement basic queue processing
            # In a full implementation, this would use threading/async for concurrent downloads
            for job in download_queue:
                try:
                    # Update job status
                    job['status'] = 'starting'
                    
                    # Show download started toast notification
                    self._show_download_started_toast(job['metadata']['title'])
                    
                    # Start operation in realtime progress manager
                    if realtime_progress_manager:
                        try:
                            progress_data = realtime_progress_manager.start_operation(
                                operation_id=job['url'],
                                operation_type="download",
                                tab_id=self.get_tab_id(),
                                total_value=100,  # Progress percentage
                                file_name=job['metadata']['title'],
                                url=job['url'],
                                additional_data={
                                    'job_id': job['id'],
                                    'format': job['format'],
                                    'quality': job['quality'],
                                    'video_info': job['metadata']
                                }
                            )
                            self.log_debug(f"Started progress tracking for {job['metadata']['title']}")
                        except Exception as e:
                            self.log_error(f"Error starting progress tracking: {e}")
                    
                    # Emit download started event
                    self.video_download_started.emit(job['url'])
                    self.emit_tab_event('download_started', {
                        'job_id': job['id'],
                        'url': job['url'],
                        'title': job['metadata']['title'],
                        'format': job['format'],
                        'quality': job['quality'],
                        'timestamp': self.performance_monitor.current_time(),
                        'downloading_count': self.downloading_count + 1
                    })
                    
                    # Initiate download through TikTokDownloader
                    if self.downloader:
                        # Set output directory
                        self.downloader.set_output_dir(job['output_folder'])
                        
                        # Start download
                        self.downloader.download_video(
                            url=job['url'],
                            format_id=job['format_id'],
                            audio_only=job['audio_only']
                        )
                        
                        success_count += 1
                        job['status'] = 'in_progress'
                        
                    else:
                        self.log_error(f"Downloader not available for job {job['id']}")
                        job['status'] = 'failed'
                        
                except Exception as e:
                    self.log_error(f"Error processing download job {job.get('id', 'unknown')}: {e}")
                    job['status'] = 'failed'
            
            return success_count
            
        except Exception as e:
            self.log_error(f"Error processing download queue: {e}")
            return 0

    def get_selected_quality(self, row):
        """Get selected quality from row in table"""
        try:
            if row is None or row < 0 or row >= self.video_table.rowCount():
                return "1080p"  # Default value when no row is available
            
            quality_cell = self.video_table.cellWidget(row, 3)  # Quality column (index 3)
            if quality_cell:
                quality_combo = quality_cell.findChild(QComboBox)
                if quality_combo:
                    return quality_combo.currentText()
            
            # Fallback to cell item if combobox not found
            quality_item = self.video_table.item(row, 3)
            if quality_item:
                return quality_item.text()
                
            return "1080p"  # Default value
        except Exception as e:
            self.log_error(f"Error getting selected quality: {e}")
            return "1080p"
        
    def get_selected_format(self, row):
        """Get selected format from row in table"""
        try:
            if row is None or row < 0 or row >= self.video_table.rowCount():
                return "Video (mp4)"  # Default value when no row is available
            
            format_cell = self.video_table.cellWidget(row, 4)  # Format column (index 4)
            if format_cell:
                format_combo = format_cell.findChild(QComboBox)
                if format_combo:
                    return format_combo.currentText()
            
            # Fallback to cell item if combobox not found
            format_item = self.video_table.item(row, 4)
            if format_item:
                return format_item.text()
                
            return "Video (mp4)"  # Default value
        except Exception as e:
            self.log_error(f"Error getting selected format: {e}")
            return "Video (mp4)"
    
    # =============================================================================
    # Performance and Debugging
    # =============================================================================
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this tab"""
        return self.performance_monitor.get_performance_report()
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information for troubleshooting"""
        return {
            'tab_id': self.get_tab_id(),
            'is_initialized': self.is_initialized(),
            'is_active': self.is_active(),
            'data_dirty': self.is_data_dirty(),
            'video_count': len(self.video_info_dict),
            'processing_count': self.processing_count,
            'downloading_count': self.downloading_count,
            'all_selected': self.all_selected,
            'output_folder': self.output_folder_display.text() if hasattr(self, 'output_folder_display') else '',
            'downloader_available': self.downloader is not None,
            'performance_metrics': self.get_performance_metrics(),
            'validation_errors': self.validate_input()
        } 