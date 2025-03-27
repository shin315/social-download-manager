#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Update dialog for Social Download Manager
"""

import os
import webbrowser
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QMessageBox, QProgressBar,
                             QFrame, QSizePolicy, QFileDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFontMetrics, QFont, QPixmap, QColor, QPainter
from urllib.parse import unquote


class HoverButton(QPushButton):
    """Button with hover effects"""
    
    def __init__(self, text, parent=None, accent_color="#0078d7", hover_color="#0086f0", pressed_color="#0067b8"):
        super().__init__(text, parent)
        self.accent_color = accent_color
        self.hover_color = hover_color
        self.pressed_color = pressed_color
        self.setMouseTracking(True)
        self.hovering = False
        
        # Round corners and styling
        self.setFixedHeight(36)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.accent_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 100px;
            }}
            
            QPushButton:hover {{
                background-color: {self.hover_color};
            }}
            
            QPushButton:pressed {{
                background-color: {self.pressed_color};
            }}
            
            QPushButton:disabled {{
                background-color: #666666;
                color: #aaaaaa;
            }}
        """)


class UpdateDialog(QDialog):
    """Dialog to show update information and download options"""
    
    def __init__(self, parent=None, update_info=None):
        super().__init__(parent)
        self.parent = parent
        self.update_info = update_info
        
        self.setWindowTitle(self.tr_("DIALOG_UPDATE_AVAILABLE"))
        self.setMinimumSize(450, 350)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        # Apply parent theme if available
        if hasattr(parent, 'current_theme'):
            self.current_theme = parent.current_theme
            if self.current_theme == "dark":
                self.base_color = "#2d2d2d"
                self.text_color = "#ffffff"
                self.secondary_bg = "#3d3d3d"
                self.border_color = "#555555"
                self.accent_color = "#0078d7"
                self.hover_color = "#0086f0"
                self.pressed_color = "#0067b8"
            else:
                self.base_color = "#f5f5f5"
                self.text_color = "#333333"
                self.secondary_bg = "#ffffff"
                self.border_color = "#cccccc"
                self.accent_color = "#0078d7"
                self.hover_color = "#0086f0"
                self.pressed_color = "#0067b8"
            
            self.setStyleSheet(f"""
                QDialog {{
                    background-color: {self.base_color};
                    color: {self.text_color};
                    border-radius: 8px;
                }}
            """)
        
        self.init_ui()
    
    def tr_(self, text):
        """Translate text if parent has translation method"""
        if hasattr(self.parent, 'tr_'):
            return self.parent.tr_(text)
        return text
    
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header with version information
        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)
        
        # Update icon
        update_icon_label = QLabel()
        update_icon_label.setFixedSize(80, 80)
        update_icon = QPixmap("assets/update.png")
        if update_icon.isNull():
            # Default icon size if image is not found
            update_icon_label.setText("🔄")
            update_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            update_icon_label.setStyleSheet(f"""
                font-size: 40px;
                color: {self.accent_color};
                background-color: {self.secondary_bg};
                border-radius: 40px;
                border: 2px solid {self.accent_color};
            """)
        else:
            update_icon_label.setPixmap(update_icon.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio))
            
        header_layout.addWidget(update_icon_label)
        
        # Version info
        version_layout = QVBoxLayout()
        version_layout.setSpacing(8)
        
        title_label = QLabel(self.tr_("DIALOG_UPDATE_AVAILABLE"))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {self.accent_color};")
        version_layout.addWidget(title_label)
        
        if self.update_info and "remote_version" in self.update_info:
            version_text = f"{self.tr_('DIALOG_NEW_VERSION')}: <b>{self.update_info['remote_version']}</b>"
            if "current_version" in self.update_info:
                version_text += f" ({self.tr_('DIALOG_CURRENT_VERSION')}: {self.update_info['current_version']})"
                
            version_label = QLabel(version_text)
            version_label.setTextFormat(Qt.TextFormat.RichText)
            version_layout.addWidget(version_label)
            
            if "release_date" in self.update_info and self.update_info["release_date"]:
                date_label = QLabel(f"{self.tr_('DIALOG_RELEASE_DATE')}: <i>{self.update_info['release_date']}</i>")
                date_label.setTextFormat(Qt.TextFormat.RichText)
                version_layout.addWidget(date_label)
        
        header_layout.addLayout(version_layout)
        header_layout.addStretch(1)
        main_layout.addLayout(header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(f"background-color: {self.border_color};")
        main_layout.addWidget(separator)
        
        # Release notes section
        notes_header = QLabel(self.tr_("DIALOG_RELEASE_NOTES"))
        notes_header.setFont(QFont("", 12, QFont.Weight.Bold))
        main_layout.addWidget(notes_header)
        
        notes_edit = QTextEdit()
        notes_edit.setReadOnly(True)
        notes_edit.setMinimumHeight(150)
        notes_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.secondary_bg};
                color: {self.text_color};
                border: 1px solid {self.border_color};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        
        # Set release notes
        if self.update_info and "release_notes" in self.update_info:
            notes_edit.setPlainText(self.update_info["release_notes"])
        else:
            notes_edit.setPlainText(self.tr_("DIALOG_NO_NOTES"))
        
        main_layout.addWidget(notes_edit)
        
        # GitHub link
        github_label = QLabel(f'<a href="https://github.com/shin315/social-download-manager/releases" style="color: {self.accent_color};">GitHub Releases</a>')
        github_label.setTextFormat(Qt.TextFormat.RichText)
        github_label.setOpenExternalLinks(True)
        github_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(github_label)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.secondary_bg};
                border: 1px solid {self.border_color};
                border-radius: 4px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {self.accent_color};
                border-radius: 3px;
            }}
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Close button
        close_button = QPushButton(self.tr_("DIALOG_CLOSE"))
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #666666;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: #777777;
            }}
            QPushButton:pressed {{
                background-color: #555555;
            }}
        """)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        # Download button
        download_button = QPushButton(self.tr_("DIALOG_DOWNLOAD"))
        download_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.accent_color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {self.hover_color};
            }}
            QPushButton:pressed {{
                background-color: {self.pressed_color};
            }}
        """)
        download_button.clicked.connect(self.download_update)
        button_layout.addWidget(download_button)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
    def download_update(self):
        """Download update from GitHub"""
        try:
            # Get download URL for current platform
            import platform
            os_type = platform.system().lower()
            
            # Get version and construct basic URL
            version = self.update_info.get("remote_version", "1.1.0")
            
            # For debugging/testing
            if version == "1.5.0":
                # Use a test ZIP file that exists
                url = "https://github.com/atom/atom/releases/download/v1.60.0/atom-windows.zip"
            else:
                # Normal URL construction
                base_url = "https://github.com/shin315/social-download-manager/releases/download"
                if os_type == "windows":
                    url = f"{base_url}/v{version}/social_download_manager_windows_v{version}.zip"
                elif os_type == "darwin":  # macOS
                    url = f"{base_url}/v{version}/social_download_manager_mac_v{version}.zip"
                else:  # Linux
                    url = f"{base_url}/v{version}/social_download_manager_linux_v{version}.zip"
            
            # Get default file name
            default_file_name = unquote(os.path.basename(url))
            
            # Open file dialog to choose save location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                self.tr_("DIALOG_CHOOSE_SAVE_LOCATION"),
                os.path.join(os.path.expanduser("~"), "Downloads", default_file_name),
                "ZIP Files (*.zip)"
            )
            
            # If user canceled, return
            if not file_path:
                return
                
            # Start download thread
            self.download_thread = DownloadThread(url, file_path)
            self.download_thread.progress.connect(self.update_progress)
            self.download_thread.finished.connect(self.download_finished)
            self.download_thread.error.connect(self.download_error)
            
            # Show progress bar
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Start download
            self.download_thread.start()
            
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr_("DIALOG_ERROR"),
                f"{self.tr_('DIALOG_DOWNLOAD_ERROR')}: {str(e)}"
            )
            
    def update_progress(self, progress):
        """Update progress bar value"""
        self.progress_bar.setValue(progress)
        
    def download_finished(self, file_path):
        """Handle download completion"""
        self.progress_bar.setVisible(False)
        
        # Show success message with file location
        QMessageBox.information(
            self,
            self.tr_("DIALOG_DOWNLOAD_COMPLETE"),
            self.tr_("DIALOG_DOWNLOAD_COMPLETE_MSG").format(file_path)
        )
        
        # Open folder containing the file
        try:
            import os
            # Use appropriate method based on platform
            if os.name == 'nt':  # Windows
                os.startfile(os.path.dirname(file_path))
            elif os.name == 'posix':  # macOS/Linux
                import subprocess
                subprocess.call(('xdg-open', os.path.dirname(file_path)))
        except Exception as e:
            print(f"Error opening folder: {str(e)}")
        
        self.accept()
        
    def download_error(self, error):
        """Handle download error"""
        self.progress_bar.setVisible(False)
        QMessageBox.warning(
            self,
            self.tr_("DIALOG_ERROR"),
            f"{self.tr_('DIALOG_DOWNLOAD_ERROR')}: {error}"
        )


class DownloadThread(QThread):
    """Thread for downloading update file"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, url, file_path):
        super().__init__()
        self.url = url
        self.file_path = file_path
        
    def run(self):
        try:
            import os
            import requests
            
            # Create directory if it doesn't exist
            download_dir = os.path.dirname(self.file_path)
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
                
            # Download file with progress
            response = requests.get(self.url, stream=True, timeout=30)
            total_size = int(response.headers.get('content-length', 0))
            
            if response.status_code == 200:
                with open(self.file_path, 'wb') as f:
                    if total_size == 0:  # No content length header
                        f.write(response.content)
                        self.progress.emit(100)
                    else:
                        downloaded = 0
                        for data in response.iter_content(chunk_size=4096):
                            downloaded += len(data)
                            f.write(data)
                            progress = int(downloaded * 100 / total_size)
                            self.progress.emit(progress)
                            
                self.finished.emit(self.file_path)
            else:
                self.error.emit(f"HTTP Error: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.error.emit(f"Connection error: {str(e)}")
        except Exception as e:
            self.error.emit(str(e))


class UpdateCheckerThread(QThread):
    """Thread for checking updates in background"""
    
    # Signal to emit update check results
    update_check_complete = pyqtSignal(dict)
    
    def __init__(self, update_checker):
        super().__init__()
        self.update_checker = update_checker
        
    def run(self):
        """Run update check in background thread"""
        try:
            result = self.update_checker.get_update_info()
            self.update_check_complete.emit(result)
        except Exception as e:
            self.update_check_complete.emit({
                "success": False,
                "error": str(e)
            }) 