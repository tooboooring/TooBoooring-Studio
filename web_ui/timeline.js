// web_ui/timeline.js

export class Timeline {
    constructor(rulerCanvas, waveformCanvas, segmentsCanvas) {
        this.rulerCanvas = rulerCanvas;
        this.waveformCanvas = waveformCanvas;
        this.segmentsCanvas = segmentsCanvas;
        this.rulerCtx = rulerCanvas.getContext('2d');
        this.waveformCtx = waveformCanvas.getContext('2d');
        this.segmentsCtx = segmentsCanvas.getContext('2d');

        this.colors = {
            background: '#2B2B2B',
            text: '#CCC',
            line: '#444444',
            keep: '#2fb344',   // Green - for audible segments
            remove: '#ef4444',  // Red - for silent segments to remove
            removeAudible: '#ff8c00'  // Orange - for audible segments marked for removal
        };
        
        this.segments = [];
        this.duration = 0;
        this.playhead = 0;
        this.onSeek = null; // Will be a function: (timeSeconds) => {}
        this.onZoomChanged = null; // Will be a function: (zoomLevel) => {}
        this.waveformData = null; // Legacy: single waveform array (for backward compatibility)
        this.waveforms = {}; // Multi-track: {track_index: {waveform: [...], track_info: {...}}}
        
        // Zoom and scroll
        this.zoom = 1.0; // 1.0 = normal, >1.0 = zoomed in, <1.0 = zoomed out
        this.minZoom = 0.1;
        this.maxZoom = 100.0;
        this.scrollOffset = 0; // Horizontal scroll offset in seconds
        
        // Get reference to the scrollable wrapper (panel-content div)
        this.scrollWrapper = this.rulerCanvas.parentElement;
        
        // Set canvas size to match its display size
        this.resizeCanvas(this.rulerCanvas);
        this.resizeCanvas(this.waveformCanvas);
        this.resizeCanvas(this.segmentsCanvas);
    }

    resizeCanvas(canvas) {
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;
    }

    // Main function to call
    draw(segments, duration, waveformData) {
        this.segments = segments || [];
        this.duration = duration || 0;
        
        // Handle both single waveform (legacy) and multi-track waveforms
        if (waveformData && typeof waveformData === 'object' && !Array.isArray(waveformData)) {
            // Multi-track format: {track_index: {waveform: [...], track_info: {...}}}
            this.waveforms = waveformData;
            this.waveformData = null; // Clear legacy data
        } else {
            // Legacy single waveform format: array
            this.waveformData = waveformData;
            this.waveforms = {}; // Clear multi-track data
        }
        
        // Reset scroll if duration changed significantly
        const visibleDuration = this.duration / this.zoom;
        if (this.scrollOffset > this.duration - visibleDuration) {
            this.scrollOffset = Math.max(0, this.duration - visibleDuration);
        }
        
        this.resizeCanvas(this.rulerCanvas);
        this.resizeCanvas(this.waveformCanvas);
        this.resizeCanvas(this.segmentsCanvas);
        
        this.drawRuler(duration);
        this.drawWaveform(waveformData);
        this.drawSegments();
    }

    drawRuler(duration) {
        const ctx = this.rulerCtx;
        const w = this.rulerCanvas.width;
        const h = this.rulerCanvas.height;

        // Clear and draw background
        ctx.fillStyle = this.colors.background;
        ctx.fillRect(0, 0, w, h);

        if (duration <= 0) return;

        ctx.fillStyle = this.colors.text;
        ctx.font = '12px sans-serif';

        // Calculate visible time range
        const visibleDuration = duration / this.zoom;
        const startTime = this.scrollOffset;
        const endTime = Math.min(duration, startTime + visibleDuration);

        // Draw ticks based on zoom level
        const tickInterval = this.getTickInterval(visibleDuration);
        const firstTick = Math.ceil(startTime / tickInterval) * tickInterval;
        
        for (let time = firstTick; time <= endTime; time += tickInterval) {
            const x = this.timeToX(time, w, duration);
            if (x >= 0 && x <= w) {
                ctx.strokeStyle = this.colors.line;
                ctx.beginPath();
                ctx.moveTo(x, h);
                ctx.lineTo(x, h - 10);
                ctx.stroke();

                ctx.fillText(this.formatTime(time), x + 5, h - 15);
            }
        }
        
        // Draw the playhead
        this.drawPlayhead();
    }
    
    getTickInterval(visibleDuration) {
        // Choose tick interval based on visible duration
        if (visibleDuration <= 1) return 0.1;
        if (visibleDuration <= 10) return 1;
        if (visibleDuration <= 60) return 5;
        if (visibleDuration <= 300) return 30;
        return 60;
    }
    
    formatTime(seconds) {
        if (seconds < 60) {
            return seconds.toFixed(1) + 's';
        }
        const mins = Math.floor(seconds / 60);
        const secs = (seconds % 60).toFixed(1);
        return `${mins}m ${secs}s`;
    }
    
    timeToX(time, canvasWidth, duration) {
        const visibleDuration = duration / this.zoom;
        const startTime = this.scrollOffset;
        const relativeTime = time - startTime;
        return (relativeTime / visibleDuration) * canvasWidth;
    }
    
    xToTime(x, canvasWidth, duration) {
        const visibleDuration = duration / this.zoom;
        const startTime = this.scrollOffset;
        return startTime + (x / canvasWidth) * visibleDuration;
    }

    drawWaveform(data) {
        const ctx = this.waveformCtx;
        const w = this.waveformCanvas.width;
        const h = this.waveformCanvas.height;

        ctx.fillStyle = this.colors.background;
        ctx.fillRect(0, 0, w, h);

        if (this.duration <= 0) {
            return; // No duration
        }

        // Check if we have multi-track waveforms
        if (this.waveforms && Object.keys(this.waveforms).length > 0) {
            this.drawMultiWaveforms();
            return;
        }

        // Legacy: single waveform array
        if (!data || !Array.isArray(data) || data.length === 0) {
            return; // No data
        }

        ctx.strokeStyle = '#3b82f6'; // Blue
        ctx.lineWidth = 1;
        
        const mid_h = h / 2;
        
        // Calculate visible time range
        const visibleDuration = this.duration / this.zoom;
        const startTime = this.scrollOffset;
        const endTime = Math.min(this.duration, startTime + visibleDuration);
        
        ctx.beginPath();
        ctx.lineWidth = 1.5; // Slightly thicker lines
        
        for (let i = 0; i < data.length; i++) {
            const time = (i / data.length) * this.duration;
            
            // Only draw if within visible range
            if (time >= startTime && time <= endTime) {
                const x = this.timeToX(time, w, this.duration);
                const amplitude = data[i] * mid_h * 1.3; // 30% bigger amplitude
                
                if (x >= 0 && x <= w) {
                    ctx.moveTo(x, mid_h - amplitude);
                    ctx.lineTo(x, mid_h + amplitude);
                }
            }
        }
        ctx.stroke();
    }
    
    drawMultiWaveforms() {
        const ctx = this.waveformCtx;
        const w = this.waveformCanvas.width;
        const h = this.waveformCanvas.height;

        if (!this.waveforms || Object.keys(this.waveforms).length === 0) {
            return;
        }

        // Different colors for each track (matching Tkinter UI)
        const trackColors = ["#4a9eff", "#ff6b6b", "#51cf66", "#ffd43b", "#ff8c00", "#ba68c8"];
        const trackColorsDim = ["#2d5f99", "#993f3f", "#307a3d", "#997a23", "#99540a", "#6d3e75"];

        // Calculate how much height each track gets
        const numTracks = Object.keys(this.waveforms).length;
        const trackHeight = h / numTracks;

        // Sort tracks by index for consistent display order
        const sortedTracks = Object.entries(this.waveforms).sort((a, b) => parseInt(a[0]) - parseInt(b[0]));

        // Calculate visible time range
        const visibleDuration = this.duration / this.zoom;
        const startTime = this.scrollOffset;
        const endTime = Math.min(this.duration, startTime + visibleDuration);

        // Draw each track
        sortedTracks.forEach(([trackIndexStr, waveformData], idx) => {
            const trackIndex = parseInt(trackIndexStr);
            const waveform = waveformData.waveform;
            const trackInfo = waveformData.track_info || {};

            if (!waveform || !Array.isArray(waveform) || waveform.length === 0) {
                return; // Skip invalid waveforms
            }

            // Calculate vertical position for this track
            const trackYStart = idx * trackHeight;
            const trackCenterY = trackYStart + trackHeight / 2;

            // Get colors for this track
            const colorIdx = idx % trackColors.length;
            const activeColor = trackColors[colorIdx];
            const dimColor = trackColorsDim[colorIdx];

            // Draw separator line between tracks (except for first track)
            if (idx > 0) {
                ctx.strokeStyle = '#333333';
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(0, trackYStart);
                ctx.lineTo(w, trackYStart);
                ctx.stroke();
            }

            // Draw track label
            const labelText = trackInfo.name || `Track ${trackIndex + 1}`;
            ctx.fillStyle = '#FFFFFF';
            ctx.font = 'bold 8px sans-serif';
            ctx.fillText(labelText, 5, trackYStart + 10);

            // Draw the waveform
            ctx.lineWidth = 1.5; // Slightly thicker lines
            const maxAmplitude = (trackHeight / 2 - 15) * 1.3; // 30% bigger amplitude

            for (let i = 0; i < waveform.length; i++) {
                const time = (i / waveform.length) * this.duration;

                // Only draw if within visible range
                if (time >= startTime && time <= endTime) {
                    const x = this.timeToX(time, w, this.duration);

                    if (x >= 0 && x <= w) {
                        // Normalize amplitude (waveform is already normalized from Python)
                        const amplitude = Math.abs(waveform[i]) * maxAmplitude;

                        // Determine color based on whether this time is in an audible segment
                        let inAudibleSegment = false;
                        if (this.segments && this.segments.length > 0) {
                            inAudibleSegment = this.segments.some(seg =>
                                seg.type === 'audible' && seg.start <= time && time <= seg.end
                            );
                        }

                        ctx.strokeStyle = inAudibleSegment ? activeColor : dimColor;
                        ctx.beginPath();
                        ctx.moveTo(x, trackCenterY - amplitude);
                        ctx.lineTo(x, trackCenterY + amplitude);
                        ctx.stroke();
                    }
                }
            }
        });
    }

    drawSegments() { // No parameters needed, it uses 'this'
        const ctx = this.segmentsCtx;
        const w = this.segmentsCanvas.width;
        const h = this.segmentsCanvas.height;

        // Clear canvas with background color
        ctx.fillStyle = this.colors.background;
        ctx.fillRect(0, 0, w, h);

        if (!this.segments || this.segments.length === 0 || this.duration === 0) {
            ctx.fillStyle = this.colors.text;
            ctx.font = '12px sans-serif';
            ctx.fillText("No segments detected.", 10, h / 2);
            return;
        }

        // Calculate visible time range
        const visibleDuration = this.duration / this.zoom;
        const startTime = this.scrollOffset;
        const endTime = Math.min(this.duration, startTime + visibleDuration);

        // Draw each segment
        for (const segment of this.segments) {
            // Only draw if segment overlaps with visible range
            if (segment.end < startTime || segment.start > endTime) {
                continue;
            }
            
            // Calculate X positions for this segment
            const x_start = this.timeToX(Math.max(segment.start, startTime), w, this.duration);
            const x_end = this.timeToX(Math.min(segment.end, endTime), w, this.duration);
            const width = Math.max(1, x_end - x_start); // Ensure at least 1px width

            // Determine color based on segment type and keep status
            // Initialize keep property if it doesn't exist
            if (segment.keep === undefined) {
                segment.keep = (segment.type === 'audible'); // Audible defaults to true, silent defaults to false
            }
            
            if (segment.type === 'audible') {
                // Audible segments: green if kept, orange if removed
                ctx.fillStyle = segment.keep ? this.colors.keep : this.colors.removeAudible; // Green: #2fb344 or Orange: #ff8c00
            } else {
                // Silent segments: gray if kept, red if removed
                ctx.fillStyle = segment.keep ? '#666666' : this.colors.remove; // Gray or Red: #ef4444
            }
            
            // Draw the segment rectangle
            ctx.fillRect(x_start, 5, width, h - 10);
        }
    }

    bindClick() {
        // Attaches a click listener to the segments canvas
        this.segmentsCanvas.addEventListener('click', this.handleClick.bind(this));
    }

    handleClick(event) {
        if (!this.segments || this.segments.length === 0 || this.duration === 0) {
            return; // Nothing to click
        }

        const rect = this.segmentsCanvas.getBoundingClientRect();
        // Convert display coordinates to canvas coordinates
        const scaleX = this.segmentsCanvas.width / rect.width;
        const x = (event.clientX - rect.left) * scaleX;
        const w = this.segmentsCanvas.width;
        const timeClicked = this.xToTime(x, w, this.duration);

        // 1. Find the segment that was clicked
        let clickedSegment = null;
        for (const segment of this.segments) {
            if (timeClicked >= segment.start && timeClicked <= segment.end) {
                clickedSegment = segment;
                break;
            }
        }

        // 2. Toggle logic for BOTH audible and silent segments
        if (clickedSegment) {
            // Initialize keep property if it doesn't exist
            if (clickedSegment.keep === undefined) {
                // Audible segments default to keep=true, silent segments default to keep=false
                clickedSegment.keep = (clickedSegment.type === 'audible');
            }
            
            // Toggle the keep status
            clickedSegment.keep = !clickedSegment.keep;
            this.drawSegments();
            
            const segmentType = clickedSegment.type === 'audible' ? 'audible (green)' : 'silent (red)';
            console.log(`Toggled ${segmentType} segment: ${clickedSegment.start.toFixed(2)}s - ${clickedSegment.end.toFixed(2)}s, New keep status: ${clickedSegment.keep}`);
        }
        
        // 3. ALWAYS seek to clicked position (works for both green/audible and red/silent segments)
        if (this.onSeek) {
            this.onSeek(timeClicked);
        }
    }

    drawPlayhead() {
        if (this.duration <= 0) {
            return; // Can't draw playhead without duration
        }
        
        const ctx = this.rulerCtx;
        const w = this.rulerCanvas.width;
        const h = this.rulerCanvas.height;

        // Calculate X position using zoom/scroll
        const x = this.timeToX(this.playhead, w, this.duration);
        
        // Only draw if visible
        if (x < 0 || x > w) {
            return;
        }

        // Draw red line
        ctx.strokeStyle = '#ef4444'; // Red
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
    }

    updatePlayhead(timeSeconds) {
        this.playhead = timeSeconds;
        this.ensurePlayheadVisible();

        // Redraw the ruler (which clears, draws ticks, and draws the playhead)
        if (this.duration > 0) {
            this.drawRuler(this.duration);
        }
    }

    bindRulerClick() {
        this.rulerCanvas.addEventListener('click', (event) => {
            if (this.duration === 0) return;

            const rect = this.rulerCanvas.getBoundingClientRect();
            // Convert display coordinates to canvas coordinates
            const scaleX = this.rulerCanvas.width / rect.width;
            const x = (event.clientX - rect.left) * scaleX;
            const w = this.rulerCanvas.width;
            const timeClicked = this.xToTime(x, w, this.duration);

            if (this.onSeek) {
                this.onSeek(timeClicked);
            }
        });
    }
    
    // Zoom methods
    zoomIn() {
        const oldZoom = this.zoom;
        this.zoom = Math.min(this.maxZoom, this.zoom * 1.5);
        if (oldZoom !== this.zoom) {
            this.ensurePlayheadVisible();
            this.redraw();
            if (this.onZoomChanged) {
                this.onZoomChanged(this.zoom);
            }
        }
    }
    
    zoomOut() {
        const oldZoom = this.zoom;
        this.zoom = Math.max(this.minZoom, this.zoom / 1.5);
        if (oldZoom !== this.zoom) {
            this.ensurePlayheadVisible();
            this.redraw();
            if (this.onZoomChanged) {
                this.onZoomChanged(this.zoom);
            }
        }
    }
    
    setZoom(level) {
        const oldZoom = this.zoom;
        this.zoom = Math.max(this.minZoom, Math.min(this.maxZoom, level));
        if (oldZoom !== this.zoom) {
            this.ensurePlayheadVisible();
            this.redraw();
            // Notify listeners of zoom change
            if (this.onZoomChanged) {
                this.onZoomChanged(this.zoom);
            }
        }
    }
    
    // Scroll methods
    scrollLeft() {
        const visibleDuration = this.duration / this.zoom;
        const scrollAmount = visibleDuration * 0.2;
        this.scrollOffset = Math.max(0, this.scrollOffset - scrollAmount);
        this.redraw();
    }
    
    scrollRight() {
        const visibleDuration = this.duration / this.zoom;
        const maxScroll = Math.max(0, this.duration - visibleDuration);
        const scrollAmount = visibleDuration * 0.2;
        this.scrollOffset = Math.min(maxScroll, this.scrollOffset + scrollAmount);
        this.redraw();
    }
    
    scrollToStart() {
        this.scrollOffset = 0;
        this.redraw();
    }
    
    scrollToEnd() {
        const visibleDuration = this.duration / this.zoom;
        this.scrollOffset = Math.max(0, this.duration - visibleDuration);
        this.redraw();
    }
    
    ensurePlayheadVisible() {
        const visibleDuration = this.duration / this.zoom;
        const endTime = this.scrollOffset + visibleDuration;
        
        if (this.playhead < this.scrollOffset) {
            this.scrollOffset = Math.max(0, this.playhead - visibleDuration * 0.1);
        } else if (this.playhead > endTime) {
            this.scrollOffset = Math.min(this.duration - visibleDuration, this.playhead - visibleDuration * 0.9);
        }
    }
    
    redraw() {
        if (this.duration > 0) {
            this.drawRuler(this.duration);
            // Use multi-track waveforms if available, otherwise fall back to single waveform
            const waveformData = Object.keys(this.waveforms).length > 0 ? this.waveforms : this.waveformData;
            this.drawWaveform(waveformData);
            this.drawSegments();
        }
    }
    
    // Statistics
    getStatistics() {
        if (!this.segments || this.segments.length === 0 || this.duration <= 0) {
            return {
                totalDuration: this.duration,
                audibleTime: 0,
                silenceTime: 0,
                silencePercentage: 0,
                segmentCount: 0
            };
        }
        
        let audibleTime = 0;
        let silenceTime = 0;
        
        for (const segment of this.segments) {
            const duration = segment.end - segment.start;
            if (segment.type === 'audible') {
                audibleTime += duration;
            } else {
                silenceTime += duration;
            }
        }
        
        return {
            totalDuration: this.duration,
            audibleTime: audibleTime,
            silenceTime: silenceTime,
            silencePercentage: (silenceTime / this.duration) * 100,
            segmentCount: this.segments.length
        };
    }
    
    // Mouse wheel zoom (Ctrl + Scroll)
    bindWheelEvents() {
        // Listen for wheel events on the scrollable wrapper
        if (!this.scrollWrapper) return;
        
        this.scrollWrapper.addEventListener('wheel', (event) => {
            if (event.ctrlKey || event.metaKey) { // Ctrl on Windows/Linux, Cmd on Mac
                event.preventDefault(); // Stop the page from zooming
                
                // Calculate zoom change based on scroll direction
                const zoomAmount = event.deltaY * -0.01; // Negative deltaY = scroll up = zoom in
                const newZoom = Math.max(this.minZoom, Math.min(this.maxZoom, this.zoom + zoomAmount));
                
                if (newZoom !== this.zoom) {
                    this.setZoom(newZoom);
                }
            }
            // If Ctrl/Cmd is not held, allow normal horizontal scrolling
        }, { passive: false });
    }
    
    // Keyboard navigation (Arrow keys, Home/End)
    bindKeyEvents() {
        // Listen for keyboard events on the window
        // Only handle keys when timeline has data and is focused
        window.addEventListener('keydown', (event) => {
            // Only handle if we have a duration and the timeline is likely visible
            if (this.duration <= 0) return;
            
            // Check if user is typing in an input field (don't intercept)
            const target = event.target;
            if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
                return;
            }
            
            let newTime = this.playhead;
            let seek = false;
            
            if (event.key === 'ArrowLeft') {
                newTime = Math.max(0, this.playhead - 1); // Seek back 1 second
                seek = true;
            } else if (event.key === 'ArrowRight') {
                newTime = Math.min(this.duration, this.playhead + 1); // Seek forward 1 second
                seek = true;
            } else if (event.key === 'Home') {
                newTime = 0;
                seek = true;
            } else if (event.key === 'End') {
                newTime = this.duration;
                seek = true;
            }
            
            if (seek && this.onSeek) {
                event.preventDefault(); // Stop arrow keys from scrolling the page
                this.onSeek(newTime);
            }
        });
    }
}