#!/usr/bin/env python3
"""
Main launcher for Video Production Suite.

Launches the Web UI (PyWebView-based) - the only supported interface.

Run: python -m video_production_app.launcher.launcher
Or directly: python -m video_production_app.web.launcher
"""

import sys
from pathlib import Path

# Set up path before relative imports
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from video_production_app.utils.entry_helpers import setup_project_path
from video_production_app.web.launcher import launch as launch_web


def main():
    """Main entry point - launches Web UI."""
    print("\n" + "=" * 50)
    print("  🎬 Video Production Suite")
    print("=" * 50)
    print("🌐 Launching Web UI...\n")
    
    # Set up project path
    setup_project_path()
    
    # Launch Web UI
    launch_web()


if __name__ == "__main__":
    main()

