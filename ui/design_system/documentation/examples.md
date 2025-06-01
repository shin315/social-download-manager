# Design System Examples

## Complete UI Examples

### Download Manager Interface

```python
from ui.design_system.components import *
from ui.design_system.tokens import initialize_design_system

def create_download_manager():
    """Complete download manager interface example"""
    
    # Initialize design system
    design_system = initialize_design_system()
    
    # Main container
    main_container = QWidget()
    layout = QVBoxLayout(main_container)
    
    # Header card with title and controls
    header_card = CardComponent(title="Social Download Manager")
    header_layout = QHBoxLayout()
    
    # Smart URL input with workflow optimization
    url_container = create_workflow_optimized_widget("download_input")
    
    # Download controls
    controls_layout = QHBoxLayout()
    download_btn = EnhancedButton("Download", "download", primary=True)
    pause_btn = EnhancedButton("Pause", "pause", primary=False)
    cancel_btn = EnhancedButton("Cancel", "close", primary=False)
    
    # Add hover animations
    apply_hover_animations(download_btn, scale=True, glow=True)
    apply_hover_animations(pause_btn, scale=True)
    apply_hover_animations(cancel_btn, scale=True)
    
    controls_layout.addWidget(download_btn)
    controls_layout.addWidget(pause_btn)
    controls_layout.addWidget(cancel_btn)
    
    # Progress card
    progress_card = CardComponent(title="Download Progress", elevation=ElevationLevel.RAISED)
    progress_layout = QVBoxLayout()
    
    # Enhanced progress bar with animations
    progress_bar = EnhancedProgressBar()
    apply_loading_animation(progress_bar, pulse=True)
    
    # Status display
    status_layout = QHBoxLayout()
    status_icon = IconComponent('info', IconSize.SM)
    status_label = QLabel("Ready to download")
    
    status_layout.addWidget(status_icon)
    status_layout.addWidget(status_label)
    
    progress_layout.addWidget(progress_bar)
    progress_layout.addLayout(status_layout)
    progress_card.add_content_layout(progress_layout)
    
    # Queue card with bulk actions
    queue_card = CardComponent(title="Download Queue", elevation=ElevationLevel.SUBTLE)
    queue_layout = QVBoxLayout()
    
    # Bulk actions toolbar
    bulk_toolbar = create_workflow_optimized_widget("bulk_actions_toolbar")
    queue_layout.addWidget(bulk_toolbar)
    
    # Queue list (placeholder)
    queue_list = QLabel("Queue items will appear here...")
    queue_layout.addWidget(queue_list)
    queue_card.add_content_layout(queue_layout)
    
    # Assemble interface
    layout.addWidget(header_card)
    layout.addWidget(url_container)
    layout.addLayout(controls_layout)
    layout.addWidget(progress_card)
    layout.addWidget(queue_card)
    
    return main_container
```

### Settings Panel

```python
def create_settings_panel():
    """Complete settings panel with smart organization"""
    
    container = QWidget()
    layout = QVBoxLayout(container)
    
    # Quick Settings Card
    quick_card = CardComponent(title="Quick Settings", elevation=ElevationLevel.RAISED)
    quick_layout = QVBoxLayout()
    
    # Smart defaults integration
    smart_defaults = SmartDefaults()
    
    # Quality setting with learned preferences
    quality_input = EnhancedInput(
        text="720p",
        label="Default Quality",
        placeholder="Select quality..."
    )
    
    # Output folder with smart suggestions
    folder_input = EnhancedInput(
        text="Downloads/",
        label="Output Folder",
        placeholder="Choose folder..."
    )
    
    # Concurrent downloads
    concurrent_input = EnhancedInput(
        text="3",
        label="Concurrent Downloads",
        validation_type="number"
    )
    
    quick_layout.addWidget(quality_input)
    quick_layout.addWidget(folder_input)
    quick_layout.addWidget(concurrent_input)
    quick_card.add_content_layout(quick_layout)
    
    # Advanced Settings Card
    advanced_card = CardComponent(title="Advanced Settings")
    advanced_layout = QVBoxLayout()
    
    # Retry settings
    retry_input = EnhancedInput("3", "Retry Attempts", validation_type="number")
    timeout_input = EnhancedInput("30", "Timeout (seconds)", validation_type="number")
    
    advanced_layout.addWidget(retry_input)
    advanced_layout.addWidget(timeout_input)
    advanced_card.add_content_layout(advanced_layout)
    
    # Keyboard Shortcuts Card
    shortcuts_card = CardComponent(title="Keyboard Shortcuts")
    shortcuts_layout = QVBoxLayout()
    
    shortcuts_info = [
        ("Ctrl+N", "New Download"),
        ("Ctrl+D", "Start Download"),
        ("Ctrl+P", "Pause Download"),
        ("F1", "Show Help")
    ]
    
    for key, desc in shortcuts_info:
        shortcut_row = QHBoxLayout()
        key_label = QLabel(f"{key}:")
        key_label.setStyleSheet("font-weight: bold;")
        desc_label = QLabel(desc)
        
        shortcut_row.addWidget(key_label)
        shortcut_row.addWidget(desc_label)
        shortcut_row.addStretch()
        
        shortcuts_layout.addLayout(shortcut_row)
    
    shortcuts_card.add_content_layout(shortcuts_layout)
    
    # Save button with success feedback
    save_btn = EnhancedButton("Save Settings", "check", primary=True)
    apply_hover_animations(save_btn, scale=True, glow=True)
    
    # Assemble panel
    layout.addWidget(quick_card)
    layout.addWidget(advanced_card)
    layout.addWidget(shortcuts_card)
    layout.addWidget(save_btn)
    
    return container
```

### Error Handling Example

```python
def setup_error_handling(main_window):
    """Setup comprehensive error handling with user guidance"""
    
    # Initialize error manager
    error_manager = ErrorStateManager(main_window)
    
    # Network error example
    def handle_network_error():
        error_manager.show_error_state(
            error_type="network",
            error_message="Unable to connect to video source",
            recovery_suggestions=[
                "Check your internet connection",
                "Verify the URL is accessible",
                "Try again in a few moments"
            ],
            auto_retry=True
        )
    
    # URL validation error
    def handle_url_error():
        error_manager.show_error_state(
            error_type="url",
            error_message="Invalid or inaccessible video URL",
            recovery_suggestions=[
                "Verify the URL is complete and correct",
                "Check if the video is public",
                "Try copying the URL again"
            ]
        )
    
    # File system error
    def handle_file_error():
        error_manager.show_error_state(
            error_type="file",
            error_message="Cannot save file to specified location",
            recovery_suggestions=[
                "Check available disk space",
                "Verify write permissions",
                "Choose a different output folder"
            ]
        )
    
    return {
        'network': handle_network_error,
        'url': handle_url_error,
        'file': handle_file_error
    }
```

## Component Integration Examples

### Animated Card Grid

```python
def create_animated_card_grid():
    """Grid of cards with staggered animations"""
    
    container = QWidget()
    grid_layout = QGridLayout(container)
    
    # Create cards with different elevations
    cards = []
    for i in range(6):
        card = CardComponent(
            title=f"Video {i+1}",
            elevation=ElevationLevel.SUBTLE
        )
        
        # Add content
        content_layout = QVBoxLayout()
        
        # Thumbnail placeholder
        thumbnail = QLabel("Thumbnail")
        thumbnail.setMinimumSize(160, 90)
        thumbnail.setStyleSheet("background: #f0f0f0; border-radius: 4px;")
        
        # Video info
        title_label = QLabel(f"Amazing Video Title {i+1}")
        duration_label = QLabel("5:30")
        
        content_layout.addWidget(thumbnail)
        content_layout.addWidget(title_label)
        content_layout.addWidget(duration_label)
        
        card.add_content_layout(content_layout)
        
        # Add hover animations
        apply_hover_animations(card, scale=True, elevation=True)
        
        # Position in grid
        row = i // 3
        col = i % 3
        grid_layout.addWidget(card, row, col)
        
        cards.append(card)
    
    return container, cards
```

### Enhanced Form

```python
def create_enhanced_form():
    """Form with validation and smart interactions"""
    
    form_card = CardComponent(title="Download Settings", elevation=ElevationLevel.RAISED)
    form_layout = QVBoxLayout()
    
    # URL input with validation
    url_input = EnhancedInput(
        placeholder="https://youtube.com/watch?v=...",
        label="Video URL",
        validation_type="url"
    )
    
    # Quality selector
    quality_input = EnhancedInput(
        text="720p",
        label="Quality",
        placeholder="Select quality..."
    )
    
    # Output filename
    filename_input = EnhancedInput(
        placeholder="Enter filename...",
        label="Output Filename"
    )
    
    # Auto-fill filename when URL changes
    def on_url_changed():
        url = url_input.text()
        if url:
            smart_defaults = SmartDefaults()
            suggested_name = smart_defaults.suggest_output_path(url)
            filename_input.setText(suggested_name)
    
    url_input.textChanged.connect(on_url_changed)
    
    # Submit button with loading state
    submit_btn = EnhancedButton("Start Download", "download", primary=True)
    
    def on_submit():
        # Validate inputs
        if url_input.validate():
            submit_btn.set_loading_state(True, "Starting...")
            # Simulate processing
            QTimer.singleShot(2000, lambda: submit_btn.set_success_state(True))
        else:
            submit_btn.set_error_state(True)
    
    submit_btn.clicked.connect(on_submit)
    
    # Add animations
    apply_hover_animations(submit_btn, scale=True, glow=True)
    
    # Assemble form
    form_layout.addWidget(url_input)
    form_layout.addWidget(quality_input)
    form_layout.addWidget(filename_input)
    form_layout.addWidget(submit_btn)
    
    form_card.add_content_layout(form_layout)
    
    return form_card
```

## Animation Examples

### Staggered List Animation

```python
def animate_list_items(items, delay=100):
    """Animate list items with staggered timing"""
    
    animation_manager = AnimationManager()
    
    for i, item in enumerate(items):
        # Stagger the start time
        start_delay = i * delay
        
        # Create fade and slide animation
        QTimer.singleShot(start_delay, lambda widget=item: (
            animation_manager.fade_in(widget, duration=300),
            animation_manager.slide_in(widget, 'up', duration=300)
        ))
```

### Loading State Animation

```python
def create_loading_interface():
    """Interface with loading states and animations"""
    
    container = QWidget()
    layout = QVBoxLayout(container)
    
    # Loading cards
    for i in range(3):
        card = CardComponent(title=f"Loading Item {i+1}")
        
        # Shimmer effect for loading content
        content = QLabel("Loading content...")
        apply_loading_animation(content, shimmer=True)
        
        content_layout = QVBoxLayout()
        content_layout.addWidget(content)
        card.add_content_layout(content_layout)
        
        layout.addWidget(card)
    
    return container
```

## Integration with PyQt6

### Custom Widget Integration

```python
class DownloadWidget(QWidget):
    """Custom widget using design system components"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_interactions()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Use design system components
        self.url_input = EnhancedInput(
            placeholder="Enter video URL...",
            label="Video URL",
            validation_type="url"
        )
        
        self.download_btn = EnhancedButton("Download", "download", primary=True)
        self.progress_bar = EnhancedProgressBar()
        
        # Add animations
        apply_hover_animations(self.download_btn, scale=True)
        apply_loading_animation(self.progress_bar, pulse=True)
        
        layout.addWidget(self.url_input)
        layout.addWidget(self.download_btn)
        layout.addWidget(self.progress_bar)
    
    def setup_interactions(self):
        # Setup keyboard shortcuts
        self.shortcuts = KeyboardShortcuts(self)
        self.shortcuts.register_action('start_download', self.start_download)
        
        # Setup smart defaults
        self.smart_defaults = SmartDefaults()
        
        # Connect signals
        self.download_btn.clicked.connect(self.start_download)
        self.url_input.textChanged.connect(self.on_url_changed)
    
    def start_download(self):
        if self.url_input.validate():
            self.download_btn.set_loading_state(True, "Downloading...")
            # Start actual download process
        else:
            self.download_btn.set_error_state(True)
    
    def on_url_changed(self):
        url = self.url_input.text()
        if url:
            # Use smart defaults to suggest quality
            quality = self.smart_defaults.suggest_quality_setting(url)
            # Update UI accordingly
```

## Theme Integration Examples

### Dynamic Theme Switching

```python
def setup_theme_switching(main_window):
    """Setup dynamic theme switching with animations"""
    
    from ui.design_system.themes import ThemeManager
    
    theme_manager = ThemeManager()
    
    # Theme toggle button
    theme_btn = EnhancedButton("", "sun", primary=False)
    
    def toggle_theme():
        current = theme_manager.current_theme
        new_theme = 'dark' if current == 'light' else 'light'
        
        # Animate theme transition
        animation_manager = AnimationManager()
        animation_manager.fade_out(main_window, duration=150)
        
        QTimer.singleShot(150, lambda: (
            theme_manager.apply_theme(new_theme),
            animation_manager.fade_in(main_window, duration=150),
            theme_btn.set_icon('moon' if new_theme == 'dark' else 'sun')
        ))
    
    theme_btn.clicked.connect(toggle_theme)
    apply_hover_animations(theme_btn, scale=True)
    
    return theme_btn
```

For more examples, see the test files in the project root. 