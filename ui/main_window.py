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
    """Cửa sổ chính của ứng dụng SoDownloader"""
    
    # Tín hiệu khi ngôn ngữ thay đổi
    language_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.output_folder = ""
        self.current_theme = "dark"  # Lưu theme hiện tại
        
        # Khởi tạo quản lý ngôn ngữ
        self.lang_manager = get_language_manager()
        
        # Lưu trữ các action platform để cập nhật icon dựa vào theme
        self.platform_actions = {}
        
        self.setup_font()
        self.init_ui()
        
        # Thiết lập chế độ tối mặc định
        self.set_theme("dark")
        
        # Cập nhật giao diện theo ngôn ngữ hiện tại
        self.update_ui_language()

    def setup_font(self):
        """Thiết lập font Inter cho ứng dụng"""
        # Tạo font Inter thường (không đậm)
        font = QFont("Inter", 10, QFont.Weight.Normal)
        QApplication.setFont(font)

    def init_ui(self):
        """Khởi tạo giao diện người dùng"""
        self.setWindowTitle("SoDownloader")
        self.setGeometry(100, 100, 1000, 700)  # Điều chỉnh kích thước cửa sổ lớn hơn
        self.setWindowIcon(QIcon("assets/logo.png"))
        
        # Thiết lập layout chính
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Tạo menu bar
        self.create_menu_bar()

        # Tạo tab widget và các tab
        self.tab_widget = QTabWidget()
        
        # Tab Video Info
        self.video_info_tab = VideoInfoTab(self)
        self.tab_widget.addTab(self.video_info_tab, self.tr_("TAB_VIDEO_INFO"))

        # Tab Downloaded Videos
        self.downloaded_videos_tab = DownloadedVideosTab(self)
        self.tab_widget.addTab(self.downloaded_videos_tab, self.tr_("TAB_DOWNLOADED_VIDEOS"))

        # Đặt tab widget làm widget trung tâm
        main_layout.addWidget(self.tab_widget)

        # Tạo status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(self.tr_("STATUS_READY"))
        
        # Khởi tạo donate dialog (không hiển thị)
        self.donate_dialog = None

    def create_menu_bar(self):
        """Tạo menu bar với các menu và action"""
        menu_bar = self.menuBar()

        # Menu File
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
        
        # Menu Platform (YouTube, Instagram, Facebook)
        platform_menu = menu_bar.addMenu(self.tr_("MENU_PLATFORM"))
        
        # Chọn icon suffix dựa vào theme hiện tại
        icon_suffix = "-outlined" if self.current_theme == "dark" else "-bw"
        
        # Action: TikTok (Hiện tại)
        tiktok_icon = QIcon(f"assets/platforms/tiktok{icon_suffix}.png")
        tiktok_action = QAction(tiktok_icon, self.tr_("PLATFORM_TIKTOK"), self)
        tiktok_action.setCheckable(True)
        tiktok_action.setChecked(True)  # Mặc định là đang ở TikTok
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
        
        # Lưu các action vào dictionary để update icon khi đổi theme
        self.platform_actions = {
            "tiktok": tiktok_action,
            "youtube": youtube_action,
            "instagram": instagram_action,
            "facebook": facebook_action
        }
        
        # Menu Theme (Dark/Light)
        theme_menu = menu_bar.addMenu(self.tr_("MENU_APPEARANCE"))
        
        # Tạo action group để chọn 1 trong các theme
        light_mode_action = QAction(self.tr_("MENU_LIGHT_MODE"), self)
        light_mode_action.setCheckable(True)
        light_mode_action.triggered.connect(lambda: self.set_theme("light"))
        theme_menu.addAction(light_mode_action)
        
        dark_mode_action = QAction(self.tr_("MENU_DARK_MODE"), self)
        dark_mode_action.setCheckable(True)
        dark_mode_action.setChecked(True)  # Mặc định là dark mode
        dark_mode_action.triggered.connect(lambda: self.set_theme("dark"))
        theme_menu.addAction(dark_mode_action)
        
        # Tạo action group để chỉ chọn một theme
        theme_group = QActionGroup(self)
        theme_group.addAction(light_mode_action)
        theme_group.addAction(dark_mode_action)
        theme_group.setExclusive(True)
        
        # Menu Language
        self.lang_menu = menu_bar.addMenu(self.tr_("MENU_LANGUAGE"))
        self.create_language_menu()
        
        # Menu Help
        help_menu = menu_bar.addMenu(self.tr_("MENU_HELP"))
        
        # Action: About
        about_action = QAction(self.tr_("MENU_ABOUT"), self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # Action: Check for Updates
        check_updates_action = QAction(self.tr_("MENU_CHECK_UPDATES"), self)
        check_updates_action.triggered.connect(self.show_developing_feature)
        help_menu.addAction(check_updates_action)
        
        # Thêm separator trước Buy Me A Coffee
        help_menu.addSeparator()
        
        # Action: Buy Me A Coffee (đặt trong menu Help thay vì là một menu riêng)
        donate_action = QAction(self.tr_("MENU_BUY_COFFEE"), self)
        donate_action.triggered.connect(self.show_donate_tab)
        help_menu.addAction(donate_action)

    def create_language_menu(self):
        """Tạo menu ngôn ngữ động từ các ngôn ngữ có sẵn"""
        # Xóa tất cả action hiện có trong menu
        self.lang_menu.clear()
        
        # Tạo action group để chỉ một ngôn ngữ được chọn
        lang_action_group = QActionGroup(self)
        lang_action_group.setExclusive(True)
        
        # Lấy danh sách ngôn ngữ từ LanguageManager
        available_languages = self.lang_manager.get_available_languages()
        current_language = self.lang_manager.current_language
        
        # Thêm từng ngôn ngữ vào menu
        for lang_code, lang_name in available_languages.items():
            lang_action = QAction(lang_name, self)
            lang_action.setCheckable(True)
            lang_action.setChecked(lang_code == current_language)
            lang_action.triggered.connect(lambda checked, code=lang_code: self.set_language(code))
            lang_action_group.addAction(lang_action)
            self.lang_menu.addAction(lang_action)

    def set_output_folder(self):
        """Mở hộp thoại chọn thư mục đầu ra"""
        # Sử dụng thư mục hiện tại làm điểm bắt đầu nếu có
        start_folder = self.output_folder if self.output_folder else ""
        
        folder = QFileDialog.getExistingDirectory(
            self, self.tr_("MENU_CHOOSE_FOLDER"), start_folder)
        if folder:
            self.output_folder = folder
            self.video_info_tab.update_output_folder(folder)
            self.status_bar.showMessage(self.tr_("STATUS_FOLDER_SET").format(folder))

    def set_language(self, lang_code):
        """Thay đổi ngôn ngữ của ứng dụng"""
        if self.lang_manager.set_language(lang_code):
            # Cập nhật giao diện với ngôn ngữ mới
            self.update_ui_language()
            
            # Phát tín hiệu để các component khác cập nhật
            self.language_changed.emit(lang_code)
            
            # Hiển thị thông báo
            language_name = self.lang_manager.get_current_language_name()
            self.status_bar.showMessage(self.tr_("STATUS_LANGUAGE_CHANGED").format(language_name))

    def update_ui_language(self):
        """Cập nhật giao diện với ngôn ngữ hiện tại"""
        # Cập nhật tiêu đề tab
        self.tab_widget.setTabText(0, self.tr_("TAB_VIDEO_INFO"))
        self.tab_widget.setTabText(1, self.tr_("TAB_DOWNLOADED_VIDEOS"))
        
        # Cập nhật menu
        self.menuBar().clear()
        self.create_menu_bar()
        
        # Cập nhật các component khác nếu cần
        self.video_info_tab.update_language()
        self.downloaded_videos_tab.update_language()
        
    def tr_(self, key):
        """Dịch chuỗi dựa trên ngôn ngữ hiện tại"""
        return self.lang_manager.get_text(key)

    def show_developing_feature(self):
        """Hiển thị thông báo tính năng đang phát triển"""
        QMessageBox.information(
            self, self.tr_("DIALOG_COMING_SOON"), self.tr_("DIALOG_FEATURE_DEVELOPING"))

    def show_about(self):
        """Hiển thị thông tin về ứng dụng"""
        QMessageBox.about(
            self, 
            self.tr_("ABOUT_TITLE"),
            f"{self.tr_('ABOUT_MESSAGE')}\n\nDeveloped by: Shin\nEmail: shin315@gmail.com"
        )
        
    def set_theme(self, theme):
        """Thay đổi giao diện giữa Light và Dark mode"""
        app = QApplication.instance()
        self.current_theme = theme
        
        if theme == "dark":
            # Áp dụng Dark mode stylesheet
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
                QHeaderView::section {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    padding: 5px;
                    border: 1px solid #444444;
                }
                QLineEdit, QComboBox {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 5px;
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
                QMenu {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #444444;
                }
                QMenu::item:selected {
                    background-color: #0078d7;
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
                /* Đồng bộ màu sắc cho các icon trong context menu */
                QMenu::icon {
                    color: #cccccc;
                }
                /* Màu sắc cho tất cả các action trong context menu */
                QMenu QAction {
                    color: #ffffff;
                }
                /* Màu sắc cho tất cả các icon khi chuột phải */
                QMenu::indicator:non-exclusive:checked {
                    image: url(:/qt-project.org/styles/commonstyle/images/checkbox-checked.png);
                    color: #cccccc;
                }
                /* Thiết lập màu chung cho tất cả các icon trong context menu */
                QMenu QIcon {
                    color: #cccccc;
                }
                /* Màu cho icon cut, copy, paste và các icon khác trong context menu */
                QLineEdit::contextmenu-item QMenu::icon,
                QLineEdit::contextmenu-item QAction::icon,
                QTextEdit::contextmenu-item QMenu::icon,
                QTextEdit::contextmenu-item QAction::icon,
                QPlainTextEdit::contextmenu-item QMenu::icon,
                QPlainTextEdit::contextmenu-item QAction::icon {
                    color: #cccccc;
                }
                /* Title bar (thanh tiêu đề) */
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
            """)
            self.status_bar.showMessage(self.tr_("STATUS_DARK_MODE_ENABLED"))
            
            # Cập nhật icon sang phiên bản viền trắng rõ ràng hơn
            self.update_platform_icons("-outlined")
        else:
            # Áp dụng Light mode stylesheet với màu sắc tương phản tốt hơn
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
                QHeaderView::section {
                    background-color: #e0e0e0;
                    color: #333333;
                    padding: 5px;
                    border: 1px solid #cccccc;
                }
                QLineEdit, QComboBox {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #cccccc;
                    padding: 5px;
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
                QMenu {
                    background-color: #f5f5f5;
                    color: #333333;
                    border: 1px solid #cccccc;
                }
                QMenu::item:selected {
                    background-color: #0078d7;
                    color: #ffffff;
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
                /* Đồng bộ màu sắc cho các icon trong context menu */
                QMenu::icon {
                    color: #555555;
                }
                /* Màu sắc cho tất cả các action trong context menu */
                QMenu QAction {
                    color: #333333;
                }
                /* Màu sắc cho tất cả các icon khi chuột phải */
                QMenu::indicator:non-exclusive:checked {
                    image: url(:/qt-project.org/styles/commonstyle/images/checkbox-checked.png);
                    color: #555555;
                }
                /* Thiết lập màu chung cho tất cả các icon trong context menu */
                QMenu QIcon {
                    color: #555555;
                }
                /* Title bar (thanh tiêu đề) */
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
            """)
            self.status_bar.showMessage(self.tr_("STATUS_LIGHT_MODE_ENABLED"))
            
            # Cập nhật icon sang phiên bản đen
            self.update_platform_icons("-bw")
            
        # Cập nhật màu sắc cho các tab con
        if hasattr(self, 'downloaded_videos_tab') and hasattr(self.downloaded_videos_tab, 'apply_theme_colors'):
            self.downloaded_videos_tab.apply_theme_colors(theme)
            
        if hasattr(self, 'video_info_tab') and hasattr(self.video_info_tab, 'apply_theme_colors'):
            self.video_info_tab.apply_theme_colors(theme)
            
        # Cập nhật theme cho donate dialog nếu đã được tạo
        if hasattr(self, 'donate_dialog') and self.donate_dialog:
            # Cập nhật style cho dialog
            if theme == "dark":
                self.donate_dialog.setStyleSheet("background-color: #2d2d2d; color: #ffffff;")
            else:
                self.donate_dialog.setStyleSheet("background-color: #f5f5f5; color: #333333;")
            
            # Cập nhật donate_tab nếu tồn tại
            if hasattr(self, 'donate_tab'):
                self.donate_tab.apply_theme_colors(theme)

    def update_platform_icons(self, suffix):
        """Cập nhật icon cho các menu platform theo theme"""
        if not hasattr(self, 'platform_actions'):
            return
            
        for platform, action in self.platform_actions.items():
            icon_path = f"assets/platforms/{platform}{suffix}.png"
            action.setIcon(QIcon(icon_path))

    def show_donate_tab(self):
        """Hiển thị dialog donate"""
        # Tạo dialog nếu chưa có
        if not self.donate_dialog:
            self.donate_dialog = QDialog(self)
            self.donate_dialog.setObjectName("donateDialog")  # Thêm objectName cho dialog
            self.donate_dialog.setWindowTitle(self.tr_("DONATE_TITLE"))
            self.donate_dialog.setMinimumSize(320, 340)  # Giảm chiều cao từ 400 xuống 340
            self.donate_dialog.setMaximumSize(330, 350)  # Giảm chiều cao từ 420 xuống 350
            self.donate_dialog.setWindowFlags(self.donate_dialog.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
            self.donate_dialog.setModal(True)
            
            # Đặt style trực tiếp dựa trên theme hiện tại
            if self.current_theme == "dark":
                self.donate_dialog.setStyleSheet("background-color: #2d2d2d; color: #ffffff;")
            else:
                self.donate_dialog.setStyleSheet("background-color: #f5f5f5; color: #333333;")
            
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            
            self.donate_tab = DonateTab(self.donate_dialog)  # Lưu donate_tab như một thuộc tính
            layout.addWidget(self.donate_tab)
            
            self.donate_dialog.setLayout(layout)
            
            # Đăng ký tín hiệu language_changed cho DonateTab
            self.language_changed.connect(lambda: self.donate_tab.update_language())
            
            # Áp dụng theme cho dialog - sử dụng theme hiện tại của app
            self.donate_tab.apply_theme_colors(self.current_theme)
        else:
            # Cập nhật title và nội dung theo ngôn ngữ hiện tại
            self.donate_dialog.setWindowTitle(self.tr_("DONATE_TITLE"))
            
            # Cập nhật style của dialog dựa trên theme hiện tại
            if self.current_theme == "dark":
                self.donate_dialog.setStyleSheet("background-color: #2d2d2d; color: #ffffff;")
            else:
                self.donate_dialog.setStyleSheet("background-color: #f5f5f5; color: #333333;")
            
            # Cập nhật donate_tab đã lưu
            if hasattr(self, 'donate_tab'):
                self.donate_tab.update_language()
                self.donate_tab.apply_theme_colors(self.current_theme)
        
        # Hiển thị dialog
        self.donate_dialog.exec() 