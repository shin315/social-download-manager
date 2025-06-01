"""
UX Workflow Optimization

Advanced workflow optimization system that streamlines user workflows,
reduces click counts, implements smart defaults, and improves overall
user experience for common tasks.
"""

import re
from typing import Dict, List, Optional, Callable, Any, Tuple, Union
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QApplication, QMessageBox, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSettings, QUrl
from PyQt6.QtGui import QKeySequence, QDesktopServices, QShortcut

from .enhanced_widgets import EnhancedButton, EnhancedInput, EnhancedProgressBar
from .cards import CardComponent, ElevationLevel
from .icons import IconComponent, IconSize
from ..styles.style_manager import StyleManager


class SmartDefaults:
    """
    Smart defaults system that learns user preferences and provides
    intelligent auto-fill capabilities based on usage patterns.
    """
    
    def __init__(self):
        self.settings = QSettings("SocialDownloadManager", "UserPreferences")
        self.style_manager = StyleManager()
        
        # Track usage patterns
        self.url_patterns: Dict[str, int] = self._load_url_patterns()
        self.file_patterns: Dict[str, int] = self._load_file_patterns()
        self.quality_preferences: Dict[str, int] = self._load_quality_preferences()
        
    def _load_url_patterns(self) -> Dict[str, int]:
        """Load previously used URL patterns"""
        patterns = {}
        size = self.settings.beginReadArray("url_patterns")
        for i in range(size):
            self.settings.setArrayIndex(i)
            pattern = self.settings.value("pattern", "")
            count = self.settings.value("count", 0, int)
            if pattern:
                patterns[pattern] = count
        self.settings.endArray()
        return patterns
    
    def _load_file_patterns(self) -> Dict[str, int]:
        """Load previously used filename patterns"""
        patterns = {}
        size = self.settings.beginReadArray("file_patterns")
        for i in range(size):
            self.settings.setArrayIndex(i)
            pattern = self.settings.value("pattern", "")
            count = self.settings.value("count", 0, int)
            if pattern:
                patterns[pattern] = count
        self.settings.endArray()
        return patterns
    
    def _load_quality_preferences(self) -> Dict[str, int]:
        """Load quality preference history"""
        preferences = {}
        size = self.settings.beginReadArray("quality_preferences")
        for i in range(size):
            self.settings.setArrayIndex(i)
            quality = self.settings.value("quality", "")
            count = self.settings.value("count", 0, int)
            if quality:
                preferences[quality] = count
        self.settings.endArray()
        return preferences
    
    def suggest_output_path(self, video_url: str, video_title: str = "") -> str:
        """
        Suggest optimal output path based on URL and title
        
        Args:
            video_url: Source video URL
            video_title: Video title if available
            
        Returns:
            Suggested output path
        """
        # Extract platform from URL
        platform = self._extract_platform(video_url)
        
        # Clean and format title
        clean_title = self._clean_filename(video_title) if video_title else "video"
        
        # Get most common file extension for this platform
        preferred_extension = self._get_preferred_extension(platform)
        
        # Build suggested path
        suggested_name = f"{clean_title}.{preferred_extension}"
        
        # Apply file pattern learning
        suggested_name = self._apply_file_pattern_learning(suggested_name, platform)
        
        return suggested_name
    
    def suggest_quality_setting(self, video_url: str) -> str:
        """
        Suggest optimal quality setting based on URL and user history
        
        Args:
            video_url: Source video URL
            
        Returns:
            Suggested quality setting
        """
        platform = self._extract_platform(video_url)
        
        # Get most used quality for this platform
        platform_qualities = {k: v for k, v in self.quality_preferences.items() 
                            if platform in k.lower()}
        
        if platform_qualities:
            most_used = max(platform_qualities.items(), key=lambda x: x[1])
            return most_used[0].split('_')[-1]  # Extract quality part
        
        # Default quality preferences by platform
        platform_defaults = {
            'youtube': '1080p',
            'tiktok': '720p',
            'instagram': '720p',
            'default': '720p'
        }
        
        return platform_defaults.get(platform, platform_defaults['default'])
    
    def suggest_download_folder(self, video_url: str) -> str:
        """
        Suggest download folder based on URL and user patterns
        
        Args:
            video_url: Source video URL
            
        Returns:
            Suggested download folder
        """
        platform = self._extract_platform(video_url)
        
        # Get most common folder pattern for this platform
        folder_key = f"folder_{platform}"
        
        if folder_key in self.file_patterns:
            # Use learned folder preference
            folders = [k for k in self.file_patterns.keys() if folder_key in k]
            if folders:
                most_used = max(folders, key=lambda x: self.file_patterns[x])
                return most_used.replace(folder_key + "_", "")
        
        # Default folder structure
        return f"Downloads/{platform.title()}"
    
    def learn_user_choice(self, choice_type: str, value: str, context: str = ""):
        """
        Learn from user choices to improve future suggestions
        
        Args:
            choice_type: Type of choice ('quality', 'folder', 'filename')
            value: User's chosen value
            context: Additional context (e.g., platform)
        """
        key = f"{choice_type}_{context}_{value}" if context else f"{choice_type}_{value}"
        
        if choice_type == "quality":
            self.quality_preferences[key] = self.quality_preferences.get(key, 0) + 1
        elif choice_type in ["folder", "filename"]:
            self.file_patterns[key] = self.file_patterns.get(key, 0) + 1
        
        # Save learning data
        self._save_learning_data()
    
    def _extract_platform(self, url: str) -> str:
        """Extract platform from URL"""
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'tiktok.com' in url:
            return 'tiktok'
        elif 'instagram.com' in url:
            return 'instagram'
        elif 'twitter.com' in url or 'x.com' in url:
            return 'twitter'
        else:
            return 'unknown'
    
    def _clean_filename(self, title: str) -> str:
        """Clean title for safe filename"""
        # Remove invalid filename characters
        cleaned = re.sub(r'[<>:"/\\|?*]', '', title)
        # Replace spaces with underscores
        cleaned = re.sub(r'\s+', '_', cleaned)
        # Limit length
        return cleaned[:50] if len(cleaned) > 50 else cleaned
    
    def _get_preferred_extension(self, platform: str) -> str:
        """Get preferred file extension for platform"""
        platform_extensions = {
            'youtube': 'mp4',
            'tiktok': 'mp4',
            'instagram': 'mp4',
            'twitter': 'mp4',
            'default': 'mp4'
        }
        return platform_extensions.get(platform, platform_extensions['default'])
    
    def _apply_file_pattern_learning(self, suggested_name: str, platform: str) -> str:
        """Apply learned file naming patterns"""
        # Get common patterns for this platform
        platform_patterns = {k: v for k, v in self.file_patterns.items() 
                            if platform in k}
        
        if platform_patterns:
            # Find most common naming pattern
            most_common = max(platform_patterns.items(), key=lambda x: x[1])
            pattern = most_common[0]
            
            # Apply pattern if it makes sense
            if 'prefix_' in pattern:
                prefix = pattern.split('prefix_')[1].split('_')[0]
                suggested_name = f"{prefix}_{suggested_name}"
            elif 'suffix_' in pattern:
                suffix = pattern.split('suffix_')[1].split('_')[0]
                name_parts = suggested_name.rsplit('.', 1)
                suggested_name = f"{name_parts[0]}_{suffix}.{name_parts[1]}"
        
        return suggested_name
    
    def _save_learning_data(self):
        """Save learning data to persistent storage"""
        # Save URL patterns
        self.settings.beginWriteArray("url_patterns")
        for i, (pattern, count) in enumerate(self.url_patterns.items()):
            self.settings.setArrayIndex(i)
            self.settings.setValue("pattern", pattern)
            self.settings.setValue("count", count)
        self.settings.endArray()
        
        # Save file patterns
        self.settings.beginWriteArray("file_patterns")
        for i, (pattern, count) in enumerate(self.file_patterns.items()):
            self.settings.setArrayIndex(i)
            self.settings.setValue("pattern", pattern)
            self.settings.setValue("count", count)
        self.settings.endArray()
        
        # Save quality preferences
        self.settings.beginWriteArray("quality_preferences")
        for i, (quality, count) in enumerate(self.quality_preferences.items()):
            self.settings.setArrayIndex(i)
            self.settings.setValue("quality", quality)
            self.settings.setValue("count", count)
        self.settings.endArray()


class KeyboardShortcuts:
    """
    Comprehensive keyboard shortcuts system for power users
    
    Provides quick access to common actions and workflow optimization.
    """
    
    def __init__(self, parent_widget: QWidget):
        self.parent = parent_widget
        self.shortcuts: Dict[str, QShortcut] = {}
        self.actions: Dict[str, Callable] = {}
        
        self._setup_default_shortcuts()
    
    def _setup_default_shortcuts(self):
        """Set up default keyboard shortcuts"""
        default_shortcuts = {
            # Primary actions
            'Ctrl+N': 'new_download',
            'Ctrl+O': 'open_url',
            'Ctrl+S': 'save_settings',
            'Ctrl+D': 'start_download',
            'Ctrl+P': 'pause_download',
            'Ctrl+R': 'resume_download',
            'Ctrl+Q': 'quit_application',
            
            # Navigation
            'Ctrl+1': 'switch_to_downloads',
            'Ctrl+2': 'switch_to_settings',
            'Ctrl+3': 'switch_to_history',
            'Tab': 'next_field',
            'Shift+Tab': 'previous_field',
            
            # Quick actions
            'F1': 'show_help',
            'F5': 'refresh',
            'F11': 'toggle_fullscreen',
            'Escape': 'cancel_action',
            'Enter': 'confirm_action',
            'Delete': 'remove_selected',
            
            # Bulk operations
            'Ctrl+A': 'select_all',
            'Ctrl+Shift+D': 'download_all',
            'Ctrl+Shift+P': 'pause_all',
            'Ctrl+Shift+C': 'clear_completed',
            
            # Quality shortcuts
            'Alt+1': 'set_quality_720p',
            'Alt+2': 'set_quality_1080p',
            'Alt+3': 'set_quality_1440p',
            'Alt+4': 'set_quality_4k',
        }
        
        for key_combo, action_name in default_shortcuts.items():
            self.add_shortcut(key_combo, action_name)
    
    def add_shortcut(self, key_combination: str, action_name: str, action_func: Optional[Callable] = None):
        """
        Add or update a keyboard shortcut
        
        Args:
            key_combination: Key combination (e.g., 'Ctrl+N')
            action_name: Action identifier
            action_func: Function to call (optional)
        """
        # Remove existing shortcut if it exists
        if action_name in self.shortcuts:
            self.shortcuts[action_name].deleteLater()
        
        # Create new shortcut
        shortcut = QShortcut(QKeySequence(key_combination), self.parent)
        
        if action_func:
            shortcut.activated.connect(action_func)
            self.actions[action_name] = action_func
        
        self.shortcuts[action_name] = shortcut
    
    def register_action(self, action_name: str, action_func: Callable):
        """Register an action function for existing shortcut"""
        self.actions[action_name] = action_func
        
        if action_name in self.shortcuts:
            # Disconnect existing connections
            self.shortcuts[action_name].activated.disconnect()
            # Connect new function
            self.shortcuts[action_name].activated.connect(action_func)
    
    def get_shortcut_help(self) -> List[Tuple[str, str]]:
        """Get list of all shortcuts for help display"""
        shortcut_help = []
        
        for action_name, shortcut in self.shortcuts.items():
            key_sequence = shortcut.key().toString()
            description = self._get_action_description(action_name)
            shortcut_help.append((key_sequence, description))
        
        return sorted(shortcut_help)
    
    def _get_action_description(self, action_name: str) -> str:
        """Get human-readable description for action"""
        descriptions = {
            'new_download': 'Start new download',
            'open_url': 'Open URL input',
            'save_settings': 'Save current settings',
            'start_download': 'Start/resume download',
            'pause_download': 'Pause current download',
            'resume_download': 'Resume paused download',
            'quit_application': 'Quit application',
            'switch_to_downloads': 'Switch to Downloads tab',
            'switch_to_settings': 'Switch to Settings tab',
            'switch_to_history': 'Switch to History tab',
            'next_field': 'Move to next field',
            'previous_field': 'Move to previous field',
            'show_help': 'Show help dialog',
            'refresh': 'Refresh current view',
            'toggle_fullscreen': 'Toggle fullscreen mode',
            'cancel_action': 'Cancel current action',
            'confirm_action': 'Confirm current action',
            'remove_selected': 'Remove selected items',
            'select_all': 'Select all items',
            'download_all': 'Download all queued items',
            'pause_all': 'Pause all downloads',
            'clear_completed': 'Clear completed downloads',
            'set_quality_720p': 'Set quality to 720p',
            'set_quality_1080p': 'Set quality to 1080p',
            'set_quality_1440p': 'Set quality to 1440p',
            'set_quality_4k': 'Set quality to 4K',
        }
        
        return descriptions.get(action_name, action_name.replace('_', ' ').title())


class BulkActions:
    """
    Bulk action system for efficient multi-item operations
    
    Provides batch processing capabilities for common workflows.
    """
    
    def __init__(self, parent_widget: QWidget):
        self.parent = parent_widget
        self.selected_items: List[Any] = []
        self.bulk_operations: Dict[str, Callable] = {}
        
        self._setup_bulk_operations()
    
    def _setup_bulk_operations(self):
        """Set up available bulk operations"""
        self.bulk_operations = {
            'download_all': self._bulk_download,
            'pause_all': self._bulk_pause,
            'resume_all': self._bulk_resume,
            'remove_all': self._bulk_remove,
            'change_quality': self._bulk_change_quality,
            'change_output_folder': self._bulk_change_folder,
            'export_urls': self._bulk_export_urls,
            'import_urls': self._bulk_import_urls,
        }
    
    def set_selected_items(self, items: List[Any]):
        """Set currently selected items for bulk operations"""
        self.selected_items = items
    
    def get_available_operations(self) -> List[str]:
        """Get list of available bulk operations"""
        return list(self.bulk_operations.keys())
    
    def execute_bulk_operation(self, operation_name: str, **kwargs) -> bool:
        """
        Execute bulk operation on selected items
        
        Args:
            operation_name: Name of operation to execute
            **kwargs: Additional arguments for operation
            
        Returns:
            True if operation was successful
        """
        if operation_name not in self.bulk_operations:
            return False
        
        if not self.selected_items:
            return False
        
        try:
            operation_func = self.bulk_operations[operation_name]
            return operation_func(**kwargs)
        except Exception as e:
            print(f"Bulk operation failed: {e}")
            return False
    
    def _bulk_download(self, **kwargs) -> bool:
        """Start download for all selected items"""
        success_count = 0
        for item in self.selected_items:
            try:
                # Trigger download for item
                if hasattr(item, 'start_download'):
                    item.start_download()
                    success_count += 1
            except Exception:
                continue
        
        return success_count > 0
    
    def _bulk_pause(self, **kwargs) -> bool:
        """Pause all selected downloads"""
        success_count = 0
        for item in self.selected_items:
            try:
                if hasattr(item, 'pause_download'):
                    item.pause_download()
                    success_count += 1
            except Exception:
                continue
        
        return success_count > 0
    
    def _bulk_resume(self, **kwargs) -> bool:
        """Resume all selected downloads"""
        success_count = 0
        for item in self.selected_items:
            try:
                if hasattr(item, 'resume_download'):
                    item.resume_download()
                    success_count += 1
            except Exception:
                continue
        
        return success_count > 0
    
    def _bulk_remove(self, **kwargs) -> bool:
        """Remove all selected items"""
        confirm = kwargs.get('confirm', True)
        
        if confirm:
            # Show confirmation dialog
            reply = QMessageBox.question(
                self.parent,
                "Confirm Bulk Removal",
                f"Are you sure you want to remove {len(self.selected_items)} items?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return False
        
        success_count = 0
        for item in self.selected_items:
            try:
                if hasattr(item, 'remove'):
                    item.remove()
                    success_count += 1
            except Exception:
                continue
        
        return success_count > 0
    
    def _bulk_change_quality(self, quality: str = "720p", **kwargs) -> bool:
        """Change quality setting for all selected items"""
        success_count = 0
        for item in self.selected_items:
            try:
                if hasattr(item, 'set_quality'):
                    item.set_quality(quality)
                    success_count += 1
            except Exception:
                continue
        
        return success_count > 0
    
    def _bulk_change_folder(self, folder_path: str = "", **kwargs) -> bool:
        """Change output folder for all selected items"""
        success_count = 0
        for item in self.selected_items:
            try:
                if hasattr(item, 'set_output_folder'):
                    item.set_output_folder(folder_path)
                    success_count += 1
            except Exception:
                continue
        
        return success_count > 0
    
    def _bulk_export_urls(self, file_path: str = "", **kwargs) -> bool:
        """Export URLs of selected items to file"""
        if not file_path:
            return False
        
        try:
            urls = []
            for item in self.selected_items:
                if hasattr(item, 'get_url'):
                    urls.append(item.get_url())
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(urls))
            
            return True
        except Exception:
            return False
    
    def _bulk_import_urls(self, file_path: str = "", **kwargs) -> bool:
        """Import URLs from file"""
        if not file_path:
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            # Add URLs to download queue
            success_count = 0
            for url in urls:
                if self._is_valid_url(url):
                    # Add to queue logic would go here
                    success_count += 1
            
            return success_count > 0
        except Exception:
            return False
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for downloading"""
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return url_pattern.match(url) is not None


class ErrorStateManager:
    """
    Enhanced error state management with user guidance
    
    Provides clear error messaging, recovery suggestions, and user guidance.
    """
    
    def __init__(self, parent_widget: QWidget):
        self.parent = parent_widget
        self.style_manager = StyleManager()
        self.error_history: List[Dict] = []
        
    def show_error_state(self, 
                        error_type: str,
                        error_message: str,
                        recovery_suggestions: List[str] = None,
                        auto_retry: bool = False) -> None:
        """
        Show enhanced error state with guidance
        
        Args:
            error_type: Type of error ('network', 'url', 'file', 'permission')
            error_message: User-friendly error description
            recovery_suggestions: List of suggested recovery actions
            auto_retry: Whether to offer automatic retry
        """
        # Create error card
        error_card = self._create_error_card(error_type, error_message, 
                                           recovery_suggestions, auto_retry)
        
        # Log error for pattern analysis
        self._log_error(error_type, error_message)
        
        # Show error card (implementation would depend on UI structure)
        # For now, we'll create the card structure
        
    def _create_error_card(self, 
                          error_type: str,
                          error_message: str,
                          recovery_suggestions: List[str] = None,
                          auto_retry: bool = False) -> CardComponent:
        """Create error display card with recovery options"""
        
        # Create error card with appropriate styling
        error_card = CardComponent(
            elevation=ElevationLevel.ELEVATED,
            title="Error Occurred"
        )
        
        # Error icon and message
        error_layout = QVBoxLayout()
        
        # Error icon
        error_icon = IconComponent('error', IconSize.LG)
        error_icon_label = QLabel()
        error_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Error message
        message_label = QLabel(error_message)
        message_label.setWordWrap(True)
        message_label.setObjectName("error_message")
        
        error_layout.addWidget(error_icon_label)
        error_layout.addWidget(message_label)
        
        # Recovery suggestions
        if recovery_suggestions:
            suggestions_label = QLabel("Try these solutions:")
            suggestions_label.setObjectName("suggestions_title")
            error_layout.addWidget(suggestions_label)
            
            for suggestion in recovery_suggestions:
                suggestion_label = QLabel(f"• {suggestion}")
                suggestion_label.setObjectName("suggestion_item")
                error_layout.addWidget(suggestion_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        if auto_retry:
            retry_button = EnhancedButton("Retry", "refresh", primary=True)
            button_layout.addWidget(retry_button)
        
        help_button = EnhancedButton("Get Help", "info", primary=False)
        dismiss_button = EnhancedButton("Dismiss", "close", primary=False)
        
        button_layout.addWidget(help_button)
        button_layout.addWidget(dismiss_button)
        
        error_layout.addLayout(button_layout)
        error_card.add_content_layout(error_layout)
        
        # Apply error styling
        self._apply_error_styling(error_card, error_type)
        
        return error_card
    
    def _apply_error_styling(self, card: CardComponent, error_type: str):
        """Apply error-specific styling to card"""
        error_colors = {
            'network': self.style_manager.get_token_value('color-status-warning', '#F59E0B'),
            'url': self.style_manager.get_token_value('color-status-error', '#EF4444'),
            'file': self.style_manager.get_token_value('color-status-warning', '#F59E0B'),
            'permission': self.style_manager.get_token_value('color-status-error', '#EF4444'),
            'default': self.style_manager.get_token_value('color-status-error', '#EF4444')
        }
        
        error_color = error_colors.get(error_type, error_colors['default'])
        
        error_styles = f"""
        CardComponent {{
            border-left: 4px solid {error_color};
        }}
        
        #error_message {{
            color: {self.style_manager.get_token_value('color-text-primary', '#0F172A')};
            font-size: 14px;
            margin: 8px 0;
        }}
        
        #suggestions_title {{
            color: {self.style_manager.get_token_value('color-text-secondary', '#64748B')};
            font-weight: 600;
            margin-top: 12px;
        }}
        
        #suggestion_item {{
            color: {self.style_manager.get_token_value('color-text-secondary', '#64748B')};
            font-size: 13px;
            margin: 4px 0;
        }}
        """
        
        card.setStyleSheet(card.styleSheet() + error_styles)
    
    def _log_error(self, error_type: str, error_message: str):
        """Log error for pattern analysis"""
        import datetime
        
        error_entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'type': error_type,
            'message': error_message
        }
        
        self.error_history.append(error_entry)
        
        # Keep only last 100 errors
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]
    
    def get_error_recovery_suggestions(self, error_type: str) -> List[str]:
        """Get context-appropriate recovery suggestions"""
        suggestions = {
            'network': [
                "Check your internet connection",
                "Try refreshing the page",
                "Check if the website is accessible",
                "Try again in a few moments"
            ],
            'url': [
                "Verify the URL is correct and complete",
                "Check if the video is public and available",
                "Try copying the URL again from the source",
                "Make sure the video hasn't been removed"
            ],
            'file': [
                "Check available disk space",
                "Verify write permissions to output folder",
                "Choose a different output location",
                "Close other applications using the file"
            ],
            'permission': [
                "Run the application as administrator",
                "Check folder write permissions",
                "Choose a different output folder",
                "Contact system administrator if needed"
            ]
        }
        
        return suggestions.get(error_type, [
            "Try the operation again",
            "Check application settings", 
            "Restart the application if the problem persists"
        ])


def create_workflow_optimized_widget(widget_type: str, **kwargs) -> QWidget:
    """
    Factory function for creating workflow-optimized widgets
    
    Args:
        widget_type: Type of widget to create
        **kwargs: Widget-specific arguments
        
    Returns:
        Optimized widget with workflow enhancements
    """
    if widget_type == "download_input":
        return _create_optimized_download_input(**kwargs)
    elif widget_type == "settings_panel":
        return _create_optimized_settings_panel(**kwargs)
    elif widget_type == "bulk_actions_toolbar":
        return _create_bulk_actions_toolbar(**kwargs)
    else:
        raise ValueError(f"Unknown widget type: {widget_type}")


def _create_optimized_download_input(**kwargs) -> QWidget:
    """Create optimized download input with smart defaults"""
    smart_defaults = SmartDefaults()
    
    container = QWidget()
    layout = QVBoxLayout(container)
    
    # URL input with smart validation
    url_input = EnhancedInput(
        placeholder="Enter video URL (YouTube, TikTok, etc.)",
        label="Video URL"
    )
    
    # Auto-suggest based on clipboard
    clipboard = QApplication.clipboard()
    clipboard_text = clipboard.text()
    if clipboard_text and _is_video_url(clipboard_text):
        url_input.setText(clipboard_text)
    
    # Output settings with smart defaults
    output_input = EnhancedInput(
        placeholder="Output filename (auto-generated)",
        label="Output File"
    )
    
    # Quality selector with learned preferences
    quality_input = EnhancedInput(
        placeholder="Video quality (auto-selected)",
        label="Quality"
    )
    
    layout.addWidget(url_input)
    layout.addWidget(output_input)
    layout.addWidget(quality_input)
    
    # Auto-fill when URL changes
    def on_url_changed():
        url = url_input.text()
        if url:
            suggested_output = smart_defaults.suggest_output_path(url)
            suggested_quality = smart_defaults.suggest_quality_setting(url)
            
            output_input.setText(suggested_output)
            quality_input.setText(suggested_quality)
    
    url_input.textChanged.connect(on_url_changed)
    
    return container


def _create_optimized_settings_panel(**kwargs) -> QWidget:
    """Create optimized settings panel with smart organization"""
    container = QWidget()
    layout = QVBoxLayout(container)
    
    # Organized settings cards
    cards = [
        _create_quick_settings_card(),
        _create_advanced_settings_card(),
        _create_keyboard_shortcuts_card()
    ]
    
    for card in cards:
        layout.addWidget(card)
    
    return container


def _create_bulk_actions_toolbar(**kwargs) -> QWidget:
    """Create bulk actions toolbar"""
    container = QWidget()
    layout = QHBoxLayout(container)
    
    # Bulk action buttons
    actions = [
        ("Download All", "download", "primary"),
        ("Pause All", "pause", "secondary"),
        ("Remove Selected", "close", "secondary"),
        ("Export URLs", "file", "secondary")
    ]
    
    for text, icon, style in actions:
        button = EnhancedButton(text, icon, primary=(style == "primary"))
        layout.addWidget(button)
    
    return container


def _create_quick_settings_card() -> CardComponent:
    """Create quick settings card"""
    card = CardComponent(title="Quick Settings")
    
    # Common settings with smart defaults
    settings_layout = QVBoxLayout()
    
    quality_input = EnhancedInput("720p", "Default Quality")
    folder_input = EnhancedInput("Downloads/", "Default Folder")
    
    settings_layout.addWidget(quality_input)
    settings_layout.addWidget(folder_input)
    
    card.add_content_layout(settings_layout)
    return card


def _create_advanced_settings_card() -> CardComponent:
    """Create advanced settings card"""
    card = CardComponent(title="Advanced Settings")
    
    # Advanced options
    advanced_layout = QVBoxLayout()
    
    concurrent_input = EnhancedInput("3", "Concurrent Downloads")
    retry_input = EnhancedInput("3", "Retry Attempts")
    
    advanced_layout.addWidget(concurrent_input)
    advanced_layout.addWidget(retry_input)
    
    card.add_content_layout(advanced_layout)
    return card


def _create_keyboard_shortcuts_card() -> CardComponent:
    """Create keyboard shortcuts reference card"""
    card = CardComponent(title="Keyboard Shortcuts")
    
    shortcuts_layout = QVBoxLayout()
    
    common_shortcuts = [
        ("Ctrl+N", "New Download"),
        ("Ctrl+D", "Start Download"),
        ("F1", "Show Help")
    ]
    
    for key, description in common_shortcuts:
        shortcut_label = QLabel(f"{key}: {description}")
        shortcuts_layout.addWidget(shortcut_label)
    
    card.add_content_layout(shortcuts_layout)
    return card


def _is_video_url(url: str) -> bool:
    """Check if URL is likely a video URL"""
    video_domains = [
        'youtube.com', 'youtu.be', 'tiktok.com', 'instagram.com',
        'twitter.com', 'x.com', 'facebook.com', 'vimeo.com'
    ]
    
    return any(domain in url.lower() for domain in video_domains) 