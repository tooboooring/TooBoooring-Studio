"""
Project Manager for TooBoooring Studio.

Handles saving and loading project files (.tbproj) including:
- Video metadata
- Segments and silence detection results
- AI analysis history
- Timeline state and settings
- Project versioning

Project files are JSON-based for portability and easy debugging.
"""

import json
import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import traceback


class ProjectManagerError(Exception):
    """Custom exception for project management errors."""
    pass


class ProjectManager:
    """
    Manages project save/load operations for video editing projects.
    
    Project Structure:
        {
            "project_version": "1.0",
            "created": "2025-11-30T12:00:00Z",
            "modified": "2025-11-30T14:30:00Z",
            "video": {
                "filename": "video.mp4",
                "file_path": "/path/to/video.mp4",
                "file_size": 12345678,
                "duration": 120.5,
                "file_hash": "md5_hash"  # For validation
            },
            "audio_tracks": [...],
            "segments": [...],
            "ai_analysis_history": [...],
            "settings": {...},
            "timeline_state": {
                "zoom_level": 1.0,
                "scroll_position": 0,
                "selected_segments": []
            },
            "metadata": {
                "app_version": "1.0.0",
                "last_save_user": "username"
            }
        }
    """
    
    PROJECT_VERSION = "1.0"
    PROJECT_EXTENSION = ".tbproj"
    
    def __init__(self, ffprobe_path: str = ""):
        """
        Initialize ProjectManager.
        
        Args:
            ffprobe_path: Path to ffprobe executable (empty for system PATH)
        """
        self.ffprobe_path = ffprobe_path
    
    def get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a video file.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary containing:
            - filename: Name of the file
            - file_path: Absolute path to the file
            - file_size: Size in bytes
            - duration: Duration in seconds
            - file_hash: MD5 hash for validation (first 1MB only for performance)
            - exists: Whether the file exists
            
        Raises:
            ProjectManagerError: If video file doesn't exist or is invalid
        """
        video_file = Path(video_path)
        
        # Check if file exists
        if not video_file.exists():
            raise ProjectManagerError(f"Video file not found: {video_path}")
        
        if not video_file.is_file():
            raise ProjectManagerError(f"Path is not a file: {video_path}")
        
        # Get basic file info
        file_size = video_file.stat().st_size
        
        # Calculate partial file hash (first 1MB for performance)
        try:
            file_hash = self._calculate_file_hash(video_path, max_bytes=1024*1024)
        except Exception as e:
            # Hash calculation failed, but don't block the operation
            file_hash = None
        
        # Get video duration using FFprobe
        try:
            from .ffmpeg_wrapper import get_video_duration
            duration = get_video_duration(video_path, self.ffprobe_path)
        except Exception as e:
            raise ProjectManagerError(f"Failed to get video duration: {str(e)}")
        
        return {
            "filename": video_file.name,
            "file_path": str(video_file.absolute()),
            "file_size": file_size,
            "duration": duration,
            "file_hash": file_hash,
            "exists": True
        }
    
    def _calculate_file_hash(self, filepath: str, max_bytes: int = 1024*1024) -> str:
        """
        Calculate MD5 hash of a file (partial for performance).
        
        Args:
            filepath: Path to file
            max_bytes: Maximum bytes to read (default 1MB)
            
        Returns:
            MD5 hash as hex string
        """
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            chunk = f.read(max_bytes)
            hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def create_project_data(
        self,
        video_metadata: Dict[str, Any],
        audio_tracks: Optional[List[Dict[str, Any]]] = None,
        segments: Optional[List[Dict[str, Any]]] = None,
        ai_analysis_history: Optional[List[Dict[str, Any]]] = None,
        settings: Optional[Dict[str, Any]] = None,
        timeline_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a project data dictionary ready for saving.
        
        Args:
            video_metadata: Video file metadata from get_video_metadata()
            audio_tracks: List of audio track information
            segments: List of video segments (silence detection results)
            ai_analysis_history: List of AI analysis runs
            settings: Application settings
            timeline_state: Timeline UI state (zoom, scroll, etc.)
            
        Returns:
            Complete project data dictionary
        """
        now = datetime.utcnow().isoformat() + "Z"
        
        project_data = {
            "project_version": self.PROJECT_VERSION,
            "created": now,
            "modified": now,
            "video": video_metadata,
            "audio_tracks": audio_tracks or [],
            "segments": segments or [],
            "ai_analysis_history": ai_analysis_history or [],
            "settings": settings or {},
            "timeline_state": timeline_state or {
                "zoom_level": 1.0,
                "scroll_position": 0,
                "selected_segments": []
            },
            "metadata": {
                "app_version": "1.0.0",
                "last_save_user": os.getenv("USERNAME", os.getenv("USER", "unknown"))
            }
        }
        
        return project_data
    
    def save_project_file(self, data: Dict[str, Any], filepath: str) -> Dict[str, Any]:
        """
        Save project data to a .tbproj file.
        
        Args:
            data: Project data dictionary (should match project structure)
            filepath: Target filepath (will add .tbproj if not present)
            
        Returns:
            Dictionary with:
            - success: bool
            - filepath: str (actual saved path)
            - message: str
            
        Raises:
            ProjectManagerError: If save operation fails
        """
        # Ensure .tbproj extension
        filepath = Path(filepath)
        if filepath.suffix != self.PROJECT_EXTENSION:
            filepath = filepath.with_suffix(self.PROJECT_EXTENSION)
        
        # Validate data structure
        if not isinstance(data, dict):
            raise ProjectManagerError("Project data must be a dictionary")
        
        # Update modified timestamp
        if "modified" in data:
            data["modified"] = datetime.utcnow().isoformat() + "Z"
        
        # Create parent directory if it doesn't exist
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ProjectManagerError(f"Failed to create directory: {str(e)}")
        
        # Write JSON file with pretty formatting
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except PermissionError:
            raise ProjectManagerError(f"Permission denied: Cannot write to {filepath}")
        except Exception as e:
            raise ProjectManagerError(f"Failed to write project file: {str(e)}")
        
        return {
            "success": True,
            "filepath": str(filepath.absolute()),
            "message": f"Project saved successfully to {filepath.name}"
        }
    
    def load_project_file(self, filepath: str) -> Dict[str, Any]:
        """
        Load project data from a .tbproj file.
        
        Args:
            filepath: Path to .tbproj file
            
        Returns:
            Project data dictionary
            
        Raises:
            ProjectManagerError: If file doesn't exist, is corrupted, or read fails
        """
        # Safety check for None or empty filepath
        if not filepath:
            raise ProjectManagerError("No file path provided")
        
        if not isinstance(filepath, str):
            raise ProjectManagerError(f"Invalid filepath type: {type(filepath)}")
        
        filepath = Path(filepath)
        
        # Check if file exists
        if not filepath.exists():
            raise ProjectManagerError(f"Project file not found: {filepath}")
        
        if not filepath.is_file():
            raise ProjectManagerError(f"Path is not a file: {filepath}")
        
        # Check extension
        if filepath.suffix != self.PROJECT_EXTENSION:
            raise ProjectManagerError(
                f"Invalid file extension. Expected {self.PROJECT_EXTENSION}, "
                f"got {filepath.suffix}"
            )
        
        # Read and parse JSON
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except PermissionError:
            raise ProjectManagerError(f"Permission denied: Cannot read {filepath}")
        except json.JSONDecodeError as e:
            raise ProjectManagerError(
                f"Corrupt project file: Invalid JSON at line {e.lineno}, column {e.colno}"
            )
        except Exception as e:
            raise ProjectManagerError(f"Failed to read project file: {str(e)}")
        
        # Validate project structure
        if not isinstance(data, dict):
            raise ProjectManagerError("Invalid project file: Root must be a dictionary")
        
        if "project_version" not in data:
            raise ProjectManagerError("Invalid project file: Missing project_version")
        
        # Version compatibility check
        if data.get("project_version") != self.PROJECT_VERSION:
            # In the future, handle version migration here
            pass
        
        # Validate video reference
        if "video" not in data:
            raise ProjectManagerError("Invalid project file: Missing video metadata")
        
        # Check if referenced video file exists
        video_path = data["video"].get("file_path")
        if video_path and not Path(video_path).exists():
            # Video moved or deleted - return data but add warning
            data["video"]["exists"] = False
            data["warnings"] = data.get("warnings", [])
            data["warnings"].append(f"Video file not found: {video_path}")
        else:
            data["video"]["exists"] = True
        
        return data
    
    def validate_project_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate project data structure and return validation results.
        
        Args:
            data: Project data dictionary
            
        Returns:
            Dictionary with:
            - valid: bool
            - errors: List[str]
            - warnings: List[str]
        """
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ["project_version", "video"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Video metadata validation
        if "video" in data:
            video = data["video"]
            if video is None:
                warnings.append("Video metadata is empty")
            elif isinstance(video, dict):
                required_video_fields = ["filename", "file_path", "duration"]
                for field in required_video_fields:
                    if field not in video or video[field] is None:
                        warnings.append(f"Missing or empty video field: {field}")
                
                # Check if video file exists (only if file_path is a valid string)
                file_path = video.get("file_path")
                if file_path and isinstance(file_path, str) and file_path.strip():
                    if not Path(file_path).exists():
                        warnings.append(f"Video file not found: {file_path}")
                        # Mark as not existing for frontend to handle
                        video["exists"] = False
                    else:
                        video["exists"] = True
                else:
                    warnings.append("Video file path is missing or invalid")
                    video["exists"] = False
        
        # Segments validation
        if "segments" in data and data["segments"]:
            if not isinstance(data["segments"], list):
                errors.append("Segments must be a list")
        
        # AI analysis validation
        if "ai_analysis_history" in data and data["ai_analysis_history"]:
            if not isinstance(data["ai_analysis_history"], list):
                errors.append("AI analysis history must be a list")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_recent_projects(self, projects_dir: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get list of recent project files from a directory.
        
        Args:
            projects_dir: Directory to scan for .tbproj files
            limit: Maximum number of projects to return
            
        Returns:
            List of project info dictionaries, sorted by modification time (newest first)
        """
        projects_dir = Path(projects_dir)
        
        if not projects_dir.exists():
            return []
        
        # Find all .tbproj files
        project_files = list(projects_dir.glob(f"**/*{self.PROJECT_EXTENSION}"))
        
        # Get info for each project
        projects = []
        for filepath in project_files:
            try:
                stat = filepath.stat()
                
                # Try to load basic info without full parsing
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                projects.append({
                    "filepath": str(filepath.absolute()),
                    "filename": filepath.name,
                    "modified": data.get("modified", datetime.fromtimestamp(stat.st_mtime).isoformat()),
                    "created": data.get("created", ""),
                    "video_filename": data.get("video", {}).get("filename", "Unknown"),
                    "file_size": stat.st_size
                })
            except Exception:
                # Skip corrupted or inaccessible files
                continue
        
        # Sort by modified time (newest first)
        projects.sort(key=lambda x: x["modified"], reverse=True)
        
        return projects[:limit]
    
    def auto_save_filename(self, video_path: str, suffix: str = "autosave") -> str:
        """
        Generate an auto-save filename based on video filename.
        
        Args:
            video_path: Path to video file
            suffix: Suffix to add to filename (default: "autosave")
            
        Returns:
            Suggested filename (e.g., "video_autosave.tbproj")
        """
        video_file = Path(video_path)
        # Use video filename with suffix, no timestamp (overwrites same file each time)
        return f"{video_file.stem}_{suffix}{self.PROJECT_EXTENSION}"
    
    def export_project_summary(self, data: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of project data.
        
        Args:
            data: Project data dictionary
            
        Returns:
            Formatted string with project summary
        """
        lines = []
        lines.append("=" * 60)
        lines.append("TooBoooring Studio Project Summary")
        lines.append("=" * 60)
        
        # Project info
        lines.append(f"\nProject Version: {data.get('project_version', 'Unknown')}")
        lines.append(f"Created: {data.get('created', 'Unknown')}")
        lines.append(f"Modified: {data.get('modified', 'Unknown')}")
        
        # Video info
        if "video" in data:
            video = data["video"]
            lines.append(f"\nVideo: {video.get('filename', 'Unknown')}")
            lines.append(f"Duration: {video.get('duration', 0):.2f}s")
            lines.append(f"File Size: {video.get('file_size', 0) / 1024 / 1024:.2f} MB")
        
        # Segments info
        if "segments" in data:
            segments = data["segments"]
            lines.append(f"\nSegments: {len(segments)} total")
            audible = sum(1 for s in segments if s.get("type") == "audible")
            silent = sum(1 for s in segments if s.get("type") == "silence")
            lines.append(f"  - Audible: {audible}")
            lines.append(f"  - Silent: {silent}")
        
        # AI analysis info
        if "ai_analysis_history" in data:
            history = data["ai_analysis_history"]
            lines.append(f"\nAI Analysis Runs: {len(history)}")
            for i, run in enumerate(history, 1):
                lines.append(f"  {i}. Model: {run.get('model', 'Unknown')}")
                lines.append(f"     Date: {run.get('timestamp', 'Unknown')}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)


# Convenience functions for quick access
def get_video_metadata(video_path: str, ffprobe_path: str = "") -> Dict[str, Any]:
    """
    Quick function to get video metadata.
    
    Args:
        video_path: Path to video file
        ffprobe_path: Path to ffprobe executable
        
    Returns:
        Video metadata dictionary
    """
    manager = ProjectManager(ffprobe_path=ffprobe_path)
    return manager.get_video_metadata(video_path)


def save_project_file(data: Dict[str, Any], filepath: str) -> Dict[str, Any]:
    """
    Quick function to save project file.
    
    Args:
        data: Project data dictionary
        filepath: Target filepath
        
    Returns:
        Save result dictionary
    """
    manager = ProjectManager()
    return manager.save_project_file(data, filepath)


def load_project_file(filepath: str) -> Dict[str, Any]:
    """
    Quick function to load project file.
    
    Args:
        filepath: Path to .tbproj file
        
    Returns:
        Project data dictionary
    """
    manager = ProjectManager()
    return manager.load_project_file(filepath)

