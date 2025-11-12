#!/usr/bin/env python3
"""
Standalone entry point for Web UI (PyWebView-based).

This file allows you to launch the Web UI directly without using the launcher.
Simply run: python -m video_production_app.entry_points.web_ui

The Web UI provides a modern, browser-based interface for video silence cutting.
"""

import sys
from pathlib import Path

def main():
    """Launch the Web UI."""
    print("🌐 Launching Web UI...")
    print("=" * 50)
    
    try:
        # Add project root to path (go up one level: video_production_app -> root)
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        # Import and run the web UI
        from video_production_app.web.web_main import main as web_main
        web_main()
        
    except ImportError as e:
        print(f"❌ Error: Could not import Web UI dependencies.")
        print(f"   Make sure PyWebView is installed: pip install pywebview")
        print(f"   Error details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error launching Web UI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

