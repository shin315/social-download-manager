# Platform-Specific Metadata Structures

## Database Platform Implementation Details

### SQLite-Specific Optimizations

#### 1. **Data Type Mappings**

SQLite has dynamic typing, but we'll use type affinity for optimal performance:

```sql
-- Optimized SQLite data types for our schema
TEXT        -- For strings, URLs, descriptions, JSON
INTEGER     -- For IDs, counts, timestamps (epoch)
REAL        -- For floating point numbers (fps, percentages)
BLOB        -- For binary data (future: thumbnails, cached data)
NUMERIC     -- For decimal values (DECIMAL mapped to NUMERIC)
```

#### 2. **SQLite-Specific Schema Enhancements**

```sql
-- Enable foreign key constraints (must be done per connection)
PRAGMA foreign_keys = ON;

-- Performance optimizations
PRAGMA journal_mode = WAL;           -- Write-Ahead Logging for better concurrency
PRAGMA synchronous = NORMAL;         -- Balance between safety and performance  
PRAGMA cache_size = -64000;          -- 64MB cache (negative = KB)
PRAGMA temp_store = MEMORY;          -- Store temp tables in memory
PRAGMA mmap_size = 268435456;        -- 256MB memory-mapped I/O
```

#### 3. **Platform-Specific Table Structures**

### YouTube Metadata Schema

YouTube content has rich metadata - here's how we store it efficiently:

```sql
-- YouTube-specific metadata examples in content_metadata table
INSERT INTO content_metadata (content_id, metadata_type, metadata_key, metadata_value, data_type) VALUES
-- Video technical specs
(1, 'video_specs', 'resolution_width', '1920', 'integer'),
(1, 'video_specs', 'resolution_height', '1080', 'integer'),
(1, 'video_specs', 'fps', '30.0', 'float'),
(1, 'video_specs', 'video_codec', 'avc1.640028', 'string'),
(1, 'video_specs', 'audio_codec', 'mp4a.40.2', 'string'),
(1, 'video_specs', 'container', 'mp4', 'string'),

-- YouTube-specific metadata
(1, 'platform_specific', 'youtube_video_id', 'dQw4w9WgXcQ', 'string'),
(1, 'platform_specific', 'youtube_channel_id', 'UCuAXFkgsw1L7xaCfnd5JJOw', 'string'),
(1, 'platform_specific', 'youtube_channel_name', 'Rick Astley', 'string'),
(1, 'platform_specific', 'youtube_upload_date', '2009-10-25', 'string'),
(1, 'platform_specific', 'youtube_category_id', '10', 'integer'),
(1, 'platform_specific', 'youtube_category_name', 'Music', 'string'),
(1, 'platform_specific', 'youtube_language', 'en', 'string'),
(1, 'platform_specific', 'youtube_license', 'youtube', 'string'),
(1, 'platform_specific', 'youtube_age_limit', '0', 'integer'),
(1, 'platform_specific', 'youtube_is_live', 'false', 'boolean'),
(1, 'platform_specific', 'youtube_was_live', 'false', 'boolean'),

-- Engagement metrics (can be updated)
(1, 'engagement', 'like_count', '13567891', 'integer'),
(1, 'engagement', 'dislike_count', '807839', 'integer'),
(1, 'engagement', 'comment_count', '2479751', 'integer'),
(1, 'engagement', 'view_count', '1437264847', 'integer'),

-- Quality/format options metadata
(1, 'quality_options', 'available_formats', '["mp4", "webm", "3gp"]', 'json'),
(1, 'quality_options', 'available_qualities', '["144p", "240p", "360p", "480p", "720p", "1080p"]', 'json'),
(1, 'quality_options', 'has_audio', 'true', 'boolean'),
(1, 'quality_options', 'has_video', 'true', 'boolean'),

-- Playlist information (if applicable)
(1, 'playlist_info', 'playlist_id', 'PLrAXtmRdnEQy4GXLwVpQ7R1-Q6s7YrL0g', 'string'),
(1, 'playlist_info', 'playlist_title', 'Rick Astley Greatest Hits', 'string'),
(1, 'playlist_info', 'playlist_index', '1', 'integer'),
(1, 'playlist_info', 'playlist_count', '15', 'integer');
```

### TikTok Metadata Schema

TikTok has different metadata structure focused on short-form content:

```sql
-- TikTok-specific metadata examples
INSERT INTO content_metadata (content_id, metadata_type, metadata_key, metadata_value, data_type) VALUES
-- Video specs for TikTok (typically mobile-optimized)
(2, 'video_specs', 'resolution_width', '720', 'integer'),
(2, 'video_specs', 'resolution_height', '1280', 'integer'),
(2, 'video_specs', 'fps', '30.0', 'float'),
(2, 'video_specs', 'aspect_ratio', '9:16', 'string'),
(2, 'video_specs', 'orientation', 'portrait', 'string'),

-- TikTok-specific metadata
(2, 'platform_specific', 'tiktok_video_id', '7123456789012345678', 'string'),
(2, 'platform_specific', 'tiktok_user_id', '@username', 'string'),
(2, 'platform_specific', 'tiktok_user_display_name', 'Display Name', 'string'),
(2, 'platform_specific', 'tiktok_user_verified', 'true', 'boolean'),
(2, 'platform_specific', 'tiktok_music_id', '7012345678901234567', 'string'),
(2, 'platform_specific', 'tiktok_music_title', 'Original Sound', 'string'),
(2, 'platform_specific', 'tiktok_music_author', '@username', 'string'),
(2, 'platform_specific', 'tiktok_effect_ids', '["effect1", "effect2"]', 'json'),
(2, 'platform_specific', 'tiktok_hashtags', '["fyp", "viral", "trend"]', 'json'),
(2, 'platform_specific', 'tiktok_mentions', '["@user1", "@user2"]', 'json'),
(2, 'platform_specific', 'tiktok_is_ad', 'false', 'boolean'),
(2, 'platform_specific', 'tiktok_region_blocked', 'false', 'boolean'),

-- Engagement metrics (TikTok-style)
(2, 'engagement', 'like_count', '125634', 'integer'),
(2, 'engagement', 'comment_count', '1547', 'integer'),
(2, 'engagement', 'share_count', '8923', 'integer'),
(2, 'engagement', 'play_count', '1567890', 'integer'),
(2, 'engagement', 'download_count', '2134', 'integer'),

-- TikTok content classification
(2, 'content_classification', 'is_original_sound', 'false', 'boolean'),
(2, 'content_classification', 'has_captions', 'true', 'boolean'),
(2, 'content_classification', 'has_stickers', 'true', 'boolean'),
(2, 'content_classification', 'duet_info', '{"is_duet": true, "original_video_id": "7012345678901234567"}', 'json');
```

### Instagram Metadata Schema

Instagram supports multiple content types (posts, reels, stories):

```sql
-- Instagram-specific metadata examples
INSERT INTO content_metadata (content_id, metadata_type, metadata_key, metadata_value, data_type) VALUES
-- Instagram content specs
(3, 'video_specs', 'resolution_width', '1080', 'integer'),
(3, 'video_specs', 'resolution_height', '1080', 'integer'),
(3, 'video_specs', 'aspect_ratio', '1:1', 'string'),

-- Instagram-specific metadata
(3, 'platform_specific', 'instagram_media_id', '2876543210123456789', 'string'),
(3, 'platform_specific', 'instagram_shortcode', 'CXYZabcdefg', 'string'),
(3, 'platform_specific', 'instagram_user_id', '123456789', 'string'),
(3, 'platform_specific', 'instagram_username', 'username', 'string'),
(3, 'platform_specific', 'instagram_user_full_name', 'Full Name', 'string'),
(3, 'platform_specific', 'instagram_user_verified', 'true', 'boolean'),
(3, 'platform_specific', 'instagram_media_type', 'reel', 'string'),
(3, 'platform_specific', 'instagram_is_carousel', 'false', 'boolean'),
(3, 'platform_specific', 'instagram_carousel_count', '1', 'integer'),
(3, 'platform_specific', 'instagram_location_id', '12345', 'string'),
(3, 'platform_specific', 'instagram_location_name', 'New York, NY', 'string'),

-- Instagram engagement
(3, 'engagement', 'like_count', '15678', 'integer'),
(3, 'engagement', 'comment_count', '234', 'integer'),
(3, 'engagement', 'view_count', '89123', 'integer'),

-- Instagram hashtags and mentions
(3, 'content_tags', 'hashtags', '["photography", "art", "inspiration"]', 'json'),
(3, 'content_tags', 'mentions', '["@photographer", "@artist"]', 'json');
```

## Storage Optimization Strategies

### 1. **Hierarchical Metadata Storage**

For complex nested metadata, use the `parent_key` field:

```sql
-- Example: YouTube video format information
INSERT INTO content_metadata (content_id, metadata_type, metadata_key, metadata_value, data_type, parent_key) VALUES
-- Format group
(1, 'formats', 'format_id', '22', 'string', NULL),
(1, 'formats', 'ext', 'mp4', 'string', 'format_22'),
(1, 'formats', 'resolution', '720p', 'string', 'format_22'),
(1, 'formats', 'filesize', '45678901', 'integer', 'format_22'),
(1, 'formats', 'video_codec', 'avc1.64001F', 'string', 'format_22'),
(1, 'formats', 'audio_codec', 'mp4a.40.2', 'string', 'format_22'),
-- Another format
(1, 'formats', 'format_id', '18', 'string', NULL),
(1, 'formats', 'ext', 'mp4', 'string', 'format_18'),
(1, 'formats', 'resolution', '360p', 'string', 'format_18'),
(1, 'formats', 'filesize', '12345678', 'integer', 'format_18');
```

### 2. **Indexing Strategy for Metadata**

```sql
-- Indexes for efficient metadata queries
CREATE INDEX idx_content_metadata_lookup ON content_metadata(content_id, metadata_type, metadata_key);
CREATE INDEX idx_content_metadata_type ON content_metadata(metadata_type);
CREATE INDEX idx_content_metadata_key ON content_metadata(metadata_key);
CREATE INDEX idx_content_metadata_value ON content_metadata(metadata_value) WHERE data_type IN ('string', 'integer');

-- Partial indexes for common queries
CREATE INDEX idx_content_metadata_platform_specific ON content_metadata(content_id, metadata_key, metadata_value) 
    WHERE metadata_type = 'platform_specific';
CREATE INDEX idx_content_metadata_engagement ON content_metadata(content_id, metadata_key, metadata_value) 
    WHERE metadata_type = 'engagement';
```

### 3. **Data Type Validation**

```sql
-- Add CHECK constraints for data integrity
ALTER TABLE content_metadata ADD CONSTRAINT chk_data_type 
    CHECK (data_type IN ('string', 'integer', 'float', 'boolean', 'json', 'timestamp'));

-- Add triggers for data type validation
CREATE TRIGGER validate_metadata_value
BEFORE INSERT ON content_metadata
WHEN NEW.data_type = 'integer' AND NEW.metadata_value NOT GLOB '[0-9]*'
BEGIN
    SELECT RAISE(ABORT, 'Invalid integer value for metadata');
END;

CREATE TRIGGER validate_metadata_boolean
BEFORE INSERT ON content_metadata  
WHEN NEW.data_type = 'boolean' AND NEW.metadata_value NOT IN ('true', 'false')
BEGIN
    SELECT RAISE(ABORT, 'Invalid boolean value for metadata');
END;
```

## Platform Data Extraction Patterns

### 1. **YouTube Data Extraction**

```python
# Example extraction pattern for YouTube
def extract_youtube_metadata(video_info: dict) -> List[Tuple]:
    """Extract YouTube metadata into key-value pairs"""
    metadata = []
    
    # Basic video information
    if 'id' in video_info:
        metadata.append(('platform_specific', 'youtube_video_id', video_info['id'], 'string'))
    
    if 'uploader_id' in video_info:
        metadata.append(('platform_specific', 'youtube_channel_id', video_info['uploader_id'], 'string'))
    
    if 'uploader' in video_info:
        metadata.append(('platform_specific', 'youtube_channel_name', video_info['uploader'], 'string'))
    
    # Video specifications
    if 'width' in video_info:
        metadata.append(('video_specs', 'resolution_width', str(video_info['width']), 'integer'))
    
    if 'height' in video_info:
        metadata.append(('video_specs', 'resolution_height', str(video_info['height']), 'integer'))
    
    if 'fps' in video_info:
        metadata.append(('video_specs', 'fps', str(video_info['fps']), 'float'))
    
    # Engagement metrics
    if 'like_count' in video_info:
        metadata.append(('engagement', 'like_count', str(video_info['like_count']), 'integer'))
    
    if 'view_count' in video_info:
        metadata.append(('engagement', 'view_count', str(video_info['view_count']), 'integer'))
    
    return metadata
```

### 2. **TikTok Data Extraction**

```python
def extract_tiktok_metadata(video_info: dict) -> List[Tuple]:
    """Extract TikTok metadata into key-value pairs"""
    metadata = []
    
    # TikTok-specific fields
    if 'id' in video_info:
        metadata.append(('platform_specific', 'tiktok_video_id', video_info['id'], 'string'))
    
    if 'author' in video_info:
        author = video_info['author']
        if 'unique_id' in author:
            metadata.append(('platform_specific', 'tiktok_user_id', author['unique_id'], 'string'))
        if 'nickname' in author:
            metadata.append(('platform_specific', 'tiktok_user_display_name', author['nickname'], 'string'))
        if 'verified' in author:
            metadata.append(('platform_specific', 'tiktok_user_verified', str(author['verified']).lower(), 'boolean'))
    
    # Music information
    if 'music' in video_info:
        music = video_info['music']
        if 'id' in music:
            metadata.append(('platform_specific', 'tiktok_music_id', music['id'], 'string'))
        if 'title' in music:
            metadata.append(('platform_specific', 'tiktok_music_title', music['title'], 'string'))
    
    # Extract hashtags
    if 'hashtags' in video_info:
        hashtags_json = json.dumps(video_info['hashtags'])
        metadata.append(('platform_specific', 'tiktok_hashtags', hashtags_json, 'json'))
    
    return metadata
```

## Query Performance Optimization

### 1. **Common Query Patterns**

```sql
-- Efficient queries using the new metadata structure

-- Get all YouTube videos with specific quality
SELECT c.id, c.title, cm.metadata_value as quality
FROM content c
JOIN content_metadata cm ON c.id = cm.content_id
JOIN platforms p ON c.platform_id = p.id
WHERE p.name = 'youtube' 
  AND cm.metadata_type = 'video_specs' 
  AND cm.metadata_key = 'resolution_height'
  AND CAST(cm.metadata_value AS INTEGER) >= 720;

-- Get engagement metrics for a content item
SELECT 
    cm.metadata_key,
    cm.metadata_value,
    cm.data_type
FROM content_metadata cm
WHERE cm.content_id = ? 
  AND cm.metadata_type = 'engagement';

-- Find content by platform-specific ID
SELECT c.*, p.name as platform_name
FROM content c
JOIN platforms p ON c.platform_id = p.id
JOIN content_metadata cm ON c.id = cm.content_id
WHERE cm.metadata_type = 'platform_specific'
  AND cm.metadata_key = 'youtube_video_id'
  AND cm.metadata_value = ?;
```

### 2. **Materialized Views for Performance**

```sql
-- Create views for commonly accessed data
CREATE VIEW content_with_platform AS
SELECT 
    c.*,
    p.name as platform_name,
    p.display_name as platform_display_name
FROM content c
JOIN platforms p ON c.platform_id = p.id
WHERE c.is_deleted = FALSE;

-- View for content with basic metadata
CREATE VIEW content_summary AS
SELECT 
    c.id,
    c.title,
    c.author_name,
    p.name as platform,
    GROUP_CONCAT(
        CASE WHEN cm.metadata_key = 'resolution_height' THEN cm.metadata_value END
    ) as resolution_height,
    GROUP_CONCAT(
        CASE WHEN cm.metadata_key = 'view_count' THEN cm.metadata_value END
    ) as view_count
FROM content c
JOIN platforms p ON c.platform_id = p.id
LEFT JOIN content_metadata cm ON c.id = cm.content_id 
    AND cm.metadata_type IN ('video_specs', 'engagement')
    AND cm.metadata_key IN ('resolution_height', 'view_count')
WHERE c.is_deleted = FALSE
GROUP BY c.id, c.title, c.author_name, p.name;
```

## Storage Size Optimization

### 1. **Data Compression Strategies**

```sql
-- Use efficient storage for JSON data
-- Store commonly used values in lookup tables
CREATE TABLE metadata_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    value_hash TEXT UNIQUE NOT NULL,      -- SHA256 of the value
    value_content TEXT NOT NULL,          -- Actual JSON/large text content
    usage_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Modified content_metadata for large values
ALTER TABLE content_metadata ADD COLUMN value_ref_id INTEGER REFERENCES metadata_values(id);

-- Trigger to handle large values automatically
CREATE TRIGGER handle_large_metadata_values
BEFORE INSERT ON content_metadata
WHEN LENGTH(NEW.metadata_value) > 1000  -- Values larger than 1KB
BEGIN
    INSERT OR IGNORE INTO metadata_values (value_hash, value_content)
    VALUES (
        SUBSTR(HEX(RANDOMBLOB(16)), 1, 32),  -- Simple hash for demo
        NEW.metadata_value
    );
    
    UPDATE metadata_values 
    SET usage_count = usage_count + 1
    WHERE value_content = NEW.metadata_value;
    
    SELECT NEW.metadata_value = NULL;  -- Clear the original value
    SELECT NEW.value_ref_id = (
        SELECT id FROM metadata_values WHERE value_content = NEW.metadata_value
    );
END;
```

This platform-specific metadata structure provides:

1. **Flexible Storage**: Accommodates any platform's unique metadata
2. **Efficient Queries**: Proper indexing for fast lookups
3. **Type Safety**: Data type validation and constraints
4. **Scalability**: Handles large amounts of metadata efficiently
5. **Performance**: Optimized for SQLite with proper indexes and views
6. **Extensibility**: Easy to add new platforms without schema changes 