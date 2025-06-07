import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import advanced pagination system
try:
    from core.database.advanced_pagination import (
        AdvancedDatabasePaginator, SortOrder, PaginationDirection
    )
    HAS_ADVANCED_PAGINATION = True
except ImportError:
    HAS_ADVANCED_PAGINATION = False
    print("Advanced pagination not available - using basic pagination")


class DatabaseManager:
    """Database manager for download history"""
    
    def __init__(self, db_path=None):
        """
        Initialize database manager
        
        Args:
            db_path: Path to database file, if None will create in user directory
        """
        if not db_path:
            app_data_dir = os.path.join(os.path.expanduser("~"), ".tiktok_downloader")
            if not os.path.exists(app_data_dir):
                os.makedirs(app_data_dir)
            db_path = os.path.join(app_data_dir, "downloads.db")
            
        self.db_path = db_path
        self.init_db()
        
        # Initialize advanced pagination if available
        if HAS_ADVANCED_PAGINATION:
            try:
                self.advanced_paginator = AdvancedDatabasePaginator(self.db_path)
                print("✅ Advanced pagination enabled")
            except Exception as e:
                print(f"⚠️ Advanced pagination failed to initialize: {e}")
                self.advanced_paginator = None
        else:
            self.advanced_paginator = None
    
    def init_db(self):
        """Initialize database if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create downloads table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            filepath TEXT NOT NULL,
            quality TEXT,
            format TEXT,
            duration INTEGER,
            filesize TEXT,
            status TEXT,
            download_date TEXT,
            metadata TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_download(self, download_info):
        """
        Add a download record to the database
        
        Args:
            download_info: Dictionary containing information about the downloaded video
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convert metadata to JSON string
        metadata = {}
        if 'caption' in download_info:
            metadata['caption'] = download_info['caption']
        if 'hashtags' in download_info:
            metadata['hashtags'] = download_info['hashtags']
        if 'thumbnail' in download_info:
            metadata['thumbnail'] = download_info['thumbnail']
        if 'creator' in download_info:
            metadata['creator'] = download_info['creator']
        if 'description' in download_info:
            metadata['description'] = download_info['description']
        
        metadata_json = json.dumps(metadata)
        
        # Add new record
        cursor.execute('''
        INSERT INTO downloads (url, title, filepath, quality, format, duration, 
                               filesize, status, download_date, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            download_info.get('url', ''),
            download_info.get('title', 'Unknown'),
            download_info.get('filepath', ''),
            download_info.get('quality', ''),
            download_info.get('format', ''),
            download_info.get('duration', 0),
            download_info.get('filesize', ''),
            download_info.get('status', 'Success'),
            download_info.get('download_date', datetime.now().strftime("%Y/%m/%d %H:%M")),
            metadata_json
        ))
        
        conn.commit()
        conn.close()
    
    def get_downloads(self):
        """
        Get all download records from the database
        
        Returns:
            List[Dict]: List of download records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return results as dictionaries
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM downloads ORDER BY download_date DESC')
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            download = dict(row)
            
            # Parse metadata from JSON
            if 'metadata' in download and download['metadata']:
                try:
                    metadata = json.loads(download['metadata'])
                    download.update(metadata)
                except:
                    pass
                    
            result.append(download)
            
        conn.close()
        return result
    
    def search_downloads(self, keyword):
        """
        Search the database for a keyword
        
        Args:
            keyword: Search keyword
        
        Returns:
            List[Dict]: List of matching download records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Search by title or metadata
        cursor.execute('''
        SELECT * FROM downloads 
        WHERE title LIKE ? OR metadata LIKE ?
        ORDER BY download_date DESC
        ''', (f'%{keyword}%', f'%{keyword}%'))
        
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            download = dict(row)
            
            # Parse metadata from JSON
            if 'metadata' in download and download['metadata']:
                try:
                    metadata = json.loads(download['metadata'])
                    download.update(metadata)
                except:
                    pass
                    
            result.append(download)
            
        conn.close()
        return result
    
    def delete_download(self, download_id):
        """
        Delete a download record from the database
        
        Args:
            download_id: ID of the record to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM downloads WHERE id = ?', (download_id,))
            conn.commit()
            success = cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting download: {e}")
            success = False
            
        conn.close()
        return success
    
    def get_download_by_url(self, url):
        """
        Get a download record by URL
        
        Args:
            url: URL of the video
            
        Returns:
            Dict or None: Record information or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM downloads WHERE url = ?', (url,))
        row = cursor.fetchone()
        
        if row:
            download = dict(row)
            
            # Parse metadata from JSON
            if 'metadata' in download and download['metadata']:
                try:
                    metadata = json.loads(download['metadata'])
                    download.update(metadata)
                except:
                    pass
                    
            conn.close()
            return download
        
        conn.close()
        return None
    
    def delete_download_by_title(self, title):
        """
        Delete a download record from the database based on title
        
        Args:
            title: Title of the video to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM downloads WHERE title = ?', (title,))
            conn.commit()
            deleted_count = cursor.rowcount
            print(f"Successfully deleted {deleted_count} records with title: {title}")
            success = deleted_count > 0
            conn.close()
            return success
        except Exception as e:
            print(f"Error deleting download by title: {e}")
            conn.close()
            return False
        
    def get_download_by_title(self, title):
        """
        Get a download record by title
        
        Args:
            title: Title of the video
            
        Returns:
            Dict or None: Record information or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM downloads WHERE title = ?', (title,))
        row = cursor.fetchone()
        
        if row:
            download = dict(row)
            
            # Parse metadata from JSON
            if 'metadata' in download and download['metadata']:
                try:
                    metadata = json.loads(download['metadata'])
                    download.update(metadata)
                except:
                    pass
                    
            conn.close()
            return download
        
        conn.close()
        return None
    
    def get_downloaded_videos_paginated(self, limit: int = 100, offset: int = 0,
                                      filters: Dict[str, Any] = None,
                                      sort_column: str = None, sort_order: str = None):
        """
        Get downloaded videos with pagination support for lazy loading
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            filters: Dictionary of filter conditions
            sort_column: Column to sort by
            sort_order: Sort order ('ASC' or 'DESC')
            
        Returns:
            List[Dict]: List of download records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build WHERE clause
        where_conditions = []
        params = []
        
        if filters:
            for field, condition in filters.items():
                if field == 'title' and isinstance(condition, str):
                    where_conditions.append("LOWER(title) LIKE LOWER(?)")
                    params.append(f"%{condition}%")
                elif field == 'creator' and isinstance(condition, str):
                    where_conditions.append("json_extract(metadata, '$.creator') LIKE ?")
                    params.append(f"%{condition}%")
                elif field == 'quality' and isinstance(condition, list):
                    placeholders = ",".join(["?" for _ in condition])
                    where_conditions.append(f"quality IN ({placeholders})")
                    params.extend(condition)
                elif field == 'status' and isinstance(condition, str):
                    where_conditions.append("status = ?")
                    params.append(condition)
                elif field == 'date_range' and isinstance(condition, tuple) and len(condition) == 2:
                    where_conditions.append("download_date BETWEEN ? AND ?")
                    params.extend(condition)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Build ORDER BY clause
        order_clause = "download_date DESC"  # Default sort
        if sort_column and sort_order:
            # Map display columns to database columns
            column_mapping = {
                'title': 'title',
                'creator': "json_extract(metadata, '$.creator')",
                'quality': 'quality',
                'format': 'format',
                'file_size': 'filesize',
                'status': 'status',
                'download_date': 'download_date',
                'date': 'download_date'
            }
            
            if sort_column in column_mapping:
                db_column = column_mapping[sort_column]
                order_clause = f"{db_column} {sort_order}"
        
        # Build complete query
        query = f"""
        SELECT * FROM downloads 
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            download = dict(row)
            
            # Parse metadata from JSON
            if 'metadata' in download and download['metadata']:
                try:
                    metadata = json.loads(download['metadata'])
                    download.update(metadata)
                except:
                    pass
            
            # Convert to format expected by lazy table model
            formatted_download = {
                'id': download.get('id'),
                'title': download.get('title', ''),
                'creator': download.get('creator', ''),
                'quality': download.get('quality', ''),
                'format': download.get('format', ''),
                'file_size': download.get('filesize', ''),
                'status': download.get('status', ''),
                'download_date': download.get('download_date', ''),
                'hashtags': download.get('hashtags', []),
                'file_path': download.get('filepath', ''),
                'url': download.get('url', ''),
                'duration': download.get('duration', 0),
                'description': download.get('description', ''),
                'thumbnail': download.get('thumbnail', '')
            }
            result.append(formatted_download)
        
        conn.close()
        return result
    
    def get_downloaded_videos_count(self, filters: Dict[str, Any] = None) -> int:
        """
        Get total count of downloaded videos for pagination
        
        Args:
            filters: Dictionary of filter conditions
            
        Returns:
            int: Total number of records
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build WHERE clause (same as paginated method)
        where_conditions = []
        params = []
        
        if filters:
            for field, condition in filters.items():
                if field == 'title' and isinstance(condition, str):
                    where_conditions.append("LOWER(title) LIKE LOWER(?)")
                    params.append(f"%{condition}%")
                elif field == 'creator' and isinstance(condition, str):
                    where_conditions.append("json_extract(metadata, '$.creator') LIKE ?")
                    params.append(f"%{condition}%")
                elif field == 'quality' and isinstance(condition, list):
                    placeholders = ",".join(["?" for _ in condition])
                    where_conditions.append(f"quality IN ({placeholders})")
                    params.extend(condition)
                elif field == 'status' and isinstance(condition, str):
                    where_conditions.append("status = ?")
                    params.append(condition)
                elif field == 'date_range' and isinstance(condition, tuple) and len(condition) == 2:
                    where_conditions.append("download_date BETWEEN ? AND ?")
                    params.extend(condition)
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        query = f"SELECT COUNT(*) FROM downloads WHERE {where_clause}"
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        
        conn.close()
        return count

    def update_download_filesize(self, identifier, new_filesize):
        """
        Update the file size for a download record
        
        Args:
            identifier: URL or ID of the video to update
            new_filesize: New file size (string format, e.g., "10.5 MB")
            
        Returns:
            bool: True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            print(f"Attempting to update filesize to {new_filesize} for {identifier}")
            
            # Check if identifier is URL or ID
            if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
                # ID case
                cursor.execute('UPDATE downloads SET filesize = ? WHERE id = ?', (new_filesize, identifier))
            else:
                # URL case
                cursor.execute('UPDATE downloads SET filesize = ? WHERE url = ?', (new_filesize, identifier))
            
            conn.commit()
            success = cursor.rowcount > 0
            if success:
                print(f"Successfully updated filesize to {new_filesize} for {identifier}")
            else:
                print(f"No records found for {identifier}")
        except Exception as e:
            print(f"Error updating download filesize: {e}")
            success = False
            
        conn.close()
        return success 
    
    # =============================================================================
    # Statistics Methods for Cross-Tab Synchronization
    # =============================================================================
    
    def get_total_download_count(self):
        """
        Get total number of downloads
        
        Returns:
            int: Total download count
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM downloads')
            count = cursor.fetchone()[0]
        except Exception as e:
            print(f"Error getting total download count: {e}")
            count = 0
            
        conn.close()
        return count
    
    def get_successful_download_count(self):
        """
        Get number of successful downloads
        
        Returns:
            int: Successful download count
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM downloads WHERE status = ?', ('Success',))
            count = cursor.fetchone()[0]
        except Exception as e:
            print(f"Error getting successful download count: {e}")
            count = 0
            
        conn.close()
        return count
    
    def get_failed_download_count(self):
        """
        Get number of failed downloads
        
        Returns:
            int: Failed download count
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM downloads WHERE status != ?', ('Success',))
            count = cursor.fetchone()[0]
        except Exception as e:
            print(f"Error getting failed download count: {e}")
            count = 0
            
        conn.close()
        return count
    
    def get_download_statistics(self):
        """
        Get comprehensive download statistics
        
        Returns:
            dict: Dictionary containing various statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        try:
            # Total downloads
            cursor.execute('SELECT COUNT(*) FROM downloads')
            stats['total_downloads'] = cursor.fetchone()[0]
            
            # Successful downloads
            cursor.execute('SELECT COUNT(*) FROM downloads WHERE status = ?', ('Success',))
            stats['successful_downloads'] = cursor.fetchone()[0]
            
            # Failed downloads
            cursor.execute('SELECT COUNT(*) FROM downloads WHERE status != ?', ('Success',))
            stats['failed_downloads'] = cursor.fetchone()[0]
            
            # Success rate
            if stats['total_downloads'] > 0:
                stats['success_rate'] = (stats['successful_downloads'] / stats['total_downloads']) * 100
            else:
                stats['success_rate'] = 0
            
            # Recent downloads (last 24 hours)
            cursor.execute('''
                SELECT COUNT(*) FROM downloads 
                WHERE datetime(download_date) >= datetime('now', '-1 day')
            ''')
            stats['recent_downloads_24h'] = cursor.fetchone()[0]
            
            # Total file size
            cursor.execute('SELECT SUM(CAST(REPLACE(filesize, " MB", "") AS REAL)) FROM downloads WHERE filesize LIKE "% MB"')
            result = cursor.fetchone()[0]
            stats['total_size_mb'] = result if result else 0
            
            # Most common quality
            cursor.execute('''
                SELECT quality, COUNT(*) as count 
                FROM downloads 
                WHERE quality != "" 
                GROUP BY quality 
                ORDER BY count DESC 
                LIMIT 1
            ''')
            quality_result = cursor.fetchone()
            stats['most_common_quality'] = quality_result[0] if quality_result else 'Unknown'
            
            # Most common format
            cursor.execute('''
                SELECT format, COUNT(*) as count 
                FROM downloads 
                WHERE format != "" 
                GROUP BY format 
                ORDER BY count DESC 
                LIMIT 1
            ''')
            format_result = cursor.fetchone()
            stats['most_common_format'] = format_result[0] if format_result else 'Unknown'
            
        except Exception as e:
            print(f"Error getting download statistics: {e}")
            # Return basic stats on error
            stats = {
                'total_downloads': 0,
                'successful_downloads': 0,
                'failed_downloads': 0,
                'success_rate': 0,
                'recent_downloads_24h': 0,
                'total_size_mb': 0,
                'most_common_quality': 'Unknown',
                'most_common_format': 'Unknown'
            }
            
        conn.close()
        return stats
    
    def get_download_trends(self, days=7):
        """
        Get download trends over specified number of days
        
        Args:
            days: Number of days to analyze (default: 7)
            
        Returns:
            dict: Daily download counts and trends
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        trends = {}
        
        try:
            # Get daily download counts
            cursor.execute('''
                SELECT DATE(download_date) as date, COUNT(*) as count
                FROM downloads 
                WHERE datetime(download_date) >= datetime('now', '-{} day')
                GROUP BY DATE(download_date)
                ORDER BY date DESC
            '''.format(days))
            
            daily_counts = cursor.fetchall()
            trends['daily_counts'] = [{'date': row[0], 'count': row[1]} for row in daily_counts]
            
            # Calculate average downloads per day
            if daily_counts:
                total_downloads = sum(row[1] for row in daily_counts)
                trends['avg_downloads_per_day'] = total_downloads / len(daily_counts)
            else:
                trends['avg_downloads_per_day'] = 0
            
            # Get peak download day
            if daily_counts:
                peak_day = max(daily_counts, key=lambda x: x[1])
                trends['peak_day'] = {'date': peak_day[0], 'count': peak_day[1]}
            else:
                trends['peak_day'] = {'date': None, 'count': 0}
                
        except Exception as e:
            print(f"Error getting download trends: {e}")
            trends = {
                'daily_counts': [],
                'avg_downloads_per_day': 0,
                'peak_day': {'date': None, 'count': 0}
            }
            
        conn.close()
        return trends
    
    # =============================================================================
    # Advanced Pagination Methods (Task 15.3)
    # =============================================================================
    
    def get_videos_with_advanced_pagination(self, 
                                          cursor: Optional[str] = None,
                                          filters: Optional[Dict[str, Any]] = None,
                                          sort_column: str = "download_date",
                                          sort_order: str = "DESC",
                                          page_size: int = 100):
        """
        Get videos using advanced keyset pagination for optimal performance
        
        Args:
            cursor: Base64 encoded pagination cursor for keyset pagination
            filters: Filter conditions (creator, quality, status, etc.)
            sort_column: Column to sort by (default: download_date)
            sort_order: Sort direction ASC/DESC (default: DESC)
            page_size: Number of items per page (default: 100)
            
        Returns:
            dict: Pagination result with items, cursors, and metadata
        """
        if not self.advanced_paginator:
            # Fallback to basic pagination
            print("⚠️ Advanced pagination not available, using basic method")
            return self._fallback_pagination(cursor, filters, sort_column, sort_order, page_size)
        
        try:
            # Convert sort order to enum
            from core.database.advanced_pagination import SortOrder as AdvancedSortOrder
            sort_enum = AdvancedSortOrder.DESC if sort_order.upper() == "DESC" else AdvancedSortOrder.ASC
            
            # Map columns between downloads and downloaded_videos schema
            column_mapping = {
                'download_date': 'upload_timestamp',  # Map to timestamp for consistency
                'title': 'title',
                'filesize': 'file_size',
                'duration': 'duration',
                'quality': 'quality',
                'format': 'format',
                'status': 'status'
            }
            
            mapped_column = column_mapping.get(sort_column, 'upload_timestamp')
            
            # Execute advanced pagination
            result = self.advanced_paginator.paginate(
                cursor=cursor,
                filters=self._map_filters_for_advanced_pagination(filters),
                sort_column=mapped_column,
                sort_order=sort_enum,
                page_size=page_size
            )
            
            # Convert result items back to downloads schema
            converted_items = []
            for item in result.items:
                converted_item = self._convert_advanced_result_to_download(item)
                converted_items.append(converted_item)
            
            return {
                'items': converted_items,
                'has_next_page': result.has_next_page,
                'has_previous_page': result.has_previous_page,
                'total_count': result.total_count,
                'next_cursor': result.next_cursor,
                'previous_cursor': result.previous_cursor,
                'page_info': result.page_info,
                'pagination_type': 'advanced_keyset'
            }
            
        except Exception as e:
            print(f"❌ Advanced pagination error: {e}")
            # Fallback to basic pagination
            return self._fallback_pagination(cursor, filters, sort_column, sort_order, page_size)
    
    def _map_filters_for_advanced_pagination(self, filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Map filter fields from downloads schema to downloaded_videos schema"""
        if not filters:
            return None
        
        mapped_filters = {}
        
        # Map common filter fields
        field_mapping = {
            'title': 'title',
            'creator': 'creator',
            'quality': 'quality',
            'format': 'format',
            'status': 'status'
        }
        
        for old_field, new_field in field_mapping.items():
            if old_field in filters:
                mapped_filters[new_field] = filters[old_field]
        
        # Handle date range filters
        if 'date_range' in filters:
            mapped_filters['date_range'] = filters['date_range']
        
        # Handle size range filters
        if 'size_range' in filters:
            mapped_filters['file_size_range'] = filters['size_range']
            
        return mapped_filters
    
    def _convert_advanced_result_to_download(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert advanced pagination result back to downloads schema"""
        
        # Convert timestamp back to readable date
        upload_timestamp = item.get('upload_timestamp', 0)
        if upload_timestamp:
            try:
                download_date = datetime.fromtimestamp(upload_timestamp).strftime("%Y/%m/%d %H:%M")
            except:
                download_date = datetime.now().strftime("%Y/%m/%d %H:%M")
        else:
            download_date = datetime.now().strftime("%Y/%m/%d %H:%M")
        
        # Map fields back to downloads schema
        converted = {
            'id': item.get('video_id', 0),
            'url': item.get('url', ''),
            'title': item.get('title', 'Unknown'),
            'filepath': '',  # Not stored in advanced schema
            'quality': item.get('quality', ''),
            'format': item.get('format', ''),
            'duration': item.get('duration', 0),
            'filesize': self._format_file_size(item.get('file_size', 0)),
            'status': item.get('status', 'Unknown'),
            'download_date': download_date,
            'metadata': '',  # Could be reconstructed if needed
            'creator': item.get('creator', ''),
        }
        
        return converted
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size from bytes to readable string"""
        if not size_bytes or size_bytes == 0:
            return "Unknown"
        
        # Convert bytes to MB
        size_mb = size_bytes / (1024 * 1024)
        return f"{size_mb:.1f} MB"
    
    def _fallback_pagination(self, cursor, filters, sort_column, sort_order, page_size):
        """Fallback to basic OFFSET/LIMIT pagination"""
        
        # Extract page number from cursor (if provided)
        page_number = 0
        if cursor:
            try:
                import base64
                import json
                cursor_data = json.loads(base64.b64decode(cursor.encode()).decode())
                page_number = cursor_data.get('page', 0)
            except:
                page_number = 0
        
        offset = page_number * page_size
        
        # Use existing paginated method
        items = self.get_downloaded_videos_paginated(
            limit=page_size + 1,  # +1 to check for next page
            offset=offset,
            filters=filters,
            sort_column=sort_column,
            sort_order=sort_order
        )
        
        has_next_page = len(items) > page_size
        if has_next_page:
            items = items[:page_size]  # Remove extra item
        
        # Generate simple cursors
        next_cursor = None
        previous_cursor = None
        
        if has_next_page:
            import base64
            import json
            next_data = {'page': page_number + 1, 'page_size': page_size}
            next_cursor = base64.b64encode(json.dumps(next_data).encode()).decode()
        
        if page_number > 0:
            import base64
            import json
            prev_data = {'page': page_number - 1, 'page_size': page_size}
            previous_cursor = base64.b64encode(json.dumps(prev_data).encode()).decode()
        
        total_count = self.get_downloaded_videos_count(filters)
        
        return {
            'items': items,
            'has_next_page': has_next_page,
            'has_previous_page': page_number > 0,
            'total_count': total_count,
            'next_cursor': next_cursor,
            'previous_cursor': previous_cursor,
            'page_info': {
                'page_size': page_size,
                'items_returned': len(items),
                'current_page': page_number,
                'sort_column': sort_column,
                'sort_order': sort_order
            },
            'pagination_type': 'basic_offset'
        }
    
    async def stream_videos_async(self, **kwargs):
        """Stream videos asynchronously using advanced pagination"""
        if not self.advanced_paginator:
            print("⚠️ Async streaming not available without advanced pagination")
            return
        
        try:
            async for batch in self.advanced_paginator.stream_data(**kwargs):
                # Convert each batch item
                converted_batch = []
                for item in batch:
                    converted_item = self._convert_advanced_result_to_download(item)
                    converted_batch.append(converted_item)
                yield converted_batch
        except Exception as e:
            print(f"❌ Async streaming error: {e}")
    
    def get_pagination_statistics(self):
        """Get statistics about pagination performance and usage"""
        if not self.advanced_paginator:
            return {"advanced_pagination": False, "message": "Advanced pagination not available"}
        
        try:
            stats = self.advanced_paginator.get_statistics()
            stats["advanced_pagination"] = True
            return stats
        except Exception as e:
            return {"advanced_pagination": False, "error": str(e)}
    
    def refresh_pagination_views(self):
        """Refresh materialized views for better pagination performance"""
        if not self.advanced_paginator:
            print("⚠️ Cannot refresh views without advanced pagination")
            return False
        
        try:
            self.advanced_paginator.refresh_materialized_views()
            return True
        except Exception as e:
            print(f"❌ Error refreshing views: {e}")
            return False