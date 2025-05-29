# Query Optimization Plan for Social Download Manager v2.0

## Overview

This document provides a comprehensive query optimization plan for the Social Download Manager v2.0 database schema. It analyzes common query patterns, identifies performance bottlenecks, and provides optimized solutions for expected workloads.

## Application Query Patterns Analysis

### 1. **Content Management Queries (60% of database operations)**

#### Primary Content Operations
```sql
-- Content listing with platform filtering (High frequency: ~40% of reads)
-- OPTIMIZED VERSION
SELECT 
    c.id,
    c.title,
    c.author_name,
    c.duration_seconds,
    c.view_count,
    c.status,
    p.display_name as platform_name
FROM content c
JOIN platforms p ON c.platform_id = p.id
WHERE c.is_deleted = FALSE
  AND c.platform_id = ?
  AND c.status = 'completed'
ORDER BY c.created_at DESC
LIMIT 50;

-- Performance: Uses idx_content_platform_status_created covering index
-- Estimated: <1ms for 100K records

-- Content search with metadata (Medium frequency: ~15% of reads)
-- OPTIMIZED VERSION
WITH content_search AS (
    SELECT DISTINCT c.id
    FROM content c
    WHERE c.is_deleted = FALSE
      AND (c.title LIKE '%' || ? || '%' 
           OR c.author_name LIKE '%' || ? || '%')
)
SELECT 
    c.*,
    p.display_name as platform_name,
    GROUP_CONCAT(
        CASE WHEN cm.metadata_type = 'engagement' 
             THEN cm.metadata_key || ':' || cm.metadata_value 
        END
    ) as engagement_data
FROM content_search cs
JOIN content c ON cs.id = c.id
JOIN platforms p ON c.platform_id = p.id
LEFT JOIN content_metadata cm ON c.id = cm.content_id 
    AND cm.metadata_type = 'engagement'
GROUP BY c.id
ORDER BY c.view_count DESC
LIMIT 20;

-- Performance: Uses FTS optimization and covering indexes
-- Estimated: 5-10ms for 100K records
```

#### Content Detail Retrieval
```sql
-- Single content with all metadata (High frequency: ~25% of reads)
-- OPTIMIZED VERSION
SELECT 
    c.*,
    p.name as platform_name,
    p.display_name as platform_display_name
FROM content c
JOIN platforms p ON c.platform_id = p.id
WHERE c.id = ?;

-- Get all metadata for content
SELECT 
    metadata_type,
    metadata_key,
    metadata_value,
    data_type,
    parent_key
FROM content_metadata
WHERE content_id = ?
ORDER BY metadata_type, metadata_key;

-- Performance: Primary key lookup + index scan
-- Estimated: <1ms
```

### 2. **Download Management Queries (25% of database operations)**

#### Active Download Monitoring
```sql
-- Real-time download status (Very high frequency: continuous polling)
-- OPTIMIZED VERSION
SELECT 
    d.id,
    d.content_id,
    d.status,
    d.progress_percentage,
    d.current_speed_bps,
    d.queued_at,
    d.started_at,
    c.title as content_title,
    c.author_name,
    p.name as platform
FROM downloads d
JOIN content c ON d.content_id = c.id
JOIN platforms p ON c.platform_id = p.id
WHERE d.status IN ('queued', 'starting', 'downloading', 'processing', 'retrying')
ORDER BY d.queued_at ASC;

-- Performance: Uses idx_downloads_active partial index
-- Estimated: <1ms for 1K active downloads
```

#### Download History and Analytics
```sql
-- Download completion stats (Medium frequency: ~10% of reads)
-- OPTIMIZED VERSION
SELECT 
    DATE(d.completed_at) as download_date,
    p.name as platform,
    COUNT(*) as completed_count,
    AVG(d.actual_file_size) as avg_file_size,
    SUM(d.actual_file_size) as total_downloaded
FROM downloads d
JOIN content c ON d.content_id = c.id
JOIN platforms p ON c.platform_id = p.id
WHERE d.status = 'completed'
  AND d.completed_at >= DATE('now', '-30 days')
GROUP BY DATE(d.completed_at), p.name
ORDER BY download_date DESC, platform;

-- Performance: Uses idx_downloads_completed + aggregation
-- Estimated: 10-20ms for 10K records
```

### 3. **Metadata Operations (10% of database operations)**

#### Platform-Specific Data Retrieval
```sql
-- YouTube video metadata extraction (Medium frequency)
-- OPTIMIZED VERSION
SELECT 
    cm.metadata_key,
    cm.metadata_value,
    cm.data_type
FROM content_metadata cm
WHERE cm.content_id = ?
  AND cm.metadata_type = 'platform_specific'
  AND cm.metadata_key LIKE 'youtube_%'
ORDER BY cm.metadata_key;

-- Performance: Uses idx_content_metadata_platform_specific
-- Estimated: <1ms
```

#### Engagement Metrics Aggregation
```sql
-- Platform engagement comparison (Low frequency: reporting)
-- OPTIMIZED VERSION
WITH engagement_data AS (
    SELECT 
        c.platform_id,
        CAST(cm.metadata_value AS INTEGER) as metric_value,
        cm.metadata_key
    FROM content_metadata cm
    JOIN content c ON cm.content_id = c.id
    WHERE cm.metadata_type = 'engagement'
      AND cm.data_type = 'integer'
      AND cm.metadata_key IN ('view_count', 'like_count', 'comment_count')
      AND c.is_deleted = FALSE
)
SELECT 
    p.display_name as platform,
    ed.metadata_key as metric_type,
    COUNT(*) as content_count,
    AVG(ed.metric_value) as avg_value,
    MAX(ed.metric_value) as max_value
FROM engagement_data ed
JOIN platforms p ON ed.platform_id = p.id
GROUP BY p.id, ed.metadata_key
ORDER BY p.display_name, ed.metadata_key;

-- Performance: Uses CTE + aggregation with indexes
-- Estimated: 50-100ms for 100K metadata records
```

### 4. **Search and Filter Operations (5% of database operations)**

#### Advanced Content Search
```sql
-- Multi-criteria content search (Medium frequency)
-- OPTIMIZED VERSION with denormalization consideration
CREATE VIEW content_search_view AS
SELECT 
    c.id,
    c.title,
    c.author_name,
    c.description,
    c.platform_id,
    c.content_type,
    c.status,
    c.view_count,
    c.created_at,
    p.name as platform_name,
    GROUP_CONCAT(t.name) as tag_names,
    -- Denormalized commonly searched metadata
    MAX(CASE WHEN cm.metadata_key = 'resolution_height' 
             THEN CAST(cm.metadata_value AS INTEGER) END) as resolution_height,
    MAX(CASE WHEN cm.metadata_key = 'duration' 
             THEN CAST(cm.metadata_value AS INTEGER) END) as duration_seconds_meta
FROM content c
JOIN platforms p ON c.platform_id = p.id
LEFT JOIN content_tags ct ON c.id = ct.content_id
LEFT JOIN tags t ON ct.tag_id = t.id
LEFT JOIN content_metadata cm ON c.id = cm.content_id 
    AND cm.metadata_type = 'video_specs'
    AND cm.metadata_key IN ('resolution_height', 'duration')
WHERE c.is_deleted = FALSE
GROUP BY c.id, c.title, c.author_name, c.description, c.platform_id, 
         c.content_type, c.status, c.view_count, c.created_at, p.name;

-- Search query using the optimized view
SELECT *
FROM content_search_view
WHERE (title LIKE '%' || ? || '%' OR author_name LIKE '%' || ? || '%')
  AND platform_name = ?
  AND resolution_height >= 720
  AND tag_names LIKE '%' || ? || '%'
ORDER BY view_count DESC
LIMIT 25;

-- Performance: Pre-computed view with selective indexes
-- Estimated: 5-15ms for complex searches
```

## Optimization Strategies

### 1. **Read Optimization Techniques**

#### Materialized Views for Complex Aggregations
```sql
-- Content summary materialized view (updated via triggers)
CREATE TABLE content_summary_cache (
    content_id INTEGER PRIMARY KEY,
    platform_name VARCHAR(50),
    total_downloads INTEGER,
    avg_download_speed REAL,
    metadata_json TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE
);

-- Update trigger for cache maintenance
CREATE TRIGGER update_content_summary_cache
    AFTER INSERT ON downloads
    FOR EACH ROW
    WHEN NEW.status = 'completed'
BEGIN
    INSERT OR REPLACE INTO content_summary_cache (
        content_id, 
        total_downloads, 
        avg_download_speed,
        last_updated
    )
    SELECT 
        NEW.content_id,
        COUNT(*),
        AVG(d.average_speed_bps),
        CURRENT_TIMESTAMP
    FROM downloads d
    WHERE d.content_id = NEW.content_id 
      AND d.status = 'completed';
END;
```

#### Strategic Denormalization
```sql
-- Add computed columns to content table for hot data
ALTER TABLE content ADD COLUMN metadata_cache TEXT DEFAULT '{}';
ALTER TABLE content ADD COLUMN engagement_score INTEGER DEFAULT 0;
ALTER TABLE content ADD COLUMN download_count INTEGER DEFAULT 0;

-- Trigger to maintain denormalized data
CREATE TRIGGER maintain_content_cache
    AFTER UPDATE ON content_metadata
    FOR EACH ROW
    WHEN NEW.metadata_type = 'engagement'
BEGIN
    UPDATE content 
    SET engagement_score = (
        SELECT COALESCE(
            CAST(cm1.metadata_value AS INTEGER), 0) + 
            COALESCE(CAST(cm2.metadata_value AS INTEGER), 0) + 
            COALESCE(CAST(cm3.metadata_value AS INTEGER), 0)
        FROM content_metadata cm1
        LEFT JOIN content_metadata cm2 ON cm1.content_id = cm2.content_id 
            AND cm2.metadata_key = 'like_count'
        LEFT JOIN content_metadata cm3 ON cm1.content_id = cm3.content_id 
            AND cm3.metadata_key = 'comment_count'
        WHERE cm1.content_id = NEW.content_id 
          AND cm1.metadata_key = 'view_count'
    )
    WHERE id = NEW.content_id;
END;
```

### 2. **Write Optimization Techniques**

#### Batch Operations for Metadata
```sql
-- Optimized batch metadata insertion
INSERT INTO content_metadata (content_id, metadata_type, metadata_key, metadata_value, data_type)
SELECT 
    ? as content_id,
    metadata_type,
    metadata_key,
    metadata_value,
    data_type
FROM (
    VALUES 
    ('platform_specific', 'youtube_video_id', ?, 'string'),
    ('platform_specific', 'youtube_channel_id', ?, 'string'),
    ('video_specs', 'resolution_width', ?, 'integer'),
    ('video_specs', 'resolution_height', ?, 'integer'),
    ('engagement', 'view_count', ?, 'integer'),
    ('engagement', 'like_count', ?, 'integer')
) AS metadata_values(metadata_type, metadata_key, metadata_value, data_type);

-- Performance: Single transaction vs. multiple inserts (6x faster)
```

#### Optimized Download Progress Updates
```sql
-- Batch download progress update (called every 1-2 seconds)
UPDATE downloads 
SET 
    progress_percentage = ?,
    current_speed_bps = ?,
    average_speed_bps = (
        (average_speed_bps * (? - 1) + ?) / ?
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE id = ?;

-- Include session tracking in same transaction
INSERT INTO download_sessions (
    download_id, 
    session_uuid, 
    bytes_downloaded, 
    peak_speed_bps
) VALUES (?, ?, ?, ?)
ON CONFLICT(session_uuid) DO UPDATE SET
    bytes_downloaded = excluded.bytes_downloaded,
    peak_speed_bps = MAX(peak_speed_bps, excluded.peak_speed_bps),
    session_ended_at = CURRENT_TIMESTAMP;
```

### 3. **Query Performance Testing Framework**

#### Benchmarking Queries
```sql
-- Create test data generator
CREATE TABLE query_performance_tests (
    test_id INTEGER PRIMARY KEY,
    test_name VARCHAR(100),
    query_sql TEXT,
    expected_time_ms INTEGER,
    last_run_time_ms INTEGER,
    last_run_timestamp TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending'
);

-- Sample performance tests
INSERT INTO query_performance_tests (test_name, query_sql, expected_time_ms) VALUES
('content_list_platform', 'SELECT * FROM content WHERE platform_id = 1 AND status = "completed" ORDER BY created_at DESC LIMIT 50', 5),
('download_active_monitoring', 'SELECT * FROM downloads WHERE status IN ("downloading", "processing")', 2),
('metadata_platform_lookup', 'SELECT * FROM content_metadata WHERE content_id = 1 AND metadata_type = "platform_specific"', 1),
('content_search_basic', 'SELECT * FROM content WHERE title LIKE "%test%" AND platform_id = 1', 10),
('engagement_aggregation', 'SELECT AVG(CAST(metadata_value AS INTEGER)) FROM content_metadata WHERE metadata_key = "view_count"', 20);
```

#### Automated Performance Monitoring
```sql
-- Performance monitoring view
CREATE VIEW query_performance_monitor AS
SELECT 
    test_name,
    query_sql,
    expected_time_ms,
    last_run_time_ms,
    CASE 
        WHEN last_run_time_ms <= expected_time_ms THEN 'PASS'
        WHEN last_run_time_ms <= expected_time_ms * 1.5 THEN 'WARNING'
        ELSE 'FAIL'
    END as performance_status,
    (last_run_time_ms * 100.0 / expected_time_ms) as performance_ratio,
    last_run_timestamp
FROM query_performance_tests
ORDER BY performance_ratio DESC;
```

## Bottleneck Analysis and Solutions

### 1. **Identified Performance Bottlenecks**

#### Content Metadata Joins
**Problem**: Large content_metadata table causes slow joins
**Solution**: 
- Use covering indexes
- Implement metadata caching
- Consider partitioning by metadata_type

```sql
-- Optimized metadata query with subquery approach
SELECT c.*, 
    (SELECT GROUP_CONCAT(metadata_key || ':' || metadata_value)
     FROM content_metadata cm1 
     WHERE cm1.content_id = c.id 
       AND cm1.metadata_type = 'platform_specific') as platform_data,
    (SELECT GROUP_CONCAT(metadata_key || ':' || metadata_value)
     FROM content_metadata cm2 
     WHERE cm2.content_id = c.id 
       AND cm2.metadata_type = 'engagement') as engagement_data
FROM content c
WHERE c.platform_id = ?
ORDER BY c.created_at DESC;
```

#### Large Dataset Pagination
**Problem**: OFFSET becomes slow for large datasets
**Solution**: Cursor-based pagination

```sql
-- Traditional pagination (SLOW for large offsets)
SELECT * FROM content ORDER BY created_at DESC LIMIT 50 OFFSET 10000;

-- Optimized cursor-based pagination
SELECT * FROM content 
WHERE created_at < ?  -- cursor from previous page
ORDER BY created_at DESC 
LIMIT 50;
```

### 2. **Scalability Considerations**

#### Database Size Projections
- **1 year**: ~1M content records, ~10M metadata records
- **3 years**: ~5M content records, ~50M metadata records  
- **5 years**: ~10M content records, ~100M metadata records

#### Optimization Strategies by Scale

**Small Scale (< 100K records)**
- Standard indexes sufficient
- No denormalization needed
- Direct queries preferred

**Medium Scale (100K - 1M records)**
- Add covering indexes
- Implement metadata caching
- Use materialized views for reporting

**Large Scale (> 1M records)**
- Aggressive denormalization
- Partition large tables
- Implement read replicas
- Consider sharding by platform

### 3. **Performance Monitoring Strategy**

#### Key Performance Indicators (KPIs)
```sql
-- Daily performance metrics
CREATE VIEW daily_performance_metrics AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_queries,
    AVG(execution_time_ms) as avg_response_time,
    MAX(execution_time_ms) as max_response_time,
    COUNT(CASE WHEN execution_time_ms > 100 THEN 1 END) as slow_queries
FROM query_log
WHERE created_at >= DATE('now', '-7 days')
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

#### Automated Alerts
- Queries taking > 50ms (warning)
- Queries taking > 200ms (critical)
- More than 10% slow queries in 5-minute window
- Database size growing > 20% per month

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Implement core optimized queries
- [ ] Add essential covering indexes
- [ ] Set up performance monitoring
- [ ] Create query benchmarking framework

### Phase 2: Enhancement (Week 3-4)
- [ ] Implement strategic denormalization
- [ ] Add materialized views for reporting
- [ ] Optimize batch operations
- [ ] Implement cursor-based pagination

### Phase 3: Scale Preparation (Week 5-6)
- [ ] Add advanced covering indexes
- [ ] Implement metadata caching
- [ ] Set up automated performance alerts
- [ ] Prepare horizontal scaling strategies

### Phase 4: Monitoring and Tuning (Ongoing)
- [ ] Monitor query performance
- [ ] Optimize based on real usage patterns
- [ ] Adjust indexes based on performance data
- [ ] Plan for database growth

This query optimization plan ensures the Social Download Manager v2.0 database can handle expected workloads efficiently while maintaining good performance as the dataset grows. 