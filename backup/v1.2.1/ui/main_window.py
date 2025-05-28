from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QComboBox,
                             QFileDialog, QCheckBox, QHeaderView, QMessageBox,
                             QStatusBar, QMenu, QProgressBar, QDialog, QToolTip)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QActionGroup, QFont, QFontDatabase, QKeySequence
from PyQt6.QtWidgets import QApplication
import os
import json
import sys
from datetime import datetime

from ui.video_info_tab import VideoInfoTab
from ui.downloaded_videos_tab import DownloadedVideosTab
from ui.donate_tab import DonateTab
from ui.update_dialog import UpdateDialog, UpdateCheckerThread
from localization import get_language_manager
from utils.update_checker import UpdateChecker
from utils.downloader import TikTokDownloader

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # In development mode, use current directory
        if getattr(sys, 'frozen', False):
            # If running as a bundled executable
            base_path = os.path.dirname(sys.executable)
        else:
            # If running in development environment
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, relative_path)

class MainWindow(QMainWindow):
    """Main window of the Social Download Manager application"""
    
    # Signal emitted when language is changed - không cần tham số
    language_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.output_folder = ""
        self.current_theme = "dark"  # Store current theme
        
        # Initialize language manager
        self.lang_manager = get_language_manager()
        
        # Store platform actions to update icons based on theme
        self.platform_actions = {}
        
        self.setup_font()
        self.init_ui()
        
        # Load output folder, language and theme from config if available
        self.load_config()
        
        # Áp dụng rõ ràng theme hiện tại sau khi đã load từ config
        self.set_theme(self.current_theme)
        
        # Update UI based on current language
        self.update_ui_language()
        
        # Check for FFmpeg availability at startup
        self.check_ffmpeg_availability()

    def setup_font(self):
        """Set up Inter font for the application"""
        # Create normal Inter font (not bold)
        font = QFont("Inter", 10, QFont.Weight.Normal)
        QApplication.setFont(font)

    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Social Download Manager")
        self.setGeometry(100, 100, 1000, 700)  # Adjust window size to be larger
        self.setWindowIcon(QIcon(get_resource_path("assets/Logo_new_32x32.png")))
        
        # Set up main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Create menu bar
        self.create_menu_bar()

        # Create tab widget and tabs
        self.tab_widget = QTabWidget()
        
        # Video Info Tab
        self.video_info_tab = VideoInfoTab(self)
        self.tab_widget.addTab(self.video_info_tab, self.tr_("TAB_VIDEO_INFO"))

        # Downloaded Videos Tab
        self.downloaded_videos_tab = DownloadedVideosTab(self)
        self.tab_widget.addTab(self.downloaded_videos_tab, self.tr_("TAB_DOWNLOADED_VIDEOS"))

        # Set tab widget as central widget
        main_layout.addWidget(self.tab_widget)

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(self.tr_("STATUS_READY"))
        
        # Initialize donate dialog (not displayed)
        self.donate_dialog = None

    def create_menu_bar(self):
        """Create menu bar with menus and actions"""
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu(self.tr_("MENU_FILE"))
        
        # Action: Set Output Folder
        set_output_action = QAction(self.tr_("MENU_CHOOSE_FOLDER"), self)
        set_output_action.setShortcut("Ctrl+O")
        set_output_action.triggered.connect(self.set_output_folder)
        file_menu.addAction(set_output_action)
        
        file_menu.addSeparator()
        
        # Action: Exit
        exit_action = QAction(self.tr_("MENU_EXIT"), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Platform Menu (YouTube, Instagram, Facebook)
        platform_menu = menu_bar.addMenu(self.tr_("MENU_PLATFORM"))
        
        # Choose icon suffix based on current theme
        icon_suffix = "-outlined" if self.current_theme == "dark" else "-bw"
        
        # Action: TikTok (Current)
        tiktok_icon = QIcon(get_resource_path(f"assets/platforms/tiktok{icon_suffix}.png"))
        tiktok_action = QAction(tiktok_icon, self.tr_("PLATFORM_TIKTOK"), self)
        tiktok_action.setCheckable(True)
        tiktok_action.setChecked(True)  # Default is TikTok
        platform_menu.addAction(tiktok_action)
        
        platform_menu.addSeparator()
        
        # Action: YouTube
        youtube_icon = QIcon(get_resource_path(f"assets/platforms/youtube{icon_suffix}.png"))
        youtube_action = QAction(youtube_icon, self.tr_("PLATFORM_YOUTUBE"), self)
        youtube_action.triggered.connect(self.show_developing_feature)
        platform_menu.addAction(youtube_action)
        
        # Action: Instagram
        instagram_icon = QIcon(get_resource_path(f"assets/platforms/instagram{icon_suffix}.png"))
        instagram_action = QAction(instagram_icon, self.tr_("PLATFORM_INSTAGRAM"), self)
        instagram_action.triggered.connect(self.show_developing_feature)
        platform_menu.addAction(instagram_action)
        
        # Action: Facebook
        facebook_icon = QIcon(get_resource_path(f"assets/platforms/facebook{icon_suffix}.png"))
        facebook_action = QAction(facebook_icon, self.tr_("PLATFORM_FACEBOOK"), self)
        facebook_action.triggered.connect(self.show_developing_feature)
        platform_menu.addAction(facebook_action)
        
        # Store actions in dictionary to update icons when theme changes
        self.platform_actions = {
            "tiktok": tiktok_action,
            "youtube": youtube_action,
            "instagram": instagram_action,
            "facebook": facebook_action
        }
        
        # Theme Menu (Dark/Light)
        theme_menu = menu_bar.addMenu(self.tr_("MENU_APPEARANCE"))
        
        # Create action group to select one of the themes
        light_mode_action = QAction(self.tr_("MENU_LIGHT_MODE"), self)
        light_mode_action.setCheckable(True)
        light_mode_action.triggered.connect(lambda: self.set_theme("light"))
        theme_menu.addAction(light_mode_action)
        
        dark_mode_action = QAction(self.tr_("MENU_DARK_MODE"), self)
        dark_mode_action.setCheckable(True)
        dark_mode_action.triggered.connect(lambda: self.set_theme("dark"))
        theme_menu.addAction(dark_mode_action)
        
        # Đặt checked cho theme hiện tại dựa trên self.current_theme
        if self.current_theme == "light":
            light_mode_action.setChecked(True)
            dark_mode_action.setChecked(False)
        else:  # dark theme
            dark_mode_action.setChecked(True)
            light_mode_action.setChecked(False)
        
        # Create action group to select only one theme
        theme_group = QActionGroup(self)
        theme_group.addAction(light_mode_action)
        theme_group.addAction(dark_mode_action)
        theme_group.setExclusive(True)
        
        # Language Menu
        self.lang_menu = menu_bar.addMenu(self.tr_("MENU_LANGUAGE"))
        self.create_language_menu()
        
        # Help Menu
        help_menu = menu_bar.addMenu(self.tr_("MENU_HELP"))
        
        # Action: About
        about_action = QAction(self.tr_("MENU_ABOUT"), self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # Action: Check for Updates
        check_updates_action = QAction(self.tr_("MENU_CHECK_UPDATES"), self)
        check_updates_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(check_updates_action)
        
        # Add separator before Buy Me A Coffee
        help_menu.addSeparator()
        
        # Action: Buy Me A Coffee (placed in Help menu instead of separate menu)
        donate_action = QAction(self.tr_("MENU_BUY_COFFEE"), self)
        donate_action.triggered.connect(self.show_donate_tab)
        help_menu.addAction(donate_action)

    def create_language_menu(self):
        """Create dynamic language menu from available languages"""
        # Clear all existing actions in menu
        self.lang_menu.clear()
        
        # Create action group so only one language can be selected
        lang_action_group = QActionGroup(self)
        lang_action_group.setExclusive(True)
        
        # Get language list from LanguageManager
        available_languages = self.lang_manager.get_available_languages()
        current_language = self.lang_manager.current_language
        
        # Add each language to menu
        for lang_code, lang_name in available_languages.items():
            lang_action = QAction(lang_name, self)
            lang_action.setCheckable(True)
            lang_action.setChecked(lang_code == current_language)
            lang_action.triggered.connect(lambda checked, code=lang_code: self.set_language(code))
            lang_action_group.addAction(lang_action)
            self.lang_menu.addAction(lang_action)

    def set_output_folder(self):
        """Set output folder"""
        # Use current folder as starting point if available
        start_folder = self.output_folder if self.output_folder else ""
        
        folder = QFileDialog.getExistingDirectory(
            self, self.tr_("MENU_CHOOSE_FOLDER"), start_folder)
        if folder:
            self.output_folder = folder
            self.video_info_tab.update_output_folder(folder)
            self.status_bar.showMessage(self.tr_("STATUS_FOLDER_SET").format(folder))
            
            # Save to config file
            try:
                self.save_config('last_output_folder', folder)
                # Log to debug file
                log_file = get_resource_path('log.txt')
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"[{datetime.now()}] MainWindow set_output_folder called: Saving '{folder}' to config\n")
            except Exception as e:
                # Log error
                try:
                    log_file = get_resource_path('log.txt')
                    with open(log_file, 'a', encoding='utf-8') as log:
                        log.write(f"[{datetime.now()}] Error saving folder from MainWindow: {str(e)}\n")
                except:
                    pass

    def set_language(self, lang_code):
        """Set application language"""
        # Set language in manager
        self.lang_manager.set_language(lang_code)
        
        # Notify all tabs of language change
        self.language_changed.emit()
        
        # Update tab names
        self.tab_widget.setTabText(0, self.tr_("TAB_VIDEO_INFO"))
        self.tab_widget.setTabText(1, self.tr_("TAB_DOWNLOADED_VIDEOS"))
        
        # Update menu items
        self.update_ui_language()
        
        # Update status bar
        lang_name = self.tr_("LANGUAGE_NAME")
        self.status_bar.showMessage(self.tr_("STATUS_LANGUAGE_CHANGED").format(lang_name))
        
        # Save language setting to config
        self.save_config('language', lang_code)
        # Log language change
        try:
            log_file = get_resource_path('log.txt')
            with open(log_file, 'a', encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] Language changed to: {lang_code}\n")
        except:
            pass

    def update_ui_language(self):
        """Update UI with current language"""
        # Update tab titles
        self.tab_widget.setTabText(0, self.tr_("TAB_VIDEO_INFO"))
        self.tab_widget.setTabText(1, self.tr_("TAB_DOWNLOADED_VIDEOS"))
        
        # Update menu
        self.menuBar().clear()
        self.create_menu_bar()
        
        # Update other components if needed
        self.video_info_tab.update_language()
        self.downloaded_videos_tab.update_language()
        
    def tr_(self, key):
        """Translate string based on current language"""
        return self.lang_manager.get_text(key)

    def check_for_updates(self):
        """Check for software updates"""
        # Show status message
        self.status_bar.showMessage(self.tr_("DIALOG_CHECKING_UPDATES"))
        
        # Create update checker
        self.update_checker = UpdateChecker()
        
        # Create and run thread
        self.update_thread = UpdateCheckerThread(self.update_checker)
        self.update_thread.update_check_complete.connect(self.handle_update_result)
        self.update_thread.start()
    
    def handle_update_result(self, result):
        """Handle the results from update check"""
        if not result.get("success", False):
            # Error checking for updates
            QMessageBox.warning(
                self,
                self.tr_("DIALOG_ERROR"),
                f"{self.tr_('DIALOG_UPDATE_ERROR')}: {result.get('error', 'Unknown error')}"
            )
            self.status_bar.showMessage(self.tr_("DIALOG_UPDATE_ERROR"))
            return
            
        if not result.get("has_update", False):
            # No updates available
            QMessageBox.information(
                self,
                self.tr_("DIALOG_NO_UPDATES"),
                self.tr_("DIALOG_LATEST_VERSION")
            )
            self.status_bar.showMessage(self.tr_("DIALOG_LATEST_VERSION"))
            return
            
        # Show update dialog with result information
        update_dialog = UpdateDialog(self, result)
        update_dialog.exec()
        
        # Reset status after dialog closes
        self.status_bar.showMessage(self.tr_("STATUS_READY"))

    def show_developing_feature(self):
        """Display notification for features under development"""
        QMessageBox.information(
            self, self.tr_("DIALOG_COMING_SOON"), self.tr_("DIALOG_FEATURE_DEVELOPING"))

    def show_about(self):
        """Display information about the application"""
        try:
            # Sử dụng AboutDialog nếu có thể import
            from ui.about_dialog import AboutDialog
            dialog = AboutDialog(self)
            dialog.exec()
        except ImportError:
            # Fallback nếu không tìm thấy AboutDialog
            QMessageBox.about(
                self, 
                self.tr_("ABOUT_TITLE"),
                f"{self.tr_('ABOUT_MESSAGE')}\n\n"
                f"Version: 1.2.1\n"
                f"© 2025 Shin\n\n"
                f"Key Features:\n"
                f"• Download TikTok videos in various formats\n"
                f"• Manage downloaded videos with detailed information\n"
                f"• Multi-language support (English & Vietnamese)\n"
                f"• Dark and Light theme options\n\n"
                f"Developer: Shin\n"
                f"Email: shin315@gmail.com\n"
                f"GitHub: github.com/shin315/social-download-manager"
            )
        
    def set_theme(self, theme):
        """Set application theme (dark/light)"""
        self.current_theme = theme
        
        # Apply theme to all components
        if theme == "dark":
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    font-family: 'Inter';
                }
                QTabWidget::pane {
                    border: 1px solid #444444;
                    background-color: #2d2d2d;
                }
                QTabBar::tab {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    padding: 8px 15px;
                    border: 1px solid #444444;
                }
                QTabBar::tab:selected {
                    background-color: #0078d7;
                    font-weight: normal;
                }
                QTabBar::tab:hover:!selected {
                    background-color: #505050;
                }
                QTableWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    gridline-color: #444444;
                    border: 1px solid #444444;
                }
                QTableWidget::item {
                    border-bottom: 1px solid #444444;
                    color: #ffffff;
                }
                QTableWidget::item:selected {
                    background-color: #0078d7;
                }
                QTableWidget::item:hover {
                    background-color: #3a3a3a;
                }
                QHeaderView::section {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    padding: 5px;
                    border: 1px solid #444444;
                }
                QHeaderView::section:hover {
                    background-color: #505050;
                }
                QLineEdit, QComboBox {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 5px;
                }
                QComboBox:hover {
                    background-color: #505050;
                    border: 1px solid #666666;
                }
                QComboBox::drop-down:hover {
                    background-color: #505050;
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
                QPushButton:pressed {
                    background-color: #0067b8;
                }
                QPushButton:disabled {
                    background-color: #444444 !important;
                    color: #777777 !important;
                    border: none !important;
                }
                QCheckBox {
                    color: #ffffff;
                }
                QCheckBox::indicator {
                    width: 13px;
                    height: 13px;
                    background-color: #3d3d3d;
                    border: 1px solid #555555;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #0078d7;
                    border: 1px solid #0078d7;
                    border-radius: 2px;
                }
                QTableWidget QCheckBox::indicator {
                    width: 13px;
                    height: 13px;
                    background-color: #3d3d3d;
                    border: 1px solid #555555;
                    border-radius: 2px;
                }
                QTableWidget QCheckBox::indicator:checked {
                    background-color: #0078d7;
                    border: 1px solid #0078d7;
                    border-radius: 2px;
                }
                QMenuBar {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QMenuBar::item:selected {
                    background-color: #3d3d3d;
                }
                QMenuBar::item:hover {
                    background-color: #3d3d3d;
                }
                QMenu {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #444444;
                }
                QMenu::item:selected {
                    background-color: #0078d7;
                }
                QMenu::item:hover:!selected {
                    background-color: #3d3d3d;
                }
                QStatusBar {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QDialog {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border-radius: 8px;
                }
                /* Synchronize colors for icons in context menu */
                QMenu::icon {
                    color: #cccccc;
                }
                /* Colors for all actions in context menu */
                QMenu QAction {
                    color: #ffffff;
                }
                /* Colors for all icons in right-click */
                QMenu::indicator:non-exclusive:checked {
                    image: url(:/qt-project.org/styles/commonstyle/images/checkbox-checked.png);
                    color: #cccccc;
                }
                /* Set common color for all icons in context menu */
                QMenu QIcon {
                    color: #cccccc;
                }
                /* Color for cut, copy, paste icons and other icons in context menu */
                QLineEdit::contextmenu-item QMenu::icon,
                QLineEdit::contextmenu-item QAction::icon,
                QTextEdit::contextmenu-item QMenu::icon,
                QTextEdit::contextmenu-item QAction::icon,
                QPlainTextEdit::contextmenu-item QMenu::icon,
                QPlainTextEdit::contextmenu-item QAction::icon {
                    color: #cccccc;
                }
                /* Title bar */
                QDockWidget::title {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QMainWindow::title {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QWidget#titleBar {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QToolTip {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 5px;
                    border-radius: 3px;
                }
            """)
            self.status_bar.showMessage(self.tr_("STATUS_DARK_MODE_ENABLED"))
            
            # Force tooltips to update immediately by hiding any visible tooltip
            QToolTip.hideText()
            # Set application-wide tooltip style
            QApplication.instance().setStyleSheet("""
                QToolTip {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 5px;
                    border-radius: 3px;
                }
            """)
            
            # Update icons to white outline version for better visibility
            self.update_platform_icons("-outlined")
        else:
            # Apply Light mode stylesheet with better contrast colors
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #f0f0f0;
                    color: #333333;
                    font-family: 'Inter';
                }
                QTabWidget::pane {
                    background-color: #f0f0f0;
                }
                QTabBar::tab {
                    background-color: #e0e0e0;
                    color: #333333;
                    padding: 8px 15px;
                    border: 1px solid #cccccc;
                }
                QTabBar::tab:selected {
                    background-color: #0078d7;
                    color: #ffffff;
                    font-weight: normal;
                }
                QTabBar::tab:hover:!selected {
                    background-color: #d0d0d0;
                }
                QTableWidget {
                    background-color: #ffffff;
                    color: #333333;
                    gridline-color: #dddddd;
                    border: 1px solid #cccccc;
                }
                QTableWidget::item {
                    border-bottom: 1px solid #eeeeee;
                    color: #333333;
                }
                QTableWidget::item:selected {
                    background-color: #0078d7;
                    color: #ffffff;
                }
                QTableWidget::item:hover {
                    background-color: #e8e8e8;
                }
                QHeaderView::section {
                    background-color: #e0e0e0;
                    color: #333333;
                    padding: 5px;
                    border: 1px solid #cccccc;
                }
                QHeaderView::section:hover {
                    background-color: #d0d0d0;
                }
                QLineEdit, QComboBox {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #cccccc;
                    padding: 5px;
                }
                QComboBox:hover {
                    background-color: #f5f5f5;
                    border: 1px solid #bbbbbb;
                }
                QComboBox::drop-down:hover {
                    background-color: #e5e5e5;
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
                QPushButton:pressed {
                    background-color: #0067b8;
                }
                QPushButton:disabled {
                    background-color: #e5e5e5 !important;
                    color: #a0a0a0 !important;
                    border: 1px solid #d0d0d0 !important;
                }
                QCheckBox {
                    color: #333333;
                }
                QCheckBox::indicator {
                    width: 13px;
                    height: 13px;
                    background-color: #e0e0e0;
                    border: 1px solid #aaaaaa;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #0078d7;
                    border: 1px solid #0078d7;
                    border-radius: 2px;
                }
                QTableWidget QCheckBox::indicator {
                    width: 13px;
                    height: 13px;
                    background-color: #e0e0e0;
                    border: 1px solid #aaaaaa;
                    border-radius: 2px;
                }
                QTableWidget QCheckBox::indicator:checked {
                    background-color: #0078d7;
                    border: 1px solid #0078d7;
                    border-radius: 2px;
                }
                QMenuBar {
                    background-color: #e0e0e0;
                    color: #333333;
                    border-bottom: 1px solid #cccccc;
                }
                QMenuBar::item:selected {
                    background-color: #d0d0d0;
                }
                QMenuBar::item:hover {
                    background-color: #d0d0d0;
                }
                QMenu {
                    background-color: #f5f5f5;
                    color: #333333;
                    border: 1px solid #cccccc;
                }
                QMenu::item:selected {
                    background-color: #0078d7;
                    color: #ffffff;
                }
                QMenu::item:hover:!selected {
                    background-color: #e0e0e0;
                }
                QStatusBar {
                    background-color: #e0e0e0;
                    color: #333333;
                    border-top: 1px solid #cccccc;
                }
                QDialog {
                    background-color: #f5f5f5;
                    color: #333333;
                    border-radius: 8px;
                }
                /* Synchronize colors for icons in context menu */
                QMenu::icon {
                    color: #555555;
                }
                /* Colors for all actions in context menu */
                QMenu QAction {
                    color: #333333;
                }
                /* Colors for all icons in right-click */
                QMenu::indicator:non-exclusive:checked {
                    image: url(:/qt-project.org/styles/commonstyle/images/checkbox-checked.png);
                    color: #555555;
                }
                /* Set common color for all icons in context menu */
                QMenu QIcon {
                    color: #555555;
                }
                /* Title bar */
                QDockWidget::title {
                    background-color: #e0e0e0;
                    color: #333333;
                }
                QMainWindow::title {
                    background-color: #e0e0e0;
                    color: #333333;
                }
                QWidget#titleBar {
                    background-color: #e0e0e0;
                    color: #333333;
                }
                QToolTip {
                    background-color: #f5f5f5;
                    color: #333333;
                    border: 1px solid #cccccc;
                    padding: 5px;
                    border-radius: 3px;
                }
            """)
            self.status_bar.showMessage(self.tr_("STATUS_LIGHT_MODE_ENABLED"))
            
            # Force tooltips to update immediately by hiding any visible tooltip
            QToolTip.hideText()
            # Set application-wide tooltip style
            QApplication.instance().setStyleSheet("""
                QToolTip {
                    background-color: #f5f5f5;
                    color: #333333;
                    border: 1px solid #cccccc;
                    padding: 5px;
                    border-radius: 3px;
                }
            """)
            
            # Update icons to black version
            self.update_platform_icons("-bw")
            
        # Update colors for child tabs
        if hasattr(self, 'downloaded_videos_tab') and hasattr(self.downloaded_videos_tab, 'apply_theme_colors'):
            self.downloaded_videos_tab.apply_theme_colors(theme)
            
        if hasattr(self, 'video_info_tab') and hasattr(self.video_info_tab, 'apply_theme_colors'):
            self.video_info_tab.apply_theme_colors(theme)
            
        # Update theme for donate dialog if already created
        if hasattr(self, 'donate_dialog') and self.donate_dialog:
            # Update dialog style
            if theme == "dark":
                self.donate_dialog.setStyleSheet("background-color: #2d2d2d; color: #ffffff;")
            else:
                self.donate_dialog.setStyleSheet("background-color: #f5f5f5; color: #333333;")
            
            # Update donate_tab if exists
            if hasattr(self, 'donate_tab'):
                self.donate_tab.apply_theme_colors(self.current_theme)

        # Save theme setting to config
        self.save_config('theme', theme)
        # Log theme change
        try:
            log_file = get_resource_path('log.txt')
            with open(log_file, 'a', encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] Theme changed to: {theme}\n")
        except:
            pass

    def update_platform_icons(self, suffix):
        """Update icons for platform menus based on theme"""
        if not hasattr(self, 'platform_actions'):
            return
            
        for platform, action in self.platform_actions.items():
            icon_path = get_resource_path(f"assets/platforms/{platform}{suffix}.png")
            action.setIcon(QIcon(icon_path))

    def show_donate_tab(self):
        """Display donate dialog"""
        # Create dialog if not exists
        if not self.donate_dialog:
            self.donate_dialog = QDialog(self)
            self.donate_dialog.setObjectName("donateDialog")  # Add objectName for dialog
            self.donate_dialog.setWindowTitle(self.tr_("DONATE_TITLE"))
            self.donate_dialog.setMinimumSize(320, 340)  # Reduced height from 400 to 340
            self.donate_dialog.setMaximumSize(330, 350)  # Reduced height from 420 to 350
            self.donate_dialog.setWindowFlags(self.donate_dialog.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
            self.donate_dialog.setModal(True)
            
            # Set style directly based on current theme
            if self.current_theme == "dark":
                self.donate_dialog.setStyleSheet("background-color: #2d2d2d; color: #ffffff;")
            else:
                self.donate_dialog.setStyleSheet("background-color: #f5f5f5; color: #333333;")
            
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            
            self.donate_tab = DonateTab(self.donate_dialog)  # Store donate_tab as a property
            layout.addWidget(self.donate_tab)
            
            self.donate_dialog.setLayout(layout)
            
            # Register language_changed signal for DonateTab
            self.language_changed.connect(lambda: self.donate_tab.update_language())
            
            # Apply theme to dialog - use current app theme
            self.donate_tab.apply_theme_colors(self.current_theme)
        else:
            # Update title and content based on current language
            self.donate_dialog.setWindowTitle(self.tr_("DONATE_TITLE"))
            
            # Update dialog style based on current theme
            if self.current_theme == "dark":
                self.donate_dialog.setStyleSheet("background-color: #2d2d2d; color: #ffffff;")
            else:
                self.donate_dialog.setStyleSheet("background-color: #f5f5f5; color: #333333;")
            
            # Update stored donate_tab
            if hasattr(self, 'donate_tab'):
                self.donate_tab.update_language()
                self.donate_tab.apply_theme_colors(self.current_theme)
        
        # Display dialog
        self.donate_dialog.exec()

    def check_ffmpeg_availability(self):
        """Check if FFmpeg is installed at startup and inform the user if it is not."""
        ffmpeg_installed, error_message = TikTokDownloader.check_ffmpeg_installed()
        
        if not ffmpeg_installed:
            # Show a message in the status bar
            self.status_bar.showMessage(self.tr_("STATUS_FFMPEG_MISSING"), 5000)
            
            # Show a warning dialog (after a slight delay to not block startup)
            QTimer.singleShot(1000, lambda: QMessageBox.warning(
                self,
                self.tr_("DIALOG_WARNING"),
                f"{self.tr_('DIALOG_FFMPEG_MISSING')}\n\n"
                f"{self.tr_('DIALOG_MP3_UNAVAILABLE')}\n\n"
                f"▶ {self.tr_('DIALOG_SEE_README')} (README.md)"
            ))
            
            # Store FFmpeg availability status
            self.ffmpeg_available = False
        else:
            self.ffmpeg_available = True

    def load_config(self):
        """Load configuration from config.json file"""
        try:
            # Get application base directory (where the exe is)
            if getattr(sys, 'frozen', False):
                # If we're running as a PyInstaller bundle
                app_dir = os.path.dirname(sys.executable)
            else:
                # If we're running in a normal Python environment
                app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            config_file = os.path.join(app_dir, 'config.json')
            log_file = os.path.join(app_dir, 'log.txt')
            
            with open(log_file, 'a', encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] Loading config from: {config_file}\n")
                log.write(f"[{datetime.now()}] App directory: {app_dir}\n")
                log.write(f"[{datetime.now()}] Executable path: {sys.executable if getattr(sys, 'frozen', False) else 'Not running as exe'}\n")
                
                if os.path.exists(config_file):
                    log.write(f"[{datetime.now()}] Config file exists, reading content\n")
                    try:
                        with open(config_file, 'r') as f:
                            config_content = f.read()
                            log.write(f"[{datetime.now()}] Config content: {config_content}\n")
                            
                            if config_content.strip():  # Check if not empty
                                config = json.loads(config_content)
                                
                                # Load output folder if available
                                last_folder = config.get('last_output_folder', '')
                                log.write(f"[{datetime.now()}] Read last_output_folder from config: '{last_folder}'\n")
                                
                                if last_folder and os.path.exists(last_folder):
                                    log.write(f"[{datetime.now()}] Setting output_folder to: {last_folder}\n")
                                    self.output_folder = last_folder
                                    if hasattr(self, 'video_info_tab'):
                                        self.video_info_tab.update_output_folder(last_folder)
                                else:
                                    log.write(f"[{datetime.now()}] Output folder doesn't exist or is empty: '{last_folder}'\n")
                                
                                # Load language setting
                                language = config.get('language', '')
                                if language:
                                    log.write(f"[{datetime.now()}] Setting language to: {language}\n")
                                    self.lang_manager.set_language(language)
                                    # No need to emit signal here because it's during initialization
                                    # Update tab names and menu after language is set
                                    self.tab_widget.setTabText(0, self.tr_("TAB_VIDEO_INFO"))
                                    self.tab_widget.setTabText(1, self.tr_("TAB_DOWNLOADED_VIDEOS"))
                                    self.update_ui_language()
                                
                                # Load theme setting
                                theme = config.get('theme', '')
                                if theme in ['dark', 'light']:
                                    log.write(f"[{datetime.now()}] Setting theme to: {theme}\n")
                                    self.current_theme = theme
                                    # Không áp dụng theme ở đây nữa, sẽ được áp dụng sau khi load_config() 
                                    # để đảm bảo stylesheet được áp dụng đầy đủ
                                    # self.set_theme(theme)  # <-- Bỏ dòng này
                            else:
                                log.write(f"[{datetime.now()}] Config file is empty\n")
                    except Exception as e:
                        log.write(f"[{datetime.now()}] Error parsing config file: {str(e)}\n")
                else:
                    log.write(f"[{datetime.now()}] Config file doesn't exist\n")
                    
                    # Try to create the config file with empty content
                    try:
                        with open(config_file, 'w') as f:
                            f.write("{}")
                        log.write(f"[{datetime.now()}] Created empty config file\n")
                    except Exception as e:
                        log.write(f"[{datetime.now()}] Error creating empty config file: {str(e)}\n")
        except Exception as e:
            # Write to log file
            try:
                log_file = get_resource_path('log.txt')
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"[{datetime.now()}] Error loading configuration: {str(e)}\n")
            except:
                pass
            print(f"Error loading configuration: {e}")

    def save_config(self, key, value):
        """Save configuration to config.json file"""
        try:
            # Get application base directory (where the exe is)
            if getattr(sys, 'frozen', False):
                # If we're running as a PyInstaller bundle
                app_dir = os.path.dirname(sys.executable)
            else:
                # If we're running in a normal Python environment
                app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            config_file = os.path.join(app_dir, 'config.json')
            log_file = os.path.join(app_dir, 'log.txt')
            
            with open(log_file, 'a', encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] Saving config to: {config_file}\n")
                log.write(f"[{datetime.now()}] App directory: {app_dir}\n")
                log.write(f"[{datetime.now()}] Key: {key}, Value: {value}\n")
            
                # Create or load existing config
                config = {}
                if os.path.exists(config_file):
                    log.write(f"[{datetime.now()}] Config file exists, reading existing content\n")
                    try:
                        with open(config_file, 'r') as f:
                            content = f.read().strip()
                            if content:  # Only try to parse if not empty
                                config = json.loads(content)
                                log.write(f"[{datetime.now()}] Existing config: {config}\n")
                            else:
                                log.write(f"[{datetime.now()}] Config file exists but is empty\n")
                    except Exception as e:
                        log.write(f"[{datetime.now()}] Error reading existing config: {str(e)}\n")
                else:
                    log.write(f"[{datetime.now()}] Config file doesn't exist, will create new\n")
                
                # Update config
                config[key] = value
                log.write(f"[{datetime.now()}] Updated config: {config}\n")
                
                # Save config
                try:
                    with open(config_file, 'w') as f:
                        json.dump(config, f)
                    log.write(f"[{datetime.now()}] Successfully saved config\n")
                    
                    # Verify config was written correctly
                    with open(config_file, 'r') as f:
                        content = f.read()
                        log.write(f"[{datetime.now()}] Verification - Config content after save: {content}\n")
                except Exception as e:
                    log.write(f"[{datetime.now()}] Error saving config: {str(e)}\n")
                    # Try to check if file is write-protected
                    if os.path.exists(config_file):
                        try:
                            import stat
                            file_stats = os.stat(config_file)
                            is_readonly = not (file_stats.st_mode & stat.S_IWRITE)
                            log.write(f"[{datetime.now()}] Config file read-only status: {is_readonly}\n")
                        except Exception as stat_error:
                            log.write(f"[{datetime.now()}] Error checking file permissions: {str(stat_error)}\n")
        except Exception as e:
            # Write to log file
            try:
                log_file = get_resource_path('log.txt')
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"[{datetime.now()}] Error in save_config: {str(e)}\n")
            except:
                pass
            print(f"Error saving configuration: {e}") 

    def setup_tabs(self):
        """Set up tabs in the main window"""
        # Create tabs container
        self.tabs = QTabWidget()
        self.tabs.setObjectName("tabs")
        
        # Create tabs
        self.video_info_tab = VideoInfoTab(self)
        self.downloaded_videos_tab = DownloadedVideosTab(self)
        
        # Add custom method to handle tab changes and ensure no sort indicators
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # Add tabs to container
        self.tabs.addTab(self.video_info_tab, self.tr_("TAB_VIDEO_INFO"))
        self.tabs.addTab(self.downloaded_videos_tab, self.tr_("TAB_DOWNLOADS"))
        
        # Set tab layout properties
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(True)
        
        # Set tabs as central widget
        self.setCentralWidget(self.tabs)
    
    # Thêm phương thức mới để xử lý khi chuyển tab
    def on_tab_changed(self, tab_index):
        """Handle tab change event"""
        # Ensure no sort indicators are shown in any tables
        if tab_index == 0:  # Video Info tab
            if hasattr(self.video_info_tab, 'video_table'):
                self.video_info_tab.video_table.horizontalHeader().setSortIndicatorShown(False)
                self.video_info_tab.video_table.setSortingEnabled(False)
        elif tab_index == 1:  # Downloaded Videos tab
            if hasattr(self.downloaded_videos_tab, 'downloads_table'):
                self.downloaded_videos_tab.downloads_table.horizontalHeader().setSortIndicatorShown(False)
                self.downloaded_videos_tab.downloads_table.setSortingEnabled(False)