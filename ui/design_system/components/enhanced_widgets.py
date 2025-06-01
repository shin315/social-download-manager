"""
Enhanced Widget Components

Modern PyQt6 widgets enhanced with animations, micro-interactions,
and polished visual feedback for superior user experience.
"""

from typing import Optional, Union, Callable
from PyQt6.QtWidgets import (QPushButton, QLabel, QLineEdit, QComboBox, 
                             QCheckBox, QProgressBar, QWidget, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

from .animations import (AnimationManager, HoverAnimator, LoadingAnimator,
                        MicroInteractionManager, enhance_widget_interactions,
                        apply_hover_animations, apply_loading_animation)
from .cards import CardComponent, ElevationLevel
from .icons import IconComponent, IconSize, IconStyle
from ..styles.style_manager import StyleManager


class EnhancedButton(QPushButton):
    """
    Enhanced button with animations and micro-interactions
    
    Features:
    - Hover scale animation
    - Click feedback animation
    - Loading state with animation
    - Success/error feedback
    - Modern styling with design tokens
    """
    
    # Enhanced signals
    success = pyqtSignal()
    error = pyqtSignal()
    
    def __init__(self, 
                 text: str = "",
                 icon_name: Optional[str] = None,
                 primary: bool = True,
                 enable_animations: bool = True,
                 parent: Optional[QWidget] = None):
        """
        Initialize enhanced button
        
        Args:
            text: Button text
            icon_name: Optional icon name from icon system
            primary: Primary button styling
            enable_animations: Enable hover/click animations
            parent: Parent widget
        """
        super().__init__(text, parent)
        
        self.icon_name = icon_name
        self.primary = primary
        self.enable_animations = enable_animations
        self.style_manager = StyleManager()
        
        self._is_loading = False
        self._loader = None
        self._original_text = text
        
        self._setup_button()
        if enable_animations:
            self._setup_animations()
    
    def _setup_button(self):
        """Set up button with modern styling"""
        # Add icon if specified
        if self.icon_name:
            icon = IconComponent(self.icon_name, IconSize.SM)
            self.setIcon(icon.pixmap())
        
        # Apply enhanced styling
        self._apply_modern_styling()
        
        # Set minimum size for better touch targets
        self.setMinimumHeight(40)
        
        # Connect signals for feedback
        self.success.connect(self._show_success_feedback)
        self.error.connect(self._show_error_feedback)
    
    def _setup_animations(self):
        """Set up button animations and micro-interactions"""
        # Enable all interaction enhancements
        enhance_widget_interactions(self, 
                                  enable_hover=True,
                                  enable_click=True, 
                                  enable_focus=True)
    
    def _apply_modern_styling(self):
        """Apply modern button styling with design tokens"""
        if self.primary:
            bg_color = self.style_manager.get_token_value('color-button-primary-background', '#3B82F6')
            text_color = self.style_manager.get_token_value('color-button-primary-text', '#FFFFFF')
            hover_color = self.style_manager.get_token_value('color-button-primary-background-hover', '#2563EB')
        else:
            bg_color = self.style_manager.get_token_value('color-button-secondary-background', '#F1F5F9')
            text_color = self.style_manager.get_token_value('color-button-secondary-text', '#475569')
            hover_color = self.style_manager.get_token_value('color-button-secondary-background-hover', '#E2E8F0')
        
        button_styles = f"""
        EnhancedButton {{
            background-color: {bg_color};
            color: {text_color};
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: 500;
            font-size: 14px;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        
        EnhancedButton:hover {{
            background-color: {hover_color};
        }}
        
        EnhancedButton:pressed {{
            background-color: {bg_color};
        }}
        
        EnhancedButton:disabled {{
            background-color: {self.style_manager.get_token_value('color-background-tertiary', '#F8FAFC')};
            color: {self.style_manager.get_token_value('color-text-tertiary', '#94A3B8')};
        }}
        """
        
        self.setStyleSheet(button_styles)
    
    def set_loading(self, loading: bool = True, loading_text: str = "Loading..."):
        """Set button loading state with animation"""
        if loading and not self._is_loading:
            self._is_loading = True
            self._original_text = self.text()
            self.setText(loading_text)
            self.setEnabled(False)
            
            # Start loading animation
            self._loader = apply_loading_animation(self, "pulse")
            
        elif not loading and self._is_loading:
            self._is_loading = False
            self.setText(self._original_text)
            self.setEnabled(True)
            
            # Stop loading animation
            if self._loader:
                self._loader.stop_loading_animations()
                self._loader = None
    
    def _show_success_feedback(self):
        """Show success animation feedback"""
        success_anim = MicroInteractionManager.add_success_feedback(self)
        success_anim()
    
    def _show_error_feedback(self):
        """Show error animation feedback"""
        error_anim = MicroInteractionManager.add_error_feedback(self)
        error_anim()
    
    def trigger_success(self):
        """Manually trigger success feedback"""
        self.success.emit()
    
    def trigger_error(self):
        """Manually trigger error feedback"""
        self.error.emit()


class EnhancedInput(QLineEdit):
    """
    Enhanced input field with animations and better UX
    
    Features:
    - Focus glow animation
    - Floating label behavior
    - Success/error state indicators
    - Modern styling with design tokens
    """
    
    def __init__(self, 
                 placeholder: str = "",
                 label: str = "",
                 enable_animations: bool = True,
                 parent: Optional[QWidget] = None):
        """
        Initialize enhanced input
        
        Args:
            placeholder: Placeholder text
            label: Optional floating label
            enable_animations: Enable focus animations
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.label_text = label
        self.enable_animations = enable_animations
        self.style_manager = StyleManager()
        
        self._has_content = False
        self._is_focused = False
        
        self.setPlaceholderText(placeholder)
        self._setup_input()
        
        if enable_animations:
            self._setup_animations()
    
    def _setup_input(self):
        """Set up input with modern styling"""
        self._apply_modern_styling()
        self.setMinimumHeight(44)
        
        # Connect text change signal
        self.textChanged.connect(self._on_text_changed)
    
    def _setup_animations(self):
        """Set up input animations"""
        enhance_widget_interactions(self,
                                  enable_hover=False,  # Subtle for inputs
                                  enable_click=False,
                                  enable_focus=True)
    
    def _apply_modern_styling(self):
        """Apply modern input styling"""
        bg_color = self.style_manager.get_token_value('color-background-primary', '#FFFFFF')
        text_color = self.style_manager.get_token_value('color-text-primary', '#0F172A')
        border_color = self.style_manager.get_token_value('color-border-default', '#E2E8F0')
        focus_color = self.style_manager.get_token_value('color-border-focus', '#3B82F6')
        
        input_styles = f"""
        EnhancedInput {{
            background-color: {bg_color};
            color: {text_color};
            border: 2px solid {border_color};
            border-radius: 8px;
            padding: 12px 16px;
            font-size: 14px;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        
        EnhancedInput:focus {{
            border-color: {focus_color};
            outline: none;
        }}
        
        EnhancedInput:hover {{
            border-color: {self.style_manager.get_token_value('color-border-strong', '#CBD5E1')};
        }}
        """
        
        self.setStyleSheet(input_styles)
    
    def _on_text_changed(self, text: str):
        """Handle text changes for floating label behavior"""
        self._has_content = bool(text.strip())
        self._update_label_state()
    
    def _update_label_state(self):
        """Update floating label appearance"""
        # This would typically involve animating label position
        # For now, we'll use placeholder behavior
        pass
    
    def set_success_state(self):
        """Set input to success state"""
        success_color = self.style_manager.get_token_value('color-status-success', '#10B981')
        self.setStyleSheet(self.styleSheet() + f"""
        EnhancedInput {{
            border-color: {success_color} !important;
        }}
        """)
        
        # Add success feedback
        success_anim = MicroInteractionManager.add_success_feedback(self)
        success_anim()
    
    def set_error_state(self, error_message: str = ""):
        """Set input to error state"""
        error_color = self.style_manager.get_token_value('color-status-error', '#EF4444')
        self.setStyleSheet(self.styleSheet() + f"""
        EnhancedInput {{
            border-color: {error_color} !important;
        }}
        """)
        
        # Add error feedback
        error_anim = MicroInteractionManager.add_error_feedback(self)
        error_anim()


class EnhancedProgressBar(QProgressBar):
    """
    Enhanced progress bar with smooth animations
    
    Features:
    - Smooth value transitions
    - Pulse animation for indeterminate state
    - Modern styling with gradient effects
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize enhanced progress bar"""
        super().__init__(parent)
        
        self.style_manager = StyleManager()
        self.animation_manager = AnimationManager()
        self._current_animation = None
        
        self._setup_progress_bar()
    
    def _setup_progress_bar(self):
        """Set up progress bar with modern styling"""
        self._apply_modern_styling()
        self.setMinimumHeight(8)
        self.setTextVisible(False)  # Use custom text positioning
    
    def _apply_modern_styling(self):
        """Apply modern progress bar styling"""
        bg_color = self.style_manager.get_token_value('color-background-tertiary', '#F1F5F9')
        fill_color = self.style_manager.get_token_value('color-brand-primary-500', '#3B82F6')
        
        progress_styles = f"""
        EnhancedProgressBar {{
            background-color: {bg_color};
            border: none;
            border-radius: 4px;
        }}
        
        EnhancedProgressBar::chunk {{
            background-color: {fill_color};
            border-radius: 4px;
            transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        """
        
        self.setStyleSheet(progress_styles)
    
    def set_value_animated(self, value: int, duration_ms: int = 300):
        """Set progress value with smooth animation"""
        if self._current_animation:
            self._current_animation.stop()
        
        # Create smooth transition animation
        # Note: QProgressBar doesn't directly support animated values
        # This is a simplified version - full implementation would need custom painting
        
        # For now, use timer to create stepped animation
        start_value = self.value()
        target_value = value
        steps = 20
        step_duration = duration_ms // steps
        step_size = (target_value - start_value) / steps
        
        def animate_step(current_step):
            if current_step <= steps:
                new_value = int(start_value + (step_size * current_step))
                self.setValue(new_value)
                
                QTimer.singleShot(step_duration, 
                                lambda: animate_step(current_step + 1))
        
        animate_step(0)


class EnhancedCard(CardComponent):
    """
    Enhanced card component with advanced animations
    
    Extends the base CardComponent with more sophisticated animations
    and interactive behaviors.
    """
    
    def __init__(self, 
                 elevation: ElevationLevel = ElevationLevel.RAISED,
                 enable_advanced_animations: bool = True,
                 **kwargs):
        """
        Initialize enhanced card
        
        Args:
            elevation: Card elevation level
            enable_advanced_animations: Enable advanced hover/interaction animations
            **kwargs: Arguments passed to CardComponent
        """
        super().__init__(elevation=elevation, **kwargs)
        
        self.enable_advanced_animations = enable_advanced_animations
        
        if enable_advanced_animations:
            self._setup_advanced_animations()
    
    def _setup_advanced_animations(self):
        """Set up advanced card animations"""
        # Apply multiple animation types
        hover_animator = HoverAnimator(self)
        hover_animator.enable_hover_scale(1.02)  # Subtle scale
        
        # Add elevation animation on hover
        if self.clickable:
            hover_animator.enable_hover_elevation(2)


def create_enhanced_button(text: str, 
                         icon_name: Optional[str] = None,
                         primary: bool = True,
                         on_click: Optional[Callable] = None) -> EnhancedButton:
    """
    Factory function for creating enhanced buttons
    
    Args:
        text: Button text
        icon_name: Optional icon name
        primary: Primary button styling
        on_click: Click handler function
        
    Returns:
        Configured EnhancedButton
    """
    button = EnhancedButton(text, icon_name, primary)
    
    if on_click:
        button.clicked.connect(on_click)
    
    return button


def create_enhanced_input(placeholder: str,
                        label: str = "",
                        validator: Optional[Callable] = None) -> EnhancedInput:
    """
    Factory function for creating enhanced inputs
    
    Args:
        placeholder: Placeholder text
        label: Optional floating label
        validator: Optional validation function
        
    Returns:
        Configured EnhancedInput
    """
    input_field = EnhancedInput(placeholder, label)
    
    if validator:
        def validate_input():
            if validator(input_field.text()):
                input_field.set_success_state()
            else:
                input_field.set_error_state()
        
        input_field.textChanged.connect(lambda: validate_input())
    
    return input_field


def create_enhanced_progress(minimum: int = 0,
                           maximum: int = 100,
                           initial_value: int = 0) -> EnhancedProgressBar:
    """
    Factory function for creating enhanced progress bars
    
    Args:
        minimum: Minimum value
        maximum: Maximum value
        initial_value: Initial progress value
        
    Returns:
        Configured EnhancedProgressBar
    """
    progress = EnhancedProgressBar()
    progress.setRange(minimum, maximum)
    progress.setValue(initial_value)
    
    return progress 