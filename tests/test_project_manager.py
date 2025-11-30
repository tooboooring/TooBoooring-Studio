"""
Test suite for Project Save/Load functionality.

Run with: python -m pytest tests/test_project_manager.py
"""

import pytest
import json
import tempfile
from pathlib import Path
from video_production_app.core.project_manager import (
    ProjectManager,
    ProjectManagerError,
    get_video_metadata,
    save_project_file,
    load_project_file
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_video_path(temp_dir):
    """Create a mock video file for testing."""
    video_file = temp_dir / "test_video.mp4"
    # Create a small fake video file
    video_file.write_bytes(b"FAKE_VIDEO_DATA" * 1000)
    return str(video_file)


@pytest.fixture
def project_manager():
    """Create a ProjectManager instance."""
    return ProjectManager()


@pytest.fixture
def sample_project_data():
    """Create sample project data for testing."""
    return {
        "project_version": "1.0",
        "created": "2025-11-30T12:00:00Z",
        "modified": "2025-11-30T12:00:00Z",
        "video": {
            "filename": "test_video.mp4",
            "file_path": "/path/to/test_video.mp4",
            "file_size": 1000000,
            "duration": 120.5,
            "file_hash": "abc123",
            "exists": True
        },
        "audio_tracks": [
            {"index": 0, "codec": "aac", "channels": "stereo"}
        ],
        "segments": [
            {"start": 0.0, "end": 10.5, "type": "audible", "action": "keep"},
            {"start": 10.5, "end": 12.0, "type": "silence", "action": "remove"}
        ],
        "ai_analysis_history": [
            {
                "model": "Llama 3.3 70B",
                "timestamp": "2025-11-30T12:30:00Z",
                "segments_analyzed": 50
            }
        ],
        "settings": {
            "silence_db": -40,
            "silence_duration": 0.7
        },
        "timeline_state": {
            "zoom_level": 1.0,
            "scroll_position": 0
        },
        "metadata": {
            "app_version": "1.0.0",
            "last_save_user": "testuser"
        }
    }


class TestProjectManager:
    """Test ProjectManager class functionality."""
    
    def test_initialization(self, project_manager):
        """Test ProjectManager initializes correctly."""
        assert project_manager is not None
        assert project_manager.PROJECT_VERSION == "1.0"
        assert project_manager.PROJECT_EXTENSION == ".tbproj"
    
    def test_save_project_file(self, project_manager, sample_project_data, temp_dir):
        """Test saving a project file."""
        filepath = temp_dir / "test_project.tbproj"
        
        result = project_manager.save_project_file(sample_project_data, str(filepath))
        
        assert result["success"] is True
        assert filepath.exists()
        assert filepath.suffix == ".tbproj"
    
    def test_save_adds_extension(self, project_manager, sample_project_data, temp_dir):
        """Test that .tbproj extension is added if missing."""
        filepath = temp_dir / "test_project"  # No extension
        
        result = project_manager.save_project_file(sample_project_data, str(filepath))
        
        saved_path = Path(result["filepath"])
        assert saved_path.suffix == ".tbproj"
    
    def test_load_project_file(self, project_manager, sample_project_data, temp_dir):
        """Test loading a project file."""
        filepath = temp_dir / "test_project.tbproj"
        
        # Save first
        project_manager.save_project_file(sample_project_data, str(filepath))
        
        # Load
        loaded_data = project_manager.load_project_file(str(filepath))
        
        assert loaded_data["project_version"] == "1.0"
        assert loaded_data["video"]["filename"] == "test_video.mp4"
        assert len(loaded_data["segments"]) == 2
        assert len(loaded_data["ai_analysis_history"]) == 1
    
    def test_load_nonexistent_file(self, project_manager):
        """Test loading a file that doesn't exist."""
        with pytest.raises(ProjectManagerError, match="not found"):
            project_manager.load_project_file("/nonexistent/path/project.tbproj")
    
    def test_load_corrupt_json(self, project_manager, temp_dir):
        """Test loading a corrupted JSON file."""
        filepath = temp_dir / "corrupt.tbproj"
        filepath.write_text("{ invalid json ]")
        
        with pytest.raises(ProjectManagerError, match="Corrupt project file"):
            project_manager.load_project_file(str(filepath))
    
    def test_validate_project_data_valid(self, project_manager, sample_project_data):
        """Test validation of valid project data."""
        validation = project_manager.validate_project_data(sample_project_data)
        
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
    
    def test_validate_project_data_missing_fields(self, project_manager):
        """Test validation with missing required fields."""
        invalid_data = {"project_version": "1.0"}  # Missing video
        
        validation = project_manager.validate_project_data(invalid_data)
        
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0
        assert any("video" in err.lower() for err in validation["errors"])
    
    def test_create_project_data(self, project_manager):
        """Test creating project data structure."""
        video_metadata = {
            "filename": "test.mp4",
            "file_path": "/path/to/test.mp4",
            "duration": 100.0,
            "file_size": 1000000
        }
        
        segments = [{"start": 0, "end": 10, "type": "audible"}]
        
        project_data = project_manager.create_project_data(
            video_metadata=video_metadata,
            segments=segments
        )
        
        assert "project_version" in project_data
        assert project_data["video"]["filename"] == "test.mp4"
        assert len(project_data["segments"]) == 1
        assert "created" in project_data
        assert "modified" in project_data
    
    def test_auto_save_filename(self, project_manager):
        """Test auto-save filename generation."""
        video_path = "/path/to/my_video.mp4"
        
        filename = project_manager.auto_save_filename(video_path)
        
        assert filename.startswith("my_video_autosave_")
        assert filename.endswith(".tbproj")
    
    def test_export_project_summary(self, project_manager, sample_project_data):
        """Test exporting project summary."""
        summary = project_manager.export_project_summary(sample_project_data)
        
        assert "TooBoooring Studio Project Summary" in summary
        assert "test_video.mp4" in summary
        assert "Duration:" in summary
        assert "Segments:" in summary
    
    def test_get_recent_projects(self, project_manager, sample_project_data, temp_dir):
        """Test getting recent projects."""
        # Create multiple project files
        for i in range(3):
            filepath = temp_dir / f"project_{i}.tbproj"
            project_manager.save_project_file(sample_project_data, str(filepath))
        
        recent = project_manager.get_recent_projects(str(temp_dir), limit=5)
        
        assert len(recent) == 3
        assert all(p["filename"].endswith(".tbproj") for p in recent)
        # Should be sorted by modified time (newest first)
        assert recent[0]["modified"] >= recent[1]["modified"]
    
    def test_file_hash_calculation(self, project_manager, temp_dir):
        """Test file hash calculation."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello World")
        
        hash1 = project_manager._calculate_file_hash(str(test_file))
        hash2 = project_manager._calculate_file_hash(str(test_file))
        
        # Same file should produce same hash
        assert hash1 == hash2
        
        # Different content should produce different hash
        test_file.write_text("Different Content")
        hash3 = project_manager._calculate_file_hash(str(test_file))
        assert hash1 != hash3


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_save_project_file_function(self, sample_project_data, temp_dir):
        """Test save_project_file convenience function."""
        filepath = temp_dir / "test.tbproj"
        
        result = save_project_file(sample_project_data, str(filepath))
        
        assert result["success"] is True
        assert Path(result["filepath"]).exists()
    
    def test_load_project_file_function(self, sample_project_data, temp_dir):
        """Test load_project_file convenience function."""
        filepath = temp_dir / "test.tbproj"
        
        # Save first
        save_project_file(sample_project_data, str(filepath))
        
        # Load
        loaded = load_project_file(str(filepath))
        
        assert loaded["video"]["filename"] == sample_project_data["video"]["filename"]


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_save_with_unicode_characters(self, project_manager, sample_project_data, temp_dir):
        """Test saving project with unicode characters."""
        sample_project_data["video"]["filename"] = "测试视频_тест_🎬.mp4"
        filepath = temp_dir / "test_unicode.tbproj"
        
        result = project_manager.save_project_file(sample_project_data, str(filepath))
        assert result["success"] is True
        
        # Load and verify
        loaded = project_manager.load_project_file(str(filepath))
        assert loaded["video"]["filename"] == "测试视频_тест_🎬.mp4"
    
    def test_save_large_project(self, project_manager, sample_project_data, temp_dir):
        """Test saving project with large number of segments."""
        # Create 10000 segments
        sample_project_data["segments"] = [
            {"start": i, "end": i+1, "type": "audible"}
            for i in range(10000)
        ]
        
        filepath = temp_dir / "large_project.tbproj"
        result = project_manager.save_project_file(sample_project_data, str(filepath))
        
        assert result["success"] is True
        
        # Verify load
        loaded = project_manager.load_project_file(str(filepath))
        assert len(loaded["segments"]) == 10000
    
    def test_save_empty_project(self, project_manager, temp_dir):
        """Test saving minimal project data."""
        minimal_data = {
            "project_version": "1.0",
            "video": {
                "filename": "test.mp4",
                "file_path": "/test.mp4",
                "duration": 0,
                "file_size": 0
            }
        }
        
        filepath = temp_dir / "minimal.tbproj"
        result = project_manager.save_project_file(minimal_data, str(filepath))
        
        assert result["success"] is True
    
    def test_load_with_missing_video_file(self, project_manager, sample_project_data, temp_dir):
        """Test loading project when video file doesn't exist."""
        sample_project_data["video"]["file_path"] = "/nonexistent/video.mp4"
        filepath = temp_dir / "test.tbproj"
        
        # Save
        project_manager.save_project_file(sample_project_data, str(filepath))
        
        # Load (should succeed but add warning)
        loaded = project_manager.load_project_file(str(filepath))
        
        assert loaded["video"]["exists"] is False
        assert any("not found" in w.lower() for w in loaded.get("warnings", []))
    
    def test_invalid_project_version(self, project_manager, sample_project_data, temp_dir):
        """Test loading project with different version."""
        sample_project_data["project_version"] = "2.0"
        filepath = temp_dir / "test.tbproj"
        
        project_manager.save_project_file(sample_project_data, str(filepath))
        
        # Should load successfully (version migration not yet implemented)
        loaded = project_manager.load_project_file(str(filepath))
        assert loaded["project_version"] == "2.0"


def test_integration_workflow(project_manager, temp_dir):
    """Test complete workflow: create, save, modify, save, load."""
    # Step 1: Create project
    video_metadata = {
        "filename": "workflow_test.mp4",
        "file_path": str(temp_dir / "workflow_test.mp4"),
        "duration": 100.0,
        "file_size": 1000000
    }
    
    project_data = project_manager.create_project_data(
        video_metadata=video_metadata,
        segments=[{"start": 0, "end": 10}]
    )
    
    # Step 2: Save
    filepath = temp_dir / "workflow.tbproj"
    project_manager.save_project_file(project_data, str(filepath))
    
    # Step 3: Load
    loaded = project_manager.load_project_file(str(filepath))
    assert len(loaded["segments"]) == 1
    
    # Step 4: Modify
    loaded["segments"].append({"start": 10, "end": 20})
    
    # Step 5: Save again
    project_manager.save_project_file(loaded, str(filepath))
    
    # Step 6: Load and verify
    final = project_manager.load_project_file(str(filepath))
    assert len(final["segments"]) == 2
    assert final["modified"] != final["created"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

