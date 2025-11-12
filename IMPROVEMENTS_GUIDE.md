# Code Improvements Guide

This document explains the issues found in the codebase and how to fix them.

## 1. Inconsistent Error Handling

### Problem
Different functions return errors in different formats, and callers don't always check for errors consistently.

### Examples

**Example 1: Inconsistent return formats**
```python
# web_main.py - Some functions return {"error": str}
def load_video(self):
    try:
        # ... code ...
        return video_info
    except Exception as e:
        return {"error": str(e)}  # Returns dict with "error" key

# But other functions return None or raise exceptions
def get_loadable_file_url(self, file_path):
    try:
        # ... code ...
        return 'file:///' + url_path
    except Exception as e:
        return None  # Returns None instead of error dict
```

**Example 2: JavaScript doesn't always check for errors**
```javascript
// main.js - Sometimes checks for error, sometimes doesn't
const videoInfo = await window.pywebview.api.load_video();
if (videoInfo && !videoInfo.error) {  // ✅ Checks for error
    // ... use videoInfo
}

// But in detectSilence:
const segments = await window.pywebview.api.detect_silence(...);
// ❌ Doesn't check if segments is {"error": "..."} before using it
if (segments && !segments.error) {  // Should check this!
    timeline.draw(segments, ...);
}
```

### Fix

**Standardize error format:**
```python
# Create a helper function for consistent error responses
def _error_response(self, message: str) -> dict:
    """Return a standardized error response."""
    return {"error": message, "status": "error"}

def _success_response(self, data: dict) -> dict:
    """Return a standardized success response."""
    return {"status": "success", **data}

# Use it everywhere:
def load_video(self):
    try:
        # ... code ...
        return self._success_response({"videoInfo": video_info})
    except Exception as e:
        return self._error_response(str(e))
```

**Always check for errors in JavaScript:**
```javascript
// Create a helper function
function checkError(result) {
    if (!result) return { hasError: true, message: "No response" };
    if (result.error) return { hasError: true, message: result.error };
    if (result.status === "error") return { hasError: true, message: result.message };
    return { hasError: false, data: result };
}

// Use it everywhere:
const result = await window.pywebview.api.detect_silence(...);
const { hasError, message, data } = checkError(result);
if (hasError) {
    alert(`Error: ${message}`);
    return;
}
// Use data safely
timeline.draw(data.segments, ...);
```

---

## 2. Memory Management

### Problem
Large video files can cause memory issues because:
- Full waveforms are loaded into memory at once
- No limits on file size
- No cleanup of temporary data

### Example
```python
# waveform.py - Loads entire audio into memory
def extract_audio_waveform(file_path, ffmpeg_path, status_callback):
    # This loads the ENTIRE audio file into memory
    y, sr = librosa.load(temp_audio_file, sr=None)  # ❌ Could be GB for long videos
    return y  # Returns full array
```

### Fix

**Add file size limits and chunking:**
```python
import os
from pathlib import Path

MAX_FILE_SIZE_MB = 500  # Limit file size
MAX_WAVEFORM_SAMPLES = 1000000  # Limit waveform samples

def extract_audio_waveform(file_path, ffmpeg_path, status_callback):
    # Check file size first
    file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        status_callback(f"⚠️ File too large ({file_size_mb:.1f}MB). Max: {MAX_FILE_SIZE_MB}MB")
        return None
    
    # Extract audio
    y, sr = librosa.load(temp_audio_file, sr=None)
    
    # Limit samples if too large
    if len(y) > MAX_WAVEFORM_SAMPLES:
        status_callback(f"⚠️ Audio too long. Downsampling for display...")
        # Downsample immediately instead of keeping full array
        step = len(y) // MAX_WAVEFORM_SAMPLES
        y = y[::step]
    
    return y
```

**Add cleanup:**
```python
def get_waveform_data(self, file_path, width):
    waveform_data = None
    try:
        # ... extract waveform ...
        return waveform_data
    finally:
        # Explicitly clear large variables
        waveform_data = None
        import gc
        gc.collect()  # Force garbage collection
```

---

## 3. Progress Callback Not Reset on Errors

### Problem
When export fails, the progress bar might stay at a partial value instead of resetting.

### Example
```javascript
// main.js - exportVideo function
async function exportVideo() {
    // ... validation ...
    
    window.updateProgress(0, "Calculating...", 0);  // ✅ Resets at start
    
    const result = await window.pywebview.api.export_video(...);
    
    if (result.status === 'success') {
        window.updateProgress(100, "Complete", 0);  // ✅ Sets to 100%
    } else {
        // ❌ Doesn't reset progress on error!
        statusLabel.textContent = "Export failed.";
        // Progress bar might still show 45% or whatever it was at failure
    }
}
```

### Fix

**Always reset progress in finally block:**
```javascript
async function exportVideo() {
    let exportSucceeded = false;
    
    try {
        // ... validation ...
        window.updateProgress(0, "Calculating...", 0);
        
        const result = await window.pywebview.api.export_video(...);
        
        if (result.status === 'success') {
            window.updateProgress(100, "Complete", 0);
            exportSucceeded = true;
        } else {
            // Reset progress on error
            window.updateProgress(0, "Failed", 0);
        }
    } catch (error) {
        // Reset progress on exception
        window.updateProgress(0, "Error", 0);
        console.error("Export error:", error);
    } finally {
        // Always re-enable button
        exportButton.disabled = false;
        exportButton.textContent = "Export Video";
        
        // Reset progress if not already set
        if (!exportSucceeded) {
            window.updateProgress(0, "Ready", 0);
        }
    }
}
```

---

## 4. File Path Handling

### Problem
Inconsistent use of `Path` objects vs strings, and Windows path handling issues.

### Example
```python
# web_main.py - Mixes Path and string
def load_video(self):
    file_path = filedialog.askopenfilename(...)  # Returns string
    duration = get_video_duration(Path(file_path), ...)  # Converts to Path
    # But sometimes uses file_path as string elsewhere
```

### Fix

**Standardize on Path objects:**
```python
from pathlib import Path
from typing import Union

def normalize_path(path: Union[str, Path]) -> Path:
    """Convert string or Path to Path object, handling Windows paths."""
    if isinstance(path, str):
        return Path(path)
    return path

def safe_path_string(path: Union[str, Path]) -> str:
    """Convert Path to string safely for FFmpeg."""
    return str(normalize_path(path))

# Use everywhere:
def load_video(self):
    file_path_str = filedialog.askopenfilename(...)
    if not file_path_str:
        return None
    
    file_path = normalize_path(file_path_str)  # Always use Path
    
    # Validate path
    if not file_path.exists():
        return self._error_response("File does not exist")
    
    # Use Path object consistently
    duration = get_video_duration(file_path, ...)
    
    # Only convert to string when needed (e.g., for JSON)
    return {
        "filePath": str(file_path),  # Convert for JSON
        "fileName": file_path.name,   # Use Path methods
        "duration": duration
    }
```

**Add path validation:**
```python
def validate_video_path(path: Union[str, Path]) -> tuple[bool, str]:
    """Validate video file path."""
    try:
        path_obj = normalize_path(path)
        
        # Check if exists
        if not path_obj.exists():
            return False, "File does not exist"
        
        # Check if file (not directory)
        if not path_obj.is_file():
            return False, "Path is not a file"
        
        # Check file extension
        valid_extensions = {'.mp4', '.mkv', '.mov', '.avi', '.wmv', '.flv', '.webm', '.m4v'}
        if path_obj.suffix.lower() not in valid_extensions:
            return False, f"Invalid file type: {path_obj.suffix}"
        
        # Check file size (prevent DoS)
        max_size = 10 * 1024 * 1024 * 1024  # 10GB
        if path_obj.stat().st_size > max_size:
            return False, "File too large (max 10GB)"
        
        return True, ""
    except Exception as e:
        return False, f"Path validation error: {str(e)}"
```

---

## 5. Type Hints

### Problem
Many functions lack type hints, making code harder to understand and maintain.

### Example
```python
# web_main.py - Missing type hints
def load_video(self):  # ❌ No return type
    # What does this return? dict? None? Something else?
    return video_info

def detect_silence(self, video_path, track_index):  # ❌ No types
    # What types are video_path and track_index?
    pass
```

### Fix

**Add comprehensive type hints:**
```python
from typing import Optional, Dict, List, Any, Callable
from pathlib import Path

class Api:
    def load_video(self) -> Optional[Dict[str, Any]]:
        """
        Load a video file.
        
        Returns:
            Dict with video info or None if cancelled
        """
        # ... code ...
        return video_info
    
    def detect_silence(
        self, 
        video_path: str, 
        track_index: int
    ) -> Dict[str, Any]:
        """
        Detect silence in video.
        
        Args:
            video_path: Path to video file
            track_index: Index of audio track to analyze
            
        Returns:
            Dict with segments or error info
        """
        # ... code ...
        return segments
    
    def export_video(
        self,
        video_info: Dict[str, Any],
        segments: List[Dict[str, Any]],
        export_settings: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Export video with silence removed.
        
        Args:
            video_info: Video information dict
            segments: List of segment dicts
            export_settings: Export configuration dict
            
        Returns:
            Dict with status and message
        """
        # ... code ...
        return {"status": "success", "message": "..."}
```

---

## 6. Logging

### Problem
Using `print()` statements instead of proper logging makes it hard to:
- Control log levels (debug, info, warning, error)
- Write logs to files
- Filter logs in production

### Example
```python
# web_main.py - Uses print() everywhere
print(f"Python: Analyzing {file_path}...")
print(f"Error analyzing video: {e}")
print(f"Python: Found {len(segments)} segments.")
```

### Fix

**Replace print() with logging:**
```python
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Console handler (for development)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler (for production)
log_file = Path(__file__).parent.parent / "logs" / "app.log"
log_file.parent.mkdir(exist_ok=True)
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Use logger instead of print:
class Api:
    def load_video(self):
        logger.info(f"Loading video: {file_path}")
        try:
            # ... code ...
            logger.info(f"Successfully loaded video: {video_info['fileName']}")
            return video_info
        except Exception as e:
            logger.error(f"Error loading video: {e}", exc_info=True)
            return {"error": str(e)}
    
    def detect_silence(self, video_path, track_index):
        logger.debug(f"Detecting silence for {video_path} on track {track_index}")
        # ... code ...
        logger.info(f"Found {len(segments)} segments")
        return segments
```

**For web UI console (keep both):**
```python
def log_to_console(self, message: str):
    """Sends a log message to the web UI console."""
    logger.info(message)  # ✅ Use logger
    self.console_log.append(message)
    if self.window:
        try:
            escaped_message = message.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
            self.window.evaluate_js(f'window.app.addLog("{escaped_message}");')
        except Exception as e:
            logger.error(f"Error sending log to console: {e}")  # ✅ Use logger
```

---

## Summary of Priority Fixes

1. **High Priority:**
   - ✅ Add error checking in JavaScript (prevents crashes)
   - ✅ Reset progress on errors (better UX)
   - ✅ Add file size validation (prevents DoS)

2. **Medium Priority:**
   - ✅ Replace print() with logging (better debugging)
   - ✅ Add type hints (better code maintainability)
   - ✅ Standardize error responses (consistent API)

3. **Low Priority:**
   - ✅ Memory management improvements (for very large files)
   - ✅ Path handling standardization (cleaner code)

Would you like me to implement any of these fixes?

