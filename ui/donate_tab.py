from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QGraphicsDropShadowEffect, QSpacerItem)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QColor, QFont, QCursor
import os
import webbrowser

from localization import get_language_manager

class DonateTab(QWidget):
    """Tab hiển thị thông tin donate"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Khởi tạo quản lý ngôn ngữ
        self.lang_manager = get_language_manager()
        self.init_ui()
        
    def init_ui(self):
        """Khởi tạo giao diện"""
        # Layout chính
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # Container chính với padding
        container = QWidget()
        container.setObjectName("containerWidget")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 15, 20, 10)  # Giảm padding dưới
        container_layout.setSpacing(8)  # Giảm khoảng cách giữa các phần tử
        
        # Tiêu đề
        self.title_label = QLabel(self.tr_("DONATE_TITLE"))
        self.title_label.setObjectName("titleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.title_label)
        
        # Text thông báo
        self.message_label = QLabel(self.tr_("DONATE_DESC"))
        self.message_label.setObjectName("messageLabel")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.message_label)
        
        # Phần trung tâm với QR và nút
        center_frame = QFrame()
        center_frame.setObjectName("centerFrame")
        center_layout = QVBoxLayout(center_frame)
        center_layout.setSpacing(10)  # Giảm khoảng cách giữa QR và nút
        center_layout.setContentsMargins(0, 5, 0, 0)  # Thêm padding trên
        
        # QR code không có đường kẻ dọc
        qr_container = QFrame()
        qr_container.setObjectName("qrContainer")
        qr_container.setFixedSize(150, 150)
        qr_layout = QVBoxLayout(qr_container)
        qr_layout.setContentsMargins(0, 0, 0, 0)
        
        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_label.setObjectName("qrLabel")
        
        try:
            qr_image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "momo_qr.png")
            if os.path.exists(qr_image_path):
                qr_pixmap = QPixmap(qr_image_path)
                qr_pixmap = qr_pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                qr_label.setPixmap(qr_pixmap)
            else:
                print("QR code file not found. Please add 'momo_qr.png' to the 'assets' folder")
        except Exception as e:
            print(f"Could not load QR code: {e}")
            
        qr_layout.addWidget(qr_label)
        center_layout.addWidget(qr_container, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Phần nút với hiệu ứng
        buttons_frame = QFrame()
        buttons_frame.setObjectName("buttonsFrame")
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        # Thêm spacer để căn giữa nút
        buttons_layout.addStretch(1)
        
        # Nút Buy Me A Coffee với thiết kế đẹp
        self.coffee_button = QPushButton(self.tr_("DONATE_COFFEE_LINK"))
        self.coffee_button.setObjectName("coffeeButton")
        self.coffee_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.coffee_button.clicked.connect(lambda: webbrowser.open("https://buymeacoffee.com/shin315"))
        
        buttons_layout.addWidget(self.coffee_button)
        buttons_layout.addStretch(1)
        
        center_layout.addWidget(buttons_frame)
        container_layout.addWidget(center_frame)
        
        # Thêm ít stretch hơn để đỡ lãng phí không gian
        container_layout.addStretch(1)
        
        # Thêm frame container vào layout chính
        main_layout.addWidget(container)
        
    def tr_(self, key):
        """Dịch chuỗi dựa trên ngôn ngữ hiện tại"""
        return self.lang_manager.get_text(key)
        
    def update_language(self):
        """Cập nhật ngôn ngữ cho tất cả các thành phần"""
        # Cập nhật tiêu đề
        if hasattr(self, 'title_label'):
            self.title_label.setText(self.tr_("DONATE_TITLE"))
        
        # Cập nhật thông báo
        if hasattr(self, 'message_label'):
            self.message_label.setText(self.tr_("DONATE_DESC"))
            
        # Cập nhật button
        if hasattr(self, 'coffee_button'):
            self.coffee_button.setText(self.tr_("DONATE_COFFEE_LINK"))
        
    def apply_theme_colors(self, theme):
        """Áp dụng màu sắc theo chủ đề"""
        if theme == "dark":
            # Đảm bảo nền của container là tối
            self.setStyleSheet("""
                #containerWidget {
                    background-color: #2d2d2d;
                }
                #titleLabel {
                    color: #ffffff;
                    font-size: 20px;
                    font-weight: bold;
                    background-color: transparent;
                }
                #messageLabel {
                    color: #e0e0e0;
                    font-size: 13px;
                    line-height: 1.3;
                    background-color: transparent;
                }
                #qrContainer {
                    background-color: white;
                    border-radius: 10px;
                }
                #centerFrame {
                    margin: 5px 0;
                    background-color: transparent;
                }
                #coffeeButton {
                    background-color: #FF813F;
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 18px;
                    font-size: 13px;
                    font-weight: bold;
                    min-width: 140px;
                }
                #coffeeButton:hover {
                    background-color: #FF9B5C;
                }
                #coffeeButton:pressed {
                    background-color: #E57539;
                }
                #buttonsFrame {
                    background-color: transparent;
                }
            """)
            
            # Thêm style cho parent dialog nếu tồn tại
            if self.parent():
                self.parent().setStyleSheet("""
                    background-color: #2d2d2d;
                    color: #ffffff;
                """)
        else:
            # Đảm bảo nền của container là sáng
            self.setStyleSheet("""
                #containerWidget {
                    background-color: #f5f5f5;
                }
                #titleLabel {
                    color: #111111;
                    font-size: 20px;
                    font-weight: bold;
                    background-color: transparent;
                }
                #messageLabel {
                    color: #222222;
                    font-size: 13px;
                    line-height: 1.3;
                    background-color: transparent;
                }
                #qrContainer {
                    background-color: white;
                    border-radius: 10px;
                    border: 1px solid #eeeeee;
                }
                #centerFrame {
                    margin: 5px 0;
                    background-color: transparent;
                }
                #coffeeButton {
                    background-color: #FF813F;
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 18px;
                    font-size: 13px;
                    font-weight: bold;
                    min-width: 140px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                #coffeeButton:hover {
                    background-color: #FF9B5C;
                }
                #coffeeButton:pressed {
                    background-color: #E57539;
                }
                #buttonsFrame {
                    background-color: transparent;
                }
            """)
            
            # Thêm style cho parent dialog nếu tồn tại
            if self.parent():
                self.parent().setStyleSheet("""
                    background-color: #f5f5f5;
                    color: #111111;
                """) 