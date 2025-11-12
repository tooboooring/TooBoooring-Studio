"""
Main entry point for Video Production Suite.

This file redirects to the launcher for backward compatibility.
For direct access, use:
- python launcher.py (interactive menu)
- python web_ui.py (Web UI directly)
- python tkinter_ui.py (Tkinter UI directly)
- python launcher.py web (web UI via launcher)
- python launcher.py tkinter (Tkinter UI via launcher)
"""

import sys
from pathlib import Path

# Redirect to launcher
if __name__ == '__main__':
    launcher_path = Path(__file__).parent / 'launcher' / 'launcher.py'
    if launcher_path.exists():
        print("📋 Redirecting to launcher...")
        print("   For direct access, use:")
        print("   - python -m video_production_app.entry_points.web_ui (Web UI)")
        print("   - python -m video_production_app.entry_points.tkinter_ui (Tkinter UI)")
        print("   - python -m video_production_app.launcher (Interactive menu)")
        print()
        # Import and run launcher
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from video_production_app.launcher import show_launcher_menu
        show_launcher_menu()
    else:
        print("❌ Error: launcher not found!")
        print("   Please run: python -m video_production_app.launcher")
        print("   Or use: python -m video_production_app.entry_points.web_ui or python -m video_production_app.entry_points.tkinter_ui")
        sys.exit(1)
