"""
Enhanced Internationalization Manager for v2.0 UI Architecture

This module provides comprehensive internationalization support including:
- Dynamic language loading and switching without restart
- Right-to-left (RTL) layout support for Arabic, Hebrew, etc.
- Locale-specific formatting for numbers, dates, currencies
- Translation management tools and content editing
- Pluralization rules for different languages
- Context-aware translations and gender support
- Translation validation and automated testing
- Performance-optimized translation caching
"""

import logging
import threading
import json
import re
import os
import locale
from typing import Dict, Any, Optional, Callable, List, Set, Union, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from enum import Enum, auto
from pathlib import Path
from collections import defaultdict
import weakref
from decimal import Decimal
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QLocale
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)


class TextDirection(Enum):
    """Text direction for different languages"""
    LTR = "ltr"  # Left-to-right
    RTL = "rtl"  # Right-to-left
    AUTO = "auto"  # Auto-detect based on content


class PluralForm(Enum):
    """Plural forms for different languages"""
    ZERO = "zero"
    ONE = "one"
    TWO = "two"
    FEW = "few"
    MANY = "many"
    OTHER = "other"


class TranslationContext(Enum):
    """Translation context for disambiguation"""
    UI_BUTTON = "ui_button"
    UI_MENU = "ui_menu"
    UI_TOOLTIP = "ui_tooltip"
    MESSAGE = "message"
    ERROR = "error"
    TITLE = "title"
    DESCRIPTION = "description"
    LABEL = "label"
    PLACEHOLDER = "placeholder"
    CUSTOM = "custom"


@dataclass
class LanguageInfo:
    """Language configuration and metadata"""
    code: str  # ISO 639-1 code (e.g., 'en', 'zh')
    name: str  # Native language name
    english_name: str  # English name
    direction: TextDirection = TextDirection.LTR
    
    # Locale settings
    locale_code: str = ""  # Full locale code (e.g., 'en_US', 'zh_CN')
    country: str = ""
    region: str = ""
    
    # Formatting
    decimal_separator: str = "."
    thousands_separator: str = ","
    currency_symbol: str = "$"
    currency_position: str = "before"  # "before" or "after"
    
    # Date/time formatting
    date_format: str = "%Y-%m-%d"
    time_format: str = "%H:%M:%S"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    
    # Text settings
    font_family: Optional[str] = None
    font_size_adjustment: float = 1.0
    line_height_adjustment: float = 1.0
    
    # Pluralization
    plural_rules: Dict[PluralForm, str] = field(default_factory=dict)
    
    # Status
    enabled: bool = True
    progress: float = 0.0  # Translation completion percentage
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class TranslationEntry:
    """Individual translation entry"""
    key: str
    source_text: str
    translated_text: str
    context: TranslationContext = TranslationContext.CUSTOM
    
    # Metadata
    description: str = ""
    plural_forms: Dict[PluralForm, str] = field(default_factory=dict)
    variables: List[str] = field(default_factory=list)
    max_length: Optional[int] = None
    
    # Status
    approved: bool = False
    fuzzy: bool = False
    needs_review: bool = False
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    translator: str = ""
    reviewer: str = ""


@dataclass
class TranslationValidationError:
    """Translation validation error"""
    key: str
    language: str
    error_type: str
    message: str
    severity: str  # "error", "warning", "info"
    suggestion: Optional[str] = None


@dataclass
class I18nMetrics:
    """Internationalization metrics and statistics"""
    total_translations: int = 0
    completed_translations: int = 0
    pending_translations: int = 0
    
    # Language statistics
    language_coverage: Dict[str, float] = field(default_factory=dict)
    translation_quality_scores: Dict[str, float] = field(default_factory=dict)
    
    # Performance
    cache_hit_rate: float = 0.0
    average_lookup_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    
    # Validation
    validation_errors: int = 0
    validation_warnings: int = 0
    last_validation: Optional[datetime] = None


class I18nManager(QObject):
    """
    Enhanced internationalization manager providing comprehensive i18n support,
    dynamic language switching, RTL layouts, and translation management
    for v2.0 UI architecture.
    """
    
    # Signals for i18n events
    language_changed = pyqtSignal(str, str)  # old_language, new_language
    translation_loaded = pyqtSignal(str, int)  # language, translation_count
    direction_changed = pyqtSignal(str)  # new_direction
    locale_changed = pyqtSignal(str)  # new_locale
    translation_missing = pyqtSignal(str, str)  # key, language
    validation_completed = pyqtSignal(str, int, int)  # language, errors, warnings
    font_changed = pyqtSignal(str, str)  # language, font_family
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = self._create_default_config()
        if config:
            self.config.update(config)
        
        # Core state
        self._current_language = self.config['default_language']
        self._languages: Dict[str, LanguageInfo] = {}
        self._translations: Dict[str, Dict[str, TranslationEntry]] = {}
        self._translation_cache: Dict[str, str] = {}
        self._registered_components: Dict[str, QWidget] = {}
        
        # Pluralization and formatting
        self._plural_evaluators: Dict[str, Callable] = {}
        self._number_formatters: Dict[str, Callable] = {}
        self._date_formatters: Dict[str, Callable] = {}
        
        # Translation management
        self._fallback_language = self.config['fallback_language']
        self._missing_translations: Set[Tuple[str, str]] = set()  # (key, language)
        self._validation_errors: List[TranslationValidationError] = []
        
        # Performance tracking
        self._metrics = I18nMetrics()
        self._lookup_times: List[float] = []
        
        # Storage paths
        self._translations_path = Path(self.config['translations_path'])
        self._translations_path.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Auto-validation timer
        self._validation_timer: Optional[QTimer] = None
        
        # Initialize system
        self._load_builtin_languages()
        self._load_translations()
        self._setup_auto_validation()
        
        self.logger.info(f"I18nManager initialized with config: {self.config}")
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration for i18n manager"""
        return {
            'default_language': 'en',
            'fallback_language': 'en',
            'translations_path': 'data/translations',
            'enable_auto_validation': True,
            'enable_translation_cache': True,
            'enable_rtl_support': True,
            'enable_font_adjustment': True,
            'validation_interval_hours': 24,
            'cache_size_limit': 10000,
            'auto_detect_language': True,
            'enable_pluralization': True,
            'enable_gender_support': False,
            'translation_timeout_ms': 100
        }
    
    def _load_builtin_languages(self) -> None:
        """Load built-in language configurations"""
        try:
            # English (default)
            self._languages['en'] = LanguageInfo(
                code='en',
                name='English',
                english_name='English',
                direction=TextDirection.LTR,
                locale_code='en_US',
                country='US',
                region='Americas',
                plural_rules={
                    PluralForm.ONE: 'n == 1',
                    PluralForm.OTHER: 'n != 1'
                }
            )
            
            # Spanish
            self._languages['es'] = LanguageInfo(
                code='es',
                name='Español',
                english_name='Spanish',
                direction=TextDirection.LTR,
                locale_code='es_ES',
                country='ES',
                region='Europe',
                decimal_separator=',',
                thousands_separator='.',
                currency_symbol='€',
                plural_rules={
                    PluralForm.ONE: 'n == 1',
                    PluralForm.OTHER: 'n != 1'
                }
            )
            
            # Chinese Simplified
            self._languages['zh'] = LanguageInfo(
                code='zh',
                name='中文',
                english_name='Chinese',
                direction=TextDirection.LTR,
                locale_code='zh_CN',
                country='CN',
                region='Asia',
                currency_symbol='¥',
                font_family='SimSun, Microsoft YaHei',
                plural_rules={
                    PluralForm.OTHER: 'true'  # Chinese has no plural forms
                }
            )
            
            # Arabic
            self._languages['ar'] = LanguageInfo(
                code='ar',
                name='العربية',
                english_name='Arabic',
                direction=TextDirection.RTL,
                locale_code='ar_SA',
                country='SA',
                region='Middle East',
                decimal_separator='.',
                thousands_separator=',',
                currency_symbol='ر.س',
                currency_position='after',
                font_family='Tahoma, Arial Unicode MS',
                font_size_adjustment=1.1,
                plural_rules={
                    PluralForm.ZERO: 'n == 0',
                    PluralForm.ONE: 'n == 1',
                    PluralForm.TWO: 'n == 2',
                    PluralForm.FEW: 'n % 100 >= 3 && n % 100 <= 10',
                    PluralForm.MANY: 'n % 100 >= 11 && n % 100 <= 99',
                    PluralForm.OTHER: 'true'
                }
            )
            
            # Hebrew
            self._languages['he'] = LanguageInfo(
                code='he',
                name='עברית',
                english_name='Hebrew',
                direction=TextDirection.RTL,
                locale_code='he_IL',
                country='IL',
                region='Middle East',
                currency_symbol='₪',
                font_family='David, Arial Unicode MS',
                plural_rules={
                    PluralForm.ONE: 'n == 1',
                    PluralForm.TWO: 'n == 2',
                    PluralForm.MANY: 'n % 10 == 0 && n != 0',
                    PluralForm.OTHER: 'true'
                }
            )
            
            # Japanese
            self._languages['ja'] = LanguageInfo(
                code='ja',
                name='日本語',
                english_name='Japanese',
                direction=TextDirection.LTR,
                locale_code='ja_JP',
                country='JP',
                region='Asia',
                currency_symbol='¥',
                font_family='Meiryo, MS Gothic',
                plural_rules={
                    PluralForm.OTHER: 'true'  # Japanese has no plural forms
                }
            )
            
            # Initialize plural evaluators
            for lang_code, lang_info in self._languages.items():
                self._create_plural_evaluator(lang_code, lang_info.plural_rules)
            
            self.logger.info(f"Loaded {len(self._languages)} built-in languages")
            
        except Exception as e:
            self.logger.error(f"Failed to load built-in languages: {e}")
    
    def _create_plural_evaluator(self, language: str, rules: Dict[PluralForm, str]) -> None:
        """Create plural evaluation function for a language"""
        try:
            def evaluate_plural(n: Union[int, float]) -> PluralForm:
                # Convert to int for evaluation
                n_int = int(n)
                
                # Evaluate rules in order
                for form, rule in rules.items():
                    try:
                        # Safe evaluation of plural rule
                        if eval(rule, {"n": n_int, "true": True, "false": False}):
                            return form
                    except:
                        continue
                
                return PluralForm.OTHER
            
            self._plural_evaluators[language] = evaluate_plural
            
        except Exception as e:
            self.logger.error(f"Failed to create plural evaluator for {language}: {e}")
    
    def _load_translations(self) -> None:
        """Load translations from files"""
        try:
            loaded_count = 0
            
            for lang_file in self._translations_path.glob("*.json"):
                lang_code = lang_file.stem
                
                try:
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        translation_data = json.load(f)
                    
                    # Convert to TranslationEntry objects
                    self._translations[lang_code] = {}
                    
                    for key, data in translation_data.items():
                        if isinstance(data, str):
                            # Simple string translation
                            entry = TranslationEntry(
                                key=key,
                                source_text=data,
                                translated_text=data
                            )
                        else:
                            # Complex translation entry
                            entry = TranslationEntry(
                                key=key,
                                source_text=data.get('source', ''),
                                translated_text=data.get('text', ''),
                                context=TranslationContext(data.get('context', 'custom')),
                                description=data.get('description', ''),
                                plural_forms={
                                    PluralForm(k): v for k, v in data.get('plural', {}).items()
                                },
                                approved=data.get('approved', False),
                                fuzzy=data.get('fuzzy', False)
                            )
                        
                        self._translations[lang_code][key] = entry
                    
                    loaded_count += len(self._translations[lang_code])
                    
                    # Update language progress
                    if lang_code in self._languages:
                        total_keys = len(self._get_all_translation_keys())
                        translated_keys = len(self._translations[lang_code])
                        self._languages[lang_code].progress = (translated_keys / total_keys) * 100 if total_keys > 0 else 0
                    
                    self.translation_loaded.emit(lang_code, len(self._translations[lang_code]))
                    
                except Exception as e:
                    self.logger.error(f"Failed to load translations for {lang_code}: {e}")
            
            self.logger.info(f"Loaded {loaded_count} translations for {len(self._translations)} languages")
            
        except Exception as e:
            self.logger.error(f"Failed to load translations: {e}")
    
    def _get_all_translation_keys(self) -> Set[str]:
        """Get all unique translation keys across all languages"""
        all_keys = set()
        for translations in self._translations.values():
            all_keys.update(translations.keys())
        return all_keys
    
    def _setup_auto_validation(self) -> None:
        """Set up automatic translation validation"""
        if not self.config['enable_auto_validation']:
            return
        
        try:
            self._validation_timer = QTimer()
            self._validation_timer.timeout.connect(self._run_validation)
            self._validation_timer.start(self.config['validation_interval_hours'] * 3600000)
            
            self.logger.info("Auto-validation enabled")
            
        except Exception as e:
            self.logger.error(f"Failed to setup auto-validation: {e}")
    
    def set_language(self, language: str, force_reload: bool = False) -> bool:
        """
        Set the current language and apply to all registered components
        
        Args:
            language: Language code to switch to
            force_reload: Force reload of translations
            
        Returns:
            True if language change successful, False otherwise
        """
        with self._lock:
            try:
                if language not in self._languages:
                    self.logger.error(f"Language {language} not available")
                    return False
                
                old_language = self._current_language
                
                if old_language == language and not force_reload:
                    return True
                
                self.logger.info(f"Switching language from {old_language} to {language}")
                
                # Update current language
                self._current_language = language
                
                # Clear translation cache if enabled
                if self.config['enable_translation_cache']:
                    self._translation_cache.clear()
                
                # Apply language to all registered components
                self._apply_language_to_components(language)
                
                # Update application locale
                self._update_application_locale(language)
                
                # Apply RTL/LTR layout changes
                self._apply_text_direction(language)
                
                # Apply font changes if needed
                self._apply_font_adjustments(language)
                
                # Emit signals
                self.language_changed.emit(old_language, language)
                
                lang_info = self._languages[language]
                if lang_info.direction != self._languages[old_language].direction:
                    self.direction_changed.emit(lang_info.direction.value)
                
                self.locale_changed.emit(lang_info.locale_code)
                
                if lang_info.font_family:
                    self.font_changed.emit(language, lang_info.font_family)
                
                self.logger.info(f"Language switched to {language} successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to set language to {language}: {e}")
                return False
    
    def _apply_language_to_components(self, language: str) -> None:
        """Apply language changes to all registered components"""
        try:
            for component_id, component in self._registered_components.items():
                if hasattr(component, 'retranslate_ui'):
                    component.retranslate_ui()
                elif hasattr(component, 'update_translations'):
                    component.update_translations(language)
                
                # Update component direction if RTL support enabled
                if self.config['enable_rtl_support']:
                    direction = self._languages[language].direction
                    if hasattr(component, 'setLayoutDirection'):
                        from PyQt6.QtCore import Qt
                        qt_direction = Qt.LayoutDirection.RightToLeft if direction == TextDirection.RTL else Qt.LayoutDirection.LeftToRight
                        component.setLayoutDirection(qt_direction)
                        
        except Exception as e:
            self.logger.error(f"Failed to apply language to components: {e}")
    
    def _update_application_locale(self, language: str) -> None:
        """Update Qt application locale"""
        try:
            lang_info = self._languages[language]
            qt_locale = QLocale(lang_info.locale_code)
            QLocale.setDefault(qt_locale)
            
            # Update system locale if possible
            try:
                locale.setlocale(locale.LC_ALL, lang_info.locale_code)
            except locale.Error:
                # Fallback to C locale
                locale.setlocale(locale.LC_ALL, 'C')
                
        except Exception as e:
            self.logger.error(f"Failed to update application locale: {e}")
    
    def _apply_text_direction(self, language: str) -> None:
        """Apply text direction changes for RTL languages"""
        if not self.config['enable_rtl_support']:
            return
        
        try:
            lang_info = self._languages[language]
            app = QApplication.instance()
            
            if app and lang_info.direction == TextDirection.RTL:
                from PyQt6.QtCore import Qt
                app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            elif app:
                from PyQt6.QtCore import Qt
                app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
                
        except Exception as e:
            self.logger.error(f"Failed to apply text direction: {e}")
    
    def _apply_font_adjustments(self, language: str) -> None:
        """Apply font adjustments for specific languages"""
        if not self.config['enable_font_adjustment']:
            return
        
        try:
            lang_info = self._languages[language]
            
            if lang_info.font_family:
                app = QApplication.instance()
                if app:
                    font = app.font()
                    font.setFamily(lang_info.font_family)
                    
                    if lang_info.font_size_adjustment != 1.0:
                        new_size = int(font.pointSize() * lang_info.font_size_adjustment)
                        font.setPointSize(new_size)
                    
                    app.setFont(font)
                    
        except Exception as e:
            self.logger.error(f"Failed to apply font adjustments: {e}")
    
    def translate(self, key: str, context: Optional[TranslationContext] = None,
                 variables: Optional[Dict[str, Any]] = None,
                 count: Optional[int] = None, language: Optional[str] = None) -> str:
        """
        Translate a text key with optional context and variables
        
        Args:
            key: Translation key
            context: Translation context for disambiguation
            variables: Variables for string interpolation
            count: Count for pluralization
            language: Specific language (defaults to current)
            
        Returns:
            Translated text or original key if not found
        """
        lookup_start = datetime.now()
        
        try:
            target_language = language or self._current_language
            
            # Check cache first
            cache_key = f"{target_language}:{key}:{count}"
            if self.config['enable_translation_cache'] and cache_key in self._translation_cache:
                return self._translation_cache[cache_key]
            
            # Get translation entry
            translation_entry = self._get_translation_entry(key, target_language, context)
            
            if not translation_entry:
                # Try fallback language
                if target_language != self._fallback_language:
                    translation_entry = self._get_translation_entry(key, self._fallback_language, context)
                
                if not translation_entry:
                    # Mark as missing and return key
                    self._missing_translations.add((key, target_language))
                    self.translation_missing.emit(key, target_language)
                    return key
            
            # Get appropriate text based on pluralization
            if count is not None and self.config['enable_pluralization']:
                translated_text = self._get_plural_text(translation_entry, count, target_language)
            else:
                translated_text = translation_entry.translated_text
            
            # Apply variable substitution
            if variables:
                translated_text = self._substitute_variables(translated_text, variables)
            
            # Cache the result
            if self.config['enable_translation_cache']:
                if len(self._translation_cache) >= self.config['cache_size_limit']:
                    # Remove oldest entries (simple FIFO)
                    oldest_keys = list(self._translation_cache.keys())[:100]
                    for old_key in oldest_keys:
                        del self._translation_cache[old_key]
                
                self._translation_cache[cache_key] = translated_text
            
            # Update performance metrics
            lookup_time = (datetime.now() - lookup_start).total_seconds() * 1000
            self._lookup_times.append(lookup_time)
            if len(self._lookup_times) > 1000:
                self._lookup_times = self._lookup_times[-1000:]
            
            return translated_text
            
        except Exception as e:
            self.logger.error(f"Translation failed for key '{key}': {e}")
            return key
    
    def _get_translation_entry(self, key: str, language: str, 
                              context: Optional[TranslationContext]) -> Optional[TranslationEntry]:
        """Get translation entry for key, language, and context"""
        if language not in self._translations:
            return None
        
        translations = self._translations[language]
        
        # Try exact key match first
        if key in translations:
            entry = translations[key]
            # Check context match if specified
            if context is None or entry.context == context:
                return entry
        
        # Try context-specific key
        if context:
            context_key = f"{context.value}.{key}"
            if context_key in translations:
                return translations[context_key]
        
        return None
    
    def _get_plural_text(self, entry: TranslationEntry, count: int, language: str) -> str:
        """Get appropriate plural form for count"""
        try:
            if not entry.plural_forms:
                return entry.translated_text
            
            # Get plural evaluator for language
            evaluator = self._plural_evaluators.get(language)
            if not evaluator:
                return entry.translated_text
            
            # Evaluate plural form
            plural_form = evaluator(count)
            
            # Get text for plural form
            if plural_form in entry.plural_forms:
                return entry.plural_forms[plural_form]
            
            # Fallback to base text
            return entry.translated_text
            
        except Exception as e:
            self.logger.error(f"Plural evaluation failed: {e}")
            return entry.translated_text
    
    def _substitute_variables(self, text: str, variables: Dict[str, Any]) -> str:
        """Substitute variables in translated text"""
        try:
            # Support both {variable} and %(variable)s formats
            for var_name, var_value in variables.items():
                # Format value based on current language locale
                formatted_value = self._format_variable(var_value)
                
                # Replace both formats
                text = text.replace(f"{{{var_name}}}", str(formatted_value))
                text = text.replace(f"%({var_name})s", str(formatted_value))
            
            return text
            
        except Exception as e:
            self.logger.error(f"Variable substitution failed: {e}")
            return text
    
    def _format_variable(self, value: Any) -> str:
        """Format variable value according to current language locale"""
        try:
            lang_info = self._languages[self._current_language]
            
            if isinstance(value, (int, float, Decimal)):
                return self.format_number(value)
            elif isinstance(value, (date, datetime)):
                return self.format_date(value)
            else:
                return str(value)
                
        except Exception as e:
            self.logger.error(f"Variable formatting failed: {e}")
            return str(value)
    
    def format_number(self, number: Union[int, float, Decimal], 
                     language: Optional[str] = None) -> str:
        """Format number according to language locale"""
        try:
            target_language = language or self._current_language
            lang_info = self._languages[target_language]
            
            # Convert to string with appropriate decimal places
            if isinstance(number, int):
                number_str = str(number)
            else:
                number_str = f"{number:.2f}"
            
            # Split integer and decimal parts
            if '.' in number_str:
                integer_part, decimal_part = number_str.split('.')
            else:
                integer_part, decimal_part = number_str, ""
            
            # Add thousands separators
            if len(integer_part) > 3:
                # Insert separators from right to left
                formatted_integer = ""
                for i, digit in enumerate(reversed(integer_part)):
                    if i > 0 and i % 3 == 0:
                        formatted_integer = lang_info.thousands_separator + formatted_integer
                    formatted_integer = digit + formatted_integer
                integer_part = formatted_integer
            
            # Combine with decimal separator
            if decimal_part:
                return f"{integer_part}{lang_info.decimal_separator}{decimal_part}"
            else:
                return integer_part
                
        except Exception as e:
            self.logger.error(f"Number formatting failed: {e}")
            return str(number)
    
    def format_currency(self, amount: Union[int, float, Decimal],
                       language: Optional[str] = None) -> str:
        """Format currency according to language locale"""
        try:
            target_language = language or self._current_language
            lang_info = self._languages[target_language]
            
            formatted_number = self.format_number(amount, target_language)
            
            if lang_info.currency_position == "before":
                return f"{lang_info.currency_symbol}{formatted_number}"
            else:
                return f"{formatted_number} {lang_info.currency_symbol}"
                
        except Exception as e:
            self.logger.error(f"Currency formatting failed: {e}")
            return str(amount)
    
    def format_date(self, date_obj: Union[date, datetime], 
                   language: Optional[str] = None) -> str:
        """Format date according to language locale"""
        try:
            target_language = language or self._current_language
            lang_info = self._languages[target_language]
            
            if isinstance(date_obj, datetime):
                return date_obj.strftime(lang_info.datetime_format)
            else:
                return date_obj.strftime(lang_info.date_format)
                
        except Exception as e:
            self.logger.error(f"Date formatting failed: {e}")
            return str(date_obj)
    
    def register_component(self, component_id: str, component: QWidget) -> bool:
        """Register a component for automatic retranslation"""
        try:
            self._registered_components[component_id] = component
            
            # Apply current language to new component
            if hasattr(component, 'retranslate_ui'):
                component.retranslate_ui()
            
            self.logger.info(f"Component {component_id} registered for i18n")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register component {component_id}: {e}")
            return False
    
    def unregister_component(self, component_id: str) -> bool:
        """Unregister a component from automatic retranslation"""
        try:
            if component_id in self._registered_components:
                del self._registered_components[component_id]
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to unregister component {component_id}: {e}")
            return False
    
    def add_translation(self, key: str, language: str, text: str,
                       context: Optional[TranslationContext] = None,
                       description: str = "", plural_forms: Dict[PluralForm, str] = None) -> bool:
        """Add or update a translation"""
        with self._lock:
            try:
                if language not in self._translations:
                    self._translations[language] = {}
                
                entry = TranslationEntry(
                    key=key,
                    source_text=text,
                    translated_text=text,
                    context=context or TranslationContext.CUSTOM,
                    description=description,
                    plural_forms=plural_forms or {}
                )
                
                self._translations[language][key] = entry
                
                # Clear cache for this key
                if self.config['enable_translation_cache']:
                    cache_keys_to_remove = [k for k in self._translation_cache.keys() if k.startswith(f"{language}:{key}")]
                    for cache_key in cache_keys_to_remove:
                        del self._translation_cache[cache_key]
                
                self.logger.info(f"Translation added: {language}:{key}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to add translation: {e}")
                return False
    
    def remove_translation(self, key: str, language: str) -> bool:
        """Remove a translation"""
        with self._lock:
            try:
                if language in self._translations and key in self._translations[language]:
                    del self._translations[language][key]
                    
                    # Clear cache
                    if self.config['enable_translation_cache']:
                        cache_keys_to_remove = [k for k in self._translation_cache.keys() if k.startswith(f"{language}:{key}")]
                        for cache_key in cache_keys_to_remove:
                            del self._translation_cache[cache_key]
                    
                    return True
                return False
                
            except Exception as e:
                self.logger.error(f"Failed to remove translation: {e}")
                return False
    
    def _run_validation(self) -> None:
        """Run comprehensive translation validation"""
        try:
            self.logger.info("Starting translation validation")
            self._validation_errors.clear()
            
            error_count = 0
            warning_count = 0
            
            for language, translations in self._translations.items():
                lang_errors, lang_warnings = self._validate_language(language, translations)
                error_count += lang_errors
                warning_count += lang_warnings
            
            # Update metrics
            self._metrics.validation_errors = error_count
            self._metrics.validation_warnings = warning_count
            self._metrics.last_validation = datetime.now()
            
            # Emit validation completed signal
            self.validation_completed.emit("all", error_count, warning_count)
            
            self.logger.info(f"Validation completed: {error_count} errors, {warning_count} warnings")
            
        except Exception as e:
            self.logger.error(f"Translation validation failed: {e}")
    
    def _validate_language(self, language: str, translations: Dict[str, TranslationEntry]) -> Tuple[int, int]:
        """Validate translations for a specific language"""
        error_count = 0
        warning_count = 0
        
        try:
            all_keys = self._get_all_translation_keys()
            
            # Check for missing translations
            for key in all_keys:
                if key not in translations:
                    self._validation_errors.append(TranslationValidationError(
                        key=key,
                        language=language,
                        error_type="missing_translation",
                        message=f"Translation missing for key '{key}'",
                        severity="warning"
                    ))
                    warning_count += 1
            
            # Check individual translations
            for key, entry in translations.items():
                # Check for empty translations
                if not entry.translated_text.strip():
                    self._validation_errors.append(TranslationValidationError(
                        key=key,
                        language=language,
                        error_type="empty_translation",
                        message="Translation is empty",
                        severity="error"
                    ))
                    error_count += 1
                
                # Check for variable consistency
                source_vars = set(re.findall(r'\{(\w+)\}', entry.source_text))
                translated_vars = set(re.findall(r'\{(\w+)\}', entry.translated_text))
                
                if source_vars != translated_vars:
                    missing_vars = source_vars - translated_vars
                    extra_vars = translated_vars - source_vars
                    
                    message = "Variable mismatch: "
                    if missing_vars:
                        message += f"missing {missing_vars}, "
                    if extra_vars:
                        message += f"extra {extra_vars}"
                    
                    self._validation_errors.append(TranslationValidationError(
                        key=key,
                        language=language,
                        error_type="variable_mismatch",
                        message=message,
                        severity="error"
                    ))
                    error_count += 1
                
                # Check length constraints
                if entry.max_length and len(entry.translated_text) > entry.max_length:
                    self._validation_errors.append(TranslationValidationError(
                        key=key,
                        language=language,
                        error_type="length_exceeded",
                        message=f"Translation too long: {len(entry.translated_text)} > {entry.max_length}",
                        severity="warning"
                    ))
                    warning_count += 1
            
        except Exception as e:
            self.logger.error(f"Language validation failed for {language}: {e}")
        
        return error_count, warning_count
    
    def get_available_languages(self) -> List[LanguageInfo]:
        """Get list of available languages"""
        return list(self._languages.values())
    
    def get_current_language(self) -> str:
        """Get current language code"""
        return self._current_language
    
    def get_language_info(self, language: str) -> Optional[LanguageInfo]:
        """Get language information"""
        return self._languages.get(language)
    
    def get_missing_translations(self, language: Optional[str] = None) -> List[str]:
        """Get list of missing translation keys"""
        if language:
            return [key for key, lang in self._missing_translations if lang == language]
        else:
            return list(set(key for key, lang in self._missing_translations))
    
    def get_validation_errors(self, language: Optional[str] = None) -> List[TranslationValidationError]:
        """Get validation errors"""
        if language:
            return [error for error in self._validation_errors if error.language == language]
        else:
            return self._validation_errors.copy()
    
    def get_i18n_metrics(self) -> I18nMetrics:
        """Get internationalization metrics"""
        # Update cache hit rate
        if self._lookup_times:
            self._metrics.average_lookup_time_ms = sum(self._lookup_times) / len(self._lookup_times)
        
        # Update language coverage
        all_keys = self._get_all_translation_keys()
        total_keys = len(all_keys)
        
        for language, translations in self._translations.items():
            if total_keys > 0:
                coverage = (len(translations) / total_keys) * 100
                self._metrics.language_coverage[language] = coverage
        
        # Update translation counts
        self._metrics.total_translations = sum(len(translations) for translations in self._translations.values())
        
        return self._metrics
    
    def export_translations(self, language: str, export_path: str, format: str = "json") -> bool:
        """Export translations to file"""
        try:
            if language not in self._translations:
                return False
            
            translations = self._translations[language]
            
            if format.lower() == "json":
                export_data = {}
                for key, entry in translations.items():
                    export_data[key] = {
                        'text': entry.translated_text,
                        'context': entry.context.value,
                        'description': entry.description,
                        'approved': entry.approved,
                        'fuzzy': entry.fuzzy
                    }
                    
                    if entry.plural_forms:
                        export_data[key]['plural'] = {
                            form.value: text for form, text in entry.plural_forms.items()
                        }
                
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Translations exported for {language} to {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export translations: {e}")
            return False
    
    def import_translations(self, language: str, import_path: str) -> bool:
        """Import translations from file"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if language not in self._translations:
                self._translations[language] = {}
            
            imported_count = 0
            
            for key, data in import_data.items():
                if isinstance(data, str):
                    # Simple format
                    entry = TranslationEntry(
                        key=key,
                        source_text=data,
                        translated_text=data
                    )
                else:
                    # Complex format
                    entry = TranslationEntry(
                        key=key,
                        source_text=data.get('source', ''),
                        translated_text=data.get('text', ''),
                        context=TranslationContext(data.get('context', 'custom')),
                        description=data.get('description', ''),
                        approved=data.get('approved', False),
                        fuzzy=data.get('fuzzy', False)
                    )
                    
                    if 'plural' in data:
                        entry.plural_forms = {
                            PluralForm(k): v for k, v in data['plural'].items()
                        }
                
                self._translations[language][key] = entry
                imported_count += 1
            
            # Clear cache
            if self.config['enable_translation_cache']:
                self._translation_cache.clear()
            
            self.logger.info(f"Imported {imported_count} translations for {language}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import translations: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown the i18n manager"""
        with self._lock:
            try:
                self.logger.info("Shutting down I18nManager")
                
                # Stop validation timer
                if self._validation_timer:
                    self._validation_timer.stop()
                
                # Save any pending translations
                # (Implementation would depend on auto-save requirements)
                
                self.logger.info("I18nManager shutdown completed")
                
            except Exception as e:
                self.logger.error(f"Error during I18nManager shutdown: {e}")


# Factory function for creating i18n manager instances
def create_i18n_manager(config: Optional[Dict[str, Any]] = None) -> I18nManager:
    """Create a new i18n manager instance with optional configuration"""
    return I18nManager(config)


# Global instance management
_global_i18n_manager: Optional[I18nManager] = None


def get_global_i18n_manager() -> I18nManager:
    """Get or create the global i18n manager instance"""
    global _global_i18n_manager
    
    if _global_i18n_manager is None:
        _global_i18n_manager = I18nManager()
    
    return _global_i18n_manager


def set_global_i18n_manager(manager: I18nManager) -> None:
    """Set the global i18n manager instance"""
    global _global_i18n_manager
    _global_i18n_manager = manager


# Convenience functions for global usage
def _(key: str, **kwargs) -> str:
    """Convenience function for translation (similar to gettext)"""
    return get_global_i18n_manager().translate(key, **kwargs)


def ngettext(singular_key: str, plural_key: str, count: int, **kwargs) -> str:
    """Convenience function for plural translations"""
    return get_global_i18n_manager().translate(
        singular_key, count=count, **kwargs
    ) 