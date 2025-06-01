"""
Integration Test Configuration
=============================

Centralized configuration management for integration testing scenarios.
Provides test-specific configurations for different integration test phases.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Configuration for test databases."""
    v2_clean_path: str = ""
    v1_migration_path: str = ""
    corrupted_path: str = ""
    backup_path: str = ""
    connection_timeout: int = 30
    enable_foreign_keys: bool = True


@dataclass
class MockServiceConfig:
    """Configuration for mock services."""
    tiktok_enabled: bool = True
    youtube_enabled: bool = True
    network_simulation: bool = True
    response_delay_ms: int = 100
    error_rate_percent: float = 0.0
    

@dataclass
class TestDataConfig:
    """Configuration for test data generation."""
    num_tiktok_urls: int = 10
    num_youtube_urls: int = 8
    num_invalid_urls: int = 5
    generate_large_dataset: bool = False
    include_edge_cases: bool = True


@dataclass
class ComponentTestConfig:
    """Configuration for component-specific testing."""
    app_controller_timeout: int = 60
    ui_update_timeout: int = 5
    platform_handler_timeout: int = 30
    repository_timeout: int = 15
    error_handling_timeout: int = 10


@dataclass
class IntegrationTestConfig:
    """Master configuration for integration testing."""
    test_name: str = "integration_test"
    test_mode: str = "full"  # "quick", "full", "focused"
    parallel_execution: bool = False
    capture_logs: bool = True
    cleanup_on_failure: bool = True
    
    # Sub-configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    mock_services: MockServiceConfig = field(default_factory=MockServiceConfig)
    test_data: TestDataConfig = field(default_factory=TestDataConfig)
    components: ComponentTestConfig = field(default_factory=ComponentTestConfig)
    
    # Test execution settings
    max_test_duration_minutes: int = 30
    retry_failed_tests: bool = True
    retry_count: int = 2
    
    # Environment settings
    temp_dir_prefix: str = "sdm_integration_"
    preserve_test_artifacts: bool = False
    log_level: str = "DEBUG"


class IntegrationTestConfigManager:
    """Manages integration test configurations for different scenarios."""
    
    def __init__(self):
        self.configs = {}
        self._initialize_default_configs()
    
    def _initialize_default_configs(self):
        """Initialize predefined test configurations."""
        
        # Quick Integration Test Config (for CI/CD)
        quick_config = IntegrationTestConfig(
            test_name="quick_integration",
            test_mode="quick",
            max_test_duration_minutes=10,
            parallel_execution=True,
            cleanup_on_failure=True
        )
        quick_config.test_data.num_tiktok_urls = 3
        quick_config.test_data.num_youtube_urls = 2
        quick_config.test_data.include_edge_cases = False
        quick_config.mock_services.response_delay_ms = 50
        self.configs["quick"] = quick_config
        
        # Full Integration Test Config (for comprehensive testing)
        full_config = IntegrationTestConfig(
            test_name="full_integration",
            test_mode="full",
            max_test_duration_minutes=45,
            parallel_execution=False,
            preserve_test_artifacts=True
        )
        full_config.test_data.generate_large_dataset = True
        full_config.test_data.include_edge_cases = True
        full_config.mock_services.error_rate_percent = 5.0
        self.configs["full"] = full_config
        
        # Error Handling Focused Config
        error_config = IntegrationTestConfig(
            test_name="error_handling_integration",
            test_mode="focused",
            max_test_duration_minutes=20,
            retry_failed_tests=False  # Want to see actual failures
        )
        error_config.mock_services.error_rate_percent = 20.0
        error_config.test_data.num_invalid_urls = 10
        error_config.components.error_handling_timeout = 30
        self.configs["error_focused"] = error_config
        
        # Performance Integration Config
        performance_config = IntegrationTestConfig(
            test_name="performance_integration",
            test_mode="focused",
            max_test_duration_minutes=60,
            parallel_execution=True
        )
        performance_config.test_data.generate_large_dataset = True
        performance_config.test_data.num_tiktok_urls = 50
        performance_config.test_data.num_youtube_urls = 30
        performance_config.mock_services.response_delay_ms = 200
        self.configs["performance"] = performance_config
        
        # Database Migration Focused Config
        migration_config = IntegrationTestConfig(
            test_name="migration_integration",
            test_mode="focused",
            max_test_duration_minutes=25,
            preserve_test_artifacts=True
        )
        migration_config.database.connection_timeout = 60
        migration_config.components.repository_timeout = 30
        self.configs["migration"] = migration_config
    
    def get_config(self, config_name: str) -> IntegrationTestConfig:
        """Get a specific test configuration."""
        if config_name not in self.configs:
            raise ValueError(f"Unknown config: {config_name}. Available: {list(self.configs.keys())}")
        return self.configs[config_name]
    
    def create_custom_config(self, base_config: str = "full", **overrides) -> IntegrationTestConfig:
        """Create a custom configuration based on an existing one."""
        base = self.get_config(base_config)
        
        # Create a copy of the base config
        custom_config = IntegrationTestConfig(
            test_name=overrides.get("test_name", f"custom_{base.test_name}"),
            test_mode=overrides.get("test_mode", base.test_mode),
            parallel_execution=overrides.get("parallel_execution", base.parallel_execution),
            capture_logs=overrides.get("capture_logs", base.capture_logs),
            cleanup_on_failure=overrides.get("cleanup_on_failure", base.cleanup_on_failure),
            max_test_duration_minutes=overrides.get("max_test_duration_minutes", base.max_test_duration_minutes),
            retry_failed_tests=overrides.get("retry_failed_tests", base.retry_failed_tests),
            retry_count=overrides.get("retry_count", base.retry_count)
        )
        
        # Copy sub-configurations
        custom_config.database = base.database
        custom_config.mock_services = base.mock_services
        custom_config.test_data = base.test_data
        custom_config.components = base.components
        
        return custom_config
    
    def list_available_configs(self) -> List[str]:
        """List all available configuration names."""
        return list(self.configs.keys())
    
    def get_config_summary(self, config_name: str) -> Dict[str, Any]:
        """Get a summary of a configuration."""
        config = self.get_config(config_name)
        return {
            "name": config.test_name,
            "mode": config.test_mode,
            "duration_minutes": config.max_test_duration_minutes,
            "parallel": config.parallel_execution,
            "tiktok_urls": config.test_data.num_tiktok_urls,
            "youtube_urls": config.test_data.num_youtube_urls,
            "error_rate": config.mock_services.error_rate_percent,
            "preserve_artifacts": config.preserve_test_artifacts
        }


def create_test_config_from_environment() -> IntegrationTestConfig:
    """Create test configuration from environment variables."""
    config = IntegrationTestConfig()
    
    # Read from environment
    config.test_name = os.getenv("INTEGRATION_TEST_NAME", config.test_name)
    config.test_mode = os.getenv("INTEGRATION_TEST_MODE", config.test_mode)
    config.log_level = os.getenv("INTEGRATION_LOG_LEVEL", config.log_level)
    
    # Parse boolean values
    parallel = os.getenv("INTEGRATION_PARALLEL", "false").lower()
    config.parallel_execution = parallel in ("true", "1", "yes")
    
    cleanup = os.getenv("INTEGRATION_CLEANUP", "true").lower()
    config.cleanup_on_failure = cleanup in ("true", "1", "yes")
    
    # Parse numeric values
    try:
        duration = os.getenv("INTEGRATION_MAX_DURATION")
        if duration:
            config.max_test_duration_minutes = int(duration)
    except ValueError:
        pass  # Use default
    
    try:
        error_rate = os.getenv("INTEGRATION_ERROR_RATE")
        if error_rate:
            config.mock_services.error_rate_percent = float(error_rate)
    except ValueError:
        pass  # Use default
    
    return config


class TestScenarioConfig:
    """Configuration for specific test scenarios."""
    
    @staticmethod
    def get_component_interaction_config() -> Dict[str, Any]:
        """Configuration for component interaction tests."""
        return {
            "timeout": 30,
            "retry_on_failure": True,
            "capture_intermediate_states": True,
            "validate_data_flow": True,
            "check_error_propagation": True
        }
    
    @staticmethod
    def get_end_to_end_config() -> Dict[str, Any]:
        """Configuration for end-to-end tests."""
        return {
            "timeout": 120,
            "include_ui_validation": True,
            "test_user_workflows": True,
            "validate_file_operations": True,
            "check_database_consistency": True,
            "measure_performance": True
        }
    
    @staticmethod
    def get_error_handling_config() -> Dict[str, Any]:
        """Configuration for error handling tests."""
        return {
            "timeout": 60,
            "inject_errors": True,
            "test_recovery_mechanisms": True,
            "validate_error_messages": True,
            "check_logging": True,
            "test_fallback_procedures": True
        }
    
    @staticmethod
    def get_performance_config() -> Dict[str, Any]:
        """Configuration for performance tests."""
        return {
            "timeout": 300,
            "measure_response_time": True,
            "monitor_memory_usage": True,
            "test_concurrent_operations": True,
            "validate_resource_cleanup": True,
            "performance_thresholds": {
                "max_response_time_ms": 5000,
                "max_memory_usage_mb": 512,
                "max_cpu_usage_percent": 80
            }
        }


# Global config manager instance
config_manager = IntegrationTestConfigManager()


# Convenience functions
def get_test_config(config_name: str = "full") -> IntegrationTestConfig:
    """Get a test configuration by name."""
    return config_manager.get_config(config_name)


def get_quick_test_config() -> IntegrationTestConfig:
    """Get quick test configuration for CI/CD."""
    return config_manager.get_config("quick")


def get_full_test_config() -> IntegrationTestConfig:
    """Get full test configuration for comprehensive testing."""
    return config_manager.get_config("full")


def get_error_focused_config() -> IntegrationTestConfig:
    """Get error handling focused configuration."""
    return config_manager.get_config("error_focused")


def list_test_configs() -> List[str]:
    """List all available test configurations."""
    return config_manager.list_available_configs()


def print_config_summary(config_name: str = "full"):
    """Print a summary of a test configuration."""
    summary = config_manager.get_config_summary(config_name)
    print(f"\nIntegration Test Config: {config_name}")
    print("=" * 40)
    for key, value in summary.items():
        print(f"{key:20}: {value}")
    print()


if __name__ == "__main__":
    # Demo usage
    print("Available Integration Test Configurations:")
    print("=" * 50)
    
    for config_name in list_test_configs():
        print_config_summary(config_name)
    
    # Example of creating custom config
    custom = config_manager.create_custom_config(
        "full",
        test_name="my_custom_test",
        max_test_duration_minutes=15
    )
    print(f"Created custom config: {custom.test_name}") 