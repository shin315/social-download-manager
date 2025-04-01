from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QFrame
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt
from ui.main_window import get_resource_path

class AboutDialog(QDialog):
    """Dialog displaying information about the application"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Social Download Manager")
        self.setFixedSize(400, 340)  # Tăng chiều cao để có không gian cho spacer
        
        # Create layout
        layout = QVBoxLayout()
        layout.setSpacing(10)  # Tăng khoảng cách giữa các widget
        
        # Logo
        logo_layout = QHBoxLayout()
        logo_label = QLabel()
        pixmap = QPixmap(get_resource_path("assets/Logo_new_70x70.png"))
        logo_label.setPixmap(pixmap)
        logo_layout.addStretch()
        logo_layout.addWidget(logo_label)
        logo_layout.addStretch()
        layout.addLayout(logo_layout)
        
        # App name with larger font
        app_name = QLabel("Social Download Manager")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        app_name.setFont(font)
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(app_name)
        
        # Version
        version = QLabel("Version 1.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        
        # Thêm spacer sau phần version
        layout.addSpacing(8)
        
        # Thêm divider line
        divider1 = QFrame()
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setFrameShadow(QFrame.Shadow.Sunken)
        divider1.setLineWidth(1)
        layout.addWidget(divider1)
        
        layout.addSpacing(5)
        
        # Description
        description = QLabel("A simple application to download videos without watermark from multiple platforms.")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(description)
        
        layout.addSpacing(5)  # Thêm khoảng cách
        
        # Features
        features = QLabel("• Download TikTok videos in various formats\n• Manage downloaded videos with detailed information\n• Multi-language support (English & Vietnamese)\n• Dark and Light theme options")
        features.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(features)
        
        # Thêm spacer và divider trước phần developer info
        layout.addSpacing(8)
        
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setFrameShadow(QFrame.Shadow.Sunken)
        divider2.setLineWidth(1)
        layout.addWidget(divider2)
        
        layout.addSpacing(5)
        
        # Developer info
        dev_info = QLabel("Developer: Shin\nEmail: shin315@gmail.com\nGitHub: github.com/shin315/social-download-manager")
        dev_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(dev_info)
        
        # OK button
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.setFixedWidth(100)
        ok_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout) 