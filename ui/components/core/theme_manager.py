"""
Enhanced Theme Manager for v2.0 UI Architecture

This module provides comprehensive theme management including:
- Multiple theme variants (light, dark, high-contrast, auto)
- Dynamic theme switching without application restart
- Component-specific theme overrides
- Responsive design support
- Theme inheritance and token system
- Animation transitions for theme switching
- User customization and persistence
"""

import logging
import json
import threading
from typing import Dict, Any, Optional, Callable, List, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPalette, QColor

logger = logging.getLogger(__name__)


class ThemeVariant(Enum):
    """Available theme variants"""
    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"
    AUTO = "auto"  # System-based switching
    CUSTOM = "custom"


class ThemeProperty(Enum):
    """Theme property categories"""
    COLORS = "colors"
    FONTS = "fonts"
    SPACING = "spacing"
    BORDERS = "borders"
    SHADOWS = "shadows"
    ANIMATIONS = "animations"
    BREAKPOINTS = "breakpoints"


@dataclass
class ThemeToken:
    """Individual theme token with metadata"""
    name: str
    value: Any
    category: ThemeProperty
    description: str = ""
    variants: Dict[str, Any] = field(default_factory=dict)
    responsive: bool = False
    semantic: bool = False


@dataclass
class ComponentThemeOverride:
    """Component-specific theme override"""
    component_id: str
    component_type: str
    overrides: Dict[str, Any]
    priority: int = 0
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThemeMetrics:
    """Theme usage and performance metrics"""
    switch_count: int = 0
    last_switch_time: datetime = field(default_factory=datetime.now)
    average_switch_duration: float = 0.0
    component_override_count: int = 0
    custom_tokens_count: int = 0
    theme_errors: List[str] = field(default_factory=list)


class ThemeManager(QObject):
    """
    Advanced theme manager providing comprehensive theme management,
    dynamic switching, and component customization for v2.0 UI architecture.
    """
    
    # Signals for theme events
    theme_changed = pyqtSignal(str, str)  # old_theme, new_theme
    theme_switch_started = pyqtSignal(str)  # new_theme
    theme_switch_completed = pyqtSignal(str)  # new_theme
    theme_error = pyqtSignal(str, str)  # error_type, error_message
    component_override_added = pyqtSignal(str, str)  # component_id, override_type
    token_updated = pyqtSignal(str, str, str)  # token_name, old_value, new_value
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = self._create_default_config()
        if config:
            self.config.update(config)
        
        # Theme state
        self._current_theme = ThemeVariant.LIGHT
        self._theme_variants: Dict[ThemeVariant, Dict[str, Any]] = {}
        self._theme_tokens: Dict[str, ThemeToken] = {}
        self._component_overrides: Dict[str, ComponentThemeOverride] = {}
        self._registered_components: Dict[str, QWidget] = {}
        
        # Animation and transitions
        self._transition_animations: List[QPropertyAnimation] = []
        self._transition_enabled = self.config['enable_transitions']
        self._transition_duration = self.config['transition_duration']
        
        # Metrics and monitoring
        self._metrics = ThemeMetrics()
        self._theme_callbacks: List[Callable[[str, str], None]] = []
        
        # User customization
        self._user_customizations: Dict[str, Any] = {}
        self._custom_themes: Dict[str, Dict[str, Any]] = {}
        
        # System integration
        self._system_theme_monitor: Optional[QTimer] = None
        self._persistence_path = Path(self.config['persistence_path'])
        self._persistence_path.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initialize themes
        self._initialize_builtin_themes()
        self._load_user_customizations()
        
        # Set up system theme monitoring if auto mode enabled
        if self.config['enable_auto_theme']:
            self._setup_system_theme_monitoring()
        
        self.logger.info(f"ThemeManager initialized with config: {self.config}")
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration for theme manager"""
        return {
            'enable_transitions': True,
            'transition_duration': 300,  # milliseconds
            'enable_auto_theme': True,
            'auto_theme_check_interval': 60000,  # 1 minute
            'enable_responsive_design': True,
            'enable_component_overrides': True,
            'enable_user_customization': True,
            'persistence_path': 'data/themes',
            'cache_compiled_themes': True,
            'validate_theme_tokens': True,
            'enable_high_contrast_mode': True,
            'system_theme_integration': True
        }
    
    def _initialize_builtin_themes(self) -> None:
        """Initialize built-in theme variants"""
        try:
            # Light theme
            self._theme_variants[ThemeVariant.LIGHT] = {
                'colors': {
                    'primary': '#0078d7',
                    'primary-hover': '#106ebe',
                    'secondary': '#64748b',
                    'success': '#10b981',
                    'warning': '#f59e0b',
                    'error': '#ef4444',
                    'background': '#ffffff',
                    'surface': '#f8fafc',
                    'surface-elevated': '#ffffff',
                    'text-primary': '#1e293b',
                    'text-secondary': '#64748b',
                    'text-muted': '#94a3b8',
                    'border': '#e2e8f0',
                    'border-focus': '#0078d7',
                    'shadow': 'rgba(0, 0, 0, 0.1)',
                    'overlay': 'rgba(0, 0, 0, 0.5)'
                },
                'fonts': {
                    'family-primary': 'Segoe UI, system-ui, sans-serif',
                    'family-mono': 'Consolas, monospace',
                    'size-xs': '12px',
                    'size-sm': '14px',
                    'size-base': '16px',
                    'size-lg': '18px',
                    'size-xl': '20px',
                    'size-2xl': '24px',
                    'weight-normal': '400',
                    'weight-medium': '500',
                    'weight-semibold': '600',
                    'weight-bold': '700'
                },
                'spacing': {
                    'xs': '4px',
                    'sm': '8px',
                    'md': '16px',
                    'lg': '24px',
                    'xl': '32px',
                    '2xl': '48px',
                    '3xl': '64px'
                },
                'borders': {
                    'radius-sm': '4px',
                    'radius-md': '8px',
                    'radius-lg': '12px',
                    'radius-xl': '16px',
                    'width-thin': '1px',
                    'width-thick': '2px'
                },
                'shadows': {
                    'sm': '0 1px 2px rgba(0, 0, 0, 0.05)',
                    'md': '0 4px 6px rgba(0, 0, 0, 0.1)',
                    'lg': '0 10px 15px rgba(0, 0, 0, 0.1)',
                    'xl': '0 20px 25px rgba(0, 0, 0, 0.1)'
                },
                'animations': {
                    'duration-fast': '150ms',
                    'duration-normal': '300ms',
                    'duration-slow': '500ms',
                    'easing-ease': 'ease',
                    'easing-ease-in': 'ease-in',
                    'easing-ease-out': 'ease-out'
                }
            }
            
            # Dark theme
            self._theme_variants[ThemeVariant.DARK] = {
                'colors': {
                    'primary': '#0078d7',
                    'primary-hover': '#106ebe',
                    'secondary': '#6b7280',
                    'success': '#10b981',
                    'warning': '#f59e0b',
                    'error': '#ef4444',
                    'background': '#2d2d2d',
                    'surface': '#3d3d3d',
                    'surface-elevated': '#505050',
                    'text-primary': '#f1f5f9',
                    'text-secondary': '#cbd5e1',
                    'text-muted': '#94a3b8',
                    'border': '#444444',
                    'border-focus': '#0078d7',
                    'shadow': 'rgba(0, 0, 0, 0.3)',
                    'overlay': 'rgba(0, 0, 0, 0.7)'
                },
                # Inherit other properties from light theme
                **{k: v for k, v in self._theme_variants[ThemeVariant.LIGHT].items() 
                   if k != 'colors'}
            }
            
            # High contrast theme
            self._theme_variants[ThemeVariant.HIGH_CONTRAST] = {
                'colors': {
                    'primary': '#0000ff',
                    'primary-hover': '#000080',
                    'secondary': '#808080',
                    'success': '#008000',
                    'warning': '#ff8000',
                    'error': '#ff0000',
                    'background': '#ffffff',
                    'surface': '#ffffff',
                    'surface-elevated': '#ffffff',
                    'text-primary': '#000000',
                    'text-secondary': '#000000',
                    'text-muted': '#404040',
                    'border': '#000000',
                    'border-focus': '#0000ff',
                    'shadow': 'rgba(0, 0, 0, 0.5)',
                    'overlay': 'rgba(0, 0, 0, 0.8)'
                },
                # Inherit other properties but with enhanced contrast
                **{k: v for k, v in self._theme_variants[ThemeVariant.LIGHT].items() 
                   if k != 'colors'}
            }
            
            # Create theme tokens from variants
            self._create_theme_tokens()
            
            self.logger.info("Built-in themes initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize built-in themes: {e}")
            self.theme_error.emit("initialization", str(e))
    
    def _create_theme_tokens(self) -> None:
        """Create theme tokens from theme variants for easier management"""
        try:
            for variant, theme_data in self._theme_variants.items():
                for category, properties in theme_data.items():
                    if isinstance(properties, dict):
                        for prop_name, prop_value in properties.items():
                            token_name = f"{category}-{prop_name}"
                            
                            if token_name not in self._theme_tokens:
                                self._theme_tokens[token_name] = ThemeToken(
                                    name=token_name,
                                    value=prop_value,
                                    category=ThemeProperty(category),
                                    description=f"Theme token for {prop_name} in {category} category"
                                )
                            
                            # Add variant-specific value
                            self._theme_tokens[token_name].variants[variant.value] = prop_value
            
            self.logger.debug(f"Created {len(self._theme_tokens)} theme tokens")
            
        except Exception as e:
            self.logger.error(f"Failed to create theme tokens: {e}")
    
    def _setup_system_theme_monitoring(self) -> None:
        """Set up monitoring for system theme changes"""
        try:
            if not self.config['system_theme_integration']:
                return
            
            self._system_theme_monitor = QTimer()
            self._system_theme_monitor.timeout.connect(self._check_system_theme)
            self._system_theme_monitor.start(self.config['auto_theme_check_interval'])
            
            self.logger.info("System theme monitoring enabled")
            
        except Exception as e:
            self.logger.error(f"Failed to setup system theme monitoring: {e}")
    
    def _check_system_theme(self) -> None:
        """Check if system theme has changed and update accordingly"""
        try:
            if self._current_theme != ThemeVariant.AUTO:
                return
            
            # Detect system theme (simplified detection)
            app = QApplication.instance()
            if app:
                palette = app.palette()
                bg_color = palette.color(QPalette.ColorRole.Window)
                
                # Simple heuristic: if background is dark, use dark theme
                brightness = (bg_color.red() + bg_color.green() + bg_color.blue()) / 3
                system_theme = ThemeVariant.DARK if brightness < 128 else ThemeVariant.LIGHT
                
                # Switch theme if it changed
                if self._get_effective_theme() != system_theme:
                    self._apply_theme_variant(system_theme)
                    self.logger.info(f"Auto-switched to {system_theme.value} theme based on system")
                    
        except Exception as e:
            self.logger.error(f"System theme check error: {e}")
    
    def switch_theme(self, theme_variant: Union[str, ThemeVariant], 
                    animate: bool = True) -> bool:
        """
        Switch to a different theme variant
        
        Args:
            theme_variant: Theme variant to switch to
            animate: Whether to animate the transition
            
        Returns:
            True if switch successful, False otherwise
        """
        with self._lock:
            try:
                # Convert string to enum if needed
                if isinstance(theme_variant, str):
                    theme_variant = ThemeVariant(theme_variant)
                
                old_theme = self._current_theme
                
                # Validate theme exists
                if theme_variant not in self._theme_variants and theme_variant != ThemeVariant.AUTO:
                    self.logger.error(f"Theme variant {theme_variant} not available")
                    return False
                
                self.logger.info(f"Switching theme from {old_theme.value} to {theme_variant.value}")
                self.theme_switch_started.emit(theme_variant.value)
                
                # Record switch start time for metrics
                switch_start = datetime.now()
                
                # Update current theme
                self._current_theme = theme_variant
                
                # Apply theme to all registered components
                effective_theme = self._get_effective_theme()
                if animate and self._transition_enabled:
                    self._animate_theme_switch(old_theme, effective_theme)
                else:
                    self._apply_theme_variant(effective_theme)
                
                # Update metrics
                switch_duration = (datetime.now() - switch_start).total_seconds() * 1000
                self._update_switch_metrics(switch_duration)
                
                # Execute theme change callbacks
                for callback in self._theme_callbacks:
                    try:
                        callback(old_theme.value, theme_variant.value)
                    except Exception as e:
                        self.logger.error(f"Theme callback error: {e}")
                
                # Persist theme choice
                if self.config['enable_user_customization']:
                    self._save_theme_preference(theme_variant)
                
                self.theme_switch_completed.emit(theme_variant.value)
                self.theme_changed.emit(old_theme.value, theme_variant.value)
                
                self.logger.info(f"Theme switched successfully in {switch_duration:.1f}ms")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to switch theme: {e}")
                self.theme_error.emit("switch_failed", str(e))
                return False
    
    def _get_effective_theme(self) -> ThemeVariant:
        """Get the effective theme variant (resolves AUTO to actual theme)"""
        if self._current_theme == ThemeVariant.AUTO:
            # Auto-detect based on system
            try:
                app = QApplication.instance()
                if app:
                    palette = app.palette()
                    bg_color = palette.color(QPalette.ColorRole.Window)
                    brightness = (bg_color.red() + bg_color.green() + bg_color.blue()) / 3
                    return ThemeVariant.DARK if brightness < 128 else ThemeVariant.LIGHT
            except:
                pass
            return ThemeVariant.LIGHT  # Default fallback
        
        return self._current_theme
    
    def _apply_theme_variant(self, theme_variant: ThemeVariant) -> None:
        """Apply theme variant to all registered components"""
        try:
            theme_data = self._theme_variants.get(theme_variant, {})
            
            for component_id, component in self._registered_components.items():
                self._apply_theme_to_component(component_id, component, theme_data)
            
            # Update Qt application palette
            self._update_application_palette(theme_data)
            
        except Exception as e:
            self.logger.error(f"Failed to apply theme variant {theme_variant}: {e}")
    
    def _apply_theme_to_component(self, component_id: str, component: QWidget, 
                                 theme_data: Dict[str, Any]) -> None:
        """Apply theme to a specific component"""
        try:
            # Get base theme properties
            base_theme = theme_data.copy()
            
            # Apply component-specific overrides
            if component_id in self._component_overrides:
                override = self._component_overrides[component_id]
                base_theme = self._merge_theme_overrides(base_theme, override.overrides)
            
            # Apply theme to component
            if hasattr(component, 'apply_theme'):
                component.apply_theme(base_theme)
            else:
                # Default theme application
                self._apply_default_theme(component, base_theme)
                
        except Exception as e:
            self.logger.error(f"Failed to apply theme to component {component_id}: {e}")
    
    def _apply_default_theme(self, component: QWidget, theme_data: Dict[str, Any]) -> None:
        """Apply default theme styling to a component"""
        try:
            colors = theme_data.get('colors', {})
            
            # Create basic stylesheet
            stylesheet = f"""
            QWidget {{
                background-color: {colors.get('surface', '#ffffff')};
                color: {colors.get('text-primary', '#000000')};
                border: 1px solid {colors.get('border', '#e0e0e0')};
                border-radius: 4px;
            }}
            QWidget:focus {{
                border-color: {colors.get('border-focus', '#3b82f6')};
            }}
            QPushButton {{
                background-color: {colors.get('primary', '#3b82f6')};
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {colors.get('primary-hover', '#2563eb')};
            }}
            """
            
            component.setStyleSheet(stylesheet)
            
        except Exception as e:
            self.logger.error(f"Failed to apply default theme: {e}")
    
    def _update_application_palette(self, theme_data: Dict[str, Any]) -> None:
        """Update Qt application palette based on theme"""
        try:
            app = QApplication.instance()
            if not app:
                return
            
            colors = theme_data.get('colors', {})
            palette = QPalette()
            
            # Set basic colors
            if 'background' in colors:
                palette.setColor(QPalette.ColorRole.Window, QColor(colors['background']))
            if 'surface' in colors:
                palette.setColor(QPalette.ColorRole.Base, QColor(colors['surface']))
            if 'text-primary' in colors:
                palette.setColor(QPalette.ColorRole.WindowText, QColor(colors['text-primary']))
                palette.setColor(QPalette.ColorRole.Text, QColor(colors['text-primary']))
            if 'primary' in colors:
                palette.setColor(QPalette.ColorRole.Highlight, QColor(colors['primary']))
            
            app.setPalette(palette)
            
        except Exception as e:
            self.logger.error(f"Failed to update application palette: {e}")
    
    def _animate_theme_switch(self, old_theme: ThemeVariant, new_theme: ThemeVariant) -> None:
        """Animate theme transition with smooth effects"""
        try:
            # Clear any existing animations
            for animation in self._transition_animations:
                animation.stop()
            self._transition_animations.clear()
            
            # Apply new theme immediately for now (animation can be enhanced later)
            self._apply_theme_variant(new_theme)
            
            # TODO: Implement sophisticated animation effects
            # - Fade transitions
            # - Color interpolation
            # - Staggered component updates
            
        except Exception as e:
            self.logger.error(f"Theme animation error: {e}")
    
    def register_component(self, component_id: str, component: QWidget) -> bool:
        """
        Register a component for theme management
        
        Args:
            component_id: Unique identifier for the component
            component: Widget component to register
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            self._registered_components[component_id] = component
            
            # Apply current theme to new component
            current_theme_data = self._theme_variants.get(self._get_effective_theme(), {})
            self._apply_theme_to_component(component_id, component, current_theme_data)
            
            self.logger.info(f"Component {component_id} registered for theme management")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register component {component_id}: {e}")
            return False
    
    def unregister_component(self, component_id: str) -> bool:
        """
        Unregister a component from theme management
        
        Args:
            component_id: ID of component to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        try:
            if component_id in self._registered_components:
                del self._registered_components[component_id]
            
            # Remove component overrides
            if component_id in self._component_overrides:
                del self._component_overrides[component_id]
            
            self.logger.info(f"Component {component_id} unregistered from theme management")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unregister component {component_id}: {e}")
            return False
    
    def add_component_override(self, component_id: str, overrides: Dict[str, Any], 
                             priority: int = 0) -> bool:
        """
        Add theme overrides for a specific component
        
        Args:
            component_id: ID of component to override
            overrides: Theme properties to override
            priority: Override priority (higher = more important)
            
        Returns:
            True if override added successfully, False otherwise
        """
        try:
            component = self._registered_components.get(component_id)
            if not component:
                self.logger.error(f"Component {component_id} not registered")
                return False
            
            override = ComponentThemeOverride(
                component_id=component_id,
                component_type=type(component).__name__,
                overrides=overrides,
                priority=priority
            )
            
            self._component_overrides[component_id] = override
            
            # Re-apply theme with new overrides
            current_theme_data = self._theme_variants.get(self._get_effective_theme(), {})
            self._apply_theme_to_component(component_id, component, current_theme_data)
            
            self._metrics.component_override_count += 1
            self.component_override_added.emit(component_id, "theme_override")
            
            self.logger.info(f"Theme override added for component {component_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add component override: {e}")
            return False
    
    def remove_component_override(self, component_id: str) -> bool:
        """Remove theme overrides for a component"""
        try:
            if component_id in self._component_overrides:
                del self._component_overrides[component_id]
                
                # Re-apply theme without overrides
                component = self._registered_components.get(component_id)
                if component:
                    current_theme_data = self._theme_variants.get(self._get_effective_theme(), {})
                    self._apply_theme_to_component(component_id, component, current_theme_data)
                
                self.logger.info(f"Theme override removed for component {component_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to remove component override: {e}")
            return False
    
    def _merge_theme_overrides(self, base_theme: Dict[str, Any], 
                              overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Merge theme overrides with base theme"""
        merged = base_theme.copy()
        
        for category, properties in overrides.items():
            if category in merged and isinstance(merged[category], dict):
                merged[category].update(properties)
            else:
                merged[category] = properties
        
        return merged
    
    def get_theme_token(self, token_name: str, variant: Optional[str] = None) -> Any:
        """Get value of a theme token for current or specified variant"""
        token = self._theme_tokens.get(token_name)
        if not token:
            return None
        
        if variant:
            return token.variants.get(variant, token.value)
        
        current_variant = self._get_effective_theme().value
        return token.variants.get(current_variant, token.value)
    
    def set_theme_token(self, token_name: str, value: Any, 
                       variant: Optional[str] = None) -> bool:
        """Set value of a theme token"""
        try:
            if token_name not in self._theme_tokens:
                self.logger.error(f"Theme token {token_name} not found")
                return False
            
            token = self._theme_tokens[token_name]
            old_value = token.value
            
            if variant:
                token.variants[variant] = value
            else:
                token.value = value
                # Update all registered components
                self._refresh_all_components()
            
            self.token_updated.emit(token_name, str(old_value), str(value))
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set theme token: {e}")
            return False
    
    def create_custom_theme(self, theme_name: str, base_theme: Union[str, ThemeVariant], 
                           customizations: Dict[str, Any]) -> bool:
        """Create a custom theme based on existing theme"""
        try:
            if isinstance(base_theme, str):
                base_theme = ThemeVariant(base_theme)
            
            base_data = self._theme_variants.get(base_theme, {})
            custom_data = self._merge_theme_overrides(base_data, customizations)
            
            self._custom_themes[theme_name] = custom_data
            self._metrics.custom_tokens_count += 1
            
            self.logger.info(f"Custom theme '{theme_name}' created")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create custom theme: {e}")
            return False
    
    def _refresh_all_components(self) -> None:
        """Refresh theme application for all registered components"""
        current_theme_data = self._theme_variants.get(self._get_effective_theme(), {})
        for component_id, component in self._registered_components.items():
            self._apply_theme_to_component(component_id, component, current_theme_data)
    
    def _update_switch_metrics(self, duration: float) -> None:
        """Update theme switch performance metrics"""
        self._metrics.switch_count += 1
        self._metrics.last_switch_time = datetime.now()
        
        # Calculate rolling average
        if self._metrics.average_switch_duration == 0:
            self._metrics.average_switch_duration = duration
        else:
            self._metrics.average_switch_duration = (
                self._metrics.average_switch_duration * 0.8 + duration * 0.2
            )
    
    def _save_theme_preference(self, theme_variant: ThemeVariant) -> None:
        """Save user theme preference to disk"""
        try:
            preferences = {
                'current_theme': theme_variant.value,
                'custom_themes': self._custom_themes,
                'component_overrides': {
                    k: asdict(v) for k, v in self._component_overrides.items()
                },
                'last_updated': datetime.now().isoformat()
            }
            
            prefs_file = self._persistence_path / 'theme_preferences.json'
            with open(prefs_file, 'w', encoding='utf-8') as f:
                json.dump(preferences, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save theme preferences: {e}")
    
    def _load_user_customizations(self) -> None:
        """Load user theme customizations from disk"""
        try:
            prefs_file = self._persistence_path / 'theme_preferences.json'
            if not prefs_file.exists():
                return
            
            with open(prefs_file, 'r', encoding='utf-8') as f:
                preferences = json.load(f)
            
            # Load custom themes
            self._custom_themes = preferences.get('custom_themes', {})
            
            # Restore previous theme
            saved_theme = preferences.get('current_theme')
            if saved_theme:
                try:
                    self._current_theme = ThemeVariant(saved_theme)
                except ValueError:
                    pass
            
            self.logger.info("User theme customizations loaded")
            
        except Exception as e:
            self.logger.error(f"Failed to load user customizations: {e}")
    
    def add_theme_callback(self, callback: Callable[[str, str], None]) -> None:
        """Add callback for theme change events"""
        self._theme_callbacks.append(callback)
    
    def remove_theme_callback(self, callback: Callable) -> None:
        """Remove theme change callback"""
        try:
            self._theme_callbacks.remove(callback)
        except ValueError:
            pass
    
    def get_current_theme(self) -> ThemeVariant:
        """Get current theme variant"""
        return self._current_theme
    
    def get_effective_theme_data(self) -> Dict[str, Any]:
        """Get current effective theme data"""
        return self._theme_variants.get(self._get_effective_theme(), {})
    
    def get_available_themes(self) -> List[str]:
        """Get list of available theme variants"""
        builtin = [variant.value for variant in self._theme_variants.keys()]
        custom = list(self._custom_themes.keys())
        return builtin + custom
    
    def get_theme_metrics(self) -> ThemeMetrics:
        """Get theme usage metrics"""
        return self._metrics
    
    def preview_theme(self, theme_variant: Union[str, ThemeVariant], 
                     component_id: Optional[str] = None) -> None:
        """Preview a theme without permanently switching"""
        # TODO: Implement theme preview functionality
        # This would temporarily apply theme to specific component or all components
        # for preview purposes without changing the current theme
        pass
    
    def export_theme(self, theme_variant: Union[str, ThemeVariant], 
                    export_path: str) -> bool:
        """Export theme configuration to file"""
        try:
            if isinstance(theme_variant, str):
                if theme_variant in self._custom_themes:
                    theme_data = self._custom_themes[theme_variant]
                else:
                    theme_variant = ThemeVariant(theme_variant)
                    theme_data = self._theme_variants[theme_variant]
            else:
                theme_data = self._theme_variants[theme_variant]
            
            export_data = {
                'theme_name': theme_variant.value if isinstance(theme_variant, ThemeVariant) else theme_variant,
                'theme_data': theme_data,
                'metadata': {
                    'exported_at': datetime.now().isoformat(),
                    'version': '1.0'
                }
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            self.logger.info(f"Theme exported to {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export theme: {e}")
            return False
    
    def import_theme(self, import_path: str, theme_name: Optional[str] = None) -> bool:
        """Import theme configuration from file"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            theme_data = import_data.get('theme_data', {})
            imported_name = theme_name or import_data.get('theme_name', 'imported_theme')
            
            self._custom_themes[imported_name] = theme_data
            
            self.logger.info(f"Theme imported as '{imported_name}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import theme: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown the theme manager"""
        try:
            self.logger.info("Shutting down ThemeManager")
            
            # Stop system theme monitoring
            if self._system_theme_monitor:
                self._system_theme_monitor.stop()
            
            # Stop any running animations
            for animation in self._transition_animations:
                animation.stop()
            
            # Save user preferences
            if self.config['enable_user_customization']:
                self._save_theme_preference(self._current_theme)
            
            self.logger.info("ThemeManager shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during ThemeManager shutdown: {e}")


# Factory function for creating theme manager instances
def create_theme_manager(config: Optional[Dict[str, Any]] = None) -> ThemeManager:
    """Create a new theme manager instance with optional configuration"""
    return ThemeManager(config)


# Global instance management
_global_theme_manager: Optional[ThemeManager] = None


def get_global_theme_manager() -> ThemeManager:
    """Get or create the global theme manager instance"""
    global _global_theme_manager
    
    if _global_theme_manager is None:
        _global_theme_manager = ThemeManager()
    
    return _global_theme_manager


def set_global_theme_manager(manager: ThemeManager) -> None:
    """Set the global theme manager instance"""
    global _global_theme_manager
    _global_theme_manager = manager 