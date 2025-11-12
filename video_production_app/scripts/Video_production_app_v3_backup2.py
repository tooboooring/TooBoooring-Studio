#!/usr/bin/env python3
"""
Video Production App v3.0 - Complete Professional Suite
Combines Smart Preview System (v2) with Full Processing Capabilities (v1)

Features:
- Interactive timeline with multi-track waveform visualization
- Frame-accurate preview with FFplay integration  
- Silence detection with customizable parameters
- GPU-accelerated encoding (NVIDIA, AMD, Intel)
- Batch processing
- Video trimming
- Multi-track audio support
"""

import os
import re
import sys
import json
import subprocess
import shlex
import threading
import time
from pathlib import Path
from datetime import timedelta
from typing import Callable, Optional, List, Tuple
import customtkinter as ctk
from tkinter import filedialog, messagebox, Canvas
from PIL import Image, ImageTk
import numpy as np

# Check for optional packages
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("[WARNING] opencv-python not installed. Frame preview will be limited.")

try:
    import librosa
    AUDIO_ANALYSIS_AVAILABLE = True
except ImportError:
    AUDIO_ANALYSIS_AVAILABLE = False
    print("[WARNING] librosa/soundfile not installed. Waveform visualization disabled.")


# --- DEFAULT CONFIGURATION ---
DEFAULT_SETTINGS = {
    "silence_db": -40,
    "silence_duration": 0.7,
    "pad_before": 0.1,
    "pad_after": 0.0,
    "filter_length_threshold": 4096
}

ENCODER_OPTIONS = {
    "NVIDIA (H.264)": ("h264_nvenc", "-c:v h264_nvenc -rc constqp -qp 20 -preset slow"),
    "NVIDIA (HEVC)": ("hevc_nvenc", "-c:v hevc_nvenc -rc constqp -qp 20 -preset slow"),
    "AMD (H.264)": ("h264_amf", "-c:v h264_amf -quality balanced -rc cqp -qp_p 20 -qp_i 20"),
    "AMD (HEVC)": ("hevc_amf", "-c:v hevc_amf -quality balanced -rc cqp -qp_p 20 -qp_i 20"),
    "Intel (H.264)": ("h264_qsv", "-c:v h264_qsv -q 20 -preset slow"),
    "Intel (HEVC)": ("hevc_qsv", "-c:v hevc_qsv -q 20 -preset slow"),
    "CPU (x264)": ("libx264", "-c:v libx264 -crf 20 -preset medium")
}

# --- CUSTOM COLOR THEME ---
class AppColors:
    """Professional color scheme for the application."""
    # Primary colors
    PRIMARY = "#1f6aa5"  # Blue
    PRIMARY_HOVER = "#1a5a8f"
    PRIMARY_DARK = "#164a75"
    
    # Accent colors
    SUCCESS = "#2fb344"  # Green
    SUCCESS_HOVER = "#25a339"
    WARNING = "#f59e0b"  # Amber
    DANGER = "#ef4444"  # Red
    INFO = "#3b82f6"  # Light blue
    
    # Backgrounds
    BG_DARK = "#1a1a1a"
    BG_MEDIUM = "#2b2b2b"
    BG_LIGHT = "#383838"
    BG_CARD = "gray25"
    BG_CARD_HOVER = "gray30"
    
    # Text colors
    TEXT_PRIMARY = "white"
    TEXT_SECONDARY = "gray70"
    TEXT_MUTED = "gray50"
    
    # Borders
    BORDER = "gray35"
    BORDER_LIGHT = "gray40"
    
    # Segments (for timeline)
    SEGMENT_KEEP = "#2fb344"
    SEGMENT_REMOVE = "#2b2b2b"
    SEGMENT_BORDER = "#25a339"
    
    # Waveform colors (multi-track)
    WAVEFORM_COLORS = [
        "#3b82f6",  # Blue
        "#10b981",  # Emerald
        "#f59e0b",  # Amber
        "#ec4899",  # Pink
        "#8b5cf6",  # Violet
        "#06b6d4",  # Cyan
    ]

# --- SETTINGS MANAGER ---
class SettingsManager:
    """Manages user settings with JSON persistence."""
    
    def __init__(self, config_file: str = "video_cutter_settings.json"):
        self.config_file = Path(config_file)
        self.settings = DEFAULT_SETTINGS.copy()
        self.load_settings()
    
    def load_settings(self):
        """Load settings from JSON file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except (json.JSONDecodeError, IOError):
                pass  # Use defaults if file is corrupted
    
    def save_settings(self):
        """Save settings to JSON file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except IOError:
            pass
    
    def get(self, key: str, default=None):
        return self.settings.get(key, default)
    
    def set(self, key: str, value):
        self.settings[key] = value
        self.save_settings()


# --- GPU & FFMPEG LOGIC ---
def get_available_encoders(ffmpeg_path: str, status_callback) -> list[str]:
    """Detects all available hardware and software encoders from our list."""
    ffmpeg_executable = ffmpeg_path or "ffmpeg"
    status_callback("🔍 Detecting available GPU encoders...\n")
    found_encoders = []

    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run([str(ffmpeg_executable), "-encoders"], capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
        available_encoders_output = result.stdout

        for display_name, (encoder_name, _) in ENCODER_OPTIONS.items():
            if re.search(r"^\s*V..... " + re.escape(encoder_name), available_encoders_output, re.MULTILINE):
                found_encoders.append(display_name)
        
        if "CPU (x264)" not in found_encoders:
            found_encoders.append("CPU (x264)")

        if len(found_encoders) > 1:
             status_callback(f"✅ Found {len(found_encoders) - 1} compatible hardware encoder(s).\n")
        else:
             status_callback("⚠️ No compatible hardware encoder found. Will use CPU.\n")

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        status_callback(f"❌ Could not run FFmpeg to detect encoders: {e}\n")
        if "CPU (x264)" not in found_encoders:
            found_encoders.append("CPU (x264)")
    
    found_encoders.insert(0, "Automatic (Best GPU)")
    return found_encoders


def get_audio_tracks(video_file: Path, ffprobe_path: str, status_callback) -> list[dict]:
    """Uses ffprobe to find all audio streams in a video file with detailed information."""
    status_callback(f"🔎 Scanning for audio tracks in {video_file.name}...\n")
    ffprobe_executable = ffprobe_path or "ffprobe"
    cmd = [
        str(ffprobe_executable), "-v", "error", "-show_streams", "-select_streams", "a",
        "-of", "json", str(video_file)
    ]
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
        streams = json.loads(result.stdout).get("streams", [])
        audio_tracks = []
        for stream in streams:
            track_index = stream.get("index")
            codec_name = stream.get("codec_name", "unknown")
            language = stream.get("tags", {}).get("language", "und")
            channels = stream.get("channels", "?")
            sample_rate = stream.get("sample_rate", "?")
            bit_rate = stream.get("bit_rate", "0")
            
            # Format channel info
            channel_layout = stream.get("channel_layout", "")
            if channels == 1:
                channel_str = "mono"
            elif channels == 2:
                channel_str = "stereo"
            elif channels == 6:
                channel_str = "5.1"
            elif channels == 8:
                channel_str = "7.1"
            else:
                channel_str = f"{channels}ch"
            
            # Format bitrate
            try:
                bitrate_kbps = int(bit_rate) // 1000
                bitrate_str = f"{bitrate_kbps}kbps" if bitrate_kbps > 0 else "N/A"
            except:
                bitrate_str = "N/A"
            
            # Format sample rate
            try:
                sample_rate_khz = int(sample_rate) // 1000
                sample_rate_str = f"{sample_rate_khz}kHz"
            except:
                sample_rate_str = "?"
            
            name = f"Track {track_index} ({codec_name}{f', {language}' if language != 'und' else ''})"
            
            audio_tracks.append({
                "name": name,
                "index": track_index,
                "codec": codec_name,
                "language": language,
                "channels": channels,
                "channel_str": channel_str,
                "sample_rate": sample_rate_str,
                "bitrate": bitrate_str,
                "bitrate_raw": int(bit_rate) if bit_rate.isdigit() else 0
            })
        
        if not audio_tracks:
            status_callback("⚠️ No audio tracks found in this file.\n")
        else:
            status_callback(f"✅ Found {len(audio_tracks)} audio track(s).\n")
        return audio_tracks

    except FileNotFoundError:
        status_callback(f"❌ Error: '{ffprobe_executable}' not found.\n")
        status_callback("   Please place ffprobe.exe next to the app, or add it to your system's PATH.\n")
        return []
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        status_callback(f"❌ Error scanning for audio tracks: {e}\n")
        return []


def get_video_duration(video_file: Path, ffprobe_path: str, status_callback) -> float:
    """Get video duration in seconds."""
    ffprobe_executable = ffprobe_path or "ffprobe"
    cmd = [str(ffprobe_executable), "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_file)]
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError) as e:
        status_callback(f"❌ Error getting duration: {e}\n")
        return 0.0


def analyze_audio_track_content(video_file: Path, track_index: int, ffmpeg_path: str) -> dict:
    """Analyze if an audio track has content or is silent."""
    ffmpeg_executable = ffmpeg_path or "ffmpeg"
    
    # Use volumedetect filter to analyze audio levels
    cmd = [
        str(ffmpeg_executable), "-hide_banner", "-i", str(video_file),
        "-map", f"0:{track_index}", "-af", "volumedetect",
        "-f", "null", "-t", "10", "-"  # Only analyze first 10 seconds for speed
    ]
    
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        result = subprocess.run(cmd, capture_output=True, text=True, 
                              encoding='utf-8', errors='ignore', startupinfo=startupinfo)
        
        # Parse volumedetect output
        output = result.stderr
        mean_volume = None
        max_volume = None
        
        mean_match = re.search(r'mean_volume:\s*(-?\d+\.?\d*)\s*dB', output)
        max_match = re.search(r'max_volume:\s*(-?\d+\.?\d*)\s*dB', output)
        
        if mean_match:
            mean_volume = float(mean_match.group(1))
        if max_match:
            max_volume = float(max_match.group(1))
        
        # Determine if track is silent (mean volume below -70dB or no audio)
        is_silent = False
        status = "Has Audio"
        
        if mean_volume is None or max_volume is None:
            is_silent = True
            status = "No Audio Data"
        elif mean_volume < -70 or max_volume < -60:
            is_silent = True
            status = "Silent/Empty"
        elif mean_volume < -40:
            status = "Quiet Audio"
        elif mean_volume < -20:
            status = "Normal Audio"
        else:
            status = "Loud Audio"
        
        return {
            "is_silent": is_silent,
            "mean_volume": mean_volume,
            "max_volume": max_volume,
            "status": status
        }
    
    except Exception:
        return {
            "is_silent": False,
            "mean_volume": None,
            "max_volume": None,
            "status": "Unknown"
        }


def detect_silence(video_file: Path, track_index: int, ffmpeg_path: str, settings: dict, status_callback, trim_start: float = 0, trim_end: Optional[float] = None) -> str:
    """Detect silence in audio track with optional trimming."""
    status_callback(f"🤫 Detecting silence in track {track_index}...\n")
    ffmpeg_executable = ffmpeg_path or "ffmpeg"
    
    silence_db = settings.get("silence_db", -40)
    silence_duration = settings.get("silence_duration", 0.7)
    
    silence_filter = f"silencedetect=n={silence_db}dB:d={silence_duration}"
    
    cmd = [str(ffmpeg_executable), "-hide_banner"]
    
    # Add trim if specified
    if trim_start > 0 or trim_end is not None:
        cmd.extend(["-ss", str(trim_start)])
        if trim_end is not None:
            cmd.extend(["-to", str(trim_end)])
    
    cmd.extend(["-i", str(video_file), "-map", f"0:{track_index}", "-af", silence_filter, "-f", "null", "-"])
    
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
    return result.stderr


def parse_segments(ffmpeg_output: str, duration: float, settings: dict, status_callback, trim_start: float = 0) -> list[tuple[float, float]]:
    """Parse silence detection output into audible segments."""
    starts = [float(t) + trim_start for t in re.findall(r'silence_start: (\d+\.?\d*)', ffmpeg_output)]
    ends = [float(t) + trim_start for t in re.findall(r'silence_end: (\d+\.?\d*)', ffmpeg_output)]

    if not starts and not ends:
        status_callback("🤔 No silence detected. Treating entire video as one segment.\n")
        return [(trim_start, duration)]

    pad_before = settings.get("pad_before", 0.1)
    pad_after = settings.get("pad_after", 0.0)

    audible_segments = []
    if starts and starts[0] > trim_start:
        audible_segments.append((trim_start, starts[0]))
    for i in range(len(ends)):
        start_time = ends[i]
        end_time = starts[i+1] if (i + 1) < len(starts) else duration
        if end_time > start_time:
            audible_segments.append((start_time, end_time))

    status_callback(f"🔍 Found {len(audible_segments)} audible segments.\n")
    padded_segments = [(max(trim_start, s - pad_before), min(duration, e + pad_after)) for s, e in audible_segments]
    return [p for p in padded_segments if p[1] > p[0]]


def parse_ffmpeg_progress(line: str) -> Optional[dict]:
    """Parse FFmpeg progress output."""
    progress_data = {}
    if "time=" in line:
        time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
        if time_match:
            hours, minutes, seconds = time_match.groups()
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            progress_data['time'] = total_seconds
    
    if "speed=" in line:
        speed_match = re.search(r'speed=\s*(\d+\.?\d*)x', line)
        if speed_match:
            progress_data['speed'] = float(speed_match.group(1))
    
    return progress_data if progress_data else None


def process_video_logic(video_path: str, output_dir: str, output_format: str, video_params: str, 
                       all_audio_tracks: list[dict], silence_track_index: int, 
                       ffmpeg_path: str, ffprobe_path: str, settings: dict,
                       status_callback, progress_callback=None,
                       trim_start: float = 0, trim_end: Optional[float] = None,
                       segments: Optional[list[tuple[float, float]]] = None):
    """Process video with silence removal and optional trimming."""
    video_file = Path(video_path)
    output_path = Path(output_dir)
    temp_dir = output_path / "temp_silence_cutter"
    temp_dir.mkdir(exist_ok=True)
    output_file = output_path / f"{video_file.stem}_final.{output_format.lower()}"

    if output_file.exists():
        status_callback(f"⏭️ Output file '{output_file.name}' already exists. Skipping.\n")
        return

    status_callback("-" * 40 + "\n")
    status_callback(f"🎬 Starting processing for: {video_file.name}\n")
    
    duration = get_video_duration(video_file, ffprobe_path, status_callback)
    if duration == 0.0: 
        return
    
    # Apply trim_end if specified
    effective_duration = trim_end if trim_end is not None else duration

    # Use provided segments or detect them
    if segments is None:
        ffmpeg_log = detect_silence(video_file, silence_track_index, ffmpeg_path, settings, status_callback, trim_start, trim_end)
        segments = parse_segments(ffmpeg_log, effective_duration, settings, status_callback, trim_start)
    
    if not segments:
        status_callback(f"⚠️ No valid audible segments found. Skipping.\n")
        return

    select_filter = "+".join([f"between(t,{s},{e})" for s, e in segments])
    video_args = shlex.split(video_params)
    
    audio_params = "-c:a aac -b:a 192k" if output_format.lower() == "mp4" else "-c:a pcm_s16le"
    audio_args = shlex.split(audio_params)

    filter_complex_parts = [f"[0:v]select='{select_filter}',setpts=N/FRAME_RATE/TB[v]"]
    map_args = ["[v]"]
    for i, track in enumerate(all_audio_tracks):
        stream_index = track['index']
        filter_complex_parts.append(f"[0:{stream_index}]aselect='{select_filter}',asetpts=N/SR/TB[a{i}]")
        map_args.append(f"[a{i}]")
    filter_complex = ";".join(filter_complex_parts)

    ffmpeg_executable = ffmpeg_path or "ffmpeg"
    base_cmd = [str(ffmpeg_executable), "-y", "-hide_banner"]
    
    # Add progress reporting
    if progress_callback:
        base_cmd.extend(["-progress", "pipe:1", "-stats_period", "0.5"])
    
    base_cmd.extend(["-i", str(video_file)])
    
    temp_filter_file = None
    filter_length_threshold = settings.get("filter_length_threshold", 4096)
    if len(filter_complex) > filter_length_threshold:
        status_callback("🛠️ Filter string is very long. Using a temporary script file.\n")
        temp_filter_file = temp_dir / f"{video_file.stem}_filter.txt"
        temp_filter_file.write_text(filter_complex, encoding='utf-8')
        filter_cmd = ["-filter_complex_script", str(temp_filter_file)]
    else:
        filter_cmd = ["-filter_complex", filter_complex]

    final_map_args = [arg for m in map_args for arg in ("-map", m)]
    if output_format.lower() == "mp4":
        video_args.extend(["-pix_fmt", "yuv420p"])

    cmd = base_cmd + filter_cmd + final_map_args + video_args + audio_args + [str(output_file)]
    status_callback(f"⚙️ Running FFmpeg... This may take a while.\n")
    
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        if progress_callback:
            # Run with progress monitoring
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                     text=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
            
            total_duration = sum(e - s for s, e in segments)
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    progress_data = parse_ffmpeg_progress(output)
                    if progress_data and 'time' in progress_data:
                        current_time = progress_data['time']
                        percentage = min(100, (current_time / total_duration) * 100) if total_duration > 0 else 0
                        speed = progress_data.get('speed', 0)
                        
                        if speed > 0:
                            remaining_time = (total_duration - current_time) / speed
                            eta = str(timedelta(seconds=int(remaining_time)))
                        else:
                            eta = "Calculating..."
                        
                        progress_callback(percentage, eta, speed)
            
            return_code = process.wait()
            if return_code != 0:
                stderr = process.stderr.read()
                raise subprocess.CalledProcessError(return_code, cmd, stderr=stderr)
        else:
            subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
        
        status_callback(f"✅ Successfully created: {output_file.name}\n")
        status_callback(f"📍 Saved to: {output_file}\n")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        status_callback(f"❌ FFmpeg failed for {video_file.name}!\n")
        if isinstance(e, subprocess.CalledProcessError):
            status_callback(f"   FFmpeg stderr:\n{e.stderr}\n")
        else:
            status_callback(f"   Error: '{ffmpeg_executable}' not found.\n")
    finally:
        if temp_filter_file and temp_filter_file.exists(): 
            temp_filter_file.unlink()
        try:
            if temp_dir.exists() and not any(temp_dir.iterdir()): 
                temp_dir.rmdir()
        except OSError: 
            pass




# --- WAVEFORM GENERATOR ---
class WaveformGenerator:
    """Generates audio waveform visualization."""
    
    @staticmethod
    def extract_audio_waveforms_all_tracks(video_path: str, ffmpeg_path: str, audio_tracks: List[dict],
                                          status_callback=None) -> dict:
        """Extract waveforms for ALL audio tracks separately."""
        if not AUDIO_ANALYSIS_AVAILABLE:
            if status_callback:
                status_callback("⚠️ librosa not installed. Waveform unavailable.\n")
            return {}
        
        waveforms = {}
        
        try:
            for track in audio_tracks:
                track_index = track["audio_index"]
                stream_index = track["stream_index"]
                
                if status_callback:
                    status_callback(f"📊 Extracting waveform for Track {track_index + 1}...\n")
                
                temp_audio = Path(video_path).parent / f"_temp_audio_track{track_index}.wav"
                ffmpeg_exe = ffmpeg_path or "ffmpeg"
                
                # Extract specific audio track
                cmd = [
                    str(ffmpeg_exe), "-y", "-i", str(video_path),
                    "-map", f"0:{stream_index}",  # Map specific audio stream
                    "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
                    str(temp_audio)
                ]
                
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                subprocess.run(cmd, check=True, capture_output=True, startupinfo=startupinfo)
                
                # Load audio with librosa
                y, sr = librosa.load(str(temp_audio), sr=22050, mono=True)
                
                # Store waveform
                waveforms[track_index] = {
                    "waveform": y,
                    "track_info": track
                }
                
                # Clean up
                if temp_audio.exists():
                    temp_audio.unlink()
            
            if status_callback:
                status_callback(f"✅ Extracted {len(waveforms)} waveforms!\n")
            
            return waveforms
            
        except Exception as e:
            if status_callback:
                status_callback(f"⚠️ Waveform extraction failed: {e}\n")
            # Clean up any temp files
            for i in range(10):  # Clean up potential temp files
                temp_audio = Path(video_path).parent / f"_temp_audio_track{i}.wav"
                if temp_audio.exists():
                    temp_audio.unlink()
            return waveforms
    
    @staticmethod
    def extract_audio_waveform(video_path: str, ffmpeg_path: str, 
                              status_callback=None) -> Optional[np.ndarray]:
        """Extract mixed audio waveform from video (legacy - for single track)."""
        if not AUDIO_ANALYSIS_AVAILABLE:
            if status_callback:
                status_callback("⚠️ librosa not installed. Waveform unavailable.\n")
            return None
        
        try:
            if status_callback:
                status_callback("📊 Extracting audio waveform...\n")
            
            temp_audio = Path(video_path).parent / "_temp_audio.wav"
            ffmpeg_exe = ffmpeg_path or "ffmpeg"
            
            cmd = [
                str(ffmpeg_exe), "-y", "-i", str(video_path),
                "-vn", "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
                str(temp_audio)
            ]
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            subprocess.run(cmd, check=True, capture_output=True, startupinfo=startupinfo)
            
            # Load audio
            y, sr = librosa.load(str(temp_audio), sr=22050, mono=True)
            
            # Clean up
            if temp_audio.exists():
                temp_audio.unlink()
            
            if status_callback:
                status_callback("✅ Waveform extracted!\n")
            
            return y
            
        except Exception as e:
            if status_callback:
                status_callback(f"⚠️ Waveform extraction failed: {e}\n")
            temp_audio = Path(video_path).parent / "_temp_audio.wav"
            if temp_audio.exists():
                temp_audio.unlink()
            return None
    
    @staticmethod
    def downsample_waveform(waveform: np.ndarray, target_width: int) -> np.ndarray:
        """Downsample waveform to fit display width."""
        if len(waveform) <= target_width:
            return waveform
        
        samples_per_pixel = len(waveform) // target_width
        trimmed_length = target_width * samples_per_pixel
        waveform_trimmed = waveform[:trimmed_length]
        waveform_reshaped = waveform_trimmed.reshape(target_width, samples_per_pixel)
        downsampled = np.max(np.abs(waveform_reshaped), axis=1)
        
        return downsampled




# --- FRAME PREVIEW WIDGET ---
class FramePreview(ctk.CTkFrame):
    """Simple frame preview - shows single frame at a time."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.video_path = None
        self.cap = None
        self.current_time = 0
        self.duration = 0
        self.fps = 30
        self.audio_tracks = []  # List of audio tracks
        self.selected_audio_track = 0  # Selected track index
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup frame preview UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Preview canvas
        self.canvas = Canvas(self, bg="black", highlightthickness=0, width=640, height=360)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.placeholder = self.canvas.create_text(
            320, 180, text="No frame loaded\nClick timeline to preview",
            fill="gray", font=("Arial", 14), justify="center"
        )
        
        # Control buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, pady=(0, 10))
        
        ctk.CTkButton(btn_frame, text="⏮ -1s", width=70, command=lambda: self.jump_relative(-1),
                     font=("", 12)).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="◀ -0.1s", width=70, command=lambda: self.jump_relative(-0.1),
                     font=("", 10)).pack(side="left", padx=3)
        
        self.time_label = ctk.CTkLabel(btn_frame, text="00:00.00", font=("", 13, "bold"))
        self.time_label.pack(side="left", padx=15)
        
        ctk.CTkButton(btn_frame, text="▶ +0.1s", width=70, command=lambda: self.jump_relative(0.1),
                     font=("", 10)).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="⏭ +1s", width=70, command=lambda: self.jump_relative(1),
                     font=("", 12)).pack(side="left", padx=3)
        
        # Audio track selector
        audio_track_frame = ctk.CTkFrame(self, fg_color="gray30", corner_radius=5)
        audio_track_frame.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="ew")
        
        ctk.CTkLabel(audio_track_frame, text="🎵 Audio Track:",
                    font=("", 11, "bold")).pack(side="left", padx=10)
        
        self.audio_track_var = ctk.StringVar(value="No tracks detected")
        self.audio_track_menu = ctk.CTkOptionMenu(
            audio_track_frame, 
            values=["No tracks detected"],
            variable=self.audio_track_var,
            command=self.on_audio_track_change,
            width=300
        )
        self.audio_track_menu.pack(side="left", padx=10, pady=5, fill="x", expand=True)
        
        # Play button (opens ffplay)
        self.btn_play = ctk.CTkButton(self, text="▶ Play in FFplay", 
                                      command=self.play_external, height=35,
                                      fg_color="#2fb344", hover_color="#25a339")
        self.btn_play.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")
    
    def load_video(self, video_path: str, ffprobe_path: str = ""):
        """Load video for frame extraction and detect audio tracks."""
        if not CV2_AVAILABLE:
            return False
        
        try:
            if self.cap:
                self.cap.release()
            
            self.video_path = video_path
            self.cap = cv2.VideoCapture(video_path)
            
            if not self.cap.isOpened():
                return False
            
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.duration = total_frames / self.fps if self.fps > 0 else 0
            
            # Detect audio tracks
            self.detect_audio_tracks(video_path, ffprobe_path)
            
            # Show first frame
            self.show_frame_at_time(0)
            
            return True
        except:
            return False
    
    def detect_audio_tracks(self, video_path: str, ffprobe_path: str = ""):
        """Detect all audio tracks in the video."""
        try:
            ffprobe = ffprobe_path or "ffprobe"
            cmd = [str(ffprobe), "-v", "error", "-show_streams", "-select_streams", "a",
                  "-of", "json", video_path]
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(cmd, capture_output=True, text=True,
                                   encoding='utf-8', errors='ignore', startupinfo=startupinfo)
            
            streams = json.loads(result.stdout).get("streams", [])
            self.audio_tracks = []
            
            for i, stream in enumerate(streams):
                track_index = stream.get("index", i)
                codec = stream.get("codec_name", "unknown")
                channels = stream.get("channels", "?")
                sample_rate = stream.get("sample_rate", "?")
                language = stream.get("tags", {}).get("language", "und")
                
                # Format display name
                if channels == 1:
                    ch_str = "mono"
                elif channels == 2:
                    ch_str = "stereo"
                else:
                    ch_str = f"{channels}ch"
                
                try:
                    sr_khz = int(sample_rate) // 1000
                    sr_str = f"{sr_khz}kHz"
                except:
                    sr_str = "?"
                
                display_name = f"Track {i+1} (Stream {track_index}): {codec}, {ch_str}, {sr_str}"
                if language != "und":
                    display_name += f", {language}"
                
                self.audio_tracks.append({
                    "stream_index": track_index,
                    "audio_index": i,
                    "display_name": display_name,
                    "codec": codec,
                    "language": language
                })
            
            # Update UI
            if self.audio_tracks:
                track_names = [t["display_name"] for t in self.audio_tracks]
                self.audio_track_menu.configure(values=track_names)
                self.audio_track_var.set(track_names[0])
                self.selected_audio_track = 0
            else:
                self.audio_track_menu.configure(values=["No audio tracks found"])
                self.audio_track_var.set("No audio tracks found")
                
        except Exception as e:
            print(f"Error detecting audio tracks: {e}")
            self.audio_tracks = []
    
    def on_audio_track_change(self, selected_name: str):
        """Handle audio track selection change."""
        for i, track in enumerate(self.audio_tracks):
            if track["display_name"] == selected_name:
                self.selected_audio_track = i
                break
    
    def show_frame_at_time(self, time_seconds: float):
        """Extract and display frame at specific time."""
        if not self.cap or not self.cap.isOpened():
            return
        
        try:
            self.current_time = max(0, min(time_seconds, self.duration))
            frame_number = int(self.current_time * self.fps)
            
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = self.cap.read()
            
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize to fit canvas
                canvas_width = self.canvas.winfo_width() or 640
                canvas_height = self.canvas.winfo_height() or 360
                
                frame_height, frame_width = frame_rgb.shape[:2]
                scale = min(canvas_width / frame_width, canvas_height / frame_height)
                new_width = int(frame_width * scale)
                new_height = int(frame_height * scale)
                
                frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
                
                img = Image.fromarray(frame_resized)
                self.photo = ImageTk.PhotoImage(image=img)
                
                self.canvas.delete("all")
                self.canvas.create_image(canvas_width // 2, canvas_height // 2,
                                        image=self.photo, anchor="center")
                
                # Update time label
                self.time_label.configure(text=f"{timedelta(seconds=self.current_time)}"[:10])
        except Exception as e:
            print(f"Error showing frame: {e}")
    
    def jump_relative(self, seconds: float):
        """Jump forward or backward by specified seconds."""
        if self.video_path:
            new_time = self.current_time + seconds
            self.show_frame_at_time(new_time)
    
    def play_external(self):
        """Launch ffplay with ALL audio tracks mixed together."""
        if not self.video_path:
            messagebox.showwarning("Warning", "No video loaded!")
            return
        
        # Find ffmpeg and ffplay
        base_path = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
        ffplay_path = base_path / "ffplay.exe"
        ffmpeg_path = base_path / "ffmpeg.exe"
        
        if not ffplay_path.exists():
            ffplay_path = "ffplay"
        if not ffmpeg_path.exists():
            ffmpeg_path = "ffmpeg"
        
        try:
            # Build audio mix filter for all audio tracks
            num_audio_tracks = len(self.audio_tracks)
            
            if num_audio_tracks <= 1:
                # Only one track, play normally
                cmd = [str(ffplay_path), "-ss", str(self.current_time), "-autoexit", self.video_path]
                subprocess.Popen(cmd)
            else:
                # Multiple tracks - use FFmpeg to pipe mixed audio to ffplay
                # Build filter: [0:a:0][0:a:1]amix=inputs=2:duration=longest
                audio_inputs = "".join([f"[0:a:{i}]" for i in range(num_audio_tracks)])
                mix_filter = f"{audio_inputs}amix=inputs={num_audio_tracks}:duration=longest:dropout_transition=0[aout]"
                
                # FFmpeg command: mix audio and output to pipe
                ffmpeg_cmd = [
                    str(ffmpeg_path),
                    "-ss", str(self.current_time),
                    "-i", self.video_path,
                    "-filter_complex", f"{mix_filter}",
                    "-map", "0:v:0",  # Map video
                    "-map", "[aout]",  # Map mixed audio
                    "-c:v", "copy",  # Copy video codec
                    "-c:a", "aac",  # Encode audio as AAC
                    "-f", "matroska",  # Use matroska container for piping
                    "pipe:1"  # Output to stdout
                ]
                
                # FFplay command: read from stdin
                ffplay_cmd = [str(ffplay_path), "-autoexit", "-"]
                
                # Create pipe: ffmpeg -> ffplay
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, 
                                              stderr=subprocess.DEVNULL, startupinfo=startupinfo)
                ffplay_proc = subprocess.Popen(ffplay_cmd, stdin=ffmpeg_proc.stdout, 
                                              startupinfo=startupinfo)
                
                # Allow ffmpeg to receive SIGPIPE if ffplay exits
                if ffmpeg_proc.stdout:
                    ffmpeg_proc.stdout.close()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not launch ffplay: {e}")
    
    def cleanup(self):
        if self.cap:
            self.cap.release()




# --- INTERACTIVE TIMELINE WITH WAVEFORM ---
class InteractiveTimeline(ctk.CTkFrame):
    """
    Interactive timeline with waveform visualization.
    Click to navigate, drag playhead, show segments.
    """
    
    def __init__(self, master, on_time_click=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.segments = []
        self.duration = 0
        self.waveforms = {}  # Changed: Dict of track_index -> waveform data
        self.playhead_time = 0
        self.on_time_click = on_time_click
        self.dragging = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup timeline UI."""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(header, text="📊 Interactive Timeline", 
                    font=("", 14, "bold")).pack(side="left")
        
        self.info_label = ctk.CTkLabel(header, text="Load video and detect silence",
                                       font=("", 10))
        self.info_label.pack(side="right")
        
        # Time ruler
        self.ruler_canvas = Canvas(self, bg="gray25", height=25, highlightthickness=0)
        self.ruler_canvas.pack(fill="x", padx=10, pady=(0, 2))
        
        # Waveform display (increased height for multiple tracks)
        waveform_container = ctk.CTkFrame(self, fg_color="gray20", height=200)
        waveform_container.pack(fill="x", padx=10, pady=0)
        waveform_container.pack_propagate(False)
        
        self.waveform_canvas = Canvas(waveform_container, bg="#1a1a1a", 
                                      highlightthickness=0)
        self.waveform_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Segments display
        segments_container = ctk.CTkFrame(self, fg_color="gray20", height=60)
        segments_container.pack(fill="x", padx=10, pady=(2, 0))
        segments_container.pack_propagate(False)
        
        self.segments_canvas = Canvas(segments_container, bg="#1a1a1a",
                                      highlightthickness=0)
        self.segments_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Bind mouse events for interaction
        self.waveform_canvas.bind("<Button-1>", self.on_canvas_click)
        self.waveform_canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.waveform_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        self.segments_canvas.bind("<Button-1>", self.on_canvas_click)
        self.segments_canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.segments_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
    
    def update_timeline(self, segments: List[Tuple[float, float]], duration: float,
                       waveforms: dict = None):
        """Update timeline with segments and multi-track waveforms."""
        self.segments = segments
        self.duration = duration
        self.waveforms = waveforms if waveforms is not None else {}
        self.playhead_time = 0
        
        if not segments or duration == 0:
            return
        
        self.draw_timeline()
        
        # Update info
        num_tracks = len(self.waveforms)
        total_audible = sum(e - s for s, e in segments)
        total_silence = duration - total_audible
        percent_kept = (total_audible / duration * 100) if duration > 0 else 0
        
        self.info_label.configure(
            text=f"Tracks: {num_tracks} | Keep: {timedelta(seconds=int(total_audible))} | "
                 f"Remove: {timedelta(seconds=int(total_silence))} | "
                 f"{percent_kept:.1f}% retained"
        )
    
    def draw_timeline(self):
        """Draw complete timeline with waveform and segments."""
        if self.duration == 0:
            return
        
        # Clear canvases
        self.ruler_canvas.delete("all")
        self.waveform_canvas.delete("all")
        self.segments_canvas.delete("all")
        
        # Get widths
        ruler_width = self.ruler_canvas.winfo_width() or 800
        wave_width = self.waveform_canvas.winfo_width() or 800
        wave_height = self.waveform_canvas.winfo_height() or 200
        seg_width = self.segments_canvas.winfo_width() or 800
        seg_height = 60
        
        # Draw time ruler
        self.draw_ruler(ruler_width)
        
        # Draw waveforms (multiple tracks)
        if self.waveforms:
            self.draw_multi_waveforms(wave_width, wave_height)
        
        # Draw segments
        self.draw_segments(seg_width, seg_height)
        
        # Draw playhead
        self.draw_playhead(wave_width, wave_height, seg_width, seg_height)
    
    def draw_ruler(self, width):
        """Draw time ruler."""
        self.ruler_canvas.create_rectangle(0, 0, width, 25, fill="gray25", outline="")
        
        # Determine interval
        if self.duration <= 60:
            interval = 5
        elif self.duration <= 300:
            interval = 30
        elif self.duration <= 3600:
            interval = 60
        else:
            interval = 300
        
        num_intervals = int(self.duration / interval) + 1
        for i in range(num_intervals):
            time_sec = i * interval
            if time_sec > self.duration:
                break
            
            x = (time_sec / self.duration) * width
            
            hours = int(time_sec // 3600)
            minutes = int((time_sec % 3600) // 60)
            seconds = int(time_sec % 60)
            
            if hours > 0:
                time_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                time_str = f"{minutes}:{seconds:02d}"
            
            tick_height = 15 if i % 5 == 0 else 10
            self.ruler_canvas.create_line(x, 25 - tick_height, x, 25,
                                         fill="white", width=1)
            
            if i % 5 == 0 or num_intervals <= 10:
                self.ruler_canvas.create_text(x, 5, text=time_str, fill="white",
                                             font=("", 8), anchor="n")
    
    def draw_multi_waveforms(self, width, height):
        """Draw multiple audio waveforms stacked vertically."""
        if not self.waveforms:
            return
        
        # Different colors for each track
        track_colors = ["#4a9eff", "#ff6b6b", "#51cf66", "#ffd43b", "#ff8c00", "#ba68c8"]
        track_colors_dim = ["#2d5f99", "#993f3f", "#307a3d", "#997a23", "#99540a", "#6d3e75"]
        
        num_tracks = len(self.waveforms)
        track_height = height / num_tracks
        
        sorted_tracks = sorted(self.waveforms.items())  # Sort by track index
        
        for idx, (track_index, waveform_data) in enumerate(sorted_tracks):
            waveform = waveform_data["waveform"]
            track_info = waveform_data["track_info"]
            
            # Downsample waveform to fit width
            downsampled = WaveformGenerator.downsample_waveform(waveform, width)
            
            # Normalize
            if len(downsampled) > 0:
                max_val = np.max(np.abs(downsampled))
                if max_val > 0:
                    downsampled = downsampled / max_val
            
            # Calculate position for this track
            track_y_start = idx * track_height
            track_center_y = track_y_start + track_height / 2
            
            # Get colors
            color_idx = idx % len(track_colors)
            active_color = track_colors[color_idx]
            dim_color = track_colors_dim[color_idx]
            
            # Draw separator line
            if idx > 0:
                self.waveform_canvas.create_line(0, track_y_start, width, track_y_start,
                                                fill="#333333", width=1)
            
            # Draw track label
            label_text = f"Track {track_index + 1}"
            self.waveform_canvas.create_text(5, track_y_start + 5, text=label_text,
                                            anchor="nw", fill="white", font=("", 8, "bold"))
            
            # Draw waveform
            for i, val in enumerate(downsampled):
                amp = int(val * (track_height / 2 - 10))
                x = i
                
                # Determine color based on segments
                time_at_x = (i / width) * self.duration
                in_segment = any(s <= time_at_x <= e for s, e in self.segments)
                color = active_color if in_segment else dim_color
                
                self.waveform_canvas.create_line(x, track_center_y - amp, x, track_center_y + amp,
                                                fill=color, width=1)
    
    def draw_segments(self, width, height):
        """Draw segment visualization."""
        # Background (silence)
        self.segments_canvas.create_rectangle(0, 0, width, height, fill="#2b2b2b", outline="")
        
        # Audible segments (green)
        for start, end in self.segments:
            x1 = (start / self.duration) * width
            x2 = (end / self.duration) * width
            
            self.segments_canvas.create_rectangle(x1, 0, x2, height,
                                                 fill="#2fb344", outline="")
            self.segments_canvas.create_line(x1, 0, x1, height, fill="#25a339", width=2)
            self.segments_canvas.create_line(x2, 0, x2, height, fill="#25a339", width=2)
    
    def draw_playhead(self, wave_width, wave_height, seg_width, seg_height):
        """Draw red playhead at current position."""
        wave_x = (self.playhead_time / self.duration) * wave_width if self.duration > 0 else 0
        seg_x = (self.playhead_time / self.duration) * seg_width if self.duration > 0 else 0
        
        # Playhead on waveform
        self.waveform_canvas.create_line(wave_x, 0, wave_x, wave_height,
                                        fill="#ff4444", width=3, tags="playhead")
        
        # Playhead on segments
        self.segments_canvas.create_line(seg_x, 0, seg_x, seg_height,
                                        fill="#ff4444", width=3, tags="playhead")
    
    def on_canvas_click(self, event):
        """Handle click on timeline."""
        self.dragging = True
        self.update_playhead_from_click(event.x, event.widget.winfo_width())
    
    def on_canvas_drag(self, event):
        """Handle dragging on timeline."""
        if self.dragging:
            self.update_playhead_from_click(event.x, event.widget.winfo_width())
    
    def on_canvas_release(self, event):
        """Handle mouse release."""
        self.dragging = False
    
    def update_playhead_from_click(self, x, width):
        """Update playhead position from click."""
        if self.duration == 0 or width == 0:
            return
        
        # Calculate time
        self.playhead_time = max(0, min((x / width) * self.duration, self.duration))
        
        # Redraw playhead
        wave_width = self.waveform_canvas.winfo_width() or 800
        wave_height = self.waveform_canvas.winfo_height() or 80
        seg_width = self.segments_canvas.winfo_width() or 800
        seg_height = self.segments_canvas.winfo_height() or 60
        
        # Remove old playheads
        self.waveform_canvas.delete("playhead")
        self.segments_canvas.delete("playhead")
        
        # Draw new playhead
        self.draw_playhead(wave_width, wave_height, seg_width, seg_height)
        
        # Callback
        if self.on_time_click:
            self.on_time_click(self.playhead_time)




def process_video_logic(video_path: str, output_dir: str, output_format: str, video_params: str, 
                       all_audio_tracks: list[dict], silence_track_index: int, 
                       ffmpeg_path: str, ffprobe_path: str, settings: dict,
                       status_callback, progress_callback=None,
                       trim_start: float = 0, trim_end: Optional[float] = None,
                       segments: Optional[list[tuple[float, float]]] = None):
    """Process video with silence removal and optional trimming."""
    video_file = Path(video_path)
    output_path = Path(output_dir)
    temp_dir = output_path / "temp_silence_cutter"
    temp_dir.mkdir(exist_ok=True)
    output_file = output_path / f"{video_file.stem}_final.{output_format.lower()}"

    if output_file.exists():
        status_callback(f"⏭️ Output file '{output_file.name}' already exists. Skipping.\n")
        return

    status_callback("-" * 40 + "\n")
    status_callback(f"🎬 Starting processing for: {video_file.name}\n")
    
    duration = get_video_duration(video_file, ffprobe_path, status_callback)
    if duration == 0.0: 
        return
    
    # Apply trim_end if specified
    effective_duration = trim_end if trim_end is not None else duration

    # Use provided segments or detect them
    if segments is None:
        ffmpeg_log = detect_silence(video_file, silence_track_index, ffmpeg_path, settings, status_callback, trim_start, trim_end)
        segments = parse_segments(ffmpeg_log, effective_duration, settings, status_callback, trim_start)
    
    if not segments:
        status_callback(f"⚠️ No valid audible segments found. Skipping.\n")
        return

    select_filter = "+".join([f"between(t,{s},{e})" for s, e in segments])
    video_args = shlex.split(video_params)
    
    audio_params = "-c:a aac -b:a 192k" if output_format.lower() == "mp4" else "-c:a pcm_s16le"
    audio_args = shlex.split(audio_params)

    filter_complex_parts = [f"[0:v]select='{select_filter}',setpts=N/FRAME_RATE/TB[v]"]
    map_args = ["[v]"]
    for i, track in enumerate(all_audio_tracks):
        stream_index = track['index']
        filter_complex_parts.append(f"[0:{stream_index}]aselect='{select_filter}',asetpts=N/SR/TB[a{i}]")
        map_args.append(f"[a{i}]")
    filter_complex = ";".join(filter_complex_parts)

    ffmpeg_executable = ffmpeg_path or "ffmpeg"
    base_cmd = [str(ffmpeg_executable), "-y", "-hide_banner"]
    
    # Add progress reporting
    if progress_callback:
        base_cmd.extend(["-progress", "pipe:1", "-stats_period", "0.5"])
    
    base_cmd.extend(["-i", str(video_file)])
    
    temp_filter_file = None
    filter_length_threshold = settings.get("filter_length_threshold", 4096)
    if len(filter_complex) > filter_length_threshold:
        status_callback("🛠️ Filter string is very long. Using a temporary script file.\n")
        temp_filter_file = temp_dir / f"{video_file.stem}_filter.txt"
        temp_filter_file.write_text(filter_complex, encoding='utf-8')
        filter_cmd = ["-filter_complex_script", str(temp_filter_file)]
    else:
        filter_cmd = ["-filter_complex", filter_complex]

    final_map_args = [arg for m in map_args for arg in ("-map", m)]
    if output_format.lower() == "mp4":
        video_args.extend(["-pix_fmt", "yuv420p"])

    cmd = base_cmd + filter_cmd + final_map_args + video_args + audio_args + [str(output_file)]
    status_callback(f"⚙️ Running FFmpeg... This may take a while.\n")
    
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        if progress_callback:
            # Run with progress monitoring
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                     text=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
            
            total_duration = sum(e - s for s, e in segments)
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    progress_data = parse_ffmpeg_progress(output)
                    if progress_data and 'time' in progress_data:
                        current_time = progress_data['time']
                        percentage = min(100, (current_time / total_duration) * 100) if total_duration > 0 else 0
                        speed = progress_data.get('speed', 0)
                        
                        if speed > 0:
                            remaining_time = (total_duration - current_time) / speed
                            eta = str(timedelta(seconds=int(remaining_time)))
                        else:
                            eta = "Calculating..."
                        
                        progress_callback(percentage, eta, speed)
            
            return_code = process.wait()
            if return_code != 0:
                stderr = process.stderr.read()
                raise subprocess.CalledProcessError(return_code, cmd, stderr=stderr)
        else:
            subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
        
        status_callback(f"✅ Successfully created: {output_file.name}\n")
        status_callback(f"📍 Saved to: {output_file}\n")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        status_callback(f"❌ FFmpeg failed for {video_file.name}!\n")
        if isinstance(e, subprocess.CalledProcessError):
            status_callback(f"   FFmpeg stderr:\n{e.stderr}\n")
        else:
            status_callback(f"   Error: '{ffmpeg_executable}' not found.\n")
    finally:
        if temp_filter_file and temp_filter_file.exists(): 
            temp_filter_file.unlink()
        try:
            if temp_dir.exists() and not any(temp_dir.iterdir()): 
                temp_dir.rmdir()
        except OSError: 
            pass



# --- BATCH QUEUE ITEM ---
class BatchQueueItem(ctk.CTkFrame):
    """Individual item in the batch queue."""
    
    def __init__(self, master, video_path: str, on_remove, **kwargs):
        super().__init__(master, fg_color="gray25", **kwargs)
        self.video_path = video_path
        self.on_remove = on_remove
        self.status = "pending"  # pending, processing, completed, failed
        
        # Layout
        self.grid_columnconfigure(1, weight=1)
        
        # Status indicator
        self.status_label = ctk.CTkLabel(self, text="⏸", font=("", 16), width=30)
        self.status_label.grid(row=0, column=0, padx=5, pady=5)
        
        # File name
        file_name = Path(video_path).name
        self.name_label = ctk.CTkLabel(self, text=file_name, anchor="w")
        self.name_label.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Remove button
        self.remove_btn = ctk.CTkButton(self, text="✕", width=30, command=self.remove_clicked,
                                       fg_color="transparent", hover_color="red")
        self.remove_btn.grid(row=0, column=2, padx=5, pady=5)
    
    def set_status(self, status: str):
        """Update status indicator."""
        self.status = status
        status_icons = {
            "pending": "⏸",
            "processing": "▶️",
            "completed": "✅",
            "failed": "❌"
        }
        self.status_label.configure(text=status_icons.get(status, "⏸"))
    
    def remove_clicked(self):
        """Handle remove button click."""
        if self.status != "processing":
            self.on_remove(self)





# --- MAIN APPLICATION (V3 INTEGRATED) ---
# This is the v1 app structure. You can enhance it by:
# 1. Adding a Preview tab with InteractiveTimeline and FramePreview
# 2. Syncing the detected segments between tabs
# 3. Using WaveformGenerator for timeline visualization

class VideoProductionApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🎬 Video Production Suite v3.0 - Professional Edition")
        self.geometry("1280x800")
        self.minsize(1100, 700)  # Set minimum window size
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Try to center window on screen
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 1280) // 2
        y = (screen_height - 800) // 2
        self.geometry(f"1280x800+{x}+{y}")
        
        # State variables
        self.video_path = ""
        self.save_path = ""
        self.ffmpeg_path = ""
        self.ffprobe_path = ""
        self.ffplay_path = ""
        self.available_tracks = []
        self.detected_segments = []
        self.current_duration = 0
        self.batch_queue = []
        self.processing = False
        
        # Settings manager
        self.settings = SettingsManager()
        
        self.setup_paths()
        self.create_ui()
        self.show_initial_status()
    
    def setup_paths(self):
        """Setup FFmpeg paths."""
        base_path = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
        self.ffmpeg_path = base_path / "ffmpeg.exe"
        self.ffprobe_path = base_path / "ffprobe.exe"
        self.ffplay_path = base_path / "ffplay.exe"
        if not self.ffmpeg_path.exists(): self.ffmpeg_path = ""
        if not self.ffprobe_path.exists(): self.ffprobe_path = ""
        if not self.ffplay_path.exists(): self.ffplay_path = ""
    
    def create_ui(self):
        """Create the main UI with tabs."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create tabview with enhanced styling
        self.tabview = ctk.CTkTabview(
            self, 
            corner_radius=15,
            border_width=2,
            border_color=AppColors.BORDER,
            segmented_button_fg_color=AppColors.BG_LIGHT,
            segmented_button_selected_color=AppColors.PRIMARY,
            segmented_button_selected_hover_color=AppColors.PRIMARY_HOVER,
            text_color=AppColors.TEXT_PRIMARY
        )
        self.tabview.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        
        # Add tabs
        self.tab_preview = self.tabview.add("Preview & Analysis")
        tab_main_raw = self.tabview.add("Main")
        self.tab_advanced = self.tabview.add("Advanced Settings")
        self.tab_batch = self.tabview.add("Batch Queue")
        
        # Make main tab scrollable
        tab_main_raw.grid_columnconfigure(0, weight=1)
        tab_main_raw.grid_rowconfigure(0, weight=1)
        self.tab_main = ctk.CTkScrollableFrame(tab_main_raw, fg_color="transparent")
        self.tab_main.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.tab_main.grid_columnconfigure(0, weight=1)
        
        # Setup each tab
        self.setup_preview_tab()
        self.setup_main_tab()
        self.setup_advanced_tab()
        self.setup_batch_tab()
    
    def setup_preview_tab(self):
        """Setup preview tab with interactive timeline and frame preview."""
        self.tab_preview.grid_columnconfigure(0, weight=3)
        self.tab_preview.grid_columnconfigure(1, weight=2)
        self.tab_preview.grid_rowconfigure(1, weight=1)
        
        # Header with controls - Enhanced styling
        header_frame = ctk.CTkFrame(
            self.tab_preview, 
            fg_color=AppColors.BG_CARD, 
            corner_radius=12,
            border_width=1,
            border_color=AppColors.BORDER,
            height=110
        )
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=12)
        header_frame.grid_columnconfigure(1, weight=1)
        header_frame.grid_propagate(False)
        
        # Title with gradient effect (using bold font and primary color)
        title_label = ctk.CTkLabel(
            header_frame, 
            text="🎬 Smart Preview & Analysis", 
            font=("Segoe UI", 20, "bold"),
            text_color=AppColors.PRIMARY
        )
        title_label.grid(row=0, column=0, padx=20, pady=(12, 5), sticky="w")
        
        # Control buttons with enhanced styling
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=20, pady=10, sticky="e")
        
        load_btn = ctk.CTkButton(
            btn_frame, 
            text="📁 Load Video", 
            command=self.preview_load_video,
            height=38, 
            width=130, 
            font=("Segoe UI", 13, "bold"),
            fg_color=AppColors.PRIMARY,
            hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=8
        )
        load_btn.pack(side="left", padx=5)
        
        # Track selector for silence detection with improved styling
        ctk.CTkLabel(
            btn_frame, 
            text="Detect silence in:", 
            font=("Segoe UI", 11),
            text_color=AppColors.TEXT_SECONDARY
        ).pack(side="left", padx=(15, 5))
        
        self.preview_track_selector_var = ctk.StringVar(value="Track 1")
        self.preview_track_selector = ctk.CTkOptionMenu(
            btn_frame, 
            variable=self.preview_track_selector_var,
            values=["Track 1"], 
            width=110, 
            height=38,
            state="disabled",
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=8,
            font=("Segoe UI", 11)
        )
        self.preview_track_selector.pack(side="left", padx=5)
        
        detect_btn = ctk.CTkButton(
            btn_frame, 
            text="🔍 Detect Silence", 
            command=self.preview_detect_silence,
            height=38, 
            width=150, 
            font=("Segoe UI", 13, "bold"),
            fg_color=AppColors.INFO,
            hover_color=AppColors.PRIMARY_DARK,
            corner_radius=8
        )
        detect_btn.pack(side="left", padx=5)
        
        # Status label with improved styling
        self.preview_status = ctk.CTkLabel(
            header_frame, 
            text="📂 Load a video to begin analysis...",
            font=("Segoe UI", 11),
            anchor="w", 
            text_color=AppColors.TEXT_MUTED
        )
        self.preview_status.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 12), sticky="ew")
        
        # Interactive Timeline (left side) - Enhanced styling
        self.preview_timeline = InteractiveTimeline(
            self.tab_preview, 
            fg_color=AppColors.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=AppColors.BORDER,
            on_time_click=self.on_preview_timeline_click
        )
        self.preview_timeline.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 12))
        
        # Frame Preview (right side) - Enhanced styling
        self.preview_frame = FramePreview(
            self.tab_preview,
            fg_color=AppColors.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=AppColors.BORDER
        )
        self.preview_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))
    
    def setup_main_tab(self):
        """Setup the main tab UI."""
        self.tab_main.grid_columnconfigure(0, weight=1)
        
        # Create a centered container with max width
        content_frame = ctk.CTkFrame(self.tab_main, fg_color="transparent")
        content_frame.grid(row=0, column=0, sticky="n")
        content_frame.configure(width=900)  # Max width for content
        
        # Video selection with enhanced styling
        self.label_video = ctk.CTkLabel(
            content_frame, 
            text="No video file selected.", 
            anchor="w", 
            font=("Segoe UI", 11), 
            justify="left", 
            width=850,
            text_color=AppColors.TEXT_MUTED
        )
        self.button_video = ctk.CTkButton(
            content_frame, 
            text="📁  Select Video File", 
            command=self.select_video_file, 
            height=42, 
            font=("Segoe UI", 14, "bold"), 
            width=850,
            fg_color=AppColors.PRIMARY,
            hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=10
        )
        
        # Save destination with enhanced styling
        self.label_save = ctk.CTkLabel(
            content_frame, 
            text="No save destination selected.", 
            anchor="w", 
            font=("Segoe UI", 11), 
            justify="left", 
            width=850,
            text_color=AppColors.TEXT_MUTED
        )
        self.button_save = ctk.CTkButton(
            content_frame, 
            text="💾  Select Save Destination", 
            command=self.select_save_destination, 
            height=42, 
            font=("Segoe UI", 14, "bold"), 
            width=850,
            fg_color=AppColors.PRIMARY,
            hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=10
        )
        
        # Audio track selection with enhanced styling
        self.audio_track_var = ctk.StringVar(value="Select a video first...")
        self.label_audio_track = ctk.CTkLabel(
            content_frame, 
            text="🎧 Audio Track for Silence Detection:", 
            font=("Segoe UI", 13, "bold"), 
            width=850, 
            anchor="w",
            text_color=AppColors.TEXT_PRIMARY
        )
        self.option_audio_track = ctk.CTkOptionMenu(
            content_frame, 
            values=["Select a video first..."], 
            variable=self.audio_track_var, 
            state="disabled", 
            height=38, 
            width=850,
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=8,
            font=("Segoe UI", 12)
        )
        
        # Audio track information panel with enhanced styling
        audio_info_frame = ctk.CTkFrame(
            content_frame, 
            fg_color=AppColors.BG_CARD, 
            corner_radius=10,
            border_width=1,
            border_color=AppColors.BORDER,
            width=850
        )
        audio_info_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            audio_info_frame, 
            text="🎵 Audio Track Details", 
            font=("Segoe UI", 13, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=0, column=0, padx=12, pady=(12, 8), sticky="w")
        
        # Button to analyze tracks with enhanced styling
        self.button_analyze_tracks = ctk.CTkButton(
            audio_info_frame, 
            text="🔍 Analyze All Tracks", 
            command=self.analyze_all_tracks, 
            height=32, 
            width=160,
            fg_color=AppColors.INFO,
            hover_color=AppColors.PRIMARY_DARK,
            corner_radius=8,
            font=("Segoe UI", 11, "bold"),
            state="disabled"
        )
        self.button_analyze_tracks.grid(row=0, column=1, padx=12, pady=(12, 8), sticky="e")
        
        self.audio_info_textbox = ctk.CTkTextbox(
            audio_info_frame, 
            height=100, 
            font=("Consolas", 10), 
            fg_color=AppColors.BG_DARK,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=6,
            state="disabled"
        )
        self.audio_info_textbox.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")
        
        # Trim settings
        trim_frame = ctk.CTkFrame(content_frame, fg_color="transparent", width=850)
        trim_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(trim_frame, text="Trim Start (seconds):", font=("", 11)).grid(row=0, column=0, sticky="w", padx=5)
        self.trim_start_entry = ctk.CTkEntry(trim_frame, placeholder_text="0")
        self.trim_start_entry.grid(row=1, column=0, sticky="ew", padx=5)
        
        ctk.CTkLabel(trim_frame, text="Trim End (seconds, optional):", font=("", 11)).grid(row=0, column=1, sticky="w", padx=5)
        self.trim_end_entry = ctk.CTkEntry(trim_frame, placeholder_text="Leave empty for full video")
        self.trim_end_entry.grid(row=1, column=1, sticky="ew", padx=5)
        
        # Encoder and format selection with enhanced styling
        options_frame = ctk.CTkFrame(content_frame, fg_color="transparent", width=850)
        options_frame.grid_columnconfigure((0, 1), weight=1)
        
        encoder_frame = ctk.CTkFrame(
            options_frame, 
            fg_color=AppColors.BG_CARD, 
            corner_radius=10,
            border_width=1,
            border_color=AppColors.BORDER
        )
        encoder_frame.grid(row=0, column=0, sticky="ew", padx=5)
        ctk.CTkLabel(
            encoder_frame, 
            text="🎮 Video Encoder:", 
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).pack(pady=(12, 8))
        self.encoder_var = ctk.StringVar(value="Detecting...")
        self.option_encoder = ctk.CTkOptionMenu(
            encoder_frame, 
            values=["Detecting..."], 
            variable=self.encoder_var, 
            state="disabled", 
            height=36,
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=8,
            font=("Segoe UI", 11)
        )
        self.option_encoder.pack(padx=12, pady=(0, 12), fill="x")
        
        format_frame = ctk.CTkFrame(
            options_frame, 
            fg_color=AppColors.BG_CARD, 
            corner_radius=10,
            border_width=1,
            border_color=AppColors.BORDER
        )
        format_frame.grid(row=0, column=1, sticky="ew", padx=5)
        ctk.CTkLabel(
            format_frame, 
            text="📺 Output Format:", 
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).pack(pady=(12, 8))
        self.format_var = ctk.StringVar(value="MP4")
        self.option_format = ctk.CTkOptionMenu(
            format_frame, 
            values=["MP4", "MKV"], 
            variable=self.format_var, 
            height=36,
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=8,
            font=("Segoe UI", 11)
        )
        self.option_format.pack(padx=12, pady=(0, 12), fill="x")
        
        # Preview button with enhanced styling
        self.button_preview = ctk.CTkButton(
            content_frame, 
            text="👁  Preview Video", 
            command=self.preview_video, 
            height=40, 
            fg_color=AppColors.BG_LIGHT, 
            hover_color=AppColors.BG_CARD_HOVER,
            border_width=2,
            border_color=AppColors.BORDER,
            width=850,
            font=("Segoe UI", 13, "bold"),
            corner_radius=10
        )
        
        # Detect silence button with enhanced styling
        self.button_detect = ctk.CTkButton(
            content_frame, 
            text="🔍  Detect Silence", 
            command=self.detect_silence_preview, 
            height=40, 
            fg_color=AppColors.INFO, 
            hover_color=AppColors.PRIMARY_DARK,
            width=850,
            font=("Segoe UI", 13, "bold"),
            corner_radius=10
        )
        
        # Timeline preview (using v1-style simple timeline) with enhanced styling
        # Note: Full interactive timeline is in the Preview tab
        self.timeline = ctk.CTkFrame(
            content_frame, 
            fg_color=AppColors.BG_CARD, 
            corner_radius=10,
            border_width=1,
            border_color=AppColors.BORDER,
            height=100
        )
        self.timeline_label = ctk.CTkLabel(
            self.timeline, 
            text="📊 Click 'Detect Silence' to see timeline preview\n💡 Use Preview tab for interactive timeline with waveforms", 
            font=("Segoe UI", 11),
            text_color=AppColors.TEXT_MUTED
        )
        self.timeline_label.pack(expand=True)
        
        # Process button with progress - Enhanced styling
        process_frame = ctk.CTkFrame(
            content_frame, 
            fg_color=AppColors.BG_CARD, 
            corner_radius=10,
            border_width=1,
            border_color=AppColors.BORDER,
            width=850
        )
        process_frame.grid_columnconfigure(0, weight=1)
        
        self.button_cut = ctk.CTkButton(
            process_frame, 
            text="✂️  Cut Silences & Export", 
            command=self.start_cutting_thread, 
            height=50, 
            font=("Segoe UI", 16, "bold"), 
            fg_color=AppColors.SUCCESS, 
            hover_color=AppColors.SUCCESS_HOVER,
            corner_radius=10
        )
        
        self.progress_bar = ctk.CTkProgressBar(
            process_frame, 
            height=24,
            corner_radius=6,
            border_width=1,
            border_color=AppColors.BORDER,
            progress_color=AppColors.SUCCESS
        )
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(
            process_frame, 
            text="⏹ Ready to process", 
            font=("Segoe UI", 11),
            text_color=AppColors.TEXT_SECONDARY
        )
        
        # Status textbox with enhanced styling
        self.status_textbox = ctk.CTkTextbox(
            self.tab_main, 
            state="disabled", 
            fg_color=AppColors.BG_DARK, 
            font=("Consolas", 10), 
            corner_radius=10,
            border_width=1,
            border_color=AppColors.BORDER,
            height=150
        )
        
        # Layout
        row = 0
        self.button_video.grid(row=row, column=0, padx=15, pady=(10, 3), sticky="ew")
        row += 1
        self.label_video.grid(row=row, column=0, padx=15, pady=(0, 8), sticky="w")
        row += 1
        self.button_save.grid(row=row, column=0, padx=15, pady=3, sticky="ew")
        row += 1
        self.label_save.grid(row=row, column=0, padx=15, pady=(0, 8), sticky="w")
        row += 1
        self.label_audio_track.grid(row=row, column=0, padx=15, pady=(5, 2), sticky="w")
        row += 1
        self.option_audio_track.grid(row=row, column=0, padx=15, pady=(0, 3), sticky="ew")
        row += 1
        audio_info_frame.grid(row=row, column=0, padx=15, pady=(0, 5), sticky="ew")
        row += 1
        trim_frame.grid(row=row, column=0, padx=15, pady=3, sticky="ew")
        row += 1
        options_frame.grid(row=row, column=0, padx=15, pady=5, sticky="ew")
        row += 1
        self.button_preview.grid(row=row, column=0, padx=15, pady=3, sticky="ew")
        row += 1
        self.button_detect.grid(row=row, column=0, padx=15, pady=3, sticky="ew")
        row += 1
        self.timeline.grid(row=row, column=0, padx=15, pady=5, sticky="ew")
        row += 1
        process_frame.grid(row=row, column=0, padx=15, pady=8, sticky="ew")
        self.button_cut.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=4)
        self.progress_label.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        row += 1
        self.status_textbox.grid(row=row, column=0, padx=15, pady=(8, 15), sticky="ew")
    
    def setup_advanced_tab(self):
        """Setup advanced settings tab with enhanced styling."""
        self.tab_advanced.grid_columnconfigure(0, weight=1)
        self.tab_advanced.grid_rowconfigure(1, weight=1)
        
        # Title with enhanced styling
        title_label = ctk.CTkLabel(
            self.tab_advanced, 
            text="⚙️ Silence Detection Parameters", 
            font=("Segoe UI", 20, "bold"),
            text_color=AppColors.PRIMARY
        )
        title_label.grid(row=0, column=0, pady=25)
        
        # Settings frame with enhanced styling
        settings_frame = ctk.CTkFrame(
            self.tab_advanced, 
            fg_color=AppColors.BG_CARD, 
            corner_radius=12,
            border_width=1,
            border_color=AppColors.BORDER
        )
        settings_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=15)
        settings_frame.grid_columnconfigure(1, weight=1)
        
        row = 0
        
        # Silence threshold with enhanced styling
        ctk.CTkLabel(
            settings_frame, 
            text="🔇 Silence Threshold (dB):", 
            font=("Segoe UI", 13, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=row, column=0, padx=25, pady=18, sticky="w")
        self.silence_db_var = ctk.StringVar(value=str(self.settings.get("silence_db", -40)))
        self.silence_db_entry = ctk.CTkEntry(
            settings_frame, 
            textvariable=self.silence_db_var, 
            width=120,
            height=36,
            font=("Segoe UI", 12),
            corner_radius=8,
            border_width=2,
            border_color=AppColors.BORDER
        )
        self.silence_db_entry.grid(row=row, column=1, padx=25, pady=18, sticky="w")
        ctk.CTkLabel(
            settings_frame, 
            text="💡 More negative = quieter", 
            font=("Segoe UI", 10), 
            text_color=AppColors.TEXT_MUTED
        ).grid(row=row, column=2, padx=15, pady=18, sticky="w")
        row += 1
        
        # Silence duration with enhanced styling
        ctk.CTkLabel(
            settings_frame, 
            text="⏱ Minimum Silence Duration (s):", 
            font=("Segoe UI", 13, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=row, column=0, padx=25, pady=18, sticky="w")
        self.silence_duration_var = ctk.StringVar(value=str(self.settings.get("silence_duration", 0.7)))
        self.silence_duration_entry = ctk.CTkEntry(
            settings_frame, 
            textvariable=self.silence_duration_var, 
            width=120,
            height=36,
            font=("Segoe UI", 12),
            corner_radius=8,
            border_width=2,
            border_color=AppColors.BORDER
        )
        self.silence_duration_entry.grid(row=row, column=1, padx=25, pady=18, sticky="w")
        ctk.CTkLabel(
            settings_frame, 
            text="💡 Shorter = more cuts", 
            font=("Segoe UI", 10), 
            text_color=AppColors.TEXT_MUTED
        ).grid(row=row, column=2, padx=15, pady=18, sticky="w")
        row += 1
        
        # Padding before with enhanced styling
        ctk.CTkLabel(
            settings_frame, 
            text="⏮ Padding Before Cut (s):", 
            font=("Segoe UI", 13, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=row, column=0, padx=25, pady=18, sticky="w")
        self.pad_before_var = ctk.StringVar(value=str(self.settings.get("pad_before", 0.1)))
        self.pad_before_entry = ctk.CTkEntry(
            settings_frame, 
            textvariable=self.pad_before_var, 
            width=120,
            height=36,
            font=("Segoe UI", 12),
            corner_radius=8,
            border_width=2,
            border_color=AppColors.BORDER
        )
        self.pad_before_entry.grid(row=row, column=1, padx=25, pady=18, sticky="w")
        ctk.CTkLabel(
            settings_frame, 
            text="💡 Keep more before speech", 
            font=("Segoe UI", 10), 
            text_color=AppColors.TEXT_MUTED
        ).grid(row=row, column=2, padx=15, pady=18, sticky="w")
        row += 1
        
        # Padding after with enhanced styling
        ctk.CTkLabel(
            settings_frame, 
            text="⏭ Padding After Cut (s):", 
            font=("Segoe UI", 13, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=row, column=0, padx=25, pady=18, sticky="w")
        self.pad_after_var = ctk.StringVar(value=str(self.settings.get("pad_after", 0.0)))
        self.pad_after_entry = ctk.CTkEntry(
            settings_frame, 
            textvariable=self.pad_after_var, 
            width=120,
            height=36,
            font=("Segoe UI", 12),
            corner_radius=8,
            border_width=2,
            border_color=AppColors.BORDER
        )
        self.pad_after_entry.grid(row=row, column=1, padx=25, pady=18, sticky="w")
        ctk.CTkLabel(
            settings_frame, 
            text="💡 Keep more after speech", 
            font=("Segoe UI", 10), 
            text_color=AppColors.TEXT_MUTED
        ).grid(row=row, column=2, padx=15, pady=18, sticky="w")
        row += 1
        
        # Add some vertical spacing
        settings_frame.grid_rowconfigure(row, weight=1)
        row += 1
        
        # Buttons with enhanced styling
        button_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        button_frame.grid(row=row, column=0, columnspan=3, pady=25)
        
        save_btn = ctk.CTkButton(
            button_frame, 
            text="💾  Save Settings", 
            command=self.save_advanced_settings,
            height=42, 
            width=180, 
            fg_color=AppColors.SUCCESS,
            hover_color=AppColors.SUCCESS_HOVER,
            font=("Segoe UI", 13, "bold"),
            corner_radius=10
        )
        save_btn.pack(side="left", padx=10)
        
        reset_btn = ctk.CTkButton(
            button_frame, 
            text="↺  Reset to Defaults", 
            command=self.reset_advanced_settings,
            height=42, 
            width=180, 
            fg_color=AppColors.BG_LIGHT,
            hover_color=AppColors.BG_CARD_HOVER,
            border_width=2,
            border_color=AppColors.BORDER,
            font=("Segoe UI", 13, "bold"),
            corner_radius=10
        )
        reset_btn.pack(side="left", padx=10)
    
    def setup_batch_tab(self):
        """Setup batch processing tab with enhanced styling."""
        self.tab_batch.grid_columnconfigure(0, weight=1)
        self.tab_batch.grid_rowconfigure(1, weight=1)
        
        # Header with enhanced styling
        header_frame = ctk.CTkFrame(
            self.tab_batch, 
            fg_color=AppColors.BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=AppColors.BORDER
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=15)
        header_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            header_frame, 
            text="📦 Batch Processing Queue", 
            font=("Segoe UI", 18, "bold"),
            text_color=AppColors.PRIMARY
        ).grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        button_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        button_container.grid(row=0, column=1, padx=20, pady=15, sticky="e")
        
        add_btn = ctk.CTkButton(
            button_container, 
            text="➕  Add Videos", 
            command=self.add_to_batch,
            width=140, 
            height=38,
            fg_color=AppColors.PRIMARY,
            hover_color=AppColors.PRIMARY_HOVER,
            font=("Segoe UI", 12, "bold"),
            corner_radius=8
        )
        add_btn.pack(side="left", padx=5)
        
        clear_btn = ctk.CTkButton(
            button_container, 
            text="🗑  Clear All", 
            command=self.clear_batch,
            width=140, 
            height=38, 
            fg_color=AppColors.DANGER,
            hover_color="#d93636",
            font=("Segoe UI", 12, "bold"),
            corner_radius=8
        )
        clear_btn.pack(side="left", padx=5)
        
        # Queue list (scrollable) with enhanced styling
        self.batch_scroll = ctk.CTkScrollableFrame(
            self.tab_batch, 
            fg_color=AppColors.BG_DARK, 
            corner_radius=10,
            border_width=1,
            border_color=AppColors.BORDER
        )
        self.batch_scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.batch_scroll.grid_columnconfigure(0, weight=1)
        
        # Process batch button with enhanced styling
        self.button_batch_process = ctk.CTkButton(
            self.tab_batch, 
            text="▶️  Process Batch Queue", 
            command=self.process_batch, 
            height=50, 
            font=("Segoe UI", 15, "bold"), 
            fg_color=AppColors.SUCCESS,
            hover_color=AppColors.SUCCESS_HOVER,
            corner_radius=10
        )
        self.button_batch_process.grid(row=2, column=0, padx=20, pady=(15, 8), sticky="ew")
        
        # Batch progress with enhanced styling
        self.batch_progress_bar = ctk.CTkProgressBar(
            self.tab_batch, 
            height=24,
            corner_radius=6,
            border_width=1,
            border_color=AppColors.BORDER,
            progress_color=AppColors.SUCCESS
        )
        self.batch_progress_bar.grid(row=3, column=0, padx=20, pady=8, sticky="ew")
        self.batch_progress_bar.set(0)
        
        self.batch_progress_label = ctk.CTkLabel(
            self.tab_batch, 
            text="📋 No videos in queue", 
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_SECONDARY
        )
        self.batch_progress_label.grid(row=4, column=0, padx=20, pady=(8, 20))
    
    def show_initial_status(self):
        """Show initial status messages with enhanced formatting."""
        self.update_status("=" * 60 + "\n")
        self.update_status("🎬 Welcome to Video Production Suite v3.0 - Professional Edition\n")
        self.update_status("=" * 60 + "\n")
        self.update_status(f"✅ FFmpeg: {'Found locally' if self.ffmpeg_path else 'Found in system PATH'}\n")
        self.update_status(f"✅ FFprobe: {'Found locally' if self.ffprobe_path else 'Found in system PATH'}\n")
        
        available_encoders = get_available_encoders(self.ffmpeg_path, self.update_status)
        self.option_encoder.configure(values=available_encoders, state="normal")
        self.encoder_var.set(available_encoders[0])
    
    def select_video_file(self):
        """Select a video file."""
        path = filedialog.askopenfilename(title="Select a Video File", 
                                         filetypes=[("Video Files", "*.mkv *.mp4 *.mov *.avi")])
        if not path: 
            return
        self.video_path = path
        self.label_video.configure(text=f"📹 Video: {self.video_path}")
        self.option_audio_track.configure(state="disabled")
        self.audio_track_var.set("Scanning...")
        self.detected_segments = []  # Clear previous segments
        self.timeline.update_timeline([], 0)  # Clear timeline
        
        self.available_tracks = get_audio_tracks(Path(self.video_path), self.ffprobe_path, self.update_status)
        self.current_duration = get_video_duration(Path(self.video_path), self.ffprobe_path, self.update_status)
        
        if self.available_tracks:
            track_names = [track['name'] for track in self.available_tracks]
            self.option_audio_track.configure(values=track_names, state="normal")
            self.audio_track_var.set(track_names[-1])
            
            # Display basic audio track info
            self.display_audio_info()
            self.button_analyze_tracks.configure(state="normal")
        else:
            self.audio_track_var.set("No audio tracks found")
            self.button_analyze_tracks.configure(state="disabled")
    
    def display_audio_info(self):
        """Display basic audio track information."""
        self.audio_info_textbox.configure(state="normal")
        self.audio_info_textbox.delete("1.0", "end")
        
        if not self.available_tracks:
            self.audio_info_textbox.insert("1.0", "No audio tracks found in this video.")
            self.audio_info_textbox.configure(state="disabled")
            return
        
        # Header
        header = f"{'Track':<8} {'Codec':<10} {'Channels':<10} {'Sample':<10} {'Bitrate':<12} {'Language':<10}\n"
        separator = "-" * 80 + "\n"
        
        self.audio_info_textbox.insert("end", header)
        self.audio_info_textbox.insert("end", separator)
        
        for track in self.available_tracks:
            line = (f"{track['index']:<8} "
                   f"{track['codec']:<10} "
                   f"{track['channel_str']:<10} "
                   f"{track['sample_rate']:<10} "
                   f"{track['bitrate']:<12} "
                   f"{track['language']:<10}\n")
            self.audio_info_textbox.insert("end", line)
        
        self.audio_info_textbox.insert("end", "\nℹ️ Click 'Analyze All Tracks' to check which tracks have audio content\n")
        self.audio_info_textbox.configure(state="disabled")
    
    def analyze_all_tracks(self):
        """Analyze all audio tracks for content."""
        if not self.available_tracks or not self.video_path:
            return
        
        self.button_analyze_tracks.configure(state="disabled", text="🔍 Analyzing...")
        
        def analyze():
            try:
                self.audio_info_textbox.configure(state="normal")
                self.audio_info_textbox.delete("1.0", "end")
                
                # Header
                header = f"{'Track':<8} {'Codec':<10} {'Channels':<10} {'Status':<15} {'Mean dB':<12} {'Max dB':<10}\n"
                separator = "-" * 90 + "\n"
                
                self.audio_info_textbox.insert("end", header)
                self.audio_info_textbox.insert("end", separator)
                
                for track in self.available_tracks:
                    self.update_status(f"📊 Analyzing Track {track['index']}...\n")
                    
                    analysis = analyze_audio_track_content(
                        Path(self.video_path), 
                        track['index'], 
                        self.ffmpeg_path
                    )
                    
                    # Store analysis results
                    track['analysis'] = analysis
                    
                    # Format mean and max volume
                    mean_str = f"{analysis['mean_volume']:.1f}" if analysis['mean_volume'] is not None else "N/A"
                    max_str = f"{analysis['max_volume']:.1f}" if analysis['max_volume'] is not None else "N/A"
                    
                    # Color-code status
                    status_icon = ""
                    if analysis['is_silent']:
                        status_icon = "🔇 "
                    elif analysis['status'] == "Normal Audio":
                        status_icon = "🔊 "
                    elif analysis['status'] == "Quiet Audio":
                        status_icon = "🔉 "
                    elif analysis['status'] == "Loud Audio":
                        status_icon = "📢 "
                    
                    line = (f"{track['index']:<8} "
                           f"{track['codec']:<10} "
                           f"{track['channel_str']:<10} "
                           f"{status_icon}{analysis['status']:<13} "
                           f"{mean_str:<12} "
                           f"{max_str:<10}\n")
                    
                    self.audio_info_textbox.insert("end", line)
                
                self.audio_info_textbox.insert("end", "\n✅ Analysis complete!\n")
                self.audio_info_textbox.insert("end", "🔇 = Silent/Empty track | 🔉 = Quiet | 🔊 = Normal | 📢 = Loud\n")
                self.audio_info_textbox.configure(state="disabled")
                
                self.update_status("✅ Audio track analysis complete!\n")
                
            except Exception as e:
                self.update_status(f"❌ Error analyzing tracks: {e}\n")
            finally:
                self.button_analyze_tracks.configure(state="normal", text="🔍 Analyze All Tracks")
        
        thread = threading.Thread(target=analyze, daemon=True)
        thread.start()
    
    def select_save_destination(self):
        """Select save destination folder."""
        path = filedialog.askdirectory(title="Select a Save Folder")
        if path:
            self.save_path = path
            self.label_save.configure(text=f"💾 Save to: {self.save_path}")
    
    def preview_video(self):
        """Open video preview with ffplay."""
        if not self.video_path:
            self.update_status("❌ Please select a video file first.\n")
            return
        
        if not self.ffplay_path:
            self.update_status("⚠️ ffplay.exe not found. Cannot preview video.\n")
            return
        
        self.update_status(f"👁 Opening preview for {Path(self.video_path).name}...\n")
        
        def open_preview():
            try:
                # Open ffplay without hiding console (simpler approach)
                subprocess.Popen([str(self.ffplay_path), "-autoexit", self.video_path])
            except Exception as e:
                self.update_status(f"❌ Failed to open preview: {e}\n")
        
        thread = threading.Thread(target=open_preview, daemon=True)
        thread.start()
    
    def detect_silence_preview(self):
        """Detect silence and show preview."""
        if not self.video_path:
            self.update_status("❌ Please select a video file first.\n")
            return
        
        if not self.available_tracks:
            self.update_status("❌ No audio tracks available.\n")
            return
        
        self.button_detect.configure(state="disabled", text="🔍 Detecting...")
        
        def detect():
            try:
                selected_track_name = self.audio_track_var.get()
                selected_track_index = next((t['index'] for t in self.available_tracks 
                                           if t['name'] == selected_track_name), None)
                
                if selected_track_index is None:
                    self.update_status("❌ Could not find selected audio track.\n")
                    return
                
                # Get trim values
                trim_start = 0
                trim_end = None
                try:
                    trim_start_text = self.trim_start_entry.get().strip()
                    if trim_start_text:
                        trim_start = float(trim_start_text)
                    
                    trim_end_text = self.trim_end_entry.get().strip()
                    if trim_end_text:
                        trim_end = float(trim_end_text)
                except ValueError:
                    self.update_status("⚠️ Invalid trim values. Using defaults.\n")
                
                # Detect silence
                settings_dict = {
                    "silence_db": float(self.silence_db_var.get()),
                    "silence_duration": float(self.silence_duration_var.get()),
                    "pad_before": float(self.pad_before_var.get()),
                    "pad_after": float(self.pad_after_var.get())
                }
                
                ffmpeg_log = detect_silence(Path(self.video_path), selected_track_index, 
                                           self.ffmpeg_path, settings_dict, self.update_status,
                                           trim_start, trim_end)
                
                effective_duration = trim_end if trim_end is not None else self.current_duration
                segments = parse_segments(ffmpeg_log, effective_duration, settings_dict, 
                                        self.update_status, trim_start)
                
                self.detected_segments = segments
                
                # Update simple timeline label
                if segments:
                    total_audible = sum(e - s for s, e in segments)
                    total_silence = effective_duration - total_audible
                    percent_kept = (total_audible / effective_duration * 100) if effective_duration > 0 else 0
                    self.timeline_label.configure(
                        text=f"✅ {len(segments)} segments detected\n"
                             f"Keep: {timedelta(seconds=int(total_audible))} | Remove: {timedelta(seconds=int(total_silence))} | {percent_kept:.1f}% retained\n"
                             f"💡 Go to Preview tab for interactive timeline with waveforms"
                    )
                
            except Exception as e:
                self.update_status(f"❌ Error detecting silence: {e}\n")
            finally:
                self.button_detect.configure(state="normal", text="🔍 Detect Silence")
        
        thread = threading.Thread(target=detect, daemon=True)
        thread.start()
    
    def save_advanced_settings(self):
        """Save advanced settings."""
        try:
            self.settings.set("silence_db", float(self.silence_db_var.get()))
            self.settings.set("silence_duration", float(self.silence_duration_var.get()))
            self.settings.set("pad_before", float(self.pad_before_var.get()))
            self.settings.set("pad_after", float(self.pad_after_var.get()))
            self.update_status("✅ Settings saved successfully!\n")
            messagebox.showinfo("Success", "Settings saved successfully!")
        except ValueError:
            self.update_status("❌ Invalid settings values. Please check your input.\n")
            messagebox.showerror("Error", "Invalid settings values. Please enter valid numbers.")
    
    def reset_advanced_settings(self):
        """Reset settings to defaults."""
        self.silence_db_var.set(str(DEFAULT_SETTINGS["silence_db"]))
        self.silence_duration_var.set(str(DEFAULT_SETTINGS["silence_duration"]))
        self.pad_before_var.set(str(DEFAULT_SETTINGS["pad_before"]))
        self.pad_after_var.set(str(DEFAULT_SETTINGS["pad_after"]))
        self.update_status("↺ Settings reset to defaults.\n")
    
    def add_to_batch(self):
        """Add videos to batch queue."""
        paths = filedialog.askopenfilenames(title="Select Video Files", 
                                           filetypes=[("Video Files", "*.mkv *.mp4 *.mov *.avi")])
        for path in paths:
            if path not in [item.video_path for item in self.batch_queue]:
                item = BatchQueueItem(self.batch_scroll, path, self.remove_from_batch)
                item.pack(fill="x", padx=5, pady=3)
                self.batch_queue.append(item)
        
        self.update_batch_status()
    
    def remove_from_batch(self, item: BatchQueueItem):
        """Remove item from batch queue."""
        if item in self.batch_queue:
            self.batch_queue.remove(item)
            item.destroy()
            self.update_batch_status()
    
    def clear_batch(self):
        """Clear all items from batch."""
        if self.processing:
            messagebox.showwarning("Warning", "Cannot clear queue while processing!")
            return
        
        for item in self.batch_queue:
            item.destroy()
        self.batch_queue.clear()
        self.update_batch_status()
    
    def update_batch_status(self):
        """Update batch progress label."""
        count = len(self.batch_queue)
        self.batch_progress_label.configure(text=f"{count} video(s) in queue")
    
    def process_batch(self):
        """Process all videos in batch queue."""
        if not self.batch_queue:
            messagebox.showinfo("Info", "No videos in queue!")
            return
        
        if not self.save_path:
            messagebox.showerror("Error", "Please select a save destination first!")
            self.tabview.set("Main")
            return
        
        self.button_batch_process.configure(state="disabled", text="⏳ Processing...")
        self.processing = True
        
        def process_all():
            total = len(self.batch_queue)
            for idx, item in enumerate(self.batch_queue):
                if item.status == "completed":
                    continue
                
                item.set_status("processing")
                self.batch_progress_label.configure(text=f"Processing {idx + 1}/{total}: {Path(item.video_path).name}")
                
                try:
                    # Get video info
                    video_path = item.video_path
                    tracks = get_audio_tracks(Path(video_path), self.ffprobe_path, self.update_status)
                    
                    if not tracks:
                        self.update_status(f"⚠️ Skipping {Path(video_path).name}: No audio tracks.\n")
                        item.set_status("failed")
                        continue
                    
                    # Use first audio track
                    track_index = tracks[0]['index']
                    
                    # Get encoder
                    selected_encoder_display_name = self.encoder_var.get()
                    if selected_encoder_display_name == "Automatic (Best GPU)":
                        all_encoders = self.option_encoder.cget("values")
                        best_gpu_encoder_name = "CPU (x264)"
                        for name in all_encoders:
                            if name != "Automatic (Best GPU)" and "CPU" not in name:
                                best_gpu_encoder_name = name
                                break
                        video_params = ENCODER_OPTIONS.get(best_gpu_encoder_name)[1]
                    else:
                        video_params = ENCODER_OPTIONS.get(selected_encoder_display_name, ENCODER_OPTIONS["CPU (x264)"])[1]
                    
                    # Get settings
                    settings_dict = {
                        "silence_db": float(self.silence_db_var.get()),
                        "silence_duration": float(self.silence_duration_var.get()),
                        "pad_before": float(self.pad_before_var.get()),
                        "pad_after": float(self.pad_after_var.get()),
                        "filter_length_threshold": self.settings.get("filter_length_threshold", 4096)
                    }
                    
                    # Process video
                    process_video_logic(
                        video_path=video_path,
                        output_dir=self.save_path,
                        output_format=self.format_var.get(),
                        video_params=video_params,
                        all_audio_tracks=tracks,
                        silence_track_index=track_index,
                        ffmpeg_path=self.ffmpeg_path,
                        ffprobe_path=self.ffprobe_path,
                        settings=settings_dict,
                        status_callback=self.update_status
                    )
                    
                    item.set_status("completed")
                    
                except Exception as e:
                    self.update_status(f"❌ Error processing {Path(item.video_path).name}: {e}\n")
                    item.set_status("failed")
                
                # Update batch progress
                progress = (idx + 1) / total
                self.batch_progress_bar.set(progress)
            
            self.batch_progress_label.configure(text=f"Completed {total} video(s)")
            self.button_batch_process.configure(state="normal", text="▶️ Process Batch Queue")
            self.processing = False
        
        thread = threading.Thread(target=process_all, daemon=True)
        thread.start()
    
    def update_status(self, message):
        """Update status textbox."""
        self.status_textbox.configure(state="normal")
        self.status_textbox.insert("end", message)
        self.status_textbox.see("end")
        self.status_textbox.configure(state="disabled")
    
    def update_progress(self, percentage, eta, speed):
        """Update progress bar and label."""
        self.progress_bar.set(percentage / 100)
        self.progress_label.configure(
            text=f"Progress: {percentage:.1f}% | ETA: {eta} | Speed: {speed:.2f}x"
        )
    
    def preview_load_video(self):
        """Load a video file in the Preview tab."""
        path = filedialog.askopenfilename(
            title="Select a Video File",
            filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi")]
        )
        
        if not path:
            return
        
        self.video_path = path
        self.preview_status.configure(text=f"Loading: {Path(path).name}...")
        self.update()
        
        # Load into frame preview
        if self.preview_frame.load_video(path, str(self.ffprobe_path)):
            num_tracks = len(self.preview_frame.audio_tracks)
            
            # Get audio tracks from main function for consistency
            self.available_tracks = get_audio_tracks(Path(path), self.ffprobe_path, self.update_status)
            self.current_duration = get_video_duration(Path(path), self.ffprobe_path, self.update_status)
            
            # Update track selector dropdown
            if num_tracks > 0:
                track_names = [f"Track {i+1}" for i in range(num_tracks)]
                self.preview_track_selector.configure(values=track_names, state="normal")
                self.preview_track_selector_var.set(track_names[-1])  # Default to last track
            else:
                self.preview_track_selector.configure(values=["No tracks"], state="disabled")
                self.preview_track_selector_var.set("No tracks")
            
            self.preview_status.configure(
                text=f"✅ Loaded: {Path(path).name} | {num_tracks} audio track(s) | {timedelta(seconds=int(self.current_duration))} - Click 'Detect Silence'"
            )
            
            # Also update Main tab if it's empty
            if not self.label_video.cget("text").startswith("📹"):
                self.label_video.configure(text=f"📹 Video: {path}")
                if self.available_tracks:
                    track_names_main = [track['name'] for track in self.available_tracks]
                    self.option_audio_track.configure(values=track_names_main, state="normal")
                    self.audio_track_var.set(track_names_main[-1])
                    self.display_audio_info()
                    self.button_analyze_tracks.configure(state="normal")
        else:
            self.preview_status.configure(text="❌ Failed to load video")
    
    def preview_detect_silence(self):
        """Detect silence and update timeline in Preview tab."""
        if not self.video_path:
            messagebox.showwarning("Warning", "Please load a video first!")
            return
        
        self.preview_status.configure(text="🔍 Detecting silence...")
        self.update()
        
        def detect_thread():
            try:
                # Get duration
                if self.current_duration == 0:
                    self.current_duration = get_video_duration(Path(self.video_path), 
                                                              self.ffprobe_path, self.update_status)
                duration = self.current_duration
                
                if duration == 0:
                    self.preview_status.configure(text="❌ Could not get video duration")
                    return
                
                # Get selected audio track for silence detection
                selected_track_str = self.preview_track_selector_var.get()
                try:
                    selected_track_index = int(selected_track_str.split()[-1]) - 1
                except:
                    selected_track_index = 0
                
                # Get the actual stream index
                if selected_track_index < len(self.preview_frame.audio_tracks):
                    stream_index = self.preview_frame.audio_tracks[selected_track_index]["stream_index"]
                else:
                    stream_index = 1  # Fallback
                
                # Detect silence
                self.preview_status.configure(text=f"🔍 Detecting silence in {selected_track_str}...")
                self.update()
                
                settings_dict = {
                    "silence_db": float(self.silence_db_var.get()),
                    "silence_duration": float(self.silence_duration_var.get()),
                    "pad_before": float(self.pad_before_var.get()),
                    "pad_after": float(self.pad_after_var.get())
                }
                
                ffmpeg_log = detect_silence(Path(self.video_path), stream_index, 
                                           self.ffmpeg_path, settings_dict, self.update_status)
                
                segments = parse_segments(ffmpeg_log, duration, settings_dict, self.update_status, 0)
                
                # Extract waveforms for ALL audio tracks
                if AUDIO_ANALYSIS_AVAILABLE and self.preview_frame.audio_tracks:
                    self.preview_status.configure(
                        text=f"📊 Extracting waveforms for {len(self.preview_frame.audio_tracks)} track(s)..."
                    )
                    self.update()
                    
                    waveforms = WaveformGenerator.extract_audio_waveforms_all_tracks(
                        self.video_path, self.ffmpeg_path, self.preview_frame.audio_tracks, self.update_status
                    )
                else:
                    waveforms = {}
                
                # Update timeline with multi-track waveforms
                self.preview_timeline.update_timeline(segments, duration, waveforms)
                
                # Store segments for use in Main tab
                self.detected_segments = segments
                
                self.preview_status.configure(
                    text=f"✅ Silence detected in {selected_track_str}! | {len(segments)} segments | Click timeline to preview frames"
                )
                
            except Exception as e:
                self.preview_status.configure(text=f"❌ Error: {e}")
                self.update_status(f"❌ Preview error: {e}\n")
        
        threading.Thread(target=detect_thread, daemon=True).start()
    
    def on_preview_timeline_click(self, time_seconds: float):
        """Handle timeline click - show frame at that time."""
        self.preview_frame.show_frame_at_time(time_seconds)
        self.preview_status.configure(
            text=f"📍 Showing frame at {timedelta(seconds=int(time_seconds))} | "
                 f"{len(self.detected_segments)} segments detected"
        )
    
    def start_cutting_thread(self):
        """Start video processing in a thread."""
        if not self.video_path or not self.save_path:
            self.update_status("❌ Please select a video file and a save destination first.\n")
            messagebox.showerror("Error", "Please select a video file and save destination!")
            return
        
        if not self.available_tracks:
            self.update_status("❌ Cannot start: No audio tracks were found.\n")
            messagebox.showerror("Error", "No audio tracks found in video!")
            return
        
        self.button_cut.configure(state="disabled", text="⏳ Processing...")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Starting...")
        
        thread = threading.Thread(target=self.run_silence_cutter, daemon=True)
        thread.start()
    
    def run_silence_cutter(self):
        """Main processing logic."""
        try:
            output_format = self.format_var.get()
            selected_track_name = self.audio_track_var.get()
            selected_track_index = next((t['index'] for t in self.available_tracks 
                                       if t['name'] == selected_track_name), None)
            
            if selected_track_index is None:
                self.update_status(f"❌ Error: Could not find data for track '{selected_track_name}'.\n")
                return
            
            # Get trim values
            trim_start = 0
            trim_end = None
            try:
                trim_start_text = self.trim_start_entry.get().strip()
                if trim_start_text:
                    trim_start = float(trim_start_text)
                
                trim_end_text = self.trim_end_entry.get().strip()
                if trim_end_text:
                    trim_end = float(trim_end_text)
            except ValueError:
                self.update_status("⚠️ Invalid trim values. Using defaults.\n")
            
            # Get encoder
            selected_encoder_display_name = self.encoder_var.get()
            if selected_encoder_display_name == "Automatic (Best GPU)":
                all_encoders = self.option_encoder.cget("values")
                best_gpu_encoder_name = "CPU (x264)"
                for name in all_encoders:
                    if name != "Automatic (Best GPU)" and "CPU" not in name:
                        best_gpu_encoder_name = name
                        break
                self.update_status(f"🤖 Automatic selection: Using {best_gpu_encoder_name}.\n")
                video_params = ENCODER_OPTIONS.get(best_gpu_encoder_name)[1]
            else:
                video_params = ENCODER_OPTIONS.get(selected_encoder_display_name, ENCODER_OPTIONS["CPU (x264)"])[1]
            
            # Get settings
            settings_dict = {
                "silence_db": float(self.silence_db_var.get()),
                "silence_duration": float(self.silence_duration_var.get()),
                "pad_before": float(self.pad_before_var.get()),
                "pad_after": float(self.pad_after_var.get()),
                "filter_length_threshold": self.settings.get("filter_length_threshold", 4096)
            }
            
            # Use detected segments if available, otherwise detect now
            segments_to_use = self.detected_segments if self.detected_segments else None
            
            # Process video
            process_video_logic(
                video_path=self.video_path,
                output_dir=self.save_path,
                output_format=output_format,
                video_params=video_params,
                all_audio_tracks=self.available_tracks,
                silence_track_index=selected_track_index,
                ffmpeg_path=self.ffmpeg_path,
                ffprobe_path=self.ffprobe_path,
                settings=settings_dict,
                status_callback=self.update_status,
                progress_callback=self.update_progress,
                trim_start=trim_start,
                trim_end=trim_end,
                segments=segments_to_use
            )
            
        except Exception as e:
            self.update_status(f"❌ An unexpected error occurred: {e}\n")
        finally:
            self.button_cut.configure(state="normal", text="✂️ Cut Silences")
            self.progress_label.configure(text="Complete")


if __name__ == "__main__":
    app = VideoProductionApp()
    app.mainloop()

