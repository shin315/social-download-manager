import os
import json
import sqlite3
from datetime import datetime


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
            metadata TEXT,
            has_subtitle INTEGER DEFAULT 0,
            subtitle_language TEXT,
            subtitle_type TEXT,
            platform TEXT
        )
        ''')
        
        # Check if subtitle columns exist, add them if they don't
        cursor.execute("PRAGMA table_info(downloads)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'has_subtitle' not in columns:
            cursor.execute('ALTER TABLE downloads ADD COLUMN has_subtitle INTEGER DEFAULT 0')
        
        if 'subtitle_language' not in columns:
            cursor.execute('ALTER TABLE downloads ADD COLUMN subtitle_language TEXT')
        
        if 'subtitle_type' not in columns:
            cursor.execute('ALTER TABLE downloads ADD COLUMN subtitle_type TEXT')
            
        if 'platform' not in columns:
            cursor.execute('ALTER TABLE downloads ADD COLUMN platform TEXT')
        
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
        
        # Determine platform from URL if not provided
        platform = download_info.get('platform', '')
        if not platform and 'url' in download_info:
            url = download_info.get('url', '')
            if 'tiktok.com' in url:
                platform = 'TikTok'
            elif 'youtube.com' in url or 'youtu.be' in url:
                platform = 'YouTube'
            elif 'instagram.com' in url:
                platform = 'Instagram'
            elif 'facebook.com' in url:
                platform = 'Facebook'
        
        # Add new record
        cursor.execute('''
        INSERT INTO downloads (url, title, filepath, quality, format, duration, 
                               filesize, status, download_date, metadata,
                               has_subtitle, subtitle_language, subtitle_type, platform)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            metadata_json,
            1 if download_info.get('has_subtitle', False) else 0,
            download_info.get('subtitle_language', ''),
            download_info.get('subtitle_type', ''),
            platform
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
            
            # Determine platform if not present
            if 'platform' not in download or not download['platform']:
                url = download.get('url', '')
                if 'tiktok.com' in url:
                    download['platform'] = 'TikTok'
                elif 'youtube.com' in url or 'youtu.be' in url:
                    download['platform'] = 'YouTube'
                elif 'instagram.com' in url:
                    download['platform'] = 'Instagram'
                elif 'facebook.com' in url:
                    download['platform'] = 'Facebook'
                else:
                    download['platform'] = 'Unknown'
                    
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