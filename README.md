# 🎬 Video Production Suite

> Professional video editing application with AI-powered content analysis, silence detection, and GPU-accelerated encoding

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/tooboooring/video_production_by_tooboooring)

**Repository**: [https://github.com/tooboooring/video_production_by_tooboooring](https://github.com/tooboooring/video_production_by_tooboooring)

---

## 📋 Table of Contents

- [Features](#-features)
- [Screenshots](#-screenshots)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [Project Structure](#-project-structure)
- [Requirements](#-requirements)
- [Contributing](#-contributing)
- [License](#-license)
- [Upcoming Features](#-upcoming-features)

---

## ✨ Features

### Core Video Processing
- **🎯 Silence Detection & Removal**: Advanced silence detection with customizable thresholds and duration settings
- **✂️ Video Trimming**: Frame-accurate video cutting with multi-segment support
- **🎨 GPU-Accelerated Encoding**: Hardware acceleration support for NVIDIA (NVENC), AMD (AMF), Intel (Quick Sync), and CPU encoding
- **📊 Interactive Timeline**: Visual timeline with waveform visualization for precise editing
- **🎥 Frame-Accurate Preview**: Preview video frames at exact timestamps with FFplay integration
- **🔊 Multi-Track Audio Support**: Process multiple audio tracks with independent silence detection

### AI-Powered Content Analysis
- **🤖 AI Content Analysis**: Intelligent content evaluation using OpenAI Whisper and together.ai
- **📝 Automatic Transcription**: Local audio transcription with word-level timestamps
- **🧠 Context-Aware Analysis**: AI analyzes content with surrounding context for better decisions
- **🎨 Visual Feedback**: Color-coded segments (green=keep, orange=flag) based on AI recommendations
- **💾 Export Analysis**: Save AI decisions and reasoning to JSON for review

### User Interface
- **🖥️ Desktop UI**: Modern CustomTkinter-based interface with tabbed layout
- **🌐 Web UI**: Browser-based interface using PyWebView for cross-platform compatibility
- **⌨️ Keyboard Shortcuts**: Efficient workflow with keyboard navigation
- **🎨 Customizable Themes**: Professional color schemes and UI customization

### Advanced Features
- **📦 Batch Processing**: Process multiple videos in a queue with progress tracking
- **⚙️ Advanced Settings**: Fine-tune silence detection, padding, and encoding parameters
- **💾 Settings Persistence**: Save and restore your preferred settings
- **📈 Progress Tracking**: Real-time progress updates during video processing
- **🔍 Audio Analysis**: Detailed audio track analysis and visualization

---

## 📸 Screenshots

> **Note**: Screenshots will be added here. To add screenshots:
> 1. Place images in a `docs/screenshots/` directory
> 2. Update this section with markdown image links:
>    ```markdown
>    ![Main Interface](docs/screenshots/main_interface.png)
>    ![Timeline View](docs/screenshots/timeline.png)
>    ![AI Analysis](docs/screenshots/ai_analysis.png)
>    ```

---

## 🚀 Installation

### Prerequisites

- **Python 3.8 or higher**
- **FFmpeg** (included in `video_production_app/bin/` or install system-wide)
- **Git** (for cloning the repository)

### Step-by-Step Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/tooboooring/video_production_by_tooboooring.git
   cd video_production_by_tooboooring
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify FFmpeg installation**:
   - FFmpeg executables are included in `video_production_app/bin/`
   - Or ensure FFmpeg is in your system PATH
   - Test with: `ffmpeg -version`

### Optional: AI Analysis Setup

For AI-powered content analysis features:

1. **Get a together.ai API key**:
   - Sign up at [https://together.ai](https://together.ai)
   - Create an API key from your dashboard

2. **Configure API key** (choose one method):
   - **Option A**: Enter in UI settings panel (most secure)
   - **Option B**: Create `.env` file in project root:
     ```bash
     TOGETHER_AI_API_KEY=your_api_key_here
     ```
   - **Option C**: Set system environment variable:
     ```bash
     # Windows
     setx TOGETHER_AI_API_KEY "your_api_key_here"
     
     # macOS/Linux
     export TOGETHER_AI_API_KEY="your_api_key_here"
     ```

---

## 🏃 Quick Start

### Launch the Application

**Option 1: Interactive Launcher** (Recommended)
```bash
python -m video_production_app.launcher
```

**Option 2: Direct Launch**
```bash
# Web UI
python -m video_production_app.main_web_ui

# Desktop UI (Tkinter)
python -m video_production_app.main_tkinter
```

**Option 3: Command-Line Arguments**
```bash
# Launch Web UI directly
python -m video_production_app.launcher web

# Launch Tkinter UI directly
python -m video_production_app.launcher tkinter
```

### Basic Workflow

1. **Load Video**: Click "Load Video" and select your video file
2. **Select Audio Track**: Choose the audio track to analyze
3. **Detect Silence**: Click "Detect Silence" to identify silent segments
4. **Review Timeline**: Check the waveform and segments on the timeline
5. **Optional - AI Analysis**: Run AI analysis to get content recommendations
6. **Process Video**: Click "Process Video" to export the edited video

---

## ⚙️ Configuration

### Silence Detection Settings

Customize silence detection parameters in the Advanced Settings tab:

- **Silence Threshold (dB)**: Volume level to consider as silence (default: -40 dB)
- **Silence Duration (s)**: Minimum duration to detect as silence (default: 0.7s)
- **Padding Before (s)**: Time to keep before silence (default: 0.1s)
- **Padding After (s)**: Time to keep after silence (default: 0.0s)

### Encoder Selection

Choose from multiple encoding options:

- **NVIDIA (H.264/HEVC)**: Hardware acceleration with NVENC (requires NVIDIA GPU)
- **AMD (H.264/HEVC)**: Hardware acceleration with AMF (requires AMD GPU)
- **Intel (H.264/HEVC)**: Hardware acceleration with Quick Sync (requires Intel GPU)
- **CPU (x264)**: Software encoding (works on any system, slower)
- **Automatic**: Automatically selects the best available GPU encoder

### AI Analysis Configuration

Configure AI analysis in the settings:

- **Whisper Model**: Choose transcription quality (tiny/base/small/medium/large)
  - `tiny`: Fastest, lower accuracy (~1GB VRAM)
  - `base`: Good balance, recommended (~1GB VRAM)
  - `small`: Better accuracy (~2GB VRAM)
  - `medium`: Very good accuracy (~5GB VRAM)
  - `large`: Best accuracy, slowest (~10GB VRAM)
- **Context Window**: Seconds before/after each segment to include (default: 30s)
- **API Model**: together.ai model to use (default: Meta-Llama-3.1-8B-Instruct-Turbo)

---

## 📖 Usage Guide

### Main Workflow

1. **Load Video**
   - Click "Load Video" button
   - Select your video file (supports: .mp4, .avi, .mov, .mkv, .wmv, .flv, .webm, .m4v)
   - Video information will be displayed

2. **Detect Silence**
   - Select the audio track to analyze
   - Adjust silence detection parameters if needed
   - Click "Detect Silence"
   - Review segments on the timeline (green=audible, gray=silent)

3. **AI Analysis** (Optional)
   - Enter your together.ai API key in settings
   - Select Whisper model
   - Click "🤖 AI Analysis"
   - Wait for transcription and analysis
   - Review AI recommendations (green=keep, orange=flag)

4. **Manual Editing**
   - Click segments on timeline to toggle keep/remove
   - Use frame preview to check exact timestamps
   - Adjust segment boundaries if needed

5. **Process Video**
   - Select output directory
   - Choose encoder and quality settings
   - Click "Process Video"
   - Monitor progress in the status area

### Batch Processing

1. **Add to Queue**: Click "Add to Batch" after configuring settings
2. **Review Queue**: Check the batch tab to see queued videos
3. **Process All**: Click "Process All" to start batch processing
4. **Monitor Progress**: Track progress for each video in the queue

### Keyboard Shortcuts

- **Space**: Play/Pause preview
- **Arrow Keys**: Navigate timeline
- **Mouse Wheel**: Zoom timeline
- **Click Segment**: Toggle keep/remove

---

## 📁 Project Structure

```
video_production_app/
├── __init__.py                 # Package initialization
├── config.py                   # Configuration constants
├── launcher.py                 # Main launcher
├── main_tkinter.py             # Tkinter UI entry point
├── main_web_ui.py              # Web UI entry point
│
├── core/                       # Core business logic
│   ├── ffmpeg_wrapper.py       # FFmpeg/FFprobe operations
│   ├── silence_detector.py     # Silence detection logic
│   ├── video_processor.py      # Video processing logic
│   └── settings_manager.py     # Settings persistence
│
├── ui/                         # Tkinter UI package
│   ├── app.py                  # Main application window
│   ├── main_tab.py             # Main processing tab
│   ├── preview_tab.py          # Preview & Analysis tab
│   ├── advanced_tab.py         # Advanced settings tab
│   ├── batch_tab.py            # Batch queue tab
│   └── widgets/                # Reusable UI components
│       ├── frame_preview.py    # Frame preview widget
│       ├── timeline.py          # Interactive timeline
│       ├── vlc_player.py        # VLC player integration
│       └── waveform.py         # Waveform generator
│
├── web/                        # Web UI package
│   ├── web_main.py             # PyWebView backend API
│   └── web_ui/                 # Frontend files
│       ├── index.html
│       ├── main.js
│       ├── player.js
│       ├── timeline.js
│       └── style.css
│
├── ai_analysis/                # AI content analysis
│   ├── transcriber.py          # Whisper transcription
│   ├── context_builder.py      # Context extraction
│   ├── ai_analyzer.py          # together.ai integration
│   └── orchestrator.py         # Analysis pipeline
│
├── utils/                      # Utility functions
│   ├── colors.py               # Color theme definitions
│   ├── helpers.py              # Helper functions
│   ├── logger.py               # Logging configuration
│   └── validators.py           # Input validation
│
├── bin/                        # Binary executables
│   ├── ffmpeg.exe              # FFmpeg executable
│   ├── ffprobe.exe             # FFprobe executable
│   └── ffplay.exe              # FFplay executable
│
└── scripts/                    # Build and utility scripts
    ├── build_app.py            # Application builder
    └── create_standalone.py    # Standalone app creator
```

---

## 📦 Requirements

### Core Dependencies

- **customtkinter** >= 5.2.0 - Modern Tkinter UI framework
- **pywebview** >= 4.0.0 - Web UI framework
- **Pillow** >= 10.0.0 - Image processing
- **numpy** >= 1.24.0 - Numerical operations

### AI Analysis Dependencies (Optional)

- **openai-whisper** >= 20231117 - Local audio transcription
- **requests** >= 2.31.0 - HTTP requests for together.ai API
- **pydantic** >= 2.5.0 - Structured data validation

### System Requirements

- **Python**: 3.8 or higher
- **FFmpeg**: Included in `bin/` folder or system installation
- **RAM**: 4GB minimum, 8GB recommended
- **GPU**: Optional but recommended for hardware acceleration
- **Storage**: ~500MB for application + dependencies

### Optional Dependencies

- **python-dotenv** - For `.env` file support
- **torch** - GPU acceleration for Whisper (auto-installed with Whisper)
- **opencv-python** - Enhanced frame preview features
- **librosa** - Advanced audio analysis

---

## 🤝 Contributing

Contributions are welcome! This project follows best practices for maintainability and code organization.

### Development Setup

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Set up development environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
4. **Make your changes** following the existing code structure
5. **Test your changes** thoroughly
6. **Submit a pull request**

### Code Structure Guidelines

- **Separation of Concerns**: UI, business logic, and utilities are separated
- **Module Organization**: Each module has a clear responsibility
- **Documentation**: All functions include comprehensive docstrings
- **Type Hints**: Use type hints for better code clarity
- **Error Handling**: Implement proper error handling and user feedback

### Areas for Contribution

- Bug fixes and improvements
- New features and enhancements
- Documentation improvements
- Performance optimizations
- UI/UX improvements
- Test coverage

---

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

Copyright 2024 Shankargouda Hanchinal

---

## 🚧 Upcoming Features

### Planned Enhancements

#### Video Processing
- [ ] **Multi-format Export**: Support for additional video formats and codecs
- [ ] **Video Effects**: Basic video effects (brightness, contrast, saturation adjustments)
- [ ] **Audio Mixing**: Mix multiple audio tracks with volume control
- [ ] **Subtitle Support**: Import and export SRT subtitle files
- [ ] **Video Stabilization**: Automatic video stabilization for shaky footage
- [ ] **Color Grading**: Basic color correction and grading tools

#### AI Analysis
- [ ] **Custom Prompt Templates**: User-defined AI analysis prompts
- [ ] **Multiple AI Models**: Support for different LLM providers and models
- [ ] **Ensemble Analysis**: Combine decisions from multiple AI models
- [ ] **Content Type Detection**: Automatic detection of video type (tutorial, vlog, interview)
- [ ] **Sentiment Analysis**: Analyze emotional tone of content segments
- [ ] **Keyword Extraction**: Automatic extraction of important keywords and topics
- [ ] **AI Confidence Visualization**: Visual representation of AI confidence levels

#### User Interface
- [ ] **Dark/Light Theme Toggle**: Switch between themes
- [ ] **Customizable Layout**: Resizable and rearrangeable UI panels
- [ ] **Keyboard Shortcut Customization**: User-defined keyboard shortcuts
- [ ] **Multi-language Support**: Internationalization (i18n) support
- [ ] **Tutorial Mode**: Interactive tutorial for new users
- [ ] **Undo/Redo System**: Full undo/redo functionality for edits

#### Performance & Optimization
- [ ] **GPU Acceleration for Whisper**: CUDA support for faster transcription
- [ ] **Parallel Processing**: Process multiple videos simultaneously
- [ ] **Smart Caching**: Intelligent caching of analysis results
- [ ] **Progress Resume**: Resume interrupted processing tasks
- [ ] **Cloud Processing**: Optional cloud-based processing for heavy tasks

#### Collaboration & Sharing
- [ ] **Project Files**: Save and load project configurations
- [ ] **Export Presets**: Save and share processing presets
- [ ] **Collaborative Editing**: Multiple users working on same project
- [ ] **Version Control**: Track changes to video edits
- [ ] **Cloud Storage Integration**: Direct integration with cloud storage services

#### Advanced Features
- [ ] **Audio Ducking**: Automatic background music ducking during speech
- [ ] **Scene Detection**: Automatic scene change detection
- [ ] **Face Detection**: Identify and track faces in video
- [ ] **Object Tracking**: Track objects across frames
- [ ] **Green Screen Support**: Chroma key compositing
- [ ] **Picture-in-Picture**: PIP overlay support
- [ ] **Video Speed Control**: Variable speed playback and export

### Feature Requests

We welcome feature requests from the community! If you have an idea for a feature:

1. **Check existing issues**: Search for similar feature requests
2. **Create an issue**: Open a new issue with the `enhancement` label
3. **Provide details**: Describe the feature, use cases, and potential implementation
4. **Community feedback**: Engage with other users' suggestions

### Roadmap Timeline

- **Q1 2025**: Multi-format export, subtitle support, theme toggle
- **Q2 2025**: Custom prompt templates, GPU Whisper acceleration, project files
- **Q3 2025**: Scene detection, audio ducking, cloud storage integration
- **Q4 2025**: Collaborative editing, advanced effects, mobile app

*Note: Timeline is subject to change based on community feedback and development priorities.*

---

## 🙏 Acknowledgments

- **FFmpeg**: Video processing capabilities
- **OpenAI Whisper**: Speech recognition and transcription
- **together.ai**: AI content analysis
- **CustomTkinter**: Modern UI framework
- **PyWebView**: Web UI framework

---

**Made with ❤️ by the Tooboooring (Shankargouda Hanchinal)**

For questions, issues, or contributions, please visit the [GitHub repository](https://github.com/tooboooring/video_production_by_tooboooring).

