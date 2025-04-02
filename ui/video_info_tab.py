from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableWidget, QComboBox,
                             QFileDialog, QCheckBox, QHeaderView, QMessageBox,
                             QTableWidgetItem, QProgressBar, QApplication, QDialog, QTextEdit, QMenu, QInputDialog, QSpacerItem, QSizePolicy, QDialogButtonBox, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
import os
import json
from localization import get_language_manager
from utils.downloader import Downloader
from utils.video_info import VideoInfo
from utils.platform_factory import PlatformFactory
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
import logging
import traceback

# Path to configuration file
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')

class VideoInfoTab(QWidget):
    """Tab displaying video information and downloading videos"""

    def __init__(self, parent=None):
        """Initialize the tab"""
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
        self.success_downloads = 0
        self.downloading_videos = {}
        
        # Variable to track if all items are selected
        self.all_selected = False
        
        # Current platform (default to empty, will be set by caller)
        self.current_platform = ""
        
        # Set up UI
        self.setup_ui()
        
        # Update language for all components
        self.update_language()
        
        # Load last output folder
        self.load_last_output_folder()
        
        # Initialize downloader
        self.downloader = Downloader()
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
        
    def set_current_platform(self, platform_name):
        """Set current platform and update UI accordingly"""
        if platform_name not in ["TikTok", "YouTube"]:
            return
            
        # Call set_platform which has the complete implementation
        self.set_platform(platform_name)
        
    def configure_headers_by_platform(self, platform_name):
        """Configure table headers based on the platform"""
        # Set platform name first
        self.current_platform = platform_name

        # Reset column widths
        if self.video_table.columnCount() > 0:
            for i in range(self.video_table.columnCount()):
                self.video_table.setColumnWidth(i, 100)  # Default width
        
        # Update headers based on platform
        if platform_name == "YouTube":
            self.update_table_headers_youtube()
            # Enable subtitle options for YouTube
            if hasattr(self, 'subtitle_frame'):
                self.subtitle_frame.setVisible(True)
                print("YouTube selected - Showing subtitle options")
        elif platform_name == "TikTok":
            self.update_table_headers_tiktok()
            # Disable subtitle options for TikTok
            if hasattr(self, 'subtitle_frame'):
                self.subtitle_frame.setVisible(False)
                self.subtitle_checkbox.setChecked(False)
                print("TikTok selected - Hiding subtitle options")
        else:
            # Default headers
            self.update_table_headers()
            # Disable subtitle options for other platforms
            if hasattr(self, 'subtitle_frame'):
                self.subtitle_frame.setVisible(False)
                self.subtitle_checkbox.setChecked(False)
                print("Other platform selected - Hiding subtitle options")
        
        # Update column widths after setting headers
        self.update_column_widths()

    def update_table_headers(self):
        """Update table headers based on current platform"""
        if self.current_platform == "YouTube":
            self.update_table_headers_youtube()
        else:
            self.update_table_headers_tiktok()

    def update_table_headers_tiktok(self):
        """Update table headers for TikTok"""
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
        
    def update_table_headers_youtube(self):
        """Update table headers for YouTube"""
        headers = [
            self.tr_("HEADER_SELECT"),
            self.tr_("HEADER_VIDEO_TITLE"),
            self.tr_("HEADER_CHANNEL"),  # Channel instead of Creator
            self.tr_("HEADER_PLAYLIST"),  # New column for Playlist
            self.tr_("HEADER_QUALITY"),
            self.tr_("HEADER_FORMAT"),
            self.tr_("HEADER_DURATION"),
            self.tr_("HEADER_SIZE"),
            self.tr_("HEADER_RELEASE_DATE")  # Release Date instead of Hashtags
        ]
        self.video_table.setHorizontalHeaderLabels(headers)
        
    def update_column_widths(self):
        """Update column widths based on current platform"""
        # Common columns
        self.video_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Select
        self.video_table.setColumnWidth(0, 50)
        
        self.video_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title
        
        # Platform-specific
        if self.current_platform == "YouTube":
            # YouTube column widths
            self.video_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Channel
            self.video_table.setColumnWidth(2, 120)
            
            self.video_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Playlist
            self.video_table.setColumnWidth(3, 150)
            
            self.video_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Quality
            self.video_table.setColumnWidth(4, 85)
            
            self.video_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Format
            self.video_table.setColumnWidth(5, 85)
            
            self.video_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Duration
            self.video_table.setColumnWidth(6, 90)
            
            self.video_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)  # Size
            self.video_table.setColumnWidth(7, 75)
            
            self.video_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)  # Release Date
            self.video_table.setColumnWidth(8, 120)
        else:
            # TikTok column widths
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

    def create_video_table(self):
        """Create table to display video information"""
        self.video_table = QTableWidget()
        
        # Initially set up for TikTok (default)
        self.video_table.setColumnCount(8)
        
        # Set up headers
        self.update_table_headers()
        
        # Bỏ in đậm cho header để tiết kiệm không gian
        header_font = self.video_table.horizontalHeader().font()
        header_font.setBold(False)
        self.video_table.horizontalHeader().setFont(header_font)
        
        # Set table properties
        self.video_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Update column widths
        self.update_column_widths()
        
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
        # Get URL from input field
        url = self.url_input.text().strip()
        
        # Check if URL is empty
        if not url:
            QMessageBox.warning(
                self,
                self.tr_("DIALOG_WARNING"),
                self.tr_("DIALOG_EMPTY_URL")
            )
            return
            
        # Detect platform from URL and set current platform
        if "youtube.com" in url or "youtu.be" in url:
            self.set_current_platform("YouTube")
        elif "tiktok.com" in url:
            self.set_current_platform("TikTok")
        else:
            # Show warning for unsupported URL
            QMessageBox.warning(
                self,
                self.tr_("DIALOG_WARNING"),
                self.tr_("DIALOG_INVALID_URL")
            )
            return
        
        # Check if video already exists in the table
        for row, info in self.video_info_dict.items():
            if hasattr(info, 'url') and info.url == url:
                # Show confirmation dialog
                reply = QMessageBox.question(
                    self,
                    self.tr_("DIALOG_ALREADY_EXISTS"),
                    self.tr_("DIALOG_ALREADY_EXISTS_TEXT"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.No:
                    return
                else:
                    # Remove existing entry
                    self.video_table.removeRow(row)
                    self.video_info_dict.pop(row)
                    break
        
        # Update UI to show that information is being processed
        self.processing_count += 1
        self.get_info_btn.setEnabled(False)
        self.get_info_btn.setText(self.tr_("STATUS_GETTING_INFO"))
        self.url_input.setEnabled(False)
        
        if self.parent:
            self.parent.status_bar.showMessage(self.tr_("STATUS_GETTING_INFO"))
        
        # Add loading row to table
        row = self.video_table.rowCount()
        self.video_table.insertRow(row)
        
        # Set row height
        self.video_table.setRowHeight(row, 25)
        
        # Create checkbox for selection
        self.create_checkbox_for_row(row)
        
        # Create loading placeholder
        self.video_table.setItem(row, 1, QTableWidgetItem(self.tr_("STATUS_LOADING")))
        
        # Create placeholder for creator/channel
        creator_label = self.tr_("HEADER_CHANNEL") if self.current_platform == "YouTube" else self.tr_("HEADER_CREATOR")
        self.video_table.setItem(row, 2, QTableWidgetItem(f"{creator_label}..."))
        
        # Process immediately
        QApplication.processEvents()
        
        # Call downloader to get video info
        try:
            # Create VideoInfo object with URL
            from utils.models import VideoInfo
            video_info = VideoInfo()
            video_info.url = url
            
            # Store in dictionary
            self.video_info_dict[row] = video_info
            
            # Call downloader
            self.downloader.get_video_info(url)
        except Exception as e:
            # Update UI to show error
            error_message = f"Error: {str(e)}"
            self.update_video_info_error(row, error_message)
            
            # Decrease counter
            self.processing_count -= 1
            
            # Re-enable UI
            self.get_info_btn.setEnabled(True)
            self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
            self.url_input.setEnabled(True)
            
            # Update button states
            self.update_button_states()
    
    def create_checkbox_for_row(self, row):
        """Create checkbox for a new row"""
        checkbox = QCheckBox()
        checkbox.setChecked(True)  # Default to checked
        checkbox.stateChanged.connect(self.checkbox_state_changed)
        
        checkbox_cell = QWidget()
        layout = QHBoxLayout(checkbox_cell)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_table.setCellWidget(row, 0, checkbox_cell)
    
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
        # Check if any videos are selected
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            QMessageBox.warning(
                self,
                self.tr_("DIALOG_WARNING"),
                self.tr_("DIALOG_NO_VIDEOS_SELECTED")
            )
            return
            
        # Check if output folder is selected
        output_folder = self.output_folder_display.text()
        if not output_folder:
            QMessageBox.warning(
                self,
                self.tr_("DIALOG_WARNING"),
                self.tr_("DIALOG_SELECT_OUTPUT_FOLDER")
            )
            return
            
        # Confirm download
        reply = QMessageBox.question(
            self,
            self.tr_("DIALOG_CONFIRM_DOWNLOAD"),
            self.tr_("DIALOG_CONFIRM_DOWNLOAD_TEXT").format(len(selected_rows)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # Get subtitle options
        download_subtitles = False
        subtitle_language = "en"
        
        if self.current_platform == "YouTube" and self.subtitle_checkbox.isChecked():
            download_subtitles = True
            subtitle_language = self.subtitle_language_combo.currentData()
            
        # Start download for each selected video
        for row in selected_rows:
            if row in self.video_info_dict:
                video_info = self.video_info_dict[row]
                
                # Get quality
                quality_col = 4 if self.current_platform == "YouTube" else 3
                quality_cell = self.video_table.cellWidget(row, quality_col)
                quality = "720p"  # Default quality
                if quality_cell:
                    quality_combo = quality_cell.findChild(QComboBox)
                    if quality_combo:
                        quality = quality_combo.currentText()
                        
                # Get format
                format_col = 5 if self.current_platform == "YouTube" else 4
                format_cell = self.video_table.cellWidget(row, format_col)
                format_type = "mp4"  # Default format
                if format_cell:
                    format_combo = format_cell.findChild(QComboBox)
                    if format_combo:
                        format_text = format_combo.currentText()
                        if self.tr_("FORMAT_AUDIO_MP3") in format_text:
                            format_type = "mp3"
                
                # Get custom title if available
                custom_title = None
                if hasattr(video_info, 'custom_title'):
                    custom_title = video_info.custom_title
                
                # Start download
                self.downloading_count += 1
                self.downloader.download_video(
                    video_info.url,
                    output_folder,
                    quality,
                    format_type,
                    custom_title,
                    download_subtitles,
                    subtitle_language
                )
                
        # Update UI
        if self.parent and self.parent.status_bar:
            if download_subtitles:
                self.parent.status_bar.showMessage(
                    self.tr_("STATUS_DOWNLOAD_WITH_SUBS_STARTED").format(
                        len(selected_rows), 
                        self.subtitle_language_combo.currentText()
                    )
                )
            else:
                self.parent.status_bar.showMessage(
                    self.tr_("STATUS_DOWNLOAD_STARTED").format(len(selected_rows))
                )
            
        # Update button states
        self.update_button_states()

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

    def handle_video_info(self, video_info):
        """Handle video information received from the worker thread"""
        try:
            # Get row index
            row = self.get_row_for_url(video_info.url)
            
            if row < 0:
                # If row not found, no further processing needed
                return
                
            # Log received info
            logging.debug(f"Received video info for {video_info.url}")
            if hasattr(video_info, 'title'):
                logging.debug(f"Title: {video_info.title}")
            if hasattr(video_info, 'username'):
                logging.debug(f"Username: {video_info.username}")
            
            # Store video info in dictionary
            self.video_info_dict[row] = video_info
            
            # Update video details (title and channel/creator)
            self.update_video_title(row, video_info)
            self.update_video_creator(row, video_info)
            
            # Update platform-specific columns
            if self.current_platform == "YouTube":
                self.update_youtube_specific_columns(row, video_info)
            else:
                self.update_tiktok_specific_columns(row, video_info)
            
            # Update common columns
            self.setup_video_qualities(row, video_info)
            self.setup_video_formats(row, video_info)
            self.update_video_duration(row, video_info)
            self.update_video_size(row, video_info)
            
            # Update processing count
            self.processing_count -= 1
            
            # Enable download button if all videos are processed
            if self.processing_count == 0:
                self.update_button_states()
                # Show status message if none are currently downloading
                if self.downloading_count == 0 and self.parent and self.parent.status_bar:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_READY_TO_DOWNLOAD"))
            
            # Download thumbnail in the background
            if hasattr(video_info, 'thumbnail_url') and video_info.thumbnail_url:
                self.load_thumbnail(video_info.thumbnail_url, row)
                
        except Exception as e:
            # Log error
            logging.error(f"Error handling video info: {str(e)}")
            traceback.print_exc()
            
            # Update UI to show error
            self.update_video_info_error(row, f"Error: {str(e)}")
    
    def update_youtube_specific_columns(self, row, video_info):
        """Update YouTube-specific columns in the video table"""
        # Playlist column
        playlist_name = ""
        if hasattr(video_info, 'playlist') and video_info.playlist:
            playlist_name = video_info.playlist
            
        playlist_item = QTableWidgetItem(playlist_name)
        playlist_item.setToolTip(playlist_name)
        self.video_table.setItem(row, 3, playlist_item)
        
        # Release Date column (instead of Hashtags)
        release_date = ""
        if hasattr(video_info, 'release_date') and video_info.release_date:
            release_date = video_info.release_date
            
        date_item = QTableWidgetItem(release_date)
        date_item.setToolTip(release_date)
        self.video_table.setItem(row, 8, date_item)
    
    def update_tiktok_specific_columns(self, row, video_info):
        """Update TikTok-specific columns in the video table"""
        # Hashtags column
        hashtags = ""
        if hasattr(video_info, 'hashtags') and video_info.hashtags:
            if isinstance(video_info.hashtags, list):
                hashtags = " ".join(video_info.hashtags)
            else:
                hashtags = str(video_info.hashtags)
                
        hashtag_item = QTableWidgetItem(hashtags)
        hashtag_item.setToolTip(self.format_tooltip_text(hashtags))
        self.video_table.setItem(row, 7, hashtag_item)
    
    def update_video_title(self, row, video_info):
        """Update video title in the video table"""
        title = ""
        if hasattr(video_info, 'title'):
            title = video_info.title
            
        title_item = QTableWidgetItem(title)
        title_item.setToolTip(self.format_tooltip_text(title))
        self.video_table.setItem(row, 1, title_item)
    
    def update_video_creator(self, row, video_info):
        """Update video creator/channel in the video table"""
        creator = ""
        
        # Get creator name based on platform
        if self.current_platform == "YouTube":
            if hasattr(video_info, 'channel'):
                creator = video_info.channel
        else:
            if hasattr(video_info, 'username'):
                creator = video_info.username
                
        creator_item = QTableWidgetItem(creator)
        creator_item.setToolTip(creator)
        self.video_table.setItem(row, 2, creator_item)

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
        
    def copy_to_clipboard(self, text, text_type="text"):
        """Copy text to clipboard and show notification"""
        if not text:
            return
            
        # Get clipboard
        clipboard = QApplication.clipboard()
        
        # Set text to clipboard
        clipboard.setText(text)
        
        # Show notification
        if self.parent and self.parent.status_bar:
            # Different messages based on text type
            if text_type == "title":
                self.parent.status_bar.showMessage(self.tr_("STATUS_TITLE_COPIED"))
            elif text_type == "creator":
                if self.current_platform == "YouTube":
                    self.parent.status_bar.showMessage(self.tr_("STATUS_CHANNEL_COPIED"))
                else:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_CREATOR_COPIED"))
            elif text_type == "hashtags":
                self.parent.status_bar.showMessage(self.tr_("STATUS_HASHTAGS_COPIED"))
            elif text_type == "playlist":
                self.parent.status_bar.showMessage(self.tr_("STATUS_PLAYLIST_COPIED"))
            elif text_type == "release_date":
                self.parent.status_bar.showMessage(self.tr_("STATUS_RELEASE_DATE_COPIED"))
            else:
                self.parent.status_bar.showMessage(self.tr_("STATUS_TEXT_COPIED"))

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

    def setup_video_qualities(self, row, video_info):
        """Set up quality dropdown for video"""
        # Create combobox for quality selection
        quality_combo = QComboBox()
        quality_combo.setFixedWidth(80)
        
        # Get list of qualities
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
        
        # If no qualities found, use defaults
        if not qualities:
            qualities = ['1080p', '720p', '480p', '360p']
            
        # Add items to combobox
        quality_combo.addItems(qualities)
        
        # Check for errors
        has_error = False
        if hasattr(video_info, 'title'):
            has_error = video_info.title.startswith("Error:")
        
        quality_combo.setEnabled(not has_error)
        
        # Set up cell widget
        quality_cell = QWidget()
        quality_layout = QHBoxLayout(quality_cell)
        quality_layout.addWidget(quality_combo)
        quality_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        quality_layout.setContentsMargins(0, 0, 0, 0)
        
        # Determine column index based on platform
        quality_col = 4 if self.current_platform == "YouTube" else 3
        self.video_table.setCellWidget(row, quality_col, quality_cell)
        
        return quality_combo, audio_quality, qualities
    
    def setup_video_formats(self, row, video_info):
        """Set up format dropdown for video"""
        # Create combobox for format selection
        format_combo = QComboBox()
        format_combo.setFixedWidth(75)
        
        # Add standard format options
        format_combo.addItem(self.tr_("FORMAT_VIDEO_MP4"))
        format_combo.addItem(self.tr_("FORMAT_AUDIO_MP3"))
        
        # Check for errors
        has_error = False
        if hasattr(video_info, 'title'):
            has_error = video_info.title.startswith("Error:")
        
        format_combo.setEnabled(not has_error)
        
        # Set up cell widget
        format_cell = QWidget()
        format_layout = QHBoxLayout(format_cell)
        format_layout.addWidget(format_combo)
        format_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        format_layout.setContentsMargins(0, 0, 0, 0)
        
        # Determine column index based on platform
        format_col = 5 if self.current_platform == "YouTube" else 4
        self.video_table.setCellWidget(row, format_col, format_cell)
        
        # Get quality combo for connecting signals
        quality_col = 4 if self.current_platform == "YouTube" else 3
        quality_cell = self.video_table.cellWidget(row, quality_col)
        if quality_cell:
            quality_combo = quality_cell.findChild(QComboBox)
            # Get results from setup_video_qualities
            quality_combo_data = self.video_info_dict.get(row, {})
            audio_quality = None
            video_qualities = []
            
            if hasattr(quality_combo_data, 'formats') and quality_combo_data.formats:
                for fmt in quality_combo_data.formats:
                    if 'quality' in fmt:
                        if fmt.get('is_audio', False):
                            audio_quality = fmt['quality']
                        elif fmt['quality'] not in video_qualities:
                            video_qualities.append(fmt['quality'])
            
            # Connect format change signal
            format_combo.currentIndexChanged.connect(
                lambda index, combo=format_combo, q_combo=quality_combo, 
                       audio=audio_quality, video_qs=video_qualities: 
                self.on_format_changed(index, combo, q_combo, audio, video_qs)
            )
    
    def update_video_duration(self, row, video_info):
        """Update duration cell in the video table"""
        duration_str = ""
        if hasattr(video_info, 'duration'):
            duration_str = self.format_duration(video_info.duration)
            
        duration_item = QTableWidgetItem(duration_str)
        duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Determine column index based on platform
        duration_col = 6 if self.current_platform == "YouTube" else 5
        self.video_table.setItem(row, duration_col, duration_item)
    
    def update_video_size(self, row, video_info):
        """Update size cell in the video table"""
        size_str = ""
        if hasattr(video_info, 'formats'):
            size_str = self.estimate_size(video_info.formats)
            
        size_item = QTableWidgetItem(size_str)
        size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Determine column index based on platform
        size_col = 7 if self.current_platform == "YouTube" else 6
        self.video_table.setItem(row, size_col, size_item)
    
    def get_row_for_url(self, url):
        """Find row index for a given URL"""
        # Look through video_info_dict to find matching URL
        for row, info in self.video_info_dict.items():
            if hasattr(info, 'url') and info.url == url:
                return row
        return -1
    
    def update_video_info_error(self, row, error_message):
        """Update UI to show error for a video"""
        if row < 0 or row >= self.video_table.rowCount():
            return
            
        # Update title cell with error
        title_item = QTableWidgetItem(error_message)
        title_item.setToolTip(error_message)
        self.video_table.setItem(row, 1, title_item)
        
        # Disable checkbox
        checkbox_cell = self.video_table.cellWidget(row, 0)
        if checkbox_cell:
            checkbox = checkbox_cell.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(False)
                checkbox.setEnabled(False)
        
        # Update status bar
        if self.parent and self.parent.status_bar:
            self.parent.status_bar.showMessage(error_message)
            
        # Update button states
        self.update_button_states()

    def get_selected_rows(self):
        """Get a list of rows that have checkboxes selected"""
        selected_rows = []
        
        for row in range(self.video_table.rowCount()):
            checkbox_cell = self.video_table.cellWidget(row, 0)
            if checkbox_cell:
                checkbox = checkbox_cell.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected_rows.append(row)
                    
        return selected_rows

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
        spacer_width = 18  # Adjusted for better alignment
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
        
        # Add stretch to push Subtitle options and Download button to the right
        options_layout.addStretch(1)
        
        # Subtitle options - Create them directly in the main options layout
        # Create a frame for subtitle options with a border
        self.subtitle_frame = QFrame()
        self.subtitle_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.subtitle_frame.setFrameShadow(QFrame.Shadow.Raised)
        subtitle_layout = QHBoxLayout(self.subtitle_frame)
        subtitle_layout.setContentsMargins(8, 4, 8, 4)  # Smaller margins for compact display
        
        # Checkbox for downloading subtitles
        self.subtitle_checkbox = QCheckBox(self.tr_("CHECKBOX_DOWNLOAD_SUBTITLES"))
        self.subtitle_checkbox.setChecked(False)
        self.subtitle_checkbox.setToolTip(self.tr_("TOOLTIP_DOWNLOAD_SUBTITLES"))
        self.subtitle_checkbox.stateChanged.connect(self.on_subtitle_checkbox_changed)
        subtitle_layout.addWidget(self.subtitle_checkbox)
        
        # Dropdown for subtitle language
        self.subtitle_language_combo = QComboBox()
        self.subtitle_language_combo.addItem("English", "en")
        self.subtitle_language_combo.addItem("Vietnamese", "vi")
        self.subtitle_language_combo.addItem("Korean", "ko")
        self.subtitle_language_combo.addItem("Japanese", "ja")
        self.subtitle_language_combo.addItem("Indonesian", "id")
        self.subtitle_language_combo.setEnabled(False)  # Disabled by default
        self.subtitle_language_combo.setFixedWidth(100)
        subtitle_layout.addWidget(self.subtitle_language_combo)
        
        # Add subtitle frame to main options layout
        options_layout.addWidget(self.subtitle_frame)
        
        # Show subtitle options only for YouTube
        self.subtitle_frame.setVisible(self.current_platform == "YouTube")
        
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
        # Title column (always index 1, regardless of platform)
        if column == 1:  
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
        
        # Creator/Channel column (always index 2, regardless of platform)
        elif column == 2:  
            # Get creator from item
            item = self.video_table.item(row, column)
            if item and item.text():
                # Add Copy action
                creator_label = self.tr_("CONTEXT_COPY_CHANNEL") if self.current_platform == "YouTube" else self.tr_("CONTEXT_COPY_CREATOR")
                copy_action = QAction(creator_label, self)
                copy_action.triggered.connect(lambda: self.copy_to_clipboard(item.text(), "creator"))
                context_menu.addAction(copy_action)
        
        # Platform-specific columns
        elif self.current_platform == "YouTube" and column == 3:  # Playlist column
            # Get playlist from item
            item = self.video_table.item(row, column)
            if item and item.text():
                # Add Copy action
                copy_action = QAction(self.tr_("CONTEXT_COPY_PLAYLIST"), self)
                copy_action.triggered.connect(lambda: self.copy_to_clipboard(item.text(), "playlist"))
                context_menu.addAction(copy_action)
                
        elif (self.current_platform == "TikTok" and column == 7) or \
             (self.current_platform == "YouTube" and column == 8):  # Hashtags or Release Date
            # Get text from item
            item = self.video_table.item(row, column)
            if item and item.text():
                # Add Copy action based on platform
                if self.current_platform == "TikTok":
                    copy_action = QAction(self.tr_("CONTEXT_COPY_HASHTAGS"), self)
                    copy_action.triggered.connect(lambda: self.copy_to_clipboard(item.text(), "hashtags"))
                else:  # YouTube
                    copy_action = QAction(self.tr_("CONTEXT_COPY_RELEASE_DATE"), self)
                    copy_action.triggered.connect(lambda: self.copy_to_clipboard(item.text(), "release_date"))
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
            
            # Check if video has an error
            has_error = False
            if hasattr(video_info, 'title'):
                has_error = video_info.title.startswith("Error:")
            
            # Only show Rename if video has no errors and output folder is selected
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

    def on_subtitle_checkbox_changed(self):
        """Handle change in subtitle checkbox state"""
        # Enable/disable the language dropdown based on checkbox state
        is_checked = self.subtitle_checkbox.isChecked()
        self.subtitle_language_combo.setEnabled(is_checked)
        
        # Add logging for debugging
        print(f"Subtitle checkbox changed: {is_checked}")
        print(f"Language combo enabled: {self.subtitle_language_combo.isEnabled()}")
        
        # Show a message box for debugging
        QMessageBox.information(
            self,
            "Subtitle Option Changed",
            f"Subtitle downloading is now {'enabled' if is_checked else 'disabled'}\n"
            f"Language: {self.subtitle_language_combo.currentText()}"
        )
        
        # Update UI to reflect changes
        if is_checked:
            # Show a tooltip or status message
            if self.parent and self.parent.status_bar:
                language = self.subtitle_language_combo.currentText()
                self.parent.status_bar.showMessage(f"Selected subtitles in {language}")
        else:
            # Clear any status message
            if self.parent and self.parent.status_bar:
                self.parent.status_bar.showMessage(self.tr_("STATUS_READY"))

    def set_platform(self, platform):
        """Set the current platform and update UI accordingly"""
        print(f"Setting platform to: {platform}")
        self.current_platform = platform
        
        # Configure placeholder based on platform
        if platform == "TikTok":
            self.url_input.setPlaceholderText("Enter TikTok URL(s) - separate multiple URLs with spaces")
        elif platform == "YouTube":
            self.url_input.setPlaceholderText("Enter YouTube URL(s) - separate multiple URLs with spaces")
        else:
            self.url_input.setPlaceholderText("Enter URL(s) - separate multiple URLs with spaces")
        
        # Update the column headers for the new platform
        self.update_table_headers()
        
        # Show/hide subtitle options based on platform
        # Only YouTube supports subtitles for now
        self.subtitle_frame.setVisible(platform == "YouTube")
        
        # Reset checkbox when switching platforms
        if platform != "YouTube":
            self.subtitle_checkbox.setChecked(False)
            self.subtitle_language_combo.setEnabled(False)
        
        # Clear the table when changing platforms
        self.clear_table()
        
        # Reset URL input and disable download button
        self.url_input.clear()
        self.update_button_states()

    def clear_table(self):
        """Clear all rows in the video table"""
        self.video_table.setRowCount(0)
        self.video_info_dict.clear()