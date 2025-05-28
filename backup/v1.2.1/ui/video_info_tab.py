from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableWidget, QComboBox,
                             QFileDialog, QCheckBox, QHeaderView, QMessageBox,
                             QTableWidgetItem, QProgressBar, QApplication, QDialog, QTextEdit, QMenu, QInputDialog, QSpacerItem, QSizePolicy, QDialogButtonBox)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
import os
import json
from localization import get_language_manager
from utils.downloader import TikTokDownloader, VideoInfo
from PyQt6.QtNetwork import QNetworkRequest, QNetworkAccessManager, QNetworkReply
from PyQt6.QtGui import QPixmap, QCursor, QAction
from datetime import datetime
from utils.db_manager import DatabaseManager
import requests
import shutil  # For file operations
import re
from PyQt6.QtWidgets import QToolTip
import sys
import subprocess  # Added import for subprocess

# Path to configuration file
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')

class VideoInfoTab(QWidget):
    """Tab displaying video information and downloading videos"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        # Initialize language manager
        self.lang_manager = get_language_manager()
        
        # Initialize variables to store video information
        self.video_info_dict = {}  # Dictionary with key as URL, value as VideoInfo
        
        # Counter for videos being processed
        self.processing_count = 0
        
        # Counter for videos being downloaded
        self.downloading_count = 0
        
        # Variable to track if all items are selected
        self.all_selected = False
        
        # Set up UI
        self.setup_ui()
        
        # Update language for all components
        self.update_language()
        
        # Load last output folder
        self.load_last_output_folder()
        
        # Initialize downloader
        self.downloader = TikTokDownloader()
        self.downloader.info_signal.connect(self.handle_video_info)
        self.downloader.progress_signal.connect(self.handle_progress)
        self.downloader.finished_signal.connect(self.handle_download_finished)
        # Connect to new API error signal
        self.downloader.api_error_signal.connect(self.handle_api_error)
        
        # Network manager for thumbnail loading
        self.network_manager = QNetworkAccessManager()
        
        # Connect to language change event if available
        if hasattr(parent, 'language_changed'):
            parent.language_changed.connect(self.update_language)
        
        # Update UI state
        self.update_button_states()
        
        # Initialize clipboard monitoring
        self.last_clipboard_text = ""
        # Check clipboard on init
        try:
            clipboard = QApplication.clipboard()
            if clipboard:
                self.last_clipboard_text = clipboard.text()
        except Exception as e:
            print(f"Error initializing clipboard: {e}")

    def setup_ui(self):
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # URL and Get Info section
        url_layout = QHBoxLayout()
        
        # URL Label
        self.url_label = QLabel(self.tr_("LABEL_VIDEO_URL"))
        url_layout.addWidget(self.url_label)
        
        # Create spacing to align URL input with output folder
        spacer_width = 18  # Adjusted to 70px for better alignment
        url_layout.addSpacing(spacer_width)
        
        # URL Input
        self.url_input = QLineEdit()
        self.url_input.setFixedHeight(30)
        # No longer setting fixed width - allow stretching with window
        self.url_input.setMinimumWidth(500)
        self.url_input.setPlaceholderText(self.tr_("PLACEHOLDER_VIDEO_URL"))
        # Connect returnPressed event to get_video_info function
        self.url_input.returnPressed.connect(self.get_video_info)
        url_layout.addWidget(self.url_input, 1)  # stretch factor 1 to expand when maximized
        
        # Get Info Button
        self.get_info_btn = QPushButton(self.tr_("BUTTON_GET_INFO"))
        self.get_info_btn.setFixedWidth(120)  # Fixed width
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
        # No longer setting fixed width - allow stretching with window
        self.output_folder_display.setMinimumWidth(500)
        self.output_folder_display.setPlaceholderText(self.tr_("PLACEHOLDER_OUTPUT_FOLDER"))
        output_layout.addWidget(self.output_folder_display, 1)  # stretch factor 1 to expand when maximized
        
        # Choose folder button
        self.choose_folder_btn = QPushButton(self.tr_("BUTTON_CHOOSE_FOLDER"))
        self.choose_folder_btn.setFixedWidth(120)  # Fixed width same as Get Info button
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
        
        # Select all / Unselect all button (combined into one)
        self.select_toggle_btn = QPushButton(self.tr_("BUTTON_SELECT_ALL"))
        self.select_toggle_btn.setFixedWidth(150)
        self.select_toggle_btn.clicked.connect(self.toggle_select_all)
        self.all_selected = False  # Current state (False: not all selected)
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
        
        # Add left button group to layout
        options_layout.addLayout(left_buttons_layout)
        
        # Add stretch to push Download button all the way to the right
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
        
        # Update initial button states
        self.update_button_states()

    def show_context_menu(self, position):
        """Display right-click menu for video table"""
        # Get current row and column position
        index = self.video_table.indexAt(position)
        if not index.isValid():
            return
            
        row = index.row()
        column = index.column()
        
        if row < 0 or row >= self.video_table.rowCount():
            return
        
        # Create context menu
        context_menu = QMenu(self)
        
        # Determine data type based on column
        if column == 1:  # Title
            # Get title from item
            item = self.video_table.item(row, column)
            if item and item.text():
                # Get full title from video_info_dict if available
                full_title = item.text()  # Default to displayed text
                if row in self.video_info_dict:
                    video_info = self.video_info_dict[row]
                    # Prioritize caption if available as it usually contains the most complete content
                    if hasattr(video_info, 'caption') and video_info.caption:
                        full_title = video_info.caption
                    # If no caption, try using original_title
                    elif hasattr(video_info, 'original_title') and video_info.original_title:
                        full_title = video_info.original_title
                    # If not, use title
                    elif hasattr(video_info, 'title'):
                        full_title = video_info.title
                
                # Add Copy action
                copy_action = QAction(self.tr_("CONTEXT_COPY_TITLE"), self)
                copy_action.triggered.connect(lambda: self.copy_to_clipboard(full_title, "title"))
                context_menu.addAction(copy_action)
        
        elif column == 2:  # Creator
            # Get creator from item
            item = self.video_table.item(row, column)
            if item and item.text():
                # Add Copy action
                copy_action = QAction(self.tr_("CONTEXT_COPY_CREATOR"), self)
                copy_action.triggered.connect(lambda: self.copy_to_clipboard(item.text(), "creator"))
                context_menu.addAction(copy_action)
        
        elif column == 7:  # Hashtags
            # Get hashtags from item
            item = self.video_table.item(row, column)
            if item and item.text():
                # Add Copy action
                copy_action = QAction(self.tr_("CONTEXT_COPY_HASHTAGS"), self)
                copy_action.triggered.connect(lambda: self.copy_to_clipboard(item.text(), "hashtags"))
                context_menu.addAction(copy_action)
                
        # Common functions for all columns
        # Add separator if there are previous actions
        if not context_menu.isEmpty():
            context_menu.addSeparator()
        
        # Get video information
        video_info = None
        if row in self.video_info_dict:
            video_info = self.video_info_dict[row]
        
        if video_info:
            # Check if output folder has been selected
            has_output_folder = bool(self.output_folder_display.text())
            
            # Ensure title attribute exists
            if not hasattr(video_info, 'title') or video_info.title is None or video_info.title.strip() == "":
                from datetime import datetime
                default_title = f"Video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                setattr(video_info, 'title', default_title)
                print(f"DEBUG - Created default title for video without title: {default_title}")
            
            # Check if video has an error
            has_error = False
            if hasattr(video_info, 'title'):
                has_error = video_info.title.startswith("Error:")
            
            # Only show Rename if video has no errors and output folder is selected
            # Removed hasattr(video_info, 'title') condition to allow renaming videos without titles
            if not has_error and has_output_folder and hasattr(video_info, 'url'):
                # Action Rename Video - Allow changing video name before downloading
                rename_action = QAction(self.tr_("CONTEXT_RENAME_VIDEO"), self)
                rename_action.triggered.connect(lambda: self.rename_video(row))
                context_menu.addAction(rename_action)
                
                # Add separator
                context_menu.addSeparator()
        
        # Action Delete Video - available in all cases
        delete_action = QAction(self.tr_("CONTEXT_DELETE"), self)
        delete_action.triggered.connect(lambda: self.delete_row(row))
        context_menu.addAction(delete_action)
        
        # Show menu if it has actions
        if not context_menu.isEmpty():
            context_menu.exec(QCursor.pos())

    def rename_video(self, row):
        """Allow users to rename video before downloading"""
        # Check if video_info exists
        if row not in self.video_info_dict:
            return
            
        video_info = self.video_info_dict[row]
        
        # Get current title
        current_title = video_info.title if hasattr(video_info, 'title') else ""
        
        # If no title, create default title from timestamp
        if not current_title:
            from datetime import datetime
            current_title = f"Video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"DEBUG - Creating default title for empty video title: {current_title}")
            
        # Show dialog to enter new name
        new_title, ok = QInputDialog.getText(
            self, 
            self.tr_("DIALOG_RENAME_TITLE"),
            self.tr_("DIALOG_ENTER_NEW_NAME"), 
            QLineEdit.EchoMode.Normal, 
            current_title
        )
        
        # Check if user clicked OK and new name is not empty
        if ok and new_title:
            # Clean filename to avoid invalid characters
            import re
            clean_title = re.sub(r'[\\/*?:"<>|]', '', new_title).strip()
            
            if clean_title:
                # Save original title to original_title variable if it doesn't exist
                if not hasattr(video_info, 'original_title'):
                    setattr(video_info, 'original_title', current_title)
                    
                # Update new name
                setattr(video_info, 'title', clean_title)
                
                # Add custom_title attribute
                setattr(video_info, 'custom_title', clean_title)
                
                # Update UI - title column in table
                title_cell = self.video_table.item(row, 1)
                if title_cell:
                    title_cell.setText(clean_title)
                    title_cell.setToolTip(clean_title)
                
                # Show success message
                if self.parent and self.parent.status_bar:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_RENAMED_VIDEO").format(clean_title))
                    
                print(f"DEBUG - Renamed video from '{current_title}' to '{clean_title}'")
            else:
                # Show error message if new name is invalid
                QMessageBox.warning(
                    self, 
                    self.tr_("DIALOG_ERROR"), 
                    self.tr_("DIALOG_INVALID_NAME")
                )

    def create_video_table(self):
        """Create table to display video information"""
        self.video_table = QTableWidget()
        self.video_table.setColumnCount(8)  # Reduced from 9 to 8 by removing Caption column
        
        # Set up headers
        self.update_table_headers()
        
        # Bỏ in đậm cho header để tiết kiệm không gian
        header_font = self.video_table.horizontalHeader().font()
        header_font.setBold(False)
        self.video_table.horizontalHeader().setFont(header_font)
        
        # Set table properties
        self.video_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Set custom column sizes
        self.video_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Select - checkbox column
        self.video_table.setColumnWidth(0, 50)
        
        self.video_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title - stretches
        
        self.video_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Creator
        self.video_table.setColumnWidth(2, 100)
        
        self.video_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Quality
        self.video_table.setColumnWidth(3, 85)  # Giảm từ 80 xuống 85 để vừa đủ cho "Chất Lượng"
        
        self.video_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Format
        self.video_table.setColumnWidth(4, 85)  # Tăng từ 75 lên 85 để hiển thị mũi tên dropdown
        
        self.video_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Duration
        self.video_table.setColumnWidth(5, 90)
        
        self.video_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Size
        self.video_table.setColumnWidth(6, 75)
        
        # Removed Caption column (index 7)
        
        self.video_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Hashtags 
        self.video_table.setColumnWidth(7, 150)  # Giảm từ 180 xuống 150
        
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
    
    def set_table_row_height(self):
        """Set row height for single-line display in the video table"""
        for row in range(self.video_table.rowCount()):
            self.video_table.setRowHeight(row, 25)  # Set height for single-line display

    def update_output_folder(self, folder):
        """Update output folder path"""
        self.output_folder_display.setText(folder)
        
        # Update output directory for downloader
        self.downloader.set_output_dir(folder)
        
        # Save through parent MainWindow instead of directly
        if hasattr(self, 'parent') and hasattr(self.parent, 'save_config'):
            self.parent.save_config('last_output_folder', folder)
            
            # Log to debug file
            try:
                log_file = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else 
                                      os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'log.txt')
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"[{datetime.now()}] Video_info_tab update_output_folder called: Saving '{folder}' to config via parent\n")
            except:
                pass
        else:
            # Fallback to old method if parent not available
            self.save_last_output_folder(folder)

    def choose_output_folder(self):
        """Choose output folder"""
        # Use current folder as starting point if available
        start_folder = self.output_folder_display.text() if self.output_folder_display.text() else ""
        
        folder = QFileDialog.getExistingDirectory(
            self, self.tr_("MENU_CHOOSE_FOLDER"), start_folder)
        if folder:
            self.update_output_folder(folder)
            if self.parent:
                self.parent.output_folder = folder
                self.parent.status_bar.showMessage(self.tr_("STATUS_FOLDER_SET").format(folder))
                
                # Log to debug file that folder was chosen
                try:
                    log_file = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else 
                                          os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'log.txt')
                    with open(log_file, 'a', encoding='utf-8') as log:
                        log.write(f"[{datetime.now()}] choose_output_folder called: Selected folder '{folder}'\n")
                except:
                    pass

    def load_last_output_folder(self):
        """Load last output folder from config"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    output_dir = config.get('output_dir', '')
                    if output_dir and os.path.exists(output_dir):
                        self.output_dir = output_dir
                        self.output_dir_label.setText(output_dir)
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_last_output_folder(self, folder):
        """Save last output folder path to configuration file"""
        try:
            # Use correct config path for both exe and dev environment
            if getattr(sys, 'frozen', False):
                # If running as exe
                config_file = os.path.join(os.path.dirname(sys.executable), 'config.json')
            else:
                # If running in dev mode
                config_file = CONFIG_FILE
                
            # Log which file we're saving to
            try:
                log_file = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else 
                                      os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'log.txt')
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"[{datetime.now()}] save_last_output_folder: Saving '{folder}' to '{config_file}'\n")
            except:
                pass
            
            # Create config file if it doesn't exist
            config = {}
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    content = f.read().strip()
                    if content:  # Only try to parse if not empty
                        config = json.loads(content)
            
            # Update output folder
            config['last_output_folder'] = folder
            
            # Save configuration
            with open(config_file, 'w') as f:
                json.dump(config, f)
                
            # Verify the file was written correctly
            with open(config_file, 'r') as f:
                content = f.read().strip()
                if content:
                    try:
                        log_file = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else 
                                              os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'log.txt')
                        with open(log_file, 'a', encoding='utf-8') as log:
                            log.write(f"[{datetime.now()}] save_last_output_folder verification: '{content}'\n")
                    except:
                        pass
        except Exception as e:
            # Log error
            try:
                log_file = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else 
                                      os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'log.txt')
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"[{datetime.now()}] Error saving last output folder: {str(e)}\n")
            except:
                pass
            print(f"Error saving last output folder: {e}")

    def get_video_info(self):
        """Get video information from URL"""
        url_input = self.url_input.text().strip()
        if not url_input:
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("DIALOG_NO_VIDEOS"))
            return

        # Check if output folder has been set
        if not self.output_folder_display.text():
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("DIALOG_NO_OUTPUT_FOLDER"))
            return
        
        # Handle multiple URLs (separated by whitespace)
        new_urls = url_input.split()
        
        # Create list of URLs already in table
        existing_urls = []
        for video_info in self.video_info_dict.values():
            existing_urls.append(video_info.url)
        
        # Filter out new URLs not yet in the table
        urls_to_process = []
        for url in new_urls:
            if url not in existing_urls:
                urls_to_process.append(url)
            else:
                # Notify URL already exists
                print(f"URL already exists in table: {url}")
        
        # If no new URLs to process
        if not urls_to_process:
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_NO_NEW_URLS"))
            return
            
        # Reset counter
        self.processing_count = len(urls_to_process)
        
        # Disable Get Info button while fetching information
        self.get_info_btn.setEnabled(False)
        self.get_info_btn.setText(self.tr_("STATUS_GETTING_INFO_SHORT"))
        self.url_input.setEnabled(False)
        
        # Update status
        if self.parent:
            # Display clear message on status bar
            if len(urls_to_process) > 1:
                self.parent.status_bar.showMessage(self.tr_("STATUS_GETTING_INFO_MULTIPLE").format(len(urls_to_process)))
            else:
                self.parent.status_bar.showMessage(self.tr_("STATUS_GETTING_INFO_SHORT"))
        
        # Request immediate UI update to show notification
        QApplication.processEvents()
        
        # Start getting video information from TikTokDownloader for new URLs
        for url in urls_to_process:
            # Call get_video_info method of TikTokDownloader
            # Results will be processed by on_video_info_received through the signal
            self.downloader.get_video_info(url)
            
            # Update UI after each request to ensure responsiveness
            QApplication.processEvents()

    def delete_row(self, row):
        """Delete a row from the table"""
        self.video_table.removeRow(row)
        # Update button states
        self.update_button_states()

    def delete_all_videos(self):
        """Delete all videos from the table"""
        reply = QMessageBox.question(
            self, self.tr_("DIALOG_CONFIRM_DELETION"), 
            self.tr_("DIALOG_CONFIRM_DELETE_ALL"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.video_table.setRowCount(0)
            self.video_info_dict.clear()
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_REFRESHED"))
            # Update button states
            self.update_button_states()

    def download_videos(self):
        """Download selected videos"""
        if not self.check_output_folder():
            return
        
        # Create detailed list for downloading
        download_queue = []
        videos_already_exist = []
        selected_count = 0
        
        # Count total selected videos first
        for row in range(self.video_table.rowCount()):
            checkbox_cell = self.video_table.cellWidget(row, 0)
            if checkbox_cell:
                checkbox = checkbox_cell.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected_count += 1
        
        # Variable to store user choice for all existing files
        overwrite_all = None  # None = not chosen, True = overwrite all, False = skip all
        
        # Iterate through each row in the table
        for row in range(self.video_table.rowCount()):
            checkbox_cell = self.video_table.cellWidget(row, 0)
            if checkbox_cell:
                checkbox = checkbox_cell.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    # Collect all necessary information
                    # Check if row exists in video_info_dict
                    if row not in self.video_info_dict:
                        print(f"DEBUG - Error: Row {row} not found in video_info_dict, skipping this video")
                        continue
                        
                    # Get URL from video_info_dict
                    url = self.video_info_dict[row].url
                    
                    # Get video title to display in notification
                    title = self.video_info_dict[row].title
                    
                    # Get selected quality
                    quality_cell = self.video_table.cellWidget(row, 3)
                    quality = quality_cell.findChild(QComboBox).currentText() if quality_cell else "720p"
                    
                    # Get selected format
                    format_cell = self.video_table.cellWidget(row, 4)
                    format_str = format_cell.findChild(QComboBox).currentText() if format_cell else self.tr_("FORMAT_VIDEO_MP4")
                    
                    # Check if MP3 format is selected and FFmpeg is not available
                    is_mp3 = format_str == self.tr_("FORMAT_AUDIO_MP3")
                    if is_mp3 and hasattr(self.parent, 'ffmpeg_available') and not self.parent.ffmpeg_available:
                        # Show error message
                        QMessageBox.warning(
                            self,
                            self.tr_("DIALOG_WARNING"),
                            f"{self.tr_('DIALOG_FFMPEG_MISSING')}\n\n"
                            f"{self.tr_('DIALOG_MP3_UNAVAILABLE')}\n\n"
                            f"▶ {self.tr_('DIALOG_SEE_README')} (README.md)"
                        )
                        
                        # Show status message
                        if self.parent:
                            self.parent.status_bar.showMessage(self.tr_("STATUS_FFMPEG_MISSING"), 5000)
                        
                        # Skip this video
                        continue
                    
                    # Get format_id based on quality and format
                    format_id = self.get_format_id(url, quality, format_str)

                    # Determine file extension based on format
                    is_audio = format_str == self.tr_("FORMAT_AUDIO_MP3") or "audio" in format_id.lower() or "bestaudio" in format_id.lower()
                    ext = "mp3" if is_audio else "mp4"
                    
                    # Check if title is empty before continuing
                    if not title.strip() or title.strip().startswith('#'):
                        # Display dialog to enter new name for video
                        default_name = f"Video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        new_title, ok = QInputDialog.getText(
                            self, 
                            self.tr_("DIALOG_RENAME_TITLE"),
                            self.tr_("DIALOG_ENTER_NAME_REQUIRED"), 
                            QLineEdit.EchoMode.Normal, 
                            default_name
                        )
                        
                        if not ok or not new_title.strip():
                            # User canceled or didn't enter a name, skip this video
                            print(f"DEBUG - User cancelled entering required name for video without title")
                            continue
                        
                        # Clean filename to avoid invalid characters
                        import re
                        clean_title = re.sub(r'[\\/*?:"<>|]', '', new_title).strip()
                        
                        # Update title in video_info_dict
                        if row in self.video_info_dict:
                            self.video_info_dict[row].custom_title = new_title
                            # Save new title to display in Downloaded Videos tab
                            self.video_info_dict[row].title = new_title
                            print(f"DEBUG - New title set for video without title: '{new_title}'")
                        
                        # Update title in download_queue
                        title = new_title
                    else:
                        # Clean video name, remove hashtags to create filename
                        clean_title = title
                        # Remove any remaining hashtags if present
                        import re
                        clean_title = re.sub(r'#\S+', '', clean_title).strip()
                        # Remove invalid characters for filename
                        clean_title = re.sub(r'[\\/*?:"<>|]', '', clean_title).strip()
                    
                    # Create full file path
                    output_dir = self.output_folder_display.text()
                    output_file = os.path.join(output_dir, f"{clean_title}.{ext}")

                    # Check if video already exists
                    db_manager = DatabaseManager()
                    existing_video = db_manager.get_download_by_url(url)
                    
                    # Check if file already exists on disk
                    file_exists = os.path.exists(output_file)
                    
                    if existing_video:
                        # Video already exists in database
                        videos_already_exist.append(title)
                    elif file_exists:
                        # File exists on disk but not in database
                        
                        # If user has already chosen "Apply to all", use that choice
                        if overwrite_all is not None:
                            if overwrite_all:
                                # User chose to overwrite all
                                download_queue.append({
                                    'url': url,
                                    'title': title,
                                    'format_id': format_id,
                                    'clean_title': clean_title,
                                    'ext': ext
                                })
                            else:
                                # User chose to skip all
                                continue
                        else:
                            # Display message asking if user wants to overwrite
                            msg_box = QMessageBox(self)
                            msg_box.setWindowTitle(self.tr_("DIALOG_FILE_EXISTS"))
                            
                            # Collect list of existing files
                            file_name = f"{clean_title}.{ext}"
                            file_exists_list = [file_name]
                            remaining_files = 0
                            
                            # If multiple files are selected, collect list of existing files
                            if selected_count > 1:
                                # Iterate through other rows to check for existing files
                                for check_row in range(self.video_table.rowCount()):
                                    # Skip current row because it's already in the list
                                    if check_row == row:
                                        continue
                                        
                                    check_checkbox_cell = self.video_table.cellWidget(check_row, 0)
                                    if check_checkbox_cell:
                                        check_checkbox = check_checkbox_cell.findChild(QCheckBox)
                                        if check_checkbox and check_checkbox.isChecked():
                                            # Check if row exists in video_info_dict
                                            if check_row not in self.video_info_dict:
                                                continue
                                                
                                            # Get video information
                                            check_title = self.video_info_dict[check_row].title
                                            
                                            # Get selected format
                                            check_format_cell = self.video_table.cellWidget(check_row, 4)
                                            check_format_str = check_format_cell.findChild(QComboBox).currentText() if check_format_cell else self.tr_("FORMAT_VIDEO_MP4")
                                            
                                            # Determine file extension
                                            check_is_audio = check_format_str == self.tr_("FORMAT_AUDIO_MP3")
                                            check_ext = "mp3" if check_is_audio else "mp4"
                                            
                                            # Clean filename
                                            import re
                                            check_clean_title = re.sub(r'#\S+', '', check_title).strip()
                                            check_clean_title = re.sub(r'[\\/*?:"<>|]', '', check_clean_title).strip()
                                            
                                            # Create full file path
                                            check_output_file = os.path.join(output_dir, f"{check_clean_title}.{check_ext}")
                                            
                                            # Check if file already exists
                                            if os.path.exists(check_output_file):
                                                # If there are less than 5 files, add to list
                                                if len(file_exists_list) < 5:
                                                    file_exists_list.append(f"{check_clean_title}.{check_ext}")
                                                else:
                                                    remaining_files += 1
                            
                            # Create confirmation message
                            confirmation_text = self.tr_("DIALOG_FILE_EXISTS_MESSAGE")
                            
                            # Add list of existing files
                            files_list = "\n".join([f"• {f}" for f in file_exists_list])
                            # If there are remaining files, add additional information
                            if remaining_files > 0:
                                files_list += f"\n• ... and {remaining_files} other files"
                            
                            confirmation_text += f"\n\n{files_list}"
                            
                            msg_box = QMessageBox(self)
                            msg_box.setWindowTitle(self.tr_("DIALOG_FILE_EXISTS"))
                            msg_box.setText(confirmation_text)
                            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
                            msg_box.setIcon(QMessageBox.Icon.Question)
                            
                            # Set minimum size
                            msg_box.setMinimumWidth(500)
                            msg_box.setMinimumHeight(200)
                            
                            # Determine current theme
                            current_theme = "dark"
                            if hasattr(self, 'parent') and hasattr(self.parent, 'current_theme'):
                                current_theme = self.parent.current_theme
                            
                            # Style for message box based on current theme
                            if current_theme == "light":
                                msg_box.setStyleSheet("""
                                    QMessageBox {
                                        background-color: #f0f0f0;
                                        color: #333333;
                                    }
                                    QMessageBox QLabel {
                                        color: #333333;
                                        font-size: 13px;
                                        min-height: 100px;
                                    }
                                    QPushButton {
                                        background-color: #0078d7;
                                        color: white;
                                        border: none;
                                        padding: 6px 20px;
                                        margin: 6px;
                                        border-radius: 4px;
                                        min-width: 60px;
                                    }
                                    QPushButton:hover {
                                        background-color: #1084d9;
                                    }
                                    QPushButton:pressed {
                                        background-color: #0063b1;
                                    }
                                    QPushButton:default {
                                        background-color: #0078d7;
                                        border: 1px solid #80ccff;
                                    }
                                    QCheckBox {
                                        color: #333333;
                                        spacing: 8px;
                                    }
                                    QCheckBox::indicator {
                                        width: 16px;
                                        height: 16px;
                                    }
                                """)
                            else:
                                msg_box.setStyleSheet("""
                                    QMessageBox {
                                        background-color: #2d2d2d;
                                        color: #e0e0e0;
                                    }
                                    QMessageBox QLabel {
                                        color: #e0e0e0;
                                        font-size: 13px;
                                        min-height: 100px;
                                    }
                                    QPushButton {
                                        background-color: #0078d7;
                                        color: white;
                                        border: none;
                                        padding: 6px 20px;
                                        margin: 6px;
                                        border-radius: 4px;
                                        min-width: 60px;
                                    }
                                    QPushButton:hover {
                                        background-color: #1084d9;
                                    }
                                    QPushButton:pressed {
                                        background-color: #0063b1;
                                    }
                                    QPushButton:default {
                                        background-color: #0078d7;
                                        border: 1px solid #80ccff;
                                    }
                                    QCheckBox {
                                        color: #e0e0e0;
                                        spacing: 8px;
                                    }
                                    QCheckBox::indicator {
                                        width: 16px;
                                        height: 16px;
                                    }
                                """)
                            
                            # Add "Apply to all" checkbox if more than one video is selected
                            apply_all_checkbox = None
                            if selected_count > 1:
                                apply_all_checkbox = QCheckBox(self.tr_("DIALOG_APPLY_TO_ALL"))
                                # Add checkbox to button box (same row as buttons)
                                button_box = msg_box.findChild(QDialogButtonBox)
                                if button_box:
                                    # Add checkbox to left side of button box
                                    button_layout = button_box.layout()
                                    button_layout.insertWidget(0, apply_all_checkbox, 0, Qt.AlignmentFlag.AlignLeft)
                                    # Add extra space between checkbox and buttons
                                    button_layout.insertSpacing(1, 50)
                                    # Style checkbox to be more visually appealing (not using bold font)
                                    apply_all_checkbox.setStyleSheet("QCheckBox { margin-right: 15px; }")
                            
                            # Show message box
                            reply = msg_box.exec()
                            
                            if reply == QMessageBox.StandardButton.No:
                                # User chose not to overwrite
                                if apply_all_checkbox and apply_all_checkbox.isChecked():
                                    overwrite_all = False  # Apply "not overwrite" to all
                                continue
                            
                            elif reply == QMessageBox.StandardButton.Yes:
                                # User chose to overwrite
                                if apply_all_checkbox and apply_all_checkbox.isChecked():
                                    overwrite_all = True  # Apply "overwrite" to all
                                
                                # Add to download queue
                                download_queue.append({
                                    'url': url,
                                    'title': title,
                                    'format_id': format_id,
                                    'clean_title': clean_title,
                                    'ext': ext
                                })
                    else:
                        # Video doesn't exist yet, add to download queue
                        download_queue.append({
                            'url': url,
                            'title': title,
                            'format_id': format_id,
                            'clean_title': clean_title,
                            'ext': ext
                        })
        
        # If any videos already exist, show notification
        if videos_already_exist:
            existing_titles = "\n".join([f"- {title}" for title in videos_already_exist])
            msg = f"{self.tr_('DIALOG_VIDEOS_ALREADY_EXIST')}\n{existing_titles}"
            QMessageBox.information(self, self.tr_("DIALOG_VIDEOS_EXIST"), msg)
        
        # If no videos are selected for download
        if selected_count == 0:
            if not videos_already_exist:
                QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("DIALOG_NO_VIDEOS_SELECTED"))
            return
            
        # If all selected videos already exist (no new videos to download)
        if not download_queue:
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_ALREADY_EXIST"))
            return
            
        # Reset download count
        self.downloading_count = len(download_queue)
        
        # Set total video count
        self.total_videos = len(download_queue)
            
        # Reset successful downloads count
        self.success_downloads = 0
            
        # Disable Download button while downloading
        self.download_btn.setEnabled(False)
        self.download_btn.setText(self.tr_("STATUS_DOWNLOADING_SHORT"))
            
        # Show notification about number of videos being downloaded
        if self.parent:
            if self.downloading_count > 1:
                self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOADING_MULTIPLE").format(self.downloading_count))
            else:
                video_title = download_queue[0]['title']
                self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOADING_WITH_TITLE").format(video_title))
                
        # Update UI immediately to show notification
        QApplication.processEvents()
                    
        # Iterate through each video in the queue to download
        for video_info in download_queue:
            # Always remove watermark
            remove_watermark = True
            
            # Get pre-calculated information
            clean_title = video_info.get('clean_title', '')
            ext = video_info.get('ext', 'mp4')
            
            # If no information, recalculate (using old code)
            if not clean_title:
                # Clean video name, remove hashtags to create filename
                clean_title = video_info['title']
                # Remove any remaining hashtags if present
                import re
                clean_title = re.sub(r'#\S+', '', clean_title).strip()
                # Remove invalid characters for filenames
                clean_title = re.sub(r'[\\/*?:"<>|]', '', clean_title).strip()
                
                # Determine file extension based on format
                is_audio = "audio" in video_info['format_id'].lower() or "bestaudio" in video_info['format_id'].lower()
                ext = "mp3" if is_audio else "mp4"
            
            # CHECK IF TITLE IS EMPTY AND MOVED TO THE TOP
            # AND CHECK BEFORE ADDING TO DOWNLOAD_QUEUE
            
            # Set output template with cleaned title
            output_dir = self.output_folder_display.text()
            
            # Create full file path
            output_file = os.path.join(output_dir, f"{clean_title}.{ext}")
            output_template = os.path.join(output_dir, f"{clean_title}.%(ext)s")
            
            # Start downloading with yt-dlp
            try:
                # First, check if thumbnail already exists
                thumbnails_dir = os.path.join(output_dir, "thumbnails")
                if not os.path.exists(thumbnails_dir):
                    os.makedirs(thumbnails_dir)
                
                # Get video ID from URL (part before '?')
                video_id = video_info['url'].split('/')[-1].split('?')[0]
                
                # Variable for download
                format_id = video_info['format_id']
                remove_watermark = True
                url = video_info['url']
                
                # Check if file already exists to decide if force overwrite is needed
                force_overwrite = True  # User has confirmed this earlier
                
                # If file exists, delete old file before downloading
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                        print(f"Removed existing file: {output_file}")
                    except Exception as e:
                        print(f"Error removing existing file: {str(e)}")
                
                # Call download method
                self.downloader.download_video(
                    url=url, 
                    output_template=output_template, 
                    format_id=format_id, 
                    remove_watermark=remove_watermark,
                    audio_only=(ext == "mp3"),
                    force_overwrite=force_overwrite
                )
                
                # Update download count if there's an error
                if self.parent:
                    if self.downloading_count > 1:
                        self.parent.status_bar.showMessage(
                            self.tr_("STATUS_DOWNLOADING_MULTIPLE_PROGRESS").format(
                                self.success_downloads, 
                                self.total_videos, 
                                video_info['title']
                            )
                        )
                    else:
                        self.parent.status_bar.showMessage(
                            self.tr_("STATUS_DOWNLOADING_WITH_TITLE").format(video_info['title'])
                        )
            except Exception as e:
                print(f"Error starting download: {e}")
                self.downloading_count -= 1
                if self.parent:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOAD_ERROR").format(str(e)))
        
        # If all videos have finished downloading, re-enable Download button
        if self.downloading_count <= 0:
            self.download_btn.setEnabled(True)
            self.download_btn.setText(self.tr_("BUTTON_DOWNLOAD"))
            print(f"DEBUG - All downloads finished, reset download button")
            # Reset status bar when all downloads are complete
            if self.parent and self.parent.status_bar:
                self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOAD_SUCCESS"))

    def check_output_folder(self):
        """Check if output folder exists"""
        if not self.output_folder_display.text():
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("DIALOG_NO_OUTPUT_FOLDER"))
            return False
        
        # Check if folder exists
        output_folder = self.output_folder_display.text()
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), 
                        self.tr_("DIALOG_FOLDER_NOT_FOUND").format(output_folder))
                return False
        
        return True

    def get_format_id(self, url, quality, format_str):
        """Get format_id based on quality and format"""
        # Check if video_info is in dict
        video_info = None
        for row, info in self.video_info_dict.items():
            if info.url == url:
                video_info = info
                break
                
        if not video_info or not video_info.formats:
            return "best"  # Default to best if not found
            
        # Check if format is video or audio
        is_audio = format_str == self.tr_("FORMAT_AUDIO_MP3")
        
        if is_audio:
            # Find best audio format
            for fmt in video_info.formats:
                if fmt.get('is_audio', False):
                    return fmt['format_id']
            # If no specific audio format found, use bestaudio
            return "bestaudio/best"
        else:
            # If quality is "Audio", this is a logic error, choose best video
            if quality == "Audio":
                return "best"
                
            # Find format that matches quality
            for fmt in video_info.formats:
                if fmt.get('quality', '') == quality and not fmt.get('is_audio', False):
                    return fmt['format_id']
            
            # If no exact match found, find closest format
            # Convert quality to number
            target_quality = 0
            if quality == "1080p":
                target_quality = 1080
            elif quality == "720p":
                target_quality = 720
            elif quality == "480p":
                target_quality = 480
            elif quality == "360p":
                target_quality = 360
            else:
                try:
                    # Try converting directly if format is like "540p"
                    target_quality = int(quality.replace('p', ''))
                except:
                    pass
            
            # Find closest format
            closest_fmt = None
            min_diff = float('inf')
            
            for fmt in video_info.formats:
                if fmt.get('is_audio', False):
                    continue
                    
                fmt_height = fmt.get('height', 0)
                diff = abs(fmt_height - target_quality)
                
                if diff < min_diff:
                    min_diff = diff
                    closest_fmt = fmt
            
            if closest_fmt:
                return closest_fmt['format_id']
                
            return "best"  # Default if not found

    def tr_(self, key):
        """Translate using current language manager"""
        if hasattr(self, 'lang_manager') and self.lang_manager:
            return self.lang_manager.tr(key)
        return key  # Return key if no language manager

    def format_tooltip_text(self, text):
        """Format tooltip text with line breaks for better readability"""
        if not text:
            return ""
        
        # Replace line breaks at periods, commas, and question marks with a space
        formatted_text = re.sub(r'([.!?]) ', r'\1\n', text)
        # Replace line breaks at commas with a space
        formatted_text = re.sub(r'([,]) ', r'\1\n', formatted_text)
        
        # Replace line breaks at spaces
        formatted_text = re.sub(r' (#[^\s#]+)', r'\n\1', formatted_text)
        
        return formatted_text

    def update_language(self):
        """Update language for all components"""
        # Update labels
        self.url_label.setText(self.tr_("LABEL_VIDEO_URL"))
        self.output_label.setText(self.tr_("LABEL_OUTPUT_FOLDER"))
        
        # Update placeholders
        self.url_input.setPlaceholderText(self.tr_("PLACEHOLDER_VIDEO_URL"))
        self.output_folder_display.setPlaceholderText(self.tr_("PLACEHOLDER_OUTPUT_FOLDER"))
        
        # Update buttons
        self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
        self.choose_folder_btn.setText(self.tr_("BUTTON_CHOOSE_FOLDER"))
        
        # Update toggle button text based on selection state
        if hasattr(self, 'select_toggle_btn'):
            self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL") if not self.all_selected else self.tr_("BUTTON_UNSELECT_ALL"))
        
        # Update other buttons
        if hasattr(self, 'delete_selected_btn'):
            self.delete_selected_btn.setText(self.tr_("BUTTON_DELETE_SELECTED"))
        
        if hasattr(self, 'delete_all_btn'):
            self.delete_all_btn.setText(self.tr_("BUTTON_DELETE_ALL"))
        
        if hasattr(self, 'download_btn'):
            self.download_btn.setText(self.tr_("BUTTON_DOWNLOAD"))
        
        # Update table headers
        self.update_table_headers()
        
        # Force update of the UI
        self.update()

    def update_table_headers(self):
        """Update table headers based on current language"""
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
        self.video_table.setHorizontalHeaderLabels(headers)

    # New method to apply colors based on theme
    def apply_theme_colors(self, theme):
        """Apply colors based on theme"""
        # Update colors for components
        # Determine colors based on theme
        if theme == "dark":
            # Colors for dark mode
            url_placeholder_color = "#8a8a8a"
            url_text_color = "#ffffff"
            folder_text_color = "#cccccc"
            
            # Style for table in dark mode
            table_style = """
                QTableWidget::item:hover {
                    background-color: rgba(80, 140, 255, 0.15);
                }
            """
            
            # Style for scrollbar in dark mode
            scrollbar_style = """
                QScrollBar:vertical {
                    border: none;
                    background: rgba(80, 80, 80, 0.2);
                    width: 8px;
                    margin: 0px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background: rgba(180, 180, 180, 0.5);
                    min-height: 20px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(180, 180, 180, 0.7);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
            """
        else:
            # Colors for light mode
            url_placeholder_color = "#888888"
            url_text_color = "#333333"
            folder_text_color = "#555555"
            
            # Style for table in light mode
            table_style = """
                QTableWidget::item:hover {
                    background-color: rgba(0, 120, 215, 0.1);
                }
            """
            
            # Style for scrollbar in light mode
            scrollbar_style = """
                QScrollBar:vertical {
                    border: none;
                    background: rgba(0, 0, 0, 0.05);
                    width: 8px;
                    margin: 0px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background: rgba(0, 0, 0, 0.2);
                    min-height: 20px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(0, 0, 0, 0.3);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
            """
        
        # Apply style to table
        if hasattr(self, 'video_table'):
            self.video_table.setStyleSheet(table_style)
            
        # Apply style to scrollbar
        self.setStyleSheet(scrollbar_style)
        
        # Update colors for components
        if hasattr(self, 'url_input'):
            self.url_input.setStyleSheet(f"""
                QLineEdit {{ 
                    color: {url_text_color};
                }}
                QLineEdit::placeholder {{
                    color: {url_placeholder_color};
                }}
            """)
            
        if hasattr(self, 'output_folder_display'):
            self.output_folder_display.setStyleSheet(f"""
                QLineEdit {{ 
                    color: {folder_text_color};
                }}
                QLineEdit::placeholder {{
                    color: {url_placeholder_color};
                }}
            """) 

    def handle_video_info(self, url, video_info):
        """Handle video information received"""
        try:
            print(f"Received video info for URL: {url}, title: {video_info.title}")
            
            # Update UI to show that information is being processed
            if self.parent and self.processing_count > 1:
                self.parent.status_bar.showMessage(self.tr_("STATUS_GETTING_INFO_MULTIPLE").format(self.processing_count))
                QApplication.processEvents()
            
            # Process title - remove hashtags
            if video_info.title:
                # Remove hashtags from title
                import re
                # Remove extra spaces
                cleaned_title = re.sub(r'#\S+', '', video_info.title).strip()
                # Remove multiple spaces
                cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
                video_info.original_title = video_info.title  # Save original title
                video_info.title = cleaned_title  # Save new title
            
            # Save video information in dictionary
            row = self.video_table.rowCount()
            self.video_info_dict[row] = video_info
            
            # Add new row for this video
            self.video_table.insertRow(row)
            
            # Set row height for single-line display
            self.video_table.setRowHeight(row, 25)  # Set height for single-line display
            
            # Check for errors in title
            has_error = video_info.title.startswith("Error:")
            
            # Check if content is unsupported (DIALOG_UNSUPPORTED_CONTENT)
            unsupported_content = "DIALOG_UNSUPPORTED_CONTENT" in video_info.title
            
            try:
                # Select (Checkbox)
                checkbox = QCheckBox()
                checkbox.setChecked(not has_error)  # Uncheck if there's an error
                
                # Allow selection if content is unsupported
                if unsupported_content:
                    checkbox.setEnabled(True)
                else:
                    checkbox.setEnabled(not has_error)  # Disable if there's an error
                
                # Connect stateChanged signal to checkbox_state_changed method
                checkbox.stateChanged.connect(self.checkbox_state_changed)
                
                checkbox_cell = QWidget()
                layout = QHBoxLayout(checkbox_cell)
                layout.addWidget(checkbox)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)
                self.video_table.setCellWidget(row, 0, checkbox_cell)
                
                # Title
                if unsupported_content:
                    # Show error message from language file
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
                # Disable editing
                title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.video_table.setItem(row, 1, title_item)
                
                # Creator (Move to after Title)
                creator = video_info.creator if hasattr(video_info, 'creator') and video_info.creator else ""
                creator_item = QTableWidgetItem(creator)
                creator_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Format tooltip text for better readability
                creator_tooltip = self.format_tooltip_text(creator)
                creator_item.setToolTip(creator_tooltip)  # Add tooltip on hover
                # Disable editing
                creator_item.setFlags(creator_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.video_table.setItem(row, 2, creator_item)
                
                # Quality (Combobox)
                quality_combo = QComboBox()
                # Set fixed width for combobox
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
                
                # Format (Combobox)
                format_combo = QComboBox()
                # Set fixed width for combobox
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
                
                # Duration
                duration_str = self.format_duration(video_info.duration)
                duration_item = QTableWidgetItem(duration_str)
                duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.video_table.setItem(row, 5, duration_item)
                
                # Size (estimated based on format)
                size_str = self.estimate_size(video_info.formats)
                size_item = QTableWidgetItem(size_str)
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Disable editing
                size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.video_table.setItem(row, 6, size_item)
                
                # Hashtags
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
                # Format tooltip text for better readability
                hashtags_tooltip = self.format_tooltip_text(hashtags_str)
                hashtags_item.setToolTip(hashtags_tooltip)  # Add tooltip on hover
                hashtags_item.setToolTip(hashtags_tooltip)  # Add tooltip on hover
                # Disable editing
                hashtags_item.setFlags(hashtags_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.video_table.setItem(row, 7, hashtags_item)
                
                # Add tooltip for title
                title_item = self.video_table.item(row, 1)
                if title_item:
                    title_item.setToolTip(video_info.title)
            except Exception as cell_error:
                print(f"Error creating UI cells: {cell_error}")
                # Ensure row is created correctly
                while self.video_table.columnCount() > self.video_table.item(row, 0).column() + 1:
                    self.video_table.setItem(row, self.video_table.item(row, 0).column() + 1, QTableWidgetItem("Error"))
            
            # Update status
            if self.parent:
                if has_error:
                    if unsupported_content:
                        # Display friendly error message from language file
                        self.parent.status_bar.showMessage(self.tr_("DIALOG_UNSUPPORTED_CONTENT"))
                    else:
                        # Display other errors
                        self.parent.status_bar.showMessage(video_info.title)
                else:
                    # Display notification that video info has been received
                    if self.processing_count > 1:
                        self.parent.status_bar.showMessage(self.tr_("STATUS_GETTING_INFO_MULTIPLE").format(self.processing_count))
                    else:
                        self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEO_INFO"))
                    
            # Decrease counter and check if all processing is complete
            self.processing_count -= 1
            if self.processing_count <= 0:
                # Re-enable UI
                self.get_info_btn.setEnabled(True)
                self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
                self.url_input.setEnabled(True)
                
                # Update status message
                total_videos = self.video_table.rowCount()
                if self.parent:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_LOADED").format(total_videos))
                    
                # Update UI immediately
                QApplication.processEvents()
                
                # Update Select All/Unselect All button status based on checkboxes
                self.update_select_toggle_button()
            
            # Don't hard reset status, let the update_select_toggle_button function determine the correct value based on checkbox states
            # self.all_selected = False
            # self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
            
            # Update UI
            self.get_info_btn.setEnabled(True)
            self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
            self.url_input.setEnabled(True)
            self.url_input.clear()
            
            # Update button states
            self.update_button_states()
            
            # Display notification on status bar
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_INFO_RECEIVED"))
        except Exception as e:
            print(f"Critical error in on_video_info_received: {e}")
            # Ensure counter is decreased
            self.processing_count -= 1
            if self.processing_count <= 0:
                # Re-enable UI
                self.get_info_btn.setEnabled(True)
                self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
                self.url_input.setEnabled(True)
            
            # Display error in status bar
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ERROR").format(str(e)))
    
    def handle_progress(self, url, progress, speed):
        """Update download progress"""
        # Find row containing this URL
        for row, info in self.video_info_dict.items():
            if info.url == url:
                # Display download progress in status bar
                if self.parent:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOADING_PROGRESS").format(int(progress), speed))
                break
    
    def handle_download_finished(self, url, success, file_path):
        """Handle when a video download is complete"""
        self.downloading_count -= 1
        
        # Debug log
        print(f"DEBUG - on_download_finished called with URL: {url}, success: {success}, file_path: {file_path}")
        
        # Ensure file_path doesn't contain %(ext)s
        if '%(ext)s' in file_path:
            # Check actual file extension
            if file_path.lower().endswith('.mp3'):
                file_path = file_path.replace('.%(ext)s', '.mp3')
            else:
                file_path = file_path.replace('.%(ext)s', '.mp4')
            print(f"DEBUG - Fixed file_path: {file_path}")
            
        # Search for video in table and hide progress bar
        row_to_remove = None
        found_video_info = None
        
        # Find video in the table based on URL
        for row in range(self.video_table.rowCount()):
            # Get video_info from dictionary
            row_info = self.video_info_dict.get(row)
            if row_info and row_info.url == url:
                row_to_remove = row
                found_video_info = row_info
                print(f"DEBUG - Found matching video at row {row}: {row_info.title}")
                break
        
        print(f"DEBUG - Row to remove: {row_to_remove}, Found video info: {found_video_info}")
        
        # Increment the count of successfully downloaded videos
        if success:
            self.success_downloads += 1
            video_info = found_video_info or self.video_info_dict.get(row_to_remove, None)
            filename = os.path.basename(file_path)
            
            print(f"DEBUG - Success download! File: {filename}")
            
            # Display status message
            if self.parent and self.parent.status_bar:
                # If there are still videos being downloaded
                if self.downloading_count > 0:
                    # Truncate filename if too long
                    short_filename = self.truncate_filename(filename)
                    self.parent.status_bar.showMessage(self.tr_("STATUS_ONE_OF_MULTIPLE_DONE").format(
                        short_filename,
                        self.downloading_count
                    ))
                else:
                    # If all downloads finished, show success message
                    if self.success_downloads > 1:
                        self.parent.status_bar.showMessage(self.tr_("DIALOG_DOWNLOAD_MULTIPLE_SUCCESS").format(self.success_downloads))
                    else:
                        # Truncate filename if too long
                        short_filename = self.truncate_filename(filename)
                        self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOAD_SUCCESS_WITH_FILENAME").format(short_filename))
            
            # Update UI immediately to display the message
            QApplication.processEvents()
            
            # Update Downloaded Videos tab if it exists and add the new video
            if hasattr(self.parent, 'downloaded_videos_tab') and video_info:
                print(f"DEBUG - Adding video to Downloaded Videos tab: {video_info.title}")
                
                # Get selected quality information
                quality_cell = self.video_table.cellWidget(row_to_remove, 3) if row_to_remove is not None else None
                quality = quality_cell.findChild(QComboBox).currentText() if quality_cell else "1080p"
                
                # Get selected format information
                format_cell = self.video_table.cellWidget(row_to_remove, 4) if row_to_remove is not None else None
                format_str = format_cell.findChild(QComboBox).currentText() if format_cell else self.tr_("FORMAT_VIDEO_MP4")
                
                # Check file extension and update format and quality
                if file_path.lower().endswith('.mp3'):
                    format_str = self.tr_("FORMAT_AUDIO_MP3")
                    quality = "320kbps"  # Set default quality for audio
                elif file_path.lower().endswith('.mp4'):
                    # Check if format_str is already set to audio format
                    if format_str == self.tr_("FORMAT_AUDIO_MP3"):
                        format_str = self.tr_("FORMAT_VIDEO_MP4")
                
                # Check if this is a video without a title that has been renamed
                display_title = video_info.title
                if hasattr(video_info, 'custom_title') and video_info.custom_title:
                    display_title = video_info.custom_title
                
                # If the filename is different from the original video title, it might have been renamed
                filename_without_ext = os.path.splitext(os.path.basename(file_path))[0]
                if filename_without_ext and filename_without_ext != video_info.title:
                    display_title = filename_without_ext
                
                # Create download info to add to Downloaded Videos tab
                download_info = {
                    'url': url,
                    'title': display_title,  # Use the custom name if set
                    'creator': video_info.creator if hasattr(video_info, 'creator') else "",
                    'quality': quality,
                    'format': format_str,
                    'duration': self.format_duration(video_info.duration) if hasattr(video_info, 'duration') else "Unknown",
                    'filesize': self.estimate_size(video_info.formats) if hasattr(video_info, 'formats') else "Unknown",
                    'filepath': file_path,
                    'download_date': datetime.now().strftime("%Y/%m/%d %H:%M"),
                    'hashtags': [],
                    'description': video_info.caption if hasattr(video_info, 'caption') else "",
                    'status': "Successful"
                }
                
                # Extract hashtags from original video title and caption
                combined_hashtags = set()  # Use set to avoid duplicates

                # If original_title exists, extract hashtags from it
                if hasattr(video_info, 'original_title') and video_info.original_title:
                    import re
                    # Detect all strings that start with # and end with whitespace or end of string
                    found_hashtags = re.findall(r'#([^\s#\.]+)', video_info.original_title)
                    if found_hashtags:
                        combined_hashtags.update(found_hashtags)
                    
                    # Handle the case where the title is truncated (has "..." at the end)
                    if "..." in video_info.original_title:
                        # Get hashtags from the displayed title in the download tab
                        title_file = os.path.basename(file_path)
                        if "#" in title_file:
                            additional_hashtags = re.findall(r'#([^\s#\.]+)', title_file)
                            if additional_hashtags:
                                combined_hashtags.update(additional_hashtags)

                # Get hashtags from caption
                if hasattr(video_info, 'caption') and video_info.caption:
                    import re
                    found_hashtags = re.findall(r'#([^\s#\.]+)', video_info.caption)
                    if found_hashtags:
                        combined_hashtags.update(found_hashtags)
                
                # Combine with existing hashtags in video_info
                if hasattr(video_info, 'hashtags') and video_info.hashtags:
                    combined_hashtags.update([tag.strip() for tag in video_info.hashtags])
                
                # If no hashtags found, check if filename contains hashtags
                if not combined_hashtags and "#" in filename:
                    additional_hashtags = re.findall(r'#([^\s#\.]+)', filename)
                    if additional_hashtags:
                        combined_hashtags.update(additional_hashtags)
                
                # Assign hashtags to download_info
                if combined_hashtags:
                    download_info['hashtags'] = list(combined_hashtags)
                
                # Print hashtags for debugging
                print(f"DEBUG - Combined hashtags: {download_info['hashtags']}")
                
                # Download and save thumbnail if available
                thumbnail_path = ""
                if hasattr(video_info, 'thumbnail') and video_info.thumbnail:
                    try:
                        # Create thumbnails directory if it doesn't exist
                        thumbnails_dir = os.path.join(os.path.dirname(file_path), "thumbnails")
                        if not os.path.exists(thumbnails_dir):
                            os.makedirs(thumbnails_dir)
                        
                        # Create thumbnail filename from TikTok video ID
                        video_id = url.split('/')[-1].split('?')[0]  # Get video ID from URL
                        thumbnail_path = os.path.join(thumbnails_dir, f"{video_id}.jpg")
                        
                        # Download thumbnail
                        response = requests.get(video_info.thumbnail, stream=True)
                        response.raise_for_status()
                        
                        with open(thumbnail_path, 'wb') as out_file:
                            shutil.copyfileobj(response.raw, out_file)
                    except Exception as e:
                        print(f"Error downloading thumbnail: {e}")
                
                # Save thumbnail path to video info
                download_info['thumbnail'] = thumbnail_path
                
                # Log information
                print(f"DEBUG - Title: {download_info['title']}")
                print(f"DEBUG - Quality: {download_info['quality']}, Format: {download_info['format']}")
                print(f"DEBUG - Hashtags: {download_info['hashtags']}")
                print(f"DEBUG - Thumbnail: {download_info['thumbnail']}")
                print(f"DEBUG - Status: {download_info['status']}")
                
                # Add to Downloaded Videos tab
                self.parent.downloaded_videos_tab.add_downloaded_video(download_info)
                print(f"DEBUG - Video added to Downloaded Videos tab")
                
                # Force update Downloaded Videos tab UI
                self.parent.downloaded_videos_tab.display_videos()
                print(f"DEBUG - Downloaded Videos tab display updated")
            
            # Remove row after successful download
            if row_to_remove is not None:
                print(f"DEBUG - Removing row {row_to_remove} from video table")
                self.video_table.removeRow(row_to_remove)
                if row_to_remove in self.video_info_dict:
                    del self.video_info_dict[row_to_remove]
                    print(f"DEBUG - Removed row {row_to_remove} from video_info_dict")
            else:
                print(f"DEBUG - Could not find row to remove for URL: {url}")
            
            # Update indexes of items in video_info_dict
            new_dict = {}
            print(f"DEBUG - Reindexing video_info_dict after deletion, current keys: {sorted(self.video_info_dict.keys())}")
            
            # Simplify: Just create a new dictionary with consecutive indexes
            values = list(self.video_info_dict.values())
            for new_idx in range(len(values)):
                new_dict[new_idx] = values[new_idx]
            
            self.video_info_dict = new_dict
            print(f"DEBUG - Updated video_info_dict after deletion, new size: {len(self.video_info_dict)}, new keys: {sorted(self.video_info_dict.keys())}")
            
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOAD_SUCCESS")) 
        else:
            # If download failed, display appropriate error message
            if self.parent and self.parent.status_bar:
                self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOAD_FAILED"))
                print(f"DEBUG - Download failed for URL: {url}")
        
        # If all videos have been downloaded, re-enable Download button
        if self.downloading_count <= 0:
            self.download_btn.setEnabled(True)
            self.download_btn.setText(self.tr_("BUTTON_DOWNLOAD"))
            print(f"DEBUG - All downloads finished, reset download button")
            # Reset status bar when all downloads are complete
            if self.parent and self.parent.status_bar:
                self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOAD_SUCCESS"))

    def truncate_filename(self, filename, max_length=30):
        """Truncate filename for display in status bar"""
        if len(filename) <= max_length:
            return filename
            
        # Get name and extension
        name, ext = os.path.splitext(filename)
        
        # Calculate number of characters to keep
        # Keep first 10 characters, ..., and last 10 characters + extension
        keep_length = max_length - 3  # subtract 3 dots
        first_part = (keep_length // 2) - len(ext)
        last_part = keep_length - first_part - len(ext)
        
        return f"{name[:first_part]}...{name[-last_part:]}{ext}"

    def open_folder(self, folder_path):
        """Open folder containing the file"""
        try:
            if os.path.exists(folder_path):
                if os.name == 'nt':  # Windows
                    # Use subprocess.Popen instead of os.startfile to avoid showing CMD window
                    import subprocess
                    # Ensure proper Windows path format
                    folder_path = folder_path.replace('/', '\\')
                    # Create a new process with CREATE_NO_WINDOW flag to prevent CMD window from showing
                    subprocess.Popen(['explorer', folder_path], shell=False,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
                elif os.name == 'posix':  # macOS, Linux
                    import subprocess
                    subprocess.Popen(['xdg-open', folder_path])
            else:
                QMessageBox.warning(
                    self, 
                    self.tr_("DIALOG_ERROR"), 
                    self.tr_("DIALOG_FOLDER_NOT_FOUND").format(folder_path)
                )
        except Exception as e:
            QMessageBox.warning(
                self, 
                self.tr_("DIALOG_ERROR"),
                self.tr_("DIALOG_CANNOT_OPEN_FOLDER").format(str(e))
            )
    
    def format_duration(self, seconds):
        """Format duration from seconds to MM:SS"""
        if not seconds:
            return "00:00"
        
        minutes = int(seconds / 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes:02d}:{remaining_seconds:02d}"
    
    def estimate_size(self, formats):
        """Estimate file size based on formats"""
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

    def on_format_changed(self, index, format_combo, quality_combo, audio_quality, video_qualities):
        """Handle when user changes format"""
        is_audio = format_combo.currentText() == self.tr_("FORMAT_AUDIO_MP3")
        
        # Clear all current items
        quality_combo.clear()
        
        if is_audio:
            # If audio, only display audio quality
            if audio_quality:
                quality_combo.addItem(audio_quality)
            else:
                quality_combo.addItem("Original")
        else:
            # If video, display list of video qualities
            quality_combo.addItems(video_qualities) 

    def delete_selected_videos(self):
        """Delete selected videos from the table"""
        # Count selected videos
        selected_count = 0
        for row in range(self.video_table.rowCount()):
            checkbox_cell = self.video_table.cellWidget(row, 0)
            if checkbox_cell:
                checkbox = checkbox_cell.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected_count += 1
        
        # If no videos are selected
        if selected_count == 0:
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("DIALOG_NO_VIDEOS_SELECTED"))
            return
            
        # Display confirmation dialog
        reply = QMessageBox.question(
            self, self.tr_("DIALOG_CONFIRM_DELETION"), 
            self.tr_("DIALOG_CONFIRM_DELETE_SELECTED").format(selected_count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Delete from bottom to top to avoid index errors
            for row in range(self.video_table.rowCount() - 1, -1, -1):
                checkbox_cell = self.video_table.cellWidget(row, 0)
                if checkbox_cell:
                    checkbox = checkbox_cell.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        self.video_table.removeRow(row)
                        # Update index of items in video_info_dict
                        if row in self.video_info_dict:
                            del self.video_info_dict[row]
            
            # Update indices of items in video_info_dict
            new_dict = {}
            # Simplification: Just create a new dictionary with sequential indices
            values = list(self.video_info_dict.values())
            for new_idx in range(len(values)):
                new_dict[new_idx] = values[new_idx]
            
            self.video_info_dict = new_dict
            
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_SELECTED_DELETED").format(selected_count))
            
            # After completing deletion of selected videos
            self.video_table.blockSignals(False)

    def get_selected_quality(self, row):
        """Get selected quality from row in table"""
        if row is None or row < 0 or row >= self.video_table.rowCount():
            return "1080p"  # Default value when no row is available
        
        try:
            quality_cell = self.video_table.cellWidget(row, 2)  # Quality column (index 2)
            if quality_cell:
                quality_combo = quality_cell.findChild(QComboBox)
                if quality_combo:
                    return quality_combo.currentText()
            
            # Fallback to cell item if combobox not found
            quality_item = self.video_table.item(row, 2)
            if quality_item:
                return quality_item.text()
        except Exception as e:
            print(f"Error getting quality: {e}")
            
        return "1080p"  # Default value
        
    def get_selected_format(self, row):
        """Get selected format from row in table"""
        if row is None or row < 0 or row >= self.video_table.rowCount():
            return "Video (mp4)"  # Default value when no row is available
        
        try:
            format_cell = self.video_table.cellWidget(row, 3)  # Format column (index 3)
            if format_cell:
                format_combo = format_cell.findChild(QComboBox)
                if format_combo:
                    return format_combo.currentText()
            
            # Fallback to cell item if combobox not found
            format_item = self.video_table.item(row, 3)
            if format_item:
                return format_item.text()
        except Exception as e:
            print(f"Error getting format: {e}")
            
        return "Video (mp4)"  # Default value 

    def show_copy_dialog(self, item):
        """Display dialog to copy text when double-clicking a cell in the table"""
        column = item.column()
        row = item.row()
        
        # Actual map of columns in the table:
        # Column 1: Title
        # Column 2: Creator
        # Column 7: Hashtags
        
        # Only display copy dialog for important columns
        if column not in [1, 2, 7]:
            return
        
        # Debug to understand the structure of video_info_dict
        print(f"DEBUG - video_info_dict type: {type(self.video_info_dict)}")
        print(f"DEBUG - Double-clicked on row {row}, column {column}")
        if row in self.video_info_dict:
            print(f"DEBUG - video_info at row {row} type: {type(self.video_info_dict[row])}")
            print(f"DEBUG - video_info attributes: {dir(self.video_info_dict[row])}")
        
        # Get full video information
        full_text = ""
        if row in self.video_info_dict:
            video_info = self.video_info_dict[row]
            if column == 1:  # Title
                # Print debug information to see content
                if hasattr(video_info, 'title'):
                    print(f"DEBUG - Title: '{video_info.title}'")
                if hasattr(video_info, 'caption'):
                    print(f"DEBUG - Caption: '{video_info.caption}'")
                if hasattr(video_info, 'original_title'):
                    print(f"DEBUG - Original title: '{video_info.original_title}'")
                
                # Prioritize caption as the main data source as it usually contains the most complete content
                if hasattr(video_info, 'caption') and video_info.caption:
                    full_text = video_info.caption
                elif hasattr(video_info, 'original_title') and video_info.original_title:
                    # Use original title if no caption
                    full_text = video_info.original_title
                else:
                    # Use current title if no other information is available
                    full_text = video_info.title if hasattr(video_info, 'title') else item.text()
                
                # Remove hashtags from title when displaying
                if full_text:
                    # Remove hashtags in #xxx format
                    import re
                    full_text = re.sub(r'#\w+', '', full_text)
                    # Remove hashtags in #xxx format with leading whitespace
                    full_text = re.sub(r'\s+#\w+', '', full_text)
                    # Remove extra whitespace and trailing spaces
                    full_text = re.sub(r'\s+', ' ', full_text).strip()
                
                print(f"DEBUG - Selected full_text for dialog (after removing hashtags): '{full_text}'")
            elif column == 2:  # Creator
                full_text = video_info.creator if hasattr(video_info, 'creator') else item.text()
            elif column == 7:  # Hashtags
                if hasattr(video_info, 'hashtags') and video_info.hashtags:
                    full_text = ' '.join(f"#{tag}" for tag in video_info.hashtags)
                else:
                    # Try to get from caption if no separate hashtags exist
                    if hasattr(video_info, 'caption') and video_info.caption:
                        import re
                        hashtags = re.findall(r'#(\w+)', video_info.caption)
                        if hashtags:
                            full_text = ' '.join(f"#{tag}" for tag in hashtags)
                        else:
                            full_text = item.text()
                    else:
                        full_text = item.text()
        else:
            full_text = item.text()  # Fallback to cell text
            
        if not full_text:
            return
            
        # Determine dialog title based on column
        if column == 1:
            title = self.tr_("HEADER_VIDEO_TITLE")
        elif column == 2:
            title = self.tr_("HEADER_CREATOR")
        else:  # column == 7
            title = self.tr_("HEADER_HASHTAGS")
            
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(600)  # Increase minimum width
        dialog.setMinimumHeight(400)  # Add minimum height
        dialog.resize(600, 400)
        
        # Determine current theme from parent window
        current_theme = "dark"
        if hasattr(self, 'parent') and hasattr(self.parent, 'current_theme'):
            current_theme = self.parent.current_theme
        
        # Apply style based on current theme
        if current_theme == "light":
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #f0f0f0;
                    color: #333333;
                }
                QTextEdit {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #cccccc;
                    padding: 5px;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #0078d7;
                    color: #ffffff;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #0086f0;
                }
            """)
        else:
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QTextEdit {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 5px;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #0078d7;
                    color: #ffffff;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #0086f0;
                }
            """)
        
        # Layout dialog
        layout = QVBoxLayout(dialog)
        
        # Text edit for display and copy
        text_edit = QTextEdit(dialog)
        text_edit.setPlainText(full_text)
        text_edit.setReadOnly(True)  # Only allow reading and copying
        text_edit.setMinimumHeight(300)  # Set minimum height for text edit
        text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)  # Auto wrap text
        
        layout.addWidget(text_edit)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Copy button
        copy_btn = QPushButton(self.tr_("BUTTON_COPY"))
        copy_btn.clicked.connect(lambda: self.copy_to_clipboard(full_text))
        button_layout.addWidget(copy_btn)
        
        # Close button
        close_btn = QPushButton(self.tr_("BUTTON_CANCEL"))
        close_btn.clicked.connect(dialog.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Show dialog and handle actions
        dialog.exec()
        
        # Clear selection and focus
        self.video_table.clearSelection()
        self.video_table.clearFocus()
        # Set focus back to search input
        self.url_input.setFocus()
        
    def copy_to_clipboard(self, text, column_name=None):
        """Copy text to clipboard with special handling for certain columns"""
        if not text:
            return
        
        # Special handling for title column - remove hashtags
        if column_name == "title":
            # Remove hashtags from title
            text = re.sub(r'#\w+', '', text).strip()
            # Remove double spaces
            text = re.sub(r'\s+', ' ', text)
        
        # Set text to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        # Display notification
        show_message = True
        if hasattr(self, 'parent') and hasattr(self.parent, 'settings'):
            show_message = self.parent.settings.value("show_copy_message", "true") == "true"
        
        if show_message:
            copied_text = text[:50] + "..." if len(text) > 50 else text
            self.parent.status_bar.showMessage(self.tr_("STATUS_TEXT_COPIED").format(copied_text), 3000)

    # New method to select or deselect all videos in the table
    def toggle_select_all(self):
        """Select or deselect all videos in the table"""
        self.all_selected = not self.all_selected
        
        # Update button label based on new state
        if self.all_selected:
            self.select_toggle_btn.setText(self.tr_("BUTTON_UNSELECT_ALL"))
        else:
            self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
            
        # Temporarily disconnect signals to avoid calling checkbox_state_changed multiple times
        checkboxes = []
        
        # Collect all checkboxes and disconnect signals
        for row in range(self.video_table.rowCount()):
            checkbox_cell = self.video_table.cellWidget(row, 0)
            if checkbox_cell:
                checkbox = checkbox_cell.findChild(QCheckBox)
                if checkbox:
                    # Temporarily disconnect signal
                    checkbox.stateChanged.disconnect(self.checkbox_state_changed)
                    checkboxes.append(checkbox)
        
        # Update checkbox states
        for checkbox in checkboxes:
            checkbox.setChecked(self.all_selected)
        
        # Reconnect signals after updates
        for checkbox in checkboxes:
            checkbox.stateChanged.connect(self.checkbox_state_changed)
        
        # Display notification on status bar
        if self.parent and self.parent.status_bar:
            if self.all_selected:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ALL_VIDEOS_SELECTED"))
            else:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ALL_VIDEOS_UNSELECTED")) 

    # Add method to update Toggle Select All button state based on checkboxes
    def update_select_toggle_button(self):
        """Update Toggle Select All button state based on checkboxes in the table"""
        # Check if there are any videos in the table
        if self.video_table.rowCount() == 0:
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
        if all_checked:
            self.all_selected = True
            self.select_toggle_btn.setText(self.tr_("BUTTON_UNSELECT_ALL"))
        else:
            self.all_selected = False
            self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
            
    # Method to handle checkbox state change event
    def checkbox_state_changed(self):
        """Handle checkbox state change"""
        self.update_select_toggle_button()

    def show_full_text_tooltip(self, row, column):
        """Display tooltip with full content when hovering over a cell"""
        try:
            item = self.video_table.item(row, column)
            if item:
                text = item.text()
                
                # Special handling for title column (column 1)
                if column == 1 and row in self.video_info_dict:
                    video_info = self.video_info_dict[row]
                    
                    # Prioritize caption if available (contains most complete information)
                    if hasattr(video_info, 'caption') and video_info.caption:
                        text = video_info.caption
                    # If no caption, try to use original_title
                    elif hasattr(video_info, 'original_title') and video_info.original_title:
                        text = video_info.original_title
                    # If not, use title
                    elif hasattr(video_info, 'title'):
                        text = video_info.title
                        
                # For other fields, get text directly from item
                if text:
                    # Format tooltip text for better readability with line breaks
                    formatted_text = self.format_tooltip_text(text)
                    QToolTip.showText(QCursor.pos(), formatted_text)
        except Exception as e:
            print(f"DEBUG - Error in show_full_text_tooltip: {e}")
            # Ignore exceptions
            pass

    def update_button_states(self):
        """Update button states based on number of videos in the table"""
        has_videos = self.video_table.rowCount() > 0
        
        # Disable buttons when there are no videos
        self.select_toggle_btn.setEnabled(has_videos)
        self.delete_selected_btn.setEnabled(has_videos)
        self.delete_all_btn.setEnabled(has_videos)
        self.download_btn.setEnabled(has_videos)
        
        # Don't apply style because it's already handled from main_window.py
        print("DEBUG: update_button_states in video_info_tab - button states updated without applying style")

    def set_output_folder(self):
        """Set output folder"""
        # Use current folder as starting point if available
        start_folder = self.output_folder_display.text() if self.output_folder_display.text() else ""
        
        folder = QFileDialog.getExistingDirectory(
            self, self.tr_("MENU_CHOOSE_FOLDER"), start_folder)
        if folder:
            self.update_output_folder(folder)
            # Save to config file through parent
            if hasattr(self, 'parent') and hasattr(self.parent, 'save_config'):
                self.parent.save_config('last_output_folder', folder)
                
                # Log to debug file
                try:
                    log_file = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else 
                                          os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'log.txt')
                    with open(log_file, 'a', encoding='utf-8') as log:
                        log.write(f"[{datetime.now()}] Video_info_tab set_output_folder called: Saving '{folder}' to config\n")
                except:
                    pass

    def handle_api_error(self, url, error_message):
        """Handle API errors from the downloader"""
        # Log the error
        print(f"API Error for {url}: {error_message}")
        
        # Show API error message to the user
        QMessageBox.warning(
            self,
            self.tr_("DIALOG_API_ERROR_TITLE"),
            f"{self.tr_('DIALOG_TIKTOK_API_CHANGED')}\n\n"
            f"{self.tr_('DIALOG_UPDATE_NEEDED_MESSAGE')}"
        )
        
        # Update status bar
        if self.parent:
            self.parent.status_bar.showMessage(self.tr_("DIALOG_YTDLP_OUTDATED"), 10000)