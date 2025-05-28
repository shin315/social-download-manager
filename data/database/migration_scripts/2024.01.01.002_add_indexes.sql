-- version: 2024.01.01.002
-- name: add_indexes
-- description: Add database indexes for performance optimization
-- dependencies: 2024.01.01.001
-- tags: performance, indexes, optimization

-- Content table indexes
CREATE INDEX IF NOT EXISTS idx_content_platform ON content(platform);
CREATE INDEX IF NOT EXISTS idx_content_status ON content(status);
CREATE INDEX IF NOT EXISTS idx_content_type ON content(content_type);
CREATE INDEX IF NOT EXISTS idx_content_author ON content(author);
CREATE INDEX IF NOT EXISTS idx_content_created ON content(created_at);
CREATE INDEX IF NOT EXISTS idx_content_url ON content(url);
CREATE INDEX IF NOT EXISTS idx_content_platform_id ON content(platform_id);

-- Create unique constraint for platform + platform_id combination
CREATE UNIQUE INDEX IF NOT EXISTS idx_content_platform_unique 
ON content(platform, platform_id) 
WHERE platform_id IS NOT NULL;

-- Downloads table indexes
CREATE INDEX IF NOT EXISTS idx_downloads_content_id ON downloads(content_id);
CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status);
CREATE INDEX IF NOT EXISTS idx_downloads_queued_at ON downloads(queued_at);
CREATE INDEX IF NOT EXISTS idx_downloads_completed_at ON downloads(completed_at);
CREATE INDEX IF NOT EXISTS idx_downloads_url ON downloads(url);

-- Download sessions table indexes
CREATE INDEX IF NOT EXISTS idx_sessions_content_id ON download_sessions(content_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON download_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON download_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_sessions_downloader_type ON download_sessions(downloader_type);

-- Download errors table indexes
CREATE INDEX IF NOT EXISTS idx_errors_download_id ON download_errors(download_id);
CREATE INDEX IF NOT EXISTS idx_errors_error_type ON download_errors(error_type);
CREATE INDEX IF NOT EXISTS idx_errors_created_at ON download_errors(created_at);
CREATE INDEX IF NOT EXISTS idx_errors_can_retry ON download_errors(can_retry);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_content_platform_status ON content(platform, status);
CREATE INDEX IF NOT EXISTS idx_content_status_created ON content(status, created_at);
CREATE INDEX IF NOT EXISTS idx_downloads_status_queued ON downloads(status, queued_at);

-- DOWN
-- Drop indexes in reverse order
DROP INDEX IF EXISTS idx_downloads_status_queued;
DROP INDEX IF EXISTS idx_content_status_created;
DROP INDEX IF EXISTS idx_content_platform_status;

DROP INDEX IF EXISTS idx_errors_can_retry;
DROP INDEX IF EXISTS idx_errors_created_at;
DROP INDEX IF EXISTS idx_errors_error_type;
DROP INDEX IF EXISTS idx_errors_download_id;

DROP INDEX IF EXISTS idx_sessions_downloader_type;
DROP INDEX IF EXISTS idx_sessions_started_at;
DROP INDEX IF EXISTS idx_sessions_status;
DROP INDEX IF EXISTS idx_sessions_content_id;

DROP INDEX IF EXISTS idx_downloads_url;
DROP INDEX IF EXISTS idx_downloads_completed_at;
DROP INDEX IF EXISTS idx_downloads_queued_at;
DROP INDEX IF EXISTS idx_downloads_status;
DROP INDEX IF EXISTS idx_downloads_content_id;

DROP INDEX IF EXISTS idx_content_platform_unique;
DROP INDEX IF EXISTS idx_content_platform_id;
DROP INDEX IF EXISTS idx_content_url;
DROP INDEX IF EXISTS idx_content_created;
DROP INDEX IF EXISTS idx_content_author;
DROP INDEX IF EXISTS idx_content_type;
DROP INDEX IF EXISTS idx_content_status;
DROP INDEX IF EXISTS idx_content_platform; 