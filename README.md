# Social Download Manager

A powerful tool for downloading videos from various social media platforms without watermarks.

## Features

- Download TikTok videos without watermark
- Multi-language support (English & Vietnamese)
- Batch download support
- Download history management
- Video quality selection
- Copy video information (title, creator, hashtags)

## Requirements

- Python 3.8+
- PyQt6
- requests
- beautifulsoup4

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