"""
Settings management for Video Production App.

This module handles loading, saving, and managing user settings and preferences.
It maintains backward compatibility with existing settings files while providing
a clean interface for accessing configuration data.

The SettingsManager class handles:
- Loading settings from JSON file
- Saving settings to JSON file
- Providing default values for missing settings
- Maintaining backward compatibility with existing installations

Settings are stored in a JSON file for easy editing and portability.
"""

import json
from pathlib import Path
from typing import Any, Optional

from ..config import DEFAULT_SETTINGS, SETTINGS_FILE_NAME


class SettingsManager:
    """
    Manages user settings with JSON persistence and backward compatibility.
    
    This class handles all user preferences and settings for the application.
    It automatically loads settings from a JSON file when created and saves
    them whenever changes are made.
    
    Key features:
    - Automatic loading/saving of settings
    - Default values for missing settings
    - Error handling for corrupted files
    - Backward compatibility with existing settings
    
    Attributes:
        config_file: Path to the settings JSON file
        settings: Dictionary containing all current settings
        
    Example usage:
        # Create settings manager (loads from file automatically)
        settings = SettingsManager()
        
        # Get a setting value
        silence_db = settings.get("silence_db")  # Returns -40 (default)
        
        # Set a new value (automatically saves to file)
        settings.set("silence_db", -35)
        
        # Get with custom default
        custom_value = settings.get("new_setting", "default_value")
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the settings manager.
        
        This constructor sets up the settings manager and loads existing
        settings from the JSON file. If no file exists, it creates one
        with default values.
        
        Args:
            config_file: Optional custom path to settings file.
                        If None, uses the default filename from config.
                        
        Example:
            # Use default settings file
            settings = SettingsManager()
            
            # Use custom settings file
            settings = SettingsManager("my_custom_settings.json")
        """
        # Use provided filename or default from config
        self.config_file = Path(config_file) if config_file else Path(SETTINGS_FILE_NAME)
        
        # Start with default settings
        self.settings = DEFAULT_SETTINGS.copy()
        
        # Load any existing settings from file
        self.load_settings()
    
    def load_settings(self) -> None:
        """
        Load settings from JSON file.
        
        This method reads the settings file and updates the current settings
        with any values found in the file. If the file doesn't exist or is
        corrupted, it silently continues with default values.
        
        The method is safe to call multiple times - it will re-read the file
        and update settings accordingly.
        
        Example:
            settings = SettingsManager()
            # Settings are automatically loaded in __init__
            
            # Manually reload settings (useful if file was modified externally)
            settings.load_settings()
        """
        # Check if settings file exists
        if not self.config_file.exists():
            # File doesn't exist - that's okay, we'll use defaults
            return
        
        try:
            # Try to read and parse the JSON file
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                
            # Update our settings with loaded values
            # This preserves any default values that aren't in the file
            self.settings.update(loaded_settings)
            
        except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
            # File exists but is corrupted or unreadable
            # Silently continue with defaults - don't crash the app
            # In a production app, you might want to log this error
            pass
    
    def save_settings(self) -> None:
        """
        Save current settings to JSON file.
        
        This method writes all current settings to the JSON file in a
        human-readable format with proper indentation. If saving fails
        (e.g., due to permissions), it silently continues without crashing.
        
        The method is automatically called whenever settings are changed
        via the set() method.
        
        Example:
            settings = SettingsManager()
            settings.set("silence_db", -35)  # Automatically calls save_settings()
            
            # Manually save settings
            settings.save_settings()
        """
        try:
            # Create directory if it doesn't exist
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write settings to file with nice formatting
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
                
        except IOError as e:
            # Couldn't save settings (permissions, disk full, etc.)
            # Silently continue - don't crash the app
            # In a production app, you might want to show a warning to the user
            pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        This method retrieves a setting value by its key. If the key doesn't
        exist, it returns the provided default value.
        
        Args:
            key: The setting key to retrieve
            default: Value to return if key doesn't exist
            
        Returns:
            The setting value or default if key not found
            
        Example:
            settings = SettingsManager()
            
            # Get existing setting
            silence_db = settings.get("silence_db")  # Returns -40
            
            # Get setting with custom default
            new_setting = settings.get("new_setting", "default_value")
            
            # Get setting that doesn't exist (returns None)
            missing = settings.get("nonexistent")
        """
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a setting value and save to file.
        
        This method updates a setting value and automatically saves the
        changes to the JSON file. This ensures settings persist between
        application runs.
        
        Args:
            key: The setting key to update
            value: The new value to store
            
        Example:
            settings = SettingsManager()
            
            # Set a new value (automatically saves to file)
            settings.set("silence_db", -35)
            
            # Set multiple values
            settings.set("silence_duration", 1.0)
            settings.set("pad_before", 0.2)
        """
        # Update the setting
        self.settings[key] = value
        
        # Automatically save to file
        self.save_settings()
    
    def reset_to_defaults(self) -> None:
        """
        Reset all settings to their default values.
        
        This method clears all current settings and replaces them with
        the default values from the configuration. Useful for troubleshooting
        or when users want to start fresh.
        
        Example:
            settings = SettingsManager()
            
            # User has messed up their settings
            settings.reset_to_defaults()  # Back to defaults
        """
        # Replace current settings with defaults
        self.settings = DEFAULT_SETTINGS.copy()
        
        # Save the reset settings
        self.save_settings()
    
    def get_all_settings(self) -> dict:
        """
        Get a copy of all current settings.
        
        This method returns a copy of all settings, useful for debugging
        or when you need to see all current values.
        
        Returns:
            Dictionary copy of all settings
            
        Example:
            settings = SettingsManager()
            all_settings = settings.get_all_settings()
            print(f"Current settings: {all_settings}")
        """
        return self.settings.copy()
    
    def update_settings(self, new_settings: dict) -> None:
        """
        Update multiple settings at once.
        
        This method allows updating multiple settings in one operation,
        which is more efficient than calling set() multiple times.
        
        Args:
            new_settings: Dictionary of key-value pairs to update
            
        Example:
            settings = SettingsManager()
            
            # Update multiple settings at once
            settings.update_settings({
                "silence_db": -35,
                "silence_duration": 1.0,
                "pad_before": 0.2
            })
        """
        # Update all settings
        self.settings.update(new_settings)
        
        # Save once at the end (more efficient than saving after each set)
        self.save_settings()
