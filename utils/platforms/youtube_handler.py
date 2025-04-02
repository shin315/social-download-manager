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

class YouTubeHandler(PlatformHandler):
    """Handler for YouTube videos"""
    
    def __init__(self):
        super().__init__()
        self.converting_mp3_urls = set()  # Track URLs currently being converted to MP3
    
    def get_video_info(self, url):
        """Get video information from YouTube URL"""
        if not self.is_valid_url(url):
            info = VideoInfo()
            info.url = url
            info.title = "Invalid YouTube URL"
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
                            # Handle playlists differently
                            is_playlist = result.get('_type') == 'playlist'
                            
                            if is_playlist:
                                # For playlists, we'll use the first entry for now
                                if 'entries' in result and len(result['entries']) > 0:
                                    # Store playlist info in platform_data
                                    info.platform_data['is_playlist'] = True
                                    info.platform_data['playlist_title'] = result.get('title', 'Unknown Playlist')
                                    info.platform_data['playlist_id'] = result.get('id', '')
                                    info.platform_data['playlist_count'] = len(result['entries'])
                                    
                                    # Get first entry for basic info
                                    first_entry = result['entries'][0]
                                    if first_entry:
                                        result = first_entry
                                    else:
                                        raise Exception("Could not extract video info from playlist")
                                else:
                                    raise Exception("Empty playlist")
                            else:
                                info.platform_data['is_playlist'] = False
                            
                            # Basic info
                            info.title = result.get('title', 'Unknown Title')
                            info.thumbnail = result.get('thumbnail', '')
                            info.duration = result.get('duration', 0)
                            
                            # Creator info
                            info.creator = result.get('uploader', 'Unknown')
                            info.creator_url = result.get('uploader_url', '')
                            
                            # Content info
                            info.description = result.get('description', '')
                            
                            # Try to extract YouTube tags as hashtags
                            if 'tags' in result and result['tags']:
                                info.hashtags = [f"#{tag}" for tag in result['tags']]
                            
                            # Stats
                            info.view_count = result.get('view_count', 0)
                            info.like_count = result.get('like_count', 0)
                            info.comment_count = result.get('comment_count', 0)
                            
                            # Platform specific
                            info.platform_id = result.get('id', '')
                            
                            # YouTube specific fields
                            info.platform_data['channel_id'] = result.get('channel_id', '')
                            info.platform_data['channel_url'] = result.get('channel_url', '')
                            info.platform_data['upload_date'] = result.get('upload_date', '')
                            info.platform_data['categories'] = result.get('categories', [])
                            info.platform_data['age_limit'] = result.get('age_limit', 0)
                            
                            # Get available formats
                            if 'formats' in result:
                                # Dictionary to track best version of each resolution
                                best_formats = {}
                                
                                for fmt in result['formats']:
                                    # Skip audio-only formats for now
                                    if fmt.get('vcodec', '') == 'none':
                                        continue
                                    
                                    # Skip formats without height (usually audio or unknown)
                                    height = fmt.get('height', 0)
                                    if not height:
                                        continue
                                        
                                    # Create a key for this resolution
                                    resolution_key = f"{height}p"
                                    
                                    # Format info with consistent keys
                                    format_info = {
                                        'format_id': fmt.get('format_id', ''),
                                        'ext': fmt.get('ext', 'mp4'),
                                        'filesize': fmt.get('filesize', 0),
                                        'height': height,
                                        'quality': resolution_key,
                                        'fps': fmt.get('fps', 0),
                                        'vcodec': fmt.get('vcodec', ''),
                                        'acodec': fmt.get('acodec', ''),
                                    }
                                    
                                    # Save only the best (highest filesize) for each resolution
                                    if resolution_key not in best_formats or format_info['filesize'] > best_formats[resolution_key]['filesize']:
                                        best_formats[resolution_key] = format_info
                                
                                # Add only the best format for each resolution to avoid duplicates
                                for _, format_info in sorted(best_formats.items(), key=lambda x: x[1].get('height', 0), reverse=True):
                                    info.formats.append(format_info)
                                
                                # Also add audio formats
                                audio_formats = []
                                for fmt in result['formats']:
                                    if fmt.get('vcodec', '') == 'none' and fmt.get('acodec', '') != 'none':
                                        audio_format = {
                                            'format_id': fmt.get('format_id', ''),
                                            'ext': fmt.get('ext', 'm4a'),
                                            'filesize': fmt.get('filesize', 0),
                                            'quality': 'audio',
                                            'audio_quality': fmt.get('audio_quality', 0),
                                            'acodec': fmt.get('acodec', ''),
                                        }
                                        audio_formats.append(audio_format)
                                
                                # Add best audio format
                                if audio_formats:
                                    # Sort by filesize as a proxy for quality
                                    audio_formats.sort(key=lambda x: x.get('filesize', 0), reverse=True)
                                    best_audio = audio_formats[0]
                                    best_audio['quality'] = 'audio'
                                    info.formats.append(best_audio)
                            
                            # Add MP3 format if FFmpeg is available
                            ffmpeg_available, _ = check_ffmpeg_installed()
                            if ffmpeg_available:
                                mp3_format = {
                                    'format_id': 'mp3',
                                    'ext': 'mp3',
                                    'quality': 'mp3',
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
                            logger.error(f"Error processing YouTube result data: {str(e)}")
                            info.title = f"Error processing data: {str(e)}"
                            info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                            self.info_signal.emit(url, info.copy())
                            return info
                    else:
                        # Handle case when result is None
                        logger.error("YouTube result is None")
                        info.title = f"Error: Could not retrieve info from {url}"
                        info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                        self.info_signal.emit(url, info.copy())
                        logger.error(f"Error extracting video info from {url}: No data returned")
                        return info
                        
                except Exception as e:
                    # Handle specific extraction error
                    logger.error(f"YouTube extraction error: {str(e)}")
                    info.title = f"Error: {str(e)}"
                    info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                    self.info_signal.emit(url, info.copy())
                    logger.error(f"Error during YouTube info extraction for {url}: {str(e)}")
                    return info
                    
            return info
                
        except Exception as e:
            logger.error(f"YouTube YoutubeDL error: {e}")
            info.title = f"Error: {str(e)}"
            self.info_signal.emit(url, info.copy())
            return info
    
    def is_valid_url(self, url):
        """Check if URL is a valid YouTube URL"""
        # Regex patterns to check YouTube URL
        patterns = [
            # Standard video URL
            r'https?://(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})',
            # Short URL
            r'https?://(www\.)?youtu\.be/([^&=%\?]{11})',
            # Shorts
            r'https?://(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/shorts/([^&=%\?]{11})',
            # Playlist
            r'https?://(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(playlist\?list=)([^&=%\?]+)',
            # Channel
            r'https?://(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(channel|c|user)/([^&=%\?]+)',
        ]
        
        # Check each pattern
        for pattern in patterns:
            if re.match(pattern, url):
                return True
                
        return False
    
    def download_video(self, url, format_id=None, output_template=None, audio_only=False, force_overwrite=False):
        """
        Download YouTube video
        
        Args:
            url: YouTube video URL
            format_id: Format ID to download (if None, best quality will be chosen)
            output_template: Output filename template
            audio_only: Whether to download audio only
            force_overwrite: Overwrite if file exists
        """
        # Check if URL is valid
        if not self.is_valid_url(url):
            self.api_error_signal.emit(url, "Invalid YouTube URL")
            return
        
        # Mark this URL as currently downloading
        self.downloading_urls.add(url)
        
        if not output_template:
            if not self.output_dir:
                self.output_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                
            output_template = os.path.join(self.output_dir, '%(title)s.%(ext)s')
        
        # Check if this is an audio request
        is_audio_request = audio_only or (format_id and ('audio' in format_id.lower() or 'mp3' in format_id.lower()))
        
        # Mark URL as being converted to MP3 if it's an audio request with MP3 format
        if is_audio_request and (not format_id or 'mp3' in format_id.lower()):
            self.converting_mp3_urls.add(url)
            # For MP3, we'll download best audio and convert
            format_spec = 'bestaudio'
            if '.%(ext)s' in output_template:
                temp_output_template = output_template.replace('.%(ext)s', '.%(ext)s')
            else:
                temp_output_template = output_template
        elif is_audio_request:
            # For other audio formats, download directly in that format
            format_spec = format_id if format_id else 'bestaudio'
            temp_output_template = output_template
        else:
            # For video, use the specified format or best
            temp_output_template = output_template
            if format_id:
                format_spec = format_id
            else:
                format_spec = 'bestvideo+bestaudio/best'
        
        ydl_opts = {
            'format': format_spec,
            'outtmpl': temp_output_template,
            'progress_hooks': [self._progress_hook],
            'quiet': False,
            'no_warnings': True,
        }
        
        # Add postprocessor for MP3 conversion if needed
        if is_audio_request and 'mp3' in (format_id or '').lower():
            # Check if FFmpeg is installed
            ffmpeg_available, _ = check_ffmpeg_installed()
            if not ffmpeg_available:
                logger.error("FFmpeg not found, cannot convert to MP3")
                self.api_error_signal.emit(url, "FFmpeg not found, cannot convert to MP3")
                self.downloading_urls.discard(url)
                self.converting_mp3_urls.discard(url)
                return
            
            # Add postprocessor args to hide console window on Windows
            postprocessor_args = {}
            if os.name == 'nt':
                postprocessor_args['ffmpeg'] = ['-hide_banner', '-loglevel', 'panic']
            
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            
            if postprocessor_args:
                ydl_opts['postprocessor_args'] = postprocessor_args
        
        # Add overwrite option if requested
        if force_overwrite:
            ydl_opts['force_overwrites'] = True
            ydl_opts['nooverwrites'] = False
            ydl_opts['overwrites'] = True
            
            # Add postprocessor args if not already added
            if 'postprocessor_args' not in ydl_opts:
                ydl_opts['postprocessor_args'] = {}
            if 'ffmpeg' not in ydl_opts['postprocessor_args']:
                ydl_opts['postprocessor_args']['ffmpeg'] = []
            
            # Add -y to force overwrite with ffmpeg
            ydl_opts['postprocessor_args']['ffmpeg'] += ['-y']
        
        try:
            logger.info(f"Downloading YouTube with format: {format_spec}")
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
                    
                    # Handle extension for MP3
                    if is_audio_request and 'mp3' in (format_id or '').lower():
                        ext = 'mp3'
                    else:
                        ext = info.get('ext', 'mp4')
                        
                    downloaded_file = temp_output_template.replace('%(title)s.%(ext)s', f"{title}.{ext}")
            
            # Signal completion
            self.finished_signal.emit(url, True, downloaded_file)
            self._add_to_downloads(url, True, downloaded_file)
            
        except Exception as e:
            logger.error(f"Error downloading YouTube video: {e}")
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
            
            # If this URL is being converted to MP3, update status
            if url in self.converting_mp3_urls:
                self.progress_signal.emit(url, 100, "Processing audio...")
            else:
                self.progress_signal.emit(url, 100, "Done")
            
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
        return "YouTube"
    
    @staticmethod
    def get_platform_icon():
        """Get the path to the platform icon"""
        return get_resource_path("assets/platforms/youtube.png") 