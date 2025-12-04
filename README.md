# 🎥 TooBoooring Studio (Gemini 3 Edition)

**An Agentic Video Editor that "Thinks" before it cuts.**

⚡ **Vibe Coded**: Built using Gemini 3's agentic coding capabilities via Google Antigravity.
🧠 **Powered by Gemini 3 Pro**: Uses the new `thinking_config` parameter to reason about narrative flow, not just keywords.

---

# TooBoooring Studio 3.0

> Professional video editing application with AI-powered content analysis, silence detection, and GPU-accelerated encoding

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/tooboooring/video_production_by_tooboooring)

**Repository**: [https://github.com/tooboooring/video_production_by_tooboooring](https://github.com/tooboooring/video_production_by_tooboooring)

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Performance Benchmarks](#performance-benchmarks)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Contributing](#contributing)
- [Upcoming Features](#upcoming-features)
- [License](#license)

---

## Features

### Core Video Processing

- **Silence Detection & Removal**: Advanced silence detection with customizable thresholds and duration settings
- **Video Trimming**: Frame-accurate video cutting with multi-segment support
- **GPU-Accelerated Encoding**: Hardware acceleration support for NVIDIA (NVENC), AMD (AMF), Intel (Quick Sync), and CPU encoding
- **Enhanced Timeline**: Smooth waveform visualization with color-coded segments for precise editing
- **Frame-Accurate Preview**: Preview video frames at exact timestamps with FFplay integration
- **Multi-Track Audio Mixer**: Listen to all audio tracks simultaneously with toggle controls - works with any language (Hindi, English, etc.)
- **Drag & Drop**: Simple drag and drop interface for quick video loading
- **Project Save/Load**: Save your editing sessions to .tbproj files and resume later with all segments, settings, and AI analysis history preserved

### AI-Powered Content Analysis

- **AI Content Analysis**: Intelligent content evaluation using OpenAI Whisper and together.ai
- **Automatic Transcription**: Local audio transcription with word-level timestamps (cached for performance)
- **Context-Aware Analysis**: AI analyzes content with surrounding context for better decisions
- **Visual Feedback**: Color-coded segments (green=keep, orange=flag) based on AI recommendations
- **Export Analysis**: Save AI decisions and reasoning to JSON for review
- **Analysis History**: Toggle between different AI analysis runs without re-analyzing
- **Model Tooltips**: Hover over AI models to see detailed information (personality, use cases, cut rates)
- **Multiple AI Models**: Choose from 4 specialized models optimized for different content types

### User Interface

- **Modern Web UI**: Professional three-panel layout with PyWebView for cross-platform compatibility
- **Tabbed Navigation**: Organized workspace with Media, AI Tools, and Export tabs
- **Dark Theme**: Sleek, modern zinc/slate dark theme with indigo accents optimized for video editing
- **Keyboard Shortcuts**: Efficient workflow with keyboard navigation (Ctrl+S to save, Ctrl+O to open)
- **Cost Estimation**: Real-time cost and token count estimates before running AI analysis
- **Auto-Save**: Automatic project saves every 5 minutes to prevent data loss

### Advanced Features

- **Advanced Settings**: Fine-tune silence detection, padding, and encoding parameters
- **Settings Persistence**: Save and restore your preferred settings
- **Progress Tracking**: Real-time progress updates during video processing
- **Audio Analysis**: Detailed audio track analysis and visualization

---

## Screenshots

### Main Interface

_Professional three-panel layout with video player, timeline, and tabbed controls_

![Main Interface](video_production_app/docs/screenshots/image.png)

### Timeline and Waveform Visualization

_Enhanced timeline with smooth waveform display and color-coded segments_

![Timeline and Waveform View](video_production_app/docs/screenshots/image2.png)

### AI Analysis and Project Management

_AI-powered content analysis with model selection and project save/load features_

![AI Analysis and Project Management](video_production_app/docs/screenshots/image3.png)

---

## Installation

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
     TOGETHER_API_KEY=your_api_key_here
     ```
   - **Option C**: Set system environment variable:

     ```bash
     # Windows
     setx TOGETHER_API_KEY "your_api_key_here"

     # macOS/Linux
     export TOGETHER_API_KEY="your_api_key_here"
     ```

---

## Quick Start

### Launch the Application

**Recommended method:**

```bash
python -m video_production_app.launcher.launcher
```

**Alternative (Web UI directly):**

```bash
python -m video_production_app.web.launcher
```

**Troubleshooting launch issues:**

- If you get "No module named 'video_production_app'", ensure you're in the project root directory
- If FFmpeg is not found, verify `video_production_app/bin/` contains the executables
- On Windows, you may need to run as administrator for first launch

### Basic Workflow

1. **Load Video**: Click "Load Video" or drag & drop a video file
2. **Detect Silence**: Navigate to AI Tools tab and click "Detect Silence"
3. **AI Analysis** (Optional): Run AI analysis for intelligent content recommendations
4. **Save Project** (Ctrl+S): Save your editing session to a `.tbproj` file
5. **Export Video**: Navigate to Export tab and click "Export Video"

---

## Configuration

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
- **AI Model**: Choose from 4 specialized models optimized for different content types:

| Model                           | Price (per 1M tokens) | Best For                    | Cut Rate      | Personality        |
| ------------------------------- | --------------------- | --------------------------- | ------------- | ------------------ |
| **Llama 3.3 70B** (Recommended) | $0.88                 | Vlogs, Tutorials, Narrative | Low (~5%)     | Friendly & Lenient |
| **DeepSeek R1** (Ruthless)      | $4.00                 | TikToks, Reels, Highlights  | High (~75%)   | Ruthless & Strict  |
| **Qwen 2.5 72B** (Balanced)     | $1.20                 | Corporate, Educational      | Medium (~15%) | Balanced & Logical |
| **Llama 3.1 8B** (Speed)        | $0.18                 | Quick tests, Rough cuts     | Variable      | Fast but Basic     |

**Cost Estimation Example**: A 10-minute video with 100 segments analyzed with Llama 3.3 70B typically costs $0.05-0.15.

---

## Usage Guide

### Understanding the Interface

The **TB Studio** interface is organized into a modern three-panel layout:

**Top Section:**

- **Header Bar**: Shows app branding, system status, and quick export button
- **Left Sidebar (480px)**: Tabbed navigation with three main sections:
  - **Media Tab**: Video loading, drag & drop zone
  - **AI Tools Tab**: Silence detection, AI analysis, transcription settings
  - **Export Tab**: Encoding options, format selection, render queue
- **Center Panel**: Video player with audio track mixer (when applicable)
- **Bottom Panel**: Interactive timeline with:
  - Time ruler
  - Multi-track waveform visualization
  - Color-coded segments (green/red/orange)
  - Zoom and scroll controls

### Main Workflow

1. **Load Video**

   - **Method A**: Click "Load Video" button in the Media tab
   - **Method B**: Drag & drop a video file into the upload zone
   - Supported formats: .mp4, .avi, .mov, .mkv, .wmv, .flv, .webm, .m4v
   - Video information will be displayed in the header

2. **Multi-Track Audio** (If applicable)

   - Audio track mixer appears above the video player
   - Toggle checkboxes to enable/disable tracks
   - Listen to all enabled tracks mixed in real-time
   - Works with any language (Hindi, English, etc.)

3. **Detect Silence**

   - Navigate to the **AI Tools** tab
   - Select the audio track to analyze from the dropdown
   - Adjust silence detection parameters if needed
   - Click "Detect Silence"
   - Review segments on the enhanced timeline:
     - Green = audible segments
     - Gray = silent segments
     - Smooth waveform visualization

4. **AI Analysis** (Optional)

   - Stay in the **AI Tools** tab
   - Enter your together.ai API key (saved securely in browser)
   - Select AI model (hover for detailed tooltip showing personality and cut rates)
   - Select Whisper model for transcription quality
   - View real-time cost estimate
   - Click "Run AI Analysis"
   - Wait for transcription and analysis
   - Review AI recommendations:
     - Green = keep segments
     - Red = remove segments (silence)
     - Orange/Purple = AI flagged segments
   - **Toggle History**: Use the History dropdown to compare different AI runs instantly

5. **Manual Editing**

   - Click segments on timeline to toggle keep/remove status
   - Zoom in/out using timeline controls
   - Scroll through long videos
   - Use frame preview to check exact timestamps

6. **Export Video**
   - Navigate to the **Export** tab
   - Choose encoder (GPU or CPU)
   - Select output format (MP4, MOV)
   - Set trim points if needed
   - Click "Export Video"
   - Monitor progress in real-time
   - **Additional Export Options**:
     - **Cuts List (TXT)**: Simple text file listing all kept/removed segments with timestamps
     - **EDL (Edit Decision List)**: Industry-standard format for importing into Premiere Pro, Final Cut Pro, or DaVinci Resolve
     - **XML**: Advanced project interchange format for professional NLE software
     - **JSON**: AI analysis decisions with reasoning for review and debugging

### Keyboard Shortcuts

#### Playback Controls

- **Space**: Play/Pause preview
- **Arrow Left/Right**: Navigate timeline (frame by frame)
- **Arrow Up/Down**: Zoom timeline in/out

#### File Operations

- **Ctrl+S** (or **Cmd+S** on macOS): Save project
- **Ctrl+O** (or **Cmd+O** on macOS): Open project
- **Ctrl+Shift+S**: Save project as (shows dialog)

#### Editing

- **Mouse Wheel**: Zoom timeline
- **Click Segment**: Toggle keep/remove status
- **Drag Timeline**: Scroll through video

---

## Project Structure

```
video_production_app/
├── __init__.py                 # Package initialization
├── config.py                   # Configuration constants
│
├── launcher/                   # Main launcher module
│   ├── __init__.py
│   └── launcher.py             # Main entry point
│
├── web/                        # Web UI package
│   ├── __init__.py
│   ├── launcher.py             # Web UI entry point
│   ├── web_main.py             # PyWebView backend API
│   └── web_ui/                 # Frontend files
│       ├── index.html          # Main HTML
│       ├── main.js             # Main JavaScript logic
│       ├── player.js           # Video player controls
│       ├── timeline.js         # Timeline visualization
│       └── style.css           # Stylesheet
│
├── core/                       # Core business logic
│   ├── __init__.py
│   ├── ffmpeg_wrapper.py       # FFmpeg/FFprobe operations
│   ├── silence_detector.py     # Silence detection logic
│   ├── video_processor.py      # Video processing logic
│   ├── settings_manager.py     # Settings persistence
│   └── project_manager.py      # Project save/load (.tbproj files)
│
├── ai_analysis/                # AI content analysis
│   ├── __init__.py
│   ├── transcriber.py          # Whisper transcription
│   ├── context_builder.py      # Context extraction
│   ├── ai_analyzer.py          # together.ai integration
│   └── orchestrator.py         # Analysis pipeline
│
├── utils/                      # Utility functions
│   ├── __init__.py
│   ├── colors.py               # Color theme definitions
│   ├── entry_helpers.py        # Entry point helpers
│   ├── helpers.py              # Helper functions
│   ├── logger.py               # Logging configuration
│   ├── validators.py           # Input validation
│   └── waveform.py             # Waveform generator
│
├── bin/                        # Binary executables
│   ├── __init__.py
│   ├── ffmpeg.exe              # FFmpeg executable
│   ├── ffprobe.exe             # FFprobe executable
│   └── ffplay.exe              # FFplay executable
│
└── docs/                       # Documentation
    └── screenshots/            # UI screenshots
        ├── image.png
        ├── image2.png
        └── image3.png
```

---

## Requirements

### Core Dependencies

- **pywebview** >= 4.0.0 - Web UI framework
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

#### For GPU-Accelerated Whisper Transcription

To enable CUDA GPU acceleration for faster transcription:

```bash
# Install PyTorch with CUDA support (Windows/Linux)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# For macOS (MPS acceleration)
pip install torch torchvision torchaudio
```

**Note**: Whisper will automatically use GPU if available. CPU transcription works but is slower.

#### Other Optional Packages

- **python-dotenv** - For `.env` file support (recommended for API key management)
- **opencv-python** - Enhanced frame preview features
- **librosa** + **soundfile** - Advanced audio analysis and waveform visualization

```bash
# Install all optional dependencies
pip install python-dotenv opencv-python librosa soundfile
```

---

## Contributing

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

### Code Style Guidelines

- **Python Style**: Follow PEP 8 conventions
- **Docstrings**: Use comprehensive docstrings for all functions and classes
- **Type Hints**: Include type hints for better code clarity
- **Comments**: Add comments for complex logic
- **Naming**: Use descriptive variable and function names

### Testing Procedures

**Manual Testing Checklist:**

- [ ] Test video loading (drag & drop and file picker)
- [ ] Test silence detection with different thresholds
- [ ] Test AI analysis with at least one model
- [ ] Test project save/load functionality
- [ ] Test video export with GPU and CPU encoders
- [ ] Verify keyboard shortcuts work
- [ ] Check error handling for invalid inputs

**Running Existing Tests:**

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_context_logic.py
```

### Pull Request Checklist

- [ ] Code follows project style guidelines
- [ ] All functions have docstrings
- [ ] Changes have been manually tested
- [ ] No breaking changes (or documented if necessary)
- [ ] Updated README if adding new features
- [ ] Added comments for complex logic
- [ ] Verified no new errors in logs

### Code Structure Guidelines

- **Separation of Concerns**: UI, business logic, and utilities are separated
- **Module Organization**: Each module has a clear responsibility
- **Documentation**: All functions include comprehensive docstrings
- **Type Hints**: Use type hints for better code clarity
- **Error Handling**: Implement proper error handling and user feedback

### Areas for Contribution

- 🐛 Bug fixes and improvements
- ✨ New features and enhancements
- 📚 Documentation improvements
- ⚡ Performance optimizations
- 🎨 UI/UX improvements
- 🧪 Test coverage expansion
- 🌍 Internationalization (i18n)
- 🔌 Plugin system development

---

## Performance Benchmarks

### Recommended System Specifications

| Video Resolution | Minimum RAM | Recommended RAM | GPU VRAM | Storage    |
| ---------------- | ----------- | --------------- | -------- | ---------- |
| 720p (HD)        | 4GB         | 8GB             | 2GB      | 10GB free  |
| 1080p (Full HD)  | 8GB         | 16GB            | 4GB      | 20GB free  |
| 1440p (2K)       | 12GB        | 24GB            | 6GB      | 30GB free  |
| 2160p (4K)       | 16GB        | 32GB            | 8GB+     | 50GB+ free |

### Encoding Performance Comparison

**Test Setup**: 10-minute 1080p video (H.264 source)

| Encoder              | Hardware | Export Time | Quality   | Notes                    |
| -------------------- | -------- | ----------- | --------- | ------------------------ |
| NVIDIA H.264 (NVENC) | RTX 3060 | ~2 min      | Excellent | Fastest, recommended     |
| AMD H.264 (AMF)      | RX 6600  | ~2.5 min    | Excellent | Very fast                |
| Intel H.264 (QSV)    | i7-12700 | ~3 min      | Very Good | Good balance             |
| CPU x264             | i7-12700 | ~15 min     | Excellent | Slowest, highest quality |

### Whisper Transcription Performance

**Test Setup**: 10-minute video, single audio track

| Model  | GPU (RTX 3060) | CPU (i7-12700) | Accuracy  | VRAM Usage |
| ------ | -------------- | -------------- | --------- | ---------- |
| tiny   | ~30 sec        | ~3 min         | Good      | ~1GB       |
| base   | ~45 sec        | ~5 min         | Very Good | ~1GB       |
| small  | ~1.5 min       | ~12 min        | Excellent | ~2GB       |
| medium | ~3 min         | ~30 min        | Excellent | ~5GB       |
| large  | ~6 min         | ~60 min        | Best      | ~10GB      |

**Recommendation**: Use `base` model for best speed/accuracy balance. Upgrade to `small` or `medium` for critical accuracy needs.

### AI Analysis Cost & Speed

**Test Setup**: 10-minute video, 100 segments

| Model         | API Cost   | Processing Time | Cut Rate     | Best For          |
| ------------- | ---------- | --------------- | ------------ | ----------------- |
| Llama 3.1 8B  | $0.01-0.03 | ~2 min          | Variable     | Quick tests       |
| Llama 3.3 70B | $0.05-0.15 | ~5 min          | Low (5%)     | Vlogs, tutorials  |
| Qwen 2.5 72B  | $0.08-0.20 | ~5 min          | Medium (15%) | Corporate content |
| DeepSeek R1   | $0.20-0.50 | ~8 min          | High (75%)   | Viral shorts      |

**Note**: Costs and times vary based on segment length and context window size. Use the in-app cost estimator for accurate predictions.

---

## Troubleshooting

### Common Installation Issues

**Problem**: `ModuleNotFoundError: No module named 'video_production_app'`

- **Solution**: Ensure you're running commands from the project root directory (where `README.md` is located)
- Verify virtual environment is activated if you created one

**Problem**: FFmpeg not found or encoding fails

- **Solution**:
  - Check that `video_production_app/bin/` contains `ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe`
  - Or install FFmpeg system-wide and add to PATH
  - Test with: `ffmpeg -version`

**Problem**: GPU encoder not available (NVIDIA/AMD/Intel)

- **Solution**:
  - Update GPU drivers to latest version
  - Verify GPU supports hardware encoding (NVENC/AMF/Quick Sync)
  - Use "CPU (x264)" encoder as fallback

**Problem**: Whisper transcription is very slow

- **Solution**:
  - Install PyTorch with CUDA support (see Optional Dependencies)
  - Use smaller Whisper model (`tiny` or `base`)
  - Ensure GPU has sufficient VRAM

**Problem**: together.ai API errors or rate limits

- **Solution**:
  - Verify API key is correct and has credits
  - Check internet connection
  - Increase `api_delay_seconds` in settings for rate limit errors
  - Try a different AI model

**Problem**: Application crashes or freezes

- **Solution**:
  - Check `logs/app.log` for error details
  - Ensure video file is not corrupted
  - Try with a smaller/shorter video first
  - Verify sufficient RAM available (8GB+ recommended)

### Performance Issues

**Slow video export:**

- Use GPU encoder instead of CPU
- Lower output quality settings
- Close other applications to free up resources

**High memory usage:**

- Reduce waveform cache size in settings
- Use smaller Whisper model
- Process shorter video segments

### Getting Help

- Check the [GitHub Issues](https://github.com/tooboooring/video_production_by_tooboooring/issues) for known problems
- Review `logs/app.log` for detailed error messages
- Include system info (OS, Python version, GPU) when reporting bugs

---

## FAQ

**Q: What is a .tbproj file?**
A: A TooBoooring Studio project file that saves your editing session, including all segments, settings, AI analysis history, and video metadata. You can resume editing later by opening this file.

**Q: Can I use this application offline?**
A: Partially. Video editing and silence detection work offline. AI analysis requires internet connection for together.ai API. Whisper transcription runs locally.

**Q: How do I clear the cache?**
A: Delete the cache files in your system's temp directory. Transcription cache is stored per video file hash.

**Q: Where are log files stored?**
A: In the `logs/` directory at the project root. Check `logs/app.log` for detailed application logs.

**Q: What's the difference between silence detection and AI analysis?**
A:

- **Silence Detection**: Automatically finds quiet parts based on audio volume (fast, local, free)
- **AI Analysis**: Uses AI to evaluate content quality and decide what to keep/remove (slower, requires API, costs money)

**Q: Which AI model should I choose?**
A:

- **Vlogs/Tutorials**: Llama 3.3 70B (keeps personality)
- **Short-form/Viral**: DeepSeek R1 (aggressive cuts)
- **Corporate/Educational**: Qwen 2.5 72B (balanced)
- **Testing/Budget**: Llama 3.1 8B (fast and cheap)

**Q: Can I export to formats other than MP4?**
A: Yes, the Export tab supports MP4 and MOV containers. You can also export EDL (Edit Decision List) and XML files for use in professional editing software like Premiere Pro or DaVinci Resolve.

**Q: Does this work on macOS/Linux?**
A: Yes! The application is cross-platform. Ensure you have Python 3.8+ and FFmpeg installed. GPU acceleration availability depends on your hardware.

**Q: How much does AI analysis cost?**
A: Costs vary by model and video length. Example: A 10-minute video (~100 segments) with Llama 3.3 70B costs approximately $0.05-0.15. Use the cost estimator in the UI before running analysis.

---

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

Copyright 2024 Shankargouda Hanchinal

---

## Upcoming Features

### Planned Enhancements

#### AI Analysis

- [ ] **Custom Prompt Templates**: User-defined AI analysis prompts with template editor
- [ ] **Persistent History**: Save analysis history to disk (currently session-only)
- [ ] **Model Comparison**: Side-by-side comparison of different model results
- [ ] **Ensemble Analysis**: Combine decisions from multiple AI models for better accuracy
- [ ] **Local LLM Support**: Run AI analysis with local models (Ollama, LM Studio)

#### Video Processing

- [ ] **Batch Processing**: Process multiple videos in a queue with progress tracking
- [ ] **Subtitle Support**: Import, edit, and export SRT/VTT subtitle files
- [ ] **Multi-format Export**: Support for WebM, AV1, ProRes codecs
- [ ] **Scene Detection**: Automatic scene change detection for better cuts
- [ ] **Audio Normalization**: Automatic audio level adjustment

#### User Interface

- [ ] **Light Theme**: Optional light theme for daytime use
- [ ] **Customizable Layout**: Resizable and rearrangeable UI panels
- [ ] **Undo/Redo System**: Full undo/redo functionality for edits
- [ ] **Waveform Themes**: Customizable waveform colors and styles
- [ ] **Minimap**: Timeline minimap for long videos

#### Performance & Optimization

- [ ] **GPU Acceleration for Whisper**: Optimized CUDA support for faster transcription
- [ ] **Parallel Processing**: Process multiple videos simultaneously
- [ ] **Progress Resume**: Resume interrupted processing tasks
- [ ] **Smart Caching**: Intelligent cache management for better performance
- [ ] **Proxy Editing**: Work with lower-resolution proxies for smoother editing
- [ ] **Progress Resume**: Resume interrupted processing tasks

---

**Made with love by the Tooboooring (Shankargouda Hanchinal)**

For questions, issues, or contributions, please visit the [GitHub repository](https://github.com/tooboooring/video_production_by_tooboooring).

---

## WARNING

**VIBE-CODED WARNING**: This codebase was developed with a focus on rapid iteration and functionality over strict code conventions. While the application is functional and tested, the code may contain:

- Inconsistent coding styles and patterns
- Experimental implementations that may need refactoring
- Code that works but may not follow all best practices
- Areas that could benefit from optimization or cleanup

**Use at your own discretion**. This is a working application, but contributors should be aware that some parts of the codebase may require additional polish and standardization. When contributing, please maintain consistency with the existing code style in each module.

**For Production Use**: While functional, this software is provided as-is. Always backup your work and test thoroughly before using in production environments.
