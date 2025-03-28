import yt_dlp
import os
import time
import subprocess
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal
import re
import unicodedata
import string
import shutil


class VideoInfo:
    """Class for storing video information"""
    
    def __init__(self):
        self.title = "Unknown Title"
        self.url = ""
        self.thumbnail = ""
        self.duration = 0
        self.formats = []
        self.caption = ""
        self.hashtags = []
        self.creator = "Unknown"
        self.like_count = 0
        
    def __str__(self):
        """String representation for debugging"""
        return f"VideoInfo(title='{self.title}', url='{self.url}', duration={self.duration}, formats_count={len(self.formats)})"
        
    def copy(self):
        """Create a copy of this VideoInfo"""
        new_info = VideoInfo()
        new_info.title = self.title
        new_info.url = self.url
        new_info.thumbnail = self.thumbnail
        new_info.duration = self.duration
        new_info.formats = self.formats.copy() if self.formats else []
        new_info.caption = self.caption
        new_info.hashtags = self.hashtags.copy() if self.hashtags else []
        new_info.creator = self.creator
        new_info.like_count = self.like_count
        return new_info


class TikTokDownloader(QObject):
    """Class for handling TikTok video downloads using yt-dlp"""
    
    # Signals
    progress_signal = pyqtSignal(str, float, str)  # url, progress percentage, speed
    finished_signal = pyqtSignal(str, bool, str)   # url, success, file_path
    info_signal = pyqtSignal(str, object)  # url, video_info (as object)
    
    def __init__(self):
        super().__init__()
        self.output_dir = ""
        self.downloads = {}  # Store information about downloaded videos
        self.converting_mp3_urls = set()  # Track URLs currently being converted to MP3
        self.downloading_urls = set()  # Track all URLs currently being downloaded
    
    # Static method for checking if FFmpeg is installed
    @staticmethod
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
            if not ffmpeg_path:
                return False, "FFmpeg not found in system PATH"
            
            # Verify it works by running a simple command
            subprocess.run(
                ['ffmpeg', '-version'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                check=True
            )
            return True, ""
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            return False, f"Error checking FFmpeg: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error checking FFmpeg: {str(e)}"
    
    def slugify(self, text):
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

    def set_output_dir(self, directory):
        """Set the output directory"""
        self.output_dir = directory
    
    def get_video_info(self, url):
        """Get video information from URL"""
        try:
            info = VideoInfo()
            info.url = url
            
            # Check if URL is a valid TikTok URL
            if not self._is_valid_tiktok_url(url):
                info.title = f"Error: Invalid TikTok video URL: {url}"
                info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                print(f"Emitting info signal for invalid URL: {info}")
                self.info_signal.emit(url, info.copy())  # Send a copy
                print(f"Invalid TikTok video URL: {url}")
                return info
            
            # Early check if URL contains 'photo' or 'album'
            if re.search(r'/photo/', url) or re.search(r'/album/', url):
                info.title = "Error: DIALOG_UNSUPPORTED_CONTENT"
                info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                self.info_signal.emit(url, info.copy())
                return info
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        print(f"Extracting info from URL: {url}")
                        try:
                            result = ydl.extract_info(url, download=False)
                        except Exception as e:
                            print(f"YT-DLP error: {str(e)}")
                            info.title = f"Error: {str(e)}"
                            info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                            self.info_signal.emit(url, info.copy())  # Send a copy
                            return info
                        
                        if result:
                            try:
                                print(f"Result type: {type(result)}")
                                if hasattr(result, 'keys'):
                                    print(f"Result has {len(result.keys())} keys")
                                
                                # Check if content is a video
                                is_photo = result.get('webpage_url_basename', '').startswith('photo/')
                                is_album = 'album' in result.get('webpage_url', '').lower()
                                is_image = result.get('is_image', False)
                                
                                if is_photo or is_album or is_image:
                                    info.title = "Error: DIALOG_UNSUPPORTED_CONTENT"
                                    info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                                    self.info_signal.emit(url, info.copy())
                                    return info
                                
                                info.title = result.get('title', 'Unknown Title')
                                print(f"Title: {info.title}")
                                info.thumbnail = result.get('thumbnail', '')
                                info.duration = result.get('duration', 0)
                                print(f"Duration: {info.duration}")
                                info.caption = result.get('description', '')
                                
                                # Handle tags/hashtags
                                if result.get('tags'):
                                    info.hashtags = list(result.get('tags'))  # Force a copy
                                else:
                                    info.hashtags = []
                                    
                                info.creator = result.get('uploader', 'Unknown')
                                info.like_count = result.get('like_count', 0)
                                
                                # Extract formats and make a clean copy
                                formats = []
                                if result.get('formats'):
                                    for fmt in result.get('formats'):
                                        if fmt.get('height') and fmt.get('ext') == 'mp4':
                                            format_info = {
                                                'format_id': fmt.get('format_id', ''),
                                                'ext': fmt.get('ext', ''),
                                                'height': fmt.get('height', 0),
                                                'filesize': fmt.get('filesize', 0),
                                            }
                                            
                                            # Add quality label
                                            if format_info['height'] >= 1080:
                                                format_info['quality'] = '1080p'
                                            elif format_info['height'] >= 720:
                                                format_info['quality'] = '720p'
                                            elif format_info['height'] >= 480:
                                                format_info['quality'] = '480p'
                                            elif format_info['height'] >= 360:
                                                format_info['quality'] = '360p'
                                            else:
                                                format_info['quality'] = f"{format_info['height']}p"
                                                
                                            formats.append(format_info)
                                
                                # Add audio format
                                try:
                                    audio_formats = [fmt for fmt in result.get('formats', []) 
                                                    if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none']
                                    if audio_formats:
                                        best_audio = max(audio_formats, key=lambda x: x.get('filesize', 0) or 0)
                                        formats.append({
                                            'format_id': best_audio.get('format_id', ''),
                                            'ext': best_audio.get('ext', 'mp3'),
                                            'quality': 'Audio',
                                            'filesize': best_audio.get('filesize', 0),
                                            'is_audio': True
                                        })
                                except Exception as e:
                                    print(f"Error extracting audio format: {e}")
                                
                                # If no formats found, add default
                                if not formats:
                                    print("No formats found, adding default format")
                                    formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                                else:
                                    print(f"Found {len(formats)} formats")
                                
                                info.formats = formats
                                
                                # Emit signal with video info copy
                                print(f"Emitting info signal for {url}")
                                info_copy = info.copy()
                                print(f"Sending info copy: {info_copy}")
                                self.info_signal.emit(url, info_copy)
                                return info
                            except Exception as e:
                                print(f"Error processing result data: {str(e)}")
                                info.title = f"Error processing data: {str(e)}"
                                info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                                self.info_signal.emit(url, info.copy())  # Send a copy
                                return info
                        else:
                            # Handle case when result is None
                            print("Result is None")
                            info.title = f"Error: Could not retrieve info from {url}"
                            info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                            self.info_signal.emit(url, info.copy())  # Send a copy
                            print(f"Error extracting video info from {url}: No data returned")
                            return info
                    except Exception as e:
                        # Handle specific extraction error
                        print(f"General extraction error: {str(e)}")
                        info.title = f"Error: {str(e)}"
                        info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                        self.info_signal.emit(url, info.copy())  # Send a copy
                        print(f"Error during info extraction for {url}: {str(e)}")
                        return info
                        
                return info
                
            except Exception as e:
                print(f"YoutubeDL error: {e}")
                info.title = f"Error: {str(e)}"
                self.info_signal.emit(url, info.copy())  # Send a copy
                return info
        except Exception as e:
            print(f"Critical error in get_video_info: {e}")
            info = VideoInfo()
            info.url = url
            info.title = f"Critical error: {str(e)}"
            info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
            try:
                self.info_signal.emit(url, info.copy())  # Send a copy
            except Exception as signal_err:
                print(f"Could not emit signal: {signal_err}")
            return info
    
    def _is_valid_tiktok_url(self, url):
        """Check if URL is a valid TikTok URL"""
        # Print URL for debugging
        print(f"Checking TikTok URL: {url}")
        
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
                print(f"Valid TikTok URL format: {pattern}")
                return True
                
        print(f"Invalid TikTok URL: {url}")
        return False
    
    def download_video(self, url, format_id=None, remove_watermark=True, output_template=None, audio_only=False, force_overwrite=False):
        """
        Download TikTok video
        
        Args:
            url: TikTok video URL
            format_id: Format ID to download (if None, best quality will be chosen)
            remove_watermark: Whether to remove watermark
            output_template: Output filename template
            audio_only: Whether to download audio only
            force_overwrite: Overwrite if file exists
        """
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
            if remove_watermark:
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
            if not 'postprocessor_args' in ydl_opts:
                ydl_opts['postprocessor_args'] = {}
            if not 'ffmpeg' in ydl_opts['postprocessor_args']:
                ydl_opts['postprocessor_args']['ffmpeg'] = []
            # Add -y to force overwrite with ffmpeg
            ydl_opts['postprocessor_args']['ffmpeg'] += ['-y']
        
        try:
            print(f"Downloading with format: {format_spec}")
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
                    print(f"Detected automatically generated title: {title}")
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
                    safe_title = self.slugify(title)
                    if not safe_title:  # If slugify returns empty string
                        # Create timestamp-based filename
                        safe_title = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    mp3_output = os.path.splitext(downloaded_file)[0] + '.mp3'
                else:
                    # Create safe filename with slugify
                    safe_title = self.slugify(title)
                    if not safe_title:  # If slugify returns empty string
                        safe_title = "audio"  # Set default name
                    mp3_output = os.path.splitext(downloaded_file)[0] + '.mp3'
                
                # Create path to MP3 file using safe name
                safe_mp3_path = os.path.join(os.path.dirname(downloaded_file), f"{safe_title}.mp3")
                
                # However, keep the original path to return to user
                mp3_output = os.path.splitext(downloaded_file)[0] + '.mp3'
                
                # Use FFmpeg to convert
                try:
                    # Check if FFmpeg is installed first
                    ffmpeg_installed, ffmpeg_error = self.check_ffmpeg_installed()
                    if not ffmpeg_installed:
                        error_message = f"Cannot convert to MP3: {ffmpeg_error}\n\n"
                        error_message += "Please install FFmpeg to use the MP3 download feature:\n"
                        error_message += "- Windows: Download from ffmpeg.org and add to PATH\n"
                        error_message += "- macOS: Use 'brew install ffmpeg'\n"
                        error_message += "- Linux: Use your package manager (apt, dnf, etc.)\n"
                        error_message += "\nSee README.md for detailed installation instructions."
                        
                        print(error_message)
                        self.converting_mp3_urls.discard(url)  # Remove URL from conversion list
                        self.downloading_urls.discard(url)  # Remove URL from download list
                        self.finished_signal.emit(url, False, error_message)
                        return False
                    
                    # Simplify process - convert directly to final destination file
                    # instead of using temporary file and renaming (to avoid rename errors)
                    command = [
                        'ffmpeg', '-i', downloaded_file, 
                        '-vn',  # No video
                        '-acodec', 'libmp3lame', 
                        '-q:a', '2',  # VBR quality 2 (good quality)
                        mp3_output,  # Save directly to destination file
                        '-y'  # Overwrite if exists
                    ]
                    
                    print(f"Converting to MP3: {' '.join(command)}")
                    # Use encoding='utf-8', errors='ignore' to avoid Unicode errors
                    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='ignore')
                    
                    if result.returncode != 0:
                        print(f"FFmpeg error: {result.stderr}")
                        self.converting_mp3_urls.discard(url)  # Remove URL from conversion list
                        self.downloading_urls.discard(url)  # Remove URL from download list
                        
                        # More user-friendly error message
                        error_message = f"Error converting to MP3. FFmpeg reported: {result.stderr}\n\n"
                        error_message += "This might be due to an incompatible video format or a problem with FFmpeg."
                        
                        self.finished_signal.emit(url, False, error_message)
                        return False
                    
                    # Check if MP3 file was created successfully
                    if os.path.exists(mp3_output) and os.path.getsize(mp3_output) > 0:
                        # Remove temporary MP4 file
                        os.remove(downloaded_file)
                        downloaded_file = mp3_output
                        print(f"Successfully converted to MP3: {mp3_output}")
                    else:
                        print("MP3 conversion failed or output file is empty")
                        self.converting_mp3_urls.discard(url)  # Remove URL from conversion list
                        self.downloading_urls.discard(url)  # Remove URL from download list
                        self.finished_signal.emit(url, False, "MP3 conversion failed or output file is empty")
                        return False
                        
                except Exception as e:
                    print(f"Error during MP3 conversion: {e}")
                    self.converting_mp3_urls.discard(url)  # Remove URL from conversion list
                    self.downloading_urls.discard(url)  # Remove URL from download list
                    
                    # Check if this is a FileNotFoundError, which likely means FFmpeg is not installed
                    if isinstance(e, FileNotFoundError) and 'ffmpeg' in str(e):
                        error_message = "FFmpeg is not installed or not found in the system PATH.\n\n"
                        error_message += "Please install FFmpeg to use the MP3 download feature:\n"
                        error_message += "- Windows: Download from ffmpeg.org and add to PATH\n"
                        error_message += "- macOS: Use 'brew install ffmpeg'\n"
                        error_message += "- Linux: Use your package manager (apt, dnf, etc.)\n"
                        error_message += "\nSee README.md for detailed installation instructions."
                    else:
                        error_message = f"Error during MP3 conversion: {e}"
                    
                    self.finished_signal.emit(url, False, error_message)
                    return False
            
            # Remove URL from MP3 conversion list (if present)
            self.converting_mp3_urls.discard(url)
            
            # Add to downloads history
            self._add_to_downloads(url, True, downloaded_file)
            
            # Emit completion signal and remove URL from download list
            # Ensure file_path doesn't contain %(ext)s
            if '%(ext)s' in downloaded_file:
                # Check actual file extension
                if downloaded_file.lower().endswith('.mp3'):
                    downloaded_file = downloaded_file.replace('.%(ext)s', '.mp3')
                else:
                    downloaded_file = downloaded_file.replace('.%(ext)s', '.mp4')
                
            self.finished_signal.emit(url, True, downloaded_file)
            self.downloading_urls.discard(url)
            return True
            
        except Exception as e:
            print(f"Error downloading video: {e}")
            self.converting_mp3_urls.discard(url)  # Remove URL from conversion list
            self.downloading_urls.discard(url)  # Remove URL from download list
            self.finished_signal.emit(url, False, str(e))
            return False
    
    def _progress_hook(self, d):
        """Callback for download progress"""
        if d['status'] == 'downloading':
            url = d.get('info_dict', {}).get('webpage_url', 'Unknown')
            total = d.get('total_bytes', 0)
            downloaded = d.get('downloaded_bytes', 0)
            
            if total > 0:
                progress = (downloaded / total) * 100
            else:
                progress = 0
                
            speed = d.get('speed', 0)
            if speed:
                speed_str = f"{speed / 1024 / 1024:.2f} MB/s"
            else:
                speed_str = "Unknown"
                
            self.progress_signal.emit(url, progress, speed_str)
            
        elif d['status'] == 'finished':
            url = d.get('info_dict', {}).get('webpage_url', 'Unknown')
            filename = d.get('filename', '')
            
            # Check if URL is in the process of MP3 conversion
            if url in self.converting_mp3_urls:
                # Only notify of conversion, don't emit finished signal
                self.progress_signal.emit(url, 100, "Converting to MP3...")
            elif url in self.downloading_urls:
                # This is part of the download process, only notify progress
                # and don't emit finished signal in this hook
                # (will be emitted in the download_video function after completion)
                self.progress_signal.emit(url, 100, "Download completed, processing...")
            else:
                # If URL is not in download or conversion process, emit finished signal immediately
                # (rare case, just a safeguard)
                self.finished_signal.emit(url, True, filename)
    
    def _add_to_downloads(self, url, success, file_path):
        """Add download to history"""
        now = datetime.now().strftime("%Y/%m/%d %H:%M")
        
        # Get file info
        try:
            size = os.path.getsize(file_path)
            size_mb = size / (1024 * 1024)
            size_str = f"{size_mb:.2f} MB"
        except:
            size_str = "Unknown"
            
        # Add to downloads dictionary
        self.downloads[url] = {
            'url': url,
            'file_path': file_path,
            'success': success,
            'date': now,
            'size': size_str
        } 