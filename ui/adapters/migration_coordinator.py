"""
Migration Coordinator for Task 29.6 - Managing v1.2.1 to v2.0 Transition

This module provides tools for coordinating the gradual migration from
v1.2.1 UI components to v2.0 implementations, with proper telemetry,
configuration control, and rollback capabilities.
"""

import logging
import threading
import json
from typing import Dict, Any, Optional, List, Callable, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from datetime import datetime, timedelta
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# Import adapter manager components
from .adapter_manager import AdapterManager, FallbackConfig, FeatureFlag
from .interfaces import AdapterState, AdapterPriority


class MigrationStage(Enum):
    """Stages of component migration"""
    NOT_STARTED = auto()           # Component still using v1.2.1
    ADAPTER_BRIDGED = auto()       # Component bridged through adapter
    PARTIAL_V2 = auto()           # Some features using v2.0
    MOSTLY_V2 = auto()            # Most features using v2.0
    FULLY_V2 = auto()             # Component fully migrated to v2.0
    ROLLBACK_REQUIRED = auto()     # Migration failed, rollback needed


class MigrationStrategy(Enum):
    """Strategies for component migration"""
    GRADUAL_FEATURE_BY_FEATURE = auto()  # Migrate features incrementally
    BIG_BANG_COMPONENT = auto()          # Migrate entire component at once
    USER_CONTROLLED = auto()             # Let user control migration timing
    AUTOMATIC_BACKGROUND = auto()        # Automatic migration based on metrics
    HYBRID_APPROACH = auto()             # Combination of strategies


@dataclass
class MigrationMetrics:
    """Metrics for tracking migration progress"""
    component_name: str
    stage: MigrationStage
    start_time: datetime
    last_update: datetime
    features_migrated: int = 0
    total_features: int = 0
    success_rate: float = 0.0
    error_count: int = 0
    rollback_count: int = 0
    user_satisfaction: Optional[float] = None  # 0-10 scale
    performance_impact: Optional[float] = None  # % change in performance
    memory_usage_change: Optional[float] = None  # % change in memory
    
    @property
    def completion_percentage(self) -> float:
        """Calculate migration completion percentage"""
        if self.total_features == 0:
            return 0.0
        return (self.features_migrated / self.total_features) * 100
    
    @property
    def migration_health(self) -> str:
        """Assess overall migration health"""
        if self.error_count > 5:
            return "unhealthy"
        elif self.success_rate < 0.8:
            return "concerning"
        elif self.completion_percentage < 25:
            return "early"
        elif self.completion_percentage > 75:
            return "advanced"
        else:
            return "healthy"


@dataclass
class MigrationPlan:
    """Plan for migrating a component"""
    component_name: str
    current_stage: MigrationStage
    target_stage: MigrationStage
    strategy: MigrationStrategy
    estimated_duration_days: int
    prerequisites: List[str] = field(default_factory=list)
    features_to_migrate: List[str] = field(default_factory=list)
    rollback_plan: Optional[str] = None
    risk_assessment: str = "medium"
    priority: int = 5  # 1-10 scale
    assigned_developer: Optional[str] = None
    testing_requirements: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MigrationPlan':
        """Create from dictionary"""
        # Handle enum conversions
        if 'current_stage' in data:
            data['current_stage'] = MigrationStage[data['current_stage']]
        if 'target_stage' in data:
            data['target_stage'] = MigrationStage[data['target_stage']]
        if 'strategy' in data:
            data['strategy'] = MigrationStrategy[data['strategy']]
        
        return cls(**data)


@dataclass
class TelemetryData:
    """Telemetry data for migration tracking"""
    timestamp: datetime
    component: str
    event_type: str  # "migration_started", "feature_migrated", "error", etc.
    details: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    performance_metrics: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class MigrationCoordinator(QObject):
    """
    Coordinator for managing the migration from v1.2.1 to v2.0
    """
    
    # Signals
    migration_started = pyqtSignal(str, str)      # component_name, strategy
    migration_progress = pyqtSignal(str, float)   # component_name, percentage
    migration_completed = pyqtSignal(str, bool)   # component_name, success
    feature_migrated = pyqtSignal(str, str)       # component_name, feature_name
    rollback_initiated = pyqtSignal(str, str)     # component_name, reason
    
    def __init__(self, adapter_manager: AdapterManager, data_directory: Optional[Path] = None):
        super().__init__()
        self.adapter_manager = adapter_manager
        self._logger = logging.getLogger(__name__)
        
        # Data storage
        self.data_directory = data_directory or Path("data/migration")
        self.data_directory.mkdir(parents=True, exist_ok=True)
        
        # Migration tracking
        self._migration_plans: Dict[str, MigrationPlan] = {}
        self._migration_metrics: Dict[str, MigrationMetrics] = {}
        self._telemetry_data: List[TelemetryData] = []
        
        # Configuration
        self._config_file = self.data_directory / "migration_config.json"
        self._plans_file = self.data_directory / "migration_plans.json"
        self._metrics_file = self.data_directory / "migration_metrics.json"
        
        # Load existing data
        self._load_configuration()
        self._load_migration_plans()
        self._load_metrics()
        
        # Auto-save timer
        self._save_timer = QTimer()
        self._save_timer.timeout.connect(self._auto_save)
        self._save_timer.start(60000)  # Save every minute
        
        # Threading
        self._lock = threading.RLock()
        
        # Default migration plans
        self._initialize_default_plans()
    
    def _initialize_default_plans(self):
        """Initialize default migration plans for core components"""
        default_plans = [
            MigrationPlan(
                component_name="MainWindow",
                current_stage=MigrationStage.ADAPTER_BRIDGED,
                target_stage=MigrationStage.FULLY_V2,
                strategy=MigrationStrategy.GRADUAL_FEATURE_BY_FEATURE,
                estimated_duration_days=14,
                features_to_migrate=[
                    "menu_system",
                    "status_bar",
                    "theme_management",
                    "window_state",
                    "toolbar_integration"
                ],
                prerequisites=["event_system_stable", "config_system_ready"],
                rollback_plan="Revert to direct v1.2.1 implementation",
                risk_assessment="low",
                priority=8,
                testing_requirements=[
                    "window_lifecycle_tests",
                    "menu_interaction_tests",
                    "theme_switching_tests"
                ]
            ),
            MigrationPlan(
                component_name="VideoInfoTab",
                current_stage=MigrationStage.ADAPTER_BRIDGED,
                target_stage=MigrationStage.MOSTLY_V2,
                strategy=MigrationStrategy.GRADUAL_FEATURE_BY_FEATURE,
                estimated_duration_days=10,
                features_to_migrate=[
                    "url_input_validation",
                    "metadata_display",
                    "thumbnail_loading",
                    "format_selection",
                    "download_options"
                ],
                prerequisites=["content_service_ready", "platform_factories_migrated"],
                rollback_plan="Use basic metadata display fallback",
                risk_assessment="medium",
                priority=6,
                testing_requirements=[
                    "url_parsing_tests",
                    "metadata_accuracy_tests",
                    "ui_responsiveness_tests"
                ]
            ),
            MigrationPlan(
                component_name="DownloadedVideosTab",
                current_stage=MigrationStage.ADAPTER_BRIDGED,
                target_stage=MigrationStage.FULLY_V2,
                strategy=MigrationStrategy.HYBRID_APPROACH,
                estimated_duration_days=12,
                features_to_migrate=[
                    "download_list_display",
                    "progress_tracking",
                    "file_management",
                    "batch_operations",
                    "search_filtering"
                ],
                prerequisites=["download_service_ready", "repository_layer_stable"],
                rollback_plan="Fallback to polling-based progress updates",
                risk_assessment="medium",
                priority=7,
                testing_requirements=[
                    "download_progress_tests",
                    "file_operation_tests",
                    "performance_tests"
                ]
            )
        ]
        
        for plan in default_plans:
            if plan.component_name not in self._migration_plans:
                self._migration_plans[plan.component_name] = plan
                
                # Initialize metrics
                self._migration_metrics[plan.component_name] = MigrationMetrics(
                    component_name=plan.component_name,
                    stage=plan.current_stage,
                    start_time=datetime.now(),
                    last_update=datetime.now(),
                    total_features=len(plan.features_to_migrate)
                )
    
    def start_migration(self, component_name: str, strategy: Optional[MigrationStrategy] = None) -> bool:
        """Start migration for a component"""
        with self._lock:
            if component_name not in self._migration_plans:
                self._logger.error(f"No migration plan found for component: {component_name}")
                return False
            
            plan = self._migration_plans[component_name]
            metrics = self._migration_metrics[component_name]
            
            # Update strategy if provided
            if strategy:
                plan.strategy = strategy
            
            try:
                self._logger.info(f"Starting migration for {component_name} using {plan.strategy.name}")
                
                # Check prerequisites
                if not self._check_prerequisites(plan):
                    self._logger.warning(f"Prerequisites not met for {component_name}")
                    return False
                
                # Update metrics
                metrics.stage = MigrationStage.PARTIAL_V2
                metrics.start_time = datetime.now()
                metrics.last_update = datetime.now()
                
                # Log telemetry
                self._log_telemetry(
                    component=component_name,
                    event_type="migration_started",
                    details={
                        "strategy": plan.strategy.name,
                        "target_stage": plan.target_stage.name,
                        "features_count": len(plan.features_to_migrate)
                    }
                )
                
                # Emit signal
                self.migration_started.emit(component_name, plan.strategy.name)
                
                # Start migration based on strategy
                if plan.strategy == MigrationStrategy.GRADUAL_FEATURE_BY_FEATURE:
                    return self._start_gradual_migration(component_name)
                elif plan.strategy == MigrationStrategy.BIG_BANG_COMPONENT:
                    return self._start_big_bang_migration(component_name)
                elif plan.strategy == MigrationStrategy.AUTOMATIC_BACKGROUND:
                    return self._start_automatic_migration(component_name)
                else:
                    # Default to gradual
                    return self._start_gradual_migration(component_name)
                
            except Exception as e:
                self._logger.error(f"Failed to start migration for {component_name}: {e}")
                self._handle_migration_error(component_name, e)
                return False
    
    def _check_prerequisites(self, plan: MigrationPlan) -> bool:
        """Check if migration prerequisites are met"""
        for prereq in plan.prerequisites:
            if not self._is_prerequisite_met(prereq):
                self._logger.warning(f"Prerequisite not met: {prereq}")
                return False
        return True
    
    def _is_prerequisite_met(self, prerequisite: str) -> bool:
        """Check if a specific prerequisite is met"""
        # This would check various system states
        # For now, we'll do basic checks
        
        if prerequisite == "event_system_stable":
            return self.adapter_manager.app_controller.is_ready()
        elif prerequisite == "config_system_ready":
            return self.adapter_manager.app_controller.get_config() is not None
        elif prerequisite == "content_service_ready":
            return self.adapter_manager.app_controller.get_content_service() is not None
        elif prerequisite == "download_service_ready":
            return self.adapter_manager.app_controller.get_download_service() is not None
        else:
            # Default to true for unknown prerequisites
            return True
    
    def _start_gradual_migration(self, component_name: str) -> bool:
        """Start gradual feature-by-feature migration"""
        plan = self._migration_plans[component_name]
        
        self._logger.info(f"Starting gradual migration for {component_name}")
        
        # Schedule migration of first feature
        if plan.features_to_migrate:
            first_feature = plan.features_to_migrate[0]
            return self._migrate_feature(component_name, first_feature)
        
        return True
    
    def _start_big_bang_migration(self, component_name: str) -> bool:
        """Start big-bang migration of entire component"""
        plan = self._migration_plans[component_name]
        
        self._logger.info(f"Starting big-bang migration for {component_name}")
        
        # Migrate all features at once
        success_count = 0
        for feature in plan.features_to_migrate:
            if self._migrate_feature(component_name, feature):
                success_count += 1
        
        # Check if migration was successful
        success_rate = success_count / len(plan.features_to_migrate) if plan.features_to_migrate else 1.0
        
        if success_rate >= 0.8:  # 80% success threshold
            self._complete_migration(component_name, True)
            return True
        else:
            self._handle_migration_failure(component_name, "Big-bang migration had too many failures")
            return False
    
    def _start_automatic_migration(self, component_name: str) -> bool:
        """Start automatic background migration"""
        self._logger.info(f"Starting automatic migration for {component_name}")
        
        # This would implement gradual automatic migration
        # For now, we'll use gradual approach
        return self._start_gradual_migration(component_name)
    
    def _migrate_feature(self, component_name: str, feature_name: str) -> bool:
        """Migrate a specific feature"""
        try:
            self._logger.info(f"Migrating feature {feature_name} for {component_name}")
            
            # Get the adapter
            adapter = self.adapter_manager.get_adapter_by_component_type(component_name)
            if not adapter:
                raise Exception(f"No adapter found for {component_name}")
            
            # Simulate feature migration (in real implementation, this would
            # involve specific migration logic for each feature)
            self._simulate_feature_migration(component_name, feature_name)
            
            # Update metrics
            metrics = self._migration_metrics[component_name]
            metrics.features_migrated += 1
            metrics.last_update = datetime.now()
            metrics.success_rate = metrics.features_migrated / metrics.total_features
            
            # Log telemetry
            self._log_telemetry(
                component=component_name,
                event_type="feature_migrated",
                details={
                    "feature_name": feature_name,
                    "completion_percentage": metrics.completion_percentage
                }
            )
            
            # Emit signals
            self.feature_migrated.emit(component_name, feature_name)
            self.migration_progress.emit(component_name, metrics.completion_percentage)
            
            # Check if migration is complete
            if metrics.features_migrated >= metrics.total_features:
                self._complete_migration(component_name, True)
            
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to migrate feature {feature_name} for {component_name}: {e}")
            self._handle_feature_migration_error(component_name, feature_name, e)
            return False
    
    def _simulate_feature_migration(self, component_name: str, feature_name: str):
        """Simulate feature migration (placeholder for actual migration logic)"""
        # In a real implementation, this would contain specific logic
        # for migrating each feature from v1.2.1 to v2.0
        
        feature_configs = {
            "menu_system": {"complexity": "low", "duration_ms": 100},
            "status_bar": {"complexity": "low", "duration_ms": 50},
            "theme_management": {"complexity": "medium", "duration_ms": 200},
            "url_input_validation": {"complexity": "medium", "duration_ms": 150},
            "metadata_display": {"complexity": "high", "duration_ms": 300},
            "download_list_display": {"complexity": "high", "duration_ms": 400},
            "progress_tracking": {"complexity": "high", "duration_ms": 350}
        }
        
        config = feature_configs.get(feature_name, {"complexity": "medium", "duration_ms": 200})
        
        # Simulate some processing time
        import time
        time.sleep(config["duration_ms"] / 1000.0)
        
        # Simulate potential failure for high complexity features
        if config["complexity"] == "high" and component_name == "VideoInfoTab":
            import random
            if random.random() < 0.1:  # 10% failure rate for demo
                raise Exception(f"Simulated failure for {feature_name}")
    
    def _complete_migration(self, component_name: str, success: bool):
        """Complete migration for a component"""
        metrics = self._migration_metrics[component_name]
        plan = self._migration_plans[component_name]
        
        if success:
            metrics.stage = plan.target_stage
            self._logger.info(f"Migration completed successfully for {component_name}")
        else:
            metrics.stage = MigrationStage.ROLLBACK_REQUIRED
            self._logger.warning(f"Migration failed for {component_name}")
        
        metrics.last_update = datetime.now()
        
        # Log telemetry
        self._log_telemetry(
            component=component_name,
            event_type="migration_completed",
            details={
                "success": success,
                "final_stage": metrics.stage.name,
                "duration_minutes": (datetime.now() - metrics.start_time).total_seconds() / 60
            }
        )
        
        # Emit signal
        self.migration_completed.emit(component_name, success)
    
    def _handle_migration_error(self, component_name: str, error: Exception):
        """Handle migration error"""
        metrics = self._migration_metrics[component_name]
        metrics.error_count += 1
        metrics.last_update = datetime.now()
        
        self._log_telemetry(
            component=component_name,
            event_type="migration_error",
            details={"error": str(error), "error_count": metrics.error_count}
        )
        
        # Check if rollback is needed
        if metrics.error_count >= 3:
            self.initiate_rollback(component_name, "Too many errors")
    
    def _handle_feature_migration_error(self, component_name: str, feature_name: str, error: Exception):
        """Handle feature migration error"""
        metrics = self._migration_metrics[component_name]
        metrics.error_count += 1
        
        self._log_telemetry(
            component=component_name,
            event_type="feature_migration_error",
            details={
                "feature_name": feature_name,
                "error": str(error)
            }
        )
    
    def _handle_migration_failure(self, component_name: str, reason: str):
        """Handle overall migration failure"""
        self._logger.error(f"Migration failed for {component_name}: {reason}")
        self.initiate_rollback(component_name, reason)
    
    def initiate_rollback(self, component_name: str, reason: str) -> bool:
        """Initiate rollback for a component"""
        with self._lock:
            try:
                self._logger.warning(f"Initiating rollback for {component_name}: {reason}")
                
                metrics = self._migration_metrics[component_name]
                plan = self._migration_plans[component_name]
                
                # Update metrics
                metrics.stage = MigrationStage.ROLLBACK_REQUIRED
                metrics.rollback_count += 1
                metrics.last_update = datetime.now()
                
                # Execute rollback plan
                if plan.rollback_plan:
                    self._execute_rollback_plan(component_name, plan.rollback_plan)
                
                # Log telemetry
                self._log_telemetry(
                    component=component_name,
                    event_type="rollback_initiated",
                    details={"reason": reason, "rollback_count": metrics.rollback_count}
                )
                
                # Emit signal
                self.rollback_initiated.emit(component_name, reason)
                
                # Reset to adapter-bridged state
                metrics.stage = MigrationStage.ADAPTER_BRIDGED
                metrics.features_migrated = 0
                
                return True
                
            except Exception as e:
                self._logger.error(f"Failed to initiate rollback for {component_name}: {e}")
                return False
    
    def _execute_rollback_plan(self, component_name: str, rollback_plan: str):
        """Execute the rollback plan for a component"""
        self._logger.info(f"Executing rollback plan for {component_name}: {rollback_plan}")
        
        # In a real implementation, this would contain specific rollback logic
        # For now, we'll just log the action
        
        # Reset adapter to fallback mode
        if hasattr(self.adapter_manager.fallback_manager, 'handle_adapter_failure'):
            self.adapter_manager.fallback_manager.handle_adapter_failure(
                component_name,
                Exception("Migration rollback"),
                "rollback_plan"
            )
    
    def get_migration_status(self, component_name: str) -> Optional[Dict[str, Any]]:
        """Get migration status for a component"""
        if component_name not in self._migration_metrics:
            return None
        
        metrics = self._migration_metrics[component_name]
        plan = self._migration_plans[component_name]
        
        return {
            "component_name": component_name,
            "current_stage": metrics.stage.name,
            "target_stage": plan.target_stage.name,
            "completion_percentage": metrics.completion_percentage,
            "features_migrated": metrics.features_migrated,
            "total_features": metrics.total_features,
            "success_rate": metrics.success_rate,
            "error_count": metrics.error_count,
            "rollback_count": metrics.rollback_count,
            "migration_health": metrics.migration_health,
            "estimated_days_remaining": self._estimate_remaining_days(component_name),
            "last_update": metrics.last_update.isoformat()
        }
    
    def get_all_migration_status(self) -> Dict[str, Dict[str, Any]]:
        """Get migration status for all components"""
        return {
            component: self.get_migration_status(component)
            for component in self._migration_metrics.keys()
        }
    
    def _estimate_remaining_days(self, component_name: str) -> float:
        """Estimate remaining days for migration completion"""
        metrics = self._migration_metrics[component_name]
        plan = self._migration_plans[component_name]
        
        if metrics.completion_percentage >= 100:
            return 0.0
        
        elapsed_days = (datetime.now() - metrics.start_time).days
        if elapsed_days == 0:
            return plan.estimated_duration_days
        
        # Estimate based on current progress
        progress_per_day = metrics.completion_percentage / elapsed_days
        if progress_per_day <= 0:
            return plan.estimated_duration_days
        
        remaining_percentage = 100 - metrics.completion_percentage
        return remaining_percentage / progress_per_day
    
    def _log_telemetry(self, component: str, event_type: str, details: Dict[str, Any]):
        """Log telemetry data"""
        telemetry = TelemetryData(
            timestamp=datetime.now(),
            component=component,
            event_type=event_type,
            details=details
        )
        
        self._telemetry_data.append(telemetry)
        
        # Keep only last 1000 telemetry events to manage memory
        if len(self._telemetry_data) > 1000:
            self._telemetry_data = self._telemetry_data[-1000:]
    
    def get_telemetry_data(self, component: Optional[str] = None, 
                          hours: int = 24) -> List[Dict[str, Any]]:
        """Get telemetry data for analysis"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_data = [
            telemetry.to_dict()
            for telemetry in self._telemetry_data
            if telemetry.timestamp >= cutoff_time and
               (component is None or telemetry.component == component)
        ]
        
        return filtered_data
    
    def export_migration_report(self, file_path: Optional[Path] = None) -> Path:
        """Export comprehensive migration report"""
        if file_path is None:
            file_path = self.data_directory / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "migration_status": self.get_all_migration_status(),
            "telemetry_summary": {
                "total_events": len(self._telemetry_data),
                "events_by_type": self._summarize_telemetry_by_type(),
                "errors_by_component": self._summarize_errors_by_component()
            },
            "recommendations": self._generate_recommendations()
        }
        
        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self._logger.info(f"Migration report exported to {file_path}")
        return file_path
    
    def _summarize_telemetry_by_type(self) -> Dict[str, int]:
        """Summarize telemetry events by type"""
        summary = {}
        for telemetry in self._telemetry_data:
            event_type = telemetry.event_type
            summary[event_type] = summary.get(event_type, 0) + 1
        return summary
    
    def _summarize_errors_by_component(self) -> Dict[str, int]:
        """Summarize errors by component"""
        summary = {}
        for telemetry in self._telemetry_data:
            if "error" in telemetry.event_type:
                component = telemetry.component
                summary[component] = summary.get(component, 0) + 1
        return summary
    
    def _generate_recommendations(self) -> List[str]:
        """Generate migration recommendations based on current data"""
        recommendations = []
        
        for component_name, metrics in self._migration_metrics.items():
            if metrics.migration_health == "unhealthy":
                recommendations.append(
                    f"Consider rollback for {component_name} due to high error rate"
                )
            elif metrics.migration_health == "concerning":
                recommendations.append(
                    f"Monitor {component_name} closely and consider slowing migration pace"
                )
            elif metrics.completion_percentage > 75 and metrics.success_rate > 0.9:
                recommendations.append(
                    f"Consider accelerating migration for {component_name} - good progress"
                )
        
        return recommendations
    
    def _load_configuration(self):
        """Load migration configuration from file"""
        try:
            if self._config_file.exists():
                with open(self._config_file, 'r') as f:
                    config = json.load(f)
                    # Apply configuration settings
                    self._logger.info("Migration configuration loaded")
        except Exception as e:
            self._logger.warning(f"Failed to load migration configuration: {e}")
    
    def _load_migration_plans(self):
        """Load migration plans from file"""
        try:
            if self._plans_file.exists():
                with open(self._plans_file, 'r') as f:
                    plans_data = json.load(f)
                    for component_name, plan_data in plans_data.items():
                        self._migration_plans[component_name] = MigrationPlan.from_dict(plan_data)
                    self._logger.info(f"Loaded {len(self._migration_plans)} migration plans")
        except Exception as e:
            self._logger.warning(f"Failed to load migration plans: {e}")
    
    def _load_metrics(self):
        """Load migration metrics from file"""
        try:
            if self._metrics_file.exists():
                with open(self._metrics_file, 'r') as f:
                    metrics_data = json.load(f)
                    for component_name, metric_data in metrics_data.items():
                        # Convert datetime strings back to datetime objects
                        metric_data['start_time'] = datetime.fromisoformat(metric_data['start_time'])
                        metric_data['last_update'] = datetime.fromisoformat(metric_data['last_update'])
                        metric_data['stage'] = MigrationStage[metric_data['stage']]
                        
                        self._migration_metrics[component_name] = MigrationMetrics(**metric_data)
                    self._logger.info(f"Loaded metrics for {len(self._migration_metrics)} components")
        except Exception as e:
            self._logger.warning(f"Failed to load migration metrics: {e}")
    
    def _auto_save(self):
        """Auto-save migration data"""
        try:
            self._save_migration_plans()
            self._save_metrics()
        except Exception as e:
            self._logger.error(f"Auto-save failed: {e}")
    
    def _save_migration_plans(self):
        """Save migration plans to file"""
        plans_data = {
            component_name: plan.to_dict()
            for component_name, plan in self._migration_plans.items()
        }
        
        with open(self._plans_file, 'w') as f:
            json.dump(plans_data, f, indent=2, default=str)
    
    def _save_metrics(self):
        """Save migration metrics to file"""
        metrics_data = {
            component_name: asdict(metrics)
            for component_name, metrics in self._migration_metrics.items()
        }
        
        with open(self._metrics_file, 'w') as f:
            json.dump(metrics_data, f, indent=2, default=str)
    
    def shutdown(self):
        """Shutdown the migration coordinator"""
        self._save_timer.stop()
        self._auto_save()
        self._logger.info("Migration coordinator shutdown complete") 