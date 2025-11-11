// web_ui/player.js

export class Player {
    constructor(videoElement) {
        this.videoElement = videoElement;
        this.onTimeUpdate = null;
        this.segments = [];
        this.skipSilence = false;
        
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

    loadVideo(filePath) {
        // PyWebView has a special 'pywebview.api.toggle_fullscreen' etc.
        // but for local files, we need to ask Python for a special URL.
        // For now, let's try the direct file path, but this is tricky.
        // A better way is to serve the file.
        
        // Let's create a URL that the local 'file://' protocol can use.
        // Note: This can fail due to browser security (CORS).
        console.log("Loading video with file path:", filePath);
        
        // We need to convert the path to a 'file:///' URL
        // But `pywebview` gives us a better way.
        
        // We will ask Python for a 'loadable' URL
        window.pywebview.api.get_loadable_file_url(filePath).then(url => {
            if (url) {
                console.log("Got loadable URL:", url);
                this.videoElement.src = url;
                this.videoElement.load();
            } else {
                console.error("Could not get loadable URL for video.");
            }
        });
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

