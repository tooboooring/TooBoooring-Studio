"""
Standalone Video Production App - Single File Version

This script creates a single Python file that contains the entire Video Production App.
It bundles all modules into one file for easy distribution and execution.

Usage:
    python create_standalone.py

This will create 'Video_Production_App_Standalone.py' which can be run directly
on any machine with Python and the required dependencies installed.
"""

import os
import sys
from pathlib import Path

def read_file_content(file_path):
    """Read file content and return as string."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return None

def create_standalone_file():
    """Create a single standalone Python file with all modules."""
    
    print("🔨 Creating standalone Video Production App...")
    
    # Define the order of modules to include
    modules = [
        # Core modules first
        "video_production_app/__init__.py",
        "video_production_app/config.py",
        "video_production_app/utils/__init__.py",
        "video_production_app/utils/colors.py",
        "video_production_app/utils/helpers.py",
        "video_production_app/core/__init__.py",
        "video_production_app/core/settings_manager.py",
        "video_production_app/core/ffmpeg_wrapper.py",
        "video_production_app/core/silence_detector.py",
        "video_production_app/core/video_processor.py",
        
        # UI widgets
        "video_production_app/ui/__init__.py",
        "video_production_app/ui/widgets/__init__.py",
        "video_production_app/ui/widgets/waveform.py",
        "video_production_app/ui/widgets/frame_preview.py",
        "video_production_app/ui/widgets/timeline.py",
        
        # UI tabs
        "video_production_app/ui/preview_tab.py",
        "video_production_app/ui/main_tab.py",
        "video_production_app/ui/advanced_tab.py",
        "video_production_app/ui/batch_tab.py",
        "video_production_app/ui/app.py",
    ]
    
    standalone_content = '''"""
Video Production App v3.0 - Standalone Version

This is a standalone version of the Video Production App that combines all modules
into a single Python file for easy distribution and execution.

Features:
- Silence Detection and Removal
- Multi-track Audio Support
- Interactive Timeline with Waveform Display
- Frame Preview
- Batch Processing
- Real-time Progress Tracking
- Multiple Encoder Support (CPU/GPU)

Requirements:
- Python 3.8+
- CustomTkinter: pip install customtkinter
- Optional: numpy, opencv-python, librosa for enhanced features
- FFmpeg installed and accessible via system PATH

Usage:
    python Video_Production_App_Standalone.py

Author: Refactored from Video_production_app_v3.py
Version: 3.0 - Refactored Edition
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Main application entry point
if __name__ == "__main__":
    try:
        from video_production_app.ui.app import VideoProductionApp
        import customtkinter as ctk
        
        print("Video Production App v3.0 initialized")
        print("FFmpeg path: System PATH")
        print("FFprobe path: System PATH") 
        print("FFplay path: System PATH")
        
        # Create and run the application
        app = VideoProductionApp()
        app.mainloop()
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install required packages:")
        print("pip install customtkinter")
        print("pip install pillow")
        print("Optional: pip install numpy opencv-python librosa")
        input("Press Enter to exit...")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        input("Press Enter to exit...")
'''
    
    # Add each module's content
    for module_path in modules:
        if Path(module_path).exists():
            content = read_file_content(module_path)
            if content:
                # Remove the module docstring and imports for standalone version
                lines = content.split('\n')
                
                # Find the start of actual code (after docstring)
                start_line = 0
                in_docstring = False
                docstring_quote = None
                
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    
                    # Check for start of docstring
                    if stripped.startswith('"""') or stripped.startswith("'''"):
                        if not in_docstring:
                            in_docstring = True
                            docstring_quote = stripped[:3]
                            start_line = i
                        elif stripped.endswith(docstring_quote) and len(stripped) > 3:
                            in_docstring = False
                            start_line = i + 1
                            break
                    elif in_docstring and (stripped.endswith('"""') or stripped.endswith("'''")):
                        in_docstring = False
                        start_line = i + 1
                        break
                
                # Skip empty lines at the start
                while start_line < len(lines) and not lines[start_line].strip():
                    start_line += 1
                
                # Add the module content
                module_content = '\n'.join(lines[start_line:])
                
                # Add module separator comment
                standalone_content += f"\n\n# === {module_path} ===\n"
                standalone_content += module_content
                
                print(f"✅ Added {module_path}")
            else:
                print(f"⚠️ Skipped {module_path} (could not read)")
        else:
            print(f"⚠️ Skipped {module_path} (file not found)")
    
    # Write the standalone file
    output_file = "Video_Production_App_Standalone.py"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(standalone_content)
        
        print(f"✅ Created standalone file: {output_file}")
        print(f"📁 File size: {Path(output_file).stat().st_size / 1024:.1f} KB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating standalone file: {e}")
        return False

def create_requirements_file():
    """Create a requirements.txt file for the standalone version."""
    requirements = """# Video Production App v3.0 - Requirements

# Core dependencies (required)
customtkinter>=5.2.0
pillow>=9.0.0

# Optional dependencies (for enhanced features)
numpy>=1.21.0          # For waveform processing
opencv-python>=4.5.0   # For frame preview
librosa>=0.9.0         # For advanced audio analysis

# Note: FFmpeg must be installed separately and accessible via system PATH
# Download from: https://ffmpeg.org/download.html
"""
    
    with open("requirements.txt", 'w') as f:
        f.write(requirements)
    
    print("✅ Created requirements.txt")

def main():
    """Main process to create standalone app."""
    print("🚀 Creating standalone Video Production App...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("video_production_app").exists():
        print("❌ Error: video_production_app folder not found!")
        print("Please run this script from the directory containing the video_production_app folder")
        return False
    
    # Create standalone file
    if not create_standalone_file():
        return False
    
    # Create requirements file
    create_requirements_file()
    
    print("=" * 50)
    print("🎉 Standalone app created successfully!")
    print("📁 Files created:")
    print("   - Video_Production_App_Standalone.py (main app)")
    print("   - requirements.txt (dependencies)")
    print("")
    print("🚀 To run the standalone app:")
    print("   1. Install dependencies: pip install -r requirements.txt")
    print("   2. Run the app: python Video_Production_App_Standalone.py")
    print("")
    print("📦 To create an executable (.exe) file:")
    print("   python build_app.py")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
