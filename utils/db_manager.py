import os
import json
import sqlite3
from datetime import datetime


class DatabaseManager:
    """Quản lý cơ sở dữ liệu cho lịch sử tải xuống"""
    
    def __init__(self, db_path=None):
        """
        Khởi tạo database manager
        
        Args:
            db_path: Đường dẫn đến file database, nếu None sẽ tạo trong thư mục người dùng
        """
        if not db_path:
            app_data_dir = os.path.join(os.path.expanduser("~"), ".tiktok_downloader")
            if not os.path.exists(app_data_dir):
                os.makedirs(app_data_dir)
            db_path = os.path.join(app_data_dir, "downloads.db")
            
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Khởi tạo cơ sở dữ liệu nếu chưa tồn tại"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tạo bảng downloads nếu chưa tồn tại
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
        Thêm một bản ghi tải xuống vào cơ sở dữ liệu
        
        Args:
            download_info: Dictionary chứa thông tin về video đã tải
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Chuyển metadata thành JSON string
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
        
        # Thêm bản ghi mới
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
        Lấy tất cả bản ghi tải xuống từ cơ sở dữ liệu
        
        Returns:
            List[Dict]: Danh sách các bản ghi tải xuống
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Để trả về dạng dictionary
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM downloads ORDER BY download_date DESC')
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            download = dict(row)
            
            # Parse metadata từ JSON
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
        Tìm kiếm trong cơ sở dữ liệu theo từ khóa
        
        Args:
            keyword: Từ khóa tìm kiếm
        
        Returns:
            List[Dict]: Danh sách các bản ghi tải xuống phù hợp
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Tìm kiếm theo title hoặc metadata
        cursor.execute('''
        SELECT * FROM downloads 
        WHERE title LIKE ? OR metadata LIKE ?
        ORDER BY download_date DESC
        ''', (f'%{keyword}%', f'%{keyword}%'))
        
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            download = dict(row)
            
            # Parse metadata từ JSON
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
        Xóa một bản ghi tải xuống khỏi cơ sở dữ liệu
        
        Args:
            download_id: ID của bản ghi cần xóa
            
        Returns:
            bool: True nếu xóa thành công, False nếu không
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
        Lấy bản ghi tải xuống theo URL
        
        Args:
            url: URL của video
            
        Returns:
            Dict or None: Thông tin bản ghi hoặc None nếu không tìm thấy
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM downloads WHERE url = ?', (url,))
        row = cursor.fetchone()
        
        if row:
            download = dict(row)
            
            # Parse metadata từ JSON
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
        Xóa một bản ghi tải xuống khỏi cơ sở dữ liệu dựa trên tiêu đề
        
        Args:
            title: Tiêu đề video cần xóa
            
        Returns:
            bool: True nếu xóa thành công, False nếu không
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
        Lấy bản ghi tải xuống theo tiêu đề
        
        Args:
            title: Tiêu đề của video
            
        Returns:
            Dict or None: Thông tin bản ghi hoặc None nếu không tìm thấy
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM downloads WHERE title = ?', (title,))
        row = cursor.fetchone()
        
        if row:
            download = dict(row)
            
            # Parse metadata từ JSON
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
        Cập nhật kích thước file cho một bản ghi tải xuống
        
        Args:
            identifier: URL hoặc ID của video cần cập nhật
            new_filesize: Kích thước file mới (dạng chuỗi, ví dụ: "10.5 MB")
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            print(f"Attempting to update filesize to {new_filesize} for {identifier}")
            
            # Kiểm tra xem identifier là URL hay ID
            if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
                # Trường hợp ID
                cursor.execute('UPDATE downloads SET filesize = ? WHERE id = ?', (new_filesize, identifier))
            else:
                # Trường hợp URL
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