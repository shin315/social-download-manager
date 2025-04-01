import os
import subprocess
import sys
import shutil
import time
from pathlib import Path

def create_exe():
    """Create executable file with PyInstaller"""
    print("Building Social Download Manager...")
    
    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Determine the spec file path
    spec_path = Path("social_download_manager.spec")
    
    # Check if spec file already exists
    if not spec_path.exists():
        # Generate a .spec file first - this will help with customizations
        cmd = [
            "pyinstaller",
            "--name=social_download_manager",
            "--noconsole",  # No console window
            "--onefile",    # Create a single executable
            "--icon=assets/Logo_new_32x32.png",  # Use the new logo as icon
            "--add-data=assets;assets",  # Include assets directory
            "--add-data=localization;localization",  # Include localization
            "--add-data=config.template.json;.",  # Include template config
            "main.py"  # Main script
        ]
        
        subprocess.check_call(cmd)
        print("Created spec file.")
    
    # Build using the spec file
    build_cmd = ["pyinstaller", str(spec_path)]
    subprocess.check_call(build_cmd)
    
    print("Build completed successfully!")
    print("Executable is in the 'dist' folder.")
    
    # Ensure a blank config.json is in the dist folder
    dist_dir = Path("dist/social_download_manager")
    if dist_dir.exists():
        with open(dist_dir / "config.json", "w") as f:
            f.write("{}")
        print("Created empty config.json in distribution folder.")
    
    # Open the directory with the executable
    if sys.platform == "win32":
        os.startfile("dist")
    elif sys.platform == "darwin":  # macOS
        subprocess.check_call(["open", "dist"])
    else:  # Linux
        subprocess.check_call(["xdg-open", "dist"])

if __name__ == "__main__":
    create_exe() 