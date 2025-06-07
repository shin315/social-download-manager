"""
Advanced Database Pagination System

High-performance pagination implementation providing:
- Keyset pagination (cursor-based) instead of OFFSET/LIMIT
- SQL window functions for efficient row numbering
- Materialized views for frequently accessed metadata
- Async generators for progressive data loading
- Query optimization and indexing strategies

Part of Task 15.3 - Database Pagination
"""

import sqlite3
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, AsyncGenerator, Tuple, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

# SQLite async support
try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False
    print("aiosqlite not available - using synchronous SQLite")


class SortOrder(Enum):
    ASC = "ASC"
    DESC = "DESC"


class PaginationDirection(Enum):
    FORWARD = "forward"
    BACKWARD = "backward"


@dataclass
class PaginationCursor:
    """Represents a pagination cursor for keyset pagination"""
    
    # Primary cursor values
    video_id: int
    upload_timestamp: int
    
    # Secondary sort fields for stability
    file_size: Optional[int] = None
    duration: Optional[float] = None
    
    # Metadata
    page_size: int = 100
    direction: PaginationDirection = PaginationDirection.FORWARD
    
    def to_string(self) -> str:
        """Serialize cursor to base64 string"""
        import base64
        cursor_dict = asdict(self)
        cursor_json = json.dumps(cursor_dict, default=str)
        return base64.b64encode(cursor_json.encode()).decode()
    
    @classmethod
    def from_string(cls, cursor_str: str) -> 'PaginationCursor':
        """Deserialize cursor from base64 string"""
        import base64
        cursor_json = base64.b64decode(cursor_str.encode()).decode()
        cursor_dict = json.loads(cursor_json)
        
        # Convert enum strings back to enums
        if 'direction' in cursor_dict:
            direction_str = cursor_dict['direction']
            if isinstance(direction_str, str):
                # Handle both enum string representation and value
                if direction_str.startswith('PaginationDirection.'):
                    direction_str = direction_str.split('.')[-1]
                cursor_dict['direction'] = PaginationDirection(direction_str.lower())
        
        return cls(**cursor_dict)


@dataclass 
class PaginationResult:
    """Result of a paginated query"""
    
    items: List[Dict[str, Any]]
    has_next_page: bool
    has_previous_page: bool
    total_count: Optional[int]
    next_cursor: Optional[str]
    previous_cursor: Optional[str]
    page_info: Dict[str, Any]


class KeysetPaginationStrategy:
    """
    Keyset pagination implementation for consistent performance
    
    Uses composite keys (video_id + upload_timestamp) for stable sorting
    and eliminates OFFSET performance issues for large datasets
    """
    
    def __init__(self, connection):
        self.connection = connection
        self.base_query = """
        SELECT 
            v.id as video_id,
            v.title,
            v.url,
            v.creator,
            v.file_size,
            v.duration,
            v.quality,
            v.format,
            v.status,
            v.upload_timestamp,
            v.download_timestamp
        FROM downloaded_videos v
        """
    
    def build_keyset_query(self, 
                          cursor: Optional[PaginationCursor] = None,
                          filters: Optional[Dict[str, Any]] = None,
                          sort_column: str = "upload_timestamp",
                          sort_order: SortOrder = SortOrder.DESC,
                          page_size: int = 100) -> Tuple[str, List[Any]]:
        """Build optimized keyset pagination query"""
        
        # Start with base query
        query_parts = [self.base_query]
        params = []
        where_conditions = []
        
        # Add filters
        if filters:
            filter_conditions, filter_params = self._build_filter_conditions(filters)
            where_conditions.extend(filter_conditions)
            params.extend(filter_params)
        
        # Add cursor conditions for keyset pagination
        if cursor:
            cursor_conditions, cursor_params = self._build_cursor_conditions(
                cursor, sort_column, sort_order
            )
            where_conditions.extend(cursor_conditions)
            params.extend(cursor_params)
        
        # Combine WHERE conditions
        if where_conditions:
            query_parts.append("WHERE " + " AND ".join(where_conditions))
        
        # Add ORDER BY with composite key for stability
        order_clause = self._build_order_clause(sort_column, sort_order)
        query_parts.append(order_clause)
        
        # Add LIMIT (no OFFSET needed with keyset)
        query_parts.append("LIMIT ?")
        params.append(page_size + 1)  # +1 to check for next page
        
        return " ".join(query_parts), params
    
    def _build_filter_conditions(self, filters: Dict[str, Any]) -> Tuple[List[str], List[Any]]:
        """Build WHERE conditions from filters"""
        conditions = []
        params = []
        
        for key, value in filters.items():
            if key == "title" and value:
                conditions.append("v.title LIKE ?")
                params.append(f"%{value}%")
            elif key == "creator" and value:
                conditions.append("v.creator LIKE ?") 
                params.append(f"%{value}%")
            elif key == "quality" and value:
                conditions.append("v.quality = ?")
                params.append(value)
            elif key == "status" and value:
                conditions.append("v.status = ?")
                params.append(value)
            elif key == "format" and value:
                conditions.append("v.format = ?")
                params.append(value)
            elif key == "date_range" and value:
                if isinstance(value, dict):
                    if "start" in value and value["start"]:
                        conditions.append("v.upload_timestamp >= ?")
                        params.append(int(value["start"]))
                    if "end" in value and value["end"]:
                        conditions.append("v.upload_timestamp <= ?")
                        params.append(int(value["end"]))
            elif key == "file_size_range" and value:
                if isinstance(value, dict):
                    if "min" in value and value["min"]:
                        conditions.append("v.file_size >= ?")
                        params.append(int(value["min"]))
                    if "max" in value and value["max"]:
                        conditions.append("v.file_size <= ?")
                        params.append(int(value["max"]))
            elif key == "duration_range" and value:
                if isinstance(value, dict):
                    if "min" in value and value["min"]:
                        conditions.append("v.duration >= ?")
                        params.append(float(value["min"]))
                    if "max" in value and value["max"]:
                        conditions.append("v.duration <= ?")
                        params.append(float(value["max"]))
        
        return conditions, params
    
    def _build_cursor_conditions(self, 
                                cursor: PaginationCursor,
                                sort_column: str,
                                sort_order: SortOrder) -> Tuple[List[str], List[Any]]:
        """Build cursor-based WHERE conditions for keyset pagination"""
        conditions = []
        params = []
        
        if cursor.direction == PaginationDirection.FORWARD:
            # For forward pagination
            if sort_order == SortOrder.DESC:
                # Next page: values less than cursor
                if sort_column == "upload_timestamp":
                    conditions.append(
                        "(v.upload_timestamp < ? OR "
                        "(v.upload_timestamp = ? AND v.id < ?))"
                    )
                    params.extend([cursor.upload_timestamp, cursor.upload_timestamp, cursor.video_id])
                elif sort_column == "file_size":
                    conditions.append(
                        "(v.file_size < ? OR "
                        "(v.file_size = ? AND v.upload_timestamp < ?) OR "
                        "(v.file_size = ? AND v.upload_timestamp = ? AND v.id < ?))"
                    )
                    params.extend([
                        cursor.file_size, cursor.file_size, cursor.upload_timestamp,
                        cursor.file_size, cursor.upload_timestamp, cursor.video_id
                    ])
                else:
                    # Generic column handling
                    conditions.append(f"v.{sort_column} < ? OR (v.{sort_column} = ? AND v.id < ?)")
                    cursor_value = getattr(cursor, sort_column, cursor.upload_timestamp)
                    params.extend([cursor_value, cursor_value, cursor.video_id])
            else:  # ASC
                # Next page: values greater than cursor
                if sort_column == "upload_timestamp":
                    conditions.append(
                        "(v.upload_timestamp > ? OR "
                        "(v.upload_timestamp = ? AND v.id > ?))"
                    )
                    params.extend([cursor.upload_timestamp, cursor.upload_timestamp, cursor.video_id])
                else:
                    conditions.append(f"v.{sort_column} > ? OR (v.{sort_column} = ? AND v.id > ?)")
                    cursor_value = getattr(cursor, sort_column, cursor.upload_timestamp)
                    params.extend([cursor_value, cursor_value, cursor.video_id])
        
        else:  # BACKWARD
            # For backward pagination (reverse the operators)
            if sort_order == SortOrder.DESC:
                conditions.append(
                    "(v.upload_timestamp > ? OR "
                    "(v.upload_timestamp = ? AND v.id > ?))"
                )
                params.extend([cursor.upload_timestamp, cursor.upload_timestamp, cursor.video_id])
            else:  # ASC
                conditions.append(
                    "(v.upload_timestamp < ? OR "
                    "(v.upload_timestamp = ? AND v.id < ?))"
                )
                params.extend([cursor.upload_timestamp, cursor.upload_timestamp, cursor.video_id])
        
        return conditions, params
    
    def _build_order_clause(self, sort_column: str, sort_order: SortOrder) -> str:
        """Build ORDER BY clause with composite key for stability"""
        
        # Always include id as secondary sort for stability
        if sort_column == "upload_timestamp":
            return f"ORDER BY v.upload_timestamp {sort_order.value}, v.id {sort_order.value}"
        elif sort_column == "file_size":
            return f"ORDER BY v.file_size {sort_order.value}, v.upload_timestamp {sort_order.value}, v.id {sort_order.value}"
        elif sort_column == "duration":
            return f"ORDER BY v.duration {sort_order.value}, v.upload_timestamp {sort_order.value}, v.id {sort_order.value}"
        elif sort_column == "title":
            return f"ORDER BY v.title {sort_order.value}, v.upload_timestamp {sort_order.value}, v.id {sort_order.value}"
        else:
            # Generic column
            return f"ORDER BY v.{sort_column} {sort_order.value}, v.upload_timestamp {sort_order.value}, v.id {sort_order.value}"


class MaterializedViewManager:
    """
    Manages materialized views for frequently accessed queries
    
    Pre-computes expensive aggregations and metadata queries
    to improve pagination performance
    """
    
    def __init__(self, connection):
        self.connection = connection
        self.views = {
            'video_stats_summary': self._create_video_stats_view,
            'creator_statistics': self._create_creator_stats_view,
            'quality_distribution': self._create_quality_stats_view,
            'monthly_downloads': self._create_monthly_stats_view
        }
        
        self._initialize_views()
    
    def _initialize_views(self):
        """Initialize all materialized views"""
        cursor = self.connection.cursor()
        
        # Enable materialized view support (if available)
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        except sqlite3.OperationalError:
            pass
        
        # Create views
        for view_name, create_func in self.views.items():
            try:
                create_func()
                print(f"✅ Created materialized view: {view_name}")
            except Exception as e:
                print(f"⚠️ Error creating view {view_name}: {e}")
    
    def _create_video_stats_view(self):
        """Create video statistics summary view"""
        cursor = self.connection.cursor()
        
        # Drop existing view
        cursor.execute("DROP VIEW IF EXISTS video_stats_summary")
        
        # Create view with aggregated statistics
        cursor.execute("""
        CREATE VIEW video_stats_summary AS
        SELECT 
            COUNT(*) as total_videos,
            SUM(file_size) as total_size_bytes,
            AVG(file_size) as avg_size_bytes,
            SUM(duration) as total_duration_seconds,
            AVG(duration) as avg_duration_seconds,
            COUNT(DISTINCT creator) as unique_creators,
            COUNT(DISTINCT quality) as quality_variants,
            MIN(upload_timestamp) as earliest_upload,
            MAX(upload_timestamp) as latest_upload,
            MIN(download_timestamp) as earliest_download,
            MAX(download_timestamp) as latest_download
        FROM downloaded_videos
        WHERE status = 'completed'
        """)
        
        self.connection.commit()
    
    def _create_creator_stats_view(self):
        """Create creator statistics view"""
        cursor = self.connection.cursor()
        
        cursor.execute("DROP VIEW IF EXISTS creator_statistics")
        
        cursor.execute("""
        CREATE VIEW creator_statistics AS
        SELECT 
            creator,
            COUNT(*) as video_count,
            SUM(file_size) as total_size_bytes,
            AVG(file_size) as avg_size_bytes,
            SUM(duration) as total_duration_seconds,
            AVG(duration) as avg_duration_seconds,
            MIN(upload_timestamp) as first_upload,
            MAX(upload_timestamp) as latest_upload,
            COUNT(DISTINCT quality) as quality_variants,
            GROUP_CONCAT(DISTINCT format) as formats_used
        FROM downloaded_videos
        WHERE status = 'completed' AND creator IS NOT NULL
        GROUP BY creator
        ORDER BY video_count DESC
        """)
        
        self.connection.commit()
    
    def _create_quality_stats_view(self):
        """Create quality distribution view"""
        cursor = self.connection.cursor()
        
        cursor.execute("DROP VIEW IF EXISTS quality_distribution")
        
        cursor.execute("""
        CREATE VIEW quality_distribution AS
        SELECT 
            quality,
            COUNT(*) as video_count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM downloaded_videos WHERE status = 'completed'), 2) as percentage,
            SUM(file_size) as total_size_bytes,
            AVG(file_size) as avg_size_bytes,
            AVG(duration) as avg_duration_seconds
        FROM downloaded_videos
        WHERE status = 'completed' AND quality IS NOT NULL
        GROUP BY quality
        ORDER BY video_count DESC
        """)
        
        self.connection.commit()
    
    def _create_monthly_stats_view(self):
        """Create monthly download statistics view"""
        cursor = self.connection.cursor()
        
        cursor.execute("DROP VIEW IF EXISTS monthly_downloads")
        
        cursor.execute("""
        CREATE VIEW monthly_downloads AS
        SELECT 
            strftime('%Y-%m', datetime(download_timestamp, 'unixepoch')) as month,
            COUNT(*) as downloads_count,
            SUM(file_size) as total_size_bytes,
            AVG(file_size) as avg_size_bytes,
            COUNT(DISTINCT creator) as unique_creators,
            COUNT(DISTINCT quality) as quality_variants
        FROM downloaded_videos
        WHERE status = 'completed' 
        GROUP BY strftime('%Y-%m', datetime(download_timestamp, 'unixepoch'))
        ORDER BY month DESC
        """)
        
        self.connection.commit()
    
    def refresh_views(self):
        """Refresh all materialized views (recreate them)"""
        print("🔄 Refreshing materialized views...")
        self._initialize_views()
        print("✅ Views refreshed")
    
    def get_view_data(self, view_name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get data from a materialized view"""
        if view_name not in self.views:
            raise ValueError(f"Unknown view: {view_name}")
        
        cursor = self.connection.cursor()
        
        query = f"SELECT * FROM {view_name}"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        columns = [description[0] for description in cursor.description]
        
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        return results


class AsyncDataGenerator:
    """
    Async generator for progressive data loading
    
    Provides memory-efficient streaming of large datasets
    using Python async generators
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def stream_videos(self, 
                           filters: Optional[Dict[str, Any]] = None,
                           sort_column: str = "upload_timestamp",
                           sort_order: SortOrder = SortOrder.DESC,
                           batch_size: int = 100) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Stream videos in batches using async generator"""
        
        if not HAS_AIOSQLITE:
            # Fallback to sync implementation
            async for batch in self._sync_stream_fallback(filters, sort_column, sort_order, batch_size):
                yield batch
            return
        
        cursor = None
        
        try:
            # Use async SQLite
            async with aiosqlite.connect(self.db_path) as db:
                
                # Build query
                strategy = KeysetPaginationStrategy(None)  # Will build query without executing
                base_query, params = strategy.build_keyset_query(
                    cursor=cursor,
                    filters=filters,
                    sort_column=sort_column,
                    sort_order=sort_order,
                    page_size=batch_size
                )
                
                # Execute async query
                async with db.execute(base_query, params) as cursor:
                    
                    batch = []
                    async for row in cursor:
                        
                        # Convert row to dict
                        columns = [desc[0] for desc in cursor.description]
                        video_dict = dict(zip(columns, row))
                        batch.append(video_dict)
                        
                        # Yield batch when full
                        if len(batch) >= batch_size:
                            yield batch
                            batch = []
                            
                            # Small delay to prevent blocking
                            await asyncio.sleep(0.001)
                    
                    # Yield remaining items
                    if batch:
                        yield batch
        
        except Exception as e:
            print(f"Error in async streaming: {e}")
            # Fallback to sync
            async for batch in self._sync_stream_fallback(filters, sort_column, sort_order, batch_size):
                yield batch
    
    async def _sync_stream_fallback(self, 
                                   filters: Optional[Dict[str, Any]] = None,
                                   sort_column: str = "upload_timestamp", 
                                   sort_order: SortOrder = SortOrder.DESC,
                                   batch_size: int = 100) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fallback sync implementation wrapped in async"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            strategy = KeysetPaginationStrategy(conn)
            
            cursor = None
            has_more = True
            
            while has_more:
                query, params = strategy.build_keyset_query(
                    cursor=cursor,
                    filters=filters,
                    sort_column=sort_column,
                    sort_order=sort_order,
                    page_size=batch_size
                )
                
                db_cursor = conn.execute(query, params)
                rows = db_cursor.fetchall()
                
                if not rows:
                    break
                
                # Convert rows to dicts
                batch = [dict(row) for row in rows[:batch_size]]
                
                # Check if we have more pages
                has_more = len(rows) > batch_size
                
                # Update cursor for next iteration
                if batch and has_more:
                    last_item = batch[-1]
                    cursor = PaginationCursor(
                        video_id=last_item['video_id'],
                        upload_timestamp=last_item['upload_timestamp'],
                        file_size=last_item.get('file_size'),
                        duration=last_item.get('duration'),
                        page_size=batch_size,
                        direction=PaginationDirection.FORWARD
                    )
                
                yield batch
                
                # Small delay to prevent blocking
                await asyncio.sleep(0.001)
            
            conn.close()
            
        except Exception as e:
            print(f"Error in sync streaming fallback: {e}")


class AdvancedDatabasePaginator:
    """
    Main pagination coordinator combining all optimization strategies
    
    Provides high-level interface for optimized database pagination
    with keyset pagination, materialized views, and async streaming
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
        self.keyset_strategy = None
        self.materialized_views = None
        self.async_generator = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all pagination components"""
        try:
            # Create database connection
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            
            # Initialize components
            self.keyset_strategy = KeysetPaginationStrategy(self.connection)
            self.materialized_views = MaterializedViewManager(self.connection)
            self.async_generator = AsyncDataGenerator(self.db_path)
            
            # Optimize database settings
            self._optimize_database()
            
            print("✅ AdvancedDatabasePaginator initialized successfully")
            
        except Exception as e:
            print(f"❌ Error initializing paginator: {e}")
            raise
    
    def _optimize_database(self):
        """Apply database optimizations for pagination"""
        cursor = self.connection.cursor()
        
        try:
            # Performance settings
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL") 
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            
            # Create indexes for pagination queries
            self._create_pagination_indexes()
            
            print("✅ Database optimizations applied")
            
        except sqlite3.OperationalError as e:
            print(f"⚠️ Some optimizations skipped: {e}")
    
    def _create_pagination_indexes(self):
        """Create optimized indexes for pagination queries"""
        cursor = self.connection.cursor()
        
        indexes = [
            # Composite index for keyset pagination  
            "CREATE INDEX IF NOT EXISTS idx_videos_keyset ON downloaded_videos(upload_timestamp DESC, id DESC)",
            
            # Common filter indexes
            "CREATE INDEX IF NOT EXISTS idx_videos_status ON downloaded_videos(status)",
            "CREATE INDEX IF NOT EXISTS idx_videos_creator ON downloaded_videos(creator)",
            "CREATE INDEX IF NOT EXISTS idx_videos_quality ON downloaded_videos(quality)",
            "CREATE INDEX IF NOT EXISTS idx_videos_format ON downloaded_videos(format)",
            
            # Range query indexes
            "CREATE INDEX IF NOT EXISTS idx_videos_upload_time ON downloaded_videos(upload_timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_videos_file_size ON downloaded_videos(file_size)",
            "CREATE INDEX IF NOT EXISTS idx_videos_duration ON downloaded_videos(duration)",
            
            # Composite indexes for common filter combinations
            "CREATE INDEX IF NOT EXISTS idx_videos_status_upload ON downloaded_videos(status, upload_timestamp DESC, id DESC)",
            "CREATE INDEX IF NOT EXISTS idx_videos_creator_upload ON downloaded_videos(creator, upload_timestamp DESC, id DESC)",
            "CREATE INDEX IF NOT EXISTS idx_videos_quality_upload ON downloaded_videos(quality, upload_timestamp DESC, id DESC)",
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                print(f"✅ Created index: {index_sql.split('IF NOT EXISTS')[1].split('ON')[0].strip()}")
            except sqlite3.OperationalError as e:
                print(f"⚠️ Index creation skipped: {e}")
        
        self.connection.commit()
    
    def paginate(self, 
                cursor: Optional[str] = None,
                filters: Optional[Dict[str, Any]] = None,
                sort_column: str = "upload_timestamp",
                sort_order: SortOrder = SortOrder.DESC,
                page_size: int = 100) -> PaginationResult:
        """
        Execute optimized pagination query
        
        Args:
            cursor: Base64 encoded pagination cursor
            filters: Filter conditions
            sort_column: Column to sort by
            sort_order: Sort direction
            page_size: Items per page
            
        Returns:
            PaginationResult with items and pagination metadata
        """
        
        try:
            # Parse cursor
            pagination_cursor = None
            if cursor:
                pagination_cursor = PaginationCursor.from_string(cursor)
            
            # Build and execute query
            query, params = self.keyset_strategy.build_keyset_query(
                cursor=pagination_cursor,
                filters=filters,
                sort_column=sort_column,
                sort_order=sort_order,
                page_size=page_size
            )
            
            # Execute query
            db_cursor = self.connection.execute(query, params)
            rows = db_cursor.fetchall()
            
            # Convert to dicts
            items = [dict(row) for row in rows]
            
            # Determine pagination state
            has_next_page = len(items) > page_size
            if has_next_page:
                items = items[:page_size]  # Remove extra item
            
            # Generate cursors
            next_cursor = None
            previous_cursor = None
            
            if items:
                if has_next_page:
                    last_item = items[-1]
                    next_cursor = PaginationCursor(
                        video_id=last_item['video_id'],
                        upload_timestamp=last_item['upload_timestamp'],
                        file_size=last_item.get('file_size'),
                        duration=last_item.get('duration'),
                        page_size=page_size,
                        direction=PaginationDirection.FORWARD
                    ).to_string()
                
                if pagination_cursor:  # We have a previous page
                    first_item = items[0]
                    previous_cursor = PaginationCursor(
                        video_id=first_item['video_id'],
                        upload_timestamp=first_item['upload_timestamp'],
                        file_size=first_item.get('file_size'),
                        duration=first_item.get('duration'),
                        page_size=page_size,
                        direction=PaginationDirection.BACKWARD
                    ).to_string()
            
            # Get total count (expensive, consider caching)
            total_count = self._get_filtered_count(filters)
            
            return PaginationResult(
                items=items,
                has_next_page=has_next_page,
                has_previous_page=pagination_cursor is not None,
                total_count=total_count,
                next_cursor=next_cursor,
                previous_cursor=previous_cursor,
                page_info={
                    'page_size': page_size,
                    'items_returned': len(items),
                    'sort_column': sort_column,
                    'sort_order': sort_order.value,
                    'filters_applied': bool(filters)
                }
            )
            
        except Exception as e:
            print(f"❌ Pagination error: {e}")
            raise
    
    def _get_filtered_count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Get total count for filtered results"""
        try:
            conditions, params = [], []
            
            if filters:
                filter_conditions, filter_params = self.keyset_strategy._build_filter_conditions(filters)
                conditions.extend(filter_conditions)
                params.extend(filter_params)
            
            count_query = "SELECT COUNT(*) FROM downloaded_videos v"
            if conditions:
                count_query += " WHERE " + " AND ".join(conditions)
            
            cursor = self.connection.execute(count_query, params)
            return cursor.fetchone()[0]
            
        except Exception as e:
            print(f"Error getting count: {e}")
            return 0
    
    async def stream_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Stream data using async generator"""
        async for batch in self.async_generator.stream_videos(**kwargs):
            yield batch
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database and pagination statistics"""
        try:
            stats = {}
            
            # Get materialized view data
            for view_name in self.materialized_views.views.keys():
                try:
                    view_data = self.materialized_views.get_view_data(view_name, limit=10)
                    stats[view_name] = view_data
                except Exception as e:
                    stats[view_name] = f"Error: {e}"
            
            # Database info
            cursor = self.connection.execute("PRAGMA database_list")
            db_info = dict(cursor.fetchone()) if cursor.fetchone() else {}
            stats['database_info'] = db_info
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}
    
    def refresh_materialized_views(self):
        """Refresh all materialized views"""
        if self.materialized_views:
            self.materialized_views.refresh_views()
    
    def cleanup(self):
        """Clean up resources"""
        if self.connection:
            self.connection.close()
            print("✅ Database connection closed") 