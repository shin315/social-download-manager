import yt_dlp
import os
import time
import subprocess
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal
import re
import unicodedata
import string


class VideoInfo:
    """Lớp lưu trữ thông tin video"""
    
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
    """Lớp xử lý tải video TikTok sử dụng yt-dlp"""
    
    # Signals
    progress_signal = pyqtSignal(str, float, str)  # url, progress percentage, speed
    finished_signal = pyqtSignal(str, bool, str)   # url, success, file_path
    info_signal = pyqtSignal(str, object)  # url, video_info (as object)
    
    def __init__(self):
        super().__init__()
        self.output_dir = ""
        self.downloads = {}  # Lưu trữ thông tin các video đã tải
        self.converting_mp3_urls = set()  # Theo dõi các URL đang trong quá trình convert MP3
        self.downloading_urls = set()  # Theo dõi tất cả các URL đang trong quá trình tải xuống
    
    def slugify(self, text):
        """
        Chuyển đổi văn bản thành slug an toàn cho tên file.
        Loại bỏ ký tự đặc biệt, thay thế khoảng trắng bằng gạch ngang.
        """
        # Chuẩn hóa văn bản Unicode (ví dụ: 'é' -> 'e')
        text = unicodedata.normalize('NFKD', text)
        text = ''.join([c for c in text if not unicodedata.combining(c)])
        
        # Thay thế khoảng trắng bằng gạch ngang và chuyển thành chữ thường
        text = text.lower().replace(' ', '-')
        
        # Loại bỏ các ký tự không phải chữ cái, số, gạch ngang
        text = re.sub(r'[^\w\s-]', '', text)
        
        # Loại bỏ các gạch ngang liên tiếp
        text = re.sub(r'[-\s]+', '-', text)
        
        # Đảm bảo không có gạch ngang ở đầu hoặc cuối
        return text.strip('-')

    def set_output_dir(self, directory):
        """Thiết lập thư mục đầu ra"""
        self.output_dir = directory
    
    def get_video_info(self, url):
        """Lấy thông tin video từ URL"""
        try:
            info = VideoInfo()
            info.url = url
            
            # Kiểm tra URL có phải là URL TikTok hợp lệ không
            if not self._is_valid_tiktok_url(url):
                info.title = f"Error: Invalid TikTok video URL: {url}"
                info.formats = [{'format_id': 'best', 'quality': '720p', 'ext': 'mp4', 'height': 720, 'filesize': 0}]
                print(f"Emitting info signal for invalid URL: {info}")
                self.info_signal.emit(url, info.copy())  # Send a copy
                print(f"Invalid TikTok video URL: {url}")
                return info
            
            # Kiểm tra sớm nếu URL chứa 'photo' hoặc 'album'
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
                                
                                # Kiểm tra xem nội dung có phải video hay không
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
        """Kiểm tra URL có phải là URL TikTok hợp lệ không"""
        # In URL để debug
        print(f"Checking TikTok URL: {url}")
        
        # Mẫu regex để kiểm tra URL TikTok video
        patterns = [
            # URL standard
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+',
            # URL với tham số
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+\?[\w=&]+',
            # URL rút gọn
            r'https?://(vm\.|vt\.)?tiktok\.com/\w+',
            # Mẫu khác có thể có
            r'https?://(www\.)?tiktok\.com/t/\w+',
            # Video từ webapp
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/video/\d+\?is_from_webapp=1',
            # Photo URL (sẽ được kiểm tra và xử lý lỗi sau)
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/photo/\d+',
            r'https?://(www\.)?tiktok\.com/@[\w\.-]+/photo/\d+\?[\w=&]+'
        ]
        
        # Kiểm tra từng mẫu
        for pattern in patterns:
            if re.match(pattern, url):
                print(f"Valid TikTok URL format: {pattern}")
                return True
                
        print(f"Invalid TikTok URL: {url}")
        return False
    
    def download_video(self, url, format_id=None, remove_watermark=True, output_template=None, audio_only=False, force_overwrite=False):
        """
        Tải video TikTok
        
        Args:
            url: URL của video TikTok
            format_id: ID định dạng muốn tải (nếu None, sẽ tự động chọn tốt nhất)
            remove_watermark: Có xóa watermark hay không
            output_template: Template tên file đầu ra
            audio_only: Có tải xuống chỉ âm thanh hay không
            force_overwrite: Ghi đè nếu file đã tồn tại
        """
        # Đánh dấu URL này đang trong quá trình tải xuống
        self.downloading_urls.add(url)
        
        if not output_template:
            if not self.output_dir:
                self.output_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                
            output_template = os.path.join(self.output_dir, '%(title)s.%(ext)s')
        
        # Kiểm tra đây có phải là yêu cầu audio không
        is_audio_request = audio_only or (format_id and ('audio' in format_id.lower() or 'mp3' in format_id.lower()))
        
        # Đánh dấu URL này đang trong quá trình tải MP3 nếu là audio request
        if is_audio_request:
            self.converting_mp3_urls.add(url)
        
        # For audio requests, we'll need to convert after download
        if is_audio_request:
            # Use mp4 for temporary download
            if '.%(ext)s' in output_template:
                temp_output_template = output_template.replace('.%(ext)s', '.mp4')
            else:
                temp_output_template = os.path.splitext(output_template)[0] + '.mp4'
            # Không chỉ yêu cầu 'bestaudio' vì không phải video nào cũng có stream audio riêng
            # Thay vào đó, tải video chất lượng tốt nhất và sau đó extract audio ra
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
        
        # Thêm tùy chọn ghi đè nếu được yêu cầu
        if force_overwrite:
            ydl_opts['force_overwrites'] = True  # Ghi đè các file hiện có
            ydl_opts['nooverwrites'] = False     # Đảm bảo không bỏ qua các file hiện có
            ydl_opts['overwrites'] = True        # Thử dùng tùy chọn khác
            # Thêm các tùy chọn dòng lệnh
            if not 'postprocessor_args' in ydl_opts:
                ydl_opts['postprocessor_args'] = {}
            if not 'ffmpeg' in ydl_opts['postprocessor_args']:
                ydl_opts['postprocessor_args']['ffmpeg'] = []
            # Thêm -y để force overwrite với ffmpeg
            ydl_opts['postprocessor_args']['ffmpeg'] += ['-y']
        
        try:
            print(f"Downloading with format: {format_spec}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Get the actual downloaded file path
            downloaded_file = temp_output_template
            
            # Nếu template vẫn còn chứa %(title)s, thì cần lấy thông tin tiêu đề
            if '%(title)s' in temp_output_template:
                # Get info to determine the actual filename
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'unknown_title').replace('/', '-')
                    downloaded_file = temp_output_template.replace('%(title)s', title)
            
            # If this was an audio request, convert to MP3
            if is_audio_request:
                # Lấy tiêu đề từ đường dẫn đã tải nếu có, nếu không lấy từ thông tin video
                title = os.path.splitext(os.path.basename(downloaded_file))[0]
                
                # Xử lý đặc biệt khi tên file bắt đầu bằng 'Video_' - trường hợp video không có tiêu đề
                if title.startswith("Video_") and re.match(r"Video_\d{8}_\d{6}", title):
                    print(f"Detected automatically generated title: {title}")
                    # Sử dụng trực tiếp tên này, không cần slugify để tránh thay đổi chữ hoa/thường
                    safe_title = title
                    # Đảm bảo không thay đổi case của tên file
                    mp3_output = os.path.join(os.path.dirname(downloaded_file), f"{title}.mp3")
                elif not title:
                    # Fallback để lấy tiêu đề nếu cần thiết
                    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                        info = ydl.extract_info(url, download=False)
                        title = info.get('title', 'unknown_title').replace('/', '-')
                    # Tạo tên file an toàn với slugify
                    safe_title = self.slugify(title)
                    if not safe_title:  # Nếu slugify trả về chuỗi rỗng
                        # Tạo tên file dựa trên timestamp
                        safe_title = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    mp3_output = os.path.splitext(downloaded_file)[0] + '.mp3'
                else:
                    # Tạo tên file an toàn với slugify
                    safe_title = self.slugify(title)
                    if not safe_title:  # Nếu slugify trả về chuỗi rỗng
                        safe_title = "audio"  # Đặt tên mặc định
                    mp3_output = os.path.splitext(downloaded_file)[0] + '.mp3'
                
                # Tạo đường dẫn đến file MP3 sử dụng tên an toàn
                safe_mp3_path = os.path.join(os.path.dirname(downloaded_file), f"{safe_title}.mp3")
                
                # Tuy nhiên vẫn giữ đường dẫn ban đầu để trả về cho người dùng
                mp3_output = os.path.splitext(downloaded_file)[0] + '.mp3'
                
                # Use FFmpeg to convert
                try:
                    # Đơn giản hóa quy trình - chuyển đổi trực tiếp sang file đích cuối cùng
                    # thay vì dùng file tạm thời rồi đổi tên (để tránh lỗi đổi tên)
                    command = [
                        'ffmpeg', '-i', downloaded_file, 
                        '-vn',  # No video
                        '-acodec', 'libmp3lame', 
                        '-q:a', '2',  # VBR quality 2 (good quality)
                        mp3_output,  # Lưu trực tiếp sang file đích
                        '-y'  # Overwrite if exists
                    ]
                    
                    print(f"Converting to MP3: {' '.join(command)}")
                    # Sử dụng encoding='utf-8', errors='ignore' để tránh lỗi Unicode
                    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='ignore')
                    
                    if result.returncode != 0:
                        print(f"FFmpeg error: {result.stderr}")
                        self.converting_mp3_urls.discard(url)  # Xóa URL khỏi danh sách convert
                        self.downloading_urls.discard(url)  # Xóa URL khỏi danh sách tải xuống
                        self.finished_signal.emit(url, False, f"Error converting to MP3: {result.stderr}")
                        return False
                    
                    # Kiểm tra file MP3 đã được tạo thành công chưa
                    if os.path.exists(mp3_output) and os.path.getsize(mp3_output) > 0:
                        # Xóa file MP4 tạm
                        os.remove(downloaded_file)
                        downloaded_file = mp3_output
                        print(f"Successfully converted to MP3: {mp3_output}")
                    else:
                        print("MP3 conversion failed or output file is empty")
                        self.converting_mp3_urls.discard(url)  # Xóa URL khỏi danh sách convert
                        self.downloading_urls.discard(url)  # Xóa URL khỏi danh sách tải xuống
                        self.finished_signal.emit(url, False, "MP3 conversion failed or output file is empty")
                        return False
                        
                except Exception as e:
                    print(f"Error during MP3 conversion: {e}")
                    self.converting_mp3_urls.discard(url)  # Xóa URL khỏi danh sách convert
                    self.downloading_urls.discard(url)  # Xóa URL khỏi danh sách tải xuống
                    self.finished_signal.emit(url, False, f"Error during MP3 conversion: {e}")
                    return False
            
            # Xóa URL khỏi danh sách đang convert MP3 (nếu có)
            self.converting_mp3_urls.discard(url)
            
            # Add to downloads history
            self._add_to_downloads(url, True, downloaded_file)
            
            # Phát signal hoàn thành và xóa URL khỏi danh sách tải
            # Đảm bảo file_path không còn chứa %(ext)s
            if '%(ext)s' in downloaded_file:
                # Kiểm tra đuôi file thực tế
                if downloaded_file.lower().endswith('.mp3'):
                    downloaded_file = downloaded_file.replace('.%(ext)s', '.mp3')
                else:
                    downloaded_file = downloaded_file.replace('.%(ext)s', '.mp4')
                
            self.finished_signal.emit(url, True, downloaded_file)
            self.downloading_urls.discard(url)
            return True
            
        except Exception as e:
            print(f"Error downloading video: {e}")
            self.converting_mp3_urls.discard(url)  # Xóa URL khỏi danh sách convert
            self.downloading_urls.discard(url)  # Xóa URL khỏi danh sách tải xuống
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
            
            # Kiểm tra nếu URL đang trong quá trình convert MP3
            if url in self.converting_mp3_urls:
                # Chỉ thông báo đang chuyển đổi, không phát signal finished
                self.progress_signal.emit(url, 100, "Converting to MP3...")
            elif url in self.downloading_urls:
                # Đây là một phần của quá trình tải xuống, chỉ thông báo tiến trình
                # và không phát signal finished trong hook này
                # (sẽ được phát trong hàm download_video sau khi hoàn tất)
                self.progress_signal.emit(url, 100, "Download completed, processing...")
            else:
                # Nếu URL không trong quá trình tải hoặc convert, phát signal finished ngay
                # (trường hợp này hiếm khi xảy ra, chỉ là phòng trừ)
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