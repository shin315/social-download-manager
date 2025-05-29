"""
Advanced Validation Logic for Social Download Manager v2.0

Comprehensive validation functions, business rules, and validation patterns
for ensuring data integrity across all models.
"""

import json
import re
import urllib.parse
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from urllib.parse import urlparse, parse_qs

from pydantic import ValidationError, field_validator
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# URL VALIDATION
# =============================================================================

class URLValidator:
    """Advanced URL validation for different platforms and use cases"""
    
    # Platform URL patterns
    PLATFORM_PATTERNS = {
        'tiktok': [
            r'https?://(?:www\.|vm\.)?tiktok\.com/[@\w\-\.]+/?',
            r'https?://(?:www\.)?tiktok\.com/@[\w\-\.]+/video/\d+/?',
            r'https?://vm\.tiktok\.com/[\w\-]+/?'
        ],
        'youtube': [
            r'https?://(?:www\.)?youtube\.com/watch\?v=[\w\-_]+',
            r'https?://(?:www\.)?youtube\.com/shorts/[\w\-_]+',
            r'https?://youtu\.be/[\w\-_]+',
            r'https?://(?:www\.)?youtube\.com/embed/[\w\-_]+',
            r'https?://(?:www\.)?youtube\.com/channel/[\w\-_]+',
            r'https?://(?:www\.)?youtube\.com/@[\w\-_]+',
            r'https?://(?:www\.)?youtube\.com/c/[\w\-_]+',
            r'https?://(?:www\.)?youtube\.com/user/[\w\-_]+'
        ],
        'instagram': [
            r'https?://(?:www\.)?instagram\.com/p/[\w\-_]+/?',
            r'https?://(?:www\.)?instagram\.com/reel/[\w\-_]+/?',
            r'https?://(?:www\.)?instagram\.com/stories/[\w\-_.]+/\d+/?',
            r'https?://(?:www\.)?instagram\.com/[\w\-_.]+/?'
        ]
    }
    
    @classmethod
    def validate_url_format(cls, url: str) -> str:
        """Basic URL format validation"""
        if not url or not url.strip():
            raise ValueError("URL cannot be empty")
        
        url = url.strip()
        
        # Basic URL format check
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
            
            if parsed.scheme not in ['http', 'https']:
                raise ValueError("URL must use HTTP or HTTPS protocol")
            
        except Exception as e:
            raise ValueError(f"Invalid URL format: {str(e)}")
        
        return url
    
    @classmethod
    def validate_platform_url(cls, url: str, platform: str) -> str:
        """Validate URL belongs to specific platform"""
        url = cls.validate_url_format(url)
        
        platform_lower = platform.lower()
        if platform_lower not in cls.PLATFORM_PATTERNS:
            # For unknown platforms, just validate basic format
            return url
        
        patterns = cls.PLATFORM_PATTERNS[platform_lower]
        for pattern in patterns:
            if re.match(pattern, url, re.IGNORECASE):
                return url
        
        raise ValueError(f"URL does not match {platform} format patterns")
    
    @classmethod
    def extract_content_id(cls, url: str, platform: str) -> Optional[str]:
        """Extract content ID from platform URL"""
        platform_lower = platform.lower()
        
        try:
            parsed = urlparse(url)
            
            if platform_lower == 'youtube':
                # YouTube video ID extraction
                if 'watch' in parsed.path:
                    query_params = parse_qs(parsed.query)
                    return query_params.get('v', [None])[0]
                elif '/shorts/' in parsed.path:
                    return parsed.path.split('/shorts/')[-1].split('/')[0]
                elif 'youtu.be' in parsed.netloc:
                    return parsed.path.lstrip('/')
                elif '/embed/' in parsed.path:
                    return parsed.path.split('/embed/')[-1].split('/')[0]
            
            elif platform_lower == 'tiktok':
                # TikTok video ID extraction
                if '/video/' in parsed.path:
                    return parsed.path.split('/video/')[-1].split('/')[0]
                elif 'vm.tiktok.com' in parsed.netloc:
                    return parsed.path.lstrip('/')
            
            elif platform_lower == 'instagram':
                # Instagram post ID extraction
                if '/p/' in parsed.path:
                    return parsed.path.split('/p/')[-1].split('/')[0]
                elif '/reel/' in parsed.path:
                    return parsed.path.split('/reel/')[-1].split('/')[0]
                elif '/stories/' in parsed.path:
                    parts = parsed.path.split('/stories/')[-1].split('/')
                    return f"{parts[0]}_{parts[1]}" if len(parts) > 1 else None
        
        except Exception as e:
            logger.warning(f"Could not extract content ID from {url}: {e}")
        
        return None
    
    @classmethod
    def normalize_url(cls, url: str, platform: str) -> str:
        """Normalize URL to canonical format"""
        url = cls.validate_platform_url(url, platform)
        platform_lower = platform.lower()
        
        try:
            parsed = urlparse(url)
            
            if platform_lower == 'youtube':
                content_id = cls.extract_content_id(url, platform)
                if content_id:
                    return f"https://www.youtube.com/watch?v={content_id}"
            
            elif platform_lower == 'tiktok':
                content_id = cls.extract_content_id(url, platform)
                if content_id and content_id.isdigit():
                    # For numeric IDs, construct standard URL
                    return f"https://www.tiktok.com/video/{content_id}"
            
            elif platform_lower == 'instagram':
                if '/p/' in parsed.path:
                    content_id = cls.extract_content_id(url, platform)
                    if content_id:
                        return f"https://www.instagram.com/p/{content_id}/"
                elif '/reel/' in parsed.path:
                    content_id = cls.extract_content_id(url, platform)
                    if content_id:
                        return f"https://www.instagram.com/reel/{content_id}/"
        
        except Exception as e:
            logger.warning(f"Could not normalize URL {url}: {e}")
        
        return url


# =============================================================================
# JSON VALIDATION
# =============================================================================

class JSONValidator:
    """Advanced JSON validation with schema checking"""
    
    @staticmethod
    def validate_json_string(value: str, allow_empty: bool = True) -> str:
        """Validate and normalize JSON string"""
        if not value and allow_empty:
            return "{}"
        
        if not value and not allow_empty:
            raise ValueError("JSON string cannot be empty")
        
        try:
            # Parse to validate
            parsed = json.loads(value)
            # Re-serialize to normalize formatting
            return json.dumps(parsed, separators=(',', ':'), ensure_ascii=False)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
    
    @staticmethod
    def validate_json_array(value: str, item_type: type = str) -> str:
        """Validate JSON array with type checking"""
        json_str = JSONValidator.validate_json_string(value)
        
        try:
            parsed = json.loads(json_str)
            if not isinstance(parsed, list):
                raise ValueError("JSON value must be an array")
            
            # Type check items if specified
            if item_type and parsed:
                for item in parsed:
                    if not isinstance(item, item_type):
                        raise ValueError(f"Array items must be of type {item_type.__name__}")
            
            return json_str
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON array format")
    
    @staticmethod
    def validate_json_object(value: str, required_keys: Optional[List[str]] = None) -> str:
        """Validate JSON object with optional required keys"""
        json_str = JSONValidator.validate_json_string(value)
        
        try:
            parsed = json.loads(json_str)
            if not isinstance(parsed, dict):
                raise ValueError("JSON value must be an object")
            
            # Check required keys
            if required_keys:
                missing_keys = [key for key in required_keys if key not in parsed]
                if missing_keys:
                    raise ValueError(f"Missing required keys: {missing_keys}")
            
            return json_str
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON object format")
    
    @staticmethod
    def validate_metadata_value(value: str, data_type: str) -> str:
        """Validate metadata value based on its data type"""
        if not value:
            return value
        
        try:
            if data_type == "string":
                return str(value)
            elif data_type == "integer":
                int(value)  # Validate it's a valid integer
                return value
            elif data_type == "float":
                float(value)  # Validate it's a valid float
                return value
            elif data_type == "boolean":
                if value.lower() not in ['true', 'false', '0', '1']:
                    raise ValueError("Boolean value must be 'true', 'false', '0', or '1'")
                return value
            elif data_type == "json":
                return JSONValidator.validate_json_string(value)
            elif data_type == "timestamp":
                # Validate timestamp format
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return value
            else:
                # Unknown data type, treat as string
                return str(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid {data_type} value: {str(e)}")


# =============================================================================
# NUMERIC VALIDATION
# =============================================================================

class NumericValidator:
    """Advanced numeric validation with business rules"""
    
    @staticmethod
    def validate_positive_integer(value: int, field_name: str = "value") -> int:
        """Validate positive integer"""
        if value is None:
            return value
        
        if not isinstance(value, int):
            raise ValueError(f"{field_name} must be an integer")
        
        if value < 0:
            raise ValueError(f"{field_name} must be positive")
        
        return value
    
    @staticmethod
    def validate_percentage(value: float, field_name: str = "percentage") -> float:
        """Validate percentage (0-100)"""
        if value is None:
            return value
        
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"{field_name} must be a number")
        
        if value < 0 or value > 100:
            raise ValueError(f"{field_name} must be between 0 and 100")
        
        return value
    
    @staticmethod
    def validate_decimal_precision(value: Decimal, max_digits: int, decimal_places: int) -> Decimal:
        """Validate decimal precision"""
        if value is None:
            return value
        
        try:
            if not isinstance(value, Decimal):
                value = Decimal(str(value))
        except (ValueError, InvalidOperation):
            raise ValueError("Invalid decimal value")
        
        # Check total digits
        sign, digits, exponent = value.as_tuple()
        total_digits = len(digits)
        
        if total_digits > max_digits:
            raise ValueError(f"Too many digits: {total_digits} > {max_digits}")
        
        # Check decimal places
        if exponent < -decimal_places:
            raise ValueError(f"Too many decimal places: {-exponent} > {decimal_places}")
        
        return value
    
    @staticmethod
    def validate_speed_bps(value: int) -> int:
        """Validate download speed in bytes per second"""
        if value is None:
            return value
        
        value = NumericValidator.validate_positive_integer(value, "speed")
        
        # Reasonable limits for download speed (0 to 10 Gbps)
        max_speed = 10 * 1024 * 1024 * 1024  # 10 GB/s
        if value > max_speed:
            raise ValueError(f"Speed {value} bps exceeds maximum reasonable limit")
        
        return value
    
    @staticmethod
    def validate_file_size(value: int) -> int:
        """Validate file size in bytes"""
        if value is None:
            return value
        
        value = NumericValidator.validate_positive_integer(value, "file size")
        
        # Reasonable limit for file size (100 GB)
        max_size = 100 * 1024 * 1024 * 1024
        if value > max_size:
            raise ValueError(f"File size {value} bytes exceeds maximum reasonable limit")
        
        return value


# =============================================================================
# STRING VALIDATION
# =============================================================================

class StringValidator:
    """Advanced string validation with format checking"""
    
    @staticmethod
    def validate_slug(value: str) -> str:
        """Validate URL-friendly slug"""
        if not value:
            raise ValueError("Slug cannot be empty")
        
        value = value.strip().lower()
        
        # Check for valid slug pattern (alphanumeric, hyphens, underscores)
        if not re.match(r'^[a-z0-9_-]+$', value):
            raise ValueError("Slug can only contain lowercase letters, numbers, hyphens, and underscores")
        
        # Check length
        if len(value) > 100:
            raise ValueError("Slug too long (maximum 100 characters)")
        
        return value
    
    @staticmethod
    def validate_filename(value: str, allow_path: bool = False) -> str:
        """Validate filename with optional path support"""
        if not value:
            raise ValueError("Filename cannot be empty")
        
        value = value.strip()
        
        if allow_path:
            # Validate as path
            try:
                path = Path(value)
                # Check for dangerous patterns
                if '..' in path.parts:
                    raise ValueError("Path cannot contain '..' components")
                return value
            except Exception as e:
                raise ValueError(f"Invalid path: {str(e)}")
        else:
            # Validate as simple filename
            invalid_chars = r'<>:"/\\|?*'
            if any(char in value for char in invalid_chars):
                raise ValueError(f"Filename cannot contain: {invalid_chars}")
            
            if len(value) > 255:
                raise ValueError("Filename too long (maximum 255 characters)")
        
        return value
    
    @staticmethod
    def validate_uuid_string(value: str) -> str:
        """Validate UUID string format"""
        if not value:
            raise ValueError("UUID cannot be empty")
        
        value = value.strip()
        
        # UUID pattern: 8-4-4-4-12 hex digits
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, value, re.IGNORECASE):
            raise ValueError("Invalid UUID format")
        
        return value.lower()
    
    @staticmethod
    def validate_platform_content_id(value: str, platform: str) -> str:
        """Validate platform-specific content ID format"""
        if not value:
            raise ValueError("Content ID cannot be empty")
        
        value = value.strip()
        platform_lower = platform.lower()
        
        if platform_lower == 'youtube':
            # YouTube video IDs are 11 characters, alphanumeric + hyphens/underscores
            if not re.match(r'^[a-zA-Z0-9_-]{11}$', value):
                raise ValueError("Invalid YouTube video ID format")
        
        elif platform_lower == 'tiktok':
            # TikTok video IDs are typically long numeric strings
            if not re.match(r'^\d{15,25}$', value):
                raise ValueError("Invalid TikTok video ID format")
        
        elif platform_lower == 'instagram':
            # Instagram post IDs are alphanumeric strings
            if not re.match(r'^[a-zA-Z0-9_-]+$', value):
                raise ValueError("Invalid Instagram post ID format")
        
        return value


# =============================================================================
# DATETIME VALIDATION
# =============================================================================

class DateTimeValidator:
    """Advanced datetime validation with business rules"""
    
    @staticmethod
    def validate_future_datetime(value: datetime, field_name: str = "datetime") -> datetime:
        """Validate datetime is in the future"""
        if value is None:
            return value
        
        now = datetime.now(timezone.utc)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        
        if value <= now:
            raise ValueError(f"{field_name} must be in the future")
        
        return value
    
    @staticmethod
    def validate_past_datetime(value: datetime, field_name: str = "datetime") -> datetime:
        """Validate datetime is in the past"""
        if value is None:
            return value
        
        now = datetime.now(timezone.utc)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        
        if value >= now:
            raise ValueError(f"{field_name} must be in the past")
        
        return value
    
    @staticmethod
    def validate_reasonable_date_range(value: datetime, 
                                     min_date: Optional[datetime] = None,
                                     max_date: Optional[datetime] = None) -> datetime:
        """Validate datetime is within reasonable range"""
        if value is None:
            return value
        
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        
        # Default reasonable range: 2005 (YouTube launch) to 10 years in future
        if min_date is None:
            min_date = datetime(2005, 1, 1, tzinfo=timezone.utc)
        
        if max_date is None:
            max_date = datetime.now(timezone.utc) + timedelta(days=365 * 10)
        
        if value < min_date:
            raise ValueError(f"Date too early (before {min_date.year})")
        
        if value > max_date:
            raise ValueError(f"Date too far in future (after {max_date.year})")
        
        return value
    
    @staticmethod
    def validate_duration_seconds(value: int) -> int:
        """Validate content duration in seconds"""
        if value is None:
            return value
        
        value = NumericValidator.validate_positive_integer(value, "duration")
        
        # Reasonable limits: 1 second to 24 hours
        max_duration = 24 * 60 * 60  # 24 hours
        if value > max_duration:
            raise ValueError(f"Duration {value} seconds exceeds maximum (24 hours)")
        
        return value


# =============================================================================
# BUSINESS RULE VALIDATORS
# =============================================================================

class BusinessRuleValidator:
    """High-level business rule validation"""
    
    @staticmethod
    def validate_download_request(content_data: Dict[str, Any], 
                                download_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate download request business rules"""
        errors = []
        
        # Check content status
        content_status = content_data.get('status')
        if content_status == 'failed':
            errors.append("Cannot download failed content")
        elif content_status == 'processing':
            errors.append("Content is still being processed")
        
        # Check if content URL is valid for download
        original_url = content_data.get('original_url')
        if not original_url:
            errors.append("Content must have a valid URL")
        
        # Check output directory
        output_dir = download_data.get('output_directory')
        if not output_dir:
            errors.append("Output directory is required")
        else:
            try:
                output_path = Path(output_dir)
                if not output_path.is_absolute():
                    errors.append("Output directory must be absolute path")
            except Exception:
                errors.append("Invalid output directory path")
        
        # Check retry limits
        retry_count = download_data.get('retry_count', 0)
        max_retries = download_data.get('max_retries', 3)
        if retry_count >= max_retries:
            errors.append(f"Maximum retries ({max_retries}) exceeded")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_content_metadata_consistency(content_data: Dict[str, Any], 
                                            metadata_list: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate content and metadata consistency"""
        errors = []
        
        content_type = content_data.get('content_type')
        platform_id = content_data.get('platform_id')
        
        # Check for required metadata based on content type
        if content_type == 'video':
            has_duration = any(
                m.get('metadata_key') == 'duration' for m in metadata_list
            )
            if not has_duration:
                errors.append("Video content must have duration metadata")
        
        # Check metadata belongs to same platform
        for metadata in metadata_list:
            if metadata.get('content_id') != content_data.get('id'):
                errors.append("Metadata content_id mismatch")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_quality_options(content_data: Dict[str, Any], 
                               quality_options: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate quality options are reasonable"""
        errors = []
        
        content_type = content_data.get('content_type')
        
        for option in quality_options:
            # Check resolution makes sense for content type
            if content_type == 'audio' and option.get('resolution_width'):
                errors.append("Audio content cannot have video resolution")
            
            # Check bitrate ranges
            bitrate = option.get('bitrate_kbps')
            if bitrate:
                if content_type == 'video' and bitrate > 50000:  # 50 Mbps
                    errors.append(f"Video bitrate {bitrate} kbps seems too high")
                elif content_type == 'audio' and bitrate > 1000:  # 1 Mbps
                    errors.append(f"Audio bitrate {bitrate} kbps seems too high")
            
            # Check file size estimates
            file_size = option.get('estimated_file_size')
            duration = content_data.get('duration_seconds')
            if file_size and duration and bitrate:
                # Rough estimate: bitrate * duration / 8 (convert bits to bytes)
                expected_size = (bitrate * 1000 * duration) // 8
                if abs(file_size - expected_size) > expected_size * 0.5:  # 50% tolerance
                    errors.append("File size estimate doesn't match bitrate and duration")
        
        return len(errors) == 0, errors


# =============================================================================
# CUSTOM VALIDATION DECORATORS
# =============================================================================

def validate_platform_specific(platform_field: str):
    """Decorator for platform-specific validation"""
    def decorator(validator_func: Callable) -> Callable:
        def wrapper(cls, value: Any, info=None) -> Any:
            # Get platform from model data
            if info and hasattr(info.data, platform_field):
                platform = getattr(info.data, platform_field)
                return validator_func(cls, value, platform)
            return validator_func(cls, value)
        return wrapper
    return decorator


def validate_conditional(condition_field: str, condition_value: Any):
    """Decorator for conditional validation based on another field"""
    def decorator(validator_func: Callable) -> Callable:
        def wrapper(cls, value: Any, info=None) -> Any:
            # Check condition
            if info and hasattr(info.data, condition_field):
                field_value = getattr(info.data, condition_field)
                if field_value == condition_value:
                    return validator_func(cls, value)
            return value
        return wrapper
    return decorator


# =============================================================================
# VALIDATION RULE SETS
# =============================================================================

class ValidationRuleSets:
    """Pre-defined validation rule sets for common scenarios"""
    
    CONTENT_RULES = {
        'required_fields': ['platform_id', 'original_url', 'content_type'],
        'url_validation': True,
        'status_progression': {
            'pending': ['downloading', 'failed', 'cancelled'],
            'downloading': ['processing', 'completed', 'failed', 'paused', 'cancelled'],
            'processing': ['completed', 'failed'],
            'completed': [],  # Terminal state
            'failed': ['pending'],  # Can retry
            'cancelled': ['pending'],  # Can restart
            'paused': ['downloading', 'cancelled']
        }
    }
    
    DOWNLOAD_RULES = {
        'required_fields': ['content_id', 'output_directory'],
        'max_retries': 5,
        'max_concurrent_downloads': 10,
        'status_progression': {
            'queued': ['starting', 'cancelled'],
            'starting': ['downloading', 'failed'],
            'downloading': ['processing', 'completed', 'failed', 'paused', 'cancelled'],
            'processing': ['completed', 'failed'],
            'completed': [],  # Terminal state
            'failed': ['retrying', 'cancelled'],
            'cancelled': [],  # Terminal state
            'paused': ['downloading', 'cancelled'],
            'retrying': ['downloading', 'failed']
        }
    }
    
    PLATFORM_SPECIFIC_RULES = {
        'tiktok': {
            'max_duration': 10 * 60,  # 10 minutes
            'required_metadata': ['video_type'],
            'url_patterns': URLValidator.PLATFORM_PATTERNS['tiktok']
        },
        'youtube': {
            'max_duration': 12 * 60 * 60,  # 12 hours
            'required_metadata': ['video_type'],
            'url_patterns': URLValidator.PLATFORM_PATTERNS['youtube']
        },
        'instagram': {
            'max_duration': 60 * 60,  # 1 hour
            'required_metadata': ['media_type'],
            'url_patterns': URLValidator.PLATFORM_PATTERNS['instagram']
        }
    }


# =============================================================================
# VALIDATION ERROR FORMATTING
# =============================================================================

class ValidationErrorFormatter:
    """Format validation errors for user-friendly display"""
    
    @staticmethod
    def format_pydantic_error(error: ValidationError) -> Dict[str, Any]:
        """Format Pydantic validation error"""
        formatted_errors = []
        
        for error_detail in error.errors():
            field_path = ' -> '.join(str(loc) for loc in error_detail['loc'])
            formatted_errors.append({
                'field': field_path,
                'message': error_detail['msg'],
                'type': error_detail['type'],
                'input': error_detail.get('input')
            })
        
        return {
            'validation_failed': True,
            'error_count': len(formatted_errors),
            'errors': formatted_errors
        }
    
    @staticmethod
    def format_business_rule_errors(errors: List[str]) -> Dict[str, Any]:
        """Format business rule validation errors"""
        return {
            'business_rule_violations': True,
            'error_count': len(errors),
            'errors': [{'message': error, 'type': 'business_rule'} for error in errors]
        }


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def validate_model_data(model_class: type, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Validate data against a Pydantic model"""
    try:
        model_instance = model_class.model_validate(data)
        return True, {'valid': True, 'data': model_instance.model_dump()}
    except ValidationError as e:
        return False, ValidationErrorFormatter.format_pydantic_error(e)


def validate_status_transition(current_status: str, new_status: str, 
                             entity_type: str) -> Tuple[bool, Optional[str]]:
    """Validate status transition is allowed"""
    rules = ValidationRuleSets.CONTENT_RULES if entity_type == 'content' else ValidationRuleSets.DOWNLOAD_RULES
    
    allowed_transitions = rules['status_progression'].get(current_status, [])
    
    if new_status in allowed_transitions:
        return True, None
    else:
        return False, f"Cannot transition from {current_status} to {new_status}"


def get_platform_validation_rules(platform: str) -> Dict[str, Any]:
    """Get validation rules for specific platform"""
    return ValidationRuleSets.PLATFORM_SPECIFIC_RULES.get(platform.lower(), {}) 