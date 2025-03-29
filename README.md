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
