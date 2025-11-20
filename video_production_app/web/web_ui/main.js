import { Timeline } from './timeline.js';
import { Player } from './player.js';

// Create a global app object for Python to call
window.app = {};

// --- 1. Global Variables ---
let currentVideoInfo = null;
let saveDestination = null;
let player = null;
let timeline = null;
let analysisHistory = []; // Store AI analysis runs for history toggle

// AI Models configuration (must match config.py)
const AI_MODELS = {
    "Llama 3.3 70B (Recommended)": {
        "id": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "price": 0.88,
        "desc": "The Storyteller. Smooth, natural cuts.",
        "tooltip": "Personality: Friendly & Lenient\nBest For: Vlogs, Tutorials, Narrative Content\nCut Rate: Low (~5%)\nStrengths: Excellent narrative flow, keeps personality."
    },
    "DeepSeek R1 (Ruthless)": {
        "id": "deepseek-ai/DeepSeek-R1",
        "price": 4.00,  // Blended approx
        "desc": "The Viral Editor. High-density cuts.",
        "tooltip": "Personality: Ruthless & Strict\nBest For: TikToks, Reels, Highlights\nCut Rate: High (~75%)\nStrengths: Removes ALL fluff. Perfect for short-form."
    },
    "Qwen 2.5 72B (Balanced)": {
        "id": "Qwen/Qwen2.5-72B-Instruct-Turbo",
        "price": 1.20,
        "desc": "The Professional. Logical and clean.",
        "tooltip": "Personality: Balanced & Logical\nBest For: Corporate, Educational, lectures\nCut Rate: Medium (~15%)\nStrengths: Great at following strict formatting rules."
    },
    "Llama 3.1 8B (Speed)": {
        "id": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "price": 0.18,
        "desc": "The Draftsman. Instant results.",
        "tooltip": "Personality: Fast but Basic\nBest For: Quick tests, Rough cuts\nCut Rate: Variable\nStrengths: Extremely cheap and fast."
    }
};

/**
 * Calculate estimated cost for AI analysis
 * @param {number} durationSec - Video duration in seconds
 * @param {string} modelKey - Model key from AI_MODELS
 * @returns {string} - Formatted cost string (e.g., "$0.0123")
 */
function calculateCost(durationSec, modelKey) {
    if (!durationSec || durationSec <= 0) {
        return "$0.0000";
    }
    
    const modelInfo = AI_MODELS[modelKey];
    if (!modelInfo) {
        return "$0.0000";
    }
    
    // Estimate tokens: 150 words/min * 1.3 tokens/word * duration_minutes
    // Simplified: 2.5 tokens per second
    const estimatedTokens = durationSec * 2.5;
    
    // Calculate cost
    const cost = (estimatedTokens / 1000000) * modelInfo.price;
    
    // Format tokens (e.g., 1500 -> 1.5k)
    let tokensStr;
    if (estimatedTokens >= 1000) {
        tokensStr = `${(estimatedTokens/1000).toFixed(1)}k`;
    } else {
        tokensStr = `${Math.round(estimatedTokens)}`;
    }
    
    return { cost: `$${cost.toFixed(4)}`, tokens: tokensStr };
}

/**
 * Save AI analysis result to history
 */
function saveAnalysisResult(result) {
    if (!result || !result.summary) {
        return;
    }
    
    const total = result.summary.segments_analyzed;
    const keepPct = total > 0 ? Math.round((result.summary.keep_count / total) * 100) : 0;
    
    // Create label with timestamp and summary
    const now = new Date();
    const timestamp = now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    const label = `${timestamp} - ${result.modelName} (${keepPct}% Keep)`;
    
    // Store in history
    const historyItem = {
        label: label,
        result: result,
        modelName: result.modelName,
        timestamp: now
    };
    
    analysisHistory.push(historyItem);
    
    // Update dropdown
    const historySelect = document.getElementById('ai-history-select');
    if (historySelect) {
        const values = analysisHistory.map(item => item.label);
        historySelect.innerHTML = values.map(label => `<option value="${label}">${label}</option>`).join('');
        historySelect.value = label; // Select newest
        historySelect.disabled = false;
    }
    
    console.log(`💾 Saved analysis to history: ${label}`);
}

/**
 * Load and restore a previous analysis result from history
 */
function loadHistoryItem(selectedLabel) {
    if (!selectedLabel || selectedLabel === "No runs yet" || !analysisHistory.length) {
        return;
    }
    
    // Find matching history item
    const historyItem = analysisHistory.find(item => item.label === selectedLabel);
    if (!historyItem) {
        console.warn("⚠️ Could not find history item:", selectedLabel);
        return;
    }
    
    const result = historyItem.result;
    
    // Restore segments to timeline
    if (result.segments && timeline) {
        // Get waveforms if available
        const canvasWidth = document.getElementById('waveform-canvas').offsetWidth;
        
        window.pywebview.api.get_waveforms_all_tracks(
            currentVideoInfo.filePath,
            currentVideoInfo.audioTracks,
            canvasWidth
        ).then(waveformsResult => {
            const { hasError, data: waveformsData } = checkError(waveformsResult);
            const waveforms = (!hasError && waveformsData) ? (waveformsData.waveforms || waveformsData) : null;
            
            // Redraw timeline with restored segments
            timeline.draw(result.segments, currentVideoInfo.duration, waveforms);
            
            // Update player
            if (player) {
                player.setSegments(result.segments);
            }
            
            // Update status
            const statusLabel = document.getElementById('status-label');
            if (statusLabel) {
                statusLabel.textContent = `Restored: ${historyItem.modelName} (${result.summary.keep_count} Keep, ${result.summary.flag_count} Flag)`;
            }
            
            // Update analysis summary display
            const aiAnalysisStatus = document.getElementById('ai-analysis-status');
            const aiAnalysisSummary = document.getElementById('ai-analysis-summary');
            if (aiAnalysisStatus && aiAnalysisSummary) {
                aiAnalysisStatus.style.display = 'block';
                aiAnalysisSummary.innerHTML = `
                    <strong>Restored Analysis:</strong><br>
                    ✅ Keep: ${result.summary.keep_count} | ⚠️ Flag: ${result.summary.flag_count} | ❓ Uncertain: ${result.summary.uncertain_count}<br>
                    Confidence: ${(result.summary.avg_confidence * 100).toFixed(1)}%
                `;
            }
            
            console.log(`✅ Restored analysis: ${selectedLabel}`);
        }).catch(error => {
            console.error("Error loading waveforms for history:", error);
            // Still restore segments without waveforms
            timeline.draw(result.segments, currentVideoInfo.duration, null);
            if (player) {
                player.setSegments(result.segments);
            }
        });
    }
}

/**
 * Update the cost estimate display and tooltip
 */
function updateCostDisplay() {
    const costLabel = document.getElementById('ai-cost-estimate');
    const modelSelect = document.getElementById('ai-model-select');
    
    if (!costLabel || !modelSelect) {
        return;
    }
    
    const selectedModel = modelSelect.value;
    const duration = currentVideoInfo ? currentVideoInfo.duration : 0;
    
    const result = calculateCost(duration, selectedModel);
    const modelInfo = AI_MODELS[selectedModel];
    
    // Update tooltip dynamically
    if (modelInfo && modelInfo.tooltip) {
        modelSelect.title = modelInfo.tooltip;
    } else {
        modelSelect.title = '';
    }
    
    if (duration > 0 && modelInfo) {
        costLabel.textContent = `Est. Cost: ${result.cost} (~${result.tokens} tokens) - ${modelInfo.desc}`;
        costLabel.style.color = '#888';
    } else {
        costLabel.textContent = 'Est. Cost: $0.0000 (Load a video first)';
        costLabel.style.color = '#666';
    }
}

// Global functions for Python to call via window.evaluate_js
window.updateProgress = function(percentage, eta, speed) {
    const progressPercentage = document.getElementById('progress-percentage');
    const progressBar = document.getElementById('progress-bar');
    const progressDetails = document.getElementById('progress-details');
    
    if (progressPercentage) {
        progressPercentage.textContent = `${percentage.toFixed(1)}%`;
    }
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
    }
    if (progressDetails) {
        const speedStr = speed > 0 ? `${speed.toFixed(2)}x` : 'Calculating...';
        progressDetails.textContent = `ETA: ${eta} | Speed: ${speedStr}`;
    }
};

window.updateConsole = function(message) {
    const consoleOutput = document.getElementById('console-output');
    if (consoleOutput) {
        consoleOutput.value += message;
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    }
};

window.clearConsole = function() {
    const consoleOutput = document.getElementById('console-output');
    if (consoleOutput) {
        consoleOutput.value = '';
    }
};

// --- 2. DOMContentLoaded (HTML is ready) ---
// This listener just finds elements. It does NOT call Python.
window.addEventListener('DOMContentLoaded', () => {
    console.log("DOM Loaded. Finding elements...");

    // --- Initialize UI components (Player and Timeline) ---
    player = new Player(document.getElementById('video-player'));
    timeline = new Timeline(
        document.getElementById('ruler-canvas'),
        document.getElementById('waveform-canvas'),
        document.getElementById('segments-canvas')
    );

    // Ensure timeline content is visible
    const timelinePanel = document.querySelector('.timeline.panel');
    const timelineContent = timelinePanel?.querySelector('.panel-content');
    if (timelineContent) {
        timelineContent.style.display = 'flex';
    }

    // --- Bind all UI event listeners ---
    // Get elements
    const loadVideoButton = document.getElementById('btn-load-video');
    if (!loadVideoButton) {
        console.error("ERROR: btn-load-video button not found!");
        alert("ERROR: Load video button not found. Check console for details.");
    }
    const detectSilenceButton = document.getElementById('btn-detect-silence');
    const aiAnalysisButton = document.getElementById('btn-ai-analysis');
    const exportButton = document.getElementById('btn-export-video');
    const exportCutsButton = document.getElementById('btn-export-cuts');
    const exportEdlButton = document.getElementById('btn-export-edl');
    const exportXmlButton = document.getElementById('btn-export-xml');
    const skipSilenceCheckbox = document.getElementById('skip-silence-check');
    const btnScrollStart = document.getElementById('btn-scroll-start');
    const btnZoomReset = document.getElementById('btn-zoom-reset');
    const btnScrollEnd = document.getElementById('btn-scroll-end');
    const zoomInBtn = document.getElementById('btn-zoom-in');
    const zoomOutBtn = document.getElementById('btn-zoom-out');
    const zoomResetBtn = document.getElementById('btn-zoom-reset');
    const zoomLevelSpan = document.getElementById('zoom-level');
    const scrollLeftBtn = document.getElementById('btn-scroll-left');
    const scrollRightBtn = document.getElementById('btn-scroll-right');
    const scrollStartBtn = document.getElementById('btn-scroll-start');
    const scrollEndBtn = document.getElementById('btn-scroll-end');
    const timelineStatsSpan = document.getElementById('timeline-stats');
    const toggleControlsBtn = document.getElementById('btn-toggle-controls');
    const toggleTimelineBtn = document.getElementById('btn-toggle-timeline');
    const controlsPanel = document.getElementById('controls-panel');
    const mainContent = document.querySelector('.main-content');
    const selectDestinationBtn = document.getElementById('btn-select-destination');
    const saveDestinationLabel = document.getElementById('save-destination-label');
    const analyzeTracksBtn = document.getElementById('btn-analyze-tracks');
    const audioDetailsTextbox = document.getElementById('audio-details-textbox');
    const previousFrameBtn = document.getElementById('btn-previous-frame');
    const nextFrameBtn = document.getElementById('btn-next-frame');
    const stopBtn = document.getElementById('btn-stop');
    const playbackAudioTrackSelector = document.getElementById('playback-audio-track');

    // --- Bind Listeners for Python calls ---
    if (loadVideoButton) {
        loadVideoButton.addEventListener('click', () => {
            console.log("Load video button clicked");
            loadVideo().catch(error => {
                console.error("Error in loadVideo:", error);
                const statusLabel = document.getElementById('status-label');
                if (statusLabel) {
                    statusLabel.textContent = "Error loading video.";
                }
                window.updateConsole(`❌ Error: ${error.message}\n`);
            });
        });
    } else {
        console.error("Cannot attach event listener: btn-load-video not found");
    }
    detectSilenceButton.addEventListener('click', detectSilence);
    aiAnalysisButton.addEventListener('click', runAIAnalysis);
    exportButton.addEventListener('click', exportVideo);
    exportCutsButton.addEventListener('click', exportCuts);
    exportEdlButton.addEventListener('click', exportEdl);
    exportXmlButton.addEventListener('click', exportXml);

    // --- Bind Listeners for local JS ---
    skipSilenceCheckbox.addEventListener('change', () => {
        player.setSkipSilence(skipSilenceCheckbox.checked);
    });
    
    // Audio track mute buttons are handled in loadVideo() function

    // Connect player and timeline
    player.onTimeUpdate = (time) => {
        timeline.updatePlayhead(time);
        // Update time display
        const timeDisplay = document.getElementById('time-display');
        if (timeDisplay) {
            const current = player.formatTime(player.getCurrentTime());
            const total = player.formatTime(player.getDuration());
            timeDisplay.textContent = `${current} / ${total}`;
        }
    };

    timeline.onSeek = (time) => {
        player.seek(time);
    };

    // Bind timeline controls
    timeline.bindClick();
    timeline.bindRulerClick();
    timeline.bindWheelEvents();
    timeline.bindKeyEvents();

    // Timeline zoom controls
    if (zoomInBtn) {
        zoomInBtn.addEventListener('click', () => {
            timeline.zoomIn();
            if (zoomLevelSpan) zoomLevelSpan.textContent = `${timeline.zoom.toFixed(1)}x`;
            updateTimelineStats();
        });
    }

    if (zoomOutBtn) {
        zoomOutBtn.addEventListener('click', () => {
            timeline.zoomOut();
            if (zoomLevelSpan) zoomLevelSpan.textContent = `${timeline.zoom.toFixed(1)}x`;
            updateTimelineStats();
        });
    }

    if (zoomResetBtn) {
        zoomResetBtn.addEventListener('click', () => {
            timeline.setZoom(1.0);
            if (zoomLevelSpan) zoomLevelSpan.textContent = `${timeline.zoom.toFixed(1)}x`;
            updateTimelineStats();
        });
    }

    // Timeline scroll controls
    if (scrollLeftBtn) {
        scrollLeftBtn.addEventListener('click', () => {
            timeline.scrollLeft();
            updateTimelineStats();
        });
    }

    if (scrollRightBtn) {
        scrollRightBtn.addEventListener('click', () => {
            timeline.scrollRight();
            updateTimelineStats();
        });
    }

    if (scrollStartBtn) {
        scrollStartBtn.addEventListener('click', () => {
            timeline.scrollToStart();
            updateTimelineStats();
        });
    }

    if (scrollEndBtn) {
        scrollEndBtn.addEventListener('click', () => {
            timeline.scrollToEnd();
            updateTimelineStats();
        });
    }

    if (btnScrollStart) {
        btnScrollStart.addEventListener('click', () => timeline.scrollToStart());
    }
    if (btnZoomReset) {
        btnZoomReset.addEventListener('click', () => timeline.setZoom(1.0));
    }
    if (btnScrollEnd) {
        btnScrollEnd.addEventListener('click', () => timeline.scrollToEnd());
    }

    // Set up zoom change callback to update display
    timeline.onZoomChanged = (zoomLevel) => {
        if (zoomLevelSpan) zoomLevelSpan.textContent = `${zoomLevel.toFixed(1)}x`;
        updateTimelineStats();
    };

    // Player control buttons
    if (previousFrameBtn) {
        previousFrameBtn.addEventListener('click', () => {
            player.previousFrame();
        });
    }

    if (nextFrameBtn) {
        nextFrameBtn.addEventListener('click', () => {
            player.nextFrame();
        });
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', () => {
            player.stop();
        });
    }

    // Collapsible panels
    let controlsPanelCollapsed = false;
    let timelinePanelCollapsed = false;

    if (toggleControlsBtn && controlsPanel && mainContent) {
        toggleControlsBtn.addEventListener('click', () => {
            const panelContent = controlsPanel.querySelector('.panel-content');
            if (controlsPanelCollapsed) {
                panelContent.style.display = 'block';
                mainContent.style.gridTemplateColumns = '2fr 1fr';
                toggleControlsBtn.textContent = '◀';
                controlsPanelCollapsed = false;
            } else {
                panelContent.style.display = 'none';
                mainContent.style.gridTemplateColumns = '1fr';
                toggleControlsBtn.textContent = '▶';
                controlsPanelCollapsed = true;
            }
        });
    }

    if (toggleTimelineBtn && timelinePanel) {
        toggleTimelineBtn.addEventListener('click', () => {
            const panelContent = timelinePanel.querySelector('.panel-content');
            const appContainer = document.querySelector('.app-container');
            if (timelinePanelCollapsed) {
                panelContent.style.display = 'flex';
                appContainer.style.gridTemplateRows = '40px 1fr 250px';
                toggleTimelineBtn.textContent = '▼';
                timelinePanelCollapsed = false;
                // Redraw timeline if it has data
                if (timeline.duration > 0) {
                    timeline.redraw();
                }
            } else {
                panelContent.style.display = 'none';
                appContainer.style.gridTemplateRows = '40px 1fr 40px';
                toggleTimelineBtn.textContent = '▲';
                timelinePanelCollapsed = true;
            }
        });
    }

    // Select save destination button
    if (selectDestinationBtn && saveDestinationLabel) {
        selectDestinationBtn.addEventListener('click', async () => {
            const path = await window.pywebview.api.select_save_destination();
            if (path) {
                saveDestination = path;
                saveDestinationLabel.textContent = path.length > 50 ? '...' + path.slice(-47) : path;
                saveDestinationLabel.style.color = '#4CAF50';
            }
        });
    }

    // Analyze All Tracks button
    if (analyzeTracksBtn && audioDetailsTextbox) {
        analyzeTracksBtn.addEventListener('click', async () => {
            if (!currentVideoInfo) {
                alert("Please load a video first!");
                return;
            }

            const statusLabel = document.getElementById('status-label');
            analyzeTracksBtn.disabled = true;
            analyzeTracksBtn.textContent = "Analyzing...";
            audioDetailsTextbox.value = "Analyzing audio tracks...\n";
            if (statusLabel) statusLabel.textContent = "Analyzing audio tracks...";

            try {
                const result = await window.pywebview.api.analyze_all_tracks(currentVideoInfo.filePath);
                
                // Check for errors
                const { hasError, message, data } = checkError(result);
                if (hasError) {
                    audioDetailsTextbox.value = `Error: ${message}`;
                    if (statusLabel) statusLabel.textContent = "Analysis failed.";
                    return;
                }
                
                // Extract tracks from response (handle both new format and legacy)
                const tracks = data.tracks || data || [];
                
                // Format results as a table
                let output = "Track    Codec      Channels    Status         Mean Volume   Max Volume\n";
                output += "─────────────────────────────────────────────────────────────────────\n";
                
                tracks.forEach(track => {
                    const meanStr = track.mean_volume !== null ? `${track.mean_volume.toFixed(1)} dB` : "N/A";
                    const maxStr = track.max_volume !== null ? `${track.max_volume.toFixed(1)} dB` : "N/A";
                    
                    let statusIcon = "";
                    if (track.is_silent) {
                        statusIcon = "🔇 ";
                    } else if (track.status === "Normal Audio") {
                        statusIcon = "🔊 ";
                    } else if (track.status === "Quiet Audio") {
                        statusIcon = "🔉 ";
                    } else if (track.status === "Loud Audio") {
                        statusIcon = "📢 ";
                    }
                    
                    const line = `${String(track.index).padEnd(8)} ${track.codec.padEnd(10)} ${track.channels.padEnd(10)} ${statusIcon}${track.status.padEnd(13)} ${meanStr.padEnd(12)} ${maxStr}\n`;
                    output += line;
                });
                
                output += "\n✅ Analysis complete!\n";
                output += "🔇 = Silent/Empty track | 🔉 = Quiet | 🔊 = Normal | 📢 = Loud\n";
                
                audioDetailsTextbox.value = output;
                if (statusLabel) statusLabel.textContent = `Analyzed ${tracks.length} track(s).`;
            } catch (error) {
                audioDetailsTextbox.value = `Error: ${error.message}`;
                if (statusLabel) statusLabel.textContent = "Analysis failed.";
                console.error("Error analyzing tracks:", error);
            } finally {
                analyzeTracksBtn.disabled = false;
                analyzeTracksBtn.textContent = "Analyze All Tracks";
            }
        });
    }

    // --- 3. Add console logger for Python to call ---
    const consoleOutput = document.getElementById('console-output');
    window.app.addLog = (message) => {
        if (consoleOutput) {
            consoleOutput.value += message.trim() + '\n';
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }
    };

    // Update timeline statistics helper
    function updateTimelineStats() {
        if (!timeline || !timelineStatsSpan) return;
        const stats = timeline.getStatistics();
        if (stats.segmentCount > 0) {
            timelineStatsSpan.textContent = `Duration: ${formatTime(stats.totalDuration)} | Audible: ${formatTime(stats.audibleTime)} | Silence: ${stats.silencePercentage.toFixed(1)}% | Segments: ${stats.segmentCount}`;
        } else {
            timelineStatsSpan.textContent = "No segments detected";
        }
        if (zoomLevelSpan) zoomLevelSpan.textContent = `${timeline.zoom.toFixed(1)}x`;
    }

    function formatTime(seconds) {
        if (seconds < 60) {
            return `${seconds.toFixed(1)}s`;
        }
        const mins = Math.floor(seconds / 60);
        const secs = (seconds % 60).toFixed(1);
        return `${mins}m ${secs}s`;
    }

    // --- Save AI Settings when changed ---
    const whisperModelSelect = document.getElementById('whisper-model-select');
    const apiKeyInput = document.getElementById('ai-api-key');

    // Save Whisper model when changed
    if (whisperModelSelect) {
        whisperModelSelect.addEventListener('change', async (e) => {
            const newModel = e.target.value;
            console.log(`Whisper model changed to: ${newModel}`);
            
            try {
                // Wait for pywebview to be ready
                if (window.pywebview && window.pywebview.api && window.pywebview.api.save_ai_settings) {
                    const apiKey = apiKeyInput ? apiKeyInput.value : '';
                    await window.pywebview.api.save_ai_settings(newModel, apiKey);
                    console.log('✅ AI settings saved successfully');
                } else {
                    console.warn('⚠️ pywebview API not ready yet, settings will be applied but not saved');
                }
            } catch (error) {
                console.error('❌ Error saving AI settings:', error);
            }
        });
    }

    // Save API key when it loses focus (blur event)
    if (apiKeyInput) {
        apiKeyInput.addEventListener('blur', async (e) => {
            const newApiKey = e.target.value.trim();
            
            // Only save if the key has changed and is not empty
            if (newApiKey) {
                console.log('API key changed, saving...');
                
                try {
                    if (window.pywebview && window.pywebview.api && window.pywebview.api.save_ai_settings) {
                        const whisperModel = whisperModelSelect ? whisperModelSelect.value : 'base';
                        await window.pywebview.api.save_ai_settings(whisperModel, newApiKey);
                        console.log('✅ API key saved successfully');
                    } else {
                        console.warn('⚠️ pywebview API not ready yet, API key will be used but not saved');
                    }
                } catch (error) {
                    console.error('❌ Error saving API key:', error);
                }
            }
        });
    }
    // --- Splitter Drag Logic ---
    const splitterVertical = document.getElementById('splitter-vertical');
    const splitterHorizontal = document.getElementById('splitter-horizontal');
    const playerPanel = document.getElementById('player-panel');

    const appContainer = document.querySelector('.app-container');
    const mainContentPanel = document.querySelector('.main-content');

    // Vertical Splitter (Player vs Controls)
    if (splitterVertical && playerPanel && controlsPanel) {
        let isDraggingV = false;

        splitterVertical.addEventListener('mousedown', (e) => {
            isDraggingV = true;
            splitterVertical.classList.add('dragging');
            document.body.style.cursor = 'col-resize';
            e.preventDefault(); // Prevent text selection
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDraggingV) return;

            // Calculate new width for controls panel (from right)
            const containerRect = mainContentPanel.getBoundingClientRect();
            const newControlsWidth = containerRect.right - e.clientX - (splitterVertical.offsetWidth / 2);

            // Constraints
            if (newControlsWidth >= 250 && newControlsWidth <= 600) {
                controlsPanel.style.width = `${newControlsWidth}px`;
                controlsPanel.style.flex = 'none'; // Disable flex grow/shrink
            }
        });

        document.addEventListener('mouseup', () => {
            if (isDraggingV) {
                isDraggingV = false;
                splitterVertical.classList.remove('dragging');
                document.body.style.cursor = '';
                // Trigger resize for charts/canvas if needed
                if (timeline) timeline.redraw();
            }
        });
    }

    // Horizontal Splitter (Main vs Timeline)
    if (splitterHorizontal && timelinePanel && mainContentPanel) {
        let isDraggingH = false;

        splitterHorizontal.addEventListener('mousedown', (e) => {
            isDraggingH = true;
            splitterHorizontal.classList.add('dragging');
            document.body.style.cursor = 'row-resize';
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDraggingH) return;

            // Calculate new height for timeline panel (from bottom)
            const containerRect = appContainer.getBoundingClientRect();
            const newTimelineHeight = containerRect.bottom - e.clientY - (splitterHorizontal.offsetHeight / 2);

            // Constraints
            if (newTimelineHeight >= 150 && newTimelineHeight <= 600) {
                timelinePanel.style.height = `${newTimelineHeight}px`;
                timelinePanel.style.flex = 'none';
            }
        });

        document.addEventListener('mouseup', () => {
            if (isDraggingH) {
                isDraggingH = false;
                splitterHorizontal.classList.remove('dragging');
                document.body.style.cursor = '';
                // Redraw timeline to fit new height
                if (timeline) timeline.redraw();
            }
        });
    }

    // Handle window resize to redraw timeline
    window.addEventListener('resize', () => {
        if (timeline) timeline.redraw();
    });
});

// --- 4. pywebviewready (Python API is ready) ---
// We wait for this event to safely call Python functions.
window.addEventListener('pywebviewready', async () => {
    console.log("Pywebview is ready. Getting app config...");

    const encoderSelect = document.getElementById('encoder-select');

    // --- Get Config from Python ---
    try {
        const config = await window.pywebview.api.get_app_config();
        console.log("Got config from Python:", config);
        
        if (config && config.encoders && Array.isArray(config.encoders) && config.encoders.length > 0) {
            if (encoderSelect) {
                encoderSelect.innerHTML = ""; // Clear
                config.encoders.forEach(encoder => {
                    const option = document.createElement('option');
                    option.value = encoder;
                    option.textContent = encoder;
                    encoderSelect.appendChild(option);
                });
                console.log(`✅ Successfully populated ${config.encoders.length} encoder(s) in dropdown`);
                
                // Show success message
                const encoderCount = config.encoders.length - 1; // Exclude "Automatic (Best GPU)"
                if (encoderCount > 0) {
                    window.app.addLog(`✅ Found ${encoderCount} compatible hardware encoder(s).\n`);
                } else {
                    window.app.addLog("⚠️ No compatible hardware encoder found. Will use CPU.\n");
                }
            }
        } else {
            console.error("Could not load encoders from Python.", config);
            if (encoderSelect) {
                encoderSelect.innerHTML = '<option value="CPU (x264)">CPU (x264)</option>';
            }
            window.app.addLog("⚠️ No encoders detected, using CPU fallback\n");
        }
    } catch (error) {
        console.error("❌ Error loading encoder config:", error);
        if (encoderSelect) {
            encoderSelect.innerHTML = '<option value="CPU (x264)">CPU (x264)</option>';
        }
        window.app.addLog(`❌ Error loading encoder configuration: ${error.message}\n`);
    }

    // --- Load AI Settings from Python ---
    try {
        const aiSettings = await window.pywebview.api.get_ai_settings();
        console.log("Got AI settings from Python:", aiSettings);
        
        const whisperModelSelect = document.getElementById('whisper-model-select');
        const apiKeyInput = document.getElementById('ai-api-key');
        
        if (aiSettings) {
            // Set Whisper model dropdown
            if (whisperModelSelect && aiSettings.whisper_model) {
                whisperModelSelect.value = aiSettings.whisper_model;
                console.log(`✅ Loaded Whisper model: ${aiSettings.whisper_model}`);
            }
            
            // Set API key if available
            if (apiKeyInput && aiSettings.api_key) {
                // Show indicator of where the key is loaded from
                if (aiSettings.api_key_source === 'environment') {
                    apiKeyInput.placeholder = '(Loaded from .env)';
                    apiKeyInput.value = aiSettings.api_key;
                    console.log('✅ API key loaded from .env file');
                } else if (aiSettings.api_key_source === 'saved') {
                    apiKeyInput.value = aiSettings.api_key;
                    console.log('✅ API key loaded from saved settings');
                } else {
                    console.log('ℹ️ No API key configured (use .env or enter in UI)');
                }
            }
        }
    } catch (error) {
        console.error("❌ Error loading AI settings:", error);
        // Non-fatal error - continue with defaults
    }

    // --- Add event listener for AI model selector ---
    const aiModelSelect = document.getElementById('ai-model-select');
    if (aiModelSelect) {
        aiModelSelect.addEventListener('change', () => {
            console.log(`AI model changed to: ${aiModelSelect.value}`);
            updateCostDisplay();
        });
        // Initial cost display update
        updateCostDisplay();
    }

    // --- Add event listener for AI history selector ---
    const aiHistorySelect = document.getElementById('ai-history-select');
    if (aiHistorySelect) {
        aiHistorySelect.addEventListener('change', (e) => {
            const selectedLabel = e.target.value;
            if (selectedLabel) {
                loadHistoryItem(selectedLabel);
            }
        });
    }

    window.app.addLog("Welcome! Please select a video file to begin.\n");
});

// Clean up temporary files when page is unloading
window.addEventListener('beforeunload', () => {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.cleanup_temp_files) {
        // Try to clean up, but don't wait (async cleanup)
        window.pywebview.api.cleanup_temp_files().catch(err => {
            console.warn("Error cleaning up temp files on unload:", err);
        });
    }
});

// --- Helper function for error checking ---
function checkError(result) {
    if (!result) {
        return { hasError: true, message: "No response from server" };
    }
    if (result.status === "error" || result.error) {
        return { hasError: true, message: result.error || result.message || "Unknown error" };
    }
    return { hasError: false, data: result };
}

// --- 5. Async Functions (called by listeners) ---
// We move the main logic into separate functions.

async function loadVideo() {
    console.log("loadVideo() called");
    const statusLabel = document.getElementById('status-label');
    const trackSelector = document.getElementById('audio-track-selector');

    if (!statusLabel) {
        console.error("status-label element not found!");
        return;
    }

    statusLabel.textContent = "Loading video...";
    window.clearConsole();
    window.updateConsole("Loading video file...\n");
    
    try {
        // Check if pywebview API is available
        if (!window.pywebview || !window.pywebview.api) {
            throw new Error("pywebview API not available. Make sure the app is running in pywebview.");
        }
        
        if (!window.pywebview.api.load_video) {
            throw new Error("load_video API method not found.");
        }
        
        console.log("Calling window.pywebview.api.load_video()...");
        const result = await window.pywebview.api.load_video();
        console.log("load_video result:", result);
        
        // Handle cancellation (None/null)
        if (!result) {
            statusLabel.textContent = "No video loaded.";
            window.updateConsole("No video selected.\n");
            return;
        }

        // Check for errors
        const { hasError, message, data } = checkError(result);
        console.log("checkError result:", { hasError, message, data });
        
        if (hasError) {
            statusLabel.textContent = "Error loading video.";
            window.updateConsole(`❌ Error: ${message}\n`);
            console.error("Python Error:", message);
            return;
        }

        // Success - use data (which is the videoInfo) or result directly if no wrapper
        const videoInfo = data || result;
        console.log("Using videoInfo:", videoInfo);
        
        if (!videoInfo || !videoInfo.fileName) {
            console.error("Invalid videoInfo structure:", videoInfo);
            statusLabel.textContent = "Error: Invalid video data received.";
            window.updateConsole("❌ Error: Invalid video data structure\n");
            return;
        }
        
        currentVideoInfo = videoInfo;
        
        // Clear analysis history when loading a new video
        analysisHistory = [];
        const historySelect = document.getElementById('ai-history-select');
        if (historySelect) {
            historySelect.innerHTML = '<option value="">No runs yet</option>';
            historySelect.disabled = true;
        }
        
        statusLabel.textContent = `Loaded: ${videoInfo.fileName}`;
        window.updateConsole(`✅ Video loaded: ${videoInfo.fileName}\n`);
        window.updateConsole(`Duration: ${videoInfo.duration.toFixed(2)}s\n`);
        window.updateConsole(`Audio tracks: ${videoInfo.audioTracks.length}\n`);

        trackSelector.innerHTML = ""; // Clear options
        videoInfo.audioTracks.forEach(track => {
            const option = document.createElement('option');
            option.value = track.index;
            option.textContent = track.name;
            trackSelector.appendChild(option);
        });

        // Update cost estimate with new video duration
        updateCostDisplay();

        // Populate audio track mute buttons (Premiere Pro style)
        const audioTracksButtons = document.getElementById('audio-tracks-buttons');
        if (audioTracksButtons) {
            audioTracksButtons.innerHTML = ""; // Clear existing buttons
            
            // Initialize all tracks as enabled
            player.enabledTrackIndices = videoInfo.audioTracks.map(track => track.index);
            
            // Create a mute button for each track
            videoInfo.audioTracks.forEach(track => {
                const button = document.createElement('button');
                button.className = 'audio-track-button';
                button.dataset.trackIndex = track.index;
                button.innerHTML = `<span class="track-icon">🔊</span> <span>${track.name}</span>`;
                button.title = `Click to mute/unmute ${track.name}`;
                button.setAttribute('aria-label', `Toggle ${track.name}`);
                
                // Add click handler
                button.addEventListener('click', async () => {
                    const trackIndex = parseInt(button.dataset.trackIndex);
                    const isMuted = button.classList.contains('muted');
                    
                    if (isMuted) {
                        // Unmute: add track to enabled list
                        if (!player.enabledTrackIndices.includes(trackIndex)) {
                            player.enabledTrackIndices.push(trackIndex);
                        }
                        button.classList.remove('muted');
                        button.querySelector('.track-icon').textContent = '🔊';
                    } else {
                        // Mute: remove track from enabled list
                        player.enabledTrackIndices = player.enabledTrackIndices.filter(idx => idx !== trackIndex);
                        button.classList.add('muted');
                        button.querySelector('.track-icon').textContent = '🔇';
                    }
                    
                    // Update video with new track selection
                    await player.updateAudioTracks(player.enabledTrackIndices);
                });
                
                audioTracksButtons.appendChild(button);
            });
        }

        player.loadVideo(videoInfo.filePath, videoInfo.audioTracks);
        timeline.draw([], 0, null); // Clear timeline
    } catch (error) {
        console.error("Error in loadVideo:", error);
        statusLabel.textContent = "Error loading video.";
        window.updateConsole(`❌ Error: ${error.message}\n`);
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
    window.updateConsole(`Detecting silence on track ${selectedTrackIndex}...\n`);
    console.log(`JavaScript: Asking Python to detect silence on track ${selectedTrackIndex}...`);

    const result = await window.pywebview.api.detect_silence(
        currentVideoInfo.filePath,
        parseInt(selectedTrackIndex)
    );

    detectSilenceButton.disabled = false;

    // Check for errors
    const { hasError, message, data } = checkError(result);
    if (hasError) {
        statusLabel.textContent = "Error detecting silence.";
        window.updateConsole(`❌ Error: ${message}\n`);
        console.error("Python Error:", message);
        return;
    }

    // Extract segments from response
    const segments = data.segments || data; // Handle both new format and legacy
    console.log("Got segments from Python:", segments);
    window.updateConsole(`✅ Found ${segments.length} segments\n`);
        
        // Extract waveform data for all tracks
        statusLabel.textContent = "Extracting waveforms...";
        window.updateConsole("Extracting waveform data for all tracks...\n");
        
        // Get canvas width to tell Python how much to downsample
        const canvasWidth = document.getElementById('waveform-canvas').offsetWidth;
        
        const waveformsResult = await window.pywebview.api.get_waveforms_all_tracks(
            currentVideoInfo.filePath,
            currentVideoInfo.audioTracks,
            canvasWidth
        );
        
        // Check for errors
        const { hasError: hasWaveformError, message: waveformError, data: waveformsData } = checkError(waveformsResult);
        console.log("Waveform result:", waveformsResult);
        console.log("Has error:", hasWaveformError, "Data:", waveformsData);
        
        if (!hasWaveformError && waveformsData) {
            // Extract waveforms from response (handle both new format and legacy)
            const waveforms = waveformsData.waveforms || waveformsData;
            const trackCount = Object.keys(waveforms).length;
            console.log(`Got waveforms data. Track count: ${trackCount}`, waveforms);
            
            if (trackCount > 0) {
                window.updateConsole(`✅ Waveforms extracted for ${trackCount} track(s)\n`);
                // Now draw everything
                timeline.draw(segments, currentVideoInfo.duration, waveforms);
                statusLabel.textContent = `Found ${segments.length} segments!`;
            } else {
                // No tracks in waveforms
                timeline.draw(segments, currentVideoInfo.duration, null);
                statusLabel.textContent = "Segments found (no waveform data).";
                window.updateConsole(`⚠️ Waveforms response empty (check Python console for errors)\n`);
            }
        } else {
            // Still draw, but without waveform
            timeline.draw(segments, currentVideoInfo.duration, null);
            statusLabel.textContent = "Segments found (waveform unavailable).";
            const reason = waveformError || waveformsData?.message || 'librosa not installed';
            window.updateConsole(`ℹ️ Waveform visualization disabled: ${reason}\n`);
        }
        
        // Update statistics
        const timelineStatsSpan = document.getElementById('timeline-stats');
        const zoomLevelSpan = document.getElementById('zoom-level');
        if (timelineStatsSpan && zoomLevelSpan) {
            const stats = timeline.getStatistics();
            if (stats.segmentCount > 0) {
                function formatTime(seconds) {
                    if (seconds < 60) {
                        return `${seconds.toFixed(1)}s`;
                    }
                    const mins = Math.floor(seconds / 60);
                    const secs = (seconds % 60).toFixed(1);
                    return `${mins}m ${secs}s`;
                }
                timelineStatsSpan.textContent = `Duration: ${formatTime(stats.totalDuration)} | Audible: ${formatTime(stats.audibleTime)} | Silence: ${stats.silencePercentage.toFixed(1)}% | Segments: ${stats.segmentCount}`;
            } else {
                timelineStatsSpan.textContent = "No segments detected";
            }
            zoomLevelSpan.textContent = `${timeline.zoom.toFixed(1)}x`;
        }
        
        // Send segments to the player for skip silence functionality
        player.setSegments(segments);
}

async function runAIAnalysis() {
    const statusLabel = document.getElementById('status-label');
    const aiAnalysisButton = document.getElementById('btn-ai-analysis');
    const apiKeyInput = document.getElementById('ai-api-key');
    const whisperModelSelect = document.getElementById('whisper-model-select');
    const aiModelSelect = document.getElementById('ai-model-select');
    const aiAnalysisStatus = document.getElementById('ai-analysis-status');
    const aiAnalysisSummary = document.getElementById('ai-analysis-summary');

    // Check if video is loaded
    if (!currentVideoInfo) {
        alert("Please load a video first!");
        return;
    }

    // Check if silence detection has been run (need segments)
    if (!timeline || !timeline.segments || timeline.segments.length === 0) {
        alert("Please run silence detection first!");
        return;
    }

    // Check if API key is provided
    const apiKey = apiKeyInput.value.trim();
    if (!apiKey) {
        alert("Please enter your together.ai API key in the AI Content Analysis settings!");
        return;
    }

    const whisperModel = whisperModelSelect.value;
    
    // Get selected AI model ID
    const selectedModelName = aiModelSelect.value;
    const togetherModel = AI_MODELS[selectedModelName]?.id || "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo";

    aiAnalysisButton.disabled = true;
    statusLabel.textContent = "Running AI analysis...";
    window.updateConsole(`\n${"=".repeat(60)}\n🤖 Starting AI Content Analysis...\n${"=".repeat(60)}\n`);
    console.log("JavaScript: Starting AI analysis...");
    console.log(`Using model: ${togetherModel} (${selectedModelName})`);

    try {
        const result = await window.pywebview.api.run_ai_analysis(
            currentVideoInfo.filePath,
            timeline.segments,
            apiKey,
            whisperModel,
            togetherModel
        );

        aiAnalysisButton.disabled = false;

        // Check for errors
        const { hasError, message, data } = checkError(result);
        if (hasError) {
            statusLabel.textContent = "AI analysis failed.";
            window.updateConsole(`❌ Error: ${message}\n`);
            console.error("Python Error:", message);
            return;
        }

        // Extract updated segments and summary
        const updatedSegments = data.segments || result.segments;
        const summary = data.analysis_summary || result.analysis_summary;

        console.log("AI analysis complete:", summary);
        console.log("Updated segments:", updatedSegments);
        // Log first few segments to see their AI decisions
        if (updatedSegments && updatedSegments.length > 0) {
            console.log("First 5 audible segments with AI decisions:");
            const audibleSegs = updatedSegments.filter(s => s.type === 'audible').slice(0, 5);
            audibleSegs.forEach((seg, idx) => {
                console.log(`  Segment ${idx}: keep=${seg.keep}, ai_decision=${seg.ai_decision}, confidence=${seg.ai_confidence}`);
            });
        }
        window.updateConsole(`\n✅ AI Analysis Complete!\n`);
        window.updateConsole(`   Analyzed: ${summary.segments_analyzed} segments\n`);
        window.updateConsole(`   ✅ KEEP: ${summary.keep_count}\n`);
        window.updateConsole(`   ⚠️  FLAG: ${summary.flag_count}\n`);
        window.updateConsole(`   ❓ UNCERTAIN: ${summary.uncertain_count}\n`);
        window.updateConsole(`   Confidence: ${(summary.avg_confidence * 100).toFixed(1)}%\n`);
        window.updateConsole(`   Time: ${summary.processing_time.toFixed(1)}s\n\n`);

        // Update timeline with AI-annotated segments
        // Get canvas width for waveform
        const canvasWidth = document.getElementById('waveform-canvas').offsetWidth;
        
        const waveformsResult = await window.pywebview.api.get_waveforms_all_tracks(
            currentVideoInfo.filePath,
            currentVideoInfo.audioTracks,
            canvasWidth
        );
        
        const { hasError: hasWaveformError, data: waveformsData } = checkError(waveformsResult);
        const waveforms = (!hasWaveformError && waveformsData) ? (waveformsData.waveforms || waveformsData) : null;
        
        // Redraw timeline with updated segments
        timeline.draw(updatedSegments, currentVideoInfo.duration, waveforms);
        
        // Update status display
        aiAnalysisStatus.style.display = 'block';
        aiAnalysisSummary.innerHTML = `
            <strong>Analysis Summary:</strong><br>
            ✅ Keep: ${summary.keep_count} | ⚠️ Flag: ${summary.flag_count} | ❓ Uncertain: ${summary.uncertain_count}<br>
            Confidence: ${(summary.avg_confidence * 100).toFixed(1)}%
        `;
        
        statusLabel.textContent = `AI analysis complete: ${summary.segments_analyzed} segments analyzed`;

        // Update player with new segments
        player.setSegments(updatedSegments);

        // Save to analysis history
        saveAnalysisResult({
            segments: updatedSegments,
            summary: summary,
            modelName: selectedModelName
        });

    } catch (error) {
        aiAnalysisButton.disabled = false;
        statusLabel.textContent = "AI analysis error.";
        window.updateConsole(`❌ Unexpected error: ${error}\n`);
        console.error("JavaScript Error:", error);
    }
}

async function exportVideo() {
    const statusLabel = document.getElementById('status-label');
    const exportButton = document.getElementById('btn-export-video');
    const encoderSelect = document.getElementById('encoder-select');
    const formatSelect = document.getElementById('format-select');
    const trimStartInput = document.getElementById('trim-start');
    const trimEndInput = document.getElementById('trim-end');

    if (!currentVideoInfo || !timeline.segments || timeline.segments.length === 0) {
        alert("Please load a video and detect segments first.");
        return;
    }

    if (!saveDestination) {
        alert("Please select a save destination first.");
        return;
    }

    // Get trim values
    const trimStart = parseFloat(trimStartInput.value) || 0;
    const trimEnd = trimEndInput.value ? parseFloat(trimEndInput.value) : null;

    // Validate trim values (client-side validation)
    if (trimStart < 0) {
        alert("Trim start must be >= 0");
        return;
    }
    if (trimEnd !== null && trimEnd <= trimStart) {
        alert("Trim end must be greater than trim start");
        return;
    }
    if (trimEnd !== null && trimEnd > currentVideoInfo.duration) {
        alert(`Trim end must be <= video duration (${currentVideoInfo.duration.toFixed(2)}s)`);
        return;
    }

    exportButton.disabled = true;
    exportButton.textContent = "Exporting...";
    statusLabel.textContent = "Exporting... (this may take a while)";
    
    // Reset progress
    window.updateProgress(0, "Calculating...", 0);
    window.clearConsole();
    window.updateConsole("Starting export...\n");

    console.log("JavaScript: Sending export request to Python...");

    const export_settings = {
        encoder: encoderSelect.value,
        format: formatSelect.value,
        save_path: saveDestination,
        trim_start: trimStartInput.value || null,
        trim_end: trimEndInput.value || null
    };

    let exportSucceeded = false;
    try {
        const result = await window.pywebview.api.export_video(
            currentVideoInfo,
            timeline.segments,
            export_settings
        );

        // Check for errors
        const { hasError, message, data } = checkError(result);
        
        if (!hasError && result.status === 'success') {
            window.updateProgress(100, "Complete", 0);
            statusLabel.textContent = "Export complete!";
            window.updateConsole("\n✅ Export completed successfully!\n");
            alert(result.message || "Export completed successfully!");
            exportSucceeded = true;
        } else if (result.status === 'cancelled') {
            statusLabel.textContent = "Export cancelled.";
            window.updateConsole("\n❌ Export cancelled by user.\n");
        } else {
            statusLabel.textContent = "Export failed.";
            const errorMsg = message || result.message || "Unknown error";
            window.updateConsole(`\n❌ Export failed: ${errorMsg}\n`);
            alert(`Export Failed: ${errorMsg}`);
        }
    } catch (error) {
        // Handle exceptions
        statusLabel.textContent = "Export failed.";
        window.updateConsole(`\n❌ Export error: ${error.message}\n`);
        alert(`Export Failed: ${error.message}`);
    } finally {
        // Always reset button and progress
        exportButton.disabled = false;
        exportButton.textContent = "Export Video";
        
        // Reset progress if not already set to 100%
        if (!exportSucceeded) {
            window.updateProgress(0, "Ready", 0);
        }
    }
}

async function exportCuts() {
    const statusLabel = document.getElementById('status-label');
    const exportCutsButton = document.getElementById('btn-export-cuts');

    if (!currentVideoInfo || !timeline.segments || timeline.segments.length === 0) {
        alert("Please load a video and detect segments first.");
        return;
    }

    if (!saveDestination) {
        alert("Please select a save destination first.");
        return;
    }

    // Get only audible segments (where keep=true or keep is undefined)
    const audibleSegments = timeline.segments.filter(seg => seg.keep !== false);
    
    if (audibleSegments.length === 0) {
        alert("No audible segments to export. All segments are marked for removal.");
        return;
    }

    exportCutsButton.disabled = true;
    exportCutsButton.textContent = "Exporting Cuts...";
    statusLabel.textContent = `Exporting ${audibleSegments.length} cut(s)...`;
    
    // Reset progress
    window.updateProgress(0, "Starting...", 0);
    window.clearConsole();
    window.updateConsole(`Starting export of ${audibleSegments.length} cut(s)...\n`);

    // Get trim values
    const trimStartInput = document.getElementById('trim-start');
    const trimEndInput = document.getElementById('trim-end');
    const trimStart = parseFloat(trimStartInput.value) || 0;
    const trimEnd = trimEndInput.value ? parseFloat(trimEndInput.value) : null;

    // Validate trim values (client-side validation)
    if (trimStart < 0) {
        alert("Trim start must be >= 0");
        exportCutsButton.disabled = false;
        exportCutsButton.textContent = "Export in Cuts";
        return;
    }
    if (trimEnd !== null && trimEnd <= trimStart) {
        alert("Trim end must be greater than trim start");
        exportCutsButton.disabled = false;
        exportCutsButton.textContent = "Export in Cuts";
        return;
    }
    if (trimEnd !== null && trimEnd > currentVideoInfo.duration) {
        alert(`Trim end must be <= video duration (${currentVideoInfo.duration.toFixed(2)}s)`);
        exportCutsButton.disabled = false;
        exportCutsButton.textContent = "Export in Cuts";
        return;
    }

    const export_settings = {
        encoder: document.getElementById('encoder-select').value,
        format: document.getElementById('format-select').value,
        save_path: saveDestination,
        trim_start: trimStartInput.value || null,
        trim_end: trimEndInput.value || null
    };

    let exportSucceeded = false;
    try {
        const result = await window.pywebview.api.export_video_cuts(
            currentVideoInfo,
            audibleSegments,
            export_settings
        );

        // Check for errors
        const { hasError, message, data } = checkError(result);
        
        if (!hasError && result.status === 'success') {
            window.updateProgress(100, "Complete", 0);
            statusLabel.textContent = `Export complete! ${audibleSegments.length} cut(s) exported.`;
            window.updateConsole(`\n✅ Export completed successfully! ${audibleSegments.length} cut(s) exported.\n`);
            alert(result.message || `Export completed! ${audibleSegments.length} cut(s) exported.`);
            exportSucceeded = true;
        } else if (result.status === 'cancelled') {
            statusLabel.textContent = "Export cancelled.";
            window.updateConsole("\n❌ Export cancelled by user.\n");
        } else {
            statusLabel.textContent = "Export failed.";
            const errorMsg = message || result.message || "Unknown error";
            window.updateConsole(`\n❌ Export failed: ${errorMsg}\n`);
            alert(`Export Failed: ${errorMsg}`);
        }
    } catch (error) {
        // Handle exceptions
        statusLabel.textContent = "Export failed.";
        window.updateConsole(`\n❌ Export error: ${error.message}\n`);
        alert(`Export Failed: ${error.message}`);
    } finally {
        // Always reset button and progress
        exportCutsButton.disabled = false;
        exportCutsButton.textContent = "Export in Cuts";
        
        // Reset progress if not already set to 100%
        if (!exportSucceeded) {
            window.updateProgress(0, "Ready", 0);
        }
    }
}

async function exportEdl() {
    const statusLabel = document.getElementById('status-label');
    const exportEdlButton = document.getElementById('btn-export-edl');

    if (!currentVideoInfo || !timeline.segments || timeline.segments.length === 0) {
        alert("Please load a video and detect segments first.");
        return;
    }

    // Get only audible segments (where keep=true or keep is undefined)
    const audibleSegments = timeline.segments.filter(seg => seg.keep !== false);
    
    if (audibleSegments.length === 0) {
        alert("No audible segments to export. All segments are marked for removal.");
        return;
    }

    exportEdlButton.disabled = true;
    exportEdlButton.textContent = "Exporting EDL...";
    statusLabel.textContent = "Exporting Edit Decision List...";
    
    window.clearConsole();
    window.updateConsole("Generating EDL file...\n");

    try {
        const result = await window.pywebview.api.export_edl(
            currentVideoInfo,
            audibleSegments
        );

        // Check for errors
        const { hasError, message, data } = checkError(result);
        
        if (!hasError && result.status === 'success') {
            statusLabel.textContent = "EDL export complete!";
            window.updateConsole(`\n✅ EDL file exported successfully!\n`);
            window.updateConsole(`📁 Saved to: ${result.message || result.file_path || 'Unknown location'}\n`);
            alert(`EDL file exported successfully!\n\n${result.message || result.file_path || 'File saved'}`);
        } else if (result.status === 'cancelled') {
            statusLabel.textContent = "EDL export cancelled.";
            window.updateConsole("\n❌ EDL export cancelled by user.\n");
        } else {
            statusLabel.textContent = "EDL export failed.";
            const errorMsg = message || result.message || "Unknown error";
            window.updateConsole(`\n❌ EDL export failed: ${errorMsg}\n`);
            alert(`EDL Export Failed: ${errorMsg}`);
        }
    } catch (error) {
        // Handle exceptions
        statusLabel.textContent = "EDL export failed.";
        window.updateConsole(`\n❌ EDL export error: ${error.message}\n`);
        alert(`EDL Export Failed: ${error.message}`);
    } finally {
        // Always reset button
        exportEdlButton.disabled = false;
        exportEdlButton.textContent = "Export Edit List (EDL)";
    }
}

async function exportXml() {
    const statusLabel = document.getElementById('status-label');
    const exportXmlButton = document.getElementById('btn-export-xml');

    if (!currentVideoInfo || !timeline.segments || timeline.segments.length === 0) {
        alert("Please load a video and detect segments first.");
        return;
    }

    // Get only audible segments (where keep=true or keep is undefined)
    const audibleSegments = timeline.segments.filter(seg => seg.keep !== false);
    
    if (audibleSegments.length === 0) {
        alert("No audible segments to export. All segments are marked for removal.");
        return;
    }

    exportXmlButton.disabled = true;
    exportXmlButton.textContent = "Exporting XML...";
    statusLabel.textContent = "Exporting FCP XML...";
    
    window.clearConsole();
    window.updateConsole("Generating FCP XML file...\n");

    try {
        const result = await window.pywebview.api.export_fcp_xml(
            currentVideoInfo,
            audibleSegments
        );

        // Check for errors
        const { hasError, message, data } = checkError(result);
        
        if (!hasError && result.status === 'success') {
            statusLabel.textContent = "XML export complete!";
            window.updateConsole(`\n✅ FCP XML file exported successfully!\n`);
            window.updateConsole(`📁 Saved to: ${result.message || result.file_path || 'Unknown location'}\n`);
            alert(`FCP XML file exported successfully!\n\n${result.message || result.file_path || 'File saved'}`);
        } else if (result.status === 'cancelled') {
            statusLabel.textContent = "XML export cancelled.";
            window.updateConsole("\n❌ XML export cancelled by user.\n");
        } else {
            statusLabel.textContent = "XML export failed.";
            const errorMsg = message || result.message || "Unknown error";
            window.updateConsole(`\n❌ XML export failed: ${errorMsg}\n`);
            alert(`XML Export Failed: ${errorMsg}`);
        }
    } catch (error) {
        // Handle exceptions
        statusLabel.textContent = "XML export failed.";
        window.updateConsole(`\n❌ XML export error: ${error.message}\n`);
        alert(`XML Export Failed: ${error.message}`);
    } finally {
        // Always reset button
        exportXmlButton.disabled = false;
        exportXmlButton.textContent = "Export FCP XML";
    }
}
