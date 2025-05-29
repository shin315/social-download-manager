# Social Download Manager v2.0 Database Schema Documentation

## Overview

This document provides comprehensive documentation for the Social Download Manager v2.0 database schema, designed to support multi-platform content downloading with improved performance, scalability, and maintainability.

### Key Features
- **Multi-platform support**: YouTube, TikTok, Instagram, and extensible for more
- **Flexible metadata system**: Platform-specific data without schema changes
- **Comprehensive download tracking**: Sessions, errors, quality options
- **Performance optimized**: 50+ strategic indexes, query optimization
- **Data integrity**: Multi-layer validation with constraints and triggers

## Schema Architecture

### Design Principles
1. **3rd Normal Form (3NF)**: Eliminates data redundancy
2. **Platform Agnostic Core**: Common attributes separated from platform-specific data
3. **Flexible Metadata**: Key-value storage for extensibility
4. **Audit Trail**: Complete tracking of changes and operations
5. **Performance First**: Indexes and constraints optimized for common queries

### Entity Relationship Overview
```
platforms (1) ─── (N) content (1) ─── (N) content_metadata
                      │                      
                      ├── (N) downloads (1) ─── (N) download_sessions
                      │                   │
                      │                   └── (N) download_errors
                      │
                      ├── (N) quality_options
                      │
                      └── (N) content_tags (N) ─── (1) tags
```

## Table Reference

### 1. platforms
**Purpose**: Reference table for supported platforms

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER PRIMARY KEY | AUTO_INCREMENT | Unique platform identifier |
| name | VARCHAR(50) | UNIQUE, NOT NULL | Platform identifier (lowercase) |
| display_name | VARCHAR(100) | NOT NULL | Human-readable platform name |
| base_url | VARCHAR(255) | NULL | Platform base URL |
| supported_content_types | TEXT | JSON | Supported content types array |
| is_active | BOOLEAN | DEFAULT TRUE | Platform status |
| metadata | TEXT | JSON | Platform-specific configuration |
| created_at | TIMESTAMP | DEFAULT NOW | Record creation time |
| updated_at | TIMESTAMP | DEFAULT NOW | Last update time |

**Indexes**: `uq_platforms_name_normalized`, `idx_platforms_active`

### 2. content
**Purpose**: Core content entity (platform-agnostic)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER PRIMARY KEY | AUTO_INCREMENT | Unique content identifier |
| platform_id | INTEGER | FK platforms(id), NOT NULL | Platform reference |
| original_url | TEXT | NOT NULL | Source URL |
| canonical_url | TEXT | NULL | Canonical/cleaned URL |
| platform_content_id | VARCHAR(255) | NULL | Platform's internal ID |
| title | VARCHAR(500) | NULL | Content title |
| description | TEXT | NULL | Content description |
| content_type | VARCHAR(50) | DEFAULT 'video' | Content type |
| status | VARCHAR(50) | DEFAULT 'pending' | Processing status |
| author_name | VARCHAR(255) | NULL | Content creator name |
| author_id | VARCHAR(255) | NULL | Platform author ID |
| published_at | TIMESTAMP | NULL | Original publish date |
| duration_seconds | INTEGER | NULL | Content duration |
| file_size_bytes | BIGINT | NULL | File size |
| view_count | BIGINT | DEFAULT 0 | View statistics |
| like_count | BIGINT | DEFAULT 0 | Like statistics |
| comment_count | BIGINT | DEFAULT 0 | Comment statistics |
| share_count | BIGINT | DEFAULT 0 | Share statistics |
| local_file_path | TEXT | NULL | Downloaded file path |
| thumbnail_path | TEXT | NULL | Thumbnail file path |
| is_deleted | BOOLEAN | DEFAULT FALSE | Soft delete flag |
| created_at | TIMESTAMP | DEFAULT NOW | Record creation |
| updated_at | TIMESTAMP | DEFAULT NOW | Last update |

**Key Indexes**: 
- `uq_content_platform_url` (platform_id, original_url)
- `idx_content_platform_status_created` (platform_id, status, created_at)
- `idx_content_search_fields` (title, author_name)

### 3. content_metadata
**Purpose**: Flexible platform-specific metadata storage

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER PRIMARY KEY | AUTO_INCREMENT | Unique metadata ID |
| content_id | INTEGER | FK content(id), NOT NULL | Content reference |
| metadata_type | VARCHAR(100) | NOT NULL | Metadata category |
| metadata_key | VARCHAR(255) | NOT NULL | Metadata key name |
| metadata_value | TEXT | NULL | Metadata value |
| data_type | VARCHAR(20) | DEFAULT 'string' | Value data type |
| parent_key | VARCHAR(255) | NULL | Hierarchical parent |
| created_at | TIMESTAMP | DEFAULT NOW | Creation time |
| updated_at | TIMESTAMP | DEFAULT NOW | Update time |

**Metadata Types**:
- `platform_specific`: Platform unique data
- `video_specs`: Technical specifications
- `engagement`: Social metrics
- `quality`: Quality information

### 4. downloads
**Purpose**: Download tracking and management

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER PRIMARY KEY | AUTO_INCREMENT | Download ID |
| content_id | INTEGER | FK content(id), NOT NULL | Content reference |
| status | VARCHAR(50) | DEFAULT 'queued' | Download status |
| progress_percentage | DECIMAL(5,2) | DEFAULT 0.00 | Progress (0-100) |
| current_speed_bps | BIGINT | NULL | Current speed |
| average_speed_bps | BIGINT | NULL | Average speed |
| output_directory | VARCHAR(500) | NOT NULL | Output path |
| final_file_path | TEXT | NULL | Final file location |
| actual_file_size | BIGINT | NULL | Actual downloaded size |
| retry_count | INTEGER | DEFAULT 0 | Retry attempts |
| max_retries | INTEGER | DEFAULT 3 | Maximum retries |
| error_count | INTEGER | DEFAULT 0 | Error count |
| last_error_message | TEXT | NULL | Last error message |
| download_options | TEXT | JSON | Download configuration |
| queued_at | TIMESTAMP | DEFAULT NOW | Queue time |
| started_at | TIMESTAMP | NULL | Start time |
| completed_at | TIMESTAMP | NULL | Completion time |

**Status Values**: `queued`, `starting`, `downloading`, `processing`, `completed`, `failed`, `cancelled`, `paused`, `retrying`

### 5. download_sessions
**Purpose**: Detailed session tracking for downloads

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER PRIMARY KEY | AUTO_INCREMENT | Session ID |
| download_id | INTEGER | FK downloads(id), NOT NULL | Download reference |
| session_uuid | VARCHAR(36) | UNIQUE, NOT NULL | Session identifier |
| session_type | VARCHAR(50) | DEFAULT 'standard' | Session type |
| session_status | VARCHAR(50) | DEFAULT 'active' | Session status |
| bytes_downloaded | BIGINT | DEFAULT 0 | Bytes transferred |
| total_bytes | BIGINT | NULL | Total expected bytes |
| chunks_completed | INTEGER | DEFAULT 0 | Completed chunks |
| total_chunks | INTEGER | NULL | Total chunks |
| peak_speed_bps | BIGINT | NULL | Peak transfer speed |
| average_speed_bps | BIGINT | NULL | Average speed |
| connection_count | INTEGER | NULL | Parallel connections |
| headers | TEXT | JSON | HTTP headers |
| session_started_at | TIMESTAMP | DEFAULT NOW | Session start |
| session_ended_at | TIMESTAMP | NULL | Session end |

## Common Query Patterns

### Content Listing
```sql
-- Get recent content by platform
SELECT c.*, p.display_name as platform_name
FROM content c
JOIN platforms p ON c.platform_id = p.id
WHERE c.is_deleted = FALSE
  AND p.name = 'youtube'
ORDER BY c.created_at DESC
LIMIT 50;
```

### Metadata Retrieval
```sql
-- Get all metadata for content
SELECT metadata_type, metadata_key, metadata_value, data_type
FROM content_metadata
WHERE content_id = ?
ORDER BY metadata_type, metadata_key;
```

### Download Monitoring
```sql
-- Active downloads with progress
SELECT d.*, c.title, p.name as platform
FROM downloads d
JOIN content c ON d.content_id = c.id
JOIN platforms p ON c.platform_id = p.id
WHERE d.status IN ('downloading', 'processing')
ORDER BY d.started_at;
```

## Performance Guidelines

### Indexing Strategy
- **Primary Operations**: Covering indexes for content listing, search, and filtering
- **Join Optimization**: Foreign key indexes on all relationship columns
- **Search Performance**: FTS indexes for text search operations
- **Partial Indexes**: SQLite-specific optimizations for filtered queries

### Query Optimization Tips
1. Use covering indexes to avoid table lookups
2. Implement cursor-based pagination for large datasets
3. Leverage partial indexes for status-based filtering
4. Use CTEs for complex aggregations
5. Batch metadata operations for better performance

## Migration and Maintenance

### Schema Versioning
- Migrations tracked in `schema_migrations` table
- Incremental version-controlled updates
- Rollback procedures for failed migrations

### Data Integrity
- Multi-layer validation (database + application)
- Automated integrity monitoring
- Repair procedures for common issues

### Backup Strategy
- Full database backups before schema changes
- Incremental backups for data protection
- Migration testing in staging environment

---

**Schema Version**: 2.0.0  
**Last Updated**: 2025-05-29  
**Compatible With**: SQLite 3.35+, Python 3.8+

For implementation details, see:
- [Database Schema Design](database_schema_v2_design.md)
- [Platform Metadata Schemas](platform_metadata_schemas.md)
- [Migration Path Definition](migration_path_definition.md)
- [Validation Rules Implementation](validation_rules_implementation.md) 