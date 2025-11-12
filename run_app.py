#!/usr/bin/env python3
"""
Quick launcher script for Video Production Suite.

Place this file in the project root and run: python run_app.py

This script provides an easy way to launch the application.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def main():
    """Launch the application launcher."""
    try:
        from video_production_app.launcher import show_launcher_menu
        show_launcher_menu()
    except ImportError as e:
        print(f"❌ Error: Could not import launcher.")
        print(f"   Make sure you're running from the project root directory.")
        print(f"   Error details: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error launching application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

