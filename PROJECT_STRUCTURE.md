# Video Production Suite - Complete Project Structure

## 📁 Final Organized Structure

```
temp_repo/
│
├── README.md                          # Main documentation
├── LICENSE                            # License file
├── requirements.txt                   # Python dependencies
├── ENV_SETUP.md                       # Environment setup guide
├── UI_FEATURE_ANALYSIS.md             # UI feature analysis
├── PROJECT_STRUCTURE.md               # This file
│
├── tests/                             # Test suite
│   ├── __init__.py
│   ├── test_context_logic.py
│   ├── test_deepseek.py
│   ├── test_prompt_quality.py
│   ├── test_rate_limit.py
│   └── test_transcription_perf.py
│
├── logs/                              # Application logs
│   └── app.log
│
└── video_production_app/
    ├── __init__.py                    # Package initialization
    ├── config.py                      # Configuration constants
    │
    ├── launcher/                      # Main launcher module
    │   ├── __init__.py
    │   └── launcher.py                # Main entry point
    │
    ├── web/                           # Web UI package
    │   ├── __init__.py
    │   ├── launcher.py                # Web UI launcher
    │   ├── web_main.py                # PyWebView backend API
    │   └── web_ui/                    # Frontend files
    │       ├── index.html
    │       ├── main.js
    │       ├── player.js
    │       ├── timeline.js
    │       └── style.css
    │
    ├── ai_analysis/                   # AI analysis module
    │   ├── __init__.py
    │   ├── ai_analyzer.py             # AI decision logic
    │   ├── context_builder.py         # Context window builder
    │   ├── orchestrator.py            # Analysis orchestration
    │   └── transcriber.py            # Whisper transcription
    │
    ├── core/                          # Core business logic
    │   ├── __init__.py
    │   ├── ffmpeg_wrapper.py          # FFmpeg/FFprobe operations
    │   ├── silence_detector.py        # Silence detection logic
    │   ├── video_processor.py         # Video processing logic
    │   ├── settings_manager.py        # Settings persistence
    │   └── project_manager.py         # Project save/load functionality
    │
    ├── utils/                         # Utility functions
    │   ├── __init__.py
    │   ├── colors.py                  # Color theme definitions
    │   ├── entry_helpers.py           # Entry point helpers
    │   ├── helpers.py                 # Helper functions
    │   ├── logger.py                  # Logging configuration
    │   ├── validators.py              # Input validation
    │   └── waveform.py                # Waveform generator
    │
    └── bin/                           # Binary executables
        ├── __init__.py
        ├── ffmpeg.exe                 # FFmpeg executable
        ├── ffprobe.exe                # FFprobe executable
        └── ffplay.exe                 # FFplay executable
```

## 🚀 How to Run

### Option 1: Via Main Launcher (Recommended)
```bash
python -m video_production_app.launcher.launcher
```

### Option 2: Direct Web UI Launcher
```bash
python -m video_production_app.web.launcher
```

## 📦 Package Organization

### Launcher (`launcher/`)
Main application entry point that launches the Web UI.

### Web UI (`web/`)
Complete web-based interface with PyWebView backend and HTML/CSS/JavaScript frontend.
- `launcher.py`: Entry point for Web UI
- `web_main.py`: Backend API exposed to frontend
- `web_ui/`: Frontend files (HTML, CSS, JavaScript)

### AI Analysis (`ai_analysis/`)
AI-powered content analysis using Together.ai API and Whisper transcription.

### Core Logic (`core/`)
All business logic separated from UI, making it testable and reusable.
- Video processing
- Silence detection
- FFmpeg operations
- Settings management
- Project save/load (.tbproj files)

### Utilities (`utils/`)
Shared utility functions, validators, logging, theme definitions, and waveform generation.

### Binaries (`bin/`)
FFmpeg executables in a dedicated folder for easy management.

### Tests (`tests/`)
Test suite for validating functionality.

## 🔧 Key Features

- **Clean Separation**: UI, business logic, and utilities are clearly separated
- **Modular Design**: Each component can be imported and used independently
- **Easy Maintenance**: Clear folder structure makes finding files simple
- **Professional Organization**: Follows Python package best practices
- **Web-Only UI**: Modern browser-based interface using PyWebView

## 📝 Notes

- FFmpeg executables are in `bin/` folder
- Web UI is the only supported interface (Tkinter UI removed)
- Entry points are located with their respective modules
- All documentation is at the project root
- Waveform generation moved to `utils/` for shared use

