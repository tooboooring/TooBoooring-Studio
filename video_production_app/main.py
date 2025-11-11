"""
Main entry point for Video Production Suite.

This file now redirects to the launcher.
For direct access, use:
- python launcher.py (interactive menu)
- python launcher.py web (web UI)
- python launcher.py tkinter (Tkinter UI)
"""

import sys
from pathlib import Path

# Redirect to launcher
if __name__ == '__main__':
    launcher_path = Path(__file__).parent.parent / 'launcher.py'
    if launcher_path.exists():
        print("📋 Redirecting to launcher...")
        print("   For future launches, use: python launcher.py")
        print()
        # Import and run launcher
        sys.path.insert(0, str(launcher_path.parent))
        from launcher import show_launcher_menu
        show_launcher_menu()
    else:
        print("❌ Error: launcher.py not found!")
        print("   Please run: python launcher.py")
        sys.exit(1)
