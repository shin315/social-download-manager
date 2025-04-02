import os
import re
import shutil
import unicodedata
import subprocess
import glob
import logging
import pkg_resources
import requests
import string

logger = logging.getLogger(__name__)

def check_ytdlp_version():
    """
    Kiểm tra phiên bản yt-dlp hiện tại và cảnh báo nếu quá cũ
    
    Returns:
        tuple: (bool, str) - Phiên bản OK hay không, phiên bản mới nhất nếu có
    """
    try:
        # Lấy phiên bản hiện tại
        current_version = pkg_resources.get_distribution("yt-dlp").version
        logger.info(f"Current yt-dlp version: {current_version}")
        
        try:
            # Kiểm tra phiên bản mới nhất từ PyPI
            response = requests.get("https://pypi.org/pypi/yt-dlp/json", timeout=5)
            if response.status_code == 200:
                latest_version = response.json()["info"]["version"]
                logger.info(f"Latest yt-dlp version: {latest_version}")
                
                # Cảnh báo nếu phiên bản hiện tại cũ hơn
                current_year_month = current_version.split('.')[:2]
                latest_year_month = latest_version.split('.')[:2]
                
                if current_year_month[0] < latest_year_month[0] or (current_year_month[0] == latest_year_month[0] and current_year_month[1] < latest_year_month[1]):
                    logger.warning(f"yt-dlp version {current_version} may be outdated. Latest version: {latest_version}")
                    return False, latest_version
            else:
                logger.warning(f"Failed to check latest yt-dlp version: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error checking latest yt-dlp version: {e}")
        
        return True, current_version
    except Exception as e:
        logger.error(f"Error checking yt-dlp version: {e}")
        return True, "unknown"  # Mặc định cho phép tiếp tục

def check_ffmpeg_installed():
    """
    Check if FFmpeg is installed and accessible in the system path.
    
    Returns:
        tuple: (bool, str) - True if FFmpeg is installed, False otherwise
                           - Error message if FFmpeg is not installed
    """
    try:
        # First check if ffmpeg exists in PATH
        ffmpeg_path = shutil.which('ffmpeg')
        
        # If not found in PATH, check common installation locations
        if not ffmpeg_path:
            # Common locations to check on Windows
            common_locations = [
                # Program Files
                os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'ffmpeg', 'bin', 'ffmpeg.exe'),
                os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'ffmpeg', 'bin', 'ffmpeg.exe'),
                # User directories
                os.path.join(os.environ.get('USERPROFILE', 'C:\\Users\\Default'), 'ffmpeg', 'bin', 'ffmpeg.exe'),
                # Root of C drive
                'C:\\ffmpeg\\bin\\ffmpeg.exe',
                'C:\\ffmpeg-*\\bin\\ffmpeg.exe',
            ]
            
            # Add any other drive letters
            for drive in string.ascii_uppercase:
                pattern = f"{drive}:\\ffmpeg*\\bin\\ffmpeg.exe"
                matches = glob.glob(pattern)
                if matches:
                    ffmpeg_path = matches[0]
                    break
            
            # Direct check of common locations if glob doesn't work
            if not ffmpeg_path:
                for location in common_locations:
                    if '*' in location:
                        # Handle wildcards with glob
                        matches = glob.glob(location)
                        if matches:
                            ffmpeg_path = matches[0]
                            break
                    elif os.path.exists(location):
                        ffmpeg_path = location
                        break
        
        if not ffmpeg_path:
            return False, "FFmpeg not found in system PATH or common locations"
        
        # Verify it works by running a simple command
        subprocess.run(
            [ffmpeg_path, '-version'], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=True
        )
        return True, ffmpeg_path
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        return False, f"Error checking FFmpeg: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error checking FFmpeg: {str(e)}"

def slugify(text):
    """
    Convert text to a safe slug for filenames.
    Remove special characters, replace spaces with hyphens.
    """
    # Normalize Unicode text (e.g., 'é' -> 'e')
    text = unicodedata.normalize('NFKD', text)
    text = ''.join([c for c in text if not unicodedata.combining(c)])
    
    # Replace spaces with hyphens and convert to lowercase
    text = text.lower().replace(' ', '-')
    
    # Remove characters that aren't letters, numbers, or hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    
    # Remove consecutive hyphens
    text = re.sub(r'[-\s]+', '-', text)
    
    # Ensure no hyphens at beginning or end
    return text.strip('-')

def get_resource_path(relative_path):
    """
    Get the correct path to resources, works both during development and when packaged
    
    Args:
        relative_path: Path relative to the assets directory
        
    Returns:
        str: Absolute path to the resource
    """
    import sys
    import os
    
    # Check if the application is frozen (compiled with PyInstaller)
    if getattr(sys, 'frozen', False):
        # If we're running as a bundled exe, use the sys._MEIPASS path
        base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(sys.executable)))
    else:
        # If we're running in a normal Python environment, use the current directory
        base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    return os.path.join(base_path, relative_path) 