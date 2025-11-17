#!/usr/bin/env python3
"""
Direct launcher for Web UI (PyWebView-based).

Run: python -m video_production_app.main_web_ui

The Web UI provides a modern, browser-based interface for video silence cutting.
"""

import sys
from pathlib import Path

# Set up path before relative imports
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from video_production_app.utils.entry_helpers import setup_project_path, handle_launch_error


def launch():
    """Launch the Web UI."""
    print("🌐 Launching Web UI...")
    print("=" * 50)
    
    # Set up project path
    setup_project_path()
    
    try:
        from video_production_app.web.web_main import main as web_main
        
        web_main()
    except ImportError as e:
        handle_launch_error(e, "Web", "PyWebView", "pip install pywebview")
    except Exception as e:
        handle_launch_error(e, "Web", "PyWebView", "pip install pywebview")


def main():
    """Main entry point."""
    launch()


if __name__ == "__main__":
    main()

