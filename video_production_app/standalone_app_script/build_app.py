"""
Build script for creating a standalone Video Production App executable.

This script uses PyInstaller to create a single executable file (.exe) that
includes all dependencies and can run on any Windows machine without requiring
Python or any additional installations.

Usage:
    python build_app.py

The script will:
1. Install PyInstaller if not already installed
2. Create a standalone executable
3. Include all necessary files and dependencies
4. Generate a single .exe file that can be distributed
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_pyinstaller():
    """Install PyInstaller if not already available."""
    try:
        import PyInstaller
        print("[OK] PyInstaller is already installed")
        return True
    except ImportError:
        print("[INFO] Installing PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("[OK] PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("[ERROR] Failed to install PyInstaller")
            return False

def create_spec_file():
    """Create a PyInstaller spec file for better control over the build."""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['video_production_app/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('video_production_app', 'video_production_app'),
    ] + ([('logo.png', '.')] if os.path.exists('logo.png') else []),
    hiddenimports=[
        'customtkinter',
        'tkinter',
        'PIL',
        'numpy',
        'cv2',
        'librosa',
        'pathlib',
        'threading',
        'subprocess',
        'json',
        'datetime',
        're',
        'os',
        'shutil',
        'tempfile',
        'typing',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Video_Production_App',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for windowed app (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.png' if os.path.exists('logo.png') else None,  # App icon
)
'''
    
    with open('Video_Production_App.spec', 'w') as f:
        f.write(spec_content)
    print("[OK] Created PyInstaller spec file")

def build_executable():
    """Build the standalone executable using PyInstaller."""
    print("[INFO] Building standalone executable...")
    
    try:
        # Use the spec file for better control
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm", 
            "Video_Production_App.spec"
        ])
        
        print("[OK] Executable built successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Build failed: {e}")
        return False

def create_distribution_folder():
    """Create a clean distribution folder with the executable and README."""
    dist_folder = Path("Video_Production_App_Distribution")
    
    if dist_folder.exists():
        shutil.rmtree(dist_folder)
    
    dist_folder.mkdir()
    
    # Copy the executable
    exe_path = Path("dist/Video_Production_App.exe")
    if exe_path.exists():
        shutil.copy2(exe_path, dist_folder / "Video_Production_App.exe")
        print(f"[OK] Copied executable to {dist_folder}")
    else:
        print("[ERROR] Executable not found in dist folder")
        return False
    
    # Create README
    readme_content = """# Video Production App v3.0

## Standalone Executable

This is a standalone version of the Video Production App that can run on any Windows machine without requiring Python or additional installations.

## Features

- **Silence Detection**: Automatically detect and remove silent parts from videos
- **Multi-track Audio Support**: Handle videos with multiple audio tracks
- **Interactive Timeline**: Visual timeline with waveform display and zoom/scroll
- **Frame Preview**: Preview individual video frames
- **Batch Processing**: Process multiple videos in queue
- **Progress Tracking**: Real-time progress bar with ETA and speed information
- **Multiple Encoders**: Support for CPU and GPU encoders (NVIDIA, AMD, Intel)

## Requirements

- Windows 10 or later
- FFmpeg installed and accessible via system PATH (or place ffmpeg.exe in the same folder)

## Usage

1. Double-click `Video_Production_App.exe` to start the application
2. Use the Preview tab to load and analyze your video
3. Switch to Main Processing tab to configure settings and process the video
4. Monitor progress with the enhanced progress bar

## FFmpeg Setup

If FFmpeg is not in your system PATH, you can:
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract the files
3. Place `ffmpeg.exe`, `ffprobe.exe`, and `ffplay.exe` in the same folder as this executable

## Support

This application was refactored from a monolithic Python script into a clean, modular architecture while maintaining all original functionality.

## Version

Video Production App v3.0 - Refactored Edition
"""
    
    with open(dist_folder / "README.txt", 'w') as f:
        f.write(readme_content)
    
    print(f"[OK] Created distribution folder: {dist_folder}")
    return True

def cleanup():
    """Clean up temporary build files."""
    print("[INFO] Cleaning up temporary files...")
    
    # Remove build folder
    if Path("build").exists():
        shutil.rmtree("build")
    
    # Remove dist folder (we already copied the exe)
    if Path("dist").exists():
        shutil.rmtree("dist")
    
    # Remove spec file
    if Path("Video_Production_App.spec").exists():
        os.remove("Video_Production_App.spec")
    
    print("[OK] Cleanup complete")

def main():
    """Main build process."""
    print("Starting Video Production App build process...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("video_production_app").exists():
        print("[ERROR] video_production_app folder not found!")
        print("Please run this script from the directory containing the video_production_app folder")
        return False
    
    # Step 1: Install PyInstaller
    if not install_pyinstaller():
        return False
    
    # Step 2: Create spec file
    create_spec_file()
    
    # Step 3: Build executable
    if not build_executable():
        return False
    
    # Step 4: Create distribution folder
    if not create_distribution_folder():
        return False
    
    # Step 5: Cleanup
    cleanup()
    
    print("=" * 50)
    print("[SUCCESS] Build process completed successfully!")
    print("[INFO] Your standalone app is in: Video_Production_App_Distribution/")
    print("[INFO] You can now distribute Video_Production_App.exe to any Windows machine!")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
