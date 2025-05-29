"""
Data Conversion Logic for Social Download Manager

Handles transformation of data between different schema versions,
converting v1.2.1 flat structure to v2.0 normalized structure.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Set, Union
import logging
import sqlite3
import json
import re
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse

from data.database.connection import SQLiteConnectionManager
from .version_detection import VersionInfo, DatabaseVersion, VersionManager
from data.database.exceptions import DatabaseError, DataValidationError


@dataclass
class ConversionStats:
    """Statistics for data conversion process"""
    total_v1_records: int = 0
    successful_conversions: int = 0
    failed_conversions: int = 0
    content_records_created: int = 0
    download_records_created: int = 0
    skipped_duplicates: int = 0
    parsing_errors: int = 0
    validation_errors: int = 0
    conversion_time_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class V1DownloadRecord:
    """Represents a v1.2.1 download record"""
    id: int
    url: str
    title: str
    filepath: str
    quality: Optional[str]
    format: Optional[str]
    duration: Optional[int]
    filesize: Optional[str]
    status: str
    download_date: str
    metadata: str  # JSON string
    
    def parse_metadata(self) -> Dict[str, Any]:
        """Parse the JSON metadata string"""
        try:
            if not self.metadata:
                return {}
            return json.loads(self.metadata)
        except (json.JSONDecodeError, TypeError) as e:
            return {}


@dataclass
class V2ContentRecord:
    """Represents a v2.0 content record"""
    platform_id: str
    platform_content_id: str
    original_url: str
    title: Optional[str]
    description: Optional[str]
    author_name: Optional[str]
    author_url: Optional[str]
    thumbnail_url: Optional[str]
    duration_seconds: Optional[int]
    view_count: Optional[int]
    like_count: Optional[int]
    content_type: str = 'video'
    published_at: Optional[str] = None
    metadata_json: Optional[str] = None
    status: str = 'active'


@dataclass
class V2DownloadRecord:
    """Represents a v2.0 download record"""
    content_id: int
    file_path: str
    file_name: str
    file_size_bytes: Optional[int]
    format: Optional[str]
    quality: Optional[str]
    status: str = 'pending'
    download_started_at: Optional[str] = None
    download_completed_at: Optional[str] = None
    download_progress: float = 0.0
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata_json: Optional[str] = None


class PlatformDetector:
    """Detects platform and extracts content IDs from URLs"""
    
    PLATFORM_PATTERNS = {
        'tiktok': [
            r'tiktok\.com/@[\w.-]+/video/(\d+)',
            r'vm\.tiktok\.com/(\w+)',
            r'tiktok\.com/t/(\w+)',
        ],
        'youtube': [
            r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'youtu\.be/([a-zA-Z0-9_-]+)',
            r'youtube\.com/embed/([a-zA-Z0-9_-]+)',
        ],
        'instagram': [
            r'instagram\.com/p/([a-zA-Z0-9_-]+)',
            r'instagram\.com/reel/([a-zA-Z0-9_-]+)',
            r'instagram\.com/tv/([a-zA-Z0-9_-]+)',
        ],
        'twitter': [
            r'twitter\.com/\w+/status/(\d+)',
            r'x\.com/\w+/status/(\d+)',
        ],
        'facebook': [
            r'facebook\.com/watch/\?v=(\d+)',
            r'facebook\.com/\w+/videos/(\d+)',
        ]
    }
    
    @classmethod
    def detect_platform_and_id(cls, url: str) -> Tuple[str, str]:
        """
        Detect platform and extract content ID from URL
        
        Returns:
            Tuple of (platform_id, content_id)
        """
        url_lower = url.lower()
        
        for platform, patterns in cls.PLATFORM_PATTERNS.items():
            if platform in url_lower:
                for pattern in patterns:
                    match = re.search(pattern, url, re.IGNORECASE)
                    if match:
                        return platform, match.group(1)
        
        # Fallback: use domain as platform and hash as content ID
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Create a hash-based content ID for unknown platforms
            content_id = hashlib.md5(url.encode()).hexdigest()[:16]
            
            return domain, content_id
        except Exception:
            return 'unknown', hashlib.md5(url.encode()).hexdigest()[:16]


class MetadataParser:
    """Parses and extracts useful information from v1.2.1 metadata"""
    
    @staticmethod
    def parse_filesize_to_bytes(filesize_str: Optional[str]) -> Optional[int]:
        """Convert filesize string (e.g., '8.2MB') to bytes"""
        if not filesize_str:
            return None
        
        try:
            # Extract number and unit
            import re
            match = re.match(r'([0-9.]+)\s*([KMGT]?B)', filesize_str.upper())
            if not match:
                return None
            
            size_num = float(match.group(1))
            unit = match.group(2)
            
            multipliers = {
                'B': 1,
                'KB': 1024,
                'MB': 1024 ** 2,
                'GB': 1024 ** 3,
                'TB': 1024 ** 4
            }
            
            return int(size_num * multipliers.get(unit, 1))
            
        except (ValueError, AttributeError):
            return None
    
    @staticmethod
    def extract_filename_from_path(filepath: str) -> str:
        """Extract filename from full file path"""
        if not filepath:
            return 'unknown_file'
        
        try:
            return Path(filepath).name
        except Exception:
            # Fallback: split by / or \ and take last part
            parts = re.split(r'[/\\]', filepath)
            return parts[-1] if parts else 'unknown_file'
    
    @staticmethod
    def parse_download_date(date_str: str) -> Optional[str]:
        """Parse v1.2.1 download date to ISO format"""
        if not date_str:
            return None
        
        try:
            # Try to parse common v1.2.1 format: "2024/12/25 10:30:00"
            if '/' in date_str and ' ' in date_str:
                dt = datetime.strptime(date_str, '%Y/%m/%d %H:%M:%S')
                return dt.isoformat()
            
            # Try other common formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%d/%m/%Y %H:%M:%S',
                '%d/%m/%Y'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            return None
            
        except Exception:
            return None
    
    @staticmethod
    def extract_metadata_fields(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize metadata fields"""
        extracted = {}
        
        # Common field mappings
        field_mappings = {
            'description': ['description', 'desc', 'caption'],
            'author_name': ['creator', 'author', 'uploader', 'channel'],
            'author_url': ['creator_url', 'author_url', 'channel_url'],
            'thumbnail_url': ['thumbnail', 'thumb', 'thumbnail_url'],
            'view_count': ['views', 'view_count', 'viewCount'],
            'like_count': ['likes', 'like_count', 'likeCount'],
            'published_at': ['published_at', 'upload_date', 'publishedAt']
        }
        
        for target_field, source_fields in field_mappings.items():
            for source_field in source_fields:
                if source_field in metadata and metadata[source_field]:
                    extracted[target_field] = metadata[source_field]
                    break
        
        # Special handling for hashtags
        if 'hashtags' in metadata:
            hashtags = metadata['hashtags']
            if isinstance(hashtags, list):
                extracted['hashtags'] = hashtags
            elif isinstance(hashtags, str):
                # Parse hashtag string
                extracted['hashtags'] = re.findall(r'#\w+', hashtags)
        
        return extracted


class IDataConverter(ABC):
    """Interface for data conversion engines"""
    
    @abstractmethod
    def convert_v1_to_v2(self) -> ConversionStats:
        """Convert v1.2.1 data to v2.0 structure"""
        pass
    
    @abstractmethod
    def validate_conversion_requirements(self) -> Tuple[bool, List[str]]:
        """Validate that conversion can be performed"""
        pass


class SQLiteDataConverter(IDataConverter):
    """SQLite-specific data conversion implementation"""
    
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self.connection_manager = connection_manager
        self.logger = logging.getLogger(__name__)
        self.stats = ConversionStats()
    
    def convert_v1_to_v2(self) -> ConversionStats:
        """Convert v1.2.1 data to v2.0 normalized structure"""
        start_time = datetime.now()
        self.stats = ConversionStats()  # Reset stats
        
        try:
            self.logger.info("Starting v1.2.1 to v2.0 data conversion")
            
            # Validate conversion requirements
            is_valid, errors = self.validate_conversion_requirements()
            if not is_valid:
                self.stats.errors.extend(errors)
                return self.stats
            
            with self.connection_manager.connection() as conn:
                # Load all v1.2.1 records
                v1_records = self._load_v1_records(conn)
                self.stats.total_v1_records = len(v1_records)
                
                self.logger.info(f"Found {len(v1_records)} v1.2.1 records to convert")
                
                # Process each record
                content_id_map = {}  # Maps v1 record ID to v2 content ID
                
                for v1_record in v1_records:
                    try:
                        # Convert to v2 structure
                        content_record, download_record = self._convert_single_record(v1_record)
                        
                        # Check for duplicate content
                        existing_content_id = self._find_existing_content(conn, content_record)
                        
                        if existing_content_id:
                            # Use existing content record
                            content_id = existing_content_id
                            self.stats.skipped_duplicates += 1
                            self.logger.debug(f"Using existing content ID {content_id} for URL: {content_record.original_url}")
                        else:
                            # Insert new content record
                            content_id = self._insert_content_record(conn, content_record)
                            self.stats.content_records_created += 1
                            self.logger.debug(f"Created content ID {content_id} for URL: {content_record.original_url}")
                        
                        # Update download record with content ID
                        download_record.content_id = content_id
                        content_id_map[v1_record.id] = content_id
                        
                        # Insert download record
                        download_id = self._insert_download_record(conn, download_record)
                        self.stats.download_records_created += 1
                        
                        self.stats.successful_conversions += 1
                        
                    except Exception as e:
                        self.stats.failed_conversions += 1
                        error_msg = f"Failed to convert record ID {v1_record.id}: {e}"
                        self.stats.errors.append(error_msg)
                        self.logger.error(error_msg)
                
                # Commit all changes
                conn.commit()
                
                self.stats.conversion_time_seconds = (datetime.now() - start_time).total_seconds()
                
                self.logger.info(f"Data conversion completed in {self.stats.conversion_time_seconds:.2f} seconds")
                self.logger.info(f"Successfully converted {self.stats.successful_conversions}/{self.stats.total_v1_records} records")
                
                return self.stats
                
        except Exception as e:
            self.stats.conversion_time_seconds = (datetime.now() - start_time).total_seconds()
            error_msg = f"Data conversion failed: {e}"
            self.stats.errors.append(error_msg)
            self.logger.error(error_msg)
            return self.stats
    
    def validate_conversion_requirements(self) -> Tuple[bool, List[str]]:
        """Validate that conversion can be performed"""
        errors = []
        
        try:
            with self.connection_manager.connection() as conn:
                cursor = conn.cursor()
                
                # Check if v1.2.1 backup table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='downloads_v1_backup'")
                if not cursor.fetchone():
                    errors.append("downloads_v1_backup table not found - schema transformation must be completed first")
                
                # Check if v2.0 tables exist
                required_tables = ['content', 'downloads']
                for table in required_tables:
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                    if not cursor.fetchone():
                        errors.append(f"Required v2.0 table '{table}' not found")
                
                # Check if v2.0 tables are empty (to avoid duplicate data)
                if not errors:  # Only check if tables exist
                    cursor.execute("SELECT COUNT(*) FROM content")
                    content_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM downloads")
                    downloads_count = cursor.fetchone()[0]
                    
                    if content_count > 0 or downloads_count > 0:
                        errors.append(f"v2.0 tables are not empty (content: {content_count}, downloads: {downloads_count}) - data conversion already performed?")
        
        except Exception as e:
            errors.append(f"Failed to validate conversion requirements: {e}")
        
        return len(errors) == 0, errors
    
    def _load_v1_records(self, conn: sqlite3.Connection) -> List[V1DownloadRecord]:
        """Load all v1.2.1 records from backup table"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, url, title, filepath, quality, format, duration, 
                   filesize, status, download_date, metadata
            FROM downloads_v1_backup
            ORDER BY id
        """)
        
        records = []
        for row in cursor.fetchall():
            record = V1DownloadRecord(
                id=row[0],
                url=row[1],
                title=row[2],
                filepath=row[3],
                quality=row[4],
                format=row[5],
                duration=row[6],
                filesize=row[7],
                status=row[8],
                download_date=row[9],
                metadata=row[10] or '{}'
            )
            records.append(record)
        
        return records
    
    def _convert_single_record(self, v1_record: V1DownloadRecord) -> Tuple[V2ContentRecord, V2DownloadRecord]:
        """Convert a single v1.2.1 record to v2.0 structure"""
        
        # Parse metadata
        metadata = v1_record.parse_metadata()
        extracted_metadata = MetadataParser.extract_metadata_fields(metadata)
        
        # Detect platform and content ID
        platform_id, platform_content_id = PlatformDetector.detect_platform_and_id(v1_record.url)
        
        # Create content record
        content_record = V2ContentRecord(
            platform_id=platform_id,
            platform_content_id=platform_content_id,
            original_url=v1_record.url,
            title=v1_record.title,
            description=extracted_metadata.get('description'),
            author_name=extracted_metadata.get('author_name'),
            author_url=extracted_metadata.get('author_url'),
            thumbnail_url=extracted_metadata.get('thumbnail_url'),
            duration_seconds=v1_record.duration,
            view_count=extracted_metadata.get('view_count'),
            like_count=extracted_metadata.get('like_count'),
            content_type='video',
            published_at=extracted_metadata.get('published_at'),
            metadata_json=json.dumps(metadata) if metadata else None,
            status='active'
        )
        
        # Create download record
        file_size_bytes = MetadataParser.parse_filesize_to_bytes(v1_record.filesize)
        file_name = MetadataParser.extract_filename_from_path(v1_record.filepath)
        
        # Convert status
        download_status = self._convert_download_status(v1_record.status)
        
        # Parse download dates
        download_completed_at = MetadataParser.parse_download_date(v1_record.download_date)
        
        download_record = V2DownloadRecord(
            content_id=0,  # Will be set after content insertion
            file_path=v1_record.filepath,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            format=v1_record.format,
            quality=v1_record.quality,
            status=download_status,
            download_started_at=download_completed_at,  # Use same for both if successful
            download_completed_at=download_completed_at if download_status == 'completed' else None,
            download_progress=1.0 if download_status == 'completed' else 0.0,
            error_message=None if download_status == 'completed' else f"Original status: {v1_record.status}",
            retry_count=0,
            metadata_json=json.dumps({
                'v1_record_id': v1_record.id,
                'original_status': v1_record.status,
                'migration_timestamp': datetime.now().isoformat()
            })
        )
        
        return content_record, download_record
    
    def _convert_download_status(self, v1_status: str) -> str:
        """Convert v1.2.1 status to v2.0 status"""
        if not v1_status:
            return 'unknown'
        
        status_mapping = {
            'success': 'completed',
            'completed': 'completed',
            'finished': 'completed',
            'done': 'completed',
            'failed': 'failed',
            'error': 'failed',
            'pending': 'pending',
            'downloading': 'in_progress',
            'in_progress': 'in_progress',
            'paused': 'paused',
            'cancelled': 'cancelled',
            'canceled': 'cancelled'
        }
        
        v1_status_lower = v1_status.lower()
        return status_mapping.get(v1_status_lower, 'unknown')
    
    def _find_existing_content(self, conn: sqlite3.Connection, content_record: V2ContentRecord) -> Optional[int]:
        """Find existing content record by URL or platform content ID"""
        cursor = conn.cursor()
        
        # First try by exact URL match
        cursor.execute("SELECT id FROM content WHERE original_url = ?", (content_record.original_url,))
        result = cursor.fetchone()
        if result:
            return result[0]
        
        # Then try by platform and content ID
        cursor.execute("""
            SELECT id FROM content 
            WHERE platform_id = ? AND platform_content_id = ?
        """, (content_record.platform_id, content_record.platform_content_id))
        result = cursor.fetchone()
        if result:
            return result[0]
        
        return None
    
    def _insert_content_record(self, conn: sqlite3.Connection, content_record: V2ContentRecord) -> int:
        """Insert content record and return the new ID"""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO content (
                platform_id, platform_content_id, original_url, title, description,
                author_name, author_url, thumbnail_url, duration_seconds,
                view_count, like_count, content_type, published_at, metadata_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            content_record.platform_id,
            content_record.platform_content_id,
            content_record.original_url,
            content_record.title,
            content_record.description,
            content_record.author_name,
            content_record.author_url,
            content_record.thumbnail_url,
            content_record.duration_seconds,
            content_record.view_count,
            content_record.like_count,
            content_record.content_type,
            content_record.published_at,
            content_record.metadata_json,
            content_record.status
        ))
        
        return cursor.lastrowid
    
    def _insert_download_record(self, conn: sqlite3.Connection, download_record: V2DownloadRecord) -> int:
        """Insert download record and return the new ID"""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO downloads (
                content_id, file_path, file_name, file_size_bytes, format, quality,
                status, download_started_at, download_completed_at, download_progress,
                error_message, retry_count, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            download_record.content_id,
            download_record.file_path,
            download_record.file_name,
            download_record.file_size_bytes,
            download_record.format,
            download_record.quality,
            download_record.status,
            download_record.download_started_at,
            download_record.download_completed_at,
            download_record.download_progress,
            download_record.error_message,
            download_record.retry_count,
            download_record.metadata_json
        ))
        
        return cursor.lastrowid


class DataConversionManager:
    """High-level manager for data conversion operations"""
    
    def __init__(self, connection_manager: SQLiteConnectionManager):
        self.connection_manager = connection_manager
        self.converter = SQLiteDataConverter(connection_manager)
        self.version_manager = VersionManager(connection_manager)
        self.logger = logging.getLogger(__name__)
    
    def execute_data_conversion(self) -> Tuple[bool, str, ConversionStats]:
        """
        Execute complete data conversion from v1.2.1 to v2.0
        
        Returns:
            Tuple of (success, message, stats)
        """
        try:
            # Validate current state
            current_version = self.version_manager.get_current_version_info()
            
            if current_version.version != DatabaseVersion.V2_0_0:
                return False, f"Database must be at v2.0.0 for data conversion (current: {current_version.version.value})", ConversionStats()
            
            if not current_version.schema_valid:
                return False, "Database schema is not valid - run schema transformation first", ConversionStats()
            
            # Execute conversion
            self.logger.info("Starting data conversion process")
            stats = self.converter.convert_v1_to_v2()
            
            if stats.failed_conversions == 0:
                success_message = f"Data conversion completed successfully: {stats.successful_conversions} records converted"
                if stats.skipped_duplicates > 0:
                    success_message += f" ({stats.skipped_duplicates} duplicates skipped)"
                
                return True, success_message, stats
            else:
                partial_message = f"Data conversion completed with errors: {stats.successful_conversions} succeeded, {stats.failed_conversions} failed"
                return False, partial_message, stats
                
        except Exception as e:
            self.logger.error(f"Data conversion failed: {e}")
            error_stats = ConversionStats()
            error_stats.errors.append(str(e))
            return False, f"Data conversion error: {e}", error_stats 