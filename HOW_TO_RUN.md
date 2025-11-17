# 🚀 How to Run Video Production Suite

## Quick Start (Easiest Way)

### Option 1: Use the Quick Launcher Scripts (Recommended)

Place these files in the project root and run them:

```bash
# Interactive menu (choose Web UI or Tkinter UI)
python run_app.py

# Launch Web UI directly
python run_web_ui.py

# Launch Tkinter UI directly
python run_tkinter_ui.py
```

## Method 2: Using Python Module Syntax

### From Project Root Directory

Make sure you're in the project root directory (`d:\silance cutter`), then:

```bash
# Interactive launcher menu
python -m video_production_app.launcher

# Web UI directly
python -m video_production_app.entry_points.web_ui

# Tkinter UI directly
python -m video_production_app.entry_points.tkinter_ui
```

### With Command Line Arguments

```bash
# Launch Web UI via launcher
python -m video_production_app.launcher web

# Launch Tkinter UI via launcher
python -m video_production_app.launcher tkinter
```

## Method 3: Direct Python Execution

If you're in the project root:

```bash
# Web UI
python -m video_production_app.entry_points.web_ui

# Tkinter UI
python -m video_production_app.entry_points.tkinter_ui
```

## Troubleshooting

### Error: "No module named 'video_production_app'"

**Solution:** Make sure you're running from the project root directory (`d:\silance cutter`)

```bash
cd "d:\silance cutter"
python run_app.py
```

### Error: "Could not import web UI dependencies"

**Solution:** Install required packages:

```bash
pip install pywebview
pip install customtkinter
pip install numpy
```

### Error: "FFmpeg not found"

**Solution:** FFmpeg executables should be in `video_production_app/bin/` folder. If missing:
1. Download FFmpeg for Windows
2. Extract `ffmpeg.exe`, `ffprobe.exe`, and `ffplay.exe`
3. Place them in `video_production_app/bin/` folder

### Check Your Current Directory

```bash
# Windows PowerShell
pwd

# Windows CMD
cd

# Should show: d:\silance cutter
```

## Project Structure

```
d:\silance cutter\              ← You should be here
├── run_app.py                  ← Quick launcher (easiest)
├── run_web_ui.py              ← Quick Web UI launcher
├── run_tkinter_ui.py           ← Quick Tkinter UI launcher
└── video_production_app\       ← Main package
    ├── entry_points\          ← Entry points
    ├── launcher\              ← Launcher module
    ├── web\                   ← Web UI
    ├── ui\                    ← Tkinter UI
    └── ...
```

## Recommended Workflow

1. **First Time Setup:**
   ```bash
   cd "d:\silance cutter"
   pip install pywebview customtkinter numpy
   ```

2. **Daily Use:**
   ```bash
   cd "d:\silance cutter"
   python run_app.py
   ```

That's it! The interactive menu will let you choose which UI to use.

