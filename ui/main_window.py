from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QComboBox,
                             QFileDialog, QCheckBox, QHeaderView, QMessageBox,
                             QStatusBar, QMenu, QProgressBar, QDialog)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QActionGroup, QFont, QFontDatabase, QKeySequence
from PyQt6.QtWidgets import QApplication

from ui.video_info_tab import VideoInfoTab
from ui.downloaded_videos_tab import DownloadedVideosTab
from ui.donate_tab import DonateTab
from localization import get_language_manager


class MainWindow(QMainWindow):
    """Main window of the Social Download Manager application"""
    
    # Signal emitted when language is changed
    language_changed = pyqtSignal(str)

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
        
        # Set dark mode as default
        self.set_theme("dark")
        
        # Update UI based on current language
        self.update_ui_language()

    def setup_font(self):
        """Set up Inter font for the application"""
        # Create normal Inter font (not bold)
        font = QFont("Inter", 10, QFont.Weight.Normal)
        QApplication.setFont(font)

    def init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Social Download Manager")
        self.setGeometry(100, 100, 1000, 700)  # Adjust window size to be larger
        self.setWindowIcon(QIcon("assets/logo.png"))
        
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
        tiktok_icon = QIcon(f"assets/platforms/tiktok{icon_suffix}.png")
        tiktok_action = QAction(tiktok_icon, self.tr_("PLATFORM_TIKTOK"), self)
        tiktok_action.setCheckable(True)
        tiktok_action.setChecked(True)  # Default is TikTok
        platform_menu.addAction(tiktok_action)
        
        platform_menu.addSeparator()
        
        # Action: YouTube
        youtube_icon = QIcon(f"assets/platforms/youtube{icon_suffix}.png")
        youtube_action = QAction(youtube_icon, self.tr_("PLATFORM_YOUTUBE"), self)
        youtube_action.triggered.connect(self.show_developing_feature)
        platform_menu.addAction(youtube_action)
        
        # Action: Instagram
        instagram_icon = QIcon(f"assets/platforms/instagram{icon_suffix}.png")
        instagram_action = QAction(instagram_icon, self.tr_("PLATFORM_INSTAGRAM"), self)
        instagram_action.triggered.connect(self.show_developing_feature)
        platform_menu.addAction(instagram_action)
        
        # Action: Facebook
        facebook_icon = QIcon(f"assets/platforms/facebook{icon_suffix}.png")
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
        dark_mode_action.setChecked(True)  # Default is dark mode
        dark_mode_action.triggered.connect(lambda: self.set_theme("dark"))
        theme_menu.addAction(dark_mode_action)
        
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
        check_updates_action.triggered.connect(self.show_developing_feature)
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
        """Open dialog to choose output folder"""
        # Use current folder as starting point if available
        start_folder = self.output_folder if self.output_folder else ""
        
        folder = QFileDialog.getExistingDirectory(
            self, self.tr_("MENU_CHOOSE_FOLDER"), start_folder)
        if folder:
            self.output_folder = folder
            self.video_info_tab.update_output_folder(folder)
            self.status_bar.showMessage(self.tr_("STATUS_FOLDER_SET").format(folder))

    def set_language(self, lang_code):
        """Change application language"""
        if self.lang_manager.set_language(lang_code):
            # Update UI with new language
            self.update_ui_language()
            
            # Emit signal for other components to update
            self.language_changed.emit(lang_code)
            
            # Display notification
            language_name = self.lang_manager.get_current_language_name()
            self.status_bar.showMessage(self.tr_("STATUS_LANGUAGE_CHANGED").format(language_name))

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

    def show_developing_feature(self):
        """Display notification for features under development"""
        QMessageBox.information(
            self, self.tr_("DIALOG_COMING_SOON"), self.tr_("DIALOG_FEATURE_DEVELOPING"))

    def show_about(self):
        """Display information about the application"""
        QMessageBox.about(
            self, 
            self.tr_("ABOUT_TITLE"),
            f"{self.tr_('ABOUT_MESSAGE')}\n\nDeveloped by: Shin\nEmail: shin315@gmail.com"
        )
        
    def set_theme(self, theme):
        """Switch between Light and Dark mode"""
        app = QApplication.instance()
        self.current_theme = theme
        
        if theme == "dark":
            # Apply Dark mode stylesheet
            app.setStyleSheet("""
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
            
            # Update icons to white outline version for better visibility
            self.update_platform_icons("-outlined")
        else:
            # Apply Light mode stylesheet with better contrast colors
            app.setStyleSheet("""
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
                    color: white;
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

    def update_platform_icons(self, suffix):
        """Update icons for platform menus based on theme"""
        if not hasattr(self, 'platform_actions'):
            return
            
        for platform, action in self.platform_actions.items():
            icon_path = f"assets/platforms/{platform}{suffix}.png"
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