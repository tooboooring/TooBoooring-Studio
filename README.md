# 🎬 TooBoooring Studio

Welcome to **TooBoooring Studio** — a premium, web-based video editing and transcription application designed for speed, precision, and ease of use. 

This project is a modern reimagining of our original desktop Silence Cutter, rebuilt from the ground up using a lightning-fast React frontend and a powerful Python FastAPI backend.

---

## ✨ Features
- **AI Transcription (Whisper):** Generate highly accurate transcripts locally.
- **Automated Silence Cutting:** Detect and remove dead air instantly using customizable volume and duration thresholds.
- **Interactive Timeline:** A dynamic, web-based waveform visualization for editing video and audio.
- **Hardware Acceleration:** Full support for FFmpeg custom encoders (like NVENC) for rapid rendering.
- **Project Management:** Save and load your `.tbproj` editing sessions at any time.

---

## 🛠️ Technology Stack
* **Frontend:** Vite + React (Vanilla CSS for premium glassmorphic styling)
* **Backend:** Python + FastAPI
* **Processing:** FFmpeg (Video/Audio Manipulation)
* **AI Engine:** OpenAI Whisper

---

## 🚀 How to Run Locally

### 1. Start the Backend (FastAPI)
The backend handles video processing, FFmpeg commands, and AI transcription.
```bash
cd "TooBoooring Studio/backend"
pip install -r requirements.txt
python main.py
```
*The API will be available at `http://localhost:8000`*

### 2. Start the Frontend (Vite/React)
The frontend provides the sleek, interactive web interface.
```bash
cd "TooBoooring Studio/frontend"
npm install
npm run dev
```
*The web app will instantly launch at `http://localhost:5173`*

---

## 📁 Repository Structure
- `/TooBoooring Studio/frontend/` - Contains the Vite + React single-page application.
- `/TooBoooring Studio/backend/` - Contains the Python FastAPI server and logic.
- `/legacy_app_archive/` - *(Ignored by Git)* Local archive of the original Tkinter desktop application.
