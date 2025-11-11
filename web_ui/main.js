import { Timeline } from './timeline.js';
import { Player } from './player.js';

// Create a global app object for Python to call
window.app = {};

// --- 1. Global Variables ---
let currentVideoInfo = null;
let player = null;
let timeline = null;

// --- 2. DOMContentLoaded (HTML is ready) ---
window.addEventListener('DOMContentLoaded', () => {
    console.log("DOM Loaded. Finding elements...");
    
    // --- Initialize UI components (Player and Timeline) ---
    player = new Player(document.getElementById('video-player'));
    timeline = new Timeline(
        document.getElementById('ruler-canvas'),
        document.getElementById('waveform-canvas'),
        document.getElementById('segments-canvas')
    );

    // --- Bind all UI event listeners ---
    const loadVideoButton = document.getElementById('btn-load-video');
    const detectSilenceButton = document.getElementById('btn-detect-silence');
    const exportButton = document.getElementById('btn-export-video');
    const skipSilenceCheckbox = document.getElementById('skip-silence-check');
    const btnScrollStart = document.getElementById('btn-scroll-start');
    const btnZoomReset = document.getElementById('btn-zoom-reset');
    const btnScrollEnd = document.getElementById('btn-scroll-end');

    // --- Bind Listeners for Python calls ---
    loadVideoButton.addEventListener('click', loadVideo);
    detectSilenceButton.addEventListener('click', detectSilence);
    exportButton.addEventListener('click', exportVideo);
    
    // --- Bind Listeners for local JS ---
    skipSilenceCheckbox.addEventListener('change', () => {
        player.setSkipSilence(skipSilenceCheckbox.checked);
    });

    // Connect player and timeline
    player.onTimeUpdate = (time) => timeline.updatePlayhead(time);
    timeline.onSeek = (time) => player.seek(time);

    // Bind timeline controls
    timeline.bindClick();
    timeline.bindRulerClick();
    timeline.bindWheelEvents();
    timeline.bindKeyEvents();

    btnScrollStart.addEventListener('click', () => timeline.scrollToStart());
    btnZoomReset.addEventListener('click', () => timeline.setZoom(1.0));
    btnScrollEnd.addEventListener('click', () => timeline.scrollToEnd());

    // --- 3. Add console logger for Python to call ---
    const consoleOutput = document.getElementById('console-output');
    window.app.addLog = (message) => {
        consoleOutput.value += message.trim() + '\n';
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    };
});

// --- 4. pywebviewready (Python API is ready) ---
window.addEventListener('pywebviewready', async () => {
    console.log("Pywebview is ready. Initializing...");
    
    const encoderSelect = document.getElementById('encoder-select');

    // --- Get Config from Python ---
    const config = await window.pywebview.api.get_app_config();
    if (config && config.encoders) {
        encoderSelect.innerHTML = ""; // Clear
        config.encoders.forEach(encoder => {
            const option = document.createElement('option');
            option.value = encoder;
            option.textContent = encoder;
            encoderSelect.appendChild(option);
        });
        console.log("Encoders loaded.");
    } else {
        console.error("Could not load encoders from Python.", config);
    }
    
    window.app.addLog("Welcome! Please select a video file to begin.");
    
    // --- NO MORE SPLITTER CODE ---
    // The static CSS grid will handle the layout.
    
    // We need to call resizeAndRedraw ONCE on load to fix canvas sizes
    timeline.resizeAndRedraw();
});

// --- 5. Async Functions (called by listeners) ---
// (These are unchanged and will work)

async function loadVideo() {
    const statusLabel = document.getElementById('status-label');
    const trackSelector = document.getElementById('audio-track-selector');
    
    statusLabel.textContent = "Loading video...";
    const videoInfo = await window.pywebview.api.load_video();
    
    if (videoInfo && !videoInfo.error) {
        currentVideoInfo = videoInfo;
        statusLabel.textContent = `Loaded: ${videoInfo.fileName}`;
        
        trackSelector.innerHTML = ""; // Clear options
        videoInfo.audioTracks.forEach(track => {
            const option = document.createElement('option');
            option.value = track.index;
            option.textContent = track.name;
            trackSelector.appendChild(option);
        });
        
        player.loadVideo(videoInfo.filePath);
        timeline.draw([], 0, null); // Clear timeline
        timeline.resizeAndRedraw(); // Redraw with new info
        
    } else if (videoInfo && videoInfo.error) {
        statusLabel.textContent = "Error loading video.";
        console.error("Python Error:", videoInfo.error);
    } else {
        statusLabel.textContent = "No video loaded.";
    }
}

async function detectSilence() {
    const statusLabel = document.getElementById('status-label');
    const trackSelector = document.getElementById('audio-track-selector');
    const detectSilenceButton = document.getElementById('btn-detect-silence');

    if (!currentVideoInfo) {
        alert("Please load a video first!");
        return;
    }
    
    const selectedTrackIndex = trackSelector.value;
    if (!selectedTrackIndex) {
        alert("No audio track selected!");
        return;
    }
    
    detectSilenceButton.disabled = true;
    statusLabel.textContent = "Detecting silence...";
    
    const segments = await window.pywebview.api.detect_silence(
        currentVideoInfo.filePath,
        parseInt(selectedTrackIndex)
    );
    
    statusLabel.textContent = "Extracting waveform...";
    // Get width from the *scroll wrapper* now
    const canvasWidth = document.getElementById('timeline-scroll-wrapper').offsetWidth;
    const waveformData = await window.pywebview.api.get_waveform_data(
        currentVideoInfo.filePath,
        canvasWidth
    );
    
    if (segments && !segments.error) {
        timeline.draw(segments, currentVideoInfo.duration, waveformData);
        player.setSegments(segments);
        statusLabel.textContent = `Found ${segments.length} segments!`;
    } else {
        timeline.draw([], currentVideoInfo.duration, waveformData);
        statusLabel.textContent = "Error detecting silence.";
    }
    
    detectSilenceButton.disabled = false;
    timeline.resizeAndRedraw(); // Redraw with new data
}

async function exportVideo() {
    const statusLabel = document.getElementById('status-label');
    const exportButton = document.getElementById('btn-export-video');
    
    if (!currentVideoInfo || !timeline.segments || timeline.segments.length === 0) {
        alert("Please load a video and detect segments first.");
        return;
    }
    
    exportButton.disabled = true;
    exportButton.textContent = "Exporting...";
    statusLabel.textContent = "Exporting... (this may take a while)";
    
    const export_settings = {
        encoder: document.getElementById('encoder-select').value,
        format: document.getElementById('format-select').value,
        trim_start: document.getElementById('trim-start').value || null,
        trim_end: document.getElementById('trim-end').value || null
    };
    
    const result = await window.pywebview.api.export_video(
        currentVideoInfo,
        timeline.segments,
        export_settings
    );
    
    exportButton.disabled = false;
    exportButton.textContent = "Export Video";
    
    if (result.status === 'success') {
        statusLabel.textContent = "Export complete!";
        alert(result.message);
    } else {
        statusLabel.textContent = "Export failed.";
        alert(`Export Failed: ${result.message}`);
    }
}