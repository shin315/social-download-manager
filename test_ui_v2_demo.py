#!/usr/bin/env python3
"""
Social Download Manager v2.0 - UI Demo

Standalone demo to test the new design system and UI components
without affecting the stable v1.2.1 version.
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QProgressBar, QSpacerItem, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QPalette

# Add current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import the new design system
try:
    from ui.design_system import (
        get_token_manager, get_theme_manager, 
        StyleManager, ComponentStyler
    )
    from ui.design_system.components import (
        ModernCard, ModernButton, ModernInput,
        IconButton, AnimatedProgressBar
    )
    from ui.design_system.components.icons import IconSet
    DESIGN_SYSTEM_AVAILABLE = True
    print("✅ Design System loaded successfully!")
except ImportError as e:
    print(f"❌ Design System not available: {e}")
    DESIGN_SYSTEM_AVAILABLE = False


class UIV2Demo(QMainWindow):
    """Demo window showcasing v2 UI components and design system"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Social Download Manager v2.0 - UI Demo")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize design system if available
        self.token_manager = None
        self.theme_manager = None
        self.style_manager = None
        
        if DESIGN_SYSTEM_AVAILABLE:
            self.init_design_system()
        
        self.init_ui()
        self.apply_styling()
        
    def init_design_system(self):
        """Initialize the design system components"""
        try:
            self.token_manager = get_token_manager()
            self.theme_manager = get_theme_manager()
            self.style_manager = StyleManager()
            print("✅ Design system components initialized")
        except Exception as e:
            print(f"❌ Failed to initialize design system: {e}")
            DESIGN_SYSTEM_AVAILABLE = False
    
    def init_ui(self):
        """Initialize the demo UI"""
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        self.create_header(main_layout)
        
        # Demo sections in tabs
        self.create_demo_tabs(main_layout)
        
        # Footer
        self.create_footer(main_layout)
    
    def create_header(self, layout):
        """Create demo header"""
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        
        # Title
        title = QLabel("🎨 Social Download Manager v2.0 UI Demo")
        title.setObjectName("demo-title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Subtitle
        subtitle = QLabel("Showcasing the new design system, components, and modern UI")
        subtitle.setObjectName("demo-subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header_widget)
    
    def create_demo_tabs(self, layout):
        """Create tabbed demo sections"""
        self.tab_widget = QTabWidget()
        
        # Design System Demo Tab
        self.tab_widget.addTab(self.create_design_system_tab(), "🎨 Design System")
        
        # Components Demo Tab  
        self.tab_widget.addTab(self.create_components_tab(), "🧩 Components")
        
        # Layout Demo Tab
        self.tab_widget.addTab(self.create_layout_tab(), "📐 Layout")
        
        # Download Demo Tab
        self.tab_widget.addTab(self.create_download_demo_tab(), "⬬ Download Demo")
        
        layout.addWidget(self.tab_widget)
    
    def create_design_system_tab(self):
        """Create design system showcase tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        
        # Design Tokens Section
        tokens_section = self.create_tokens_showcase()
        layout.addWidget(tokens_section)
        
        # Theme Controls
        theme_section = self.create_theme_controls()
        layout.addWidget(theme_section)
        
        # Typography Showcase
        typo_section = self.create_typography_showcase()
        layout.addWidget(typo_section)
        
        layout.addStretch()
        return tab
    
    def create_tokens_showcase(self):
        """Create design tokens showcase"""
        section = QFrame()
        section.setObjectName("demo-section")
        layout = QVBoxLayout(section)
        
        # Section title
        title = QLabel("🎨 Design Tokens")
        title.setObjectName("section-title")
        layout.addWidget(title)
        
        # Color tokens
        if DESIGN_SYSTEM_AVAILABLE and self.token_manager:
            colors_layout = QHBoxLayout()
            
            # Primary colors
            primary_frame = self.create_color_showcase("Primary", [
                "color-brand-primary-500",
                "color-brand-primary-600", 
                "color-brand-primary-700"
            ])
            colors_layout.addWidget(primary_frame)
            
            # Background colors
            bg_frame = self.create_color_showcase("Background", [
                "color-background-primary",
                "color-background-secondary",
                "color-background-tertiary"
            ])
            colors_layout.addWidget(bg_frame)
            
            layout.addLayout(colors_layout)
        else:
            error_label = QLabel("❌ Design tokens not available")
            error_label.setStyleSheet("color: red; font-style: italic;")
            layout.addWidget(error_label)
        
        return section
    
    def create_color_showcase(self, group_name, token_names):
        """Create color showcase for a group"""
        frame = QFrame()
        frame.setObjectName("color-group")
        layout = QVBoxLayout(frame)
        
        # Group title
        title = QLabel(group_name)
        title.setObjectName("color-group-title")
        layout.addWidget(title)
        
        # Color swatches
        for token_name in token_names:
            if self.token_manager:
                try:
                    token = self.token_manager.get_token(token_name)
                    if token:
                        color_widget = self.create_color_swatch(token_name, token.value)
                        layout.addWidget(color_widget)
                except Exception as e:
                    print(f"Could not get token {token_name}: {e}")
        
        return frame
    
    def create_color_swatch(self, name, color_value):
        """Create a color swatch widget"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Color box
        color_box = QLabel()
        color_box.setFixedSize(30, 30)
        color_box.setStyleSheet(f"background-color: {color_value}; border: 1px solid #ccc; border-radius: 4px;")
        
        # Color info
        info_label = QLabel(f"{name}\n{color_value}")
        info_label.setObjectName("color-info")
        
        layout.addWidget(color_box)
        layout.addWidget(info_label)
        layout.addStretch()
        
        return widget
    
    def create_theme_controls(self):
        """Create theme switching controls"""
        section = QFrame()
        section.setObjectName("demo-section")
        layout = QVBoxLayout(section)
        
        title = QLabel("🌓 Theme Controls")
        title.setObjectName("section-title")
        layout.addWidget(title)
        
        # Theme buttons
        buttons_layout = QHBoxLayout()
        
        themes = ["light", "dark", "high-contrast"]
        for theme in themes:
            btn = QPushButton(f"{theme.title()} Theme")
            btn.setObjectName(f"theme-btn-{theme}")
            btn.clicked.connect(lambda checked, t=theme: self.switch_theme(t))
            buttons_layout.addWidget(btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        return section
    
    def create_typography_showcase(self):
        """Create typography showcase"""
        section = QFrame()
        section.setObjectName("demo-section")
        layout = QVBoxLayout(section)
        
        title = QLabel("📝 Typography")
        title.setObjectName("section-title")
        layout.addWidget(title)
        
        # Typography samples
        samples = [
            ("Heading 1", "This is a large heading", "heading-1"),
            ("Heading 2", "This is a medium heading", "heading-2"),
            ("Body Text", "This is regular body text for reading content", "body-text"),
            ("Caption", "This is smaller caption text", "caption-text")
        ]
        
        for label, text, obj_name in samples:
            sample_widget = QWidget()
            sample_layout = QHBoxLayout(sample_widget)
            
            label_widget = QLabel(f"{label}:")
            label_widget.setFixedWidth(100)
            label_widget.setObjectName("typo-label")
            
            text_widget = QLabel(text)
            text_widget.setObjectName(obj_name)
            
            sample_layout.addWidget(label_widget)
            sample_layout.addWidget(text_widget)
            sample_layout.addStretch()
            
            layout.addWidget(sample_widget)
        
        return section
    
    def create_components_tab(self):
        """Create components showcase tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        
        # Modern Components Section
        if DESIGN_SYSTEM_AVAILABLE:
            components_section = self.create_modern_components_showcase()
            layout.addWidget(components_section)
        
        # Standard Components Section
        standard_section = self.create_standard_components_showcase()
        layout.addWidget(standard_section)
        
        layout.addStretch()
        return tab
    
    def create_modern_components_showcase(self):
        """Create modern components showcase"""
        section = QFrame()
        section.setObjectName("demo-section")
        layout = QVBoxLayout(section)
        
        title = QLabel("🆕 Modern Components")
        title.setObjectName("section-title")
        layout.addWidget(title)
        
        # Cards row
        cards_layout = QHBoxLayout()
        try:
            # Create modern cards
            card1 = ModernCard("Download Progress", parent=section)
            card1_layout = QVBoxLayout(card1)
            card1_layout.addWidget(QLabel("TikTok Video Download"))
            
            progress = AnimatedProgressBar()
            progress.setValue(65)
            card1_layout.addWidget(progress)
            
            card2 = ModernCard("Quick Actions", parent=section)
            card2_layout = QVBoxLayout(card2)
            
            # Modern buttons
            btn1 = ModernButton("Primary Action", button_type="primary")
            btn2 = ModernButton("Secondary Action", button_type="secondary")
            card2_layout.addWidget(btn1)
            card2_layout.addWidget(btn2)
            
            cards_layout.addWidget(card1)
            cards_layout.addWidget(card2)
            cards_layout.addStretch()
            
        except Exception as e:
            error_label = QLabel(f"❌ Modern components error: {e}")
            error_label.setStyleSheet("color: red;")
            cards_layout.addWidget(error_label)
        
        layout.addLayout(cards_layout)
        return section
    
    def create_standard_components_showcase(self):
        """Create standard components showcase"""
        section = QFrame()
        section.setObjectName("demo-section")
        layout = QVBoxLayout(section)
        
        title = QLabel("🔧 Standard Components")
        title.setObjectName("section-title")
        layout.addWidget(title)
        
        # Form components
        form_layout = QVBoxLayout()
        
        # Input field
        url_input = QLineEdit()
        url_input.setPlaceholderText("Enter TikTok/YouTube URL...")
        url_input.setObjectName("url-input")
        form_layout.addWidget(QLabel("Video URL:"))
        form_layout.addWidget(url_input)
        
        # Dropdown
        quality_combo = QComboBox()
        quality_combo.addItems(["HD (1080p)", "Standard (720p)", "Mobile (480p)"])
        quality_combo.setObjectName("quality-combo")
        form_layout.addWidget(QLabel("Quality:"))
        form_layout.addWidget(quality_combo)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        download_btn = QPushButton("Download Video")
        download_btn.setObjectName("download-btn")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel-btn")
        
        buttons_layout.addWidget(download_btn)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addStretch()
        
        form_layout.addLayout(buttons_layout)
        layout.addLayout(form_layout)
        
        return section
    
    def create_layout_tab(self):
        """Create layout showcase tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Add placeholder content
        placeholder = QLabel("📐 Layout demos coming soon...\n\nThis will showcase:\n• Grid layouts\n• Responsive design\n• Spacing system")
        placeholder.setObjectName("placeholder-text")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
        layout.addWidget(placeholder)
        layout.addStretch()
        
        return tab
    
    def create_download_demo_tab(self):
        """Create download simulation demo"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        
        # Demo controls
        controls_section = QFrame()
        controls_section.setObjectName("demo-section")
        controls_layout = QVBoxLayout(controls_section)
        
        title = QLabel("⬬ Download Simulation")
        title.setObjectName("section-title")
        controls_layout.addWidget(title)
        
        # URL input
        url_input = QLineEdit()
        url_input.setPlaceholderText("https://www.tiktok.com/@user/video/1234567890")
        url_input.setText("https://www.tiktok.com/@example/video/demo")  # Demo URL
        controls_layout.addWidget(QLabel("Video URL:"))
        controls_layout.addWidget(url_input)
        
        # Download button
        download_btn = QPushButton("🚀 Start Demo Download")
        download_btn.setObjectName("demo-download-btn")
        download_btn.clicked.connect(self.start_demo_download)
        controls_layout.addWidget(download_btn)
        
        layout.addWidget(controls_section)
        
        # Progress section
        self.progress_section = QFrame()
        self.progress_section.setObjectName("demo-section")
        progress_layout = QVBoxLayout(self.progress_section)
        
        progress_title = QLabel("📊 Download Progress")
        progress_title.setObjectName("section-title")
        progress_layout.addWidget(progress_title)
        
        # Progress bar
        self.demo_progress = QProgressBar()
        self.demo_progress.setObjectName("demo-progress")
        self.demo_progress.setValue(0)
        progress_layout.addWidget(self.demo_progress)
        
        # Status text
        self.status_label = QLabel("Ready to download...")
        self.status_label.setObjectName("status-text")
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(self.progress_section)
        layout.addStretch()
        
        return tab
    
    def create_footer(self, layout):
        """Create demo footer"""
        footer = QLabel("Built with ❤️ using PyQt6 and the new Social Download Manager v2.0 Design System")
        footer.setObjectName("demo-footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)
    
    def switch_theme(self, theme_name):
        """Switch to different theme"""
        print(f"🌓 Switching to {theme_name} theme...")
        if DESIGN_SYSTEM_AVAILABLE and self.theme_manager:
            try:
                self.theme_manager.set_current_theme(theme_name)
                self.apply_styling()
                print(f"✅ Theme switched to {theme_name}")
            except Exception as e:
                print(f"❌ Failed to switch theme: {e}")
        else:
            # Fallback styling
            self.apply_fallback_theme(theme_name)
    
    def start_demo_download(self):
        """Start demo download simulation"""
        print("🚀 Starting demo download...")
        self.status_label.setText("Fetching video information...")
        self.demo_progress.setValue(0)
        
        # Simulate download progress
        self.demo_timer = QTimer()
        self.demo_timer.timeout.connect(self.update_demo_progress)
        self.demo_timer.start(200)  # Update every 200ms
        
        self.demo_progress_value = 0
    
    def update_demo_progress(self):
        """Update demo download progress"""
        self.demo_progress_value += 2
        self.demo_progress.setValue(self.demo_progress_value)
        
        # Update status based on progress
        if self.demo_progress_value < 20:
            self.status_label.setText("🔍 Analyzing video URL...")
        elif self.demo_progress_value < 40:
            self.status_label.setText("📡 Fetching video metadata...")
        elif self.demo_progress_value < 70:
            self.status_label.setText("⬬ Downloading video content...")
        elif self.demo_progress_value < 90:
            self.status_label.setText("🎨 Processing video file...")
        elif self.demo_progress_value >= 100:
            self.status_label.setText("✅ Download completed successfully!")
            self.demo_timer.stop()
    
    def apply_styling(self):
        """Apply styling to the demo"""
        if DESIGN_SYSTEM_AVAILABLE and self.style_manager:
            try:
                # Apply design system styling
                self.style_manager.apply_theme_to_widget(self)
                print("✅ Design system styling applied")
            except Exception as e:
                print(f"❌ Failed to apply design system styling: {e}")
                self.apply_fallback_styling()
        else:
            self.apply_fallback_styling()
    
    def apply_fallback_styling(self):
        """Apply fallback styling when design system is not available"""
        print("⚠️ Applying fallback styling...")
        
        # Basic modern styling
        self.setStyleSheet("""
        QMainWindow {
            background-color: #fafafa;
        }
        
        QLabel#demo-title {
            font-size: 24px;
            font-weight: bold;
            color: #1a1a1a;
            margin: 10px 0;
        }
        
        QLabel#demo-subtitle {
            font-size: 14px;
            color: #666666;
            margin-bottom: 20px;
        }
        
        QFrame#demo-section {
            background-color: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            margin: 5px 0;
            padding: 15px;
        }
        
        QLabel#section-title {
            font-size: 16px;
            font-weight: bold;
            color: #333333;
            margin-bottom: 10px;
        }
        
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
        }
        
        QPushButton:hover {
            background-color: #1976D2;
        }
        
        QPushButton:pressed {
            background-color: #0D47A1;
        }
        
        QLineEdit {
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 14px;
        }
        
        QLineEdit:focus {
            border-color: #2196F3;
        }
        
        QComboBox {
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 14px;
        }
        
        QProgressBar {
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            text-align: center;
            height: 20px;
        }
        
        QProgressBar::chunk {
            background-color: #4CAF50;
            border-radius: 4px;
        }
        
        QTabWidget::pane {
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            background-color: white;
        }
        
        QTabBar::tab {
            background-color: #f5f5f5;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }
        
        QTabBar::tab:selected {
            background-color: white;
            border-bottom: 2px solid #2196F3;
        }
        
        QLabel#demo-footer {
            color: #666666;
            font-style: italic;
            margin-top: 20px;
        }
        """)
    
    def apply_fallback_theme(self, theme_name):
        """Apply fallback theme styling"""
        if theme_name == "dark":
            self.setStyleSheet(self.styleSheet().replace("#fafafa", "#2b2b2b")
                              .replace("white", "#3c3c3c")
                              .replace("#1a1a1a", "#ffffff")
                              .replace("#333333", "#ffffff")
                              .replace("#666666", "#cccccc")
                              .replace("#e0e0e0", "#555555"))
        elif theme_name == "high-contrast":
            self.setStyleSheet(self.styleSheet().replace("#2196F3", "#000000")
                              .replace("#1976D2", "#333333")
                              .replace("#4CAF50", "#000000"))


def main():
    """Main demo function"""
    print("🎨 Starting Social Download Manager v2.0 UI Demo...")
    
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Social Download Manager v2.0 Demo")
    app.setApplicationVersion("2.0.0-demo")
    
    # Create and show demo window
    demo = UIV2Demo()
    demo.show()
    
    print("✅ Demo window created and shown")
    print("🎯 Use the tabs to explore different UI features:")
    print("   • Design System: Colors, tokens, themes")
    print("   • Components: Modern UI components")
    print("   • Layout: Layout system (coming soon)")
    print("   • Download Demo: Simulated download process")
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 