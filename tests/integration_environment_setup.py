#!/usr/bin/env python3
"""
Integration Testing Environment Setup
====================================

This module provides comprehensive environment setup for integration testing
of Social Download Manager v2.0. It prepares databases, mock services, test data,
and configuration required for testing component integration.
"""

import os
import sys
import shutil
import sqlite3
import tempfile
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from unittest.mock import MagicMock, patch
import threading
import time
import unittest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class IntegrationTestEnvironment:
    """Manages the complete integration testing environment setup and teardown."""
    
    def __init__(self, test_name: str = "integration_test"):
        self.test_name = test_name
        self.test_dir = Path(tempfile.mkdtemp(prefix=f"{test_name}_"))
        self.original_dir = Path.cwd()
        self.databases = {}
        self.mock_services = {}
        self.config_backup = {}
        self.cleanup_tasks = []
        
        # Setup logging for environment setup
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for environment operations."""
        logger = logging.getLogger(f"integration_env_{self.test_name}")
        logger.setLevel(logging.DEBUG)
        
        # Create handler for test environment logging
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
        
    def setup_complete_environment(self) -> Dict[str, Any]:
        """Setup complete integration testing environment."""
        self.logger.info(f"Setting up integration environment: {self.test_name}")
        
        environment_info = {
            'test_dir': str(self.test_dir),
            'databases': {},
            'mock_services': {},
            'config_files': {},
            'test_data': {}
        }
        
        try:
            # 1. Create directory structure
            self._create_directory_structure()
            
            # 2. Setup test databases
            environment_info['databases'] = self._setup_test_databases()
            
            # 3. Setup mock services
            environment_info['mock_services'] = self._setup_mock_services()
            
            # 4. Create test configuration
            environment_info['config_files'] = self._setup_test_configuration()
            
            # 5. Generate test data
            environment_info['test_data'] = self._generate_test_data()
            
            # 6. Setup environment variables
            self._setup_environment_variables()
            
            # 7. Initialize component mocks
            self._setup_component_mocks()
            
            self.logger.info("Integration environment setup completed successfully")
            return environment_info
            
        except Exception as e:
            self.logger.error(f"Failed to setup environment: {e}")
            self.cleanup()
            raise
            
    def _create_directory_structure(self):
        """Create required directory structure for testing."""
        directories = [
            'data/database',
            'data/models', 
            'logs',
            'downloads',
            'test_assets',
            'mock_responses',
            'backup'
        ]
        
        for dir_path in directories:
            full_path = self.test_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created directory: {full_path}")
            
    def _setup_test_databases(self) -> Dict[str, str]:
        """Setup test databases for integration testing."""
        databases = {}
        
        # 1. Create clean v2.0 database
        v2_db_path = self.test_dir / 'data' / 'database' / 'test_v2.db'
        databases['v2_clean'] = str(v2_db_path)
        self._create_v2_database(v2_db_path)
        
        # 2. Create v1.2.1 database for migration testing
        v1_db_path = self.test_dir / 'data' / 'database' / 'test_v1.db'
        databases['v1_migration'] = str(v1_db_path)
        self._create_v1_database(v1_db_path)
        
        # 3. Create corrupted database for error testing
        corrupted_db_path = self.test_dir / 'data' / 'database' / 'test_corrupted.db'
        databases['corrupted'] = str(corrupted_db_path)
        self._create_corrupted_database(corrupted_db_path)
        
        self.databases = databases
        self.logger.info(f"Setup {len(databases)} test databases")
        return databases
        
    def _create_v2_database(self, db_path: Path) -> None:
        """Create v2.0 database with schema."""
        try:
            conn = sqlite3.connect(str(db_path))
            
            # Try to use the full schema first
            schema_path = PROJECT_ROOT / 'data' / 'database' / 'schema_v2_sqlite.sql'
            
            if schema_path.exists():
                try:
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        schema_sql = f.read()
                    
                    # Split and execute statements individually to avoid executescript issues
                    statements = self._split_sql_statements(schema_sql)
                    
                    for statement in statements:
                        if statement.strip():
                            try:
                                conn.execute(statement)
                            except sqlite3.Error as e:
                                self.logger.debug(f"Skipping statement due to error: {e}")
                                continue
                    
                    conn.commit()
                    self.logger.debug(f"Created v2 database using full schema at {db_path}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to use full schema: {e}, falling back to minimal schema")
                    conn.close()
                    db_path.unlink(missing_ok=True)
                    conn = sqlite3.connect(str(db_path))
                    self._create_minimal_v2_schema(conn)
            else:
                self.logger.warning("Full schema not found, using minimal schema")
                self._create_minimal_v2_schema(conn)
                
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to create v2 database: {e}")
            # Create minimal fallback
            conn = sqlite3.connect(str(db_path))
            self._create_minimal_v2_schema(conn)
            conn.close()

    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """Split SQL content into individual statements, handling complex cases."""
        # Remove comments and normalize whitespace
        lines = []
        for line in sql_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                lines.append(line)
        
        content = ' '.join(lines)
        
        # Split by semicolon but be careful about strings and complex statements
        statements = []
        current_statement = ""
        in_string = False
        string_char = None
        
        i = 0
        while i < len(content):
            char = content[i]
            
            if not in_string:
                if char in ["'", '"']:
                    in_string = True
                    string_char = char
                elif char == ';':
                    current_statement += char
                    statements.append(current_statement.strip())
                    current_statement = ""
                    i += 1
                    continue
            else:
                if char == string_char:
                    # Check if it's escaped
                    if i + 1 < len(content) and content[i + 1] == string_char:
                        # Escaped quote, skip both
                        current_statement += char + content[i + 1]
                        i += 2
                        continue
                    else:
                        in_string = False
                        string_char = None
            
            current_statement += char
            i += 1
        
        # Add any remaining statement
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements

    def _create_minimal_v2_schema(self, conn: sqlite3.Connection) -> None:
        """Create minimal v2.0 schema for testing."""
        minimal_schema = """
        PRAGMA foreign_keys = ON;
        
        CREATE TABLE platforms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) NOT NULL UNIQUE,
            display_name VARCHAR(100) NOT NULL,
            base_url VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform_id INTEGER NOT NULL,
            original_url TEXT NOT NULL,
            platform_content_id VARCHAR(255),
            title TEXT,
            description TEXT,
            content_type VARCHAR(50) NOT NULL DEFAULT 'video',
            status VARCHAR(50) DEFAULT 'pending',
            author_name VARCHAR(255),
            view_count BIGINT DEFAULT 0,
            like_count BIGINT DEFAULT 0,
            published_at TIMESTAMP,
            local_file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_deleted BOOLEAN DEFAULT FALSE,
            
            FOREIGN KEY (platform_id) REFERENCES platforms(id),
            UNIQUE(platform_id, platform_content_id)
        );
        
        CREATE TABLE downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            status VARCHAR(50) DEFAULT 'queued',
            progress_percentage DECIMAL(5,2) DEFAULT 0.00,
            final_file_path TEXT,
            queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            error_count INTEGER DEFAULT 0,
            last_error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE
        );
        
        INSERT INTO platforms (name, display_name, base_url, is_active) VALUES
        ('youtube', 'YouTube', 'https://www.youtube.com', TRUE),
        ('tiktok', 'TikTok', 'https://www.tiktok.com', TRUE);
        """
        
        conn.executescript(minimal_schema)
        self.logger.debug("Created minimal v2 schema")
        
    def _create_v1_database(self, db_path: Path):
        """Create v1.2.1 database for migration testing."""
        conn = sqlite3.connect(str(db_path))
        
        # v1.2.1 schema (simplified)
        conn.executescript("""
            CREATE TABLE downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                platform TEXT,
                file_path TEXT,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            INSERT INTO downloads (url, title, platform, file_path) VALUES
            ('https://www.tiktok.com/@user/video/123', 'Test Video 1', 'tiktok', '/downloads/video1.mp4'),
            ('https://www.tiktok.com/@user/video/456', 'Test Video 2', 'tiktok', '/downloads/video2.mp4');
        """)
        
        conn.close()
        self.logger.debug(f"Created v1.2.1 database: {db_path}")
        
    def _create_corrupted_database(self, db_path: Path):
        """Create corrupted database for error handling testing."""
        # Create a file that looks like a database but is corrupted
        with open(db_path, 'wb') as f:
            f.write(b'SQLite format 3\x00' + b'\x00' * 100 + b'corrupted_data' * 50)
            
        self.logger.debug(f"Created corrupted database: {db_path}")
        
    def _setup_mock_services(self) -> Dict[str, Any]:
        """Setup mock services for external API calls."""
        mock_services = {}
        
        # 1. TikTok API Mock
        tiktok_mock = self._create_tiktok_mock()
        mock_services['tiktok'] = tiktok_mock
        
        # 2. YouTube API Mock
        youtube_mock = self._create_youtube_mock()
        mock_services['youtube'] = youtube_mock
        
        # 3. Network Mock for error scenarios
        network_mock = self._create_network_mock()
        mock_services['network'] = network_mock
        
        self.mock_services = mock_services
        self.logger.info(f"Setup {len(mock_services)} mock services")
        return mock_services
        
    def _create_tiktok_mock(self) -> Dict[str, Any]:
        """Create TikTok API mock responses."""
        mock_responses = {
            'success_response': {
                'id': '7234567890123456789',
                'title': 'Test TikTok Video',
                'author': 'test_user',
                'duration': 30,
                'view_count': 1000,
                'download_urls': {
                    'video': 'https://mock-cdn.tiktok.com/video.mp4',
                    'audio': 'https://mock-cdn.tiktok.com/audio.mp3'
                }
            },
            'error_response': {
                'error': 'Video not found',
                'code': 404
            },
            'rate_limit_response': {
                'error': 'Rate limit exceeded',
                'code': 429,
                'retry_after': 60
            }
        }
        
        # Save mock responses to file
        mock_file = self.test_dir / 'mock_responses' / 'tiktok_responses.json'
        with open(mock_file, 'w') as f:
            json.dump(mock_responses, f, indent=2)
            
        return {
            'type': 'tiktok_api',
            'responses_file': str(mock_file),
            'responses': mock_responses
        }
        
    def _create_youtube_mock(self) -> Dict[str, Any]:
        """Create YouTube API mock responses."""
        mock_responses = {
            'success_response': {
                'id': 'dQw4w9WgXcQ',
                'title': 'Test YouTube Video',
                'channel': 'Test Channel',
                'duration': '3:32',
                'view_count': 50000,
                'download_urls': {
                    'video': 'https://mock-youtube.com/video.mp4',
                    'audio': 'https://mock-youtube.com/audio.mp3'
                }
            },
            'private_video_response': {
                'error': 'Video is private',
                'code': 403
            }
        }
        
        mock_file = self.test_dir / 'mock_responses' / 'youtube_responses.json'
        with open(mock_file, 'w') as f:
            json.dump(mock_responses, f, indent=2)
            
        return {
            'type': 'youtube_api',
            'responses_file': str(mock_file),
            'responses': mock_responses
        }
        
    def _create_network_mock(self) -> Dict[str, Any]:
        """Create network error mock scenarios."""
        network_scenarios = {
            'timeout': {'exception': 'TimeoutError', 'message': 'Request timed out'},
            'connection_error': {'exception': 'ConnectionError', 'message': 'Failed to connect'},
            'dns_error': {'exception': 'DNSError', 'message': 'DNS resolution failed'},
            'ssl_error': {'exception': 'SSLError', 'message': 'SSL handshake failed'}
        }
        
        mock_file = self.test_dir / 'mock_responses' / 'network_errors.json'
        with open(mock_file, 'w') as f:
            json.dump(network_scenarios, f, indent=2)
            
        return {
            'type': 'network_errors',
            'scenarios_file': str(mock_file),
            'scenarios': network_scenarios
        }
        
    def _setup_test_configuration(self) -> Dict[str, str]:
        """Setup test configuration files."""
        config_files = {}
        
        # 1. Main config
        main_config = {
            'database': {
                'path': str(self.test_dir / 'data' / 'database' / 'test_v2.db'),
                'backup_path': str(self.test_dir / 'backup'),
                'migration_enabled': True
            },
            'downloads': {
                'path': str(self.test_dir / 'downloads'),
                'max_concurrent': 3,
                'timeout': 30
            },
            'logging': {
                'level': 'DEBUG',
                'file': str(self.test_dir / 'logs' / 'test.log'),
                'console': True
            },
            'platforms': {
                'tiktok': {
                    'enabled': True,
                    'mock_mode': True
                },
                'youtube': {
                    'enabled': True,
                    'mock_mode': True
                }
            }
        }
        
        config_file = self.test_dir / 'config.json'
        with open(config_file, 'w') as f:
            json.dump(main_config, f, indent=2)
        config_files['main'] = str(config_file)
        
        # 2. Error handling config
        error_config = {
            'categorization': {
                'enabled': True,
                'auto_classify': True
            },
            'recovery': {
                'enabled': True,
                'max_attempts': 3,
                'fallback_enabled': True
            },
            'logging': {
                'enabled': True,
                'level': 'DEBUG'
            }
        }
        
        error_config_file = self.test_dir / 'error_config.json'
        with open(error_config_file, 'w') as f:
            json.dump(error_config, f, indent=2)
        config_files['error_handling'] = str(error_config_file)
        
        self.logger.info(f"Created {len(config_files)} configuration files")
        return config_files
        
    def _generate_test_data(self) -> Dict[str, Any]:
        """Generate test data for integration testing."""
        test_data = {}
        
        # 1. Valid URLs for testing
        test_urls = {
            'tiktok': [
                'https://www.tiktok.com/@testuser/video/7234567890123456789',
                'https://vm.tiktok.com/ZMJAbCdEf/',
                'https://www.tiktok.com/@user2/video/7234567890123456790'
            ],
            'youtube': [
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'https://youtu.be/dQw4w9WgXcQ',
                'https://www.youtube.com/watch?v=abcdefghijk'
            ],
            'invalid': [
                'https://invalid-url.com/video',
                'not-a-url',
                'https://unsupported-platform.com/video/123'
            ]
        }
        
        urls_file = self.test_dir / 'test_assets' / 'test_urls.json'
        with open(urls_file, 'w') as f:
            json.dump(test_urls, f, indent=2)
        test_data['urls'] = str(urls_file)
        
        # 2. User scenarios
        user_scenarios = [
            {
                'name': 'Single Video Download',
                'steps': [
                    'Enter TikTok URL',
                    'Click download',
                    'Wait for completion',
                    'Verify file saved'
                ],
                'expected_outcome': 'Video downloaded successfully'
            },
            {
                'name': 'Batch Download',
                'steps': [
                    'Enter multiple URLs',
                    'Start batch download',
                    'Monitor progress',
                    'Verify all files saved'
                ],
                'expected_outcome': 'All videos downloaded'
            },
            {
                'name': 'Error Recovery',
                'steps': [
                    'Enter invalid URL',
                    'Attempt download',
                    'Observe error handling',
                    'Try recovery suggestions'
                ],
                'expected_outcome': 'Graceful error handling'
            }
        ]
        
        scenarios_file = self.test_dir / 'test_assets' / 'user_scenarios.json'
        with open(scenarios_file, 'w') as f:
            json.dump(user_scenarios, f, indent=2)
        test_data['scenarios'] = str(scenarios_file)
        
        self.logger.info(f"Generated test data with {len(test_urls)} URL sets and {len(user_scenarios)} scenarios")
        return test_data
        
    def _setup_environment_variables(self):
        """Setup environment variables for testing."""
        env_vars = {
            'TEST_MODE': 'true',
            'DATABASE_PATH': str(self.test_dir / 'data' / 'database' / 'test_v2.db'),
            'DOWNLOADS_PATH': str(self.test_dir / 'downloads'),
            'LOG_LEVEL': 'DEBUG',
            'MOCK_SERVICES': 'true'
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
            self.cleanup_tasks.append(lambda k=key: os.environ.pop(k, None))
            
        self.logger.debug(f"Set {len(env_vars)} environment variables")
        
    def _setup_component_mocks(self):
        """Setup component-level mocks for testing."""
        # Mock external dependencies that aren't part of integration testing
        
        # 1. Mock file system operations for controlled testing
        self.mock_services['file_system'] = MagicMock()
        
        # 2. Mock network requests for predictable responses
        self.mock_services['requests'] = MagicMock()
        
        # 3. Mock system notifications
        self.mock_services['notifications'] = MagicMock()
        
        self.logger.debug("Setup component mocks")
        
    def apply_mocks(self) -> List[unittest.mock._patch]:
        """Apply mock patches for integration testing."""
        patches = []
        
        try:
            # Mock TikTok handler
            tiktok_patch = patch('platforms.tiktok.tiktok_handler.TikTokHandler')
            tiktok_mock = tiktok_patch.start()
            tiktok_mock.return_value.extract_video_info.return_value = {
                'title': 'Mock TikTok Video',
                'author': 'mock_user',
                'duration': 30,
                'view_count': 1000
            }
            patches.append(tiktok_patch)
            
            # Mock YouTube handler
            youtube_patch = patch('platforms.youtube.youtube_handler.YouTubeHandler')
            youtube_mock = youtube_patch.start()
            youtube_mock.return_value.extract_video_info.return_value = {
                'title': 'Mock YouTube Video',
                'author': 'mock_channel',
                'duration': 180,
                'view_count': 5000
            }
            patches.append(youtube_patch)
            
            # Mock network requests if requests module is available
            try:
                import requests
                requests_patch = patch('requests.get')
                requests_mock = requests_patch.start()
                requests_mock.return_value.status_code = 200
                requests_mock.return_value.json.return_value = {'status': 'mock_response'}
                patches.append(requests_patch)
            except ImportError:
                self.logger.debug("Requests module not available for mocking")
            
            self.logger.debug("Setup component mocks")
            
        except Exception as e:
            self.logger.warning(f"Failed to apply some mocks: {e}")
            # Continue with partial mocks
        
        return patches
        
    def get_test_database_path(self, db_type: str = 'v2_clean') -> str:
        """Get path to specific test database."""
        return self.databases.get(db_type, '')
        
    def get_test_config_path(self, config_type: str = 'main') -> str:
        """Get path to specific test configuration."""
        config_files = getattr(self, 'config_files', {})
        return config_files.get(config_type, '')
        
    def cleanup(self):
        """Clean up test environment."""
        self.logger.info(f"Cleaning up integration environment: {self.test_name}")
        
        # Run cleanup tasks
        for cleanup_task in self.cleanup_tasks:
            try:
                cleanup_task()
            except Exception as e:
                self.logger.warning(f"Cleanup task failed: {e}")
        
        # Remove test directory
        if self.test_dir.exists():
            try:
                shutil.rmtree(self.test_dir)
                self.logger.debug(f"Removed test directory: {self.test_dir}")
            except Exception as e:
                self.logger.warning(f"Failed to remove test directory: {e}")
                
        # Change back to original directory
        os.chdir(self.original_dir)


class IntegrationTestRunner:
    """Runs integration tests with proper environment setup."""
    
    def __init__(self, test_suite_name: str = "integration_tests"):
        self.test_suite_name = test_suite_name
        self.environment = None
        self.patches = []
        
    def __enter__(self):
        """Setup environment on entering context."""
        self.environment = IntegrationTestEnvironment(self.test_suite_name)
        env_info = self.environment.setup_complete_environment()
        self.patches = self.environment.apply_mocks()
        return self.environment, env_info
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup environment on exiting context."""
        # Stop all patches
        for patch_obj in self.patches:
            try:
                patch_obj.stop()
            except Exception as e:
                print(f"Failed to stop patch: {e}")
                
        # Cleanup environment
        if self.environment:
            self.environment.cleanup()


# Utility functions for test setup
def create_integration_environment(test_name: str = "integration_test") -> IntegrationTestEnvironment:
    """Create and setup integration test environment."""
    env = IntegrationTestEnvironment(test_name)
    env.setup_complete_environment()
    return env


def verify_environment_health(env: IntegrationTestEnvironment) -> Dict[str, bool]:
    """Verify that the integration environment is healthy and ready for testing."""
    health_checks = {}
    
    # Check databases
    for db_name, db_path in env.databases.items():
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("SELECT 1").fetchone()
            conn.close()
            health_checks[f"database_{db_name}"] = True
        except Exception:
            health_checks[f"database_{db_name}"] = False
    
    # Check test directory
    health_checks["test_directory"] = env.test_dir.exists()
    
    # Check configuration files
    health_checks["config_files"] = all(
        Path(path).exists() for path in getattr(env, 'config_files', {}).values()
    )
    
    # Check mock services
    health_checks["mock_services"] = bool(env.mock_services)
    
    return health_checks


if __name__ == "__main__":
    # Demo usage
    print("Setting up integration test environment...")
    
    with IntegrationTestRunner("demo_test") as (env, env_info):
        print(f"Environment setup in: {env_info['test_dir']}")
        print(f"Databases: {list(env_info['databases'].keys())}")
        print(f"Mock services: {list(env_info['mock_services'].keys())}")
        
        # Verify environment health
        health = verify_environment_health(env)
        print(f"Environment health: {health}")
        
        print("Environment is ready for integration testing!")
        
    print("Environment cleanup completed.") 