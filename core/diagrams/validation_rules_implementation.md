# Validation Rules Implementation for Social Download Manager v2.0

## Overview

This document defines comprehensive validation rules, constraints, and data integrity measures for the Social Download Manager v2.0 database schema. It ensures data consistency, prevents corruption, and maintains referential integrity across all tables.

## Validation Strategy

### 1. **Multi-Layer Validation Approach**

#### Database Level (Primary Defense)
- **Check constraints** for data format and range validation
- **Foreign key constraints** for referential integrity
- **Unique constraints** for preventing duplicates
- **Triggers** for complex business logic validation

#### Application Level (Secondary Defense)
- **Input validation** before database insertion
- **Business rule enforcement** in service layer
- **Data transformation** and sanitization

#### Runtime Level (Monitoring)
- **Data integrity monitoring** queries
- **Validation reports** and alerts
- **Automated data quality checks**

## Database Constraint Implementation

### 1. **Core Table Constraints**

#### Platforms Table Validation
```sql
-- Enhanced platform validation constraints
ALTER TABLE platforms ADD CONSTRAINT chk_platforms_name_format 
    CHECK (name = LOWER(name) AND name NOT LIKE '% %' AND LENGTH(name) >= 2);

ALTER TABLE platforms ADD CONSTRAINT chk_platforms_display_name_not_empty 
    CHECK (LENGTH(TRIM(display_name)) > 0);

ALTER TABLE platforms ADD CONSTRAINT chk_platforms_base_url_format 
    CHECK (base_url IS NULL OR base_url LIKE 'http%://%');

ALTER TABLE platforms ADD CONSTRAINT chk_platforms_supported_types_json 
    CHECK (json_valid(supported_content_types));

ALTER TABLE platforms ADD CONSTRAINT chk_platforms_metadata_json 
    CHECK (json_valid(metadata));

-- Unique constraint for normalized names
CREATE UNIQUE INDEX uq_platforms_name_normalized 
    ON platforms(LOWER(TRIM(name)));
```

#### Content Table Validation
```sql
-- Core content validation constraints
ALTER TABLE content ADD CONSTRAINT chk_content_url_not_empty 
    CHECK (LENGTH(TRIM(original_url)) > 0);

ALTER TABLE content ADD CONSTRAINT chk_content_url_format 
    CHECK (original_url LIKE 'http%://%' OR original_url LIKE 'ftp%://%');

ALTER TABLE content ADD CONSTRAINT chk_content_canonical_url_format 
    CHECK (canonical_url IS NULL OR canonical_url LIKE 'http%://%');

ALTER TABLE content ADD CONSTRAINT chk_content_title_length 
    CHECK (title IS NULL OR LENGTH(TRIM(title)) > 0);

ALTER TABLE content ADD CONSTRAINT chk_content_type_valid 
    CHECK (content_type IN ('video', 'audio', 'image', 'post', 'story', 'reel', 'livestream', 'playlist'));

ALTER TABLE content ADD CONSTRAINT chk_content_status_valid 
    CHECK (status IN ('pending', 'downloading', 'processing', 'completed', 'failed', 'cancelled', 'paused'));

-- Metrics validation (non-negative values)
ALTER TABLE content ADD CONSTRAINT chk_content_positive_metrics 
    CHECK (
        view_count >= 0 AND 
        like_count >= 0 AND 
        comment_count >= 0 AND 
        share_count >= 0 AND
        duration_seconds IS NULL OR duration_seconds >= 0 AND
        file_size_bytes IS NULL OR file_size_bytes >= 0
    );

-- Timeline validation
ALTER TABLE content ADD CONSTRAINT chk_content_timeline_logic 
    CHECK (
        published_at IS NULL OR published_at <= updated_at
    );

-- Platform content ID uniqueness per platform
CREATE UNIQUE INDEX uq_content_platform_content_id 
    ON content(platform_id, platform_content_id) 
    WHERE platform_content_id IS NOT NULL;

-- URL uniqueness per platform (prevent duplicates)
CREATE UNIQUE INDEX uq_content_platform_url 
    ON content(platform_id, original_url);
```

#### Content Metadata Validation
```sql
-- Metadata validation constraints
ALTER TABLE content_metadata ADD CONSTRAINT chk_metadata_key_not_empty 
    CHECK (LENGTH(TRIM(metadata_key)) > 0);

ALTER TABLE content_metadata ADD CONSTRAINT chk_metadata_type_not_empty 
    CHECK (LENGTH(TRIM(metadata_type)) > 0);

ALTER TABLE content_metadata ADD CONSTRAINT chk_metadata_data_type_valid 
    CHECK (data_type IN ('string', 'integer', 'float', 'boolean', 'json', 'timestamp'));

-- Prevent duplicate metadata entries
CREATE UNIQUE INDEX uq_content_metadata_unique 
    ON content_metadata(content_id, metadata_type, metadata_key, COALESCE(parent_key, ''));

-- Hierarchical metadata validation
ALTER TABLE content_metadata ADD CONSTRAINT chk_metadata_hierarchy_self_reference 
    CHECK (parent_key != metadata_key);
```

### 2. **Download System Validation**

#### Downloads Table Constraints
```sql
-- Download validation constraints
ALTER TABLE downloads ADD CONSTRAINT chk_downloads_status_valid 
    CHECK (status IN ('queued', 'starting', 'downloading', 'processing', 'completed', 'failed', 'cancelled', 'paused', 'retrying'));

ALTER TABLE downloads ADD CONSTRAINT chk_downloads_progress_range 
    CHECK (progress_percentage >= 0.00 AND progress_percentage <= 100.00);

ALTER TABLE downloads ADD CONSTRAINT chk_downloads_retry_counts 
    CHECK (retry_count >= 0 AND max_retries >= 0 AND retry_count <= max_retries + 5);

ALTER TABLE downloads ADD CONSTRAINT chk_downloads_speed_positive 
    CHECK (
        current_speed_bps IS NULL OR current_speed_bps >= 0 AND
        average_speed_bps IS NULL OR average_speed_bps >= 0
    );

ALTER TABLE downloads ADD CONSTRAINT chk_downloads_file_size_positive 
    CHECK (actual_file_size IS NULL OR actual_file_size > 0);

ALTER TABLE downloads ADD CONSTRAINT chk_downloads_output_directory_not_empty 
    CHECK (LENGTH(TRIM(output_directory)) > 0);

ALTER TABLE downloads ADD CONSTRAINT chk_downloads_options_json 
    CHECK (json_valid(download_options));

-- Timeline validation for downloads
ALTER TABLE downloads ADD CONSTRAINT chk_downloads_timeline_logic 
    CHECK (
        (started_at IS NULL OR started_at >= queued_at) AND
        (completed_at IS NULL OR completed_at >= queued_at) AND
        (started_at IS NULL OR completed_at IS NULL OR completed_at >= started_at)
    );

-- Status-dependent validation
ALTER TABLE downloads ADD CONSTRAINT chk_downloads_completed_requirements 
    CHECK (
        (status != 'completed' OR (completed_at IS NOT NULL AND final_file_path IS NOT NULL)) AND
        (status != 'failed' OR error_count > 0)
    );
```

#### Download Sessions Validation
```sql
-- Session validation constraints
ALTER TABLE download_sessions ADD CONSTRAINT chk_sessions_status_valid 
    CHECK (session_status IN ('active', 'completed', 'failed', 'cancelled', 'paused'));

ALTER TABLE download_sessions ADD CONSTRAINT chk_sessions_type_valid 
    CHECK (session_type IN ('standard', 'retry', 'resume', 'parallel'));

ALTER TABLE download_sessions ADD CONSTRAINT chk_sessions_uuid_format 
    CHECK (LENGTH(session_uuid) = 36 AND session_uuid LIKE '%-%-%-%-%');

ALTER TABLE download_sessions ADD CONSTRAINT chk_sessions_bytes_positive 
    CHECK (
        bytes_downloaded >= 0 AND
        (total_bytes IS NULL OR total_bytes >= bytes_downloaded) AND
        chunks_completed >= 0 AND
        (total_chunks IS NULL OR total_chunks >= chunks_completed)
    );

ALTER TABLE download_sessions ADD CONSTRAINT chk_sessions_speed_positive 
    CHECK (
        peak_speed_bps IS NULL OR peak_speed_bps >= 0 AND
        average_speed_bps IS NULL OR average_speed_bps >= 0 AND
        connection_count IS NULL OR connection_count >= 1
    );

ALTER TABLE download_sessions ADD CONSTRAINT chk_sessions_headers_json 
    CHECK (json_valid(headers));

-- Session timeline validation
ALTER TABLE download_sessions ADD CONSTRAINT chk_sessions_timeline_logic 
    CHECK (
        session_ended_at IS NULL OR session_ended_at >= session_started_at
    );
```

### 3. **Quality and Tag System Validation**

#### Quality Options Constraints
```sql
-- Quality options validation
ALTER TABLE quality_options ADD CONSTRAINT chk_quality_label_not_empty 
    CHECK (LENGTH(TRIM(quality_label)) > 0);

ALTER TABLE quality_options ADD CONSTRAINT chk_quality_format_not_empty 
    CHECK (LENGTH(TRIM(format)) > 0);

ALTER TABLE quality_options ADD CONSTRAINT chk_quality_dimensions_positive 
    CHECK (
        (resolution_width IS NULL OR resolution_width > 0) AND
        (resolution_height IS NULL OR resolution_height > 0) AND
        (bitrate_kbps IS NULL OR bitrate_kbps > 0) AND
        (audio_bitrate_kbps IS NULL OR audio_bitrate_kbps > 0) AND
        (fps IS NULL OR fps > 0) AND
        (estimated_file_size IS NULL OR estimated_file_size > 0)
    );

-- Logical resolution validation
ALTER TABLE quality_options ADD CONSTRAINT chk_quality_resolution_logic 
    CHECK (
        (resolution_width IS NULL) = (resolution_height IS NULL)
    );

-- URL validation for quality options
ALTER TABLE quality_options ADD CONSTRAINT chk_quality_download_url_format 
    CHECK (download_url IS NULL OR download_url LIKE 'http%://%');

-- Prevent duplicate quality options per content
CREATE UNIQUE INDEX uq_quality_options_content_quality_format 
    ON quality_options(content_id, quality_label, format);
```

#### Tags System Constraints
```sql
-- Tags validation constraints
ALTER TABLE tags ADD CONSTRAINT chk_tags_name_not_empty 
    CHECK (LENGTH(TRIM(name)) > 0);

ALTER TABLE tags ADD CONSTRAINT chk_tags_slug_format 
    CHECK (slug = LOWER(slug) AND slug NOT LIKE '% %' AND LENGTH(slug) > 0);

ALTER TABLE tags ADD CONSTRAINT chk_tags_type_valid 
    CHECK (tag_type IN ('user', 'auto', 'hashtag', 'category', 'system'));

ALTER TABLE tags ADD CONSTRAINT chk_tags_usage_count_positive 
    CHECK (usage_count >= 0);

-- Content tags junction table validation
ALTER TABLE content_tags ADD CONSTRAINT chk_content_tags_assigned_by_valid 
    CHECK (assigned_by IN ('user', 'auto', 'import', 'system'));

ALTER TABLE content_tags ADD CONSTRAINT chk_content_tags_confidence_range 
    CHECK (confidence_score IS NULL OR (confidence_score >= 0.00 AND confidence_score <= 1.00));
```

## Advanced Validation Triggers

### 1. **Data Type Validation Triggers**

```sql
-- Validate metadata values based on declared data type
CREATE TRIGGER validate_metadata_integer_values
    BEFORE INSERT ON content_metadata
    FOR EACH ROW
    WHEN NEW.data_type = 'integer' 
BEGIN
    SELECT CASE 
        WHEN NEW.metadata_value NOT GLOB '[+-]*[0-9]*' 
        THEN RAISE(ABORT, 'Invalid integer value: ' || NEW.metadata_value || ' for key: ' || NEW.metadata_key)
    END;
END;

CREATE TRIGGER validate_metadata_float_values
    BEFORE INSERT ON content_metadata
    FOR EACH ROW
    WHEN NEW.data_type = 'float'
BEGIN
    SELECT CASE 
        WHEN NEW.metadata_value NOT GLOB '[+-]*[0-9]*.*[0-9]*' AND NEW.metadata_value NOT GLOB '[+-]*[0-9]*'
        THEN RAISE(ABORT, 'Invalid float value: ' || NEW.metadata_value || ' for key: ' || NEW.metadata_key)
    END;
END;

CREATE TRIGGER validate_metadata_boolean_values
    BEFORE INSERT ON content_metadata
    FOR EACH ROW
    WHEN NEW.data_type = 'boolean'
BEGIN
    SELECT CASE 
        WHEN NEW.metadata_value NOT IN ('true', 'false', '1', '0')
        THEN RAISE(ABORT, 'Invalid boolean value: ' || NEW.metadata_value || ' for key: ' || NEW.metadata_key)
    END;
END;

CREATE TRIGGER validate_metadata_json_values
    BEFORE INSERT ON content_metadata
    FOR EACH ROW
    WHEN NEW.data_type = 'json'
BEGIN
    SELECT CASE 
        WHEN NOT json_valid(NEW.metadata_value)
        THEN RAISE(ABORT, 'Invalid JSON value for key: ' || NEW.metadata_key)
    END;
END;

CREATE TRIGGER validate_metadata_timestamp_values
    BEFORE INSERT ON content_metadata
    FOR EACH ROW
    WHEN NEW.data_type = 'timestamp'
BEGIN
    SELECT CASE 
        WHEN datetime(NEW.metadata_value) IS NULL
        THEN RAISE(ABORT, 'Invalid timestamp value: ' || NEW.metadata_value || ' for key: ' || NEW.metadata_key)
    END;
END;
```

### 2. **Business Logic Validation Triggers**

```sql
-- Validate download status transitions
CREATE TRIGGER validate_download_status_transitions
    BEFORE UPDATE ON downloads
    FOR EACH ROW
    WHEN NEW.status != OLD.status
BEGIN
    -- Define valid status transitions
    SELECT CASE 
        -- From queued
        WHEN OLD.status = 'queued' AND NEW.status NOT IN ('starting', 'cancelled', 'failed')
        THEN RAISE(ABORT, 'Invalid status transition from queued to ' || NEW.status)
        
        -- From starting
        WHEN OLD.status = 'starting' AND NEW.status NOT IN ('downloading', 'failed', 'cancelled')
        THEN RAISE(ABORT, 'Invalid status transition from starting to ' || NEW.status)
        
        -- From downloading
        WHEN OLD.status = 'downloading' AND NEW.status NOT IN ('processing', 'paused', 'failed', 'retrying', 'cancelled')
        THEN RAISE(ABORT, 'Invalid status transition from downloading to ' || NEW.status)
        
        -- From processing
        WHEN OLD.status = 'processing' AND NEW.status NOT IN ('completed', 'failed', 'cancelled')
        THEN RAISE(ABORT, 'Invalid status transition from processing to ' || NEW.status)
        
        -- From completed (should not change)
        WHEN OLD.status = 'completed' AND NEW.status != 'completed'
        THEN RAISE(ABORT, 'Cannot change status from completed to ' || NEW.status)
        
        -- From retrying
        WHEN OLD.status = 'retrying' AND NEW.status NOT IN ('downloading', 'failed', 'cancelled')
        THEN RAISE(ABORT, 'Invalid status transition from retrying to ' || NEW.status)
    END;
END;

-- Validate content metadata consistency
CREATE TRIGGER validate_content_metadata_consistency
    BEFORE INSERT ON content_metadata
    FOR EACH ROW
BEGIN
    -- Ensure content exists and is not deleted
    SELECT CASE 
        WHEN NOT EXISTS (
            SELECT 1 FROM content 
            WHERE id = NEW.content_id AND is_deleted = FALSE
        )
        THEN RAISE(ABORT, 'Cannot add metadata to non-existent or deleted content: ' || NEW.content_id)
    END;
    
    -- Validate platform-specific metadata keys
    SELECT CASE 
        WHEN NEW.metadata_type = 'platform_specific' AND NEW.metadata_key LIKE 'youtube_%' AND NOT EXISTS (
            SELECT 1 FROM content c 
            JOIN platforms p ON c.platform_id = p.id 
            WHERE c.id = NEW.content_id AND p.name = 'youtube'
        )
        THEN RAISE(ABORT, 'YouTube metadata key "' || NEW.metadata_key || '" not valid for non-YouTube content')
        
        WHEN NEW.metadata_type = 'platform_specific' AND NEW.metadata_key LIKE 'tiktok_%' AND NOT EXISTS (
            SELECT 1 FROM content c 
            JOIN platforms p ON c.platform_id = p.id 
            WHERE c.id = NEW.content_id AND p.name = 'tiktok'
        )
        THEN RAISE(ABORT, 'TikTok metadata key "' || NEW.metadata_key || '" not valid for non-TikTok content')
    END;
END;

-- Validate quality options consistency
CREATE TRIGGER validate_quality_options_consistency
    BEFORE INSERT ON quality_options
    FOR EACH ROW
BEGIN
    -- Ensure content exists
    SELECT CASE 
        WHEN NOT EXISTS (SELECT 1 FROM content WHERE id = NEW.content_id)
        THEN RAISE(ABORT, 'Cannot add quality option to non-existent content: ' || NEW.content_id)
    END;
    
    -- Validate resolution consistency
    SELECT CASE 
        WHEN NEW.quality_label LIKE '%p' AND NEW.resolution_height != CAST(REPLACE(NEW.quality_label, 'p', '') AS INTEGER)
        THEN RAISE(ABORT, 'Quality label "' || NEW.quality_label || '" does not match resolution height ' || NEW.resolution_height)
    END;
END;
```

### 3. **Data Integrity Maintenance Triggers**

```sql
-- Maintain tag usage counts
CREATE TRIGGER maintain_tag_usage_count_insert
    AFTER INSERT ON content_tags
    FOR EACH ROW
BEGIN
    UPDATE tags 
    SET usage_count = usage_count + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.tag_id;
END;

CREATE TRIGGER maintain_tag_usage_count_delete
    AFTER DELETE ON content_tags
    FOR EACH ROW
BEGIN
    UPDATE tags 
    SET usage_count = CASE 
        WHEN usage_count > 0 THEN usage_count - 1 
        ELSE 0 
    END,
    updated_at = CURRENT_TIMESTAMP
    WHERE id = OLD.tag_id;
END;

-- Maintain content download count
CREATE TRIGGER maintain_content_download_count
    AFTER UPDATE ON downloads
    FOR EACH ROW
    WHEN NEW.status = 'completed' AND OLD.status != 'completed'
BEGIN
    UPDATE content 
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.content_id;
END;

-- Prevent deletion of referenced platforms
CREATE TRIGGER prevent_platform_deletion_with_content
    BEFORE DELETE ON platforms
    FOR EACH ROW
BEGIN
    SELECT CASE 
        WHEN EXISTS (SELECT 1 FROM content WHERE platform_id = OLD.id)
        THEN RAISE(ABORT, 'Cannot delete platform "' || OLD.name || '" because it has associated content')
    END;
END;
```

## Application-Level Validation

### 1. **Input Validation Service**

```python
# File: core/services/validation/input_validator.py
import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

class InputValidator:
    """
    Application-level input validation service
    """
    
    # URL validation patterns
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    # Platform-specific URL patterns
    PLATFORM_URL_PATTERNS = {
        'youtube': re.compile(r'https?://(www\.)?(youtube\.com|youtu\.be)/', re.IGNORECASE),
        'tiktok': re.compile(r'https?://(www\.)?tiktok\.com/', re.IGNORECASE),
        'instagram': re.compile(r'https?://(www\.)?instagram\.com/', re.IGNORECASE),
    }
    
    def validate_content_data(self, content_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate content data before database insertion"""
        errors = {}
        
        # Validate required fields
        required_fields = ['original_url', 'platform_id']
        for field in required_fields:
            if not content_data.get(field):
                errors.setdefault(field, []).append(f"{field} is required")
        
        # Validate URL format
        if content_data.get('original_url'):
            if not self._is_valid_url(content_data['original_url']):
                errors.setdefault('original_url', []).append("Invalid URL format")
        
        # Validate platform consistency
        if content_data.get('platform_id') and content_data.get('original_url'):
            platform_name = self._get_platform_name(content_data['platform_id'])
            if not self._is_url_valid_for_platform(content_data['original_url'], platform_name):
                errors.setdefault('original_url', []).append(f"URL not valid for platform {platform_name}")
        
        # Validate content type
        if content_data.get('content_type'):
            valid_types = ['video', 'audio', 'image', 'post', 'story', 'reel', 'livestream', 'playlist']
            if content_data['content_type'] not in valid_types:
                errors.setdefault('content_type', []).append(f"Content type must be one of: {', '.join(valid_types)}")
        
        # Validate metrics (non-negative)
        metric_fields = ['view_count', 'like_count', 'comment_count', 'share_count', 'duration_seconds']
        for field in metric_fields:
            if content_data.get(field) is not None:
                try:
                    value = int(content_data[field])
                    if value < 0:
                        errors.setdefault(field, []).append(f"{field} must be non-negative")
                except (ValueError, TypeError):
                    errors.setdefault(field, []).append(f"{field} must be a valid integer")
        
        return errors
    
    def validate_metadata(self, metadata_list: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Validate metadata entries"""
        errors = {}
        
        for i, metadata in enumerate(metadata_list):
            metadata_errors = []
            
            # Validate required fields
            if not metadata.get('metadata_key'):
                metadata_errors.append("metadata_key is required")
            
            if not metadata.get('metadata_type'):
                metadata_errors.append("metadata_type is required")
            
            # Validate data type consistency
            if metadata.get('data_type') and metadata.get('metadata_value'):
                if not self._validate_data_type_value(metadata['data_type'], metadata['metadata_value']):
                    metadata_errors.append(f"Value '{metadata['metadata_value']}' is not valid for data type '{metadata['data_type']}'")
            
            if metadata_errors:
                errors[f'metadata[{i}]'] = metadata_errors
        
        return errors
    
    def validate_download_data(self, download_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate download data"""
        errors = {}
        
        # Validate required fields
        required_fields = ['content_id', 'output_directory']
        for field in required_fields:
            if not download_data.get(field):
                errors.setdefault(field, []).append(f"{field} is required")
        
        # Validate progress percentage
        if download_data.get('progress_percentage') is not None:
            try:
                progress = float(download_data['progress_percentage'])
                if not 0 <= progress <= 100:
                    errors.setdefault('progress_percentage', []).append("Progress must be between 0 and 100")
            except (ValueError, TypeError):
                errors.setdefault('progress_percentage', []).append("Progress must be a valid number")
        
        # Validate retry counts
        retry_count = download_data.get('retry_count', 0)
        max_retries = download_data.get('max_retries', 3)
        if retry_count > max_retries:
            errors.setdefault('retry_count', []).append("Retry count cannot exceed max retries")
        
        return errors
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL has valid format"""
        if not url or not isinstance(url, str):
            return False
        return bool(self.URL_PATTERN.match(url))
    
    def _is_url_valid_for_platform(self, url: str, platform_name: str) -> bool:
        """Check if URL matches expected platform"""
        if platform_name.lower() in self.PLATFORM_URL_PATTERNS:
            pattern = self.PLATFORM_URL_PATTERNS[platform_name.lower()]
            return bool(pattern.match(url))
        return True  # Allow unknown platforms
    
    def _validate_data_type_value(self, data_type: str, value: str) -> bool:
        """Validate value against declared data type"""
        try:
            if data_type == 'integer':
                int(value)
                return True
            elif data_type == 'float':
                float(value)
                return True
            elif data_type == 'boolean':
                return value.lower() in ('true', 'false', '1', '0')
            elif data_type == 'json':
                json.loads(value)
                return True
            elif data_type == 'timestamp':
                # Try parsing common timestamp formats
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ'):
                    try:
                        datetime.strptime(value, fmt)
                        return True
                    except ValueError:
                        continue
                return False
            else:  # string
                return True
        except (ValueError, TypeError, json.JSONDecodeError):
            return False
```

### 2. **Business Rule Validator**

```python
# File: core/services/validation/business_rule_validator.py
class BusinessRuleValidator:
    """
    Business logic validation service
    """
    
    def __init__(self, db_service):
        self.db = db_service
    
    def validate_content_uniqueness(self, content_data: Dict[str, Any]) -> List[str]:
        """Validate content is not already in database"""
        errors = []
        
        # Check for duplicate URLs on same platform
        existing = self.db.execute("""
            SELECT id FROM content 
            WHERE platform_id = ? AND original_url = ? AND is_deleted = FALSE
        """, (content_data['platform_id'], content_data['original_url'])).fetchone()
        
        if existing:
            errors.append(f"Content already exists with ID {existing[0]}")
        
        # Check for duplicate platform content IDs
        if content_data.get('platform_content_id'):
            existing = self.db.execute("""
                SELECT id FROM content 
                WHERE platform_id = ? AND platform_content_id = ? AND is_deleted = FALSE
            """, (content_data['platform_id'], content_data['platform_content_id'])).fetchone()
            
            if existing:
                errors.append(f"Content with platform ID '{content_data['platform_content_id']}' already exists")
        
        return errors
    
    def validate_download_constraints(self, download_data: Dict[str, Any]) -> List[str]:
        """Validate download business constraints"""
        errors = []
        
        # Check if content exists and is not deleted
        content = self.db.execute("""
            SELECT id, status FROM content 
            WHERE id = ? AND is_deleted = FALSE
        """, (download_data['content_id'],)).fetchone()
        
        if not content:
            errors.append("Cannot create download for non-existent or deleted content")
        
        # Check for duplicate active downloads
        active_download = self.db.execute("""
            SELECT id FROM downloads 
            WHERE content_id = ? AND status IN ('queued', 'starting', 'downloading', 'processing', 'retrying')
        """, (download_data['content_id'],)).fetchone()
        
        if active_download:
            errors.append(f"Active download already exists for this content (ID: {active_download[0]})")
        
        return errors
    
    def validate_metadata_business_rules(self, content_id: int, metadata_list: List[Dict]) -> List[str]:
        """Validate metadata business constraints"""
        errors = []
        
        # Get content platform for validation
        content = self.db.execute("""
            SELECT p.name FROM content c 
            JOIN platforms p ON c.platform_id = p.id 
            WHERE c.id = ?
        """, (content_id,)).fetchone()
        
        if not content:
            errors.append("Cannot add metadata to non-existent content")
            return errors
        
        platform_name = content[0]
        
        # Validate platform-specific metadata keys
        for metadata in metadata_list:
            if metadata.get('metadata_type') == 'platform_specific':
                key = metadata.get('metadata_key', '')
                
                # YouTube-specific validation
                if key.startswith('youtube_') and platform_name != 'youtube':
                    errors.append(f"YouTube metadata key '{key}' not valid for {platform_name} content")
                
                # TikTok-specific validation
                elif key.startswith('tiktok_') and platform_name != 'tiktok':
                    errors.append(f"TikTok metadata key '{key}' not valid for {platform_name} content")
                
                # Instagram-specific validation
                elif key.startswith('instagram_') and platform_name != 'instagram':
                    errors.append(f"Instagram metadata key '{key}' not valid for {platform_name} content")
        
        return errors
```

## Data Integrity Monitoring

### 1. **Integrity Check Queries**

```sql
-- File: scripts/database/data_integrity_checks.sql
-- Comprehensive data integrity monitoring queries

-- Check for orphaned records
CREATE VIEW data_integrity_issues AS
-- Orphaned content metadata
SELECT 
    'orphaned_metadata' as issue_type,
    COUNT(*) as issue_count,
    'content_metadata records without valid content_id' as description,
    GROUP_CONCAT(cm.id) as affected_ids
FROM content_metadata cm
LEFT JOIN content c ON cm.content_id = c.id
WHERE c.id IS NULL
GROUP BY issue_type

UNION ALL

-- Orphaned downloads
SELECT 
    'orphaned_downloads' as issue_type,
    COUNT(*) as issue_count,
    'downloads records without valid content_id' as description,
    GROUP_CONCAT(d.id) as affected_ids
FROM downloads d
LEFT JOIN content c ON d.content_id = c.id
WHERE c.id IS NULL
GROUP BY issue_type

UNION ALL

-- Orphaned download sessions
SELECT 
    'orphaned_download_sessions' as issue_type,
    COUNT(*) as issue_count,
    'download_sessions records without valid download_id' as description,
    GROUP_CONCAT(ds.id) as affected_ids
FROM download_sessions ds
LEFT JOIN downloads d ON ds.download_id = d.id
WHERE d.id IS NULL
GROUP BY issue_type

UNION ALL

-- Content with invalid platform references
SELECT 
    'invalid_platform_refs' as issue_type,
    COUNT(*) as issue_count,
    'content records with invalid platform_id' as description,
    GROUP_CONCAT(c.id) as affected_ids
FROM content c
LEFT JOIN platforms p ON c.platform_id = p.id
WHERE p.id IS NULL
GROUP BY issue_type

UNION ALL

-- Duplicate content entries
SELECT 
    'duplicate_content' as issue_type,
    COUNT(*) - COUNT(DISTINCT original_url, platform_id) as issue_count,
    'duplicate content records for same URL and platform' as description,
    '' as affected_ids
FROM content
WHERE is_deleted = FALSE
GROUP BY issue_type
HAVING issue_count > 0

UNION ALL

-- Invalid download status combinations
SELECT 
    'invalid_download_status' as issue_type,
    COUNT(*) as issue_count,
    'downloads with invalid status/completion combinations' as description,
    GROUP_CONCAT(d.id) as affected_ids
FROM downloads d
WHERE (
    (d.status = 'completed' AND (d.completed_at IS NULL OR d.final_file_path IS NULL)) OR
    (d.status = 'failed' AND d.error_count = 0) OR
    (d.progress_percentage = 100 AND d.status NOT IN ('completed', 'processing'))
)
GROUP BY issue_type

UNION ALL

-- Inconsistent tag usage counts
SELECT 
    'inconsistent_tag_usage' as issue_type,
    COUNT(*) as issue_count,
    'tags with incorrect usage_count values' as description,
    GROUP_CONCAT(t.id) as affected_ids
FROM tags t
LEFT JOIN (
    SELECT tag_id, COUNT(*) as actual_count
    FROM content_tags
    GROUP BY tag_id
) ct ON t.id = ct.tag_id
WHERE COALESCE(ct.actual_count, 0) != t.usage_count
GROUP BY issue_type;
```

### 2. **Automated Integrity Repair**

```sql
-- File: scripts/database/integrity_repair.sql
-- Automated repair procedures for common integrity issues

-- Repair tag usage counts
UPDATE tags
SET usage_count = COALESCE((
    SELECT COUNT(*) 
    FROM content_tags ct 
    WHERE ct.tag_id = tags.id
), 0),
updated_at = CURRENT_TIMESTAMP
WHERE usage_count != COALESCE((
    SELECT COUNT(*) 
    FROM content_tags ct 
    WHERE ct.tag_id = tags.id
), 0);

-- Clean up orphaned metadata (soft delete approach)
UPDATE content_metadata
SET metadata_value = '[ORPHANED]',
    updated_at = CURRENT_TIMESTAMP
WHERE content_id NOT IN (SELECT id FROM content);

-- Mark invalid downloads as failed
UPDATE downloads
SET status = 'failed',
    error_count = error_count + 1,
    last_error_message = 'Data integrity check: Invalid status combination',
    updated_at = CURRENT_TIMESTAMP
WHERE (
    (status = 'completed' AND (completed_at IS NULL OR final_file_path IS NULL)) OR
    (status = 'failed' AND error_count = 0)
);
```

## Validation Documentation and Guidelines

### 1. **Developer Guidelines**

#### Validation Checklist for Application Developers

**Before Database Operations:**
- [ ] Validate all input data using `InputValidator`
- [ ] Check business rules using `BusinessRuleValidator`
- [ ] Ensure required fields are present and non-empty
- [ ] Validate data type consistency for metadata
- [ ] Check URL formats and platform compatibility

**During Database Operations:**
- [ ] Use database transactions for multi-table operations
- [ ] Handle constraint violation exceptions gracefully
- [ ] Log validation failures for debugging
- [ ] Provide meaningful error messages to users

**After Database Operations:**
- [ ] Verify data was inserted correctly
- [ ] Check for constraint violations in related tables
- [ ] Update derived/computed values if necessary
- [ ] Monitor for data integrity issues

### 2. **Error Handling Patterns**

```python
# File: core/services/validation/validation_service.py
class ValidationService:
    """
    Centralized validation service combining all validation layers
    """
    
    def __init__(self, db_service):
        self.input_validator = InputValidator()
        self.business_validator = BusinessRuleValidator(db_service)
        self.db = db_service
    
    def validate_and_save_content(self, content_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Validate and save content with comprehensive error handling"""
        
        try:
            # Input validation
            input_errors = self.input_validator.validate_content_data(content_data)
            if input_errors:
                return False, {'validation_errors': input_errors}
            
            # Business rule validation
            business_errors = self.business_validator.validate_content_uniqueness(content_data)
            if business_errors:
                return False, {'business_errors': business_errors}
            
            # Attempt database insertion
            with self.db.transaction():
                content_id = self.db.insert_content(content_data)
                
                # Validate metadata if provided
                if 'metadata' in content_data:
                    metadata_errors = self.business_validator.validate_metadata_business_rules(
                        content_id, content_data['metadata']
                    )
                    if metadata_errors:
                        raise ValueError(f"Metadata validation failed: {metadata_errors}")
                    
                    self.db.insert_metadata(content_id, content_data['metadata'])
                
                return True, {'content_id': content_id}
                
        except Exception as e:
            # Handle database constraint violations
            if 'UNIQUE constraint failed' in str(e):
                return False, {'constraint_error': 'Duplicate content detected'}
            elif 'CHECK constraint failed' in str(e):
                return False, {'constraint_error': f'Data validation failed: {str(e)}'}
            elif 'FOREIGN KEY constraint failed' in str(e):
                return False, {'constraint_error': 'Invalid reference to related data'}
            else:
                # Log unexpected errors
                logger.error(f"Unexpected validation error: {str(e)}")
                return False, {'system_error': 'An unexpected error occurred'}
```

This comprehensive validation rules implementation ensures data integrity, prevents corruption, and maintains consistency across all aspects of the Social Download Manager v2.0 database schema. 