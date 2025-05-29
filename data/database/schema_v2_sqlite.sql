-- Social Download Manager v2.0 Database Schema
-- SQLite Implementation with Performance Optimizations
-- Created: 2024-12-XX
-- Version: 2.0.0

-- =============================================================================
-- PRAGMA SETTINGS FOR OPTIMAL PERFORMANCE
-- =============================================================================

PRAGMA foreign_keys = ON;              -- Enable foreign key constraints
PRAGMA journal_mode = WAL;             -- Write-Ahead Logging for concurrency
PRAGMA synchronous = NORMAL;           -- Balance safety and performance
PRAGMA cache_size = -64000;            -- 64MB cache size
PRAGMA temp_store = MEMORY;            -- Store temp tables in memory
PRAGMA mmap_size = 268435456;          -- 256MB memory-mapped I/O
PRAGMA optimize;                       -- Enable query planner optimizations

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Platforms reference table
CREATE TABLE platforms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    base_url VARCHAR(255),
    api_endpoint VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    supported_content_types TEXT DEFAULT '[]',  -- JSON array
    metadata TEXT DEFAULT '{}',                 -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_name_format CHECK (name = LOWER(name) AND name NOT LIKE '% %'),
    CONSTRAINT chk_supported_types_json CHECK (json_valid(supported_content_types)),
    CONSTRAINT chk_metadata_json CHECK (json_valid(metadata))
);

-- Core content table (platform-agnostic)
CREATE TABLE content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform_id INTEGER NOT NULL,
    
    -- Core identifiers
    original_url TEXT NOT NULL,
    platform_content_id VARCHAR(255),
    canonical_url TEXT,
    
    -- Basic content info
    title TEXT,
    description TEXT,
    content_type VARCHAR(50) NOT NULL DEFAULT 'video',
    status VARCHAR(50) DEFAULT 'pending',
    
    -- Content creator info
    author_name VARCHAR(255),
    author_id VARCHAR(255),
    author_url TEXT,
    
    -- Media properties
    duration_seconds INTEGER,
    file_size_bytes BIGINT,
    file_format VARCHAR(20),
    
    -- Engagement metrics (commonly accessed, so kept in main table)
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
    
    -- Common timestamps and versioning
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    is_deleted BOOLEAN DEFAULT FALSE,
    
    -- Foreign keys
    FOREIGN KEY (platform_id) REFERENCES platforms(id),
    
    -- Constraints
    CONSTRAINT chk_content_type CHECK (content_type IN ('video', 'audio', 'image', 'post', 'story', 'reel', 'livestream', 'playlist')),
    CONSTRAINT chk_status CHECK (status IN ('pending', 'downloading', 'processing', 'completed', 'failed', 'cancelled', 'paused')),
    CONSTRAINT chk_url_not_empty CHECK (LENGTH(TRIM(original_url)) > 0),
    CONSTRAINT chk_positive_metrics CHECK (
        view_count >= 0 AND like_count >= 0 AND 
        comment_count >= 0 AND share_count >= 0
    ),
    
    -- Unique constraints
    UNIQUE(platform_id, platform_content_id)
);

-- Platform-specific metadata (flexible key-value storage)
CREATE TABLE content_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL,
    
    -- Metadata organization
    metadata_type VARCHAR(100) NOT NULL,
    metadata_key VARCHAR(255) NOT NULL,
    metadata_value TEXT,
    data_type VARCHAR(20) DEFAULT 'string',
    
    -- For hierarchical metadata
    parent_key VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE,
    
    -- Constraints
    CONSTRAINT chk_data_type CHECK (data_type IN ('string', 'integer', 'float', 'boolean', 'json', 'timestamp')),
    CONSTRAINT chk_metadata_key_not_empty CHECK (LENGTH(TRIM(metadata_key)) > 0),
    
    -- Unique constraint to prevent duplicate metadata
    UNIQUE(content_id, metadata_type, metadata_key, parent_key)
);

-- Downloads table
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
    current_speed_bps BIGINT,
    average_speed_bps BIGINT,
    
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
    downloader_engine VARCHAR(50),
    download_options TEXT DEFAULT '{}',  -- JSON
    
    -- Standard fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    
    -- Foreign keys
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE,
    
    -- Constraints
    CONSTRAINT chk_download_status CHECK (status IN ('queued', 'starting', 'downloading', 'processing', 'completed', 'failed', 'cancelled', 'paused', 'retrying')),
    CONSTRAINT chk_progress_range CHECK (progress_percentage >= 0.00 AND progress_percentage <= 100.00),
    CONSTRAINT chk_retry_counts CHECK (retry_count >= 0 AND max_retries >= 0),
    CONSTRAINT chk_download_options_json CHECK (json_valid(download_options))
);

-- Download sessions for detailed tracking
CREATE TABLE download_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    download_id INTEGER NOT NULL,
    
    -- Session identification
    session_uuid VARCHAR(36) UNIQUE NOT NULL,
    session_type VARCHAR(50) DEFAULT 'standard',
    
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
    headers TEXT DEFAULT '{}',  -- JSON
    proxy_used TEXT,
    
    -- Status
    session_status VARCHAR(50) DEFAULT 'active',
    termination_reason TEXT,
    
    -- Standard fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (download_id) REFERENCES downloads(id) ON DELETE CASCADE,
    
    -- Constraints
    CONSTRAINT chk_session_type CHECK (session_type IN ('standard', 'retry', 'resume', 'parallel')),
    CONSTRAINT chk_session_status CHECK (session_status IN ('active', 'completed', 'failed', 'cancelled', 'paused')),
    CONSTRAINT chk_session_uuid_format CHECK (LENGTH(session_uuid) = 36),
    CONSTRAINT chk_headers_json CHECK (json_valid(headers)),
    CONSTRAINT chk_positive_bytes CHECK (bytes_downloaded >= 0)
);

-- Download errors tracking
CREATE TABLE download_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    download_id INTEGER NOT NULL,
    session_id INTEGER,
    
    -- Error classification
    error_type VARCHAR(100) NOT NULL,
    error_code VARCHAR(50),
    error_message TEXT NOT NULL,
    
    -- Technical details
    stack_trace TEXT,
    request_url TEXT,
    response_headers TEXT,  -- JSON
    user_agent TEXT,
    
    -- Context information
    retry_attempt INTEGER DEFAULT 0,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Resolution tracking
    is_resolved BOOLEAN DEFAULT FALSE,
    resolution_method TEXT,
    resolved_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (download_id) REFERENCES downloads(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES download_sessions(id) ON DELETE SET NULL,
    
    -- Constraints
    CONSTRAINT chk_error_type_not_empty CHECK (LENGTH(TRIM(error_type)) > 0),
    CONSTRAINT chk_error_message_not_empty CHECK (LENGTH(TRIM(error_message)) > 0)
);

-- Quality options available for content
CREATE TABLE quality_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL,
    
    -- Quality specification
    quality_label VARCHAR(50) NOT NULL,
    format VARCHAR(20) NOT NULL,
    
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
    download_url TEXT,
    expires_at TIMESTAMP,
    
    -- Standard fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE,
    
    -- Constraints
    CONSTRAINT chk_quality_label_not_empty CHECK (LENGTH(TRIM(quality_label)) > 0),
    CONSTRAINT chk_format_not_empty CHECK (LENGTH(TRIM(format)) > 0),
    CONSTRAINT chk_positive_dimensions CHECK (
        (resolution_width IS NULL OR resolution_width > 0) AND
        (resolution_height IS NULL OR resolution_height > 0)
    ),
    
    -- Unique constraint
    UNIQUE(content_id, quality_label, format)
);

-- Tags for content organization
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    tag_type VARCHAR(50) DEFAULT 'user',
    usage_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_tag_name_not_empty CHECK (LENGTH(TRIM(name)) > 0),
    CONSTRAINT chk_tag_slug_format CHECK (slug = LOWER(slug) AND slug NOT LIKE '% %'),
    CONSTRAINT chk_tag_type CHECK (tag_type IN ('user', 'auto', 'hashtag', 'category', 'system')),
    CONSTRAINT chk_usage_count_positive CHECK (usage_count >= 0)
);

-- Junction table for content-tag relationships
CREATE TABLE content_tags (
    content_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    
    -- Relationship metadata
    assigned_by VARCHAR(50) DEFAULT 'user',
    confidence_score DECIMAL(3,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Primary key
    PRIMARY KEY (content_id, tag_id),
    
    -- Foreign keys
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    
    -- Constraints
    CONSTRAINT chk_assigned_by CHECK (assigned_by IN ('user', 'auto', 'import', 'system')),
    CONSTRAINT chk_confidence_range CHECK (confidence_score IS NULL OR (confidence_score >= 0.00 AND confidence_score <= 1.00))
);

-- =============================================================================
-- SUPPORTING TABLES
-- =============================================================================

-- Schema migrations tracking
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
    can_rollback BOOLEAN DEFAULT FALSE,
    
    -- Constraints
    CONSTRAINT chk_version_not_empty CHECK (LENGTH(TRIM(version)) > 0)
);

-- Application settings
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_setting_key_not_empty CHECK (LENGTH(TRIM(setting_key)) > 0),
    CONSTRAINT chk_setting_data_type CHECK (data_type IN ('string', 'integer', 'float', 'boolean', 'json'))
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE OPTIMIZATION
-- =============================================================================

-- Content table indexes
CREATE INDEX idx_content_platform ON content(platform_id);
CREATE INDEX idx_content_status ON content(status);
CREATE INDEX idx_content_type ON content(content_type);
CREATE INDEX idx_content_author ON content(author_name);
CREATE INDEX idx_content_published ON content(published_at);
CREATE INDEX idx_content_platform_content_id ON content(platform_id, platform_content_id);
CREATE INDEX idx_content_url ON content(original_url);
CREATE INDEX idx_content_not_deleted ON content(is_deleted) WHERE is_deleted = FALSE;

-- Content metadata indexes
CREATE INDEX idx_content_metadata_lookup ON content_metadata(content_id, metadata_type, metadata_key);
CREATE INDEX idx_content_metadata_type ON content_metadata(metadata_type);
CREATE INDEX idx_content_metadata_key ON content_metadata(metadata_key);
CREATE INDEX idx_content_metadata_value ON content_metadata(metadata_value) WHERE data_type IN ('string', 'integer');
CREATE INDEX idx_content_metadata_platform_specific ON content_metadata(content_id, metadata_key, metadata_value) 
    WHERE metadata_type = 'platform_specific';
CREATE INDEX idx_content_metadata_engagement ON content_metadata(content_id, metadata_key, metadata_value) 
    WHERE metadata_type = 'engagement';

-- Downloads table indexes
CREATE INDEX idx_downloads_content ON downloads(content_id);
CREATE INDEX idx_downloads_status ON downloads(status);
CREATE INDEX idx_downloads_queued_at ON downloads(queued_at);
CREATE INDEX idx_downloads_active ON downloads(status) WHERE status IN ('queued', 'downloading', 'processing');

-- Download sessions indexes
CREATE INDEX idx_download_sessions_download ON download_sessions(download_id);
CREATE INDEX idx_download_sessions_uuid ON download_sessions(session_uuid);
CREATE INDEX idx_download_sessions_started ON download_sessions(session_started_at);
CREATE INDEX idx_download_sessions_status ON download_sessions(session_status);

-- Download errors indexes
CREATE INDEX idx_download_errors_download ON download_errors(download_id);
CREATE INDEX idx_download_errors_session ON download_errors(session_id);
CREATE INDEX idx_download_errors_type ON download_errors(error_type);
CREATE INDEX idx_download_errors_occurred ON download_errors(occurred_at);
CREATE INDEX idx_download_errors_unresolved ON download_errors(is_resolved) WHERE is_resolved = FALSE;

-- Quality options indexes
CREATE INDEX idx_quality_options_content ON quality_options(content_id);
CREATE INDEX idx_quality_options_available ON quality_options(is_available) WHERE is_available = TRUE;
CREATE INDEX idx_quality_options_quality ON quality_options(quality_label);

-- Tags indexes
CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_tags_slug ON tags(slug);
CREATE INDEX idx_tags_type ON tags(tag_type);
CREATE INDEX idx_tags_usage ON tags(usage_count);

-- Content tags indexes
CREATE INDEX idx_content_tags_content ON content_tags(content_id);
CREATE INDEX idx_content_tags_tag ON content_tags(tag_id);
CREATE INDEX idx_content_tags_assigned_by ON content_tags(assigned_by);

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- Content with platform information
CREATE VIEW content_with_platform AS
SELECT 
    c.*,
    p.name as platform_name,
    p.display_name as platform_display_name,
    p.base_url as platform_base_url
FROM content c
JOIN platforms p ON c.platform_id = p.id
WHERE c.is_deleted = FALSE;

-- Content summary with basic metadata
CREATE VIEW content_summary AS
SELECT 
    c.id,
    c.title,
    c.author_name,
    c.duration_seconds,
    c.view_count,
    c.like_count,
    c.status,
    p.name as platform,
    p.display_name as platform_display,
    c.created_at,
    c.published_at
FROM content c
JOIN platforms p ON c.platform_id = p.id
WHERE c.is_deleted = FALSE;

-- Active downloads with progress
CREATE VIEW active_downloads AS
SELECT 
    d.*,
    c.title as content_title,
    c.author_name,
    p.name as platform_name
FROM downloads d
JOIN content c ON d.content_id = c.id
JOIN platforms p ON c.platform_id = p.id
WHERE d.status IN ('queued', 'starting', 'downloading', 'processing', 'retrying');

-- =============================================================================
-- TRIGGERS FOR DATA INTEGRITY AND AUTOMATION
-- =============================================================================

-- Update timestamps trigger for content
CREATE TRIGGER update_content_timestamp
    AFTER UPDATE ON content
    FOR EACH ROW
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE content SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Update timestamps trigger for content_metadata
CREATE TRIGGER update_content_metadata_timestamp
    AFTER UPDATE ON content_metadata
    FOR EACH ROW
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE content_metadata SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Validate metadata values based on data type
CREATE TRIGGER validate_metadata_integer
    BEFORE INSERT ON content_metadata
    FOR EACH ROW
    WHEN NEW.data_type = 'integer' AND NEW.metadata_value NOT GLOB '[+-]*[0-9]*'
BEGIN
    SELECT RAISE(ABORT, 'Invalid integer value for metadata: ' || NEW.metadata_value);
END;

CREATE TRIGGER validate_metadata_float
    BEFORE INSERT ON content_metadata
    FOR EACH ROW
    WHEN NEW.data_type = 'float' AND NEW.metadata_value NOT GLOB '[+-]*[0-9]*.*[0-9]*'
BEGIN
    SELECT RAISE(ABORT, 'Invalid float value for metadata: ' || NEW.metadata_value);
END;

CREATE TRIGGER validate_metadata_boolean
    BEFORE INSERT ON content_metadata
    FOR EACH ROW
    WHEN NEW.data_type = 'boolean' AND NEW.metadata_value NOT IN ('true', 'false')
BEGIN
    SELECT RAISE(ABORT, 'Invalid boolean value for metadata: ' || NEW.metadata_value);
END;

CREATE TRIGGER validate_metadata_json
    BEFORE INSERT ON content_metadata
    FOR EACH ROW
    WHEN NEW.data_type = 'json' AND NOT json_valid(NEW.metadata_value)
BEGIN
    SELECT RAISE(ABORT, 'Invalid JSON value for metadata: ' || NEW.metadata_value);
END;

-- Update tag usage count
CREATE TRIGGER update_tag_usage_count_insert
    AFTER INSERT ON content_tags
    FOR EACH ROW
BEGIN
    UPDATE tags SET usage_count = usage_count + 1 WHERE id = NEW.tag_id;
END;

CREATE TRIGGER update_tag_usage_count_delete
    AFTER DELETE ON content_tags
    FOR EACH ROW
BEGIN
    UPDATE tags SET usage_count = usage_count - 1 WHERE id = OLD.tag_id;
END;

-- =============================================================================
-- INITIAL DATA
-- =============================================================================

-- Insert supported platforms
INSERT INTO platforms (name, display_name, base_url, supported_content_types, is_active) VALUES
('youtube', 'YouTube', 'https://www.youtube.com', '["video", "audio", "playlist"]', TRUE),
('tiktok', 'TikTok', 'https://www.tiktok.com', '["video"]', TRUE),
('instagram', 'Instagram', 'https://www.instagram.com', '["video", "image", "story", "reel"]', TRUE),
('facebook', 'Facebook', 'https://www.facebook.com', '["video", "image", "post"]', FALSE),
('twitter', 'Twitter/X', 'https://x.com', '["video", "image", "post"]', FALSE);

-- Insert initial schema migration record
INSERT INTO schema_migrations (version, description, success) VALUES
('2.0.0', 'Initial v2.0 schema creation', TRUE);

-- Insert default application settings
INSERT INTO application_settings (setting_key, setting_value, data_type, description, is_required) VALUES
('app_version', '2.0.0', 'string', 'Application version', TRUE),
('database_version', '2.0.0', 'string', 'Database schema version', TRUE),
('default_download_directory', 'downloads', 'string', 'Default download directory', TRUE),
('max_concurrent_downloads', '3', 'integer', 'Maximum concurrent downloads', TRUE),
('enable_thumbnails', 'true', 'boolean', 'Enable thumbnail downloading', FALSE),
('default_video_quality', '720p', 'string', 'Default video quality preference', FALSE);

-- =============================================================================
-- PERFORMANCE OPTIMIZATION COMMANDS
-- =============================================================================

-- Analyze tables for query optimization
ANALYZE;

-- Final optimization
PRAGMA optimize; 