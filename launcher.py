#!/usr/bin/env python3
"""
Launcher for Video Production Suite
Allows user to choose between Web UI (PyWebView) and Tkinter UI
"""

import sys
import os
from pathlib import Path

def launch_web_ui():
    """Launch the web-based UI using PyWebView."""
    print("🌐 Launching Web UI...")
    try:
        # Import and run the web UI
        sys.path.insert(0, str(Path(__file__).parent))
        from video_production_app.web_main import main
        main()
    except ImportError as e:
        print(f"❌ Error: Could not import web UI. Make sure PyWebView is installed.")
        print(f"   Install with: pip install pywebview")
        print(f"   Error details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error launching Web UI: {e}")
        sys.exit(1)

def launch_tkinter_ui():
    """Launch the Tkinter-based UI."""
    print("🖥️  Launching Tkinter UI...")
    try:
        # Import and run the Tkinter UI
        sys.path.insert(0, str(Path(__file__).parent))
        from video_production_app.ui.app import VideoProductionApp
        app = VideoProductionApp()
        app.mainloop()
    except ImportError as e:
        print(f"❌ Error: Could not import Tkinter UI. Make sure CustomTkinter is installed.")
        print(f"   Install with: pip install customtkinter")
        print(f"   Error details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error launching Tkinter UI: {e}")
        sys.exit(1)

def show_launcher_menu():
    """Show a simple menu to choose UI."""
    print("\n" + "="*50)
    print("  🎬 Video Production Suite - Launcher")
    print("="*50)
    print("\nChoose your UI:")
    print("  1. Web UI (Modern, PyWebView-based)")
    print("  2. Tkinter UI (Classic, CustomTkinter-based)")
    print("  3. Exit")
    print()
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        launch_web_ui()
    elif choice == "2":
        launch_tkinter_ui()
    elif choice == "3":
        print("Goodbye!")
        sys.exit(0)
    else:
        print("❌ Invalid choice. Please try again.")
        show_launcher_menu()

if __name__ == "__main__":
    # Check for command-line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ["web", "--web", "-w"]:
            launch_web_ui()
        elif arg in ["tk", "tkinter", "--tkinter", "-t"]:
            launch_tkinter_ui()
        else:
            print(f"Unknown argument: {arg}")
            print("Usage: python launcher.py [web|tkinter]")
            sys.exit(1)
    else:
        # Show interactive menu
        show_launcher_menu()

