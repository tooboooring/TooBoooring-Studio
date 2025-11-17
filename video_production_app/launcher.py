#!/usr/bin/env python3
"""
Main launcher for Video Production Suite.

Allows user to choose between Web UI (PyWebView) and Tkinter UI via:
- Interactive menu (default)
- Command-line arguments: python -m video_production_app.launcher [web|tkinter]
"""

import sys
from pathlib import Path

# Set up path before relative imports
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from video_production_app.utils.entry_helpers import setup_project_path
from video_production_app.main_tkinter import launch as launch_tkinter
from video_production_app.main_web_ui import launch as launch_web


def show_launcher_menu():
    """Show interactive menu to choose UI."""
    print("\n" + "=" * 50)
    print("  🎬 Video Production Suite - Launcher")
    print("=" * 50)
    print("\nChoose your UI:")
    print("  1. Web UI (Modern, PyWebView-based)")
    print("  2. Tkinter UI (Classic, CustomTkinter-based)")
    print("  3. Exit")
    print("\n💡 Tip: You can also run directly:")
    print("   - python -m video_production_app.main_web_ui (for Web UI)")
    print("   - python -m video_production_app.main_tkinter (for Tkinter UI)")
    print()
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        launch_web()
    elif choice == "2":
        launch_tkinter()
    elif choice == "3":
        print("Goodbye!")
        sys.exit(0)
    else:
        print("❌ Invalid choice. Please try again.")
        show_launcher_menu()


def main():
    """Main entry point for launcher."""
    # Set up project path
    setup_project_path()
    
    # Check for command-line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ["web", "--web", "-w"]:
            launch_web()
        elif arg in ["tk", "tkinter", "--tkinter", "-t"]:
            launch_tkinter()
        else:
            print(f"Unknown argument: {arg}")
            print("Usage: python -m video_production_app.launcher [web|tkinter]")
            sys.exit(1)
    else:
        # Show interactive menu
        show_launcher_menu()


if __name__ == "__main__":
    main()

