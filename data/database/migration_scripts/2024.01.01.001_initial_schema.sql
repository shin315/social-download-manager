-- version: 2024.01.01.001
-- name: initial_schema
-- description: Create initial database schema with content, downloads, and related tables
-- dependencies: 
-- tags: initial, schema, foundation

-- Enable foreign keys for this session
PRAGMA foreign_keys = ON;

-- Create content table
CREATE TABLE IF NOT EXISTS content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    platform TEXT NOT NULL,
    content_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    
    -- Content metadata
    title TEXT,
    description TEXT,
    author TEXT,
    author_id TEXT,
    thumbnail_url TEXT,
    
    -- Platform identifiers
    platform_id TEXT,
    platform_url TEXT,
    
    -- Content properties
    duration REAL,
    file_size INTEGER,
    format TEXT,
    quality TEXT,
    
    -- Download information
    local_path TEXT,
    download_progress REAL DEFAULT 0.0,
    download_speed REAL,
    
    -- Content stats
    view_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    share_count INTEGER,
    
    -- Publication info
    published_at TEXT,
    
    -- Additional data
    available_qualities TEXT,  -- JSON array
    hashtags TEXT,             -- JSON array
    mentions TEXT,             -- JSON array
    
    -- Base entity fields
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    is_deleted INTEGER DEFAULT 0,
    metadata TEXT              -- JSON object
);

-- Create downloads table
CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL,
    session_id INTEGER,
    
    -- Download configuration
    url TEXT NOT NULL,
    quality TEXT,
    format TEXT,
    output_directory TEXT DEFAULT 'downloads',
    
    -- Status and progress
    status TEXT NOT NULL DEFAULT 'queued',
    progress_percentage REAL DEFAULT 0.0,
    download_speed REAL,
    
    -- File information
    filename TEXT,
    file_size INTEGER,
    file_path TEXT,
    
    -- Timing
    queued_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    
    -- Error tracking
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Base entity fields
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    is_deleted INTEGER DEFAULT 0,
    metadata TEXT,
    
    -- Foreign key constraints
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE
);

-- Create download_sessions table
CREATE TABLE IF NOT EXISTS download_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    
    -- Download configuration
    quality TEXT,
    format TEXT,
    output_path TEXT,
    
    -- Progress tracking (stored as JSON)
    progress TEXT,
    
    -- Timing information
    started_at TEXT,
    completed_at TEXT,
    
    -- Error handling
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Session metadata
    downloader_type TEXT,
    session_config TEXT,
    
    -- Base entity fields
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    is_deleted INTEGER DEFAULT 0,
    metadata TEXT,
    
    -- Foreign key constraints
    FOREIGN KEY (content_id) REFERENCES content(id) ON DELETE CASCADE
);

-- Create download_errors table
CREATE TABLE IF NOT EXISTS download_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    download_id INTEGER NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    error_code TEXT,
    stack_trace TEXT,
    retry_count INTEGER DEFAULT 0,
    can_retry INTEGER DEFAULT 1,
    
    -- Base entity fields
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    is_deleted INTEGER DEFAULT 0,
    metadata TEXT,
    
    -- Foreign key constraints
    FOREIGN KEY (download_id) REFERENCES downloads(id) ON DELETE CASCADE
);

-- DOWN
-- Drop tables in reverse order to respect foreign key constraints
DROP TABLE IF EXISTS download_errors;
DROP TABLE IF EXISTS download_sessions;
DROP TABLE IF EXISTS downloads;
DROP TABLE IF EXISTS content; 