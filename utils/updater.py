import os
import sys
import json
import requests
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                            QHBoxLayout, QTextBrowser, QMessageBox, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
import platform

# Current version of the application
CURRENT_VERSION = "1.2.0"
# URL of version.json file on GitHub
VERSION_URL = "https://raw.githubusercontent.com/shin315/social-download-manager/main/version.json"

class UpdateCheckerThread(QThread):
    """Thread to check for updates without freezing the UI"""
    update_available = pyqtSignal(dict)
    no_update = pyqtSignal()
    error = pyqtSignal(str)
    
    def run(self):
        try:
            # Load version info from GitHub
            response = requests.get(VERSION_URL, timeout=5)
            if response.status_code == 200:
                version_info = response.json()
                
                # Compare versions
                current = [int(x) for x in CURRENT_VERSION.split('.')]
                latest = [int(x) for x in version_info["version"].split('.')]
                
                # Check if newer version exists
                newer = False
                for i in range(min(len(current), len(latest))):
                    if latest[i] > current[i]:
                        newer = True
                        break
                    elif latest[i] < current[i]:
                        break
                
                if newer:
                    self.update_available.emit(version_info)
                else:
                    self.no_update.emit()
            else:
                self.error.emit(f"Error loading update information: {response.status_code}")
        except Exception as e:
            self.error.emit(f"Error checking for updates: {str(e)}")

class DownloadUpdateThread(QThread):
    """Thread to download the update"""
    progress = pyqtSignal(int)
    complete = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, url, destination):
        super().__init__()
        self.url = url
        self.destination = destination
        
    def run(self):
        try:
            # Download update file
            response = requests.get(self.url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            if response.status_code == 200:
                downloaded = 0
                with open(self.destination, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            # Update progress
                            if total_size > 0:
                                self.progress.emit(int(downloaded * 100 / total_size))
                
                self.complete.emit(self.destination)
            else:
                self.error.emit(f"Error downloading update: {response.status_code}")
        except Exception as e:
            self.error.emit(f"Error downloading update: {str(e)}")

class UpdateDialog(QDialog):
    """Dialog to show update notification"""
    def __init__(self, version_info, parent=None):
        super().__init__(parent)
        self.version_info = version_info
        self.parent = parent
        
        # Get language strings from parent if available
        self.tr_ = getattr(parent, 'tr_', lambda x: x)
        
        self.setWindowTitle(self.tr_("UPDATE_AVAILABLE_TITLE"))
        self.setMinimumWidth(450)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title with current and new version
        title_text = self.tr_("UPDATE_AVAILABLE_MESSAGE").format(
            self.version_info['version'], 
            CURRENT_VERSION
        )
        title = QLabel(title_text)
        title.setWordWrap(True)
        layout.addWidget(title)
        
        # Release date
        release_date = QLabel(f"<b>{self.version_info['release_date']}</b>")
        release_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(release_date)
        
        # Release notes
        layout.addWidget(QLabel(f"<b>{self.tr_('UPDATE_DIALOG_RELEASE_NOTES')}</b>"))
        notes = QTextBrowser()
        notes.setText(self.version_info['release_notes'])
        notes.setMaximumHeight(150)
        layout.addWidget(notes)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        # Skip button
        skip_btn = QPushButton(self.tr_("UPDATE_DIALOG_SKIP"))
        skip_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(skip_btn)
        
        # Remind me later button
        remind_btn = QPushButton(self.tr_("UPDATE_DIALOG_REMIND"))
        remind_btn.clicked.connect(self.remind_later)
        buttons_layout.addWidget(remind_btn)
        
        # Download button
        download_btn = QPushButton(self.tr_("UPDATE_DIALOG_DOWNLOAD"))
        download_btn.setDefault(True)
        download_btn.clicked.connect(self.download_update)
        buttons_layout.addWidget(download_btn)
        
        layout.addLayout(buttons_layout)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
    def remind_later(self):
        # Close dialog but don't save "skipped" state
        self.reject()
        
    def download_update(self):
        """Download the update"""
        # Determine URL based on operating system
        os_type = platform.system().lower()
        if os_type == "windows":
            url = self.version_info["download_url"]["windows"]
        elif os_type == "darwin":  # macOS
            url = self.version_info["download_url"]["mac"]
        elif os_type == "linux":
            url = self.version_info["download_url"]["linux"]
        else:
            QMessageBox.warning(self, "Not Supported", f"The operating system {os_type} is not supported yet.")
            return
        
        # Set status message in parent if available
        if hasattr(self.parent, 'set_status'):
            self.parent.set_status(self.tr_("UPDATE_DOWNLOADING"))
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        
        # Determine download directory
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        # File name
        file_name = url.split("/")[-1]
        destination = os.path.join(download_dir, file_name)
        
        # Download in a separate thread
        self.download_thread = DownloadUpdateThread(url, destination)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.complete.connect(self.download_complete)
        self.download_thread.error.connect(self.download_error)
        self.download_thread.start()
    
    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)
    
    def download_complete(self, file_path):
        """Handle download completion"""
        # Open folder containing the file
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(file_path)))
        
        # Notification
        QMessageBox.information(
            self, 
            self.tr_("UPDATE_DOWNLOAD_COMPLETE"),
            self.tr_("UPDATE_DOWNLOAD_COMPLETE_MSG").format(file_path)
        )
        self.accept()
    
    def download_error(self, error_msg):
        """Handle download error"""
        self.progress_bar.setVisible(False)
        QMessageBox.warning(
            self, 
            self.tr_("UPDATE_DOWNLOAD_ERROR"),
            self.tr_("UPDATE_DOWNLOAD_ERROR_MSG")
        )

def check_for_updates(parent=None, silent=False):
    """
    Check for updates and display dialog if a new update is available.
    
    Args:
        parent: Parent widget to display dialog
        silent: If True, only check without showing notification if no update
    """
    # Get translation function from parent if available
    tr_ = getattr(parent, 'tr_', lambda x: x)
    
    # Set status message in parent if available and not in silent mode
    if not silent and hasattr(parent, 'set_status'):
        parent.set_status(tr_("UPDATE_CHECKING"))
    
    checker = UpdateCheckerThread()
    
    def on_update_available(version_info):
        dialog = UpdateDialog(version_info, parent)
        dialog.exec()
        
        # Reset status in parent if available
        if hasattr(parent, 'set_status'):
            parent.set_status(tr_("UPDATE_AVAILABLE_NOTIFICATION"))
    
    def on_no_update():
        if not silent:
            QMessageBox.information(
                parent, 
                tr_("UPDATE_NO_NEW_VERSION"),
                tr_("UPDATE_NO_NEW_VERSION_DESC").format(CURRENT_VERSION)
            )
            
            # Reset status in parent if available
            if hasattr(parent, 'set_status'):
                parent.set_status(tr_("STATUS_READY"))
    
    def on_error(error_msg):
        if not silent:
            QMessageBox.warning(
                parent, 
                tr_("UPDATE_ERROR"),
                error_msg
            )
            
            # Reset status in parent if available
            if hasattr(parent, 'set_status'):
                parent.set_status(tr_("STATUS_READY"))
    
    checker.update_available.connect(on_update_available)
    checker.no_update.connect(on_no_update)
    checker.error.connect(on_error)
    checker.start()
    
    return checker  # Return thread to prevent early garbage collection 