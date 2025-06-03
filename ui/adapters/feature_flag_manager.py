"""
Central Feature Flag Management System for UI v1.2.1 to v2.0 Architecture Bridge

This module provides a centralized feature flag management system that controls
the transition between v1.2.1 and v2.0 functionality across all adapters.

The system supports:
- Configuration-based feature flag management
- Runtime modification capabilities
- Phase-based presets (development, staging, production)
- Logging and monitoring
- Validation and safety checks
- Utility functions for adapters

Created: 2025-06-02
Author: Architecture Bridge Team
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Set, Union
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QSettings


class FlagType(Enum):
    """Types of feature flags"""
    BOOLEAN = "boolean"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    LIST = "list"
    OBJECT = "object"


class FlagScope(Enum):
    """Scope of feature flag application"""
    GLOBAL = "global"
    ADAPTER = "adapter"
    COMPONENT = "component"
    USER = "user"
    SESSION = "session"


class FlagEnvironment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class FlagStatus(Enum):
    """Status of feature flags"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    ROLLOUT = "rollout"


@dataclass
class FlagValidationRule:
    """Validation rule for feature flags"""
    rule_id: str
    description: str
    validator: Callable[[Any], bool]
    error_message: str = ""
    warning_message: str = ""


@dataclass
class FlagDependency:
    """Dependency relationship between flags"""
    flag_name: str
    required_value: Any
    dependency_type: str = "requires"  # requires, conflicts, implies


@dataclass
class FlagMetrics:
    """Metrics for feature flag usage"""
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    first_accessed: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[datetime] = None
    performance_impact_ms: float = 0.0
    rollout_percentage: float = 0.0


@dataclass
class FeatureFlag:
    """Complete feature flag definition"""
    name: str
    value: Any
    flag_type: FlagType
    scope: FlagScope
    environment: FlagEnvironment
    status: FlagStatus
    
    # Metadata
    description: str = ""
    category: str = "general"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    # Behavior
    dependencies: List[FlagDependency] = field(default_factory=list)
    validation_rules: List[FlagValidationRule] = field(default_factory=list)
    default_value: Any = None
    rollout_percentage: float = 100.0
    
    # Monitoring
    metrics: FlagMetrics = field(default_factory=FlagMetrics)
    tags: List[str] = field(default_factory=list)
    owner: str = "system"
    
    def is_expired(self) -> bool:
        """Check if flag has expired"""
        return self.expires_at is not None and datetime.now() > self.expires_at
    
    def is_active(self) -> bool:
        """Check if flag is active and not expired"""
        return self.status == FlagStatus.ACTIVE and not self.is_expired()
    
    def update_metrics(self, error: bool = False, performance_ms: float = 0.0):
        """Update flag usage metrics"""
        now = datetime.now()
        self.metrics.access_count += 1
        self.metrics.last_accessed = now
        if self.metrics.first_accessed is None:
            self.metrics.first_accessed = now
        
        if error:
            self.metrics.error_count += 1
            self.metrics.last_error = now
        
        if performance_ms > 0:
            # Simple moving average
            self.metrics.performance_impact_ms = (
                self.metrics.performance_impact_ms * 0.8 + performance_ms * 0.2
            )


class FlagChangeEvent:
    """Event fired when a flag changes"""
    def __init__(self, flag_name: str, old_value: Any, new_value: Any, 
                 timestamp: datetime = None):
        self.flag_name = flag_name
        self.old_value = old_value
        self.new_value = new_value
        self.timestamp = timestamp or datetime.now()


class FeatureFlagManager(QObject):
    """
    Central Feature Flag Management System
    
    Provides centralized management of feature flags across the entire application
    with support for configuration files, environment variables, runtime modifications,
    validation, monitoring, and preset management.
    """
    
    # Signals
    flag_changed = pyqtSignal(str, object, object)  # flag_name, old_value, new_value
    flag_added = pyqtSignal(str, object)  # flag_name, flag
    flag_removed = pyqtSignal(str)  # flag_name
    preset_loaded = pyqtSignal(str)  # preset_name
    validation_failed = pyqtSignal(str, str)  # flag_name, error_message
    
    def __init__(self, config_path: Optional[str] = None, 
                 environment: FlagEnvironment = FlagEnvironment.DEVELOPMENT):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.environment = environment
        self.config_path = Path(config_path) if config_path else Path("config/feature_flags.json")
        self.backup_path = self.config_path.with_suffix('.backup.json')
        
        # Flag storage
        self._flags: Dict[str, FeatureFlag] = {}
        self._presets: Dict[str, Dict[str, Any]] = {}
        self._listeners: Dict[str, List[Callable]] = {}
        self._validation_rules: Dict[str, List[FlagValidationRule]] = {}
        
        # Threading
        self._lock = threading.RLock()
        self._change_events: List[FlagChangeEvent] = []
        
        # Performance monitoring
        self._metrics_timer = QTimer()
        self._metrics_timer.timeout.connect(self._collect_metrics)
        self._metrics_timer.start(30000)  # 30 seconds
        
        # Global metrics
        self._global_metrics = {
            "total_flags": 0,
            "active_flags": 0,
            "deprecated_flags": 0,
            "experimental_flags": 0,
            "flag_changes": 0,
            "validation_errors": 0,
            "performance_warnings": 0
        }
        
        # Initialize system
        self._setup_default_flags()
        self._setup_validation_rules()
        self._setup_presets()
        self._load_configuration()
        
        self.logger.info(f"FeatureFlagManager initialized with {len(self._flags)} flags")
    
    def get_flag(self, flag_name: str, default: Any = None) -> Any:
        """Get feature flag value with metrics tracking"""
        start_time = time.time()
        
        try:
            with self._lock:
                if flag_name not in self._flags:
                    self.logger.warning(f"Flag '{flag_name}' not found, using default: {default}")
                    return default
                
                flag = self._flags[flag_name]
                
                # Check if flag is expired
                if flag.is_expired():
                    self.logger.warning(f"Flag '{flag_name}' has expired, using default: {default}")
                    flag.update_metrics(error=True)
                    return default
                
                # Check rollout percentage for gradual rollout
                if flag.rollout_percentage < 100.0:
                    import random
                    if random.uniform(0, 100) > flag.rollout_percentage:
                        return flag.default_value if flag.default_value is not None else default
                
                # Update metrics
                processing_time = (time.time() - start_time) * 1000
                flag.update_metrics(performance_ms=processing_time)
                
                return flag.value
                
        except Exception as e:
            self.logger.error(f"Error getting flag '{flag_name}': {e}")
            return default
    
    def set_flag(self, flag_name: str, value: Any, validate: bool = True) -> bool:
        """Set feature flag value with validation"""
        try:
            with self._lock:
                if flag_name not in self._flags:
                    self.logger.error(f"Cannot set unknown flag '{flag_name}'")
                    return False
                
                flag = self._flags[flag_name]
                old_value = flag.value
                
                # Validate new value
                if validate and not self._validate_flag_value(flag, value):
                    return False
                
                # Check dependencies
                if not self._check_dependencies(flag_name, value):
                    return False
                
                # Update flag
                flag.value = value
                flag.updated_at = datetime.now()
                
                # Emit signals
                self.flag_changed.emit(flag_name, old_value, value)
                
                # Notify listeners
                self._notify_listeners(flag_name, old_value, value)
                
                # Record change event
                self._change_events.append(FlagChangeEvent(flag_name, old_value, value))
                self._global_metrics["flag_changes"] += 1
                
                self.logger.info(f"Flag '{flag_name}' changed from {old_value} to {value}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error setting flag '{flag_name}': {e}")
            return False
    
    def add_flag(self, flag: FeatureFlag) -> bool:
        """Add new feature flag"""
        try:
            with self._lock:
                if flag.name in self._flags:
                    self.logger.warning(f"Flag '{flag.name}' already exists")
                    return False
                
                # Validate flag
                if not self._validate_flag(flag):
                    return False
                
                self._flags[flag.name] = flag
                self._global_metrics["total_flags"] += 1
                
                self.flag_added.emit(flag.name, flag)
                self.logger.info(f"Added new flag: {flag.name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error adding flag '{flag.name}': {e}")
            return False
    
    def remove_flag(self, flag_name: str) -> bool:
        """Remove feature flag"""
        try:
            with self._lock:
                if flag_name not in self._flags:
                    return False
                
                del self._flags[flag_name]
                self._global_metrics["total_flags"] -= 1
                
                self.flag_removed.emit(flag_name)
                self.logger.info(f"Removed flag: {flag_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error removing flag '{flag_name}': {e}")
            return False
    
    def is_flag_enabled(self, flag_name: str) -> bool:
        """Check if boolean flag is enabled"""
        value = self.get_flag(flag_name, False)
        return bool(value) if value is not None else False
    
    def is_feature_available(self, feature_name: str, component: str = None) -> bool:
        """Check if a feature is available for use"""
        # Check main feature flag
        if not self.is_flag_enabled(f"enable_{feature_name}"):
            return False
        
        # Check component-specific flag if provided
        if component and not self.is_flag_enabled(f"enable_{feature_name}_{component}"):
            return False
        
        # Check environment-specific availability
        env_flag = f"{feature_name}_{self.environment.value}"
        if env_flag in self._flags:
            return self.is_flag_enabled(env_flag)
        
        return True
    
    def load_preset(self, preset_name: str) -> bool:
        """Load predefined preset configuration"""
        try:
            if preset_name not in self._presets:
                self.logger.error(f"Preset '{preset_name}' not found")
                return False
            
            preset = self._presets[preset_name]
            success_count = 0
            
            with self._lock:
                for flag_name, flag_value in preset.items():
                    if self.set_flag(flag_name, flag_value, validate=False):
                        success_count += 1
            
            self.preset_loaded.emit(preset_name)
            self.logger.info(f"Loaded preset '{preset_name}': {success_count}/{len(preset)} flags")
            return success_count == len(preset)
            
        except Exception as e:
            self.logger.error(f"Error loading preset '{preset_name}': {e}")
            return False
    
    def add_listener(self, flag_name: str, callback: Callable[[str, Any, Any], None]) -> None:
        """Add listener for flag changes"""
        if flag_name not in self._listeners:
            self._listeners[flag_name] = []
        self._listeners[flag_name].append(callback)
    
    def remove_listener(self, flag_name: str, callback: Callable) -> None:
        """Remove listener for flag changes"""
        if flag_name in self._listeners and callback in self._listeners[flag_name]:
            self._listeners[flag_name].remove(callback)
    
    def get_flag_info(self, flag_name: str) -> Optional[Dict[str, Any]]:
        """Get complete information about a flag"""
        with self._lock:
            if flag_name not in self._flags:
                return None
            
            flag = self._flags[flag_name]
            return {
                "name": flag.name,
                "value": flag.value,
                "type": flag.flag_type.value,
                "scope": flag.scope.value,
                "environment": flag.environment.value,
                "status": flag.status.value,
                "description": flag.description,
                "category": flag.category,
                "created_at": flag.created_at.isoformat(),
                "updated_at": flag.updated_at.isoformat(),
                "expires_at": flag.expires_at.isoformat() if flag.expires_at else None,
                "rollout_percentage": flag.rollout_percentage,
                "metrics": asdict(flag.metrics),
                "tags": flag.tags,
                "owner": flag.owner,
                "is_active": flag.is_active(),
                "is_expired": flag.is_expired()
            }
    
    def get_all_flags(self, filter_scope: Optional[FlagScope] = None,
                     filter_status: Optional[FlagStatus] = None) -> Dict[str, Dict[str, Any]]:
        """Get information about all flags with optional filtering"""
        result = {}
        
        with self._lock:
            for flag_name, flag in self._flags.items():
                # Apply filters
                if filter_scope and flag.scope != filter_scope:
                    continue
                if filter_status and flag.status != filter_status:
                    continue
                
                result[flag_name] = self.get_flag_info(flag_name)
        
        return result
    
    def save_configuration(self) -> bool:
        """Save current configuration to file"""
        try:
            # Create backup
            if self.config_path.exists():
                import shutil
                shutil.copy2(self.config_path, self.backup_path)
            
            # Prepare data
            config_data = {
                "environment": self.environment.value,
                "updated_at": datetime.now().isoformat(),
                "flags": {},
                "presets": self._presets,
                "metrics": self._global_metrics
            }
            
            with self._lock:
                for flag_name, flag in self._flags.items():
                    config_data["flags"][flag_name] = {
                        "value": flag.value,
                        "type": flag.flag_type.value,
                        "scope": flag.scope.value,
                        "environment": flag.environment.value,
                        "status": flag.status.value,
                        "description": flag.description,
                        "category": flag.category,
                        "created_at": flag.created_at.isoformat(),
                        "updated_at": flag.updated_at.isoformat(),
                        "expires_at": flag.expires_at.isoformat() if flag.expires_at else None,
                        "default_value": flag.default_value,
                        "rollout_percentage": flag.rollout_percentage,
                        "tags": flag.tags,
                        "owner": flag.owner,
                        "metrics": asdict(flag.metrics)
                    }
            
            # Write to file
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get global metrics"""
        with self._lock:
            return {
                **self._global_metrics,
                "flag_count_by_status": self._get_flag_counts_by_status(),
                "flag_count_by_scope": self._get_flag_counts_by_scope(),
                "recent_changes": len([e for e in self._change_events 
                                     if e.timestamp > datetime.now() - timedelta(hours=24)]),
                "top_accessed_flags": self._get_top_accessed_flags(10)
            }
    
    def _setup_default_flags(self) -> None:
        """Set up default feature flags for the adapter system"""
        default_flags = [
            # Core v2.0 Architecture Flags
            FeatureFlag(
                name="enable_v2_architecture",
                value=True,
                flag_type=FlagType.BOOLEAN,
                scope=FlagScope.GLOBAL,
                environment=self.environment,
                status=FlagStatus.ACTIVE,
                description="Enable v2.0 architecture components",
                category="architecture",
                owner="system"
            ),
            
            # Adapter Control Flags
            FeatureFlag(
                name="enable_main_window_adapter",
                value=True,
                flag_type=FlagType.BOOLEAN,
                scope=FlagScope.ADAPTER,
                environment=self.environment,
                status=FlagStatus.ACTIVE,
                description="Enable MainWindow adapter for v2.0 integration",
                category="adapters",
                owner="system"
            ),
            
            FeatureFlag(
                name="enable_video_info_adapter",
                value=True,
                flag_type=FlagType.BOOLEAN,
                scope=FlagScope.ADAPTER,
                environment=self.environment,
                status=FlagStatus.ACTIVE,
                description="Enable VideoInfoTab adapter for repository integration",
                category="adapters",
                owner="system"
            ),
            
            FeatureFlag(
                name="enable_downloaded_videos_adapter",
                value=True,
                flag_type=FlagType.BOOLEAN,
                scope=FlagScope.ADAPTER,
                environment=self.environment,
                status=FlagStatus.ACTIVE,
                description="Enable DownloadedVideosTab adapter for collection management",
                category="adapters",
                owner="system"
            ),
            
            # Feature-specific Flags
            FeatureFlag(
                name="enable_cross_component_coordination",
                value=True,
                flag_type=FlagType.BOOLEAN,
                scope=FlagScope.GLOBAL,
                environment=self.environment,
                status=FlagStatus.ACTIVE,
                description="Enable cross-component event coordination",
                category="events",
                owner="system"
            ),
            
            FeatureFlag(
                name="enable_repository_integration",
                value=True,
                flag_type=FlagType.BOOLEAN,
                scope=FlagScope.GLOBAL,
                environment=self.environment,
                status=FlagStatus.ACTIVE,
                description="Enable repository layer integration",
                category="data",
                owner="system"
            ),
            
            # Performance and Optimization Flags
            FeatureFlag(
                name="enable_video_caching",
                value=True,
                flag_type=FlagType.BOOLEAN,
                scope=FlagScope.COMPONENT,
                environment=self.environment,
                status=FlagStatus.ACTIVE,
                description="Enable video content caching",
                category="performance",
                owner="system"
            ),
            
            FeatureFlag(
                name="enable_pagination",
                value=True,
                flag_type=FlagType.BOOLEAN,
                scope=FlagScope.COMPONENT,
                environment=self.environment,
                status=FlagStatus.ACTIVE,
                description="Enable pagination for large collections",
                category="performance",
                owner="system"
            ),
            
            # Fallback and Safety Flags
            FeatureFlag(
                name="enable_graceful_degradation",
                value=True,
                flag_type=FlagType.BOOLEAN,
                scope=FlagScope.GLOBAL,
                environment=self.environment,
                status=FlagStatus.ACTIVE,
                description="Enable graceful degradation on component failures",
                category="safety",
                owner="system"
            ),
            
            FeatureFlag(
                name="enable_fallback_mechanisms",
                value=True,
                flag_type=FlagType.BOOLEAN,
                scope=FlagScope.GLOBAL,
                environment=self.environment,
                status=FlagStatus.ACTIVE,
                description="Enable automatic fallback mechanisms",
                category="safety",
                owner="system"
            ),
            
            # Development and Debug Flags
            FeatureFlag(
                name="enable_debug_mode",
                value=self.environment == FlagEnvironment.DEVELOPMENT,
                flag_type=FlagType.BOOLEAN,
                scope=FlagScope.GLOBAL,
                environment=self.environment,
                status=FlagStatus.ACTIVE,
                description="Enable debug mode with detailed logging",
                category="debug",
                owner="system"
            ),
            
            FeatureFlag(
                name="enable_performance_monitoring",
                value=True,
                flag_type=FlagType.BOOLEAN,
                scope=FlagScope.GLOBAL,
                environment=self.environment,
                status=FlagStatus.ACTIVE,
                description="Enable performance monitoring and metrics",
                category="monitoring",
                owner="system"
            ),
            
            # Migration Control Flags
            FeatureFlag(
                name="migration_phase",
                value="gradual",
                flag_type=FlagType.STRING,
                scope=FlagScope.GLOBAL,
                environment=self.environment,
                status=FlagStatus.ACTIVE,
                description="Current migration phase: gradual, big_bang, user_controlled",
                category="migration",
                owner="system"
            ),
            
            FeatureFlag(
                name="rollback_enabled",
                value=True,
                flag_type=FlagType.BOOLEAN,
                scope=FlagScope.GLOBAL,
                environment=self.environment,
                status=FlagStatus.ACTIVE,
                description="Enable automatic rollback on critical failures",
                category="safety",
                owner="system"
            )
        ]
        
        for flag in default_flags:
            self._flags[flag.name] = flag
        
        self._global_metrics["total_flags"] = len(self._flags)
    
    def _setup_validation_rules(self) -> None:
        """Set up validation rules for feature flags"""
        # Migration phase validation
        def validate_migration_phase(value):
            return value in ["gradual", "big_bang", "user_controlled", "automatic", "hybrid"]
        
        self._validation_rules["migration_phase"] = [
            FlagValidationRule(
                rule_id="valid_migration_phase",
                description="Migration phase must be one of the supported values",
                validator=validate_migration_phase,
                error_message="Invalid migration phase. Must be: gradual, big_bang, user_controlled, automatic, or hybrid"
            )
        ]
    
    def _setup_presets(self) -> None:
        """Set up predefined presets for different environments"""
        self._presets = {
            "development": {
                "enable_v2_architecture": True,
                "enable_main_window_adapter": True,
                "enable_video_info_adapter": True,
                "enable_downloaded_videos_adapter": True,
                "enable_debug_mode": True,
                "enable_performance_monitoring": True,
                "enable_graceful_degradation": True,
                "migration_phase": "gradual"
            },
            
            "staging": {
                "enable_v2_architecture": True,
                "enable_main_window_adapter": True,
                "enable_video_info_adapter": True,
                "enable_downloaded_videos_adapter": True,
                "enable_debug_mode": False,
                "enable_performance_monitoring": True,
                "enable_graceful_degradation": True,
                "migration_phase": "big_bang"
            },
            
            "production": {
                "enable_v2_architecture": True,
                "enable_main_window_adapter": True,
                "enable_video_info_adapter": True,
                "enable_downloaded_videos_adapter": True,
                "enable_debug_mode": False,
                "enable_performance_monitoring": True,
                "enable_graceful_degradation": True,
                "enable_fallback_mechanisms": True,
                "rollback_enabled": True,
                "migration_phase": "user_controlled"
            },
            
            "safe_mode": {
                "enable_v2_architecture": False,
                "enable_main_window_adapter": False,
                "enable_video_info_adapter": False,
                "enable_downloaded_videos_adapter": False,
                "enable_graceful_degradation": True,
                "enable_fallback_mechanisms": True,
                "rollback_enabled": True,
                "migration_phase": "gradual"
            }
        }
    
    def _load_configuration(self) -> None:
        """Load configuration from file and environment variables"""
        # Load from file if exists
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Load flags from config
                if "flags" in config_data:
                    for flag_name, flag_data in config_data["flags"].items():
                        if flag_name in self._flags:
                            flag = self._flags[flag_name]
                            flag.value = flag_data.get("value", flag.value)
                            flag.rollout_percentage = flag_data.get("rollout_percentage", 100.0)
                
                self.logger.info(f"Configuration loaded from {self.config_path}")
                
            except Exception as e:
                self.logger.error(f"Error loading configuration: {e}")
        
        # Override with environment variables
        self._load_from_environment()
    
    def _load_from_environment(self) -> None:
        """Load flag values from environment variables"""
        for flag_name in self._flags.keys():
            env_name = f"FEATURE_FLAG_{flag_name.upper()}"
            env_value = os.environ.get(env_name)
            
            if env_value is not None:
                flag = self._flags[flag_name]
                
                # Convert based on flag type
                try:
                    if flag.flag_type == FlagType.BOOLEAN:
                        value = env_value.lower() in ("true", "1", "yes", "on")
                    elif flag.flag_type == FlagType.INTEGER:
                        value = int(env_value)
                    elif flag.flag_type == FlagType.FLOAT:
                        value = float(env_value)
                    elif flag.flag_type == FlagType.LIST:
                        value = env_value.split(",")
                    else:
                        value = env_value
                    
                    flag.value = value
                    self.logger.info(f"Flag '{flag_name}' set from environment: {value}")
                    
                except ValueError as e:
                    self.logger.error(f"Invalid environment value for '{flag_name}': {e}")
    
    def _validate_flag(self, flag: FeatureFlag) -> bool:
        """Validate a complete flag definition"""
        if not flag.name or not isinstance(flag.name, str):
            self.logger.error("Flag name must be a non-empty string")
            return False
        
        return self._validate_flag_value(flag, flag.value)
    
    def _validate_flag_value(self, flag: FeatureFlag, value: Any) -> bool:
        """Validate a flag value"""
        # Type validation
        try:
            if flag.flag_type == FlagType.BOOLEAN and not isinstance(value, bool):
                raise ValueError(f"Expected boolean, got {type(value)}")
            elif flag.flag_type == FlagType.INTEGER and not isinstance(value, int):
                raise ValueError(f"Expected integer, got {type(value)}")
            elif flag.flag_type == FlagType.FLOAT and not isinstance(value, (int, float)):
                raise ValueError(f"Expected float, got {type(value)}")
            elif flag.flag_type == FlagType.STRING and not isinstance(value, str):
                raise ValueError(f"Expected string, got {type(value)}")
            elif flag.flag_type == FlagType.LIST and not isinstance(value, list):
                raise ValueError(f"Expected list, got {type(value)}")
        
        except ValueError as e:
            self.logger.error(f"Type validation failed for '{flag.name}': {e}")
            self.validation_failed.emit(flag.name, str(e))
            self._global_metrics["validation_errors"] += 1
            return False
        
        # Custom validation rules
        if flag.name in self._validation_rules:
            for rule in self._validation_rules[flag.name]:
                try:
                    if not rule.validator(value):
                        self.logger.error(f"Validation rule '{rule.rule_id}' failed for '{flag.name}': {rule.error_message}")
                        self.validation_failed.emit(flag.name, rule.error_message)
                        self._global_metrics["validation_errors"] += 1
                        return False
                except Exception as e:
                    self.logger.error(f"Validation rule '{rule.rule_id}' error: {e}")
                    return False
        
        return True
    
    def _check_dependencies(self, flag_name: str, value: Any) -> bool:
        """Check flag dependencies"""
        if flag_name not in self._flags:
            return True
        
        flag = self._flags[flag_name]
        
        for dependency in flag.dependencies:
            dep_flag_name = dependency.flag_name
            required_value = dependency.required_value
            dep_type = dependency.dependency_type
            
            if dep_flag_name not in self._flags:
                self.logger.warning(f"Dependency flag '{dep_flag_name}' not found")
                continue
            
            current_dep_value = self._flags[dep_flag_name].value
            
            if dep_type == "requires" and current_dep_value != required_value:
                self.logger.error(f"Flag '{flag_name}' requires '{dep_flag_name}' to be {required_value}")
                return False
            elif dep_type == "conflicts" and current_dep_value == required_value:
                self.logger.error(f"Flag '{flag_name}' conflicts with '{dep_flag_name}' being {required_value}")
                return False
        
        return True
    
    def _notify_listeners(self, flag_name: str, old_value: Any, new_value: Any) -> None:
        """Notify registered listeners of flag changes"""
        if flag_name in self._listeners:
            for callback in self._listeners[flag_name]:
                try:
                    callback(flag_name, old_value, new_value)
                except Exception as e:
                    self.logger.error(f"Error in flag change listener: {e}")
    
    def _collect_metrics(self) -> None:
        """Collect and update metrics"""
        with self._lock:
            self._global_metrics["active_flags"] = sum(
                1 for flag in self._flags.values() 
                if flag.status == FlagStatus.ACTIVE
            )
            self._global_metrics["deprecated_flags"] = sum(
                1 for flag in self._flags.values() 
                if flag.status == FlagStatus.DEPRECATED
            )
            self._global_metrics["experimental_flags"] = sum(
                1 for flag in self._flags.values() 
                if flag.status == FlagStatus.EXPERIMENTAL
            )
    
    def _get_flag_counts_by_status(self) -> Dict[str, int]:
        """Get flag counts grouped by status"""
        counts = {}
        for flag in self._flags.values():
            status = flag.status.value
            counts[status] = counts.get(status, 0) + 1
        return counts
    
    def _get_flag_counts_by_scope(self) -> Dict[str, int]:
        """Get flag counts grouped by scope"""
        counts = {}
        for flag in self._flags.values():
            scope = flag.scope.value
            counts[scope] = counts.get(scope, 0) + 1
        return counts
    
    def _get_top_accessed_flags(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most accessed flags"""
        sorted_flags = sorted(
            self._flags.values(),
            key=lambda f: f.metrics.access_count,
            reverse=True
        )
        
        return [
            {
                "name": flag.name,
                "access_count": flag.metrics.access_count,
                "error_count": flag.metrics.error_count,
                "performance_ms": flag.metrics.performance_impact_ms
            }
            for flag in sorted_flags[:limit]
        ]


# Global instance for easy access
_global_flag_manager: Optional[FeatureFlagManager] = None


def get_flag_manager() -> FeatureFlagManager:
    """Get global feature flag manager instance"""
    global _global_flag_manager
    if _global_flag_manager is None:
        _global_flag_manager = FeatureFlagManager()
    return _global_flag_manager


def initialize_flag_manager(config_path: Optional[str] = None,
                          environment: FlagEnvironment = FlagEnvironment.DEVELOPMENT) -> FeatureFlagManager:
    """Initialize global feature flag manager"""
    global _global_flag_manager
    _global_flag_manager = FeatureFlagManager(config_path, environment)
    return _global_flag_manager


# Utility functions for easy access
def get_flag(flag_name: str, default: Any = None) -> Any:
    """Get feature flag value"""
    return get_flag_manager().get_flag(flag_name, default)


def is_flag_enabled(flag_name: str) -> bool:
    """Check if boolean flag is enabled"""
    return get_flag_manager().is_flag_enabled(flag_name)


def is_feature_available(feature_name: str, component: str = None) -> bool:
    """Check if feature is available"""
    return get_flag_manager().is_feature_available(feature_name, component)


def set_flag(flag_name: str, value: Any) -> bool:
    """Set feature flag value"""
    return get_flag_manager().set_flag(flag_name, value)


def load_preset(preset_name: str) -> bool:
    """Load feature flag preset"""
    return get_flag_manager().load_preset(preset_name) 