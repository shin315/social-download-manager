"""
Database Performance Optimizer

Optimizes SQLite queries with indexing, caching, and background execution.
Part of Task 13.4: Optimize Database Performance
"""

import sqlite3
import hashlib
import json
import threading
import time
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, Future
from collections import OrderedDict
from datetime import datetime, timedelta
from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal, QThreadPool, QRunnable, QTimer


@dataclass
class QueryCache:
    """Cache entry for database queries"""
    result: Any
    timestamp: datetime
    hash_key: str
    access_count: int = 0
    ttl_seconds: int = 300  # 5 minutes default TTL


class BackgroundQuery(QRunnable):
    """Background query execution using QRunnable"""
    
    def __init__(self, query: str, params: tuple, callback_signal, db_path: str):
        super().__init__()
        self.query = query
        self.params = params
        self.callback_signal = callback_signal
        self.db_path = db_path
        self.result = None
        self.error = None
    
    def run(self):
        """Execute query in background thread"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(self.query, self.params)
            
            if self.query.strip().upper().startswith('SELECT'):
                self.result = [dict(row) for row in cursor.fetchall()]
            else:
                conn.commit()
                self.result = cursor.rowcount
                
            conn.close()
            
            # Emit result signal
            self.callback_signal.emit(self.result, None)
            
        except Exception as e:
            self.error = str(e)
            self.callback_signal.emit(None, self.error)


class DatabaseOptimizer(QObject):
    """
    Advanced database performance optimizer for downloads table
    
    Features:
    - Automatic index creation on filtered columns
    - Intelligent query caching with TTL
    - Background query execution using QThreadPool
    - Batch loading optimization for large datasets
    - Query performance monitoring
    """
    
    # Signals
    query_completed = pyqtSignal(object, object)  # result, error
    index_created = pyqtSignal(str)  # index_name
    cache_statistics_updated = pyqtSignal(dict)  # stats
    
    def __init__(self, db_path: str, cache_size: int = 100):
        super().__init__()
        
        self.db_path = db_path
        self.cache_size = cache_size
        
        # Query cache with LRU eviction
        self.query_cache: OrderedDict[str, QueryCache] = OrderedDict()
        self.cache_lock = threading.Lock()
        
        # Performance monitoring
        self.query_stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'background_queries': 0,
            'index_usage': {},
            'slow_queries': []  # Queries taking > 100ms
        }
        
        # Thread pool for background queries
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)  # Limit concurrent database connections
        
        # Cache cleanup timer
        self.cache_cleanup_timer = QTimer()
        self.cache_cleanup_timer.timeout.connect(self._cleanup_expired_cache)
        self.cache_cleanup_timer.start(60000)  # Cleanup every minute
        
        # Initialize optimization
        self._initialize_optimization()
    
    def _initialize_optimization(self):
        """Initialize database optimization"""
        try:
            self._create_performance_indexes()
            self._analyze_database()
            self._setup_sqlite_optimization()
            
        except Exception as e:
            print(f"Error initializing database optimization: {e}")
    
    def _create_performance_indexes(self):
        """Create indexes on frequently filtered columns"""
        indexes_to_create = [
            # Main filtering columns from Task 13.1-13.3
            ("idx_downloads_title", "CREATE INDEX IF NOT EXISTS idx_downloads_title ON downloads(title)"),
            ("idx_downloads_quality", "CREATE INDEX IF NOT EXISTS idx_downloads_quality ON downloads(quality)"),
            ("idx_downloads_format", "CREATE INDEX IF NOT EXISTS idx_downloads_format ON downloads(format)"),
            ("idx_downloads_status", "CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status)"),
            ("idx_downloads_date", "CREATE INDEX IF NOT EXISTS idx_downloads_date ON downloads(download_date)"),
            
            # Composite indexes for common filter combinations
            ("idx_downloads_quality_date", "CREATE INDEX IF NOT EXISTS idx_downloads_quality_date ON downloads(quality, download_date)"),
            ("idx_downloads_status_date", "CREATE INDEX IF NOT EXISTS idx_downloads_status_date ON downloads(status, download_date)"),
            
            # Full-text search optimization
            ("idx_downloads_title_case", "CREATE INDEX IF NOT EXISTS idx_downloads_title_case ON downloads(LOWER(title))"),
            
            # Metadata search optimization (JSON extract)
            ("idx_downloads_metadata_creator", "CREATE INDEX IF NOT EXISTS idx_downloads_metadata_creator ON downloads(json_extract(metadata, '$.creator'))"),
            ("idx_downloads_metadata_hashtags", "CREATE INDEX IF NOT EXISTS idx_downloads_metadata_hashtags ON downloads(json_extract(metadata, '$.hashtags'))")
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for index_name, create_sql in indexes_to_create:
            try:
                cursor.execute(create_sql)
                self.index_created.emit(index_name)
                print(f"✅ Created index: {index_name}")
                
            except sqlite3.Error as e:
                print(f"⚠️ Index creation warning for {index_name}: {e}")
        
        conn.commit()
        conn.close()
    
    def _analyze_database(self):
        """Analyze database for query optimization"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Update SQLite statistics
            cursor.execute("ANALYZE")
            
            # Get table info
            cursor.execute("PRAGMA table_info(downloads)")
            columns = cursor.fetchall()
            
            # Get index info
            cursor.execute("PRAGMA index_list(downloads)")
            indexes = cursor.fetchall()
            
            print(f"📊 Database analysis complete:")
            print(f"   - Columns: {len(columns)}")
            print(f"   - Indexes: {len(indexes)}")
            
        except sqlite3.Error as e:
            print(f"Error analyzing database: {e}")
        finally:
            conn.close()
    
    def _setup_sqlite_optimization(self):
        """Configure SQLite for optimal performance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Optimize SQLite settings for read-heavy workload
            cursor.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging for better concurrency
            cursor.execute("PRAGMA synchronous = NORMAL")  # Balanced durability/performance
            cursor.execute("PRAGMA cache_size = 10000")  # 10MB cache
            cursor.execute("PRAGMA temp_store = MEMORY")  # Use memory for temp tables
            cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB memory mapping
            
            print("✅ SQLite optimization settings applied")
            
        except sqlite3.Error as e:
            print(f"Error setting SQLite optimization: {e}")
        finally:
            conn.close()
    
    def execute_query_async(self, query: str, params: tuple = (), cache_key: str = None, ttl: int = 300):
        """
        Execute query asynchronously with caching
        
        Args:
            query: SQL query string
            params: Query parameters
            cache_key: Optional cache key, auto-generated if None
            ttl: Cache TTL in seconds
        """
        self.query_stats['total_queries'] += 1
        
        # Generate cache key if not provided
        if cache_key is None:
            cache_key = self._generate_cache_key(query, params)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            self.query_stats['cache_hits'] += 1
            # Emit cached result immediately
            self.query_completed.emit(cached_result, None)
            return
        
        self.query_stats['cache_misses'] += 1
        self.query_stats['background_queries'] += 1
        
        # Execute in background
        background_query = BackgroundQuery(query, params, self._on_background_query_complete, self.db_path)
        background_query.cache_key = cache_key
        background_query.ttl = ttl
        
        self.thread_pool.start(background_query)
    
    def execute_query_sync(self, query: str, params: tuple = (), cache_key: str = None, ttl: int = 300):
        """
        Execute query synchronously with caching
        
        Args:
            query: SQL query string
            params: Query parameters  
            cache_key: Optional cache key
            ttl: Cache TTL in seconds
            
        Returns:
            Query result or None if error
        """
        self.query_stats['total_queries'] += 1
        
        # Generate cache key if not provided
        if cache_key is None:
            cache_key = self._generate_cache_key(query, params)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            self.query_stats['cache_hits'] += 1
            return cached_result
        
        self.query_stats['cache_misses'] += 1
        
        # Execute synchronously
        start_time = time.time()
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(query, params)
            
            if query.strip().upper().startswith('SELECT'):
                result = [dict(row) for row in cursor.fetchall()]
            else:
                conn.commit()
                result = cursor.rowcount
            
            conn.close()
            
            # Track slow queries
            execution_time = (time.time() - start_time) * 1000
            if execution_time > 100:  # > 100ms
                self.query_stats['slow_queries'].append({
                    'query': query[:100] + '...' if len(query) > 100 else query,
                    'time_ms': execution_time,
                    'timestamp': datetime.now().isoformat()
                })
            
            # Cache result
            self._store_in_cache(cache_key, result, ttl)
            
            return result
            
        except Exception as e:
            print(f"Database query error: {e}")
            return None
    
    def get_downloads_optimized(self, filters: Dict[str, Any] = None, limit: int = 50, offset: int = 0):
        """
        Optimized method to get downloads with filtering and pagination
        
        Args:
            filters: Dictionary of filter conditions
            limit: Maximum number of records (batch size)
            offset: Offset for pagination
            
        Returns:
            List of download records
        """
        where_conditions = []
        params = []
        
        if filters:
            for field, condition in filters.items():
                if field == 'title' and isinstance(condition, str):
                    where_conditions.append("LOWER(title) LIKE LOWER(?)")
                    params.append(f"%{condition}%")
                elif field == 'quality' and isinstance(condition, list):
                    placeholders = ",".join(["?" for _ in condition])
                    where_conditions.append(f"quality IN ({placeholders})")
                    params.extend(condition)
                elif field == 'date_range' and isinstance(condition, tuple) and len(condition) == 2:
                    where_conditions.append("download_date BETWEEN ? AND ?")
                    params.extend(condition)
                elif field == 'creator':
                    where_conditions.append("json_extract(metadata, '$.creator') LIKE ?")
                    params.append(f"%{condition}%")
                elif field == 'hashtags':
                    where_conditions.append("json_extract(metadata, '$.hashtags') LIKE ?")
                    params.append(f"%{condition}%")
        
        # Build query
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        query = f"""
        SELECT * FROM downloads 
        WHERE {where_clause}
        ORDER BY download_date DESC 
        LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        # Generate cache key for this specific query
        cache_key = f"downloads_optimized_{hashlib.md5(str(filters).encode()).hexdigest()}_{limit}_{offset}"
        
        return self.execute_query_sync(query, tuple(params), cache_key, ttl=120)  # 2-minute cache
    
    def get_filter_statistics(self, field: str):
        """
        Get statistics for filter fields (e.g., quality counts)
        
        Args:
            field: Field name to get statistics for
            
        Returns:
            Dictionary with field values and their counts
        """
        if field == 'quality':
            query = "SELECT quality, COUNT(*) as count FROM downloads WHERE quality IS NOT NULL GROUP BY quality ORDER BY count DESC"
        elif field == 'format':
            query = "SELECT format, COUNT(*) as count FROM downloads WHERE format IS NOT NULL GROUP BY format ORDER BY count DESC"
        elif field == 'status':
            query = "SELECT status, COUNT(*) as count FROM downloads WHERE status IS NOT NULL GROUP BY status ORDER BY count DESC"
        elif field == 'creator':
            query = "SELECT json_extract(metadata, '$.creator') as creator, COUNT(*) as count FROM downloads WHERE creator IS NOT NULL GROUP BY creator ORDER BY count DESC LIMIT 50"
        else:
            return {}
        
        cache_key = f"filter_stats_{field}"
        result = self.execute_query_sync(query, (), cache_key, ttl=600)  # 10-minute cache
        
        if result:
            return {row[field if field != 'creator' else 'creator']: row['count'] for row in result}
        
        return {}
    
    def _on_background_query_complete(self, result, error):
        """Handle background query completion"""
        sender = self.sender()
        
        if error is None and result is not None:
            # Cache the result
            self._store_in_cache(sender.cache_key, result, sender.ttl)
        
        # Forward the signal
        self.query_completed.emit(result, error)
    
    def _generate_cache_key(self, query: str, params: tuple) -> str:
        """Generate cache key for query and parameters"""
        combined = f"{query}|{str(params)}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _get_from_cache(self, key: str) -> Any:
        """Retrieve item from cache if not expired"""
        with self.cache_lock:
            if key in self.query_cache:
                cache_entry = self.query_cache[key]
                
                # Check if expired
                if datetime.now() - cache_entry.timestamp > timedelta(seconds=cache_entry.ttl_seconds):
                    del self.query_cache[key]
                    return None
                
                # Move to end (LRU)
                self.query_cache.move_to_end(key)
                cache_entry.access_count += 1
                
                return cache_entry.result
        
        return None
    
    def _store_in_cache(self, key: str, result: Any, ttl: int):
        """Store item in cache with TTL"""
        with self.cache_lock:
            # Remove oldest items if cache is full
            while len(self.query_cache) >= self.cache_size:
                self.query_cache.popitem(last=False)
            
            # Store new entry
            self.query_cache[key] = QueryCache(
                result=result,
                timestamp=datetime.now(),
                hash_key=key,
                ttl_seconds=ttl
            )
    
    def _cleanup_expired_cache(self):
        """Remove expired cache entries"""
        with self.cache_lock:
            current_time = datetime.now()
            expired_keys = []
            
            for key, cache_entry in self.query_cache.items():
                if current_time - cache_entry.timestamp > timedelta(seconds=cache_entry.ttl_seconds):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.query_cache[key]
            
            if expired_keys:
                print(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
    
    def clear_cache(self):
        """Clear all cached queries"""
        with self.cache_lock:
            self.query_cache.clear()
        print("🗑️ Query cache cleared")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache and query performance statistics"""
        with self.cache_lock:
            cache_size = len(self.query_cache)
            total_access_count = sum(entry.access_count for entry in self.query_cache.values())
        
        hit_rate = (self.query_stats['cache_hits'] / max(1, self.query_stats['total_queries'])) * 100
        
        stats = {
            'cache_size': cache_size,
            'cache_hit_rate': round(hit_rate, 2),
            'total_queries': self.query_stats['total_queries'],
            'cache_hits': self.query_stats['cache_hits'],
            'cache_misses': self.query_stats['cache_misses'],
            'background_queries': self.query_stats['background_queries'],
            'total_cache_accesses': total_access_count,
            'slow_queries_count': len(self.query_stats['slow_queries']),
            'recent_slow_queries': self.query_stats['slow_queries'][-5:]  # Last 5 slow queries
        }
        
        self.cache_statistics_updated.emit(stats)
        return stats
    
    def optimize_for_large_dataset(self, enable: bool = True):
        """Enable/disable optimizations for large datasets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if enable:
                # More aggressive caching and optimization for large datasets
                cursor.execute("PRAGMA cache_size = 20000")  # 20MB cache
                cursor.execute("PRAGMA mmap_size = 536870912")  # 512MB memory mapping
                self.cache_size = 200  # Larger query cache
                print("✅ Large dataset optimizations enabled")
            else:
                # Standard settings
                cursor.execute("PRAGMA cache_size = 10000")  # 10MB cache
                cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB memory mapping
                self.cache_size = 100  # Standard cache size
                print("✅ Standard optimizations restored")
                
        except sqlite3.Error as e:
            print(f"Error setting large dataset optimizations: {e}")
        finally:
            conn.close()
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.cache_cleanup_timer.stop()
            self.thread_pool.waitForDone(5000)  # Wait up to 5 seconds
            self.clear_cache()
            print("🧹 DatabaseOptimizer cleanup completed")
        except Exception as e:
            print(f"Error during cleanup: {e}")


# Singleton instance
_database_optimizer_instance = None

def get_database_optimizer(db_path: str = None) -> DatabaseOptimizer:
    """Get or create DatabaseOptimizer singleton instance"""
    global _database_optimizer_instance
    
    if _database_optimizer_instance is None and db_path:
        _database_optimizer_instance = DatabaseOptimizer(db_path)
    
    return _database_optimizer_instance 