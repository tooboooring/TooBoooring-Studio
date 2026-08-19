# TooBoooring Studio - Implementation Plan

## Overview
**TooBoooring Studio** is a robust, web-based video editing and transcription application built as a comprehensive college project. It integrates a highly interactive, browser-based video timeline with a powerful Python backend. By leveraging an open-source React-based UI core and customizing it, we are able to focus our primary development efforts on integrating advanced backend features like AI transcription (Whisper) and precise audio silence detection (FFmpeg).

---

## 🛠️ Technology Stack
- **Frontend (UI)**: Vite + React 19, Tailwind CSS, Zustand (state management). *Baseline adapted from open-source React video editor principles.*
- **Backend (API & Processing)**: Python (FastAPI) to handle heavy lifting, file operations, and serve AI tasks.
- **Media Engine**: FFmpeg (for video slicing, encoding, audio extraction).
- **AI Engine**: OpenAI Whisper (for highly accurate local transcription).

---

## 📋 Comprehensive Feature List

### 1. Frontend Video Editor (Web UI)
- **Interactive Timeline**: A dynamic waveform generator and multi-track timeline built in React.
- **Frame Preview**: Video frame preview with time-based navigation controls synchronized with the timeline.
- **Custom Integrations**: Custom UI components ("TooBoooring Tools") that allow the user to trigger backend AI tasks directly from the editor.
- **Drag & Drop Loading**: Easily drop media files into the browser to load them.

### 2. Backend Core FFmpeg & Processing Logic
- **Hardware Encoder Detection**: Automatically detect available encoders (e.g., NVENC, CPU x264).
- **Silence Detection**: Run FFmpeg silence detection based on customizable dB thresholds and minimum durations.
- **Segment Parsing & Validation**: Convert FFmpeg silence outputs into usable segments that are passed back to the React frontend.
- **Video Processing Engine**: Slice and stitch video files together to seamlessly remove dead air.

### 3. Application State & Project Management
- **Settings Persistence**: Load/save configuration settings (JSON format).
- **Project Files (`.tbproj`)**: Save the entire editing session (loaded videos, detected segments, selected audio tracks) and resume later.
- **Batch Processing Queue**: Queue up multiple video files for automated processing.

### 4. AI & Transcription
- **Whisper Integration**: Extract audio and run it through a local Whisper model to generate highly accurate transcripts via FastAPI.
- **Text-to-Video Synchronization**: Map generated text to video timestamps on the React timeline.

---

## 🚀 Architecture Guidelines
- **Separation of Concerns**: The React frontend purely handles the UI state and timeline visualization. All intense media manipulation and AI processing is offloaded to the FastAPI backend via REST API calls.
- **Testing**: Every major integration must be verified in the app and have an automated test (Rule 4).
