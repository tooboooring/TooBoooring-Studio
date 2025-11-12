// web_ui/player.js

export class Player {
    constructor(videoElement) {
        this.videoElement = videoElement;
        this.onTimeUpdate = null;
        this.segments = [];
        this.skipSilence = false;
        this.audioTracks = [];
        this.currentAudioTrackIndex = null;
        this.originalVideoPath = null;
        this.enabledTrackIndices = []; // Track which tracks are enabled
        
        // Listen for timeupdate events from the video element
        this.videoElement.addEventListener('timeupdate', () => {
            const currentTime = this.videoElement.currentTime;

            // 1. Always update the playhead
            if (this.onTimeUpdate) {
                this.onTimeUpdate(currentTime);
            }

            // 2. Check for "Skip Silence"
            if (this.skipSilence && this.segments.length > 0) {
                // Loop through segments
                for (const segment of this.segments) {
                    // Check if we are inside a segment that should be skipped
                    if (!segment.keep) { // Find segments to remove
                        const start = segment.start;
                        const end = segment.end;

                        // Check if current time is inside this "bad" segment
                        // Add a small buffer (0.1s) to prevent getting stuck
                        if (currentTime >= start && currentTime < (end - 0.1)) {
                            console.log(`Skipping segment from ${start.toFixed(2)} to ${end.toFixed(2)}`);

                            // Jump to the end of this segment
                            this.videoElement.currentTime = end;
                            break; // Exit loop after a jump
                        }
                    }
                }
            }
        });
    }

    loadVideo(filePath, audioTracks = []) {
        // PyWebView has a special 'pywebview.api.toggle_fullscreen' etc.
        // but for local files, we need to ask Python for a special URL.
        // For now, let's try the direct file path, but this is tricky.
        // A better way is to serve the file.
        
        // Let's create a URL that the local 'file://' protocol can use.
        // Note: This can fail due to browser security (CORS).
        console.log("Loading video with file path:", filePath);
        
        // Store original video path and audio tracks info
        this.originalVideoPath = filePath;
        this.audioTracks = audioTracks || [];
        
        // We need to convert the path to a 'file:///' URL
        // But `pywebview` gives us a better way.
        
        // We will ask Python for a 'loadable' URL
        window.pywebview.api.get_loadable_file_url(filePath).then(url => {
            if (url) {
                console.log("Got loadable URL:", url);
                this.videoElement.src = url;
                this.videoElement.load();
                
                // Wait for video metadata to load, then set up audio track selection
                this.videoElement.addEventListener('loadedmetadata', () => {
                    this.setupAudioTracks();
                }, { once: true });
            } else {
                console.error("Could not get loadable URL for video.");
            }
        });
    }
    
    setupAudioTracks() {
        // Try to use HTML5 audioTracks API if available
        if (this.videoElement.audioTracks && this.videoElement.audioTracks.length > 0) {
            console.log(`Found ${this.videoElement.audioTracks.length} audio track(s) in video element`);
            
            // Enable the first track by default
            if (this.videoElement.audioTracks.length > 0) {
                this.videoElement.audioTracks[0].enabled = true;
                // Disable others
                for (let i = 1; i < this.videoElement.audioTracks.length; i++) {
                    this.videoElement.audioTracks[i].enabled = false;
                }
            }
        } else {
            console.log("audioTracks API not available, using fallback method");
        }
    }
    
    setAudioTrack(trackIndex) {
        // Try to use HTML5 audioTracks API
        if (this.videoElement.audioTracks && this.videoElement.audioTracks.length > 0) {
            // Disable all tracks first
            for (let i = 0; i < this.videoElement.audioTracks.length; i++) {
                this.videoElement.audioTracks[i].enabled = false;
            }
            
            // Enable the selected track
            if (trackIndex >= 0 && trackIndex < this.videoElement.audioTracks.length) {
                this.videoElement.audioTracks[trackIndex].enabled = true;
                this.currentAudioTrackIndex = trackIndex;
                console.log(`Switched to audio track ${trackIndex}`);
            }
        } else {
            // Fallback: If audioTracks API is not available, we'll need to use FFmpeg
            // For now, just log a message
            console.log(`Audio track selection requested for track ${trackIndex}, but audioTracks API not available`);
            this.currentAudioTrackIndex = trackIndex;
            
            // Note: To actually switch tracks, we would need to:
            // 1. Use FFmpeg to create a temporary video with only the selected track
            // 2. Or use a media source extension (MSE) approach
            // For now, we'll just store the preference
        }
    }
    
    async updateAudioTracks(enabledTrackIndices) {
        // This will be called when track mute buttons are clicked
        // We'll use Python backend to create a temporary video with selected tracks
        if (!this.originalVideoPath) {
            console.error("No original video path available");
            return;
        }
        
        console.log(`Updating audio tracks: ${enabledTrackIndices}`);
        
        // Call Python to create video with selected tracks
        try {
            const tempVideoPath = await window.pywebview.api.create_video_with_audio_tracks(
                this.originalVideoPath,
                enabledTrackIndices
            );
            
            if (tempVideoPath) {
                // Load the new video
                const url = await window.pywebview.api.get_loadable_file_url(tempVideoPath);
                if (url) {
                    const wasPlaying = !this.videoElement.paused;
                    const currentTime = this.videoElement.currentTime;
                    
                    this.videoElement.src = url;
                    this.videoElement.load();
                    
                    // Restore playback state
                    this.videoElement.addEventListener('loadedmetadata', () => {
                        this.videoElement.currentTime = currentTime;
                        if (wasPlaying) {
                            this.videoElement.play();
                        }
                    }, { once: true });
                }
            } else {
                // No temp file means use original (all tracks)
                const url = await window.pywebview.api.get_loadable_file_url(this.originalVideoPath);
                if (url) {
                    const wasPlaying = !this.videoElement.paused;
                    const currentTime = this.videoElement.currentTime;
                    
                    this.videoElement.src = url;
                    this.videoElement.load();
                    
                    this.videoElement.addEventListener('loadedmetadata', () => {
                        this.videoElement.currentTime = currentTime;
                        if (wasPlaying) {
                            this.videoElement.play();
                        }
                    }, { once: true });
                }
            }
        } catch (error) {
            console.error("Error updating audio tracks:", error);
        }
    }

    seek(timeSeconds) {
        this.videoElement.currentTime = timeSeconds;
    }

    setSegments(segments) {
        this.segments = segments || [];
    }

    setSkipSilence(skip) {
        this.skipSilence = skip;
        console.log("Skip Silence set to:", this.skipSilence);
    }

    previousFrame() {
        // Step back by 1/30 second (or try to get actual FPS)
        const step = 1 / 30; // Default to 30 fps
        this.videoElement.currentTime = Math.max(0, this.videoElement.currentTime - step);
    }

    nextFrame() {
        // Step forward by 1/30 second
        const step = 1 / 30; // Default to 30 fps
        this.videoElement.currentTime = Math.min(
            this.videoElement.duration || Infinity,
            this.videoElement.currentTime + step
        );
    }

    stop() {
        this.videoElement.pause();
        this.videoElement.currentTime = 0;
    }

    formatTime(seconds) {
        if (!isFinite(seconds) || isNaN(seconds)) return "00:00:00";
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    getCurrentTime() {
        return this.videoElement.currentTime || 0;
    }

    getDuration() {
        return this.videoElement.duration || 0;
    }
}

