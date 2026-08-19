# TooBoooring Studio - Implementation Plan & Feature List

## Overview
**TooBoooring Studio** is being rebuilt from the ground up as a modern, web-based application. This transition moves away from the legacy Tkinter desktop UI to a sleek, browser-based frontend (HTML/CSS/Vanilla JS) powered by a robust Python backend. The app will retain all the powerful features of the old "Silence Cutter" while introducing new AI-driven capabilities like Whisper transcription.

---

## 🛠️ Technology Stack
- **Frontend (UI)**: Vanilla HTML5, CSS3, and JavaScript. 
- **Backend (API & Processing)**: Python (FastAPI) to handle heavy lifting, file operations, and serve the frontend.
- **Media Engine**: FFmpeg (for video slicing, encoding, audio extraction).
- **AI/ML Engine**: OpenAI Whisper (for highly accurate local transcription).
- **Communication**: REST API calls (AJAX/Fetch) between the JS frontend and Python backend.

---

## 📋 Feature List

### 1. Core Video Processing (The "Silence Cutter" Legacy)
- **Silence Detection**: Automatically scan audio tracks to detect silent segments based on user-defined volume thresholds (dB) and durations.
- **Precision Cutting**: Slice and stitch video files together using FFmpeg to seamlessly remove dead air.
- **Batch Processing**: Queue up multiple video files for automated, sequential processing without user intervention.
- **Custom Encoder Support**: Support for hardware acceleration (e.g., NVIDIA NVENC) and CPU encoders (x264).

### 2. The New Timeline & Preview (Web UI)
- **HTML5 Video Player**: Real-time video preview in the browser.
- **Interactive Waveform**: Visual representation of audio tracks, highlighting which segments will be cut (silence) and kept (speech).
- **Drag & Drop**: Easily drop media files directly into the browser to load them into the app.

### 3. Transcription & AI (New)
- **Whisper Integration**: Extract audio and run it through a local Whisper model to generate highly accurate transcripts.
- **Text-to-Video Synchronization**: Map generated text to video timestamps. *(Potential feature: "Edit by text" - delete a word in the transcript to cut it from the video).*

### 4. Project & Settings Management
- **Project Files (`.tbproj`)**: Save current editing sessions (including loaded videos, detected silences, and settings) and resume them later.
- **Advanced Configuration**: UI controls to fine-tune silence threshold, padding around cuts, and audio track selection.

---

## 🚀 Phase 1: Foundation Setup (Next Steps)
1. **Initialize Directory Structure**: Set up the backend (`app/`) and frontend (`static/`) folders inside `TooBoooring Studio`.
2. **Set up the Backend Server**: Create a basic Python FastAPI script (`main.py`) to serve the HTML files and provide a local API at `http://localhost:8000`.
3. **Build the Skeleton UI**: Create the `index.html` layout for the main editor, timeline area, and settings sidebar.
4. **Connect Frontend to Backend**: Establish API routes so the frontend can send commands (like uploading/loading a video) to the Python backend.
