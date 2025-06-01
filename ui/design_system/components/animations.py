"""
Animation & Micro-interaction System

Modern animation components providing smooth transitions, micro-interactions,
and visual feedback for enhanced user experience and interface polish.
"""

import enum
from typing import Dict, Optional, Union, Callable, Any
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PyQt6.QtCore import (QPropertyAnimation, QSequentialAnimationGroup, 
                          QParallelAnimationGroup, QEasingCurve, QTimer, 
                          pyqtSignal, QRect, QPoint, QSize)
from PyQt6.QtGui import QColor, QPalette
from ..styles.style_manager import StyleManager


class AnimationDuration(enum.Enum):
    """Standard animation duration presets following design system timing"""
    INSTANT = 0        # No animation
    FAST = 150         # Quick feedback (hover, clicks)
    NORMAL = 250       # Standard transitions
    SLOW = 350         # Complex state changes
    DELIBERATE = 500   # Important transitions requiring attention


class EasingType(enum.Enum):
    """Animation easing curves for different interaction types"""
    LINEAR = QEasingCurve.Type.Linear
    EASE_OUT = QEasingCurve.Type.OutCubic        # Most natural for UI
    EASE_IN = QEasingCurve.Type.InCubic          # Good for exit animations
    EASE_IN_OUT = QEasingCurve.Type.InOutCubic   # Smooth, balanced
    BOUNCE = QEasingCurve.Type.OutBounce         # Playful feedback
    ELASTIC = QEasingCurve.Type.OutElastic       # Attention-grabbing


class AnimationManager:
    """
    Central animation management system
    
    Provides consistent animation behaviors across the application
    with performance optimization and proper cleanup.
    """
    
    def __init__(self):
        self.active_animations: Dict[str, QPropertyAnimation] = {}
        self.style_manager = StyleManager()
    
    def create_fade_animation(self, 
                            widget: QWidget,
                            start_opacity: float = 0.0,
                            end_opacity: float = 1.0,
                            duration: AnimationDuration = AnimationDuration.NORMAL,
                            easing: EasingType = EasingType.EASE_OUT) -> QPropertyAnimation:
        """
        Create smooth fade in/out animation
        
        Args:
            widget: Target widget for animation
            start_opacity: Starting opacity (0.0 to 1.0)
            end_opacity: Ending opacity (0.0 to 1.0)
            duration: Animation timing
            easing: Easing curve type
            
        Returns:
            Configured opacity animation
        """
        # Ensure widget has opacity effect
        if not widget.graphicsEffect():
            opacity_effect = QGraphicsOpacityEffect()
            widget.setGraphicsEffect(opacity_effect)
        
        opacity_effect = widget.graphicsEffect()
        
        animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(duration.value)
        animation.setStartValue(start_opacity)
        animation.setEndValue(end_opacity)
        animation.setEasingCurve(easing.value)
        
        return animation
    
    def create_slide_animation(self,
                             widget: QWidget,
                             start_pos: QPoint,
                             end_pos: QPoint,
                             duration: AnimationDuration = AnimationDuration.NORMAL,
                             easing: EasingType = EasingType.EASE_OUT) -> QPropertyAnimation:
        """
        Create smooth slide animation
        
        Args:
            widget: Target widget
            start_pos: Starting position
            end_pos: Ending position
            duration: Animation timing
            easing: Easing curve
            
        Returns:
            Configured position animation
        """
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration.value)
        animation.setStartValue(start_pos)
        animation.setEndValue(end_pos)
        animation.setEasingCurve(easing.value)
        
        return animation
    
    def create_scale_animation(self,
                             widget: QWidget,
                             start_scale: float = 1.0,
                             end_scale: float = 1.1,
                             duration: AnimationDuration = AnimationDuration.FAST,
                             easing: EasingType = EasingType.EASE_OUT) -> QParallelAnimationGroup:
        """
        Create smooth scale animation (simulated via geometry)
        
        Args:
            widget: Target widget
            start_scale: Starting scale factor
            end_scale: Ending scale factor
            duration: Animation timing
            easing: Easing curve
            
        Returns:
            Scale animation group
        """
        current_geometry = widget.geometry()
        center = current_geometry.center()
        
        # Calculate scaled geometry
        start_size = QSize(
            int(current_geometry.width() * start_scale),
            int(current_geometry.height() * start_scale)
        )
        end_size = QSize(
            int(current_geometry.width() * end_scale),
            int(current_geometry.height() * end_scale)
        )
        
        # Create start and end rectangles centered on original position
        start_rect = QRect(
            center.x() - start_size.width() // 2,
            center.y() - start_size.height() // 2,
            start_size.width(),
            start_size.height()
        )
        end_rect = QRect(
            center.x() - end_size.width() // 2,
            center.y() - end_size.height() // 2,
            end_size.width(),
            end_size.height()
        )
        
        animation = QPropertyAnimation(widget, b"geometry")
        animation.setDuration(duration.value)
        animation.setStartValue(start_rect)
        animation.setEndValue(end_rect)
        animation.setEasingCurve(easing.value)
        
        # Wrap in parallel group for consistency
        group = QParallelAnimationGroup()
        group.addAnimation(animation)
        
        return group
    
    def create_elevation_animation(self,
                                 widget: QWidget,
                                 start_elevation: int = 2,
                                 end_elevation: int = 8,
                                 duration: AnimationDuration = AnimationDuration.FAST) -> QPropertyAnimation:
        """
        Create smooth elevation change animation via shadow
        
        Args:
            widget: Target widget
            start_elevation: Starting shadow intensity
            end_elevation: Ending shadow intensity
            duration: Animation timing
            
        Returns:
            Shadow animation
        """
        # Ensure widget has shadow effect
        shadow_effect = None
        if widget.graphicsEffect() and isinstance(widget.graphicsEffect(), QGraphicsDropShadowEffect):
            shadow_effect = widget.graphicsEffect()
        else:
            shadow_effect = QGraphicsDropShadowEffect()
            shadow_effect.setColor(QColor(0, 0, 0, 30))
            shadow_effect.setOffset(0, 1)
            widget.setGraphicsEffect(shadow_effect)
        
        animation = QPropertyAnimation(shadow_effect, b"blurRadius")
        animation.setDuration(duration.value)
        animation.setStartValue(start_elevation)
        animation.setEndValue(end_elevation)
        animation.setEasingCurve(EasingType.EASE_OUT.value)
        
        return animation
    
    def register_animation(self, name: str, animation: QPropertyAnimation):
        """Register animation for management and cleanup"""
        self.active_animations[name] = animation
    
    def stop_animation(self, name: str):
        """Stop and cleanup specific animation"""
        if name in self.active_animations:
            self.active_animations[name].stop()
            del self.active_animations[name]
    
    def stop_all_animations(self):
        """Stop and cleanup all active animations"""
        for animation in self.active_animations.values():
            animation.stop()
        self.active_animations.clear()


class HoverAnimator:
    """
    Specialized animator for hover micro-interactions
    
    Provides consistent hover behaviors across components
    """
    
    def __init__(self, widget: QWidget):
        self.widget = widget
        self.animation_manager = AnimationManager()
        self.hover_animation = None
        self.leave_animation = None
        
        # Store original properties for restoration
        self.original_geometry = widget.geometry()
        self.is_animating = False
    
    def enable_hover_scale(self, 
                          scale_factor: float = 1.05,
                          duration: AnimationDuration = AnimationDuration.FAST):
        """Enable subtle scale animation on hover"""
        self.widget.enterEvent = self._create_hover_handler(
            lambda: self._animate_hover_scale(scale_factor, duration)
        )
        self.widget.leaveEvent = self._create_leave_handler(
            lambda: self._animate_leave_scale(duration)
        )
    
    def enable_hover_elevation(self,
                             elevation_increase: int = 4,
                             duration: AnimationDuration = AnimationDuration.FAST):
        """Enable elevation animation on hover"""
        self.widget.enterEvent = self._create_hover_handler(
            lambda: self._animate_hover_elevation(elevation_increase, duration)
        )
        self.widget.leaveEvent = self._create_leave_handler(
            lambda: self._animate_leave_elevation(duration)
        )
    
    def enable_hover_glow(self,
                         glow_intensity: int = 15,
                         duration: AnimationDuration = AnimationDuration.FAST):
        """Enable glow effect on hover"""
        self.widget.enterEvent = self._create_hover_handler(
            lambda: self._animate_hover_glow(glow_intensity, duration)
        )
        self.widget.leaveEvent = self._create_leave_handler(
            lambda: self._animate_leave_glow(duration)
        )
    
    def _create_hover_handler(self, animation_func: Callable):
        """Create hover event handler that preserves original behavior"""
        def hover_handler(event):
            if not self.is_animating:
                animation_func()
            # Call original enterEvent if it exists
            super(type(self.widget), self.widget).enterEvent(event)
        return hover_handler
    
    def _create_leave_handler(self, animation_func: Callable):
        """Create leave event handler that preserves original behavior"""
        def leave_handler(event):
            if not self.is_animating:
                animation_func()
            # Call original leaveEvent if it exists
            super(type(self.widget), self.widget).leaveEvent(event)
        return leave_handler
    
    def _animate_hover_scale(self, scale_factor: float, duration: AnimationDuration):
        """Animate scale increase on hover"""
        self.is_animating = True
        self.hover_animation = self.animation_manager.create_scale_animation(
            self.widget, 1.0, scale_factor, duration
        )
        self.hover_animation.finished.connect(lambda: setattr(self, 'is_animating', False))
        self.hover_animation.start()
    
    def _animate_leave_scale(self, duration: AnimationDuration):
        """Animate scale decrease on leave"""
        self.is_animating = True
        self.leave_animation = self.animation_manager.create_scale_animation(
            self.widget, 1.05, 1.0, duration
        )
        self.leave_animation.finished.connect(lambda: setattr(self, 'is_animating', False))
        self.leave_animation.start()
    
    def _animate_hover_elevation(self, elevation_increase: int, duration: AnimationDuration):
        """Animate elevation increase on hover"""
        self.is_animating = True
        self.hover_animation = self.animation_manager.create_elevation_animation(
            self.widget, 2, 2 + elevation_increase, duration
        )
        self.hover_animation.finished.connect(lambda: setattr(self, 'is_animating', False))
        self.hover_animation.start()
    
    def _animate_leave_elevation(self, duration: AnimationDuration):
        """Animate elevation decrease on leave"""
        self.is_animating = True
        self.leave_animation = self.animation_manager.create_elevation_animation(
            self.widget, 6, 2, duration
        )
        self.leave_animation.finished.connect(lambda: setattr(self, 'is_animating', False))
        self.leave_animation.start()
    
    def _animate_hover_glow(self, glow_intensity: int, duration: AnimationDuration):
        """Animate glow effect on hover"""
        # Add glow effect via shadow
        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setColor(QColor(59, 130, 246, 100))  # Blue glow
        shadow_effect.setBlurRadius(glow_intensity)
        shadow_effect.setOffset(0, 0)
        self.widget.setGraphicsEffect(shadow_effect)
    
    def _animate_leave_glow(self, duration: AnimationDuration):
        """Remove glow effect on leave"""
        self.widget.setGraphicsEffect(None)


class LoadingAnimator:
    """
    Loading state animations and progress indicators
    
    Provides smooth loading feedback for better UX
    """
    
    def __init__(self, widget: QWidget):
        self.widget = widget
        self.animation_manager = AnimationManager()
        self.pulse_animation = None
        self.rotation_timer = None
        
    def start_pulse_animation(self,
                            min_opacity: float = 0.3,
                            max_opacity: float = 1.0,
                            duration: AnimationDuration = AnimationDuration.SLOW):
        """Start pulsing opacity animation for loading state"""
        # Create repeating fade animation
        fade_out = self.animation_manager.create_fade_animation(
            self.widget, max_opacity, min_opacity, duration
        )
        fade_in = self.animation_manager.create_fade_animation(
            self.widget, min_opacity, max_opacity, duration
        )
        
        # Create sequential group that repeats
        self.pulse_animation = QSequentialAnimationGroup()
        self.pulse_animation.addAnimation(fade_out)
        self.pulse_animation.addAnimation(fade_in)
        self.pulse_animation.setLoopCount(-1)  # Infinite loop
        
        self.pulse_animation.start()
    
    def start_shimmer_effect(self):
        """Start shimmer loading effect (placeholder animation)"""
        # This would typically involve gradient animations
        # For now, use pulse as a simpler alternative
        self.start_pulse_animation(0.5, 0.8, AnimationDuration.FAST)
    
    def stop_loading_animations(self):
        """Stop all loading animations"""
        if self.pulse_animation:
            self.pulse_animation.stop()
            self.pulse_animation = None
        
        # Restore normal opacity
        self.animation_manager.create_fade_animation(
            self.widget, None, 1.0, AnimationDuration.FAST
        ).start()


class MicroInteractionManager:
    """
    Manager for subtle micro-interactions that enhance UX
    
    Provides feedback for user actions and state changes
    """
    
    @staticmethod
    def add_click_feedback(widget: QWidget):
        """Add subtle click animation feedback"""
        def click_animation():
            # Brief scale down then back up
            animator = HoverAnimator(widget)
            
            # Scale down animation
            down_animation = AnimationManager().create_scale_animation(
                widget, 1.0, 0.95, AnimationDuration.FAST, EasingType.EASE_IN
            )
            
            # Scale back up animation
            up_animation = AnimationManager().create_scale_animation(
                widget, 0.95, 1.0, AnimationDuration.FAST, EasingType.EASE_OUT
            )
            
            # Chain animations
            sequence = QSequentialAnimationGroup()
            sequence.addAnimation(down_animation)
            sequence.addAnimation(up_animation)
            sequence.start()
        
        # Override mousePressEvent to add animation
        original_press = widget.mousePressEvent
        def enhanced_press(event):
            click_animation()
            if original_press:
                original_press(event)
        
        widget.mousePressEvent = enhanced_press
    
    @staticmethod
    def add_focus_animation(widget: QWidget):
        """Add focus indication animation"""
        def focus_in_animation():
            # Subtle glow effect on focus
            shadow_effect = QGraphicsDropShadowEffect()
            shadow_effect.setColor(QColor(59, 130, 246, 150))  # Focus blue
            shadow_effect.setBlurRadius(8)
            shadow_effect.setOffset(0, 0)
            widget.setGraphicsEffect(shadow_effect)
        
        def focus_out_animation():
            # Remove glow effect
            widget.setGraphicsEffect(None)
        
        # Override focus events
        original_focus_in = widget.focusInEvent
        original_focus_out = widget.focusOutEvent
        
        def enhanced_focus_in(event):
            focus_in_animation()
            if original_focus_in:
                original_focus_in(event)
        
        def enhanced_focus_out(event):
            focus_out_animation()
            if original_focus_out:
                original_focus_out(event)
        
        widget.focusInEvent = enhanced_focus_in
        widget.focusOutEvent = enhanced_focus_out
    
    @staticmethod
    def add_success_feedback(widget: QWidget):
        """Add success state micro-interaction"""
        def success_animation():
            # Brief green glow
            shadow_effect = QGraphicsDropShadowEffect()
            shadow_effect.setColor(QColor(34, 197, 94, 200))  # Success green
            shadow_effect.setBlurRadius(12)
            shadow_effect.setOffset(0, 0)
            widget.setGraphicsEffect(shadow_effect)
            
            # Remove after delay
            QTimer.singleShot(1000, lambda: widget.setGraphicsEffect(None))
        
        return success_animation
    
    @staticmethod
    def add_error_feedback(widget: QWidget):
        """Add error state micro-interaction"""
        def error_animation():
            # Shake animation with red glow
            original_pos = widget.pos()
            
            # Red glow effect
            shadow_effect = QGraphicsDropShadowEffect()
            shadow_effect.setColor(QColor(239, 68, 68, 200))  # Error red
            shadow_effect.setBlurRadius(12)
            shadow_effect.setOffset(0, 0)
            widget.setGraphicsEffect(shadow_effect)
            
            # Shake animation
            shake_distance = 3
            positions = [
                original_pos,
                QPoint(original_pos.x() + shake_distance, original_pos.y()),
                QPoint(original_pos.x() - shake_distance, original_pos.y()),
                QPoint(original_pos.x() + shake_distance, original_pos.y()),
                original_pos
            ]
            
            animation_group = QSequentialAnimationGroup()
            
            for i in range(len(positions) - 1):
                move_animation = QPropertyAnimation(widget, b"pos")
                move_animation.setDuration(50)
                move_animation.setStartValue(positions[i])
                move_animation.setEndValue(positions[i + 1])
                animation_group.addAnimation(move_animation)
            
            animation_group.start()
            
            # Remove glow after animation
            QTimer.singleShot(1500, lambda: widget.setGraphicsEffect(None))
        
        return error_animation


def apply_hover_animations(widget: QWidget, animation_type: str = "scale"):
    """
    Utility function to quickly apply hover animations to any widget
    
    Args:
        widget: Target widget
        animation_type: Type of animation ("scale", "elevation", "glow")
    """
    animator = HoverAnimator(widget)
    
    if animation_type == "scale":
        animator.enable_hover_scale()
    elif animation_type == "elevation":
        animator.enable_hover_elevation()
    elif animation_type == "glow":
        animator.enable_hover_glow()


def apply_loading_animation(widget: QWidget, animation_type: str = "pulse"):
    """
    Utility function to apply loading animations
    
    Args:
        widget: Target widget
        animation_type: Type of loading animation ("pulse", "shimmer")
    """
    loader = LoadingAnimator(widget)
    
    if animation_type == "pulse":
        loader.start_pulse_animation()
    elif animation_type == "shimmer":
        loader.start_shimmer_effect()
    
    return loader  # Return so caller can stop animation later


def enhance_widget_interactions(widget: QWidget, 
                              enable_hover: bool = True,
                              enable_click: bool = True,
                              enable_focus: bool = True):
    """
    Utility function to enhance any widget with micro-interactions
    
    Args:
        widget: Target widget
        enable_hover: Enable hover animations
        enable_click: Enable click feedback
        enable_focus: Enable focus animations
    """
    if enable_hover:
        apply_hover_animations(widget, "scale")
    
    if enable_click:
        MicroInteractionManager.add_click_feedback(widget)
    
    if enable_focus:
        MicroInteractionManager.add_focus_animation(widget) 