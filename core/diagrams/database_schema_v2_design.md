# Database Schema v2.0 Design Document

## Executive Summary

This document outlines the design for the Social Download Manager v2.0 database schema, optimized for multi-platform content management, improved performance, and scalable metadata storage.

## Current Schema Analysis

### Existing Models (v1.2.1)
1. **BaseEntity** - Common fields (id, created_at, updated_at, version, metadata)
2. **ContentModel** - Main content entity with platform-specific fields
3. **DownloadModel** - Download tracking and progress
4. **DownloadSession** - Detailed session management  
5. **DownloadError** - Error tracking and retry logic

### Identified Issues with Current Schema
- **Monolithic ContentModel**: All platform metadata stored in single table
- **JSON blob storage**: Platform-specific data stored as JSON (not queryable)
- **Limited relationships**: Missing proper relationships between entities
- **No platform abstraction**: Platform-specific logic mixed with generic content
- **Performance concerns**: Large table with mixed data types affects queries

## New Schema Design - Entity Relationship Model

### Core Entities

#### 1. **platforms** Table
Primary reference table for supported platforms.

```sql
CREATE TABLE platforms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,          -- 'youtube', 'tiktok', etc.
    display_name VARCHAR(100) NOT NULL,        -- 'YouTube', 'TikTok', etc.
    base_url VARCHAR(255),                     -- 'https://youtube.com'
    api_endpoint VARCHAR(255),                 -- API base URL if applicable
    is_active BOOLEAN DEFAULT TRUE,
    supported_content_types JSON,              -- ['video', 'audio', 'playlist']
    metadata JSON DEFAULT '{}',               -- Platform-specific config
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Relationships**: One-to-Many with content, content_metadata

#### 2. **content** Table  
Core content information, platform-agnostic.

```sql
CREATE TABLE content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform_id INTEGER NOT NULL,
    
    -- Core identifiers
    original_url TEXT NOT NULL,
    platform_content_id VARCHAR(255),         -- Platform's internal ID
    canonical_url TEXT,                       -- Cleaned/canonical URL
    
    -- Basic content info
    title TEXT,
    description TEXT,
    content_type VARCHAR(50) NOT NULL,        -- 'video', 'audio', 'image', etc.
    status VARCHAR(50) DEFAULT 'pending',     -- 'pending', 'completed', 'failed'
    
    -- Content creator info
    author_name VARCHAR(255),
    author_id VARCHAR(255),                   -- Platform author ID
    author_url TEXT,
    
    -- Media properties
    duration_seconds INTEGER,                 -- For video/audio content
    file_size_bytes BIGINT,
    file_format VARCHAR(20),                 -- 'mp4', 'mp3', 'jpg', etc.
    
    -- Engagement metrics
    view_count BIGINT DEFAULT 0,
    like_count BIGINT DEFAULT 0,
    comment_count BIGINT DEFAULT 0,
    share_count BIGINT DEFAULT 0,
    
    -- Publication info
    published_at TIMESTAMP,
    
    -- Download info
    local_file_path TEXT,
    thumbnail_path TEXT,
    download_quality VARCHAR(50),
    
    -- Common timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    is_deleted BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (platform_id) REFERENCES platforms(id),
    UNIQUE(platform_id, platform_content_id)
);
```

**Relationships**: 
- Many-to-One with platforms
- One-to-Many with content_metadata, downloads, download_sessions
- Many-to-Many with tags (via content_tags)

#### 3. **content_metadata** Table
Platform-specific metadata storage with efficient querying.

```sql
CREATE TABLE content_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL,
    
    -- Metadata organization
    metadata_type VARCHAR(100) NOT NULL,      -- 'video_specs', 'audio_specs', 'platform_specific'
    metadata_key VARCHAR(255) NOT NULL,      -- 'resolution', 'bitrate', 'codec'
    metadata_value TEXT,                     -- Actual value
    data_type VARCHAR(20) DEFAULT 'string',  -- 'string', 'integer', 'float', 'boolean', 'json'
    
    -- For complex nested data
    parent_key VARCHAR(255),                 -- For hierarchical metadata
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE,
    UNIQUE(content_id, metadata_type, metadata_key, parent_key)
);
```

**Relationships**: Many-to-One with content

#### 4. **downloads** Table
Download tracking and management.

```sql
CREATE TABLE downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL,
    
    -- Download configuration
    requested_quality VARCHAR(50),
    requested_format VARCHAR(20),
    output_directory TEXT NOT NULL,
    custom_filename TEXT,
    
    -- Status and progress
    status VARCHAR(50) DEFAULT 'queued',
    progress_percentage DECIMAL(5,2) DEFAULT 0.00,
    current_speed_bps BIGINT,                -- Current download speed
    average_speed_bps BIGINT,                -- Average download speed
    
    -- File information
    final_filename TEXT,
    final_file_path TEXT,
    actual_file_size BIGINT,
    actual_format VARCHAR(20),
    actual_quality VARCHAR(50),
    
    -- Timing
    queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Error handling
    error_count INTEGER DEFAULT 0,
    last_error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Configuration
    downloader_engine VARCHAR(50),           -- 'yt-dlp', 'custom', etc.
    download_options JSON DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE
);
```

**Relationships**: 
- Many-to-One with content
- One-to-Many with download_sessions, download_errors

#### 5. **download_sessions** Table
Detailed session tracking for complex downloads.

```sql
CREATE TABLE download_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    download_id INTEGER NOT NULL,
    
    -- Session identification
    session_uuid VARCHAR(36) UNIQUE NOT NULL, -- For external tracking
    session_type VARCHAR(50) DEFAULT 'standard', -- 'standard', 'retry', 'resume'
    
    -- Progress tracking
    bytes_downloaded BIGINT DEFAULT 0,
    total_bytes BIGINT,
    chunks_completed INTEGER DEFAULT 0,
    total_chunks INTEGER,
    
    -- Performance metrics
    peak_speed_bps BIGINT,
    average_speed_bps BIGINT,
    connection_count INTEGER DEFAULT 1,
    
    -- Session timing
    session_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_ended_at TIMESTAMP,
    session_duration_seconds INTEGER,
    
    -- Session configuration
    user_agent TEXT,
    headers JSON DEFAULT '{}',
    proxy_used TEXT,
    
    -- Status
    session_status VARCHAR(50) DEFAULT 'active',
    termination_reason TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (download_id) REFERENCES downloads(id) ON DELETE CASCADE
);
```

**Relationships**: Many-to-One with downloads

#### 6. **download_errors** Table
Comprehensive error tracking and analysis.

```sql
CREATE TABLE download_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    download_id INTEGER NOT NULL,
    session_id INTEGER,                      -- Optional: specific session
    
    -- Error classification
    error_type VARCHAR(100) NOT NULL,        -- 'network', 'parsing', 'authentication', etc.
    error_code VARCHAR(50),                  -- HTTP status, platform error code
    error_message TEXT NOT NULL,
    
    -- Technical details
    stack_trace TEXT,
    request_url TEXT,
    response_headers JSON,
    user_agent TEXT,
    
    -- Context information
    retry_attempt INTEGER DEFAULT 0,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Resolution tracking
    is_resolved BOOLEAN DEFAULT FALSE,
    resolution_method TEXT,
    resolved_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (download_id) REFERENCES downloads(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES download_sessions(id) ON DELETE SET NULL
);
```

**Relationships**: 
- Many-to-One with downloads
- Many-to-One with download_sessions (optional)

#### 7. **tags** Table
Tag management for content organization.

```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,       -- URL-friendly version
    description TEXT,
    tag_type VARCHAR(50) DEFAULT 'user',     -- 'user', 'auto', 'hashtag', 'category'
    usage_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Relationships**: Many-to-Many with content (via content_tags)

#### 8. **content_tags** Table
Junction table for content-tag relationships.

```sql
CREATE TABLE content_tags (
    content_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    
    -- Relationship metadata
    assigned_by VARCHAR(50) DEFAULT 'user',  -- 'user', 'auto', 'import'
    confidence_score DECIMAL(3,2),          -- For auto-assigned tags (0.00-1.00)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (content_id, tag_id),
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
```

**Relationships**: Many-to-Many junction between content and tags

#### 9. **quality_options** Table
Available quality options for content.

```sql
CREATE TABLE quality_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL,
    
    -- Quality specification
    quality_label VARCHAR(50) NOT NULL,      -- '1080p', '720p', 'high', etc.
    format VARCHAR(20) NOT NULL,             -- 'mp4', 'webm', 'mp3', etc.
    
    -- Technical specifications
    resolution_width INTEGER,
    resolution_height INTEGER,
    bitrate_kbps INTEGER,
    fps DECIMAL(5,2),
    audio_bitrate_kbps INTEGER,
    
    -- File information
    estimated_file_size BIGINT,
    codec VARCHAR(50),
    audio_codec VARCHAR(50),
    
    -- Availability
    is_available BOOLEAN DEFAULT TRUE,
    download_url TEXT,                       -- If directly available
    expires_at TIMESTAMP,                    -- If URL has expiration
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE,
    UNIQUE(content_id, quality_label, format)
);
```

**Relationships**: Many-to-One with content

### Supporting Tables

#### 10. **schema_migrations** Table
Track database schema versions and migrations.

```sql
CREATE TABLE schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    migration_file VARCHAR(255),
    
    -- Execution tracking
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- Rollback information
    rollback_file VARCHAR(255),
    can_rollback BOOLEAN DEFAULT FALSE
);
```

#### 11. **application_settings** Table
Application configuration storage.

```sql
CREATE TABLE application_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key VARCHAR(255) NOT NULL UNIQUE,
    setting_value TEXT,
    data_type VARCHAR(20) DEFAULT 'string',
    description TEXT,
    
    -- Validation
    is_required BOOLEAN DEFAULT FALSE,
    default_value TEXT,
    validation_regex TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Entity Relationships Summary

### Primary Relationships:
1. **platforms** → **content** (One-to-Many)
2. **content** → **content_metadata** (One-to-Many)
3. **content** → **downloads** (One-to-Many)
4. **content** → **quality_options** (One-to-Many)
5. **downloads** → **download_sessions** (One-to-Many)
6. **downloads** → **download_errors** (One-to-Many)
7. **content** ↔ **tags** (Many-to-Many via content_tags)

### Key Design Principles:
- **Normalization**: Proper 3NF normalization to reduce redundancy
- **Flexibility**: Platform-specific metadata stored efficiently
- **Performance**: Strategic indexing and query optimization
- **Scalability**: Designed for large datasets and concurrent access
- **Auditability**: Comprehensive tracking and versioning
- **Extensibility**: Easy to add new platforms and content types

## Migration Considerations

### From v1.2.1 to v2.0:
1. **Data Migration**: Transform existing ContentModel data to normalized structure
2. **Metadata Extraction**: Parse JSON metadata into content_metadata table
3. **Platform Standardization**: Map existing platform strings to platform records
4. **Download History**: Preserve existing download tracking data
5. **Backward Compatibility**: Maintain API compatibility during transition

This design provides a solid foundation for multi-platform content management while maintaining performance and scalability. 