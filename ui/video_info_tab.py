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

# Path to configuration file
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')

class VideoInfoTab(QWidget):
    """Tab for displaying video information and downloading videos"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.lang_manager = get_language_manager()
        
        # Initialize TikTokDownloader
        self.downloader = TikTokDownloader()
        
        # Initialize video information storage
        self.video_info_dict = {}  # Dictionary with URL as key, VideoInfo as value
        
        # Counter for videos being processed
        self.processing_count = 0
        
        # Counter for videos being downloaded
        self.downloading_count = 0
        
        self.init_ui()
        self.load_last_output_folder()
        
        # Connect downloader signals
        self.connect_downloader_signals()
        
        # Connect to language change signal from MainWindow
        if parent and hasattr(parent, 'language_changed'):
            parent.language_changed.connect(self.update_language)
            
        # Apply default color style based on dark mode (may be overridden later)
        self.apply_theme_colors("dark")

    def init_ui(self):
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
        # No fixed width - allow resizing with window
        self.url_input.setMinimumWidth(500)
        self.url_input.setPlaceholderText(self.tr_("PLACEHOLDER_VIDEO_URL"))
        # Connect returnPressed event to get_video_info function
        self.url_input.returnPressed.connect(self.get_video_info)
        url_layout.addWidget(self.url_input, 1)  # stretch factor 1 to expand when window is resized
        
        # Get Info button
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
        
        # Hiển thị đường dẫn thư mục
        self.output_folder_display = QLineEdit()
        self.output_folder_display.setReadOnly(True)
        self.output_folder_display.setFixedHeight(30)
        # Không đặt chiều rộng cố định nữa - cho phép kéo giãn theo cửa sổ
        self.output_folder_display.setMinimumWidth(500)
        self.output_folder_display.setPlaceholderText(self.tr_("PLACEHOLDER_OUTPUT_FOLDER"))
        output_layout.addWidget(self.output_folder_display, 1)  # stretch factor 1 để mở rộng khi phóng to
        
        # Nút chọn thư mục
        self.choose_folder_btn = QPushButton(self.tr_("BUTTON_CHOOSE_FOLDER"))
        self.choose_folder_btn.setFixedWidth(120)  # Cố định chiều rộng giống nút Get Info
        self.choose_folder_btn.clicked.connect(self.choose_output_folder)
        output_layout.addWidget(self.choose_folder_btn)
        
        main_layout.addLayout(output_layout)

        # Bảng thông tin video
        self.create_video_table()
        main_layout.addWidget(self.video_table)

        # Phần tùy chọn và nút Download
        options_layout = QHBoxLayout()
        
        # Nhóm các nút Select/Delete sang bên trái
        left_buttons_layout = QHBoxLayout()
        
        # Nút Chọn tất cả / Bỏ chọn tất cả (gộp 2 nút thành 1)
        self.select_toggle_btn = QPushButton(self.tr_("BUTTON_SELECT_ALL"))
        self.select_toggle_btn.setFixedWidth(150)
        self.select_toggle_btn.clicked.connect(self.toggle_select_all)
        self.all_selected = False  # Trạng thái hiện tại (False: chưa chọn tất cả)
        left_buttons_layout.addWidget(self.select_toggle_btn)
        
        # Nút Delete Selected
        self.delete_selected_btn = QPushButton(self.tr_("BUTTON_DELETE_SELECTED"))
        self.delete_selected_btn.setFixedWidth(150)
        self.delete_selected_btn.clicked.connect(self.delete_selected_videos)
        left_buttons_layout.addWidget(self.delete_selected_btn)
        
        # Nút Delete All
        self.delete_all_btn = QPushButton(self.tr_("BUTTON_DELETE_ALL"))
        self.delete_all_btn.setFixedWidth(150)
        self.delete_all_btn.clicked.connect(self.delete_all_videos)
        left_buttons_layout.addWidget(self.delete_all_btn)
        
        # Thêm nhóm nút bên trái vào layout
        options_layout.addLayout(left_buttons_layout)
        
        # Thêm stretch để đẩy nút Download sang bên phải hoàn toàn
        options_layout.addStretch(1)
        
        # Nút Download ở bên phải
        self.download_btn = QPushButton(self.tr_("BUTTON_DOWNLOAD"))
        self.download_btn.setFixedWidth(150)
        self.download_btn.clicked.connect(self.download_videos)
        options_layout.addWidget(self.download_btn)

        main_layout.addLayout(options_layout)
        
        # Thiết lập context menu cho video_table
        self.video_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.video_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Cập nhật trạng thái các nút ban đầu
        self.update_button_states()

    def show_context_menu(self, position):
        """Hiển thị menu chuột phải cho bảng video"""
        # Lấy vị trí dòng và cột hiện tại
        index = self.video_table.indexAt(position)
        if not index.isValid():
            return
            
        row = index.row()
        column = index.column()
        
        if row < 0 or row >= self.video_table.rowCount():
            return
        
        # Tạo context menu
        context_menu = QMenu(self)
        
        # Xác định loại dữ liệu dựa vào cột
        if column == 1:  # Title
            # Lấy title từ item
            item = self.video_table.item(row, column)
            if item and item.text():
                # Lấy full title từ video_info_dict nếu có
                full_title = item.text()  # Default là text hiển thị
                if row in self.video_info_dict:
                    video_info = self.video_info_dict[row]
                    # Ưu tiên caption nếu có vì nó thường chứa nội dung đầy đủ nhất
                    if hasattr(video_info, 'caption') and video_info.caption:
                        full_title = video_info.caption
                    # Nếu không có caption, thử dùng original_title
                    elif hasattr(video_info, 'original_title') and video_info.original_title:
                        full_title = video_info.original_title
                    # Nếu không, dùng title
                    elif hasattr(video_info, 'title'):
                        full_title = video_info.title
                
                # Thêm action Copy
                copy_action = QAction(self.tr_("CONTEXT_COPY_TITLE"), self)
                copy_action.triggered.connect(lambda: self.copy_to_clipboard(full_title, "title"))
                context_menu.addAction(copy_action)
        
        elif column == 2:  # Creator
            # Lấy creator từ item
            item = self.video_table.item(row, column)
            if item and item.text():
                # Thêm action Copy
                copy_action = QAction(self.tr_("CONTEXT_COPY_CREATOR"), self)
                copy_action.triggered.connect(lambda: self.copy_to_clipboard(item.text(), "creator"))
                context_menu.addAction(copy_action)
        
        elif column == 7:  # Hashtags
            # Lấy hashtags từ item
            item = self.video_table.item(row, column)
            if item and item.text():
                # Thêm action Copy
                copy_action = QAction(self.tr_("CONTEXT_COPY_HASHTAGS"), self)
                copy_action.triggered.connect(lambda: self.copy_to_clipboard(item.text(), "hashtags"))
                context_menu.addAction(copy_action)
                
        # Chức năng chung cho tất cả các cột
        # Thêm separtor nếu có action trước đó
        if not context_menu.isEmpty():
            context_menu.addSeparator()
        
        # Lấy thông tin video
        video_info = None
        if row in self.video_info_dict:
            video_info = self.video_info_dict[row]
        
        if video_info:
            # Kiểm tra xem đã chọn thư mục đầu ra chưa
            has_output_folder = bool(self.output_folder_display.text())
            
            # Đảm bảo thuộc tính title tồn tại
            if not hasattr(video_info, 'title') or video_info.title is None or video_info.title.strip() == "":
                from datetime import datetime
                default_title = f"Video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                setattr(video_info, 'title', default_title)
                print(f"DEBUG - Created default title for video without title: {default_title}")
            
            # Kiểm tra video có lỗi không
            has_error = False
            if hasattr(video_info, 'title'):
                has_error = video_info.title.startswith("Error:")
            
            # Chỉ hiển thị Rename nếu video không có lỗi và đã chọn thư mục đầu ra
            # Bỏ điều kiện hasattr(video_info, 'title') để cho phép rename cả video không có tiêu đề
            if not has_error and has_output_folder and hasattr(video_info, 'url'):
                # Action Rename Video - Cho phép đổi tên video trước khi tải
                rename_action = QAction(self.tr_("CONTEXT_RENAME_VIDEO"), self)
                rename_action.triggered.connect(lambda: self.rename_video(row))
                context_menu.addAction(rename_action)
                
                # Thêm separator
                context_menu.addSeparator()
        
        # Action Delete Video - có trong mọi trường hợp
        delete_action = QAction(self.tr_("CONTEXT_DELETE"), self)
        delete_action.triggered.connect(lambda: self.delete_row(row))
        context_menu.addAction(delete_action)
        
        # Hiển thị menu nếu có action
        if not context_menu.isEmpty():
            context_menu.exec(QCursor.pos())

    def rename_video(self, row):
        """Cho phép người dùng đổi tên video trước khi tải xuống"""
        # Kiểm tra video_info có tồn tại
        if row not in self.video_info_dict:
            return
            
        video_info = self.video_info_dict[row]
        
        # Lấy tiêu đề hiện tại
        current_title = video_info.title if hasattr(video_info, 'title') else ""
        
        # Nếu không có tiêu đề, tạo tiêu đề mặc định từ timestamp
        if not current_title:
            from datetime import datetime
            current_title = f"Video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"DEBUG - Creating default title for empty video title: {current_title}")
            
        # Hiển thị dialog để nhập tên mới
        new_title, ok = QInputDialog.getText(
            self, 
            self.tr_("DIALOG_RENAME_TITLE"),
            self.tr_("DIALOG_ENTER_NEW_NAME"), 
            QLineEdit.EchoMode.Normal, 
            current_title
        )
        
        # Kiểm tra người dùng đã nhấn OK và tên mới khác rỗng
        if ok and new_title:
            # Làm sạch tên file để tránh ký tự không hợp lệ
            import re
            clean_title = re.sub(r'[\\/*?:"<>|]', '', new_title).strip()
            
            if clean_title:
                # Lưu tên gốc vào biến original_title nếu chưa có
                if not hasattr(video_info, 'original_title'):
                    setattr(video_info, 'original_title', current_title)
                    
                # Cập nhật tên mới
                setattr(video_info, 'title', clean_title)
                
                # Thêm thuộc tính custom_title
                setattr(video_info, 'custom_title', clean_title)
                
                # Cập nhật UI - cột title trong bảng
                title_cell = self.video_table.item(row, 1)
                if title_cell:
                    title_cell.setText(clean_title)
                    title_cell.setToolTip(clean_title)
                
                # Hiển thị thông báo thành công
                if self.parent and self.parent.status_bar:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_RENAMED_VIDEO").format(clean_title))
                    
                print(f"DEBUG - Renamed video from '{current_title}' to '{clean_title}'")
            else:
                # Hiển thị thông báo lỗi nếu tên mới không hợp lệ
                QMessageBox.warning(
                    self, 
                    self.tr_("DIALOG_ERROR"), 
                    self.tr_("DIALOG_INVALID_NAME")
                )

    def create_video_table(self):
        """Tạo bảng hiển thị thông tin video"""
        self.video_table = QTableWidget()
        self.video_table.setColumnCount(8)  # Giảm từ 9 xuống 8 do bỏ cột Caption
        
        # Thiết lập header
        self.update_table_headers()
        
        # Thiết lập thuộc tính bảng
        self.video_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Thiết lập kích thước cột tùy chỉnh
        self.video_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Select - cột checkbox
        self.video_table.setColumnWidth(0, 50)
        
        self.video_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title - co giãn
        
        self.video_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Creator
        self.video_table.setColumnWidth(2, 100)
        
        self.video_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Quality
        self.video_table.setColumnWidth(3, 80)
        
        self.video_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Format
        self.video_table.setColumnWidth(4, 100)
        
        self.video_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Duration
        self.video_table.setColumnWidth(5, 90)
        
        self.video_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Size
        self.video_table.setColumnWidth(6, 80)
        
        # Bỏ cột Caption (index 7)
        
        self.video_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Hashtags 
        self.video_table.setColumnWidth(7, 180)
        
        # Thiết lập số dòng ban đầu
        self.video_table.setRowCount(0)
        
        # Kết nối sự kiện double-click để hiển thị dialog copy text
        self.video_table.itemDoubleClicked.connect(self.show_copy_dialog)
        
        # Thiết lập sự kiện hover để hiển thị tooltip với text đầy đủ
        self.video_table.setMouseTracking(True)
        self.video_table.cellEntered.connect(self.show_full_text_tooltip)
        
        # Thiết lập style của bảng với hiệu ứng hover
        self.video_table.setStyleSheet("""
            QTableWidget::item:hover {
                background-color: rgba(0, 120, 215, 0.1);
            }
        """)

    def update_output_folder(self, folder):
        """Cập nhật đường dẫn thư mục đầu ra"""
        self.output_folder_display.setText(folder)
        # Lưu đường dẫn mới vào cấu hình
        self.save_last_output_folder(folder)
        
        # Cập nhật thư mục đầu ra cho downloader
        self.downloader.set_output_dir(folder)

    def choose_output_folder(self):
        """Chọn thư mục đầu ra"""
        # Lấy thư mục hiện tại để bắt đầu từ đó nếu có
        start_folder = self.output_folder_display.text() if self.output_folder_display.text() else ""
        
        folder = QFileDialog.getExistingDirectory(
            self, self.tr_("MENU_CHOOSE_FOLDER"), start_folder)
        if folder:
            self.update_output_folder(folder)
            if self.parent:
                self.parent.output_folder = folder
                self.parent.status_bar.showMessage(self.tr_("STATUS_FOLDER_SET").format(folder))

    def load_last_output_folder(self):
        """Tải đường dẫn thư mục đầu ra cuối cùng từ file cấu hình"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    last_folder = config.get('last_output_folder', '')
                    if last_folder and os.path.exists(last_folder):
                        self.update_output_folder(last_folder)
                        if self.parent:
                            self.parent.output_folder = last_folder
        except Exception as e:
            print(f"Error loading last output folder: {e}")

    def save_last_output_folder(self, folder):
        """Lưu đường dẫn thư mục đầu ra cuối cùng vào file cấu hình"""
        try:
            # Tạo file config nếu chưa tồn tại
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            
            # Cập nhật thư mục đầu ra
            config['last_output_folder'] = folder
            
            # Lưu cấu hình
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving last output folder: {e}")

    def get_video_info(self):
        """Lấy thông tin video từ URL"""
        url_input = self.url_input.text().strip()
        if not url_input:
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("DIALOG_NO_VIDEOS"))
            return

        # Kiểm tra xem đã thiết lập thư mục đầu ra chưa
        if not self.output_folder_display.text():
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("DIALOG_NO_OUTPUT_FOLDER"))
            return
        
        # Xử lý nhiều URL (ngăn cách bằng khoảng trắng)
        new_urls = url_input.split()
        
        # Tạo danh sách URL hiện có trong bảng
        existing_urls = []
        for video_info in self.video_info_dict.values():
            existing_urls.append(video_info.url)
        
        # Lọc ra các URL mới chưa tồn tại trong bảng
        urls_to_process = []
        for url in new_urls:
            if url not in existing_urls:
                urls_to_process.append(url)
            else:
                # Thông báo URL đã tồn tại
                print(f"URL already exists in table: {url}")
        
        # Nếu không có URL mới nào cần xử lý
        if not urls_to_process:
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_NO_NEW_URLS"))
            return
            
        # Đặt lại biến đếm
        self.processing_count = len(urls_to_process)
        
        # Disable button Get Info khi đang lấy thông tin
        self.get_info_btn.setEnabled(False)
        self.get_info_btn.setText(self.tr_("STATUS_GETTING_INFO_SHORT"))
        self.url_input.setEnabled(False)
        
        # Cập nhật trạng thái
        if self.parent:
            # Hiển thị thông báo rõ ràng trên status bar
            if len(urls_to_process) > 1:
                self.parent.status_bar.showMessage(self.tr_("STATUS_GETTING_INFO_MULTIPLE").format(len(urls_to_process)))
            else:
                self.parent.status_bar.showMessage(self.tr_("STATUS_GETTING_INFO_SHORT"))
        
        # Yêu cầu cập nhật giao diện ngay lập tức để hiển thị thông báo
        QApplication.processEvents()
        
        # Bắt đầu lấy thông tin video từ TikTokDownloader cho các URL mới
        for url in urls_to_process:
            # Gọi phương thức get_video_info của TikTokDownloader
            # Kết quả sẽ được xử lý bởi on_video_info_received thông qua signal
            self.downloader.get_video_info(url)
            
            # Cập nhật lại giao diện sau mỗi request để đảm bảo UI vẫn responsive
            QApplication.processEvents()

    def delete_row(self, row):
        """Xóa một dòng khỏi bảng"""
        self.video_table.removeRow(row)
        # Cập nhật trạng thái các nút
        self.update_button_states()

    def delete_all_videos(self):
        """Xóa tất cả video khỏi bảng"""
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
            # Cập nhật trạng thái các nút
            self.update_button_states()

    def download_videos(self):
        """Tải xuống các video đã chọn"""
        if not self.check_output_folder():
            return
        
        # Tạo danh sách thông tin chi tiết để tải xuống
        download_queue = []
        videos_already_exist = []
        selected_count = 0
        
        # Đếm tổng số video được chọn trước
        for row in range(self.video_table.rowCount()):
            checkbox_cell = self.video_table.cellWidget(row, 0)
            if checkbox_cell:
                checkbox = checkbox_cell.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected_count += 1
        
        # Biến lưu lựa chọn của người dùng cho tất cả file đã tồn tại
        overwrite_all = None  # None = chưa chọn, True = ghi đè tất cả, False = bỏ qua tất cả
        
        # Duyệt qua từng dòng trong bảng
        for row in range(self.video_table.rowCount()):
            checkbox_cell = self.video_table.cellWidget(row, 0)
            if checkbox_cell:
                checkbox = checkbox_cell.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    # Thu thập tất cả thông tin cần thiết
                    # Kiểm tra nếu row tồn tại trong video_info_dict
                    if row not in self.video_info_dict:
                        print(f"DEBUG - Error: Row {row} not found in video_info_dict, skipping this video")
                        continue
                        
                    # Lấy URL từ video_info_dict
                    url = self.video_info_dict[row].url
                    
                    # Lấy tiêu đề video để hiển thị trong thông báo
                    title = self.video_info_dict[row].title
                    
                    # Lấy chất lượng được chọn
                    quality_cell = self.video_table.cellWidget(row, 3)
                    quality = quality_cell.findChild(QComboBox).currentText() if quality_cell else "720p"
                    
                    # Lấy định dạng được chọn
                    format_cell = self.video_table.cellWidget(row, 4)
                    format_str = format_cell.findChild(QComboBox).currentText() if format_cell else self.tr_("FORMAT_VIDEO_MP4")
                    
                    # Lấy format_id dựa trên chất lượng và định dạng
                    format_id = self.get_format_id(url, quality, format_str)

                    # Xác định phần mở rộng file dựa trên định dạng
                    is_audio = format_str == self.tr_("FORMAT_AUDIO_MP3") or "audio" in format_id.lower() or "bestaudio" in format_id.lower()
                    ext = "mp3" if is_audio else "mp4"
                    
                    # Kiểm tra xem tiêu đề có rỗng không trước khi tiếp tục
                    if not title.strip() or title.strip().startswith('#'):
                        # Hiển thị dialog để nhập tên mới cho video
                        default_name = f"Video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        new_title, ok = QInputDialog.getText(
                            self, 
                            self.tr_("DIALOG_RENAME_TITLE"),
                            self.tr_("DIALOG_ENTER_NAME_REQUIRED"), 
                            QLineEdit.EchoMode.Normal, 
                            default_name
                        )
                        
                        if not ok or not new_title.strip():
                            # Người dùng hủy hoặc không nhập tên, bỏ qua video này
                            print(f"DEBUG - User cancelled entering required name for video without title")
                            continue
                        
                        # Làm sạch tên file để tránh ký tự không hợp lệ
                        import re
                        clean_title = re.sub(r'[\\/*?:"<>|]', '', new_title).strip()
                        
                        # Cập nhật title trong video_info_dict
                        if row in self.video_info_dict:
                            self.video_info_dict[row].custom_title = new_title
                            # Lưu title mới để hiển thị trong tab Downloaded Videos
                            self.video_info_dict[row].title = new_title
                            print(f"DEBUG - New title set for video without title: '{new_title}'")
                        
                        # Cập nhật title trong download_queue
                        title = new_title
                    else:
                        # Làm sạch tên video, loại bỏ hashtag để tạo tên file
                        clean_title = title
                        # Loại bỏ tất cả các hashtag còn sót nếu có
                        import re
                        clean_title = re.sub(r'#\S+', '', clean_title).strip()
                        # Loại bỏ các ký tự không hợp lệ cho tên file
                        clean_title = re.sub(r'[\\/*?:"<>|]', '', clean_title).strip()
                    
                    # Tạo đường dẫn file đầy đủ
                    output_dir = self.output_folder_display.text()
                    output_file = os.path.join(output_dir, f"{clean_title}.{ext}")

                    # Kiểm tra xem video đã tồn tại chưa
                    db_manager = DatabaseManager()
                    existing_video = db_manager.get_download_by_url(url)
                    
                    # Kiểm tra xem file đã tồn tại trên ổ đĩa chưa
                    file_exists = os.path.exists(output_file)
                    
                    if existing_video:
                        # Video đã tồn tại trong CSDL
                        videos_already_exist.append(title)
                    elif file_exists:
                        # File tồn tại trên ổ đĩa nhưng không có trong CSDL
                        
                        # Nếu người dùng đã chọn "Áp dụng cho tất cả", sử dụng lựa chọn đó
                        if overwrite_all is not None:
                            if overwrite_all:
                                # Người dùng đã chọn ghi đè tất cả
                                download_queue.append({
                                    'url': url,
                                    'title': title,
                                    'format_id': format_id,
                                    'clean_title': clean_title,
                                    'ext': ext
                                })
                            else:
                                # Người dùng đã chọn bỏ qua tất cả
                                continue
                        else:
                            # Hiển thị thông báo hỏi người dùng có muốn ghi đè không
                            # và thêm lựa chọn "Áp dụng cho tất cả" (chỉ khi có nhiều file)
                            
                            # Tạo message box tùy chỉnh
                            msg_box = QMessageBox(self)
                            msg_box.setWindowTitle(self.tr_("DIALOG_FILE_EXISTS"))
                            
                            # Thu thập danh sách các file đã tồn tại
                            file_name = f"{clean_title}.{ext}"
                            file_exists_list = [file_name]
                            remaining_files = 0
                            
                            # Nếu có nhiều file được chọn, thu thập danh sách các file đã tồn tại để hiển thị
                            if selected_count > 1:
                                # Duyệt qua các dòng khác để kiểm tra file đã tồn tại
                                for check_row in range(self.video_table.rowCount()):
                                    # Bỏ qua row hiện tại vì đã được thêm vào danh sách
                                    if check_row == row:
                                        continue
                                        
                                    check_checkbox_cell = self.video_table.cellWidget(check_row, 0)
                                    if check_checkbox_cell:
                                        check_checkbox = check_checkbox_cell.findChild(QCheckBox)
                                        if check_checkbox and check_checkbox.isChecked():
                                            # Chỉ kiểm tra nếu row tồn tại trong video_info_dict
                                            if check_row not in self.video_info_dict:
                                                continue
                                                
                                            # Lấy thông tin video
                                            check_title = self.video_info_dict[check_row].title
                                            
                                            # Lấy định dạng được chọn
                                            check_format_cell = self.video_table.cellWidget(check_row, 4)
                                            check_format_str = check_format_cell.findChild(QComboBox).currentText() if check_format_cell else self.tr_("FORMAT_VIDEO_MP4")
                                            
                                            # Xác định phần mở rộng file
                                            check_is_audio = check_format_str == self.tr_("FORMAT_AUDIO_MP3")
                                            check_ext = "mp3" if check_is_audio else "mp4"
                                            
                                            # Làm sạch tên file
                                            import re
                                            check_clean_title = re.sub(r'#\S+', '', check_title).strip()
                                            check_clean_title = re.sub(r'[\\/*?:"<>|]', '', check_clean_title).strip()
                                            
                                            # Tạo đường dẫn file đầy đủ
                                            check_output_file = os.path.join(output_dir, f"{check_clean_title}.{check_ext}")
                                            
                                            # Kiểm tra xem file đã tồn tại chưa
                                            if os.path.exists(check_output_file):
                                                # Nếu đã có 5 file trong danh sách, chỉ đếm số lượng
                                                if len(file_exists_list) < 5:
                                                    file_exists_list.append(f"{check_clean_title}.{check_ext}")
                                                else:
                                                    remaining_files += 1
                            
                            # Tạo nội dung thông báo
                            confirmation_text = self.tr_("DIALOG_FILE_EXISTS_MESSAGE")
                            
                            # Thêm danh sách các file đã tồn tại
                            files_list = "\n".join([f"• {f}" for f in file_exists_list])
                            # Nếu có file còn lại, thêm thông tin
                            if remaining_files > 0:
                                files_list += f"\n• ... và {remaining_files} file khác"
                            
                            confirmation_text += f"\n\n{files_list}"
                            
                            msg_box = QMessageBox(self)
                            msg_box.setWindowTitle(self.tr_("DIALOG_FILE_EXISTS"))
                            msg_box.setText(confirmation_text)
                            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
                            msg_box.setIcon(QMessageBox.Icon.Question)
                            
                            # Thiết lập kích thước tối thiểu
                            msg_box.setMinimumWidth(500)
                            msg_box.setMinimumHeight(200)
                            
                            # Xác định theme hiện tại
                            current_theme = "dark"
                            if hasattr(self, 'parent') and hasattr(self.parent, 'current_theme'):
                                current_theme = self.parent.current_theme
                            
                            # Style cho message box dựa trên theme hiện tại
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
                            
                            # Thêm checkbox "Apply to all" nếu tổng số video được chọn > 1
                            apply_all_checkbox = None
                            if selected_count > 1:
                                apply_all_checkbox = QCheckBox(self.tr_("DIALOG_APPLY_TO_ALL"))
                                # Thêm checkbox vào button box (cùng hàng với các nút)
                                button_box = msg_box.findChild(QDialogButtonBox)
                                if button_box:
                                    # Đưa checkbox vào bên trái của button box
                                    button_layout = button_box.layout()
                                    button_layout.insertWidget(0, apply_all_checkbox, 0, Qt.AlignmentFlag.AlignLeft)
                                    # Thêm khoảng cách lớn hơn giữa checkbox và các nút
                                    button_layout.insertSpacing(1, 50)
                                    # Tùy chỉnh checkbox để dễ nhìn hơn (không dùng font-weight: bold)
                                    apply_all_checkbox.setStyleSheet("QCheckBox { margin-right: 15px; }")
                            
                            # Hiển thị message box
                            reply = msg_box.exec()
                            
                            if reply == QMessageBox.StandardButton.No:
                                # Người dùng chọn không ghi đè
                                if apply_all_checkbox and apply_all_checkbox.isChecked():
                                    overwrite_all = False  # Áp dụng "không ghi đè" cho tất cả
                                continue
                            
                            elif reply == QMessageBox.StandardButton.Yes:
                                # Người dùng chọn ghi đè
                                if apply_all_checkbox and apply_all_checkbox.isChecked():
                                    overwrite_all = True  # Áp dụng "ghi đè" cho tất cả
                                
                                # Thêm vào hàng đợi tải xuống
                                download_queue.append({
                                    'url': url,
                                    'title': title,
                                    'format_id': format_id,
                                    'clean_title': clean_title,
                                    'ext': ext
                                })
                    else:
                        # Video chưa tồn tại, thêm vào hàng đợi tải xuống
                        download_queue.append({
                            'url': url,
                            'title': title,
                            'format_id': format_id,
                            'clean_title': clean_title,
                            'ext': ext
                        })
        
        # Nếu có video đã tồn tại, hiển thị thông báo
        if videos_already_exist:
            existing_titles = "\n".join([f"- {title}" for title in videos_already_exist])
            msg = f"{self.tr_('DIALOG_VIDEOS_ALREADY_EXIST')}\n{existing_titles}"
            QMessageBox.information(self, self.tr_("DIALOG_VIDEOS_EXIST"), msg)
        
        # Nếu không có video nào được chọn để tải
        if selected_count == 0:
            if not videos_already_exist:
                QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("DIALOG_NO_VIDEOS_SELECTED"))
            return
            
        # Nếu tất cả video được chọn đều đã tồn tại (không có video mới để tải)
        if not download_queue:
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_ALREADY_EXIST"))
            return
            
        # Đặt lại biến đếm
        self.downloading_count = len(download_queue)
        
        # Gán giá trị cho biến đếm tổng số video
        self.total_videos = len(download_queue)
            
        # Đặt lại biến đếm số video đã tải thành công
        self.success_downloads = 0
            
        # Disable nút Download khi đang tải
        self.download_btn.setEnabled(False)
        self.download_btn.setText(self.tr_("STATUS_DOWNLOADING_SHORT"))
            
        # Hiển thị thông báo số lượng video đang tải
        if self.parent:
            if self.downloading_count > 1:
                self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOADING_MULTIPLE").format(self.downloading_count))
            else:
                video_title = download_queue[0]['title']
                self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOADING_WITH_TITLE").format(video_title))
                
        # Cập nhật ngay lập tức để hiển thị thông báo
        QApplication.processEvents()
                    
        # Duyệt qua từng video trong hàng đợi để tải
        for video_info in download_queue:
            # Luôn xóa watermark mặc định
            remove_watermark = True
            
            # Lấy thông tin đã được tính toán trước đó
            clean_title = video_info.get('clean_title', '')
            ext = video_info.get('ext', 'mp4')
            
            # Nếu không có thông tin, tính toán lại (trường hợp dùng code cũ)
            if not clean_title:
                # Làm sạch tên video, loại bỏ hashtag để tạo tên file
                clean_title = video_info['title']
                # Loại bỏ tất cả các hashtag còn sót nếu có
                import re
                clean_title = re.sub(r'#\S+', '', clean_title).strip()
                # Loại bỏ các ký tự không hợp lệ cho tên file
                clean_title = re.sub(r'[\\/*?:"<>|]', '', clean_title).strip()
                
                # Xác định phần mở rộng file dựa trên định dạng
                is_audio = "audio" in video_info['format_id'].lower() or "bestaudio" in video_info['format_id'].lower()
                ext = "mp3" if is_audio else "mp4"
            
            # ĐOẠN KIỂM TRA TIÊU ĐỀ RỖNG ĐÃ ĐƯỢC DI CHUYỂN LÊN PHÍA TRÊN
            # VÀ ĐƯỢC KIỂM TRA TRƯỚC KHI ĐƯA VÀO DOWNLOAD_QUEUE
            
            # Thiết lập template đầu ra với tên đã được làm sạch
            output_dir = self.output_folder_display.text()
            
            # Tạo đường dẫn file đầy đủ
            output_file = os.path.join(output_dir, f"{clean_title}.{ext}")
            output_template = os.path.join(output_dir, f"{clean_title}.%(ext)s")
            
            # Bắt đầu tải xuống với yt-dlp
            try:
                # Trước tiên kiểm tra xem thumbnail đã tồn tại chưa
                thumbnails_dir = os.path.join(output_dir, "thumbnails")
                if not os.path.exists(thumbnails_dir):
                    os.makedirs(thumbnails_dir)
                
                # Lấy id của video (phần cuối URL trước dấu ?)
                video_id = video_info['url'].split('/')[-1].split('?')[0]
                
                # Biến cho tải xuống
                format_id = video_info['format_id']
                remove_watermark = True
                url = video_info['url']
                
                # Kiểm tra xem file đã tồn tại hay chưa để quyết định có force overwrite hay không
                force_overwrite = True  # Đã kiểm tra và được người dùng đồng ý
                
                # Nếu file tồn tại, xóa file cũ trước khi tải xuống
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                        print(f"Removed existing file: {output_file}")
                    except Exception as e:
                        print(f"Error removing existing file: {str(e)}")
                
                # Gọi hàm tải xuống
                self.downloader.download_video(
                    url=url, 
                    output_template=output_template, 
                    format_id=format_id, 
                    remove_watermark=remove_watermark,
                    audio_only=(ext == "mp3"),
                    force_overwrite=force_overwrite
                )
                
                # Cập nhật biến đếm nếu có lỗi
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
        
        # Nếu tất cả video đã tải xong, kích hoạt lại nút Download
        if self.downloading_count <= 0:
            self.download_btn.setEnabled(True)
            self.download_btn.setText(self.tr_("BUTTON_DOWNLOAD"))
            print(f"DEBUG - All downloads finished, reset download button")
            # Reset status bar khi tất cả đã tải xong
            if self.parent and self.parent.status_bar:
                self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOAD_SUCCESS"))

    def check_output_folder(self):
        """Kiểm tra xem thư mục đầu ra có tồn tại không"""
        if not self.output_folder_display.text():
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("DIALOG_NO_OUTPUT_FOLDER"))
            return False
        
        # Kiểm tra thư mục tồn tại
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
        """Lấy format_id dựa trên chất lượng và định dạng"""
        # Kiểm tra video_info có trong dict không
        video_info = None
        for row, info in self.video_info_dict.items():
            if info.url == url:
                video_info = info
                break
                
        if not video_info or not video_info.formats:
            return "best"  # Mặc định là best nếu không tìm thấy
            
        # Kiểm tra xem format là video hay audio
        is_audio = format_str == self.tr_("FORMAT_AUDIO_MP3")
        
        if is_audio:
            # Tìm format audio tốt nhất
            for fmt in video_info.formats:
                if fmt.get('is_audio', False):
                    return fmt['format_id']
            # Nếu không tìm thấy format audio riêng, sử dụng bestaudio
            return "bestaudio/best"
        else:
            # Nếu chất lượng là "Audio", thì đây là lỗi logic, chọn video tốt nhất
            if quality == "Audio":
                return "best"
                
            # Tìm format video phù hợp với chất lượng
            for fmt in video_info.formats:
                if fmt.get('quality', '') == quality and not fmt.get('is_audio', False):
                    return fmt['format_id']
            
            # Nếu không tìm thấy chính xác, tìm format gần nhất
            # Chuyển đổi chất lượng sang số
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
                    # Thử chuyển đổi trực tiếp nếu là định dạng như "540p"
                    target_quality = int(quality.replace('p', ''))
                except:
                    pass
            
            # Tìm format gần nhất
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
                
            return "best"  # Mặc định nếu không tìm thấy

    def tr_(self, key):
        """Dịch theo key sử dụng language manager hiện tại"""
        if hasattr(self, 'lang_manager') and self.lang_manager:
            return self.lang_manager.tr(key)
        return key  # Trả về key nếu không có language manager

    def format_tooltip_text(self, text):
        """Format tooltip text với dấu xuống dòng để dễ đọc hơn"""
        if not text:
            return ""
        
        # Xử lý xuống dòng tại dấu chấm, chấm than, chấm hỏi mà có khoảng trắng phía sau
        formatted_text = re.sub(r'([.!?]) ', r'\1\n', text)
        # Xử lý xuống dòng tại dấu phẩy mà có khoảng trắng phía sau
        formatted_text = re.sub(r'([,]) ', r'\1\n', formatted_text)
        
        # Xử lý hashtag - mỗi hashtag một dòng
        formatted_text = re.sub(r' (#[^\s#]+)', r'\n\1', formatted_text)
        
        return formatted_text

    def update_language(self):
        """Cập nhật ngôn ngữ cho tất cả các thành phần"""
        # Cập nhật các label
        self.url_label.setText(self.tr_("LABEL_VIDEO_URL"))
        self.output_label.setText(self.tr_("LABEL_OUTPUT_FOLDER"))
        
        # Cập nhật placeholder
        self.url_input.setPlaceholderText(self.tr_("PLACEHOLDER_VIDEO_URL"))
        self.output_folder_display.setPlaceholderText(self.tr_("PLACEHOLDER_OUTPUT_FOLDER"))
        
        # Cập nhật các nút
        self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
        self.choose_folder_btn.setText(self.tr_("BUTTON_CHOOSE_FOLDER"))
        self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL") if not self.all_selected else self.tr_("BUTTON_UNSELECT_ALL"))
        self.delete_selected_btn.setText(self.tr_("BUTTON_DELETE_SELECTED"))
        self.delete_all_btn.setText(self.tr_("BUTTON_DELETE_ALL"))
        self.download_btn.setText(self.tr_("BUTTON_DOWNLOAD"))
        
        # Cập nhật header bảng
        self.update_table_headers()

    def update_table_headers(self):
        """Cập nhật header của bảng theo ngôn ngữ hiện tại"""
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

    # Thêm phương thức mới để cập nhật màu sắc theo chế độ
    def apply_theme_colors(self, theme):
        """Áp dụng màu sắc theo chủ đề"""
        # Cập nhật màu sắc cho các thành phần
        # Xác định màu sắc theo theme
        if theme == "dark":
            # Màu sắc cho dark mode
            url_placeholder_color = "#8a8a8a"
            url_text_color = "#ffffff"
            folder_text_color = "#cccccc"
            
            # Style cho bảng trong dark mode
            table_style = """
                QTableWidget::item:hover {
                    background-color: rgba(80, 140, 255, 0.15);
                }
            """
            
            # Style cho thanh cuộn trong dark mode
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
            # Màu sắc cho light mode
            url_placeholder_color = "#888888"
            url_text_color = "#333333"
            folder_text_color = "#555555"
            
            # Style cho bảng trong light mode
            table_style = """
                QTableWidget::item:hover {
                    background-color: rgba(0, 120, 215, 0.1);
                }
            """
            
            # Style cho thanh cuộn trong light mode
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
        
        # Áp dụng style cho bảng
        if hasattr(self, 'video_table'):
            self.video_table.setStyleSheet(table_style)
            
        # Áp dụng style cho thanh cuộn
        self.setStyleSheet(scrollbar_style)
        
        # Áp dụng màu sắc cho các thành phần
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

    def connect_downloader_signals(self):
        """Kết nối các signals từ TikTokDownloader với UI"""
        self.downloader.info_signal.connect(self.on_video_info_received)
        self.downloader.progress_signal.connect(self.on_download_progress)
        self.downloader.finished_signal.connect(self.on_download_finished)

    # ===== Các phương thức xử lý signals từ TikTokDownloader =====
    
    def on_video_info_received(self, url, video_info):
        """Xử lý thông tin video khi nhận được"""
        try:
            print(f"Received video info for URL: {url}, title: {video_info.title}")
            
            # Cập nhật UI để hiển thị thông báo đang xử lý
            if self.parent and self.processing_count > 1:
                self.parent.status_bar.showMessage(self.tr_("STATUS_GETTING_INFO_MULTIPLE").format(self.processing_count))
                QApplication.processEvents()
            
            # Xử lý title - loại bỏ hashtag
            if video_info.title:
                # Lọc bỏ các hashtag khỏi title
                import re
                # Xóa hashtag và dấu cách thừa
                cleaned_title = re.sub(r'#\S+', '', video_info.title).strip()
                # Xóa nhiều dấu cách thành một dấu cách
                cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
                video_info.original_title = video_info.title  # Lưu title gốc
                video_info.title = cleaned_title  # Lưu title mới
            
            # Lưu thông tin video vào dictionary
            row = self.video_table.rowCount()
            self.video_info_dict[row] = video_info
            
            # Thêm dòng mới cho video này
            self.video_table.insertRow(row)
            
            # Kiểm tra nếu có lỗi trong tiêu đề
            has_error = video_info.title.startswith("Error:")
            
            # Kiểm tra xem có phải lỗi không hỗ trợ nội dung không (DIALOG_UNSUPPORTED_CONTENT)
            unsupported_content = "DIALOG_UNSUPPORTED_CONTENT" in video_info.title
            
            try:
                # Cột Select (Checkbox)
                checkbox = QCheckBox()
                checkbox.setChecked(not has_error)  # Không chọn nếu có lỗi
                
                # Cho phép chọn nếu là lỗi không hỗ trợ nội dung để có thể xóa
                if unsupported_content:
                    checkbox.setEnabled(True)
                else:
                    checkbox.setEnabled(not has_error)  # Disable nếu có lỗi
                
                # Kết nối sự kiện stateChanged với hàm checkbox_state_changed
                checkbox.stateChanged.connect(self.checkbox_state_changed)
                
                checkbox_cell = QWidget()
                layout = QHBoxLayout(checkbox_cell)
                layout.addWidget(checkbox)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)
                self.video_table.setCellWidget(row, 0, checkbox_cell)
                
                # Cột Title
                if unsupported_content:
                    # Hiển thị thông báo lỗi phù hợp từ file ngôn ngữ
                    title_text = self.tr_("DIALOG_UNSUPPORTED_CONTENT")
                else:
                    title_text = video_info.title
                    
                title_item = QTableWidgetItem(title_text)
                # Lưu title gốc vào UserRole để có thể lấy ra khi cần
                if hasattr(video_info, 'original_title') and video_info.original_title:
                    title_item.setData(Qt.ItemDataRole.UserRole, video_info.original_title)
                else:
                    title_item.setData(Qt.ItemDataRole.UserRole, title_text)
                # Format tooltip text để dễ đọc hơn
                tooltip_text = self.format_tooltip_text(title_text)
                title_item.setToolTip(tooltip_text)
                # Tắt khả năng chỉnh sửa
                title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.video_table.setItem(row, 1, title_item)
                
                # Cột Creator (Di chuyển lên vị trí ngay sau Title)
                creator = video_info.creator if hasattr(video_info, 'creator') and video_info.creator else ""
                creator_item = QTableWidgetItem(creator)
                creator_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Format tooltip text để dễ đọc hơn
                creator_tooltip = self.format_tooltip_text(creator)
                creator_item.setToolTip(creator_tooltip)  # Thêm tooltip khi hover
                # Tắt khả năng chỉnh sửa
                creator_item.setFlags(creator_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.video_table.setItem(row, 2, creator_item)
                
                # Cột Quality (Combobox)
                quality_combo = QComboBox()
                # Đặt chiều rộng cố định cho combobox
                quality_combo.setFixedWidth(80)
                
                # Lấy danh sách chất lượng từ formats
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
                
                # Sắp xếp chất lượng từ cao xuống thấp
                def quality_to_number(q):
                    try:
                        return int(q.replace('p', ''))
                    except:
                        return 0
                
                video_qualities.sort(key=quality_to_number, reverse=True)
                qualities = video_qualities
                
                if not qualities:
                    qualities = ['1080p', '720p', '480p', '360p']  # Mặc định nếu không tìm thấy
                    
                quality_combo.addItems(qualities)
                quality_combo.setEnabled(not has_error)  # Disable nếu có lỗi
                quality_cell = QWidget()
                quality_layout = QHBoxLayout(quality_cell)
                quality_layout.addWidget(quality_combo)
                quality_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                quality_layout.setContentsMargins(0, 0, 0, 0)
                self.video_table.setCellWidget(row, 3, quality_cell)
                
                # Cột Format (Combobox)
                format_combo = QComboBox()
                # Đặt chiều rộng cố định cho combobox
                format_combo.setFixedWidth(100)
                
                # Nếu là video, chỉ hiển thị hai lựa chọn: Video và Audio
                format_combo.addItem(self.tr_("FORMAT_VIDEO_MP4"))
                format_combo.addItem(self.tr_("FORMAT_AUDIO_MP3"))
                format_combo.setEnabled(not has_error)  # Disable nếu có lỗi
                format_cell = QWidget()
                format_layout = QHBoxLayout(format_cell)
                format_layout.addWidget(format_combo)
                format_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                format_layout.setContentsMargins(0, 0, 0, 0)
                self.video_table.setCellWidget(row, 4, format_cell)
                
                # Kết nối sự kiện thay đổi format với hàm xử lý
                format_combo.currentIndexChanged.connect(
                    lambda index, combo=format_combo, q_combo=quality_combo, audio=audio_quality, video_qs=qualities: 
                    self.on_format_changed(index, combo, q_combo, audio, video_qs)
                )
                
                # Cột Duration
                duration_str = self.format_duration(video_info.duration)
                duration_item = QTableWidgetItem(duration_str)
                duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Tắt khả năng chỉnh sửa
                duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.video_table.setItem(row, 5, duration_item)
                
                # Cột Size (ước lượng dựa trên format)
                size_str = self.estimate_size(video_info.formats)
                size_item = QTableWidgetItem(size_str)
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Tắt khả năng chỉnh sửa
                size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.video_table.setItem(row, 6, size_item)
                
                # Cột Hashtags
                hashtags = []
                # Trích xuất hashtags từ caption nếu có
                if video_info.caption:
                    import re
                    # Tìm tất cả các hashtag bắt đầu bằng # trong caption, hỗ trợ cả tiếng Việt và ký tự đặc biệt
                    found_hashtags = re.findall(r'#([^\s#]+)', video_info.caption)
                    if found_hashtags:
                        hashtags.extend(found_hashtags)
                
                # Kết hợp với hashtags đã có sẵn trong video_info
                if hasattr(video_info, 'hashtags') and video_info.hashtags:
                    for tag in video_info.hashtags:
                        if tag not in hashtags:
                            hashtags.append(tag)
                
                hashtags_str = " ".join([f"#{tag}" for tag in hashtags]) if hashtags else ""
                hashtags_item = QTableWidgetItem(hashtags_str)
                # Format tooltip text để dễ đọc hơn
                hashtags_tooltip = self.format_tooltip_text(hashtags_str)
                hashtags_item.setToolTip(hashtags_tooltip)  # Thêm tooltip khi hover
                # Tắt khả năng chỉnh sửa
                hashtags_item.setFlags(hashtags_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.video_table.setItem(row, 7, hashtags_item)
                
                # Thêm tooltip cho tiêu đề
                title_item = self.video_table.item(row, 1)
                if title_item:
                    title_item.setToolTip(video_info.title)
            except Exception as cell_error:
                print(f"Error creating UI cells: {cell_error}")
                # Đảm bảo dòng được tạo đúng
                while self.video_table.columnCount() > self.video_table.item(row, 0).column() + 1:
                    self.video_table.setItem(row, self.video_table.item(row, 0).column() + 1, QTableWidgetItem("Error"))
            
            # Cập nhật trạng thái
            if self.parent:
                if has_error:
                    if unsupported_content:
                        # Hiển thị thông báo lỗi thân thiện từ file ngôn ngữ
                        self.parent.status_bar.showMessage(self.tr_("DIALOG_UNSUPPORTED_CONTENT"))
                    else:
                        # Hiển thị lỗi khác
                        self.parent.status_bar.showMessage(video_info.title)
                else:
                    # Hiển thị thông báo đã nhận thông tin video
                    if self.processing_count > 1:
                        self.parent.status_bar.showMessage(self.tr_("STATUS_GETTING_INFO_MULTIPLE").format(self.processing_count))
                    else:
                        self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEO_INFO"))
                    
            # Giảm biến đếm và kiểm tra xem đã xử lý hết chưa
            self.processing_count -= 1
            if self.processing_count <= 0:
                # Kích hoạt lại UI
                self.get_info_btn.setEnabled(True)
                self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
                self.url_input.setEnabled(True)
                
                # Cập nhật thông báo trạng thái
                total_videos = self.video_table.rowCount()
                if self.parent:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_LOADED").format(total_videos))
                    
                # Cập nhật UI ngay lập tức
                QApplication.processEvents()
                
                # Cập nhật trạng thái nút Select All/Unselect All dựa trên các checkbox
                self.update_select_toggle_button()
            
            # Không reset cứng trạng thái mà để hàm update_select_toggle_button quyết định giá trị đúng dựa trên trạng thái của các checkbox.
            # self.all_selected = False
            # self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
            
            # Cập nhật UI
            self.get_info_btn.setEnabled(True)
            self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
            self.url_input.setEnabled(True)
            self.url_input.clear()
            
            # Cập nhật trạng thái các nút
            self.update_button_states()
            
            # Hiển thị thông báo trên status bar
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_INFO_RECEIVED"))
        except Exception as e:
            print(f"Critical error in on_video_info_received: {e}")
            # Đảm bảo giảm biến đếm
            self.processing_count -= 1
            if self.processing_count <= 0:
                # Kích hoạt lại UI
                self.get_info_btn.setEnabled(True)
                self.get_info_btn.setText(self.tr_("BUTTON_GET_INFO"))
                self.url_input.setEnabled(True)
            
            # Hiển thị lỗi trong status bar
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ERROR").format(str(e)))
    
    def on_download_progress(self, url, progress, speed):
        """Cập nhật tiến trình tải xuống"""
        # Tìm dòng chứa URL này
        for row, info in self.video_info_dict.items():
            if info.url == url:
                # Hiển thị tiến trình tải trong status bar
                if self.parent:
                    self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOADING_PROGRESS").format(int(progress), speed))
                break
    
    def on_download_finished(self, url, success, file_path):
        """Xử lý khi một video đã tải xong"""
        self.downloading_count -= 1
        
        # Debug log
        print(f"DEBUG - on_download_finished called with URL: {url}, success: {success}, file_path: {file_path}")
        
        # Đảm bảo file_path không còn chứa %(ext)s
        if '%(ext)s' in file_path:
            # Kiểm tra đuôi file thực tế
            if file_path.lower().endswith('.mp3'):
                file_path = file_path.replace('.%(ext)s', '.mp3')
            else:
                file_path = file_path.replace('.%(ext)s', '.mp4')
            print(f"DEBUG - Fixed file_path: {file_path}")
            
        # Tìm kiếm video trong bảng và ẩn progress bar
        row_to_remove = None
        found_video_info = None
        
        # Tìm video trong bảng dựa vào URL
        for row in range(self.video_table.rowCount()):
            # Lấy video_info từ dictionary
            row_info = self.video_info_dict.get(row)
            if row_info and row_info.url == url:
                row_to_remove = row
                found_video_info = row_info
                print(f"DEBUG - Found matching video at row {row}: {row_info.title}")
                break
        
        print(f"DEBUG - Row to remove: {row_to_remove}, Found video info: {found_video_info}")
        
        # Tăng số lượng video đã tải thành công
        if success:
            self.success_downloads += 1
            video_info = found_video_info or self.video_info_dict.get(row_to_remove, None)
            filename = os.path.basename(file_path)
            
            print(f"DEBUG - Success download! File: {filename}")
            
            # Hiển thị thông báo trạng thái
            if self.parent and self.parent.status_bar:
                # Nếu còn video đang tải
                if self.downloading_count > 0:
                    # Cắt gọn tên file nếu quá dài
                    short_filename = self.truncate_filename(filename)
                    self.parent.status_bar.showMessage(self.tr_("STATUS_ONE_OF_MULTIPLE_DONE").format(
                        short_filename,
                        self.downloading_count
                    ))
                else:
                    # Nếu đã tải hết, hiển thị thông báo tải thành công
                    if self.success_downloads > 1:
                        self.parent.status_bar.showMessage(self.tr_("DIALOG_DOWNLOAD_MULTIPLE_SUCCESS").format(self.success_downloads))
                    else:
                        # Cắt gọn tên file nếu quá dài
                        short_filename = self.truncate_filename(filename)
                        self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOAD_SUCCESS_WITH_FILENAME").format(short_filename))
            
            # Cập nhật UI ngay lập tức để hiển thị thông báo
            QApplication.processEvents()
            
            # Cập nhật tab Downloaded Videos nếu có và thêm video mới
            if hasattr(self.parent, 'downloaded_videos_tab') and video_info:
                print(f"DEBUG - Adding video to Downloaded Videos tab: {video_info.title}")
                
                # Lấy thông tin chất lượng đã chọn
                quality_cell = self.video_table.cellWidget(row_to_remove, 3) if row_to_remove is not None else None
                quality = quality_cell.findChild(QComboBox).currentText() if quality_cell else "1080p"
                
                # Lấy thông tin định dạng đã chọn
                format_cell = self.video_table.cellWidget(row_to_remove, 4) if row_to_remove is not None else None
                format_str = format_cell.findChild(QComboBox).currentText() if format_cell else self.tr_("FORMAT_VIDEO_MP4")
                
                # Kiểm tra kỹ đuôi file và cập nhật định dạng, chất lượng
                if file_path.lower().endswith('.mp3'):
                    format_str = self.tr_("FORMAT_AUDIO_MP3")
                    quality = "320kbps"  # Đặt chất lượng mặc định cho audio
                elif file_path.lower().endswith('.mp4'):
                    # Kiểm tra xem format_str có phải đã là định dạng audio không
                    if format_str == self.tr_("FORMAT_AUDIO_MP3"):
                        format_str = self.tr_("FORMAT_VIDEO_MP4")
                
                # Kiểm tra nếu đây là video không có tiêu đề đã được đặt tên mới
                display_title = video_info.title
                if hasattr(video_info, 'custom_title') and video_info.custom_title:
                    display_title = video_info.custom_title
                
                # Nếu tên file khác với tên video ban đầu, có thể đã được đổi tên
                filename_without_ext = os.path.splitext(os.path.basename(file_path))[0]
                if filename_without_ext and filename_without_ext != video_info.title:
                    display_title = filename_without_ext
                
                # Tạo thông tin tải xuống để thêm vào tab Downloaded Videos
                download_info = {
                    'url': url,
                    'title': display_title,  # Sử dụng tên đã được đặt
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
                
                # Trích xuất hashtags từ tiêu đề video gốc và caption
                combined_hashtags = set()  # Dùng set để tránh lặp lại

                # Nếu có original_title, trích xuất hashtag từ đó
                if hasattr(video_info, 'original_title') and video_info.original_title:
                    import re
                    # Phát hiện tất cả các chuỗi bắt đầu bằng # và kết thúc bằng khoảng trắng hoặc cuối chuỗi
                    found_hashtags = re.findall(r'#([^\s#\.]+)', video_info.original_title)
                    if found_hashtags:
                        combined_hashtags.update(found_hashtags)
                    
                    # Xử lý trường hợp tiêu đề bị cắt (có dấu "..." ở cuối)
                    if "..." in video_info.original_title:
                        # Lấy cả hashtag trong title hiển thị trong tab download
                        title_file = os.path.basename(file_path)
                        if "#" in title_file:
                            additional_hashtags = re.findall(r'#([^\s#\.]+)', title_file)
                            if additional_hashtags:
                                combined_hashtags.update(additional_hashtags)

                # Lấy hashtag từ caption
                if hasattr(video_info, 'caption') and video_info.caption:
                    import re
                    found_hashtags = re.findall(r'#([^\s#\.]+)', video_info.caption)
                    if found_hashtags:
                        combined_hashtags.update(found_hashtags)
                
                # Kết hợp với hashtags đã có sẵn trong video_info
                if hasattr(video_info, 'hashtags') and video_info.hashtags:
                    combined_hashtags.update([tag.strip() for tag in video_info.hashtags])
                
                # Nếu vẫn không tìm thấy hashtag nào, kiểm tra xem filename có chứa hashtag không
                if not combined_hashtags and "#" in filename:
                    additional_hashtags = re.findall(r'#([^\s#\.]+)', filename)
                    if additional_hashtags:
                        combined_hashtags.update(additional_hashtags)
                
                # Gán hashtags vào download_info
                if combined_hashtags:
                    download_info['hashtags'] = list(combined_hashtags)
                
                # In hashtag ra để debug
                print(f"DEBUG - Combined hashtags: {download_info['hashtags']}")
                
                # Tải và lưu thumbnail nếu có
                thumbnail_path = ""
                if hasattr(video_info, 'thumbnail') and video_info.thumbnail:
                    try:
                        # Tạo thư mục thumbnails nếu chưa tồn tại
                        thumbnails_dir = os.path.join(os.path.dirname(file_path), "thumbnails")
                        if not os.path.exists(thumbnails_dir):
                            os.makedirs(thumbnails_dir)
                        
                        # Tạo tên file thumbnail từ id video TikTok
                        video_id = url.split('/')[-1].split('?')[0]  # Lấy ID video từ URL
                        thumbnail_path = os.path.join(thumbnails_dir, f"{video_id}.jpg")
                        
                        # Tải thumbnail
                        response = requests.get(video_info.thumbnail, stream=True)
                        response.raise_for_status()
                        
                        with open(thumbnail_path, 'wb') as out_file:
                            shutil.copyfileobj(response.raw, out_file)
                    except Exception as e:
                        print(f"Error downloading thumbnail: {e}")
                
                # Lưu đường dẫn thumbnail vào thông tin video
                download_info['thumbnail'] = thumbnail_path
                
                # In ra log
                print(f"DEBUG - Title: {download_info['title']}")
                print(f"DEBUG - Quality: {download_info['quality']}, Format: {download_info['format']}")
                print(f"DEBUG - Hashtags: {download_info['hashtags']}")
                print(f"DEBUG - Thumbnail: {download_info['thumbnail']}")
                print(f"DEBUG - Status: {download_info['status']}")
                
                # Thêm vào tab Downloaded Videos
                self.parent.downloaded_videos_tab.add_downloaded_video(download_info)
                print(f"DEBUG - Video added to Downloaded Videos tab")
                
                # Ép cập nhật giao diện Downloaded Videos tab
                self.parent.downloaded_videos_tab.display_videos()
                print(f"DEBUG - Downloaded Videos tab display updated")
            
            # Xóa hàng sau khi tải xuống thành công
            if row_to_remove is not None:
                print(f"DEBUG - Removing row {row_to_remove} from video table")
                self.video_table.removeRow(row_to_remove)
                if row_to_remove in self.video_info_dict:
                    del self.video_info_dict[row_to_remove]
                    print(f"DEBUG - Removed row {row_to_remove} from video_info_dict")
            else:
                print(f"DEBUG - Could not find row to remove for URL: {url}")
            
            # Cập nhật lại index của các mục trong video_info_dict
            new_dict = {}
            print(f"DEBUG - Reindexing video_info_dict after deletion, current keys: {sorted(self.video_info_dict.keys())}")
            
            # Đơn giản hóa: Chỉ cần tạo dictionary mới với các index liên tiếp
            values = list(self.video_info_dict.values())
            for new_idx in range(len(values)):
                new_dict[new_idx] = values[new_idx]
            
            self.video_info_dict = new_dict
            print(f"DEBUG - Updated video_info_dict after deletion, new size: {len(self.video_info_dict)}, new keys: {sorted(self.video_info_dict.keys())}")
            
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOAD_SUCCESS")) 
        else:
            # Nếu tải thất bại, hiển thị thông báo lỗi phù hợp
            if self.parent and self.parent.status_bar:
                self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOAD_FAILED"))
                print(f"DEBUG - Download failed for URL: {url}")
        
        # Nếu tất cả video đã tải xong, kích hoạt lại nút Download
        if self.downloading_count <= 0:
            self.download_btn.setEnabled(True)
            self.download_btn.setText(self.tr_("BUTTON_DOWNLOAD"))
            print(f"DEBUG - All downloads finished, reset download button")
            # Reset status bar khi tất cả đã tải xong
            if self.parent and self.parent.status_bar:
                self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOAD_SUCCESS"))

    def truncate_filename(self, filename, max_length=30):
        """Cắt gọn tên file để hiển thị trong status bar"""
        if len(filename) <= max_length:
            return filename
            
        # Lấy tên và phần mở rộng
        name, ext = os.path.splitext(filename)
        
        # Tính toán số ký tự giữ lại
        # Giữ 10 ký tự đầu, dấu ..., và 10 ký tự cuối + phần mở rộng
        keep_length = max_length - 3  # trừ đi 3 dấu chấm
        first_part = (keep_length // 2) - len(ext)
        last_part = keep_length - first_part - len(ext)
        
        return f"{name[:first_part]}...{name[-last_part:]}{ext}"

    def open_folder(self, folder_path):
        """Mở thư mục chứa file"""
        try:
            if os.path.exists(folder_path):
                if os.name == 'nt':  # Windows
                    os.startfile(folder_path)
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
        """Định dạng thời lượng từ giây sang MM:SS"""
        if not seconds:
            return "00:00"
        
        minutes = int(seconds / 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes:02d}:{remaining_seconds:02d}"
    
    def estimate_size(self, formats):
        """Ước lượng kích thước file dựa trên formats"""
        if not formats:
            return "Unknown"
        
        # Lấy format lớn nhất
        max_size = 0
        for fmt in formats:
            if 'filesize' in fmt and fmt['filesize'] and fmt['filesize'] > max_size:
                max_size = fmt['filesize']
        
        if max_size == 0:
            return "Unknown"
        
        # Chuyển đổi sang MB
        size_mb = max_size / (1024 * 1024)
        return f"{size_mb:.2f} MB"

    def on_format_changed(self, index, format_combo, quality_combo, audio_quality, video_qualities):
        """Xử lý khi người dùng thay đổi định dạng"""
        is_audio = format_combo.currentText() == self.tr_("FORMAT_AUDIO_MP3")
        
        # Xóa tất cả items hiện tại
        quality_combo.clear()
        
        if is_audio:
            # Nếu là audio, chỉ hiển thị chất lượng audio
            if audio_quality:
                quality_combo.addItem(audio_quality)
            else:
                quality_combo.addItem("Original")
        else:
            # Nếu là video, hiển thị lại danh sách chất lượng video
            quality_combo.addItems(video_qualities) 

    def delete_selected_videos(self):
        """Xóa các video đã chọn khỏi bảng"""
        # Đếm số video đã chọn
        selected_count = 0
        for row in range(self.video_table.rowCount()):
            checkbox_cell = self.video_table.cellWidget(row, 0)
            if checkbox_cell:
                checkbox = checkbox_cell.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected_count += 1
        
        # Nếu không có video nào được chọn
        if selected_count == 0:
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("DIALOG_NO_VIDEOS_SELECTED"))
            return
            
        # Hiển thị hộp thoại xác nhận
        reply = QMessageBox.question(
            self, self.tr_("DIALOG_CONFIRM_DELETION"), 
            self.tr_("DIALOG_CONFIRM_DELETE_SELECTED").format(selected_count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Xóa từ dưới lên trên để tránh lỗi index
            for row in range(self.video_table.rowCount() - 1, -1, -1):
                checkbox_cell = self.video_table.cellWidget(row, 0)
                if checkbox_cell:
                    checkbox = checkbox_cell.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        self.video_table.removeRow(row)
                        # Cập nhật lại index của các mục trong video_info_dict
                        if row in self.video_info_dict:
                            del self.video_info_dict[row]
            
            # Cập nhật lại index của các mục trong video_info_dict
            new_dict = {}
            # Đơn giản hóa: Chỉ cần tạo dictionary mới với các index liên tiếp
            values = list(self.video_info_dict.values())
            for new_idx in range(len(values)):
                new_dict[new_idx] = values[new_idx]
            
            self.video_info_dict = new_dict
            
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_SELECTED_DELETED").format(selected_count))
            
            # Sau khi hoàn tất xóa các video đã chọn
            self.video_table.blockSignals(False)
            
            # Cập nhật trạng thái nút chọn tất cả
            self.update_select_toggle_button()
            
            # Cập nhật trạng thái các nút
            self.update_button_states()

    def get_selected_quality(self, row):
        """Lấy chất lượng được chọn từ hàng trong bảng"""
        if row is None or row < 0 or row >= self.video_table.rowCount():
            return "1080p"  # Giá trị mặc định khi không có row
        
        try:
            quality_cell = self.video_table.cellWidget(row, 2)  # Cột Quality (index 2)
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
            
        return "1080p"  # Giá trị mặc định
        
    def get_selected_format(self, row):
        """Lấy định dạng được chọn từ hàng trong bảng"""
        if row is None or row < 0 or row >= self.video_table.rowCount():
            return "Video (mp4)"  # Giá trị mặc định khi không có row
        
        try:
            format_cell = self.video_table.cellWidget(row, 3)  # Cột Format (index 3)
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
            
        return "Video (mp4)"  # Giá trị mặc định 

    def show_copy_dialog(self, item):
        """Hiển thị dialog cho phép copy text khi double-click vào ô trong bảng"""
        column = item.column()
        row = item.row()
        
        # Map thực tế của các cột trong bảng:
        # Column 1: Title
        # Column 2: Creator
        # Column 7: Hashtags
        
        # Chỉ hiển thị dialog copy cho các cột quan trọng
        if column not in [1, 2, 7]:
            return
        
        # Debug để hiểu cấu trúc của video_info_dict
        print(f"DEBUG - video_info_dict type: {type(self.video_info_dict)}")
        print(f"DEBUG - Double-clicked on row {row}, column {column}")
        if row in self.video_info_dict:
            print(f"DEBUG - video_info at row {row} type: {type(self.video_info_dict[row])}")
            print(f"DEBUG - video_info attributes: {dir(self.video_info_dict[row])}")
        
        # Lấy thông tin video đầy đủ
        full_text = ""
        if row in self.video_info_dict:
            video_info = self.video_info_dict[row]
            if column == 1:  # Title
                # In thông tin debug để xem nội dung
                if hasattr(video_info, 'title'):
                    print(f"DEBUG - Title: '{video_info.title}'")
                if hasattr(video_info, 'caption'):
                    print(f"DEBUG - Caption: '{video_info.caption}'")
                if hasattr(video_info, 'original_title'):
                    print(f"DEBUG - Original title: '{video_info.original_title}'")
                
                # Ưu tiên lấy caption làm nguồn dữ liệu chính vì thường chứa nội dung đầy đủ nhất
                if hasattr(video_info, 'caption') and video_info.caption:
                    full_text = video_info.caption
                elif hasattr(video_info, 'original_title') and video_info.original_title:
                    # Lấy tiêu đề gốc nếu không có caption
                    full_text = video_info.original_title
                else:
                    # Sử dụng title hiện tại nếu không có các thông tin khác
                    full_text = video_info.title if hasattr(video_info, 'title') else item.text()
                
                # Loại bỏ các hashtag khỏi tiêu đề khi hiển thị
                if full_text:
                    # Loại bỏ các hashtag ở dạng #xxx
                    import re
                    full_text = re.sub(r'#\w+', '', full_text)
                    # Loại bỏ các hashtag ở dạng #xxx với khoảng trắng trước
                    full_text = re.sub(r'\s+#\w+', '', full_text)
                    # Loại bỏ khoảng trắng thừa và dấu cách cuối cùng
                    full_text = re.sub(r'\s+', ' ', full_text).strip()
                
                print(f"DEBUG - Selected full_text for dialog (after removing hashtags): '{full_text}'")
            elif column == 2:  # Creator
                full_text = video_info.creator if hasattr(video_info, 'creator') else item.text()
            elif column == 7:  # Hashtags
                if hasattr(video_info, 'hashtags') and video_info.hashtags:
                    full_text = ' '.join(f"#{tag}" for tag in video_info.hashtags)
                else:
                    # Thử lấy từ caption nếu không có hashtags riêng
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
            
        # Xác định tiêu đề dialog dựa theo cột
        if column == 1:
            title = self.tr_("HEADER_VIDEO_TITLE")
        elif column == 2:
            title = self.tr_("HEADER_CREATOR")
        else:  # column == 7
            title = self.tr_("HEADER_HASHTAGS")
            
        # Tạo dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(600)  # Tăng chiều rộng tối thiểu
        dialog.setMinimumHeight(400)  # Thêm chiều cao tối thiểu
        dialog.resize(600, 400)
        
        # Xác định theme hiện tại từ parent window
        current_theme = "dark"
        if hasattr(self, 'parent') and hasattr(self.parent, 'current_theme'):
            current_theme = self.parent.current_theme
        
        # Áp dụng style dựa trên theme hiện tại
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
        
        # Text edit để hiển thị và copy
        text_edit = QTextEdit(dialog)
        text_edit.setPlainText(full_text)
        text_edit.setReadOnly(True)  # Chỉ cho phép đọc và copy
        text_edit.setMinimumHeight(300)  # Đặt chiều cao tối thiểu cho text edit
        text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)  # Tự động wrap text
        
        # Thiết lập scroll bar
        text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
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
        
        # Hiện dialog và xử lý sau khi đóng dialog
        dialog.exec()
        
        # Xóa bôi đen và đặt focus sau khi đóng dialog
        self.video_table.clearSelection()
        self.video_table.clearFocus()
        # Đặt focus về ô tìm kiếm để tránh hiệu ứng bôi đen
        self.url_input.setFocus()
        
    def copy_to_clipboard(self, text, column_name=None):
        """Sao chép văn bản vào clipboard với xử lý đặc biệt cho một số cột"""
        if not text:
            return
        
        # Xử lý đặc biệt cho cột title - loại bỏ hashtags
        if column_name == "title":
            # Loại bỏ các hashtag khỏi title
            text = re.sub(r'#\w+', '', text).strip()
            # Loại bỏ khoảng trắng kép
            text = re.sub(r'\s+', ' ', text)
        
        # Đặt văn bản vào clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        # Hiển thị thông báo
        show_message = True
        if hasattr(self, 'parent') and hasattr(self.parent, 'settings'):
            show_message = self.parent.settings.value("show_copy_message", "true") == "true"
        
        if show_message:
            copied_text = text[:50] + "..." if len(text) > 50 else text
            self.parent.status_bar.showMessage(self.tr_("STATUS_TEXT_COPIED").format(copied_text), 3000)

    # Thêm phương thức mới để chọn hoặc bỏ chọn tất cả video trong bảng
    def toggle_select_all(self):
        """Chọn hoặc bỏ chọn tất cả video trong bảng"""
        self.all_selected = not self.all_selected
        
        # Cập nhật nhãn của nút dựa trên trạng thái mới
        if self.all_selected:
            self.select_toggle_btn.setText(self.tr_("BUTTON_UNSELECT_ALL"))
        else:
            self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
            
        # Tạm ngắt kết nối signal để tránh gọi checkbox_state_changed nhiều lần
        checkboxes = []
        
        # Thu thập tất cả checkbox và ngắt kết nối signal
        for row in range(self.video_table.rowCount()):
            checkbox_cell = self.video_table.cellWidget(row, 0)
            if checkbox_cell:
                checkbox = checkbox_cell.findChild(QCheckBox)
                if checkbox:
                    # Ngắt kết nối signal tạm thời
                    checkbox.stateChanged.disconnect(self.checkbox_state_changed)
                    checkboxes.append(checkbox)
        
        # Cập nhật trạng thái checkbox
        for checkbox in checkboxes:
            checkbox.setChecked(self.all_selected)
        
        # Kết nối lại signal sau khi đã cập nhật xong
        for checkbox in checkboxes:
            checkbox.stateChanged.connect(self.checkbox_state_changed)
        
        # Hiển thị thông báo trên status bar
        if self.parent and self.parent.status_bar:
            if self.all_selected:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ALL_VIDEOS_SELECTED"))
            else:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ALL_VIDEOS_UNSELECTED")) 

    # Thêm phương thức để cập nhật trạng thái nút Toggle Select All dựa trên checkbox
    def update_select_toggle_button(self):
        """Cập nhật trạng thái nút chọn tất cả dựa trên trạng thái checkbox trong bảng"""
        # Kiểm tra xem có video nào trong bảng không
        if self.video_table.rowCount() == 0:
            return
            
        # Kiểm tra trạng thái của tất cả checkbox
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
        
        # Cập nhật trạng thái của nút và biến all_selected
        if all_checked:
            self.all_selected = True
            self.select_toggle_btn.setText(self.tr_("BUTTON_UNSELECT_ALL"))
        else:
            self.all_selected = False
            self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
            
    # Phương thức xử lý sự kiện checkbox thay đổi
    def checkbox_state_changed(self):
        """Xử lý khi trạng thái checkbox thay đổi"""
        self.update_select_toggle_button()

    def show_full_text_tooltip(self, row, column):
        """Hiển thị tooltip với toàn bộ nội dung khi hover vào ô"""
        try:
            item = self.video_table.item(row, column)
            if item:
                text = item.text()
                
                # Xử lý đặc biệt cho cột title (column 1)
                if column == 1 and row in self.video_info_dict:
                    video_info = self.video_info_dict[row]
                    
                    # Ưu tiên sử dụng caption nếu có (chứa đầy đủ thông tin nhất)
                    if hasattr(video_info, 'caption') and video_info.caption:
                        text = video_info.caption
                    # Nếu không có caption, thử dùng original_title
                    elif hasattr(video_info, 'original_title') and video_info.original_title:
                        text = video_info.original_title
                    # Nếu không, thì sử dụng title
                    elif hasattr(video_info, 'title'):
                        text = video_info.title
                        
                # Đối với các trường khác, lấy text trực tiếp từ item
                if text:
                    # Format tooltip text để dễ đọc hơn với line breaks
                    formatted_text = self.format_tooltip_text(text)
                    QToolTip.showText(QCursor.pos(), formatted_text)
        except Exception as e:
            print(f"DEBUG - Error in show_full_text_tooltip: {e}")
            # Ignore exceptions
            pass

    def update_button_states(self):
        """Cập nhật trạng thái các nút dựa trên số lượng video trong bảng"""
        has_videos = self.video_table.rowCount() > 0
        
        # Vô hiệu hóa các nút khi không có video nào
        self.select_toggle_btn.setEnabled(has_videos)
        self.delete_selected_btn.setEnabled(has_videos)
        self.delete_all_btn.setEnabled(has_videos)
        self.download_btn.setEnabled(has_videos)
        
        # Không áp dụng style vì đã được xử lý từ main_window.py
        print("DEBUG: update_button_states in video_info_tab - button states updated without applying style")