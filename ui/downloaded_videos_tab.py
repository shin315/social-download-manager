from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableWidget, QHeaderView,
                             QTableWidgetItem, QMessageBox, QFrame, QScrollArea, QApplication, QDialog, QTextEdit, QCheckBox,
                             QMenu)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QCursor, QAction
import os
import subprocess
import math
import unicodedata
from localization import get_language_manager
from utils.db_manager import DatabaseManager
from datetime import datetime
import json
import sqlite3
import re
import logging


class DownloadedVideosTab(QWidget):
    """Tab quản lý các video đã tải xuống"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.lang_manager = get_language_manager()
        self.all_videos = []  # Lưu trữ tất cả các video
        self.filtered_videos = []  # Danh sách video sau khi lọc
        self.selected_video = None  # Video được chọn hiện tại
        self.init_ui()
        self.load_downloaded_videos()
        # Biến cho việc sắp xếp
        self.sort_column = 0  # Mặc định sắp xếp theo cột thứ tự
        self.sort_order = Qt.SortOrder.AscendingOrder  # Mặc định tăng dần
        
        # Kết nối với tín hiệu thay đổi ngôn ngữ từ MainWindow
        if parent and hasattr(parent, 'language_changed'):
            parent.language_changed.connect(self.update_language)
        
        # Áp dụng kiểu màu mặc định theo chế độ tối (có thể được ghi đè sau này)
        self.apply_theme_colors("dark")
            
    def tr_(self, key):
        """Dịch chuỗi dựa trên ngôn ngữ hiện tại"""
        return self.lang_manager.get_text(key)
        
    def update_language(self):
        """Cập nhật ngôn ngữ hiển thị khi thay đổi ngôn ngữ"""
        # Cập nhật tiêu đề và nhãn tìm kiếm
        self.search_label.setText(self.tr_("LABEL_SEARCH"))
        self.search_input.setPlaceholderText(self.tr_("PLACEHOLDER_SEARCH"))
        
        # Cập nhật các nhãn thống kê
        self.update_statistics()  # Sẽ cập nhật trực tiếp các nhãn từ hàm này
        
        # Cập nhật nút Select/Unselect All
        current_text = self.select_toggle_btn.text()
        if current_text == "Select All" or current_text == "Chọn Tất Cả":
            self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
        else:
            self.select_toggle_btn.setText(self.tr_("BUTTON_UNSELECT_ALL"))
        
        # Cập nhật nút Refresh và Delete Selected
        self.refresh_btn.setText(self.tr_("BUTTON_REFRESH"))
        self.delete_selected_btn.setText(self.tr_("BUTTON_DELETE_SELECTED"))
        
        # Cập nhật tiêu đề bảng
        self.update_table_headers()
        
        # Cập nhật nội dung bảng (cần cập nhật lại các nút trong cột Action)
        for row in range(self.downloads_table.rowCount()):
            # Lấy widget ở cột Action
            action_widget = self.downloads_table.cellWidget(row, 9)
            if action_widget:
                # Tìm các nút trong widget
                for child in action_widget.findChildren(QPushButton):
                    # Cập nhật text của nút
                    if child.text() == "Open" or child.text() == "Mở":
                        child.setText(self.tr_("BUTTON_OPEN"))
                    elif child.text() == "Delete" or child.text() == "Xóa":
                        child.setText(self.tr_("BUTTON_DELETE"))
        
        # Refresh lại bảng để đảm bảo mọi thứ được hiển thị đúng
        self.display_videos()
        
    def update_table_headers(self):
        """Cập nhật header của bảng theo ngôn ngữ hiện tại"""
        headers = [
            "",  # Cột Select không có tiêu đề
            self.tr_("HEADER_TITLE"), 
            self.tr_("HEADER_CREATOR"), 
            self.tr_("HEADER_QUALITY"), 
            self.tr_("HEADER_FORMAT"), 
            self.tr_("HEADER_SIZE"), 
            self.tr_("HEADER_STATUS"), 
            self.tr_("HEADER_DATE"), 
            self.tr_("HEADER_HASHTAGS"), 
            self.tr_("HEADER_ACTIONS")
        ]
        self.downloads_table.setHorizontalHeaderLabels(headers)
        
    def update_table_buttons(self):
        """Cập nhật các nút trong bảng"""
        for row in range(self.downloads_table.rowCount()):
            # Lấy widget ở cột Action
            action_widget = self.downloads_table.cellWidget(row, 9)
            if action_widget:
                # Tìm các nút trong widget
                for child in action_widget.findChildren(QPushButton):
                    # Cập nhật theo nội dung hiện tại của nút
                    if "Open" in child.text() or "Mở" in child.text():
                        child.setText(self.tr_("BUTTON_OPEN"))
                    elif "Delete" in child.text() or "Xóa" in child.text():
                        child.setText(self.tr_("BUTTON_DELETE"))

    def init_ui(self):
        # Layout chính
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Phần tìm kiếm
        search_layout = QHBoxLayout()
        
        # Label tìm kiếm
        self.search_label = QLabel(self.tr_("LABEL_SEARCH"))
        search_layout.addWidget(self.search_label)
        
        # Input tìm kiếm
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr_("PLACEHOLDER_SEARCH"))
        self.search_input.textChanged.connect(self.filter_videos)
        search_layout.addWidget(self.search_input, 1)
        
        main_layout.addLayout(search_layout)

        # Bảng video đã tải
        self.create_downloads_table()
        main_layout.addWidget(self.downloads_table)

        # Khu vực hiển thị thông tin chi tiết video
        self.create_video_details_area()
        main_layout.addWidget(self.video_details_frame)
        
        # Ẩn khu vực chi tiết video mặc định
        self.video_details_frame.setVisible(False)

        # Thêm thanh thông tin tổng quát
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 8, 0, 0)  # Tạo khoảng cách với phần trên
        
        # Tạo frame để chứa thống kê với hiệu ứng nổi
        self.stats_frame = QFrame()
        self.stats_frame.setObjectName("statsFrame")
        stats_frame_layout = QHBoxLayout(self.stats_frame)
        stats_frame_layout.setContentsMargins(15, 10, 15, 10)
        
        # Tạo box chứa thông tin thống kê
        stats_box = QHBoxLayout()
        stats_box.setSpacing(20)  # Khoảng cách giữa các thông tin
        
        # Tổng số video
        self.total_videos_label = QLabel(self.tr_("LABEL_TOTAL_VIDEOS").format(0))
        stats_box.addWidget(self.total_videos_label)
        
        # Tổng dung lượng
        self.total_size_label = QLabel(self.tr_("LABEL_TOTAL_SIZE").format("0 MB"))
        stats_box.addWidget(self.total_size_label)
        
        # Lần tải xuống cuối cùng
        self.last_download_label = QLabel(self.tr_("LABEL_LAST_DOWNLOAD").format("N/A"))
        stats_box.addWidget(self.last_download_label)
        
        # Thêm vào layout của frame
        stats_frame_layout.addLayout(stats_box)
        stats_frame_layout.addStretch(1)
        
        # Nút Select/Unselect All
        self.select_toggle_btn = QPushButton(self.tr_("BUTTON_SELECT_ALL"))
        self.select_toggle_btn.clicked.connect(self.toggle_select_all)
        stats_frame_layout.addWidget(self.select_toggle_btn)
        
        # Nút Delete Selected
        self.delete_selected_btn = QPushButton(self.tr_("BUTTON_DELETE_SELECTED"))
        self.delete_selected_btn.clicked.connect(self.delete_selected_videos)
        stats_frame_layout.addWidget(self.delete_selected_btn)
        
        # Nút Refresh
        self.refresh_btn = QPushButton(self.tr_("BUTTON_REFRESH"))
        self.refresh_btn.clicked.connect(self.refresh_downloads)
        stats_frame_layout.addWidget(self.refresh_btn)
        
        # Thêm frame vào layout chính
        stats_layout.addWidget(self.stats_frame)
        main_layout.addLayout(stats_layout)
        
        # Kết nối sự kiện click ra ngoài
        self.downloads_table.viewport().installEventFilter(self)
        
        # Thiết lập context menu cho bảng video đã tải
        self.downloads_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.downloads_table.customContextMenuRequested.connect(self.show_context_menu)

    def create_downloads_table(self):
        """Tạo bảng hiển thị video đã tải xuống"""
        self.downloads_table = QTableWidget()
        self.downloads_table.setColumnCount(10)  # Tăng từ 9 lên 10 (thêm cột Select)
        
        # Thiết lập header
        self.update_table_headers()
        
        # Giảm font size của header
        header_font = self.downloads_table.horizontalHeader().font()
        header_font.setPointSize(8)  # Điều chỉnh kích thước font lên 8pt
        self.downloads_table.horizontalHeader().setFont(header_font)
        
        # Thiết lập độ rộng cho các cột
        self.downloads_table.setColumnWidth(0, 30)   # Select - giảm xuống
        self.downloads_table.setColumnWidth(1, 250)  # Tiêu đề - tăng thêm để ưu tiên hiển thị
        self.downloads_table.setColumnWidth(2, 80)   # Tác giả - giảm xuống
        self.downloads_table.setColumnWidth(3, 70)   # Chất lượng - giảm xuống
        self.downloads_table.setColumnWidth(4, 70)   # Định dạng - giảm để nhường cho Action
        self.downloads_table.setColumnWidth(5, 70)   # Kích thước
        self.downloads_table.setColumnWidth(6, 90)   # Trạng thái - giảm do sẽ thay đổi nội dung
        self.downloads_table.setColumnWidth(7, 110)  # Ngày tải - giảm để nhường cho Action
        self.downloads_table.setColumnWidth(8, 90)   # Hashtags - giảm lại để nhường cho Action
        self.downloads_table.setColumnWidth(9, 140)  # Thao tác - tăng để đủ chỗ hiển thị 2 nút
        
        # Thiết lập thuộc tính bảng
        self.downloads_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Chuyển từ ResizeToContents sang Fixed cho hầu hết các cột
        self.downloads_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Select
        self.downloads_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title - Stretch
        self.downloads_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Creator
        self.downloads_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Quality
        self.downloads_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Format
        self.downloads_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Size
        self.downloads_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Status
        self.downloads_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)  # Date
        self.downloads_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)  # Hashtags
        self.downloads_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)  # Actions
        
        # Vô hiệu hóa việc sắp xếp cho cột Select
        self.downloads_table.horizontalHeader().setSortIndicatorShown(True)
        # Vô hiệu hóa khả năng click để sắp xếp cột Select
        self.downloads_table.horizontalHeader().setSectionsClickable(True)
        
        # Kết nối sự kiện click header để sắp xếp (nhưng sẽ bỏ qua cột Select)
        self.downloads_table.horizontalHeader().sectionClicked.connect(self.sort_table)
        
        # Kết nối sự kiện click dòng để hiển thị thông tin chi tiết
        self.downloads_table.itemClicked.connect(self.show_video_details)
        
        # Kết nối sự kiện double-click để hiển thị dialog copy text
        self.downloads_table.itemDoubleClicked.connect(self.show_copy_dialog)
        
        # Thiết lập sự kiện hover để hiển thị tooltip với text đầy đủ
        self.downloads_table.setMouseTracking(True)
        self.downloads_table.cellEntered.connect(self.show_full_text_tooltip)
        
        # Thiết lập style của bảng với hiệu ứng hover
        self.downloads_table.setStyleSheet("""
            QTableWidget::item:hover {
                background-color: rgba(0, 120, 215, 0.1);
            }
        """)
        
        # Thiết lập số dòng ban đầu
        self.downloads_table.setRowCount(0)

    def create_video_details_area(self):
        """Tạo khu vực hiển thị thông tin chi tiết video"""
        # Tạo frame chứa thông tin chi tiết
        self.video_details_frame = QFrame()
        self.video_details_frame.setFrameShape(QFrame.Shape.NoFrame)  # Bỏ khung
        self.video_details_frame.setMinimumHeight(180)  # Chiều cao tối thiểu
        self.video_details_frame.setMaximumHeight(200)  # Chiều cao tối đa
        
        # Layout cho frame
        details_layout = QHBoxLayout(self.video_details_frame)
        details_layout.setContentsMargins(10, 10, 10, 10)
        details_layout.setSpacing(20)  # Tăng khoảng cách
        
        # Khu vực thumbnail
        self.thumbnail_frame = QFrame()
        self.thumbnail_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.thumbnail_frame.setFixedSize(150, 150)
        
        # Label hiển thị thumbnail
        thumbnail_layout = QVBoxLayout(self.thumbnail_frame)
        thumbnail_layout.setContentsMargins(0, 0, 0, 0)
        
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet("background-color: #292929; border-radius: 8px;")  # Tăng border-radius
        self.thumbnail_label.setFixedSize(150, 150)
        
        # Đặt logo TikTok làm hình mặc định (trong thực tế sẽ là thumbnail thực)
        default_pixmap = QPixmap(150, 150)
        default_pixmap.fill(Qt.GlobalColor.transparent)
        self.thumbnail_label.setPixmap(default_pixmap)
        
        # Icon phát video
        self.play_icon = QLabel(self.thumbnail_label)
        self.play_icon.setStyleSheet("background-color: transparent;")
        self.play_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.play_icon.setText("▶️")  # Unicode play icon
        self.play_icon.setStyleSheet("font-size: 48px; color: white; background-color: transparent;")
        self.play_icon.resize(150, 150)
        
        thumbnail_layout.addWidget(self.thumbnail_label)
        details_layout.addWidget(self.thumbnail_frame)
        
        # Khu vực thông tin chi tiết
        self.info_frame = QFrame()
        self.info_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.info_frame.setStyleSheet("background-color: transparent;")
        
        # Scroll area cho thông tin chi tiết
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("""
            background-color: transparent; 
            border: none;
        """)
        
        # Thiết lập style cho thanh cuộn
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 0.1);
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(80, 80, 80, 0.5);
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(80, 80, 80, 0.7);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # Widget và layout chứa thông tin chi tiết
        info_content = QWidget()
        info_content.setStyleSheet("background-color: transparent;")
        info_layout = QVBoxLayout(info_content)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(10)  # Tăng khoảng cách
        
        # Tiêu đề video
        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #e6e6e6;")  # Tăng font-size
        info_layout.addWidget(self.title_label)
        
        # Layout grid cho các thông tin kỹ thuật
        tech_info_layout = QHBoxLayout()
        tech_info_layout.setSpacing(25)  # Tăng khoảng cách
        
        # Cột 1: Quality, Format, Duration
        tech_col1 = QVBoxLayout()
        tech_col1.setSpacing(8)  # Tăng khoảng cách
        self.quality_label = QLabel()
        self.format_label = QLabel()
        self.duration_label = QLabel()
        
        for label in [self.quality_label, self.format_label, self.duration_label]:
            label.setStyleSheet("color: #b3b3b3; font-size: 13px;")  # Thêm font-size
            tech_col1.addWidget(label)
        
        # Cột 2: Size, Date
        tech_col2 = QVBoxLayout()
        tech_col2.setSpacing(8)  # Tăng khoảng cách
        self.size_label = QLabel()
        self.date_label = QLabel()
        self.status_label = QLabel()
        
        for label in [self.size_label, self.date_label, self.status_label]:
            label.setStyleSheet("color: #b3b3b3; font-size: 13px;")  # Thêm font-size
            tech_col2.addWidget(label)
        
        # Thêm các cột vào layout kỹ thuật
        tech_info_layout.addLayout(tech_col1)
        tech_info_layout.addLayout(tech_col2)
        tech_info_layout.addStretch(1)
        
        info_layout.addLayout(tech_info_layout)
        
        # Hashtags
        self.hashtags_label = QLabel()
        self.hashtags_label.setWordWrap(True)
        self.hashtags_label.setStyleSheet("color: #3897f0; font-size: 13px;")
        info_layout.addWidget(self.hashtags_label)
        
        # Đường dẫn folder
        self.folder_layout = QHBoxLayout()
        folder_icon_label = QLabel("📁")  # Unicode folder icon
        folder_icon_label.setStyleSheet("color: #b3b3b3;")
        self.folder_layout.addWidget(folder_icon_label)
        
        self.folder_label = QLabel()
        self.folder_label.setStyleSheet("color: #b3b3b3; font-size: 12px;")
        self.folder_layout.addWidget(self.folder_label)
        self.folder_layout.addStretch(1)
        
        info_layout.addLayout(self.folder_layout)
        
        # Mô tả
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #cccccc; font-size: 13px;")
        info_layout.addWidget(self.desc_label)
        
        info_layout.addStretch(1)
        
        # Thiết lập widget cho scroll area
        scroll_area.setWidget(info_content)
        
        # Thêm scroll area vào frame
        info_frame_layout = QVBoxLayout(self.info_frame)
        info_frame_layout.setContentsMargins(0, 0, 0, 0)
        info_frame_layout.addWidget(scroll_area)
        
        details_layout.addWidget(self.info_frame, 1)  # Stretch factor 1 để mở rộng

    def eventFilter(self, obj, event):
        """Xử lý sự kiện click ra ngoài video trong bảng"""
        if obj == self.downloads_table.viewport() and event.type() == event.Type.MouseButtonPress:
            item = self.downloads_table.itemAt(event.pos())
            if not item:  # Click vào khoảng trống
                # Ẩn khu vực chi tiết và hiện khu vực donate
                self.video_details_frame.setVisible(False)
                self.selected_video = None
        return super().eventFilter(obj, event)

    def show_video_details(self, item):
        """Hiển thị thông tin chi tiết video khi click vào dòng trong bảng"""
        row = item.row()
        
        # Tính toán index thực tế trong danh sách filtered_videos
        if row >= 0 and row < len(self.filtered_videos):
            video = self.filtered_videos[row]
            self.selected_video = video
            
            # Ẩn khu vực donate và hiện khu vực chi tiết
            self.video_details_frame.setVisible(True)
            
            # Cập nhật tiêu đề
            self.title_label.setText(video[0])  # Tiêu đề video
            
            # Kiểm tra đường dẫn file để xác định đúng chất lượng và định dạng
            filepath = video[8] + '/' + video[0] if video[8] and video[0] else ""
            is_mp3 = filepath and filepath.lower().endswith('.mp3')
            
            # Cập nhật thông tin kỹ thuật
            if is_mp3:
                self.quality_label.setText(f"🔷 {self.tr_('DETAIL_QUALITY')}: 320kbps")
            else:
                self.quality_label.setText(f"🔷 {self.tr_('DETAIL_QUALITY')}: {video[2]}")
            
            # Đảm bảo hiển thị định dạng đúng
            format_value = ""
            if is_mp3:
                format_value = self.tr_("FORMAT_AUDIO_MP3")
            else:
                format_value = video[3]
                if format_value == "1080p" or format_value == "720p" or format_value == "480p" or format_value == "360p" or format_value == "Video (mp4)":
                    format_value = self.tr_("FORMAT_VIDEO_MP4")
                elif format_value == "320kbps" or format_value == "192kbps" or format_value == "128kbps" or format_value == "Audio (mp3)":
                    format_value = self.tr_("FORMAT_AUDIO_MP3")
            self.format_label.setText(f"🎬 {self.tr_('DETAIL_FORMAT')}: {format_value}")
            
            # Kiểm tra file tồn tại và hiển thị status tương ứng
            status_value = video[5]
            if filepath and os.path.exists(filepath):
                status_value = "Successful"
            elif status_value == "Download successful":
                status_value = "Successful"
            self.status_label.setText(f"✅ {self.tr_('DETAIL_STATUS')}: {status_value}")
            
            # Hiển thị duration
            if hasattr(self, 'duration_label'):
                # Kiểm tra xem có thông tin duration trong video hay không (index 10 nếu có)
                if len(video) > 10 and video[10]:
                    duration = video[10]
                else:
                    # Nếu không có thì sử dụng giá trị mặc định
                    duration = "Unknown" 
                self.duration_label.setText(f"⏱️ {self.tr_('DETAIL_DURATION')}: {duration}")
            
            self.size_label.setText(f"💾 {self.tr_('DETAIL_SIZE')}: {video[4]}")
            self.date_label.setText(f"📅 {self.tr_('DETAIL_DOWNLOADED')}: {video[6]}")
            
            # Cập nhật hashtags và đảm bảo có dấu # ở đầu mỗi hashtag
            hashtags = video[7]
            if hashtags and not '#' in hashtags:
                # Nếu là chuỗi các hashtag ngăn cách bằng khoảng trắng mà không có dấu #
                hashtags = ' '.join(['#' + tag.strip() for tag in hashtags.split()])
            self.hashtags_label.setText(hashtags)
            
            # Cập nhật đường dẫn thư mục
            self.folder_label.setText(video[8])
            
            # Cập nhật mô tả
            creator = video[1] if len(video) > 1 else "Unknown"
            self.desc_label.setText(f"Creator: {creator}")
            
            # Cập nhật thumbnail nếu có đường dẫn
            # Reset pixmap trước để đảm bảo trạng thái sạch sẽ
            default_pixmap = QPixmap(150, 150)
            default_pixmap.fill(Qt.GlobalColor.transparent)
            self.thumbnail_label.setPixmap(default_pixmap)
            
            # Thiết lập style mặc định dựa trên loại file
            is_audio = is_mp3 or "MP3" in format_value or "Audio" in video[3] or "mp3" in format_value.lower()
            if is_audio:
                # Nếu là file audio, dùng icon âm nhạc làm mặc định
                self.thumbnail_label.setStyleSheet(f"background-color: {self.theme_colors['audio_background']}; border-radius: 8px;")
                self.play_icon.setText("🎵")  # Unicode music icon
                self.play_icon.setStyleSheet("font-size: 52px; color: white; background-color: transparent;")
                self.play_icon.setVisible(True)  # Luôn hiển thị icon âm nhạc cho file MP3
            else:
                # Nếu là video, dùng icon play làm mặc định
                self.thumbnail_label.setStyleSheet(f"background-color: {self.theme_colors['background']}; border-radius: 8px;")
                self.play_icon.setText("▶️")  # Unicode play icon
                self.play_icon.setStyleSheet("font-size: 52px; color: white; background-color: transparent;")
            
            # Thử tải thumbnail cho cả file mp3 và mp4
            thumbnail_path = video[11] if len(video) > 11 and video[11] else ""
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    print(f"Loading thumbnail from: {thumbnail_path}")
                    pixmap = QPixmap(thumbnail_path)
                    if not pixmap.isNull():
                        print(f"Successfully loaded thumbnail: {thumbnail_path}, size: {pixmap.width()}x{pixmap.height()}")
                        pixmap = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio)
                        self.thumbnail_label.setPixmap(pixmap)
                        # Khi thumbnail load thành công, xóa background color
                        self.thumbnail_label.setStyleSheet("background-color: transparent; border-radius: 8px;")
                        # Ẩn play icon khi có thumbnail
                        self.play_icon.setVisible(False)
                    else:
                        print(f"Failed to load thumbnail: pixmap is null for {thumbnail_path}")
                        self.play_icon.setVisible(True)
                except Exception as e:
                    print(f"Error loading thumbnail: {e} for {thumbnail_path}")
                    self.play_icon.setVisible(True)
            else:
                print(f"No thumbnail or file doesn't exist: {thumbnail_path}")
                self.play_icon.setVisible(True)
                
                # Thử tạo lại thumbnail nếu có đường dẫn video hoặc từ thông tin URL
                video_id = ""
                if len(self.selected_video) > 0:
                    db_manager = DatabaseManager()
                    video_info = db_manager.get_download_by_title(self.selected_video[0])
                    if video_info and 'url' in video_info:
                        try:
                            video_id = video_info['url'].split('/')[-1].split('?')[0]
                        except Exception as e:
                            print(f"Error extracting video ID: {e}")
                
                if video_id:
                    # Tạo thư mục thumbnails nếu chưa có
                    output_folder = video[8] if len(video) > 8 and video[8] else ""
                    if output_folder:
                        thumbnails_dir = os.path.join(output_folder, "thumbnails")
                        if not os.path.exists(thumbnails_dir):
                            try:
                                os.makedirs(thumbnails_dir)
                            except Exception as e:
                                print(f"Error creating thumbnails directory: {e}")
                                return
                        
                        # Đặt đường dẫn thumbnail mới
                        new_thumbnail_path = os.path.join(thumbnails_dir, f"{video_id}.jpg")
                        
                        # Cập nhật đường dẫn thumbnail trong database
                        if video_info:
                            try:
                                # Lấy thông tin hiện tại
                                metadata_str = video_info.get('metadata', '{}')
                                metadata = json.loads(metadata_str) if metadata_str else {}
                                metadata['thumbnail'] = new_thumbnail_path
                                
                                # Cập nhật vào database
                                conn = sqlite3.connect(db_manager.db_path)
                                cursor = conn.cursor()
                                cursor.execute(
                                    "UPDATE downloads SET metadata = ? WHERE title = ?", 
                                    (json.dumps(metadata), video[0])
                                )
                                conn.commit()
                                conn.close()
                                
                                print(f"Updated thumbnail path for {video[0]}")
                                
                                # Tạo thumbnail nếu chưa tồn tại
                                if not os.path.exists(new_thumbnail_path):
                                    # Trong trường hợp thực tế, ở đây sẽ tạo thumbnail từ video
                                    # Nhưng do giới hạn về thời gian, chỉ ghi đường dẫn để làm gốc cho lần tải sau
                                    pass
                            except Exception as e:
                                print(f"Error updating thumbnail in database: {e}")
                        else:
                            print(f"Video info not found for title: {video[0]}")
        else:
            # Không tìm thấy video trong danh sách
            self.video_details_frame.setVisible(False)
            self.selected_video = None

    def filter_videos(self):
        """Lọc video theo từ khóa tìm kiếm"""
        search_text = self.search_input.text().lower()
        
        if not search_text:
            # Nếu không có từ khóa tìm kiếm, hiển thị tất cả
            self.filtered_videos = self.all_videos.copy()
        else:
            # Lọc video theo từ khóa
            self.filtered_videos = []
            for video in self.all_videos:
                title = video[0].lower()  # Title
                hashtags = video[7].lower()  # Hashtags
                description = video[9].lower()  # Description
                
                if search_text in title or search_text in hashtags or search_text in description:
                    self.filtered_videos.append(video)
        
        # Hiển thị lại danh sách
        self.display_videos()

        # Ẩn khu vực chi tiết video khi thay đổi tìm kiếm
        self.video_details_frame.setVisible(False)
        self.selected_video = None

    def load_downloaded_videos(self):
        """Load danh sách video đã tải từ cơ sở dữ liệu"""
        try:
            # Xóa dữ liệu cũ
            self.all_videos = []
            self.filtered_videos = []
            
            # Lấy dữ liệu từ cơ sở dữ liệu
            db_manager = DatabaseManager()
            downloads = db_manager.get_downloads()
            
            if not downloads:
                print("No downloads found in database")
                return
                
            print(f"Loaded {len(downloads)} videos from database")
            
            # Xử lý từng bản ghi tải xuống
            for download in downloads:
                # Xử lý hashtags - đảm bảo hiển thị với dấu #
                hashtags = download.get('hashtags', [])
                if isinstance(hashtags, list):
                    hashtags_str = ' '.join(['#' + tag for tag in hashtags])
                else:
                    # Nếu đã là chuỗi, kiểm tra xem có dấu # không
                    hashtags_str = str(hashtags)
                    if hashtags_str and ' ' in hashtags_str and not '#' in hashtags_str:
                        hashtags_str = ' '.join(['#' + tag.strip() for tag in hashtags_str.split()])
                
                # Đảm bảo giữ đúng thông tin creator
                creator = download.get('creator', 'Unknown')
                if creator == 'Unknown' and download.get('url', ''):
                    # Trích xuất username từ URL nếu không có creator
                    url = download.get('url', '')
                    if '@' in url:
                        creator = url.split('@')[1].split('/')[0]
                
                # Hiển thị status một cách thân thiện
                status = download.get('status', 'Success')
                print(f"DEBUG loading video status initial: {status}")
                if status == 'Success' or status == 'Download successful':
                    status = 'Successful'
                print(f"DEBUG loading video status after conversion: {status}")
                
                # Kiểm tra và cập nhật kích thước file thực tế
                file_path = download.get('filepath', '')
                file_size = download.get('filesize', 'Unknown')
                db_size_updated = False
                
                if file_path and os.path.exists(file_path):
                    try:
                        size_bytes = os.path.getsize(file_path)
                        size_mb = size_bytes / (1024 * 1024)
                        actual_file_size = f"{size_mb:.2f} MB"
                        
                        # Nếu kích thước thực tế khác với giá trị trong DB
                        if actual_file_size != file_size:
                            print(f"File size mismatch for {file_path}. DB: {file_size}, Actual: {actual_file_size}")
                            file_size = actual_file_size
                            # Cập nhật kích thước vào database
                            if 'id' in download:
                                print(f"Updating filesize by ID: {download['id']}")
                                update_success = db_manager.update_download_filesize(download['id'], actual_file_size)
                                db_size_updated = update_success
                            elif 'url' in download and download['url']:
                                print(f"Updating filesize by URL: {download['url']}")
                                update_success = db_manager.update_download_filesize(download['url'], actual_file_size)
                                db_size_updated = update_success
                            else:
                                print(f"Cannot update filesize - no ID or URL found in download info")
                        # Bỏ debug message khi filesize khớp
                    except Exception as e:
                        print(f"Error getting file size: {e}")
                
                # Tạo video info với đầy đủ thông tin
                video_info = [
                    download.get('title', 'Unknown'),            # 0 - Title
                    creator,                                     # 1 - Creator
                    download.get('quality', 'Unknown'),          # 2 - Quality
                    download.get('format', 'Unknown'),           # 3 - Format
                    file_size,                                   # 4 - Size (đã cập nhật)
                    status,                                      # 5 - Status
                    download.get('download_date', 'Unknown'),    # 6 - Date
                    hashtags_str,                                # 7 - Hashtags
                    os.path.dirname(download.get('filepath', '')), # 8 - Folder
                    download.get('description', 'Unknown'),      # 9 - Description
                    download.get('duration', 'Unknown'),         # 10 - Duration
                    download.get('thumbnail', '')                # 11 - Thumbnail
                ]
                self.all_videos.append(video_info)
            
            # Cập nhật danh sách filtered_videos
            self.filtered_videos = self.all_videos.copy()
            
            # Hiển thị danh sách video
            self.display_videos()
            
            # Cập nhật thống kê
            self.update_statistics()
            
            print(f"Loaded {len(self.all_videos)} videos")
            
        except Exception as e:
            print(f"Error loading downloaded videos: {e}")
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ERROR").format(str(e)))

    def display_videos(self):
        """Hiển thị danh sách video"""
        # Xác định số lượng video cần hiển thị
        videos_to_display = self.filtered_videos
        
        # Xóa bảng cũ
        self.downloads_table.setRowCount(0)
        
        # Đặt số dòng của bảng
        self.downloads_table.setRowCount(len(videos_to_display))
        
        for i, video in enumerate(videos_to_display):
            row = i  # Sử dụng index trong filtered_videos làm row
            
            # Cột Select
            select_widget = QWidget()
            select_layout = QHBoxLayout(select_widget)
            select_layout.setContentsMargins(0, 0, 0, 0)
            select_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            checkbox = QCheckBox()
            checkbox.setObjectName(f"select_checkbox_{i}")
            # Kết nối sự kiện stateChanged với hàm checkbox_state_changed
            checkbox.stateChanged.connect(self.checkbox_state_changed)
            select_layout.addWidget(checkbox)
            
            self.downloads_table.setCellWidget(row, 0, select_widget)
            
            # Cột Title
            title_item = QTableWidgetItem(video[0])
            # Ưu tiên sử dụng full title cho tooltip nếu có
            if len(video) > 9 and video[9]:
                title_item.setToolTip(video[9])  # Tooltip với full title
            else:
                title_item.setToolTip(video[0])  # Fallback với title ngắn
            # Tắt khả năng chỉnh sửa
            title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, 1, title_item)
            
            # Cột Creator
            creator_item = QTableWidgetItem(video[1])
            creator_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Tắt khả năng chỉnh sửa
            creator_item.setFlags(creator_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, 2, creator_item)
            
            # Cột Quality
            quality_item = QTableWidgetItem(video[2])
            quality_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Tắt khả năng chỉnh sửa
            quality_item.setFlags(quality_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, 3, quality_item)
            
            # Cột Format
            format_value = video[3]
            # Đảm bảo hiển thị định dạng dưới dạng text đúng (MP4 hoặc MP3)
            if format_value == "1080p" or format_value == "720p" or format_value == "480p" or format_value == "360p" or format_value == "Video (mp4)":
                format_value = self.tr_("FORMAT_VIDEO_MP4")
            elif format_value == "320kbps" or format_value == "192kbps" or format_value == "128kbps" or format_value == "Audio (mp3)":
                format_value = self.tr_("FORMAT_AUDIO_MP3")
            # Nếu là file MP3 nhưng định dạng không đúng, sửa lại
            filepath = os.path.join(video[8], video[0]) if video[8] and video[0] else ""
            if filepath and filepath.lower().endswith('.mp3'):
                format_value = self.tr_("FORMAT_AUDIO_MP3")
            format_item = QTableWidgetItem(format_value)
            format_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Tắt khả năng chỉnh sửa
            format_item.setFlags(format_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, 4, format_item)
            
            # Cột Size
            size_item = QTableWidgetItem(video[4])
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Tắt khả năng chỉnh sửa
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, 5, size_item)
            
            # Cột Status
            status_value = video[5]  
            # Đảm bảo status luôn hiển thị "Successful" nếu file tồn tại
            filepath = os.path.join(video[8], video[0]) if video[8] and video[0] else ""
            if filepath and os.path.exists(filepath):
                status_value = "Successful"
            elif status_value == "Download successful":
                status_value = "Successful"
            status_item = QTableWidgetItem(status_value)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Tắt khả năng chỉnh sửa
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, 6, status_item)
            
            # Cột Date
            date_item = QTableWidgetItem(video[6])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Tắt khả năng chỉnh sửa
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, 7, date_item)
            
            # Cột Hashtags - đảm bảo có dấu #
            hashtags = video[7]
            # Nếu hashtags không có dấu #, thêm vào
            if hashtags and not hashtags.startswith('#'):
                if ' ' in hashtags and not '#' in hashtags:
                    hashtags = ' '.join(['#' + tag.strip() for tag in hashtags.split()])
            
            hashtags_item = QTableWidgetItem(hashtags)
            hashtags_item.setToolTip(hashtags)  # Tooltip khi hover
            # Đặt chế độ text elision (dấu ...) thành false để hiển thị đầy đủ văn bản
            hashtags_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            # Đặt chế độ word wrap để văn bản dài có thể xuống dòng nếu cần
            hashtags_item.setFlags(hashtags_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.downloads_table.setItem(row, 8, hashtags_item)
            
            # Bỏ cột Saved Folder (index 8)
            
            # Cột Action (Nút Open và Delete)
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            
            # Nút Open - mở file thay vì chỉ mở thư mục
            open_btn = QPushButton(self.tr_("BUTTON_OPEN"))
            
            # Xác định đường dẫn đầy đủ của file
            directory_path = video[8]
            title = video[0]
            format_str = video[3]
            
            # Xác định đuôi file từ format_str
            ext = "mp3" if format_str == "MP3" or "mp3" in format_str.lower() else "mp4"
            
            # Tạo đường dẫn đầy đủ
            full_filepath = ""
            if directory_path and title:
                # Tạo đường dẫn file
                possible_filepath = os.path.join(directory_path, f"{title}.{ext}")
                
                # Kiểm tra file có tồn tại không
                if os.path.exists(possible_filepath):
                    full_filepath = possible_filepath
                else:
                    # Nếu file không tồn tại, thử tìm file có tên gần giống
                    try:
                        files = os.listdir(directory_path)
                        best_match = None
                        
                        # Loại bỏ ký tự đặc biệt từ title để so sánh
                        clean_title = title.replace('?', '').replace('!', '').replace(':', '').strip()
                        
                        for file in files:
                            # Chỉ kiểm tra các file MP3 hoặc MP4
                            if file.endswith('.mp3') or file.endswith('.mp4'):
                                file_name = os.path.splitext(file)[0]
                                
                                # Kiểm tra xem title có trong tên file không
                                if clean_title in file_name or file_name in clean_title:
                                    best_match = file
                                    break
                        
                        if best_match:
                            full_filepath = os.path.join(directory_path, best_match)
                        else:
                            # Nếu không tìm thấy file, sử dụng thư mục
                            full_filepath = directory_path
                    except Exception as e:
                        print(f"DEBUG - Error finding file for Open button: {str(e)}")
                        full_filepath = directory_path
            else:
                # Nếu không có đủ thông tin, sử dụng thư mục
                full_filepath = directory_path
                
            # Lưu trữ đường dẫn cho lambda
            final_path = full_filepath if full_filepath else directory_path
            
            # Kết nối nút Open với phương thức open_folder
            open_btn.clicked.connect(lambda checked, path=final_path: self.open_folder(path))
            action_layout.addWidget(open_btn)
            
            # Nút Delete
            delete_btn = QPushButton(self.tr_("BUTTON_DELETE"))
            delete_btn.clicked.connect(lambda checked, idx=i: self.delete_video(idx))
            action_layout.addWidget(delete_btn)
            
            self.downloads_table.setCellWidget(row, 9, action_widget)
        
        # Cập nhật tổng số video hiển thị (chỉ hiển thị tổng số video)
        self.total_videos_label.setText(self.tr_("LABEL_TOTAL_VIDEOS").format(len(self.all_videos)))
        
        # Ẩn khu vực chi tiết video nếu không có video nào được chọn
        if len(videos_to_display) == 0:
            self.video_details_frame.setVisible(False)
            self.selected_video = None

    def open_folder(self, path):
        """
        Mở thư mục chứa video đã tải
        Nếu path là thư mục: mở thư mục đó
        Nếu path là file: mở thư mục chứa file và bôi đen (select) file đó
        """
        print(f"DEBUG - Opening path: '{path}'")
        
        # Xác định xem path là file hay folder
        is_file = os.path.isfile(path)
        folder_path = os.path.dirname(path) if is_file else path
        
        # Kiểm tra thư mục tồn tại
        if not os.path.exists(folder_path):
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), 
                               self.tr_("DIALOG_FOLDER_NOT_FOUND").format(folder_path))
            return
            
        # Mở thư mục và chọn file (nếu là file)
        try:
            if os.name == 'nt':  # Windows
                if is_file and os.path.exists(path):
                    # Mở Explorer và chọn file
                    path = path.replace('/', '\\')  # Đảm bảo đường dẫn đúng định dạng Windows
                    print(f"DEBUG - Using explorer /select,{path}")
                    os.system(f'explorer /select,"{path}"')
                else:
                    # Chỉ mở thư mục
                    os.startfile(folder_path)
            elif os.name == 'darwin':  # macOS
                if is_file and os.path.exists(path):
                    # Mở Finder và chọn file
                    subprocess.run(['open', '-R', path], check=True)
                else:
                    # Chỉ mở thư mục
                    subprocess.run(['open', folder_path], check=True)
            else:  # Linux và các hệ điều hành khác
                # Thử sử dụng các file manager phổ biến trên Linux
                if is_file and os.path.exists(path):
                    # Thử với nautilus (GNOME)
                    try:
                        subprocess.run(['nautilus', '--select', path], check=True)
                    except:
                        try:
                            # Thử với dolphin (KDE)
                            subprocess.run(['dolphin', '--select', path], check=True)
                        except:
                            try:
                                # Thử với thunar (XFCE)
                                subprocess.run(['thunar', path], check=True)
                            except:
                                # Nếu không có file manager nào hoạt động, mở thư mục
                                subprocess.run(['xdg-open', folder_path], check=True)
                else:
                    # Chỉ mở thư mục
                    subprocess.run(['xdg-open', folder_path], check=True)
                    
        except Exception as e:
            print(f"DEBUG - Error opening folder: {str(e)}")
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), 
                               self.tr_("DIALOG_CANNOT_OPEN_FOLDER").format(str(e)))

    def delete_video(self, video_idx):
        """Xóa video đã tải khỏi danh sách"""
        if video_idx < 0 or video_idx >= len(self.filtered_videos):
            return
            
        print(f"Delete video called with index: {video_idx}")
        print(f"Current filtered_videos length: {len(self.filtered_videos)}")
        
        # Lấy thông tin video cần xóa
        video = self.filtered_videos[video_idx]
        title = video[0]
        
        print(f"Attempting to delete video: {title}")
        
        # Hiển thị hộp thoại xác nhận xóa
        reply = QMessageBox.question(
            self, 
            self.tr_("DIALOG_CONFIRM_DELETION"), 
            self.tr_("DIALOG_CONFIRM_DELETE_VIDEO").format(title),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            print("User confirmed deletion")
            
            # Xóa khỏi cơ sở dữ liệu
            try:
                db_manager = DatabaseManager()
                db_manager.delete_download_by_title(title)
            except Exception as e:
                print(f"Error deleting video from database: {e}")
            
            # Xóa khỏi danh sách UI
            video_to_remove = self.filtered_videos[video_idx]
            if video_to_remove in self.all_videos:
                self.all_videos.remove(video_to_remove)
            self.filtered_videos.remove(video_to_remove)
            
            # Cập nhật UI
            self.update_statistics()  # Cập nhật tổng số video và tổng kích thước
            self.display_videos()
            
            # Ẩn khu vực chi tiết nếu video đang được chọn bị xóa
            if self.selected_video == video_to_remove:
                self.video_details_frame.setVisible(False)
                self.selected_video = None
            
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_DELETED").format(title))
        else:
            print("User cancelled deletion")

    def refresh_downloads(self):
        """Làm mới danh sách video đã tải"""
        try:
            # Tải lại danh sách video
            self.load_downloaded_videos()
            
            # Kiểm tra thumbnails cho tất cả video đã tải
            self.check_and_update_thumbnails()
            
            # Ẩn khu vực chi tiết video nếu không có video nào được chọn
            self.video_details_frame.setVisible(False)
            self.selected_video = None
            
            # Cập nhật trạng thái nút Select All/Unselect All
            self.update_select_toggle_button()
            
            # Cập nhật thông báo trong status bar
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_REFRESHED"))
        except Exception as e:
            print(f"Error refreshing downloads: {e}")
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_REFRESH_ERROR"))
    
    def check_and_update_thumbnails(self):
        """Kiểm tra và cập nhật thumbnails cho tất cả video"""
        if not self.all_videos:
            return
            
        db_manager = DatabaseManager()
        for video in self.all_videos:
            # Kiểm tra nếu video có thumbnail path và thumbnail tồn tại
            thumbnail_path = video[11] if len(video) > 11 and video[11] else ""
            if not thumbnail_path or not os.path.exists(thumbnail_path):
                # Tìm video_id từ URL video
                video_info = db_manager.get_download_by_title(video[0])
                if not video_info or 'url' not in video_info:
                    continue
                    
                try:
                    video_id = video_info['url'].split('/')[-1].split('?')[0]
                    
                    # Tạo thư mục thumbnails nếu chưa có
                    thumbnails_dir = os.path.join(video[8], "thumbnails")
                    if not os.path.exists(thumbnails_dir):
                        os.makedirs(thumbnails_dir)
                        
                    # Đặt đường dẫn thumbnail mới
                    new_thumbnail_path = os.path.join(thumbnails_dir, f"{video_id}.jpg")
                    
                    # Cập nhật đường dẫn thumbnail trong database
                    metadata_str = video_info.get('metadata', '{}')
                    metadata = json.loads(metadata_str) if metadata_str else {}
                    metadata['thumbnail'] = new_thumbnail_path
                    
                    # Cập nhật vào database
                    conn = sqlite3.connect(db_manager.db_path)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE downloads SET metadata = ? WHERE title = ?", 
                        (json.dumps(metadata), video[0])
                    )
                    conn.commit()
                    conn.close()
                    
                    print(f"Updated thumbnail path for {video[0]}")
                    
                    # Thử tạo thumbnail từ video hoặc từ TikTok API nếu cần thiết
                    # Ở đây chỉ cập nhật đường dẫn, thumbnail sẽ được tải lại khi cần
                except Exception as e:
                    print(f"Error updating thumbnail for {video[0]}: {e}")

    def add_downloaded_video(self, download_info):
        """Thêm video đã tải xuống vào danh sách"""
        try:
            print(f"DEBUG adding video: Title={download_info.get('title', 'Unknown')}")
            print(f"DEBUG quality={download_info.get('quality', 'Unknown')}, format={download_info.get('format', 'Unknown')}")
            
            # Đảm bảo hashtags có định dạng đúng
            hashtags = download_info.get('hashtags', [])
            if hashtags:
                if isinstance(hashtags, list):
                    hashtags_str = ' '.join(['#' + tag for tag in hashtags])
                else:
                    hashtags_str = str(hashtags)
                    if ' ' in hashtags_str and not '#' in hashtags_str:
                        hashtags_str = ' '.join(['#' + tag.strip() for tag in hashtags_str.split()])
            else:
                hashtags_str = ""
                
            print(f"DEBUG hashtags={hashtags_str}")
            
            # Lấy thông tin creator
            creator = download_info.get('creator', 'Unknown')
            # Nếu creator không có, thử lấy từ URL
            if creator == 'Unknown' and download_info.get('url', ''):
                url = download_info.get('url', '')
                if '@' in url:
                    creator = url.split('@')[1].split('/')[0]
            
            # Hiển thị status một cách thân thiện
            status = download_info.get('status', 'Success')
            print(f"DEBUG loading video status initial: {status}")
            if status == 'Success' or status == 'Download successful':
                status = 'Successful'
            print(f"DEBUG loading video status after conversion: {status}")
            
            # Lọc bỏ hashtag khỏi title nếu chưa được lọc
            title = download_info.get('title', 'Unknown')
            if hashtags and '#' in title:
                # Xóa hashtag và dấu cách thừa
                cleaned_title = re.sub(r'#\S+', '', title).strip()
                # Xóa nhiều dấu cách thành một dấu cách
                cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
                title = cleaned_title
                print(f"DEBUG cleaned title: {title}")
            
            # Kiểm tra và cập nhật kích thước file thực tế
            file_path = download_info.get('filepath', '')
            file_size = download_info.get('filesize', 'Unknown')
            if file_path and os.path.exists(file_path):
                try:
                    size_bytes = os.path.getsize(file_path)
                    size_mb = size_bytes / (1024 * 1024)
                    file_size = f"{size_mb:.2f} MB"
                    # Cập nhật kích thước trong download_info để lưu vào DB
                    download_info['filesize'] = file_size
                    print(f"Updated file size for {file_path}: {file_size}")
                except Exception as e:
                    print(f"Error getting file size: {e}")
            
            # Tạo video info với đầy đủ thông tin
            video_info = [
                title,                                           # 0 - Title (đã lọc bỏ hashtag)
                creator,                                         # 1 - Creator
                download_info.get('quality', 'Unknown'),         # 2 - Quality
                download_info.get('format', 'Unknown'),          # 3 - Format
                file_size,                                       # 4 - Size (đã cập nhật)
                status,                                          # 5 - Status
                download_info.get('download_date', 'Unknown'),   # 6 - Date
                hashtags_str,                                    # 7 - Hashtags
                os.path.dirname(download_info.get('filepath', '')), # 8 - Folder
                download_info.get('description', 'Unknown'),     # 9 - Description
                download_info.get('duration', 'Unknown'),        # 10 - Duration
                download_info.get('thumbnail', '')               # 11 - Thumbnail
            ]
            
            # Thêm video mới vào đầu danh sách thay vì cuối danh sách
            self.all_videos.insert(0, video_info)
            
            # Thêm video mới vào cơ sở dữ liệu
            try:
                db_manager = DatabaseManager()
                db_manager.add_download(download_info)
            except Exception as db_error:
                print(f"Error adding video to database: {db_error}")
            
            # Cập nhật danh sách filtered_videos
            if self.search_input.text():
                # Lọc video mới theo từ khóa hiện tại
                search_text = self.search_input.text().lower()
                title = download_info.get('title', '').lower()
                if search_text in title or search_text in hashtags_str.lower():
                    # Thêm vào đầu danh sách
                    self.filtered_videos.insert(0, video_info)
            else:
                # Nếu không có từ khóa tìm kiếm, thêm trực tiếp vào đầu danh sách
                self.filtered_videos.insert(0, video_info)
            
            # Hiển thị lại danh sách
            self.display_videos()
            
            # Cập nhật thông tin thống kê
            self.update_statistics()
            
            # Thông báo
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEO_ADDED"))
                
            return True
        except Exception as e:
            print(f"Error adding downloaded video: {e}")
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ADD_VIDEO_ERROR"))
            return False

    def update_statistics(self):
        """Cập nhật các thông tin thống kê"""
        # Cập nhật tổng số video
        count = len(self.all_videos) if hasattr(self, 'all_videos') else 0
        self.total_videos_label.setText(self.tr_("LABEL_TOTAL_VIDEOS").format(count))
        
        # Cập nhật các thông tin thống kê khác
        if hasattr(self, 'all_videos') and self.all_videos:
            # Tính tổng dung lượng
            try:
                total_size = sum(float(video[4].replace('MB', '').strip()) for video in self.all_videos if isinstance(video[4], str) and 'MB' in video[4])
                self.total_size_label.setText(self.tr_("LABEL_TOTAL_SIZE").format(f"{total_size:.2f} MB"))
            except (ValueError, IndexError):
                self.total_size_label.setText(self.tr_("LABEL_TOTAL_SIZE").format("0 MB"))
            
            # Lần tải xuống cuối cùng
            try:
                self.last_download_label.setText(self.tr_("LABEL_LAST_DOWNLOAD").format(self.all_videos[-1][6]))
            except (IndexError, TypeError):
                self.last_download_label.setText(self.tr_("LABEL_LAST_DOWNLOAD").format("N/A"))
        else:
            # Cập nhật các thông tin khi không có video
            self.total_size_label.setText(self.tr_("LABEL_TOTAL_SIZE").format("0 MB"))
            self.last_download_label.setText(self.tr_("LABEL_LAST_DOWNLOAD").format("N/A"))

    def apply_theme_colors(self, theme):
        """Áp dụng màu sắc theo chủ đề"""
        if theme == "dark":
            # Dark theme
            # Màu sắc cho dark mode
            title_color = "#e6e6e6"
            label_color = "#b3b3b3"
            desc_color = "#cccccc"
            hashtag_color = "#3897f0"
            background_color = "#292929"
            audio_background = "#7952b3"
            details_frame_style = "background-color: #2d2d2d;"
            icon_color = "#b3b3b3"
            
            # Style cho stats frame - dark mode
            stats_frame_style = """
                #statsFrame {
                    background-color: #2d2d2d;
                    border-radius: 8px;
                    padding: 8px;
                    margin-top: 8px;
                    border: 1px solid #444444;
                    box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.3);
                }
                #statsFrame QLabel {
                    color: #dddddd;
                    font-weight: 500;
                }
                #statsFrame QPushButton {
                    background-color: #0078d7;
                    color: #ffffff;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 4px;
                }
                #statsFrame QPushButton:hover {
                    background-color: #0086f0;
                }
                #statsFrame QPushButton:pressed {
                    background-color: #0067b8;
                }
            """
            
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
            # Light theme
            # Màu sắc cho light mode
            title_color = "#000000"
            label_color = "#555555"
            desc_color = "#333333"
            hashtag_color = "#0078d7"
            background_color = "#d8d8d8"
            audio_background = "#9966cc"
            details_frame_style = "background-color: #f5f5f5;"
            icon_color = "#555555"
            
            # Style cho stats frame - light mode
            stats_frame_style = """
                #statsFrame {
                    background-color: #f5f5f5;
                    border-radius: 8px;
                    padding: 5px;
                    border: 1px solid #dddddd;
                }
                #statsFrame QLabel {
                    font-weight: 500;
                }
            """
            
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
        self.downloads_table.setStyleSheet(table_style)
        
        # Áp dụng style cho thanh cuộn
        self.setStyleSheet(scrollbar_style)
        
        # Áp dụng màu sắc cho stats frame
        if hasattr(self, 'stats_frame'):
            self.stats_frame.setStyleSheet(stats_frame_style)
        
        # Áp dụng màu sắc cho các thành phần khác...
        if hasattr(self, 'video_details_frame'):
            self.video_details_frame.setStyleSheet(details_frame_style)
        
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {title_color};")
            
        if hasattr(self, 'quality_label') and hasattr(self, 'format_label') and hasattr(self, 'duration_label'):
            for label in [self.quality_label, self.format_label, self.duration_label,
                          self.size_label, self.date_label, self.status_label]:
                label.setStyleSheet(f"color: {label_color}; font-size: 13px;")
            
        if hasattr(self, 'hashtags_label'):
            self.hashtags_label.setStyleSheet(f"color: {hashtag_color}; font-size: 13px;")
            
        if hasattr(self, 'folder_label'):
            self.folder_label.setStyleSheet(f"color: {label_color}; font-size: 12px;")
            
        # Cập nhật màu cho biểu tượng thư mục
        if hasattr(self, 'folder_layout'):
            for i in range(self.folder_layout.count()):
                item = self.folder_layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QLabel) and "📁" in item.widget().text():
                    item.widget().setStyleSheet(f"color: {icon_color};")
            
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"color: {desc_color}; font-size: 13px;")
            
        if hasattr(self, 'thumbnail_label'):
            self.thumbnail_label.setStyleSheet(f"background-color: {background_color}; border-radius: 8px;")
        
        # Lưu trữ các màu để sử dụng khi hiển thị chi tiết video
        self.theme_colors = {
            "background": background_color,
            "audio_background": audio_background
        }

    def update_selected_video_details(self, video):
        """Cập nhật thông tin chi tiết video được chọn"""
        if not video:
            self.video_details_frame.setVisible(False)
            return
        
        self.selected_video = video
        self.video_details_frame.setVisible(True)
        
        # Cập nhật tiêu đề
        self.title_label.setText(video[0])  # Tiêu đề
        
        # Cập nhật thông tin kỹ thuật
        self.quality_label.setText(f"{self.tr_('DETAIL_QUALITY')}: {video[2]}")  # Chất lượng
        self.format_label.setText(f"{self.tr_('DETAIL_FORMAT')}: {video[3]}")  # Định dạng
        self.size_label.setText(f"{self.tr_('DETAIL_SIZE')}: {video[4]}")  # Kích thước
        self.date_label.setText(f"{self.tr_('DETAIL_DOWNLOADED')}: {video[6]}")  # Ngày tải
        self.status_label.setText(f"✅ {self.tr_('DETAIL_STATUS')}: {video[5]}")  # Trạng thái
        
        # Cập nhật hashtags - Đảm bảo hiển thị đúng
        hashtags = video[7]
        # Kiểm tra xem đã có dấu # chưa, nếu chưa có thì thêm vào
        if hashtags and not hashtags.startswith('#'):
            # Nếu là chuỗi các hashtag ngăn cách bằng khoảng trắng mà không có dấu #
            if ' ' in hashtags and not '#' in hashtags:
                hashtags = ' '.join(['#' + tag.strip() for tag in hashtags.split()])
        self.hashtags_label.setText(hashtags)  # Hashtags
        
        # Cập nhật đường dẫn folder
        self.folder_label.setText(video[8])  # Thư mục

        # Cập nhật tác giả
        creator = video[1] if len(video) > 1 else "Unknown"
        self.desc_label.setText(f"Creator: {creator}")
        
        # Nếu ảnh thumbnail có sẵn, hiển thị
        if hasattr(self, 'thumbnail_label') and hasattr(video, 'thumbnail'):
            try:
                pixmap = QPixmap()
                if pixmap.loadFromData(video.thumbnail):
                    pixmap = pixmap.scaled(280, 157, Qt.AspectRatioMode.KeepAspectRatio)
                    self.thumbnail_label.setPixmap(pixmap)
                    self.thumbnail_label.setVisible(True)
            except Exception as e:
                print(f"Error loading thumbnail: {e}")
                self.thumbnail_label.setVisible(False)

    def sort_table(self, column):
        """Sắp xếp bảng theo cột được click"""
        # Xác định đúng column mapping để khớp với index trong self.filtered_videos
        # Thứ tự cột hiển thị và index trong filtered_videos có thể khác nhau
        column_mapping = {
            0: 0,  # Select (không sắp xếp)
            1: 0,  # Title (index 0 trong filtered_videos)
            2: 1,  # Creator (index 1 trong filtered_videos)
            3: 2,  # Quality (index 2 trong filtered_videos)
            4: 3,  # Format (index 3 trong filtered_videos)
            5: 4,  # Size (index 4 trong filtered_videos)
            6: 5,  # Status (index 5 trong filtered_videos)
            7: 6,  # Date (index 6 trong filtered_videos)
            8: 7,  # Hashtags (index 7 trong filtered_videos)
            9: 8   # Action (không sắp xếp)
        }
        
        # Chỉ cho phép sắp xếp các cột: Title(1), Creator(2), Quality(3), Format(4), Size(5), Date(7)
        # Bỏ qua các cột khác: Select(0), Status(6), Hashtags(8), Actions(9)
        sortable_columns = [1, 2, 3, 4, 5, 7]
        if column not in sortable_columns:
            return
            
        # Map column UI sang column data
        data_column = column_mapping[column]
            
        # Đảo chiều sắp xếp nếu click vào cùng một cột
        if self.sort_column == column:
            self.sort_order = Qt.SortOrder.DescendingOrder if self.sort_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        else:
            self.sort_column = column
            self.sort_order = Qt.SortOrder.AscendingOrder
        
        # Sắp xếp danh sách video với column đã được map
        self.sort_videos(data_column)
        
        # Hiển thị lại danh sách
        self.display_videos()

    def sort_videos(self, column):
        """Sắp xếp danh sách video theo cột"""
        def get_sort_key(video):
            value = video[column]
            
            if column == 2:  # Quality
                # Chuyển đổi quality thành số để sắp xếp
                quality_order = {
                    "1080p": 10,
                    "720p": 9,
                    "480p": 8,
                    "360p": 7,
                    "320kbps": 3,  # Audio quality
                    "192kbps": 2,
                    "128kbps": 1,
                    "Unknown": 0
                }
                return quality_order.get(value, 0)
            
            elif column == 3:  # Format
                # Sắp xếp format (MP4 trước, MP3 sau)
                format_order = {
                    "MP4": 1,
                    "MP3": 2,
                    "Video (mp4)": 1,  # Cho tương thích ngược
                    "Audio (mp3)": 2,  # Cho tương thích ngược
                    "Unknown": 3
                }
                return format_order.get(value, 3)
                
            elif column == 4:  # Size
                try:
                    # Chuyển đổi MB, KB thành số
                    if 'MB' in value:
                        return float(value.replace('MB', '').strip())
                    elif 'KB' in value:
                        return float(value.replace('KB', '').strip()) / 1024
                    return 0
                except Exception as e:
                    print(f"Error converting size: {e}")
                    return 0
                    
            elif column == 0 or column == 1:  # Title hoặc Creator
                # Chuẩn hóa text trước khi sắp xếp
                try:
                    return unicodedata.normalize('NFKD', value.lower())
                except Exception as e:
                    print(f"Error normalizing text: {e}")
                    return value.lower()
                    
            # Mặc định sắp xếp text không phân biệt hoa thường
            if isinstance(value, str):
                return value.lower()
            return value
        
        # Sắp xếp danh sách
        try:
            self.filtered_videos.sort(key=get_sort_key, reverse=(self.sort_order == Qt.SortOrder.DescendingOrder))
        except Exception as e:
            print(f"Error sorting videos: {e}")

    def show_full_text_tooltip(self, row, column):
        """Hiển thị tooltip với text đầy đủ khi hover chuột vào ô"""
        # Chỉ hiển thị tooltip với các cột có văn bản
        if column in [1, 2, 8]:  # Title, Creator, Hashtags columns
            item = self.downloads_table.item(row, column)
            if item and 0 <= row < len(self.filtered_videos):
                video = self.filtered_videos[row]
                
                # Xử lý tooltip tùy theo loại cột
                if column == 1:  # Title
                    # Nếu có full title thì hiển thị full title, ngược lại hiển thị title ngắn
                    if len(video) > 9 and video[9]:
                        self.downloads_table.setToolTip(video[9])
                    else:
                        self.downloads_table.setToolTip(video[0])
                elif column == 2:  # Creator
                    # Hiển thị tên creator đầy đủ
                    self.downloads_table.setToolTip(f"Creator: {video[1]}")
                elif column == 8:  # Hashtags
                    # Hiển thị hashtags đầy đủ với format hợp lý
                    if video[7]:
                        # Làm sạch dữ liệu hashtags để hiển thị tốt hơn
                        hashtags = video[7]
                        # Chuyển thành dạng danh sách hashtags để dễ đọc
                        if ' ' in hashtags and not all(tag.startswith('#') for tag in hashtags.split()):
                            formatted_hashtags = ' '.join(['#' + tag.strip() if not tag.strip().startswith('#') else tag.strip() 
                                                          for tag in hashtags.split()])
                            self.downloads_table.setToolTip(formatted_hashtags)
                        else:
                            self.downloads_table.setToolTip(hashtags)
                    else:
                        self.downloads_table.setToolTip("No hashtags")
            else:
                self.downloads_table.setToolTip("")
        else:
            self.downloads_table.setToolTip("")

    def show_copy_dialog(self, item):
        """Hiển thị dialog cho phép copy text khi double-click vào ô trong bảng"""
        column = item.column()
        row = item.row()
        
        # Chỉ hiển thị dialog copy cho cột Title (1), Creator (2) và Hashtags (8)
        if column not in [1, 2, 8]:
            return
        
        # Lấy thông tin video đầy đủ từ filtered_videos
        full_text = ""
        if 0 <= row < len(self.filtered_videos):
            video = self.filtered_videos[row]
            
            if column == 1:  # Title
                title = video[0] if len(video) > 0 else ""
                full_title = video[9] if len(video) > 9 and video[9] else title
                
                # Loại bỏ hashtags khỏi title
                # Xóa tất cả các đoạn text bắt đầu bằng # và kết thúc bằng khoảng trắng
                cleaned_full_title = re.sub(r'#\S+\s*', '', full_title).strip()
                # Xóa nhiều dấu cách thành một dấu cách
                cleaned_full_title = re.sub(r'\s+', ' ', cleaned_full_title).strip()
                
                # Chỉ hiển thị full title đã làm sạch, không hiển thị title ngắn ở trên nữa
                full_text = cleaned_full_title
                
            elif column == 2:  # Creator
                full_text = video[1] if len(video) > 1 else ""
            elif column == 8:  # Hashtags
                # Format hashtags để dễ đọc và copy
                if len(video) > 7 and video[7]:
                    hashtags = video[7]
                    # Đảm bảo mỗi hashtag có dấu #
                    if ' ' in hashtags and not all(tag.startswith('#') for tag in hashtags.split()):
                        full_text = ' '.join(['#' + tag.strip() if not tag.strip().startswith('#') else tag.strip() 
                                              for tag in hashtags.split()])
                    else:
                        full_text = hashtags
        else:
            full_text = item.text()  # Fallback to cell text
            
        if not full_text:
            return
            
        # Xác định tiêu đề dialog dựa theo cột
        if column == 1:
            title = self.tr_("HEADER_TITLE")
        elif column == 2:
            title = self.tr_("HEADER_CREATOR")
        else:  # column == 8
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
        self.downloads_table.clearSelection()
        self.downloads_table.clearFocus()
        # Đặt focus về ô tìm kiếm để tránh hiệu ứng bôi đen
        self.search_input.setFocus()
        
    def copy_to_clipboard(self, text):
        """Copy text vào clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        if self.parent:
            self.parent.status_bar.showMessage(self.tr_("STATUS_COPIED")) 

    def delete_selected_videos(self):
        """Xóa các video đã được chọn"""
        selected_indices = []
        
        # Kiểm tra từng dòng trong bảng hiện tại
        for row in range(self.downloads_table.rowCount()):
            # Lấy widget checkbox từ cột đầu tiên
            select_widget = self.downloads_table.cellWidget(row, 0)
            if select_widget:
                checkbox = select_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    # Lấy index thực trong filtered_videos
                    selected_indices.append(row)
        
        # Kiểm tra có video nào được chọn không
        if not selected_indices:
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_NO_VIDEOS_SELECTED"))
            return
        
        # Hiển thị hộp thoại xác nhận trước khi xóa
        count = len(selected_indices)
        reply = QMessageBox.question(
            self, 
            self.tr_("DIALOG_CONFIRM_DELETION"),
            self.tr_("DIALOG_CONFIRM_DELETE_SELECTED").format(count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            print(f"User confirmed deletion of {count} videos")
            db_manager = DatabaseManager()
            deleted_count = 0
            
            # Tạo danh sách các videos cần xóa (để tránh vấn đề index shift khi xóa)
            videos_to_delete = [self.filtered_videos[idx] for idx in selected_indices]
            
            # Xóa từng video trong danh sách
            for video in videos_to_delete:
                title = video[0]
                print(f"Attempting to delete video: {title}")
                
                # Xóa khỏi cơ sở dữ liệu
                try:
                    success = db_manager.delete_download_by_title(title)
                    if success:
                        deleted_count += 1
                        # Xóa khỏi danh sách UI
                        if video in self.all_videos:
                            self.all_videos.remove(video)
                        if video in self.filtered_videos:
                            self.filtered_videos.remove(video)
                        
                        # Ẩn khu vực chi tiết nếu video đang được chọn bị xóa
                        if self.selected_video == video:
                            self.video_details_frame.setVisible(False)
                            self.selected_video = None
                except Exception as e:
                    print(f"Error deleting video from database: {e}")
            
            # Cập nhật UI
            self.update_statistics()
            self.display_videos()
            
            # Hiển thị thông báo
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_VIDEOS_DELETED").format(deleted_count))

    def toggle_select_all(self):
        """Chọn hoặc bỏ chọn tất cả video"""
        # Lấy trạng thái nút hiện tại
        is_select_all = self.select_toggle_btn.text() == self.tr_("BUTTON_SELECT_ALL")
        
        # Lấy danh sách tất cả checkbox
        checkboxes = []
        for row in range(self.downloads_table.rowCount()):
            select_widget = self.downloads_table.cellWidget(row, 0)
            if select_widget:
                checkbox = select_widget.findChild(QCheckBox)
                if checkbox:
                    checkboxes.append(checkbox)
        
        # Tạm thời ngắt kết nối signals để tránh gọi nhiều lần
        for checkbox in checkboxes:
            checkbox.blockSignals(True)
        
        # Thiết lập trạng thái mới cho tất cả checkbox
        for checkbox in checkboxes:
            checkbox.setChecked(is_select_all)
        
        # Kết nối lại signals sau khi cập nhật xong
        for checkbox in checkboxes:
            checkbox.blockSignals(False)
        
        # Cập nhật nút dựa trên hành động đã thực hiện
        if is_select_all:
            self.select_toggle_btn.setText(self.tr_("BUTTON_UNSELECT_ALL"))
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ALL_VIDEOS_SELECTED"))
        else:
            self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
            if self.parent:
                self.parent.status_bar.showMessage(self.tr_("STATUS_ALL_VIDEOS_UNSELECTED"))
                
    def update_select_toggle_button(self):
        """Cập nhật trạng thái nút chọn tất cả dựa trên trạng thái các checkbox"""
        # Kiểm tra xem có video nào trong bảng không
        if self.downloads_table.rowCount() == 0:
            return
            
        # Kiểm tra trạng thái của tất cả checkbox
        all_checked = True
        any_checked = False
        
        for row in range(self.downloads_table.rowCount()):
            select_widget = self.downloads_table.cellWidget(row, 0)
            if select_widget:
                checkbox = select_widget.findChild(QCheckBox)
                if checkbox:
                    if checkbox.isChecked():
                        any_checked = True
                    else:
                        all_checked = False
        
        # Cập nhật trạng thái của nút
        if all_checked:
            self.select_toggle_btn.setText(self.tr_("BUTTON_UNSELECT_ALL"))
        else:
            self.select_toggle_btn.setText(self.tr_("BUTTON_SELECT_ALL"))
            
    def checkbox_state_changed(self):
        """Xử lý khi trạng thái checkbox thay đổi"""
        self.update_select_toggle_button()

    def show_context_menu(self, position):
        """Hiển thị menu chuột phải cho bảng video đã tải"""
        # Lấy vị trí dòng và cột hiện tại
        index = self.downloads_table.indexAt(position)
        if not index.isValid():
            return
            
        row = index.row()
        column = index.column()
        
        if row < 0 or row >= self.downloads_table.rowCount():
            return
        
        # Tạo context menu
        context_menu = QMenu(self)
        
        # Lấy chi tiết video từ filtered_videos
        if row < len(self.filtered_videos):
            video = self.filtered_videos[row]
            
            # Xác định cách truy cập dữ liệu dựa trên kiểu của video
            if isinstance(video, list):
                # Nếu là list, truy cập theo index dựa vào schema [title, creator, quality, format, size, status, date, hashtags, directory, orig_title, duration, thumbnail]
                title = video[0] if len(video) > 0 else ""
                creator = video[1] if len(video) > 1 else ""
                format_str = video[3] if len(video) > 3 else "MP4"  # Default to MP4
                hashtags_raw = video[7] if len(video) > 7 else ""
                directory_path = video[8] if len(video) > 8 else ""
                
                # Xác định filepath dựa vào title và format
                if title and directory_path:
                    ext = "mp3" if format_str == "MP3" else "mp4"
                    filepath = os.path.join(directory_path, f"{title}.{ext}")
                else:
                    filepath = ""
            elif isinstance(video, dict):
                title = video.get('title', '')
                creator = video.get('creator', '')
                hashtags_raw = video.get('hashtags', [])
                filepath = video.get('filepath', '')
            else:
                title = getattr(video, 'title', '')
                creator = getattr(video, 'creator', '')
                hashtags_raw = getattr(video, 'hashtags', [])
                filepath = getattr(video, 'filepath', '')
            
            # Xác định loại dữ liệu dựa vào cột
            if column == 1:  # Title
                # Thêm action Copy Title
                copy_action = QAction(self.tr_("CONTEXT_COPY_TITLE"), self)
                copy_action.triggered.connect(lambda: self.copy_to_clipboard(title))
                context_menu.addAction(copy_action)
            
            elif column == 2:  # Creator
                # Thêm action Copy Creator
                copy_action = QAction(self.tr_("CONTEXT_COPY_CREATOR"), self)
                copy_action.triggered.connect(lambda: self.copy_to_clipboard(creator))
                context_menu.addAction(copy_action)
            
            elif column == 8:  # Hashtags
                # Xử lý hashtags
                hashtags_str = ""
                if isinstance(hashtags_raw, list):
                    hashtags_str = ' '.join([f"#{tag}" for tag in hashtags_raw])
                else:
                    # Nếu là string, giả sử rằng hashtags là một chuỗi đã được định dạng sẵn
                    hashtags_str = hashtags_raw
                
                # Thêm action Copy Hashtags
                copy_action = QAction(self.tr_("CONTEXT_COPY_HASHTAGS"), self)
                copy_action.triggered.connect(lambda: self.copy_to_clipboard(hashtags_str))
                context_menu.addAction(copy_action)
                
            # Chức năng chung cho tất cả các cột
            # Thêm separator nếu có action trước đó
            if not context_menu.isEmpty():
                context_menu.addSeparator()
            
            # Action: Play Video
            play_action = QAction(self.tr_("CONTEXT_PLAY_VIDEO"), self)
            play_action.triggered.connect(lambda: self.play_video(row))
            context_menu.addAction(play_action)
            
            # Action: Open File Location
            if directory_path or filepath:
                # Xác định đường dẫn đầy đủ của file
                full_filepath = ""
                
                if filepath and os.path.exists(filepath):
                    # Nếu đã có đường dẫn đầy đủ và file tồn tại
                    full_filepath = filepath
                elif title and directory_path:
                    # Nếu chỉ có title và directory, tạo đường dẫn file
                    if isinstance(video, list):
                        # Xác định đuôi file từ format_str
                        ext = "mp3" if format_str == "MP3" or "mp3" in format_str.lower() else "mp4"
                        
                        # Tạo đường dẫn file
                        possible_filepath = os.path.join(directory_path, f"{title}.{ext}")
                        
                        # Kiểm tra file có tồn tại không
                        if os.path.exists(possible_filepath):
                            full_filepath = possible_filepath
                        else:
                            # Nếu file không tồn tại, thử tìm file tương tự
                            print(f"DEBUG - File not found: '{possible_filepath}', searching for similar files...")
                            try:
                                # Tìm file có tên tương tự trong thư mục
                                files = os.listdir(directory_path)
                                best_match = None
                                
                                # Xóa bỏ các ký tự đặc biệt và dấu câu từ tên file để so sánh
                                clean_title = title.replace('?', '').replace('!', '').replace(':', '').strip()
                                
                                for file in files:
                                    # Chỉ kiểm tra các file MP3 hoặc MP4
                                    if file.endswith('.mp3') or file.endswith('.mp4'):
                                        # So sánh tên file (không có phần mở rộng) với title
                                        file_name = os.path.splitext(file)[0]
                                        
                                        # Nếu tên file chứa title hoặc ngược lại
                                        if clean_title in file_name or file_name in clean_title:
                                            best_match = file
                                            break
                                
                                if best_match:
                                    full_filepath = os.path.join(directory_path, best_match)
                                    print(f"DEBUG - Found matching file: '{full_filepath}'")
                                else:
                                    # Nếu không tìm thấy file nào, sử dụng thư mục
                                    full_filepath = directory_path
                            except Exception as e:
                                print(f"DEBUG - Error searching for file: {str(e)}")
                                full_filepath = directory_path
                    else:
                        # Mặc định sử dụng thư mục nếu không xác định được file
                        full_filepath = directory_path
                else:
                    # Nếu không có đủ thông tin, sử dụng thư mục
                    full_filepath = directory_path or os.path.dirname(filepath) if filepath else ""
                
                # Nếu vẫn không tìm thấy file, sử dụng thư mục
                if not full_filepath or not os.path.exists(full_filepath):
                    full_filepath = directory_path
                
                # Tạo action và kết nối với sự kiện
                open_folder_action = QAction(self.tr_("CONTEXT_OPEN_LOCATION"), self)
                open_folder_action.triggered.connect(lambda: self.open_folder(full_filepath))
                context_menu.addAction(open_folder_action)
            
            # Thêm separator
            context_menu.addSeparator()
            
            # Action: Delete Video
            delete_action = QAction(self.tr_("CONTEXT_DELETE"), self)
            delete_action.triggered.connect(lambda: self.delete_video(row))
            context_menu.addAction(delete_action)
        
        # Hiển thị menu nếu có action
        if not context_menu.isEmpty():
            context_menu.exec(QCursor.pos())
            
    def play_video(self, row):
        """Phát video đã tải bằng trình phát mặc định của hệ thống"""
        if row < 0 or row >= len(self.filtered_videos):
            return
            
        video = self.filtered_videos[row]
        
        # Log để debug
        print(f"DEBUG - Attempting to play video at row {row}")
        
        # Xác định cách truy cập đường dẫn file dựa trên kiểu của video
        filepath = ""
        title = ""
        directory_path = ""
        
        if isinstance(video, list):
            # Nếu là list, lấy title, format và directory để tạo đường dẫn đầy đủ
            title = video[0] if len(video) > 0 else ""
            format_str = video[3] if len(video) > 3 else "MP4"  # Default to MP4
            directory_path = video[8] if len(video) > 8 else ""
            
            print(f"DEBUG - Video data: title='{title}', format='{format_str}', directory='{directory_path}'")
        elif isinstance(video, dict):
            filepath = video.get('filepath', '')
            title = video.get('title', '')
            directory_path = video.get('directory', '')
            print(f"DEBUG - Dict filepath: '{filepath}'")
        else:
            filepath = getattr(video, 'filepath', '')
            title = getattr(video, 'title', '')
            directory_path = getattr(video, 'directory', '')
            print(f"DEBUG - Object filepath: '{filepath}'")
        
        # Nếu có sẵn filepath đầy đủ
        if filepath and os.path.exists(filepath):
            output_file = filepath
        else:
            # Nếu chưa có filepath, tạo từ directory và title
            if title and directory_path:
                # Chuẩn hóa đường dẫn thư mục
                directory_path = os.path.normpath(directory_path)
                
                # Xử lý tên file để tránh ký tự không hợp lệ trong hệ thống tệp
                safe_title = title.replace('/', '_').replace('\\', '_').replace('?', '')
                
                # Xử lý các trường hợp đuôi file
                ext = ""
                if isinstance(video, list):
                    format_str = video[3] if len(video) > 3 else "MP4"
                    ext = "mp3" if format_str == "MP3" or "mp3" in format_str.lower() else "mp4"
                else:
                    # Dựa vào định dạng của filepath nếu có
                    if filepath and filepath.lower().endswith('.mp3'):
                        ext = "mp3"
                    else:
                        ext = "mp4"  # Mặc định là mp4
                
                # Tạo đường dẫn đầy đủ
                output_file = os.path.join(directory_path, f"{safe_title}.{ext}")
                output_file = os.path.normpath(output_file)
                
                print(f"DEBUG - Generated filepath: '{output_file}'")
            else:
                print(f"DEBUG - Not enough data to generate filepath")
                QMessageBox.warning(
                    self, 
                    self.tr_("DIALOG_ERROR"), 
                    self.tr_("CONTEXT_FILE_NOT_FOUND")
                )
                return
        
        # Kiểm tra file có tồn tại không
        if not os.path.exists(output_file):
            print(f"DEBUG - File not found at '{output_file}', checking for similar files...")
            found_file = False
            
            # Thực hiện tìm kiếm file trong thư mục dựa trên title
            if directory_path and os.path.exists(directory_path):
                try:
                    # Loại bỏ thêm các ký tự không mong muốn để tìm kiếm file dễ hơn
                    search_title = title.replace('?', '').replace('!', '').replace(':', '').strip()
                    
                    # Tạo các biến thể của title để tìm kiếm
                    title_variants = [
                        search_title,
                        search_title.split('#')[0].strip(),  # Bỏ hashtag nếu có
                        ' '.join(search_title.split()[:5]) if len(search_title.split()) > 5 else search_title,  # 5 từ đầu tiên
                        search_title.replace(' ', '_')  # Thay khoảng trắng bằng gạch dưới
                    ]
                    
                    print(f"DEBUG - Searching for title variants: {title_variants}")
                    
                    # Lấy danh sách file trong thư mục
                    files = os.listdir(directory_path)
                    
                    # Tìm file phù hợp nhất
                    best_match = None
                    highest_score = 0
                    
                    for file in files:
                        # Chỉ xét các file mp4 hoặc mp3
                        if file.endswith('.mp4') or file.endswith('.mp3'):
                            file_without_ext = os.path.splitext(file)[0]
                            
                            # Tính điểm tương đồng
                            score = 0
                            for variant in title_variants:
                                if variant in file_without_ext or file_without_ext in variant:
                                    # Nếu chuỗi này nằm trong tên file hoặc ngược lại
                                    score = max(score, len(variant) / max(len(variant), len(file_without_ext)))
                                    if score > 0.8:  # Nếu độ tương đồng > 80%
                                        break
                            
                            if score > highest_score:
                                highest_score = score
                                best_match = file
                    
                    # Nếu tìm được file phù hợp
                    if best_match and highest_score > 0.5:  # Đặt ngưỡng 50% tương đồng
                        output_file = os.path.join(directory_path, best_match)
                        found_file = True
                        print(f"DEBUG - Found matching file with score {highest_score}: '{output_file}'")
                    else:
                        print(f"DEBUG - No good match found. Best match: {best_match} with score {highest_score}")
                        
                    # Nếu không tìm được file phù hợp, thử tìm file bắt đầu bằng một phần của title
                    if not found_file:
                        # Lấy 3 từ đầu tiên của title
                        first_few_words = ' '.join(search_title.split()[:3]) if len(search_title.split()) > 3 else search_title
                        
                        for file in files:
                            if (file.endswith('.mp4') or file.endswith('.mp3')) and file.startswith(first_few_words):
                                output_file = os.path.join(directory_path, file)
                                found_file = True
                                print(f"DEBUG - Found file starting with first few words: '{output_file}'")
                                break
                                
                except Exception as e:
                    print(f"DEBUG - Error while searching for files: {str(e)}")
            
            # Nếu không tìm thấy file nào phù hợp
            if not found_file:
                error_msg = f"{self.tr_('CONTEXT_FILE_NOT_FOUND')}: {title}"
                print(f"DEBUG - {error_msg}")
                QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), error_msg)
                return
        
        # Phát file bằng trình phát mặc định
        try:
            print(f"DEBUG - Playing file: '{output_file}'")
            if os.name == 'nt':  # Windows
                os.startfile(output_file)
            elif os.name == 'posix':  # macOS, Linux
                subprocess.Popen(['xdg-open', output_file])
                
            # Hiển thị thông báo trong status bar
            if self.parent and self.parent.status_bar:
                self.parent.status_bar.showMessage(f"{self.tr_('CONTEXT_PLAYING')}: {os.path.basename(output_file)}")
        except Exception as e:
            error_msg = f"{self.tr_('CONTEXT_CANNOT_PLAY')}: {str(e)}"
            print(f"DEBUG - Error playing file: {error_msg}")
            QMessageBox.warning(self, self.tr_("DIALOG_ERROR"), error_msg)
