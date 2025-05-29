# Migration Path Definition for Social Download Manager v2.0

## Overview

This document defines the comprehensive migration strategy for evolving the Social Download Manager database schema from version 1.x to 2.0 and establishes ongoing migration procedures for future schema changes.

## Migration Strategy Overview

### 1. **Current State Analysis (v1.2.1)**

#### Existing Schema Limitations
```python
# Current v1.2.1 model structure (from data/models/content_model.py)
class ContentModel:
    def __init__(self):
        self.id = None
        self.url = None
        self.title = None
        self.author = None
        self.platform = None
        self.metadata = {}  # JSON blob - not queryable
        self.download_info = {}  # Nested structure
        self.created_at = None
```

**Key Issues to Address:**
- Single monolithic table structure
- JSON blob storage (not efficiently queryable)
- Mixed data types in single fields
- No proper relationship modeling
- Limited scalability for metadata queries
- No audit trail or versioning

### 2. **Target Schema (v2.0)**

#### New Normalized Structure
- **11 core tables** with proper relationships
- **Flexible metadata system** with key-value storage
- **Comprehensive download tracking** with sessions and errors
- **Performance-optimized indexes** for common queries
- **Audit trails and versioning** throughout

## Migration Phases

### Phase 1: Schema Creation and Initialization (Zero Data Impact)

#### 1.1 Create New Schema Alongside Existing
```sql
-- File: data/database/migration_scripts/001_create_v2_schema.sql
-- Create new v2.0 schema without affecting existing data

-- Enable WAL mode for concurrent access
PRAGMA journal_mode = WAL;

-- Create all new v2.0 tables
-- (Include full schema from schema_v2_sqlite.sql)

-- Create migration tracking table
CREATE TABLE migration_status (
    migration_id VARCHAR(50) PRIMARY KEY,
    description TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',
    error_message TEXT,
    records_processed INTEGER DEFAULT 0,
    total_records INTEGER DEFAULT 0
);

-- Insert initial migration record
INSERT INTO migration_status (migration_id, description, total_records)
SELECT 
    '001_create_v2_schema', 
    'Create v2.0 schema tables and indexes',
    COUNT(*) 
FROM content_v1;  -- Assuming current table is named content_v1
```

#### 1.2 Data Migration Scripts
```sql
-- File: data/database/migration_scripts/002_migrate_platforms.sql
-- Migrate platform data first (reference table)

INSERT INTO platforms (name, display_name, base_url, is_active)
SELECT DISTINCT 
    LOWER(platform) as name,
    platform as display_name,
    CASE 
        WHEN LOWER(platform) = 'youtube' THEN 'https://www.youtube.com'
        WHEN LOWER(platform) = 'tiktok' THEN 'https://www.tiktok.com'
        WHEN LOWER(platform) = 'instagram' THEN 'https://www.instagram.com'
        ELSE NULL
    END as base_url,
    TRUE as is_active
FROM content_v1 
WHERE platform IS NOT NULL
ON CONFLICT(name) DO NOTHING;

UPDATE migration_status 
SET records_processed = (SELECT COUNT(*) FROM platforms),
    status = 'completed',
    completed_at = CURRENT_TIMESTAMP
WHERE migration_id = '002_migrate_platforms';
```

```sql
-- File: data/database/migration_scripts/003_migrate_content.sql
-- Migrate core content data

INSERT INTO content (
    platform_id,
    original_url,
    platform_content_id,
    title,
    description,
    content_type,
    status,
    author_name,
    author_id,
    duration_seconds,
    file_size_bytes,
    view_count,
    like_count,
    comment_count,
    published_at,
    local_file_path,
    thumbnail_path,
    created_at,
    updated_at
)
SELECT 
    p.id as platform_id,
    c1.url as original_url,
    -- Extract platform-specific ID from metadata
    CASE 
        WHEN p.name = 'youtube' THEN json_extract(c1.metadata, '$.id')
        WHEN p.name = 'tiktok' THEN json_extract(c1.metadata, '$.aweme_id')
        WHEN p.name = 'instagram' THEN json_extract(c1.metadata, '$.pk')
        ELSE NULL
    END as platform_content_id,
    c1.title,
    json_extract(c1.metadata, '$.description') as description,
    COALESCE(json_extract(c1.metadata, '$.content_type'), 'video') as content_type,
    CASE 
        WHEN c1.download_info IS NOT NULL AND json_extract(c1.download_info, '$.status') = 'completed' 
        THEN 'completed'
        ELSE 'pending'
    END as status,
    c1.author as author_name,
    json_extract(c1.metadata, '$.uploader_id') as author_id,
    CAST(json_extract(c1.metadata, '$.duration') AS INTEGER) as duration_seconds,
    CAST(json_extract(c1.download_info, '$.file_size') AS INTEGER) as file_size_bytes,
    CAST(COALESCE(json_extract(c1.metadata, '$.view_count'), 0) AS INTEGER) as view_count,
    CAST(COALESCE(json_extract(c1.metadata, '$.like_count'), 0) AS INTEGER) as like_count,
    CAST(COALESCE(json_extract(c1.metadata, '$.comment_count'), 0) AS INTEGER) as comment_count,
    CASE 
        WHEN json_extract(c1.metadata, '$.upload_date') IS NOT NULL 
        THEN datetime(json_extract(c1.metadata, '$.upload_date'))
        ELSE NULL
    END as published_at,
    json_extract(c1.download_info, '$.file_path') as local_file_path,
    json_extract(c1.download_info, '$.thumbnail_path') as thumbnail_path,
    c1.created_at,
    CURRENT_TIMESTAMP as updated_at
FROM content_v1 c1
JOIN platforms p ON LOWER(p.name) = LOWER(c1.platform);

UPDATE migration_status 
SET records_processed = (SELECT COUNT(*) FROM content),
    status = 'completed',
    completed_at = CURRENT_TIMESTAMP
WHERE migration_id = '003_migrate_content';
```

#### 1.3 Metadata Migration
```sql
-- File: data/database/migration_scripts/004_migrate_metadata.sql
-- Extract and migrate metadata from JSON blobs

-- Platform-specific metadata extraction
INSERT INTO content_metadata (content_id, metadata_type, metadata_key, metadata_value, data_type)
SELECT 
    c.id as content_id,
    'platform_specific' as metadata_type,
    'youtube_video_id' as metadata_key,
    json_extract(c1.metadata, '$.id') as metadata_value,
    'string' as data_type
FROM content c
JOIN content_v1 c1 ON c.original_url = c1.url
JOIN platforms p ON c.platform_id = p.id
WHERE p.name = 'youtube' 
  AND json_extract(c1.metadata, '$.id') IS NOT NULL;

-- Video specifications metadata
INSERT INTO content_metadata (content_id, metadata_type, metadata_key, metadata_value, data_type)
SELECT 
    c.id as content_id,
    'video_specs' as metadata_type,
    spec_key,
    spec_value,
    spec_data_type
FROM content c
JOIN content_v1 c1 ON c.original_url = c1.url
JOIN (
    SELECT 'resolution_width' as spec_key, '$.width' as json_path, 'integer' as spec_data_type
    UNION ALL SELECT 'resolution_height', '$.height', 'integer'
    UNION ALL SELECT 'fps', '$.fps', 'float'
    UNION ALL SELECT 'video_codec', '$.vcodec', 'string'
    UNION ALL SELECT 'audio_codec', '$.acodec', 'string'
) specs ON json_extract(c1.metadata, specs.json_path) IS NOT NULL
CROSS JOIN (
    SELECT 
        specs.spec_key,
        json_extract(c1.metadata, specs.json_path) as spec_value,
        specs.spec_data_type
) extracted_specs;

UPDATE migration_status 
SET records_processed = (SELECT COUNT(*) FROM content_metadata),
    status = 'completed',
    completed_at = CURRENT_TIMESTAMP
WHERE migration_id = '004_migrate_metadata';
```

### Phase 2: Parallel Operation (Gradual Transition)

#### 2.1 Dual-Write Implementation
```python
# File: core/services/database/dual_write_service.py
class DualWriteService:
    """
    Service to write to both old and new schema during migration period
    """
    
    def __init__(self, old_db_connection, new_db_connection):
        self.old_db = old_db_connection
        self.new_db = new_db_connection
        self.migration_mode = True
    
    def save_content(self, content_data):
        """Save content to both schemas"""
        try:
            # Write to new schema first
            new_content_id = self._save_to_new_schema(content_data)
            
            # Write to old schema for compatibility
            old_content_id = self._save_to_old_schema(content_data)
            
            # Log successful dual write
            self._log_migration_event('content_saved', {
                'old_id': old_content_id,
                'new_id': new_content_id,
                'url': content_data.get('url')
            })
            
            return new_content_id
            
        except Exception as e:
            # Rollback on failure
            self._handle_dual_write_failure(e, content_data)
            raise
    
    def _save_to_new_schema(self, content_data):
        """Save to v2.0 normalized schema"""
        with self.new_db.transaction():
            # Insert into content table
            content_id = self._insert_content(content_data)
            
            # Insert metadata
            self._insert_metadata(content_id, content_data.get('metadata', {}))
            
            # Insert quality options if available
            self._insert_quality_options(content_id, content_data.get('formats', []))
            
            return content_id
```

#### 2.2 Read Migration (Gradual Cutover)
```python
# File: core/services/database/migration_read_service.py
class MigrationReadService:
    """
    Service to gradually migrate reads from old to new schema
    """
    
    def __init__(self, config):
        self.read_percentage_new = config.get('read_percentage_new', 0)
        self.feature_flags = config.get('feature_flags', {})
    
    def get_content(self, content_id, use_new_schema=None):
        """Get content with gradual migration to new schema"""
        
        # Determine which schema to use
        if use_new_schema is None:
            use_new_schema = self._should_use_new_schema(content_id)
        
        if use_new_schema:
            return self._get_content_from_new_schema(content_id)
        else:
            return self._get_content_from_old_schema(content_id)
    
    def _should_use_new_schema(self, content_id):
        """Determine if we should use new schema based on migration strategy"""
        
        # Feature flag override
        if self.feature_flags.get('force_new_schema'):
            return True
        
        if self.feature_flags.get('force_old_schema'):
            return False
        
        # Percentage-based rollout
        if random.randint(1, 100) <= self.read_percentage_new:
            return True
        
        # ID-based rollout (consistent per content)
        if content_id % 10 < (self.read_percentage_new / 10):
            return True
        
        return False
```

### Phase 3: Data Validation and Integrity Checks

#### 3.1 Data Consistency Verification
```sql
-- File: data/database/migration_scripts/005_validate_migration.sql
-- Comprehensive data validation queries

-- Validate content migration completeness
CREATE TEMP VIEW migration_validation AS
SELECT 
    'content_count' as check_name,
    (SELECT COUNT(*) FROM content_v1) as old_count,
    (SELECT COUNT(*) FROM content) as new_count,
    CASE 
        WHEN (SELECT COUNT(*) FROM content_v1) = (SELECT COUNT(*) FROM content) 
        THEN 'PASS' 
        ELSE 'FAIL' 
    END as status;

-- Validate metadata extraction
INSERT INTO migration_validation
SELECT 
    'metadata_extracted' as check_name,
    (SELECT COUNT(DISTINCT id) FROM content_v1 WHERE metadata IS NOT NULL AND metadata != '{}') as old_count,
    (SELECT COUNT(DISTINCT content_id) FROM content_metadata) as new_count,
    CASE 
        WHEN (SELECT COUNT(DISTINCT content_id) FROM content_metadata) > 0 
        THEN 'PASS' 
        ELSE 'FAIL' 
    END as status;

-- Validate platform relationships
INSERT INTO migration_validation
SELECT 
    'platform_relationships' as check_name,
    (SELECT COUNT(DISTINCT platform) FROM content_v1 WHERE platform IS NOT NULL) as old_count,
    (SELECT COUNT(*) FROM platforms WHERE is_active = TRUE) as new_count,
    CASE 
        WHEN (SELECT COUNT(*) FROM platforms WHERE is_active = TRUE) >= 
             (SELECT COUNT(DISTINCT platform) FROM content_v1 WHERE platform IS NOT NULL)
        THEN 'PASS' 
        ELSE 'FAIL' 
    END as status;

-- Generate validation report
SELECT * FROM migration_validation;
```

#### 3.2 Performance Validation
```sql
-- File: data/database/migration_scripts/006_performance_validation.sql
-- Test query performance on migrated data

-- Create performance benchmark table
CREATE TABLE migration_performance_tests (
    test_name VARCHAR(100),
    query_sql TEXT,
    execution_time_ms INTEGER,
    records_returned INTEGER,
    test_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Test content listing performance
INSERT INTO migration_performance_tests (test_name, query_sql, execution_time_ms, records_returned)
SELECT 
    'content_listing_by_platform',
    'SELECT * FROM content c JOIN platforms p ON c.platform_id = p.id WHERE p.name = ''youtube'' LIMIT 100',
    -- Measure execution time (implementation specific)
    0, -- Will be updated by actual test runner
    (SELECT COUNT(*) FROM content c JOIN platforms p ON c.platform_id = p.id WHERE p.name = 'youtube' LIMIT 100);

-- Test metadata query performance
INSERT INTO migration_performance_tests (test_name, query_sql, execution_time_ms, records_returned)
SELECT 
    'metadata_lookup',
    'SELECT * FROM content_metadata WHERE content_id = 1',
    0,
    (SELECT COUNT(*) FROM content_metadata WHERE content_id = 1);
```

### Phase 4: Final Cutover and Cleanup

#### 4.1 Final Data Synchronization
```sql
-- File: data/database/migration_scripts/007_final_sync.sql
-- Ensure all data is synchronized before cutover

-- Sync any remaining data created during migration period
INSERT OR IGNORE INTO content (...)
SELECT ... FROM content_v1 
WHERE created_at > (SELECT MAX(created_at) FROM content);

-- Update migration completion status
UPDATE migration_status 
SET status = 'completed', completed_at = CURRENT_TIMESTAMP
WHERE migration_id LIKE '00%';
```

#### 4.2 Schema Cleanup
```sql
-- File: data/database/migration_scripts/008_cleanup_old_schema.sql
-- Remove old schema after successful migration

-- Rename old tables (don't drop immediately - keep for safety)
ALTER TABLE content_v1 RENAME TO content_v1_backup;
ALTER TABLE downloads_v1 RENAME TO downloads_v1_backup;

-- Create cleanup schedule
INSERT INTO application_settings (setting_key, setting_value, description)
VALUES ('old_schema_cleanup_date', date('now', '+30 days'), 'Date when old schema backup tables can be safely dropped');
```

## Migration Execution Framework

### 1. **Migration Runner Script**

```python
# File: scripts/database/migration_runner.py
import sqlite3
import logging
import time
from pathlib import Path

class MigrationRunner:
    """
    Robust migration execution framework with rollback capability
    """
    
    def __init__(self, db_path, migration_scripts_dir):
        self.db_path = db_path
        self.migration_scripts_dir = Path(migration_scripts_dir)
        self.logger = logging.getLogger(__name__)
    
    def run_migrations(self, target_version=None):
        """Run all pending migrations up to target version"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Get current schema version
            current_version = self._get_current_version(conn)
            
            # Get pending migrations
            migrations = self._get_pending_migrations(current_version, target_version)
            
            for migration in migrations:
                try:
                    self._run_single_migration(conn, migration)
                except Exception as e:
                    self.logger.error(f"Migration {migration['id']} failed: {e}")
                    self._handle_migration_failure(conn, migration, e)
                    raise
    
    def _run_single_migration(self, conn, migration):
        """Execute a single migration with full logging"""
        
        migration_id = migration['id']
        self.logger.info(f"Starting migration {migration_id}")
        
        start_time = time.time()
        
        try:
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Execute migration SQL
            with open(migration['file_path'], 'r') as f:
                migration_sql = f.read()
            
            conn.executescript(migration_sql)
            
            # Record migration completion
            conn.execute("""
                INSERT INTO schema_migrations (version, description, executed_at, execution_time_ms)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?)
            """, (migration_id, migration['description'], int((time.time() - start_time) * 1000)))
            
            # Commit transaction
            conn.execute("COMMIT")
            
            self.logger.info(f"Migration {migration_id} completed successfully")
            
        except Exception as e:
            # Rollback on failure
            conn.execute("ROLLBACK")
            raise
    
    def validate_migration(self, migration_id):
        """Run validation checks for a specific migration"""
        
        validation_file = self.migration_scripts_dir / f"{migration_id}_validate.sql"
        if validation_file.exists():
            with sqlite3.connect(self.db_path) as conn:
                with open(validation_file, 'r') as f:
                    validation_sql = f.read()
                
                results = conn.execute(validation_sql).fetchall()
                
                # Check if all validations passed
                failed_checks = [r for r in results if r[3] != 'PASS']
                
                if failed_checks:
                    raise ValueError(f"Migration {migration_id} validation failed: {failed_checks}")
                
                return True
```

### 2. **Rollback Procedures**

```python
# File: scripts/database/rollback_runner.py
class RollbackRunner:
    """
    Safe rollback procedures for failed migrations
    """
    
    def rollback_to_version(self, target_version):
        """Rollback database to specific version"""
        
        with sqlite3.connect(self.db_path) as conn:
            current_version = self._get_current_version(conn)
            
            # Get migrations to rollback (in reverse order)
            rollback_migrations = self._get_rollback_migrations(current_version, target_version)
            
            for migration in reversed(rollback_migrations):
                self._run_rollback(conn, migration)
    
    def _run_rollback(self, conn, migration):
        """Execute rollback for a single migration"""
        
        rollback_file = self.migration_scripts_dir / f"{migration['id']}_rollback.sql"
        
        if not rollback_file.exists():
            # Create rollback from backup if no explicit rollback script
            self._create_rollback_from_backup(conn, migration)
        else:
            # Execute explicit rollback script
            with open(rollback_file, 'r') as f:
                rollback_sql = f.read()
            
            conn.executescript(rollback_sql)
        
        # Remove migration record
        conn.execute("DELETE FROM schema_migrations WHERE version = ?", (migration['id'],))
```

## Version Control and Governance

### 1. **Schema Version Management**

```sql
-- Enhanced schema_migrations table
CREATE TABLE schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    migration_file VARCHAR(255),
    rollback_file VARCHAR(255),
    
    -- Execution tracking
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- Dependency tracking
    depends_on VARCHAR(50),
    
    -- Rollback capability
    can_rollback BOOLEAN DEFAULT FALSE,
    rollback_notes TEXT,
    
    -- Approval workflow
    approved_by VARCHAR(100),
    approved_at TIMESTAMP,
    
    FOREIGN KEY (depends_on) REFERENCES schema_migrations(version)
);
```

### 2. **Migration Naming Convention**

```
{sequence}_{version}_{description}.sql

Examples:
001_v2.0.0_create_base_schema.sql
002_v2.0.0_migrate_content_data.sql
003_v2.0.0_migrate_metadata.sql
004_v2.0.1_add_content_indexes.sql
005_v2.0.1_add_download_tracking.sql
```

### 3. **Environment-Specific Migration Strategy**

#### Development Environment
- Run all migrations automatically
- Allow experimental migrations
- Enable detailed logging
- Keep all rollback files

#### Staging Environment
- Require approval for migrations
- Run validation tests after migration
- Performance benchmark all changes
- Simulate production load

#### Production Environment
- Require multiple approvals
- Backup database before migration
- Run migrations during maintenance windows
- Monitor performance impact
- Have immediate rollback plan ready

## Zero-Downtime Migration Strategies

### 1. **Online Schema Migration**

```python
# File: scripts/database/online_migration.py
class OnlineMigrationService:
    """
    Zero-downtime migration strategies for production
    """
    
    def add_column_online(self, table_name, column_definition):
        """Add column without downtime"""
        
        # SQLite doesn't support ADD COLUMN with NOT NULL
        # Use multi-step process
        
        # Step 1: Add column as nullable
        self._execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition.replace('NOT NULL', '')}")
        
        # Step 2: Populate column with default values
        self._populate_new_column(table_name, column_definition)
        
        # Step 3: Add NOT NULL constraint if needed (requires table recreation)
        if 'NOT NULL' in column_definition:
            self._add_not_null_constraint_online(table_name, column_definition)
    
    def create_index_online(self, index_definition):
        """Create index without blocking writes"""
        
        # SQLite index creation is atomic and doesn't block reads
        # But it does block writes, so we do it in small batches
        
        self._execute(index_definition)
        
        # Verify index was created successfully
        self._verify_index_creation(index_definition)
```

### 2. **Blue-Green Migration Strategy**

```python
# File: scripts/database/blue_green_migration.py
class BlueGreenMigration:
    """
    Blue-green deployment strategy for major schema changes
    """
    
    def __init__(self, blue_db_path, green_db_path):
        self.blue_db = blue_db_path  # Current production
        self.green_db = green_db_path  # New schema
    
    def prepare_green_environment(self):
        """Set up green environment with new schema"""
        
        # Create new database with v2.0 schema
        self._create_green_database()
        
        # Migrate data to green database
        self._migrate_data_to_green()
        
        # Validate green database
        self._validate_green_database()
    
    def cutover_to_green(self):
        """Switch traffic from blue to green"""
        
        # Stop writes to blue database
        self._stop_writes()
        
        # Final data sync
        self._final_sync_to_green()
        
        # Switch application to green database
        self._switch_database_connection()
        
        # Resume writes to green database
        self._resume_writes()
        
        # Monitor for issues
        self._monitor_green_performance()
```

## Post-Migration Procedures

### 1. **Performance Monitoring**

```sql
-- Monitor query performance after migration
CREATE VIEW post_migration_performance AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_queries,
    AVG(execution_time_ms) as avg_response_time,
    MAX(execution_time_ms) as max_response_time,
    COUNT(CASE WHEN execution_time_ms > 100 THEN 1 END) as slow_queries,
    SUM(CASE WHEN execution_time_ms > 500 THEN 1 ELSE 0 END) as very_slow_queries
FROM query_performance_log
WHERE created_at >= (SELECT MAX(executed_at) FROM schema_migrations)
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### 2. **Data Integrity Checks**

```sql
-- Ongoing data integrity monitoring
CREATE VIEW data_integrity_monitor AS
SELECT 
    'orphaned_metadata' as check_name,
    COUNT(*) as issue_count,
    'content_metadata records without valid content_id' as description
FROM content_metadata cm
LEFT JOIN content c ON cm.content_id = c.id
WHERE c.id IS NULL

UNION ALL

SELECT 
    'missing_platform_refs' as check_name,
    COUNT(*) as issue_count,
    'content records without valid platform_id' as description
FROM content c
LEFT JOIN platforms p ON c.platform_id = p.id
WHERE p.id IS NULL

UNION ALL

SELECT 
    'duplicate_content' as check_name,
    COUNT(*) - COUNT(DISTINCT original_url, platform_id) as issue_count,
    'duplicate content records for same URL and platform' as description
FROM content;
```

This comprehensive migration path definition ensures a safe, reliable, and reversible transition from the current schema to the optimized v2.0 structure while maintaining data integrity and system availability throughout the process. 