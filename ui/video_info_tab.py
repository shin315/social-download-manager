from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableWidget, QComboBox,
                             QFileDialog, QCheckBox, QHeaderView, QMessageBox,
                             QTableWidgetItem, QProgressBar, QApplication, QDialog, QTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
import os
import json
from localization import get_language_manager
from utils.downloader import TikTokDownloader, VideoInfo
from PyQt6.QtNetwork import QNetworkRequest, QNetworkAccessManager, QNetworkReply
from PyQt6.QtGui import QPixmap
from datetime import datetime
from utils.db_manager import DatabaseManager
import requests
import shutil  # For file operations

# Đường dẫn đến file cấu hình
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')

class VideoInfoTab(QWidget):
    """Tab hiển thị thông tin video và tải video"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.lang_manager = get_language_manager()
        
        # Khởi tạo TikTokDownloader
        self.downloader = TikTokDownloader()
        
        # Khởi tạo biến lưu trữ thông tin video
        self.video_info_dict = {}  # Dictionary với key là URL, value là VideoInfo
        
        # Biến đếm số video đang xử lý
        self.processing_count = 0
        
        # Biến đếm số video đang tải xuống
        self.downloading_count = 0
        
        self.init_ui()
        self.load_last_output_folder()
        
        # Kết nối signals từ downloader
        self.connect_downloader_signals()
        
        # Kết nối với tín hiệu thay đổi ngôn ngữ từ MainWindow
        if parent and hasattr(parent, 'language_changed'):
            parent.language_changed.connect(self.update_language)
            
        # Áp dụng kiểu màu mặc định theo chế độ tối (có thể được ghi đè sau này)
        self.apply_theme_colors("dark")

    def init_ui(self):
        # Layout chính
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Phần URL và Get Info
        url_layout = QHBoxLayout()
        
        # Label URL
        self.url_label = QLabel(self.tr_("LABEL_VIDEO_URL"))
        url_layout.addWidget(self.url_label)
        
        # Tạo khoảng cách để căn chỉnh ô input URL với ô output folder
        spacer_width = 18  # Điều chỉnh lên 70px để căn chỉnh tốt hơn
        url_layout.addSpacing(spacer_width)
        
        # Input URL
        self.url_input = QLineEdit()
        self.url_input.setFixedHeight(30)
        # Không đặt chiều rộng cố định nữa - cho phép kéo giãn theo cửa sổ
        self.url_input.setMinimumWidth(500)
        self.url_input.setPlaceholderText(self.tr_("PLACEHOLDER_VIDEO_URL"))
        # Kết nối sự kiện returnPressed với hàm get_video_info
        self.url_input.returnPressed.connect(self.get_video_info)
        url_layout.addWidget(self.url_input, 1)  # stretch factor 1 để mở rộng khi phóng to
        
        # Nút Get Info
        self.get_info_btn = QPushButton(self.tr_("BUTTON_GET_INFO"))
        self.get_info_btn.setFixedWidth(120)  # Cố định chiều rộng
        self.get_info_btn.clicked.connect(self.get_video_info)
        url_layout.addWidget(self.get_info_btn)
        
        main_layout.addLayout(url_layout)

        # Phần Output Folder
        output_layout = QHBoxLayout()
        
        # Label Output Folder
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
        
        # Checkbox Remove Watermark đã được xóa và luôn xóa watermark mặc định
        
        options_layout.addStretch(1)
        
        # Nút Chọn tất cả
        self.select_all_btn = QPushButton(self.tr_("BUTTON_SELECT_ALL"))
        self.select_all_btn.setFixedWidth(120)
        self.select_all_btn.clicked.connect(self.select_all_videos)
        options_layout.addWidget(self.select_all_btn)
        
        # Nút Bỏ chọn tất cả
        self.unselect_all_btn = QPushButton(self.tr_("BUTTON_UNSELECT_ALL"))
        self.unselect_all_btn.setFixedWidth(120)
        self.unselect_all_btn.clicked.connect(self.unselect_all_videos)
        options_layout.addWidget(self.unselect_all_btn)
        
        # Nút Delete Selected
        self.delete_selected_btn = QPushButton(self.tr_("BUTTON_DELETE_SELECTED"))
        self.delete_selected_btn.setFixedWidth(150)
        self.delete_selected_btn.clicked.connect(self.delete_selected_videos)
        options_layout.addWidget(self.delete_selected_btn)
        
        # Nút Delete All
        self.delete_all_btn = QPushButton(self.tr_("BUTTON_DELETE_ALL"))
        self.delete_all_btn.setFixedWidth(150)
        self.delete_all_btn.clicked.connect(self.delete_all_videos)
        options_layout.addWidget(self.delete_all_btn)

        # Nút Download
        self.download_btn = QPushButton(self.tr_("BUTTON_DOWNLOAD"))
        self.download_btn.setFixedWidth(150)
        self.download_btn.clicked.connect(self.download_videos)
        options_layout.addWidget(self.download_btn)

        main_layout.addLayout(options_layout)

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
        self.video_table.setColumnWidth(5, 70)
        
        self.video_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Size
        self.video_table.setColumnWidth(6, 80)
        
        # Bỏ cột Caption (index 7)
        
        self.video_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Hashtags 
        self.video_table.setColumnWidth(7, 180)
        
        # Thiết lập số dòng ban đầu
        self.video_table.setRowCount(0)
        
        # Kết nối sự kiện double-click để hiển thị dialog copy text
        self.video_table.itemDoubleClicked.connect(self.show_copy_dialog)

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
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("DIALOG_NO_VIDEOS"))
            return

        # Xóa dữ liệu cũ trong bảng và dict
        self.video_table.setRowCount(0)
        self.video_info_dict.clear()
        
        # Kiểm tra xem đã thiết lập thư mục đầu ra chưa
        if not self.output_folder_display.text():
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("DIALOG_NO_OUTPUT_FOLDER"))
            return
        
        # Xử lý nhiều URL (ngăn cách bằng khoảng trắng)
        urls = url.split()
        
        # Đặt lại biến đếm
        self.processing_count = len(urls)
        
        # Disable button Get Info khi đang lấy thông tin
        self.get_info_btn.setEnabled(False)
        self.get_info_btn.setText(self.tr_("STATUS_GETTING_INFO_SHORT"))
        self.url_input.setEnabled(False)
        
        # Cập nhật trạng thái
        if self.parent:
            # Hiển thị thông báo rõ ràng trên status bar
            if len(urls) > 1:
                self.parent.status_bar.showMessage(self.tr_("STATUS_GETTING_INFO_MULTIPLE").format(len(urls)))
            else:
                self.parent.status_bar.showMessage(self.tr_("STATUS_GETTING_INFO_SHORT"))
        
        # Yêu cầu cập nhật giao diện ngay lập tức để hiển thị thông báo
        QApplication.processEvents()
        
        # Bắt đầu lấy thông tin video từ TikTokDownloader
        for url in urls:
            # Gọi phương thức get_video_info của TikTokDownloader
            # Kết quả sẽ được xử lý bởi on_video_info_received thông qua signal
            self.downloader.get_video_info(url)
            
            # Cập nhật lại giao diện sau mỗi request để đảm bảo UI vẫn responsive
            QApplication.processEvents()

    def delete_row(self, row):
        """Xóa một dòng khỏi bảng"""
        self.video_table.removeRow(row)

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
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_REFRESHED"))

    def download_videos(self):
        """Tải xuống các video được chọn"""
        # Kiểm tra đã chọn thư mục lưu chưa
        if not self.output_folder_display.text():
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("DIALOG_NO_OUTPUT_FOLDER"))
            return
            
        # Kiểm tra thư mục tồn tại
        output_folder = self.output_folder_display.text()
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), 
                        self.tr_("DIALOG_FOLDER_NOT_FOUND").format(output_folder))
                return
                
        # Kiểm tra video đã được thêm vào bảng chưa
        if self.video_table.rowCount() == 0:
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), self.tr_("DIALOG_NO_VIDEOS"))
            return
            
        # Tạo danh sách thông tin chi tiết để tải xuống
        download_queue = []
        videos_already_exist = []
        selected_count = 0
        
        # Duyệt qua từng dòng trong bảng
        for row in range(self.video_table.rowCount()):
            checkbox_cell = self.video_table.cellWidget(row, 0)
            if checkbox_cell:
                checkbox = checkbox_cell.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected_count += 1
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

                    # Làm sạch tên video, loại bỏ hashtag để tạo tên file
                    clean_title = title
                    # Loại bỏ tất cả các hashtag còn sót nếu có
                    import re
                    clean_title = re.sub(r'#\S+', '', clean_title).strip()
                    # Loại bỏ các ký tự không hợp lệ cho tên file
                    clean_title = re.sub(r'[\\/*?:"<>|]', '', clean_title).strip()
                    
                    # Xác định phần mở rộng file dựa trên định dạng
                    is_audio = "audio" in format_id.lower() or "bestaudio" in format_id.lower()
                    ext = "mp3" if is_audio else "mp4"
                    
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
                        # Hiển thị thông báo hỏi người dùng có muốn ghi đè không
                        msg = self.tr_("DIALOG_FILE_EXISTS_MESSAGE").format(f"{clean_title}.{ext}")
                        reply = QMessageBox.question(
                            self, 
                            self.tr_("DIALOG_FILE_EXISTS"),
                            msg,
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                            QMessageBox.StandardButton.No
                        )
                        
                        if reply == QMessageBox.StandardButton.Cancel:
                            # Người dùng chọn hủy, dừng tất cả việc tải xuống
                            if self.parent:
                                self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOAD_CANCELLED"))
                            return
                        
                        elif reply == QMessageBox.StandardButton.No:
                            # Người dùng chọn không ghi đè, bỏ qua video này
                            continue
                        
                        # Nếu chọn Yes, tiếp tục thêm vào hàng đợi tải xuống
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
        self.select_all_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
        self.unselect_all_btn.setText(self.tr_("BUTTON_UNSELECT_ALL"))
        self.delete_selected_btn.setText(self.tr_("BUTTON_DELETE_SELECTED"))
        self.delete_all_btn.setText(self.tr_("BUTTON_DELETE_ALL"))
        self.download_btn.setText(self.tr_("BUTTON_DOWNLOAD"))
        
        # Cập nhật header bảng
        self.update_table_headers()

    def tr_(self, key):
        """Dịch chuỗi dựa trên ngôn ngữ hiện tại"""
        return self.lang_manager.get_text(key)

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
        else:
            # Màu sắc cho light mode
            url_placeholder_color = "#888888"
            url_text_color = "#333333"
            folder_text_color = "#555555"
        
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
        """Xử lý khi nhận được thông tin video"""
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
                title_item.setToolTip(title_text)
                # Tắt khả năng chỉnh sửa
                title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.video_table.setItem(row, 1, title_item)
                
                # Cột Creator (Di chuyển lên vị trí ngay sau Title)
                creator = video_info.creator if hasattr(video_info, 'creator') and video_info.creator else ""
                creator_item = QTableWidgetItem(creator)
                creator_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                creator_item.setToolTip(creator)  # Thêm tooltip khi hover
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
                hashtags_item.setToolTip(hashtags_str)  # Thêm tooltip khi hover
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
                    self.parent.status_bar.showMessage(self.tr_("STATUS_ONE_OF_MULTIPLE_DONE").format(
                        filename,
                        self.downloading_count
                    ))
                else:
                    # Nếu đã tải hết, hiển thị thông báo tải thành công
                    if self.success_downloads > 1:
                        self.parent.status_bar.showMessage(self.tr_("DIALOG_DOWNLOAD_MULTIPLE_SUCCESS").format(self.success_downloads))
                    else:
                        self.parent.status_bar.showMessage(self.tr_("STATUS_DOWNLOAD_SUCCESS_WITH_FILENAME").format(filename))
            
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
                
                # Tạo thông tin tải xuống để thêm vào tab Downloaded Videos
                download_info = {
                    'url': url,
                    'title': video_info.title,  # Đã lọc bỏ hashtag
                    'creator': video_info.creator if hasattr(video_info, 'creator') else "",
                    'quality': quality,
                    'format': format_str,
                    'duration': self.format_duration(video_info.duration) if hasattr(video_info, 'duration') else "Unknown",
                    'filesize': self.estimate_size(video_info.formats) if hasattr(video_info, 'formats') else "Unknown",
                    'filepath': file_path,
                    'download_date': datetime.now().strftime("%Y/%m/%d %H:%M"),
                    'hashtags': [],
                    'description': video_info.caption if hasattr(video_info, 'caption') else "",
                    'status': "Download successful"
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
        """Xóa các video đã chọn"""
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
                # Ưu tiên lấy title gốc nếu có
                if hasattr(video_info, 'original_title') and video_info.original_title:
                    full_text = video_info.original_title
                else:
                    full_text = video_info.title if hasattr(video_info, 'title') else item.text()
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
        dialog.resize(600, 400)  # Đặt kích thước mặc định
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
        
    def copy_to_clipboard(self, text):
        """Copy text vào clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        if self.parent:
            self.parent.status_bar.showMessage(self.tr_("STATUS_COPIED")) 

    # Thêm phương thức mới để chọn tất cả các video
    def select_all_videos(self):
        """Chọn tất cả video trong bảng"""
        for row in range(self.video_table.rowCount()):
            checkbox_cell = self.video_table.cellWidget(row, 0)
            if checkbox_cell:
                checkbox = checkbox_cell.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
        
        # Hiển thị thông báo trên status bar
        if self.parent and self.parent.status_bar:
            self.parent.status_bar.showMessage(self.tr_("STATUS_ALL_VIDEOS_SELECTED"))

    # Thêm phương thức mới để bỏ chọn tất cả các video
    def unselect_all_videos(self):
        """Bỏ chọn tất cả video trong bảng"""
        for row in range(self.video_table.rowCount()):
            checkbox_cell = self.video_table.cellWidget(row, 0)
            if checkbox_cell:
                checkbox = checkbox_cell.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
        
        # Hiển thị thông báo trên status bar
        if self.parent and self.parent.status_bar:
            self.parent.status_bar.showMessage(self.tr_("STATUS_ALL_VIDEOS_UNSELECTED")) 