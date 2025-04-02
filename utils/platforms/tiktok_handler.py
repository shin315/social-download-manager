import yt_dlp
import os
import time
import subprocess
import re
import logging
from datetime import datetime
from PyQt6.QtCore import pyqtSignal

from ..platform_handler import PlatformHandler
from ..video_info import VideoInfo
from ..download_utils import slugify, check_ffmpeg_installed, get_resource_path

logger = logging.getLogger(__name__)

class TikTokHandler(PlatformHandler):
    """Handler for TikTok videos"""
    
    def __init__(self):
        super().__init__()
        self.converting_mp3_urls = set()  # Track URLs currently being converted to MP3
    
    def get_video_info(self, url):
        """Get video information from TikTok URL with improved error handling"""
        if not self.is_valid_url(url):
            info = VideoInfo()
            info.url = url
            info.title = "Invalid TikTok URL"
            info.platform = self.get_platform_name()
            self.info_signal.emit(url, info.copy())
            return info
            
        info = VideoInfo()
        info.url = url
        info.platform = self.get_platform_name()
        
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    # Extract info
                    result = ydl.extract_info(url, download=False)
                    
                    if result:
                        try:
                            # Basic info
                            info.title = result.get('title', 'Unknown Title')
                            info.thumbnail = result.get('thumbnail', '')
                            info.duration = result.get('duration', 0)
                            
                            # Creator info
                            info.creator = result.get('creator', result.get('uploader', 'Unknown'))
                            info.creator_url = result.get('uploader_url', '')
                            
                            # Content info
                            info.description = result.get('description', '')
                            
                            # Try to extract TikTok caption and hashtags
                            if info.description:
                                # Extract hashtags if available
                                hashtags = re.findall(r'#\w+', info.description)
                                if hashtags:
                                    info.hashtags = hashtags
                                info.caption = info.description
                            
                            # Stats
                            info.like_count = result.get('like_count', 0)
                            
                            # Platform specific
                            info.platform_id = result.get('id', '')
                            
                            # Get available formats
                            if 'formats' in result:
                                for fmt in result['formats']:
                                    # Skip audio-only formats for TikTok
                                    if fmt.get('vcodec', '') == 'none':
                                        continue
                                        
                                    format_info = {
                                        'format_id': fmt.get('format_id', ''),
                                        'ext': fmt.get('ext', 'mp4'),
                                        'filesize': fmt.get('filesize', 0),
                                    }
                                    
                                    # Handle quality
                                    height = fmt.get('height', 0)
                                    if height:
                                        format_info['height'] = height
                                        if height <= 360:
                                            format_info['quality'] = '360p'
                                        elif height <= 480:
                                            format_info['quality'] = '480p'
                                        elif height <= 720:
                                            format_info['quality'] = '720p'
                                        elif height <= 1080:
                                            format_info['quality'] = '1080p'
                                        else:
                                            format_info['quality'] = f'{height}p'
                                    else:
                                        format_info['quality'] = 'unknown'
                                        
                                    info.formats.append(format_info)
                            
                            # Sort formats by quality (highest first)
                            info.formats.sort(key=lambda x: x.get('height', 0), reverse=True)
                            
                            # Add MP3 format if FFmpeg is available
                            ffmpeg_available, _ = check_ffmpeg_installed()
                            if ffmpeg_available:
                                mp3_format = {
                                    'format_id': 'mp3',
                                    'ext': 'mp3',
                                    'quality': 'audio',
                                    'filesize': 0,
                                }
                                info.formats.append(mp3_format)
                            
                            # Ensure at least one format is available
                            if not info.formats:
                                info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                            
                            # Send a copy to avoid modification issues
                            info_copy = info.copy()
                            self.info_signal.emit(url, info_copy)
                            return info
                            
                        except Exception as e:
                            logger.error(f"Error processing result data: {str(e)}")
                            info.title = f"Error processing data: {str(e)}"
                            info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                            self.info_signal.emit(url, info.copy())
                            return info
                    else:
                        # Handle case when result is None
                        logger.error("Result is None")
                        info.title = f"Error: Could not retrieve info from {url}"
                        info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                        self.info_signal.emit(url, info.copy())
                        logger.error(f"Error extracting video info from {url}: No data returned")
                        return info
                        
                except Exception as e:
                    # Handle specific extraction error
                    logger.error(f"General extraction error: {str(e)}")
                    info.title = f"Error: {str(e)}"
                    info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                    self.info_signal.emit(url, info.copy())
                    logger.error(f"Error during info extraction for {url}: {str(e)}")
                    return info
                    
            return info
                
        except Exception as e:
            logger.error(f"YoutubeDL error: {e}")
            info.title = f"Error: {str(e)}"
            self.info_signal.emit(url, info.copy())
            return info
    
    def is_valid_url(self, url):
        """Check if URL is a valid TikTok URL"""
        # Regex patterns to check TikTok video URL
        patterns = [
            # Standard URL
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+',
            # URL with parameters
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+\?[\w=&]+',
            # Shortened URL
            r'https?://(vm\.|vt\.)?tiktok\.com/\w+',
            # Other possible patterns
            r'https?://(www\.)?tiktok\.com/t/\w+',
            # Video from webapp
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+\?is_from_webapp=1',
            # Photo URL (will be checked and error handled later)
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/photo/\d+',
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/photo/\d+\?[\w=&]+'
        ]
        
        # Check each pattern
        for pattern in patterns:
            if re.match(pattern, url):
                return True
                
        return False
    
    def download_video(self, url, format_id=None, output_template=None, audio_only=False, force_overwrite=False):
        """
        Download TikTok video
        
        Args:
            url: TikTok video URL
            format_id: Format ID to download (if None, best quality will be chosen)
            output_template: Output filename template
            audio_only: Whether to download audio only
            force_overwrite: Overwrite if file exists
        """
        # Check if URL is valid
        if not self.is_valid_url(url):
            self.api_error_signal.emit(url, "Invalid TikTok URL")
            return
        
        # Mark this URL as currently downloading
        self.downloading_urls.add(url)
        
        if not output_template:
            if not self.output_dir:
                self.output_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                
            output_template = os.path.join(self.output_dir, '%(title)s.%(ext)s')
        
        # Check if this is an audio request
        is_audio_request = audio_only or (format_id and ('audio' in format_id.lower() or 'mp3' in format_id.lower()))
        
        # Mark URL as being converted to MP3 if it's an audio request
        if is_audio_request:
            self.converting_mp3_urls.add(url)
        
        # For audio requests, we'll need to convert after download
        if is_audio_request:
            # Use mp4 for temporary download
            if '.%(ext)s' in output_template:
                temp_output_template = output_template.replace('.%(ext)s', '.mp4')
            else:
                temp_output_template = os.path.splitext(output_template)[0] + '.mp4'
            # Don't just request 'bestaudio' as not all videos have separate audio streams
            # Instead, download best quality video and extract audio later
            format_spec = 'best'
        else:
            temp_output_template = output_template
            # Set up format
            if format_id:
                format_spec = format_id
            else:
                format_spec = 'best'
            
            # Add no-watermark if requested
            if format_id != 'mp3':  # Don't add for MP3 format
                format_spec = 'no-watermark/' + format_spec
        
        ydl_opts = {
            'format': format_spec,
            'outtmpl': temp_output_template,
            'progress_hooks': [self._progress_hook],
            'quiet': False,
            'no_warnings': True,
        }
        
        # Add overwrite option if requested
        if force_overwrite:
            ydl_opts['force_overwrites'] = True  # Overwrite existing files
            ydl_opts['nooverwrites'] = False     # Ensure not skipping existing files
            ydl_opts['overwrites'] = True        # Try alternative option
            # Add command line options
            if 'postprocessor_args' not in ydl_opts:
                ydl_opts['postprocessor_args'] = {}
            if 'ffmpeg' not in ydl_opts['postprocessor_args']:
                ydl_opts['postprocessor_args']['ffmpeg'] = []
            # Add -y to force overwrite with ffmpeg
            ydl_opts['postprocessor_args']['ffmpeg'] += ['-y']
        
        try:
            logger.info(f"Downloading with format: {format_spec}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Get the actual downloaded file path
            downloaded_file = temp_output_template
            
            # If template still contains %(title)s, we need to get the title info
            if '%(title)s' in temp_output_template:
                # Get info to determine the actual filename
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'unknown_title').replace('/', '-')
                    downloaded_file = temp_output_template.replace('%(title)s', title)
            
            # If this was an audio request, convert to MP3
            if is_audio_request:
                # Get title from downloaded path if possible, otherwise from video info
                title = os.path.splitext(os.path.basename(downloaded_file))[0]
                
                # Special handling when filename starts with 'Video_' - case of video with no title
                if title.startswith("Video_") and re.match(r"Video_\d{8}_\d{6}", title):
                    logger.info(f"Detected automatically generated title: {title}")
                    # Use this name directly, don't slugify to avoid changing case
                    safe_title = title
                    # Ensure not changing case of filename
                    mp3_output = os.path.join(os.path.dirname(downloaded_file), f"{title}.mp3")
                elif not title:
                    # Fallback to get title if needed
                    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                        info = ydl.extract_info(url, download=False)
                        title = info.get('title', 'unknown_title').replace('/', '-')
                    # Create safe filename with slugify
                    safe_title = slugify(title)
                    if not safe_title:  # If slugify returns empty string
                        # Create timestamp-based filename
                        safe_title = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    mp3_output = os.path.splitext(downloaded_file)[0] + '.mp3'
                else:
                    # Create safe filename with slugify
                    safe_title = slugify(title)
                    if not safe_title:  # If slugify returns empty string
                        safe_title = "audio"  # Set default name
                    mp3_output = os.path.splitext(downloaded_file)[0] + '.mp3'
                
                # Create path to MP3 file using safe name
                safe_mp3_path = os.path.join(os.path.dirname(downloaded_file), f"{safe_title}.mp3")
                
                # However, keep the original path to return to user
                mp3_output = os.path.splitext(downloaded_file)[0] + '.mp3'
                
                # Use FFmpeg to convert
                try:
                    # Check FFmpeg
                    ffmpeg_available, ffmpeg_path = check_ffmpeg_installed()
                    if not ffmpeg_available:
                        logger.error("FFmpeg not found, cannot convert to MP3")
                        self.api_error_signal.emit(url, "FFmpeg not found, cannot convert to MP3")
                        # Clean up the downloaded file
                        if os.path.exists(downloaded_file):
                            try:
                                os.remove(downloaded_file)
                            except Exception as e:
                                logger.error(f"Failed to remove temporary file: {e}")
                        # Remove from tracking sets
                        self.downloading_urls.discard(url)
                        self.converting_mp3_urls.discard(url)
                        return
                    
                    logger.info(f"Converting {downloaded_file} to {mp3_output}")
                    
                    # On Windows, use creationflags to hide the console window
                    creationflags = 0x08000000 if os.name == 'nt' else 0
                    
                    process = subprocess.Popen(
                        [ffmpeg_path, '-i', downloaded_file, '-q:a', '0', '-map', 'a', mp3_output],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=creationflags
                    )
                    
                    # Wait for process to complete
                    stdout, stderr = process.communicate()
                    
                    if process.returncode != 0:
                        logger.error(f"FFmpeg error: {stderr.decode('utf-8', errors='replace')}")
                        self.api_error_signal.emit(url, f"FFmpeg error: {stderr.decode('utf-8', errors='replace')[:100]}...")
                        # Clean up the downloaded file
                        if os.path.exists(downloaded_file):
                            try:
                                os.remove(downloaded_file)
                            except Exception as e:
                                logger.error(f"Failed to remove temporary file: {e}")
                        # Remove from tracking sets
                        self.downloading_urls.discard(url)
                        self.converting_mp3_urls.discard(url)
                        return
                    
                    # Remove the original video file
                    if os.path.exists(downloaded_file):
                        try:
                            os.remove(downloaded_file)
                        except Exception as e:
                            logger.error(f"Failed to remove temporary file: {e}")
                    
                    # Signal completion
                    self.finished_signal.emit(url, True, mp3_output)
                    self._add_to_downloads(url, True, mp3_output)
                    
                except Exception as e:
                    logger.error(f"Error converting to MP3: {e}")
                    self.api_error_signal.emit(url, f"Error converting to MP3: {str(e)}")
                    # Remove from tracking sets
                    self.downloading_urls.discard(url)
                    self.converting_mp3_urls.discard(url)
                    return
                    
            else:
                # Signal completion for video
                self.finished_signal.emit(url, True, downloaded_file)
                self._add_to_downloads(url, True, downloaded_file)
            
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            self.api_error_signal.emit(url, f"Download error: {str(e)}")
            self.finished_signal.emit(url, False, "")
            # Remove from tracking sets
            self.downloading_urls.discard(url)
            if is_audio_request:
                self.converting_mp3_urls.discard(url)
    
    def _progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            url = d['info_dict'].get('webpage_url', d.get('filename', 'unknown_url'))
            
            # Calculate progress
            if 'total_bytes' in d and d['total_bytes'] > 0:
                progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                progress = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
            else:
                progress = 0
                
            # Get download speed
            speed = d.get('speed', 0)
            if speed:
                speed_str = f"{speed / 1024 / 1024:.2f} MB/s"
            else:
                speed_str = "Unknown"
                
            # Emit progress signal
            self.progress_signal.emit(url, progress, speed_str)
            
        elif d['status'] == 'finished':
            url = d['info_dict'].get('webpage_url', d.get('filename', 'unknown_url'))
            self.progress_signal.emit(url, 100, "Done")
            
            # If this URL is being converted to MP3, don't emit finished signal yet
            if url in self.converting_mp3_urls:
                self.progress_signal.emit(url, 100, "Converting to MP3...")
            
    def _add_to_downloads(self, url, success, file_path):
        """Add download to history"""
        self.downloads[url] = {
            'success': success,
            'file_path': file_path,
            'timestamp': time.time()
        }
        # Remove from tracking sets
        self.downloading_urls.discard(url)
        self.converting_mp3_urls.discard(url)
    
    @staticmethod
    def get_platform_name():
        """Get the name of the platform"""
        return "TikTok"
    
    @staticmethod
    def get_platform_icon():
        """Get the path to the platform icon"""
        return get_resource_path("assets/platforms/tiktok.png") 