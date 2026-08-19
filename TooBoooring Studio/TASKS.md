# TooBoooring Studio - Task List

*Note: As per Rule 4, no task can ever be considered complete until it is verified as working in the app and has an automated test.*

## Phase 1: Backend Foundation (FastAPI & Legacy Logic)
- [ ] **Task 1.1: Core Utility Migration**
  - Port legacy helper functions (time formatters, path validators) into `backend/core/utils`.
  - *Test*: Write unit tests for time formatting and path validation.
- [ ] **Task 1.2: FFmpeg Wrapper Setup**
  - Port legacy FFmpeg execution wrapper, encoder detection, and video duration extraction.
  - *Test*: Mock FFmpeg calls and verify correct parsing of encoder strings and durations.
- [ ] **Task 1.3: Silence Detection Engine**
  - Port `detect_silence()`, `parse_segments()`, and validate endpoints. Expose these via a FastAPI route (`/api/detect_silence`).
  - *Test*: Provide a sample audio file and assert that silence segments are returned via the API.
- [ ] **Task 1.4: Whisper Transcription Setup**
  - Integrate a local Whisper model to transcribe audio and expose it via a FastAPI route (`/api/transcribe`).
  - *Test*: Assert correct text output and timestamps for a sample audio clip via the API.
- [ ] **Task 1.5: Video Rendering Engine**
  - Implement the video slicing and stitching logic based on cut segments.
  - *Test*: Process a short dummy video and assert the output duration is correct.

## Phase 2: Frontend Integration (React + FastAPI)
- [ ] **Task 2.1: Frontend Clean-up & Branding**
  - Update the React app UI (Header, titles, logos) to reflect "TooBoooring Studio" branding instead of Freecut.
  - *Test*: Visually verify the UI loads cleanly on `localhost:5173`.
- [ ] **Task 2.2: TooBoooring Tools UI Integration**
  - Add UI buttons in the React editor for "Detect Silences" and "Transcribe Video".
  - *Test*: Verify the buttons render correctly within the existing React layout.
- [ ] **Task 2.3: API Wiring: Silence Detection**
  - Connect the "Detect Silences" button to send the current video file to the FastAPI `/api/detect_silence` route, and map the returned segments to the React timeline state.
  - *Test*: End-to-end test of sending a file and visually seeing the cuts appear on the timeline.
- [ ] **Task 2.4: API Wiring: Whisper Transcription**
  - Connect the "Transcribe" button to the FastAPI `/api/transcribe` route, and display the returned text chunks in the UI.
  - *Test*: End-to-end test verifying transcripts appear alongside the video.

## Phase 3: Project Polish & Submission Prep
- [ ] **Task 3.1: Project State Management**
  - Ensure the `.tbproj` (or equivalent JSON export) can save and load the state of the React timeline and backend settings.
  - *Test*: Save a project, reload the page, and restore it successfully.
- [ ] **Task 3.2: Final QA & "Eat your own dogfood" test**
  - Verify all rules are followed (Rule 21), ensure no duplicate functionality exists (Rule 12).
  - *Test*: Cut and export a full sample video from start to finish using the UI.
