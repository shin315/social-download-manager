# Social Download Manager v2.0 - Installation Guide

## Welcome to Social Download Manager v2.0!

This guide will help you install and set up Social Download Manager v2.0 on your computer. Don't worry if you're not tech-savvy – we'll walk you through everything step by step!

## Table of Contents
- [System Requirements](#system-requirements)
- [Download Options](#download-options)
- [Windows Installation](#windows-installation)
- [macOS Installation](#macos-installation)
- [Linux Installation](#linux-installation)
- [First-Time Setup](#first-time-setup)
- [Troubleshooting Installation Issues](#troubleshooting-installation-issues)

## System Requirements

Before installing, make sure your computer meets these requirements:

### Minimum Requirements
- **Operating System**: Windows 10, macOS 10.14, or Ubuntu 18.04 (or equivalent Linux distribution)
- **Memory (RAM)**: 4 GB RAM
- **Storage**: 500 MB free disk space
- **Internet**: Stable internet connection for downloading content

### Recommended Requirements
- **Operating System**: Windows 11, macOS 12+, or Ubuntu 20.04+
- **Memory (RAM)**: 8 GB RAM or more
- **Storage**: 2 GB free disk space (more for downloaded content)
- **Internet**: High-speed broadband connection

### Additional Notes
- Administrator privileges required for installation
- Antivirus software may need temporary adjustment during installation
- Some platforms may require additional authentication setup

## Download Options

You have several ways to get Social Download Manager v2.0:

### Option 1: Installer Package (Recommended for Beginners)
- **Windows**: Download the `.msi` installer file
- **macOS**: Download the `.dmg` installer file
- **Linux**: Download the `.deb` package (Ubuntu/Debian) or `.rpm` package (CentOS/Fedora)

### Option 2: Portable Version
- **All Platforms**: Download the portable `.zip` file
- No installation required – just extract and run
- Perfect for USB drives or temporary use

### Option 3: From Source (Advanced Users)
- Download from GitHub repository
- Requires Python 3.8+ and technical knowledge
- Best for developers or advanced customization

## Windows Installation

### Using the Installer (Recommended)

1. **Download the Installer**
   - Go to the official download page
   - Click "Download for Windows"
   - Save the `SocialDownloadManager_v2.0_Setup.msi` file to your Downloads folder

2. **Run the Installer**
   - Double-click the downloaded file
   - If Windows shows a security warning, click "More info" then "Run anyway"
   - You may need to enter your administrator password

3. **Installation Wizard**
   - Welcome screen: Click "Next"
   - License agreement: Read and click "I agree" then "Next"
   - Installation location: Keep default or choose a different folder, then click "Next"
   - Start menu folder: Keep default or change, then click "Next"
   - Ready to install: Click "Install"

4. **Complete Installation**
   - Wait for the progress bar to complete (usually 1-2 minutes)
   - Installation complete: Click "Finish"
   - The application will appear in your Start menu and desktop (if selected)

### Using the Portable Version

1. **Download and Extract**
   - Download `SocialDownloadManager_v2.0_Windows_Portable.zip`
   - Right-click the file and select "Extract All"
   - Choose a location like `C:\Programs\SocialDownloadManager\`

2. **Run the Application**
   - Navigate to the extracted folder
   - Double-click `SocialDownloadManager.exe`
   - Create a desktop shortcut by right-clicking the exe file

## macOS Installation

### Using the DMG Installer

1. **Download the Installer**
   - Download `SocialDownloadManager_v2.0_macOS.dmg`
   - The file will appear in your Downloads folder

2. **Mount and Install**
   - Double-click the `.dmg` file to mount it
   - A window will open showing the application icon
   - Drag the "Social Download Manager" icon to the "Applications" folder
   - Wait for the copy process to complete

3. **First Launch**
   - Open the Applications folder
   - Find "Social Download Manager" and double-click it
   - macOS may show a security warning – click "Open" to proceed
   - If blocked, go to System Preferences > Security & Privacy > General > Click "Open Anyway"

4. **Add to Dock (Optional)**
   - Right-click the application icon in the dock
   - Select "Options" > "Keep in Dock"

## Linux Installation

### Ubuntu/Debian (.deb package)

1. **Download the Package**
   - Download `social-download-manager_2.0_amd64.deb`

2. **Install Using GUI**
   - Double-click the `.deb` file
   - Software Center will open
   - Click "Install" and enter your password

3. **Install Using Terminal**
   ```bash
   cd ~/Downloads
   sudo dpkg -i social-download-manager_2.0_amd64.deb
   sudo apt-get install -f  # Fix any dependency issues
   ```

### CentOS/Fedora (.rpm package)

1. **Download and Install**
   ```bash
   cd ~/Downloads
   sudo rpm -i social-download-manager-2.0-1.x86_64.rpm
   ```

2. **Or using DNF (Fedora)**
   ```bash
   sudo dnf install ./social-download-manager-2.0-1.x86_64.rpm
   ```

### AppImage (Universal Linux)

1. **Download and Run**
   - Download `SocialDownloadManager-2.0-x86_64.AppImage`
   - Make it executable: `chmod +x SocialDownloadManager-2.0-x86_64.AppImage`
   - Run it: `./SocialDownloadManager-2.0-x86_64.AppImage`

## First-Time Setup

After installation, you'll need to configure the application:

### Initial Configuration Wizard

1. **Welcome Screen**
   - Language selection (choose your preferred language)
   - Theme selection (Light, Dark, or System)
   - Click "Continue"

2. **Download Settings**
   - Choose default download folder (e.g., `Downloads/SocialMedia`)
   - Select default video quality (HD recommended)
   - Enable/disable audio-only downloads
   - Click "Continue"

3. **Privacy Settings**
   - Choose whether to enable analytics (helps improve the app)
   - Configure error reporting preferences
   - Review privacy policy
   - Click "Continue"

4. **Platform Setup**
   - No immediate setup required for TikTok
   - YouTube: Optional API key for enhanced features
   - Other platforms: Will be configured when first used
   - Click "Finish"

### Testing Your Installation

1. **Quick Test**
   - Copy a TikTok video URL (e.g., from your browser)
   - Paste it into the URL field in the app
   - Click "Download"
   - Check that the video downloads to your chosen folder

2. **Verify Features**
   - Test different video qualities
   - Try downloading to different folders
   - Test pause/resume functionality

## Troubleshooting Installation Issues

### Common Windows Issues

**Issue: "Windows protected your PC" message**
- **Solution**: Click "More info" then "Run anyway". This is normal for new software.

**Issue: Installation fails with "Administrator rights required"**
- **Solution**: Right-click the installer and select "Run as administrator"

**Issue: Antivirus blocks installation**
- **Solution**: Temporarily disable antivirus, install, then re-enable it. Add the application to your antivirus whitelist.

**Issue: "MSVCP140.dll missing" error**
- **Solution**: Install Microsoft Visual C++ Redistributable from Microsoft's website

### Common macOS Issues

**Issue: "App is damaged and can't be opened"**
- **Solution**: 
  1. Open Terminal
  2. Type: `sudo xattr -rd com.apple.quarantine /Applications/Social\ Download\ Manager.app`
  3. Enter your password

**Issue: Application won't start**
- **Solution**: Check System Preferences > Security & Privacy > General for blocked apps

**Issue: "App is from an unidentified developer"**
- **Solution**: Hold Control while clicking the app, then select "Open"

### Common Linux Issues

**Issue: Dependency problems**
- **Solution**: Update your package manager first: `sudo apt update` (Ubuntu/Debian)

**Issue: Permission denied**
- **Solution**: Make sure you downloaded the correct architecture (x86_64 for 64-bit systems)

**Issue: AppImage won't run**
- **Solution**: Install FUSE: `sudo apt install fuse libfuse2` (Ubuntu/Debian)

### General Issues

**Issue: App crashes on startup**
- **Solutions**:
  1. Delete configuration folder and restart (fresh setup)
  2. Check system requirements again
  3. Update graphics drivers
  4. Run as administrator (Windows) or with sudo (Linux)

**Issue: Downloads don't work**
- **Solutions**:
  1. Check internet connection
  2. Verify download folder permissions
  3. Try a different download location
  4. Check firewall settings

**Issue: Slow performance**
- **Solutions**:
  1. Close other applications to free memory
  2. Choose a lower video quality
  3. Check available disk space
  4. Limit concurrent downloads in settings

## Getting Help

If you're still having trouble:

1. **Check the User Manual** - Available in the app's Help menu
2. **Visit our FAQ** - Common questions and answers
3. **Community Forum** - Ask questions and get help from other users
4. **Contact Support** - Email us with specific technical issues

### What to Include When Reporting Issues

- Operating system and version
- Application version
- Steps to reproduce the problem
- Error messages (copy the exact text)
- Screenshots if helpful

## Next Steps

Now that Social Download Manager v2.0 is installed:

1. **Read the Getting Started Guide** - Learn the basic workflows
2. **Explore the User Manual** - Discover all features
3. **Customize Your Settings** - Tailor the app to your needs
4. **Start Downloading** - Begin using your new content manager!

---

**Congratulations!** You've successfully installed Social Download Manager v2.0. Enjoy downloading and managing your favorite social media content!

---

*Social Download Manager v2.0 User Installation Guide*
*Last updated: June 2025* 