"""
Logging Configuration Module

Provides different logging configurations for various environments and use cases.
"""

import os
from typing import Dict, Any, List
from pathlib import Path


class LoggingConfig:
    """Centralized logging configuration management"""
    
    @staticmethod
    def get_development_config() -> Dict[str, Any]:
        """Get logging configuration for development environment"""
        return {
            'level': 'DEBUG',
            'destinations': [
                {
                    'type': 'file',
                    'path': 'logs/app_debug.log',
                    'level': 'DEBUG',
                    'max_bytes': 5 * 1024 * 1024,  # 5MB
                    'backup_count': 3
                },
                {
                    'type': 'file',
                    'path': 'logs/error_debug.log',
                    'level': 'ERROR',
                    'max_bytes': 5 * 1024 * 1024,
                    'backup_count': 3
                },
                {
                    'type': 'file',
                    'path': 'logs/performance.log',
                    'level': 'INFO',
                    'max_bytes': 10 * 1024 * 1024,
                    'backup_count': 2
                },
                {
                    'type': 'console',
                    'level': 'INFO'
                }
            ],
            'format': 'structured',
            'include_context': True,
            'include_performance': True,
            'async_logging': False,  # Synchronous for debugging
            'sensitive_data_protection': True
        }
    
    @staticmethod
    def get_production_config() -> Dict[str, Any]:
        """Get logging configuration for production environment"""
        return {
            'level': 'INFO',
            'destinations': [
                {
                    'type': 'file',
                    'path': 'logs/app.log',
                    'level': 'INFO',
                    'max_bytes': 50 * 1024 * 1024,  # 50MB
                    'backup_count': 10
                },
                {
                    'type': 'file',
                    'path': 'logs/error.log',
                    'level': 'ERROR',
                    'max_bytes': 20 * 1024 * 1024,  # 20MB
                    'backup_count': 5
                },
                {
                    'type': 'file',
                    'path': 'logs/audit.log',
                    'level': 'WARNING',
                    'max_bytes': 30 * 1024 * 1024,  # 30MB
                    'backup_count': 7
                },
                {
                    'type': 'console',
                    'level': 'ERROR'  # Only errors to console in production
                }
            ],
            'format': 'structured',
            'include_context': True,
            'include_performance': False,  # Reduce overhead
            'async_logging': True,
            'sensitive_data_protection': True
        }
    
    @staticmethod
    def get_testing_config() -> Dict[str, Any]:
        """Get logging configuration for testing environment"""
        return {
            'level': 'WARNING',
            'destinations': [
                {
                    'type': 'file',
                    'path': 'logs/test.log',
                    'level': 'WARNING',
                    'max_bytes': 1 * 1024 * 1024,  # 1MB
                    'backup_count': 2
                },
                {
                    'type': 'console',
                    'level': 'ERROR'
                }
            ],
            'format': 'structured',
            'include_context': False,
            'include_performance': False,
            'async_logging': False,
            'sensitive_data_protection': True
        }
    
    @staticmethod
    def get_error_focused_config() -> Dict[str, Any]:
        """Get configuration focused on error logging and diagnostics"""
        return {
            'level': 'INFO',
            'destinations': [
                {
                    'type': 'file',
                    'path': 'logs/error_detailed.log',
                    'level': 'WARNING',
                    'max_bytes': 25 * 1024 * 1024,  # 25MB
                    'backup_count': 8
                },
                {
                    'type': 'file',
                    'path': 'logs/critical_errors.log',
                    'level': 'CRITICAL',
                    'max_bytes': 10 * 1024 * 1024,  # 10MB
                    'backup_count': 5
                },
                {
                    'type': 'file',
                    'path': 'logs/ui_errors.log',
                    'level': 'ERROR',
                    'max_bytes': 15 * 1024 * 1024,  # 15MB
                    'backup_count': 5
                },
                {
                    'type': 'file',
                    'path': 'logs/platform_errors.log',
                    'level': 'ERROR',
                    'max_bytes': 15 * 1024 * 1024,  # 15MB
                    'backup_count': 5
                },
                {
                    'type': 'console',
                    'level': 'ERROR'
                }
            ],
            'format': 'structured',
            'include_context': True,
            'include_performance': True,
            'async_logging': True,
            'sensitive_data_protection': True
        }
    
    @staticmethod
    def get_performance_focused_config() -> Dict[str, Any]:
        """Get configuration focused on performance monitoring"""
        return {
            'level': 'INFO',
            'destinations': [
                {
                    'type': 'file',
                    'path': 'logs/performance_detailed.log',
                    'level': 'INFO',
                    'max_bytes': 30 * 1024 * 1024,  # 30MB
                    'backup_count': 10
                },
                {
                    'type': 'file',
                    'path': 'logs/download_performance.log',
                    'level': 'INFO',
                    'max_bytes': 20 * 1024 * 1024,  # 20MB
                    'backup_count': 7
                },
                {
                    'type': 'file',
                    'path': 'logs/ui_performance.log',
                    'level': 'INFO',
                    'max_bytes': 15 * 1024 * 1024,  # 15MB
                    'backup_count': 5
                },
                {
                    'type': 'console',
                    'level': 'WARNING'
                }
            ],
            'format': 'structured',
            'include_context': True,
            'include_performance': True,
            'async_logging': True,
            'sensitive_data_protection': True
        }
    
    @staticmethod
    def get_minimal_config() -> Dict[str, Any]:
        """Get minimal logging configuration for resource-constrained environments"""
        return {
            'level': 'ERROR',
            'destinations': [
                {
                    'type': 'file',
                    'path': 'logs/minimal.log',
                    'level': 'ERROR',
                    'max_bytes': 5 * 1024 * 1024,  # 5MB
                    'backup_count': 2
                }
            ],
            'format': 'simple',
            'include_context': False,
            'include_performance': False,
            'async_logging': False,
            'sensitive_data_protection': True
        }
    
    @staticmethod
    def get_config_by_environment(environment: str = None) -> Dict[str, Any]:
        """Get logging configuration based on environment"""
        if environment is None:
            environment = os.getenv('ENVIRONMENT', 'development').lower()
        
        config_map = {
            'development': LoggingConfig.get_development_config,
            'dev': LoggingConfig.get_development_config,
            'production': LoggingConfig.get_production_config,
            'prod': LoggingConfig.get_production_config,
            'testing': LoggingConfig.get_testing_config,
            'test': LoggingConfig.get_testing_config,
            'error_focused': LoggingConfig.get_error_focused_config,
            'performance_focused': LoggingConfig.get_performance_focused_config,
            'minimal': LoggingConfig.get_minimal_config
        }
        
        config_func = config_map.get(environment, LoggingConfig.get_development_config)
        return config_func()
    
    @staticmethod
    def get_custom_config(
        level: str = 'INFO',
        file_destinations: List[Dict[str, Any]] = None,
        console_level: str = 'WARNING',
        include_context: bool = True,
        include_performance: bool = True,
        async_logging: bool = True
    ) -> Dict[str, Any]:
        """Create custom logging configuration"""
        destinations = []
        
        # Add file destinations
        if file_destinations:
            destinations.extend(file_destinations)
        else:
            # Default file destination
            destinations.append({
                'type': 'file',
                'path': 'logs/app.log',
                'level': level,
                'max_bytes': 10 * 1024 * 1024,
                'backup_count': 5
            })
        
        # Add console destination
        destinations.append({
            'type': 'console',
            'level': console_level
        })
        
        return {
            'level': level,
            'destinations': destinations,
            'format': 'structured',
            'include_context': include_context,
            'include_performance': include_performance,
            'async_logging': async_logging,
            'sensitive_data_protection': True
        }
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """Validate logging configuration"""
        required_keys = ['level', 'destinations']
        
        # Check required keys
        for key in required_keys:
            if key not in config:
                return False
        
        # Validate level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if config['level'] not in valid_levels:
            return False
        
        # Validate destinations
        if not isinstance(config['destinations'], list) or not config['destinations']:
            return False
        
        for dest in config['destinations']:
            if 'type' not in dest or 'level' not in dest:
                return False
            
            if dest['type'] == 'file' and 'path' not in dest:
                return False
        
        return True
    
    @staticmethod
    def create_log_directories(config: Dict[str, Any]):
        """Create necessary log directories based on configuration"""
        for dest in config.get('destinations', []):
            if dest.get('type') == 'file':
                log_path = Path(dest['path'])
                log_path.parent.mkdir(parents=True, exist_ok=True)


class ComponentLoggerConfig:
    """Configuration for component-specific loggers"""
    
    @staticmethod
    def get_ui_logger_config() -> Dict[str, Any]:
        """Configuration for UI component logging"""
        return {
            'name': 'ui',
            'level': 'INFO',
            'file_path': 'logs/ui_component.log',
            'include_user_actions': True,
            'include_performance': True,
            'tags': ['ui', 'user_interaction']
        }
    
    @staticmethod
    def get_platform_logger_config() -> Dict[str, Any]:
        """Configuration for platform handler logging"""
        return {
            'name': 'platform',
            'level': 'INFO',
            'file_path': 'logs/platform_handler.log',
            'include_api_calls': True,
            'include_performance': True,
            'tags': ['platform', 'api', 'external']
        }
    
    @staticmethod
    def get_download_logger_config() -> Dict[str, Any]:
        """Configuration for download service logging"""
        return {
            'name': 'download',
            'level': 'INFO',
            'file_path': 'logs/download_service.log',
            'include_file_operations': True,
            'include_performance': True,
            'tags': ['download', 'file_system', 'network']
        }
    
    @staticmethod
    def get_repository_logger_config() -> Dict[str, Any]:
        """Configuration for repository logging"""
        return {
            'name': 'repository',
            'level': 'INFO',
            'file_path': 'logs/repository.log',
            'include_database_operations': True,
            'include_performance': True,
            'tags': ['repository', 'database', 'data']
        }
    
    @staticmethod
    def get_service_logger_config() -> Dict[str, Any]:
        """Configuration for service layer logging"""
        return {
            'name': 'service',
            'level': 'INFO',
            'file_path': 'logs/service_layer.log',
            'include_business_logic': True,
            'include_performance': True,
            'tags': ['service', 'business_logic']
        }


class LogRotationConfig:
    """Configuration for log rotation policies"""
    
    @staticmethod
    def get_daily_rotation() -> Dict[str, Any]:
        """Daily log rotation configuration"""
        return {
            'when': 'midnight',
            'interval': 1,
            'backup_count': 30,  # Keep 30 days
            'encoding': 'utf-8'
        }
    
    @staticmethod
    def get_weekly_rotation() -> Dict[str, Any]:
        """Weekly log rotation configuration"""
        return {
            'when': 'W0',  # Monday
            'interval': 1,
            'backup_count': 12,  # Keep 12 weeks
            'encoding': 'utf-8'
        }
    
    @staticmethod
    def get_size_based_rotation(max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5) -> Dict[str, Any]:
        """Size-based log rotation configuration"""
        return {
            'max_bytes': max_bytes,
            'backup_count': backup_count,
            'encoding': 'utf-8'
        }


class LogFilterConfig:
    """Configuration for log filtering"""
    
    @staticmethod
    def get_error_category_filter(categories: List[str]) -> Dict[str, Any]:
        """Filter configuration for specific error categories"""
        return {
            'type': 'error_category',
            'categories': categories,
            'action': 'include'  # or 'exclude'
        }
    
    @staticmethod
    def get_component_filter(components: List[str]) -> Dict[str, Any]:
        """Filter configuration for specific components"""
        return {
            'type': 'component',
            'components': components,
            'action': 'include'
        }
    
    @staticmethod
    def get_severity_filter(min_severity: str) -> Dict[str, Any]:
        """Filter configuration for minimum severity level"""
        return {
            'type': 'severity',
            'min_severity': min_severity,
            'action': 'include'
        }
    
    @staticmethod
    def get_performance_filter(min_execution_time_ms: float) -> Dict[str, Any]:
        """Filter configuration for performance metrics"""
        return {
            'type': 'performance',
            'min_execution_time_ms': min_execution_time_ms,
            'action': 'include'
        } 