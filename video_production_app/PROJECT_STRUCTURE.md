# Video Production Suite - Complete Project Structure

## 📁 Final Organized Structure

```
video_production_app/
│
├── __init__.py                    # Package initialization
├── config.py                      # Configuration constants
│
├── entry_points/                  # Application entry points
│   ├── __init__.py
│   ├── main.py                    # Main entry (redirects to launcher)
│   ├── web_ui.py                  # Web UI entry point
│   └── tkinter_ui.py              # Tkinter UI entry point
│
├── launcher/                      # Launcher module
│   ├── __init__.py
│   └── launcher.py                # Interactive launcher
│
├── web/                           # Web UI package
│   ├── __init__.py
│   ├── web_main.py                # PyWebView backend API
│   └── web_ui/                    # Frontend files
│       ├── index.html
│       ├── main.js
│       ├── player.js
│       ├── timeline.js
│       └── style.css
│
├── ui/                            # Tkinter UI package
│   ├── __init__.py
│   ├── app.py                     # Main application window
│   ├── main_tab.py                # Main processing tab
│   ├── preview_tab.py             # Preview & Analysis tab
│   ├── advanced_tab.py            # Advanced settings tab
│   ├── batch_tab.py               # Batch queue tab
│   └── widgets/                   # Reusable UI components
│       ├── __init__.py
│       ├── frame_preview.py       # Frame preview widget
│       ├── timeline.py            # Interactive timeline
│       ├── vlc_player.py          # VLC player integration
│       └── waveform.py            # Waveform generator
│
├── core/                          # Core business logic
│   ├── __init__.py
│   ├── ffmpeg_wrapper.py          # FFmpeg/FFprobe operations
│   ├── silence_detector.py        # Silence detection logic
│   ├── video_processor.py          # Video processing logic
│   └── settings_manager.py         # Settings persistence
│
├── utils/                         # Utility functions
│   ├── __init__.py
│   ├── colors.py                  # Color theme definitions
│   ├── helpers.py                 # Helper functions
│   ├── logger.py                  # Logging configuration
│   └── validators.py              # Input validation
│
├── bin/                           # Binary executables
│   ├── __init__.py
│   ├── ffmpeg.exe                 # FFmpeg executable
│   ├── ffprobe.exe                # FFprobe executable
│   └── ffplay.exe                 # FFplay executable
│
├── assets/                        # Application assets
│   └── logo.png                   # Application logo
│
├── scripts/                       # Build and utility scripts
│   ├── build_app.py               # Application builder
│   ├── build_tools.bat            # Build tools script
│   ├── create_logo.py             # Logo generator
│   ├── create_standalone.py       # Standalone app creator
│   └── Video_production_app_v3_backup2.py  # Legacy backup
│
└── docs/                          # Documentation
    ├── README.md                  # Main documentation
    ├── README_MERGED_FILE.txt     # Merged file info
    └── MERGED_COMPLETE_APP.py     # Legacy merged app (reference)
```

## 🚀 How to Run

### Option 1: Via Launcher (Recommended)
```bash
python -m video_production_app.launcher
```

### Option 2: Direct Entry Points
```bash
# Web UI
python -m video_production_app.entry_points.web_ui

# Tkinter UI
python -m video_production_app.entry_points.tkinter_ui

# Main entry (redirects to launcher)
python -m video_production_app.entry_points.main
```

### Option 3: Command Line Arguments
```bash
# Web UI via launcher
python -m video_production_app.launcher web

# Tkinter UI via launcher
python -m video_production_app.launcher tkinter
```

## 📦 Package Organization

### Entry Points (`entry_points/`)
All application entry points are centralized here for easy access and maintenance.

### Web UI (`web/`)
Complete web-based interface with PyWebView backend and HTML/CSS/JavaScript frontend.

### Tkinter UI (`ui/`)
Desktop application interface with CustomTkinter, organized into tabs and reusable widgets.

### Core Logic (`core/`)
All business logic separated from UI, making it testable and reusable.

### Utilities (`utils/`)
Shared utility functions, validators, logging, and theme definitions.

### Binaries (`bin/`)
FFmpeg executables in a dedicated folder for easy management.

### Assets (`assets/`)
Application resources like logos and icons.

### Scripts (`scripts/`)
Build scripts and development utilities.

### Documentation (`docs/`)
All documentation files in one place.

## 🔧 Key Features

- **Clean Separation**: UI, business logic, and utilities are clearly separated
- **Modular Design**: Each component can be imported and used independently
- **Easy Maintenance**: Clear folder structure makes finding files simple
- **Professional Organization**: Follows Python package best practices
- **Multiple UIs**: Both web and desktop interfaces supported
- **Centralized Entry Points**: All ways to launch the app in one place

## 📝 Notes

- FFmpeg executables are now in `bin/` folder (updated paths in code)
- All entry points are in `entry_points/` folder
- Web UI files are in `web/` folder
- Documentation is in `docs/` folder
- Build scripts are in `scripts/` folder

