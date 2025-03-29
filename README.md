# Social Download Manager

A powerful tool for downloading videos from various social media platforms without watermarks.

## Features

- Download TikTok videos without watermark
- Multi-language support (English & Vietnamese)
- Batch download support
- Download history management
- Video quality selection
- Copy video information (title, creator, hashtags)
- Download audio only (MP3 format)

## Requirements

- Python 3.8+
- PyQt6
- requests
- beautifulsoup4
- FFmpeg (required for MP3 downloads)

### Installing FFmpeg

FFmpeg is required for converting videos to MP3 format. If you don't need the MP3 download feature, you can skip this step.

#### Windows
1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html) or [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (recommended: ffmpeg-git-full.7z)
2. Extract the archive and add the `bin` folder to your system PATH
3. Verify installation by opening Command Prompt and typing `ffmpeg -version`

#### macOS
Using Homebrew:
```bash
brew install ffmpeg
```

#### Linux
Ubuntu/Debian:
```bash
sudo apt update
sudo apt install ffmpeg
```

Fedora:
```bash
sudo dnf install ffmpeg
```

Arch Linux:
```bash
sudo pacman -S ffmpeg
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/shin315/social-download-manager.git
cd social-download-manager
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up configuration:
```bash
cp config.template.json config.json
```

4. Run the application:
```bash
python main.py
```

## Configuration

The application uses a `config.json` file to store user preferences. If this file doesn't exist, copy the template file:

```bash
cp config.template.json config.json
```

Configuration options:
- `last_output_folder`: The last folder used for saving videos
- `language`: Application language ("english" or "vietnamese")

## Usage

1. Copy TikTok video URL(s)
2. Paste URL(s) into the application
3. Select desired video quality
4. Click "Download" to start downloading
5. View download history in the "Downloaded Videos" tab

### Downloading as MP3
To download audio only in MP3 format:
1. Paste the video URL
2. Select "Audio" quality in the dropdown menu
3. Click "Download"
4. The application will download the video and automatically convert it to MP3 format using FFmpeg

## Development Notes

### Temporary Files
The application generates several temporary files and directories during operation:
- `__pycache__/` directories and `.pyc` files - Python bytecode cache
- `.venv/` - Virtual environment (should not be committed to repository)

These files are excluded from the Git repository via `.gitignore`.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)

# Bản sửa lỗi tính năng kiểm tra và tải cập nhật

Bản cập nhật này sửa lỗi HTTP 404 khi tải cập nhật từ GitHub Releases.

## Các file đã được sửa đổi

1. **ui/update_dialog.py**
   - Cải thiện hàm `download_update()` để xử lý nhiều định dạng URL khác nhau
   - Thêm kiểm tra sự tồn tại của URL trước khi tải xuống
   - Cải thiện thông báo lỗi với tùy chọn mở trang GitHub Releases
   - Cải thiện hàm `download_error()` để thêm tùy chọn mở GitHub Releases khi gặp lỗi

2. **version.json**
   - Thêm trường `download_url` chứa đường dẫn chính xác cho các nền tảng khác nhau

## Thay đổi chính

### 1. Trong file `ui/update_dialog.py`:
- Giờ đây sẽ thử cả hai định dạng URL có thể có:
  - `https://github.com/shin315/social-download-manager/releases/download/v{version}/Social_Download_Manager_{version}.zip`
  - `https://github.com/shin315/social-download-manager/releases/download/{version}/Social_Download_Manager_{version}.zip`
- Kiểm tra URL xem có tồn tại không trước khi bắt đầu tải xuống
- Ưu tiên sử dụng URL trực tiếp từ file version.json nếu có

### 2. Trong file `version.json`:
- Thêm thông tin URL tải xuống cho các nền tảng khác nhau
```json
{
  "version": "1.1.0",
  "release_notes": "- Fixed bug with TikTok downloads\n- Added new interface features\n- Improved performance\n- Added multiple language support",
  "release_date": "2025-03-28",
  "download_url": {
    "windows": "https://github.com/shin315/social-download-manager/releases/download/v1.1.0/Social_Download_Manager_1.1.0.zip",
    "mac": "https://github.com/shin315/social-download-manager/releases/download/v1.1.0/Social_Download_Manager_1.1.0_mac.zip",
    "linux": "https://github.com/shin315/social-download-manager/releases/download/v1.1.0/Social_Download_Manager_1.1.0_linux.zip"
  }
}
```

## Hướng dẫn áp dụng bản cập nhật

1. Thay thế file `ui/update_dialog.py` bằng phiên bản từ bản cập nhật này
2. Cập nhật file `version.json` để thêm các URL tải xuống như mẫu trên
3. Tải file ZIP của phiên bản mới nhất lên GitHub Releases với đúng định dạng tên như trong URL

## Lưu ý
- Đảm bảo rằng URL trong `version.json` đúng với đường dẫn thực tế trên GitHub Releases
- Để tương thích với phiên bản hiện tại, nên giữ định dạng URL như trong bản mẫu 