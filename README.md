# Social Download Manager

A powerful tool for downloading TikTok videos without watermarks. Current version: 1.2.0

## Features

- Download TikTok videos without watermark
- Multi-language support (English & Vietnamese)
- Batch download support
- Download history management
- Video quality selection
- Preview downloaded videos within the app
- Copy video information (title, creator, hashtags)
- Download audio only (MP3 format)
- Light/dark mode interface
- Open file location without command prompt flashing

## What's New (v1.2.0)

- Optimized column widths for better multi-language display (especially Vietnamese)
- Fixed command prompt flashing when opening file locations
- Unchecked "Delete from disk" by default when deleting videos to prevent accidental deletion
- Improved sorting in "Downloaded Videos" tab
- Auto-sort videos by download date

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

1. Copy TikTok video URL
2. Paste URL into the application
3. Select desired video quality
4. Click "Download" to start downloading
5. View download history in the "Downloaded Videos" tab

### Downloading as MP3
To download audio only in MP3 format:
1. Paste the video URL
2. Select "Audio" quality in the dropdown menu
3. Click "Download"
4. The application will download the video and automatically convert it to MP3 format using FFmpeg

## Packaging the Application

To create a standalone executable file, we provide a build script that automates the PyInstaller process.

### Requirements
- Python 3.7+
- PyInstaller (will be automatically installed if missing)

### Steps to Package
1. Navigate to the project directory
2. Run the build script:
   ```
   python build.py
   ```
3. The script will:
   - Create or update the PyInstaller spec file
   - Package all assets and localization files correctly
   - Build the standalone executable file
   - Open the dist folder containing the final executable

### Troubleshooting
If you encounter issues with missing icons or images in the packaged application, ensure:
1. All assets are in the `assets` folder
2. The spec file includes all necessary data files
3. Try rebuilding with a clean build:
   ```
   python build.py clean
   ``` 