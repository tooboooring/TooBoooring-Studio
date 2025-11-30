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
            keep: '#2fb344',           // Green - audible segments that will be kept
            aiFlag: '#9333ea',          // Purple - segments the AI flagged for removal
            uncertain: '#f59e0b',       // Orange - uncertain segments (default to flagged)
            manualRemove: '#f59e0b',    // Orange - manually removed segments
            remove: '#ef4444',          // Red - silence segments that will be removed
            silentKeep: '#4a4a4a'        // Gray - silent segments that are kept
        };
        
        this.segments = [];
        this.duration = 0;
        this.playhead = 0;
        this.onSeek = null; // Will be a function: (timeSeconds) => {}
        this.onZoomChanged = null; // Will be a function: (zoomLevel) => {}
        this.waveformData = null; // Legacy: single waveform array (for backward compatibility)
        this.waveforms = {}; // Multi-track: {track_index: {waveform: [...], track_info: {...}}}
        
        // Zoom and scroll
        // Use config values if available, otherwise defaults
        const config = window.app?.config || {};
        const timelineConfig = config.ui_settings?.timeline || {};
        this.zoom = 1.0; // 1.0 = normal, >1.0 = zoomed in, <1.0 = zoomed out
        this.minZoom = timelineConfig.min_zoom || 0.1;
        this.maxZoom = timelineConfig.max_zoom || 100.0;
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
        console.log("Timeline.draw() called with", segments ? segments.length : 0, "segments");
        if (segments && segments.length > 0) {
            const audibleSegs = segments.filter(s => s.type === 'audible').slice(0, 5);
            console.log("  First 5 audible segments in draw():", audibleSegs.map(s => ({ 
                start: s.start.toFixed(1), 
                keep: s.keep, 
                ai_decision: s.ai_decision,
                type: s.type
            })));
        }
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

        ctx.strokeStyle = '#4a9eff'; // Blue
        ctx.fillStyle = '#4a9eff';
        ctx.lineWidth = 1.5;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        
        const mid_h = h / 2;
        const padding = 8;
        const maxAmplitude = (h / 2) - padding;
        
        // Normalize waveform to use full amplitude range
        const maxValue = Math.max(...data.map(v => Math.abs(v)));
        const normalizeFactor = maxValue > 0 ? 1.0 / maxValue : 1.0;
        
        // Calculate visible time range
        const visibleDuration = this.duration / this.zoom;
        const startTime = this.scrollOffset;
        const endTime = Math.min(this.duration, startTime + visibleDuration);
        
        // Prepare waveform points for smooth rendering
        const waveformPoints = [];
        for (let i = 0; i < data.length; i++) {
            const time = (i / data.length) * this.duration;
            if (time >= startTime && time <= endTime) {
                const x = this.timeToX(time, w, this.duration);
                if (x >= 0 && x <= w) {
                    const normalizedValue = data[i] * normalizeFactor;
                    const amplitude = normalizedValue * maxAmplitude;
                    waveformPoints.push({
                        x: x,
                        y: mid_h - amplitude
                    });
                }
            }
        }

        if (waveformPoints.length === 0) return;

        // Draw smooth continuous waveform (top half)
        ctx.globalAlpha = 0.85;
        ctx.beginPath();
        ctx.moveTo(waveformPoints[0].x, waveformPoints[0].y);
        for (let i = 1; i < waveformPoints.length; i++) {
            ctx.lineTo(waveformPoints[i].x, waveformPoints[i].y);
        }
        ctx.stroke();

        // Draw smooth continuous waveform (bottom half - symmetric)
        ctx.beginPath();
        ctx.moveTo(waveformPoints[0].x, mid_h + (mid_h - waveformPoints[0].y));
        for (let i = 1; i < waveformPoints.length; i++) {
            const bottomY = mid_h + (mid_h - waveformPoints[i].y);
            ctx.lineTo(waveformPoints[i].x, bottomY);
        }
        ctx.stroke();
        ctx.globalAlpha = 1.0;
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

        // Calculate track height - use minimum height to keep waveforms visible
        const numTracks = Object.keys(this.waveforms).length;
        const minTrackHeight = 80; // Minimum height per track for good visibility
        const calculatedHeight = h / numTracks;
        
        // Use the larger of calculated height or minimum height to ensure visibility
        const trackHeight = Math.max(calculatedHeight, minTrackHeight);

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
            // If tracks would overflow canvas height, scale them proportionally
            const totalRequiredHeight = numTracks * trackHeight;
            const scaleFactor = totalRequiredHeight > h ? h / totalRequiredHeight : 1;
            
            const scaledTrackHeight = trackHeight * scaleFactor;
            const trackYStart = idx * scaledTrackHeight;
            const trackCenterY = trackYStart + scaledTrackHeight / 2;
            const maxAmplitude = (scaledTrackHeight / 2) - 2; // 2px padding

            // Get colors for this track
            const colorIdx = idx % trackColors.length;
            const activeColor = trackColors[colorIdx];
            const dimColor = trackColorsDim[colorIdx];

            // Draw separator line between tracks (except for first track)
            if (idx > 0) {
                ctx.fillStyle = '#333333';
                ctx.fillRect(0, trackYStart, w, 1);
            }

            // Draw track label
            const labelText = trackInfo.name || `Track ${trackIndex + 1}`;
            ctx.fillStyle = '#FFFFFF';
            ctx.font = 'bold 10px sans-serif';
            ctx.fillText(labelText, 6, trackYStart + 14);

            // --- PRO PEAK RENDERING ---
            
            const samplesPerPixel = (waveform.length / this.duration) * (visibleDuration / w);
            // Normalize audio data (0.0 to 1.0)
            const globalMax = Math.max(...waveform.map(v => Math.abs(v)));
            const normFactor = globalMax > 0 ? 1 / globalMax : 1;

            // We loop through pixels (X) rather than samples. 
            // This ensures 1 pixel = 1 vertical bar. Crisp.
            for (let x = 0; x < w; x++) {
                // 1. Determine time window for this pixel
                const pixelStartTime = startTime + (x / w) * visibleDuration;
                
                // 2. Map to array indices
                const exactIndex = (pixelStartTime / this.duration) * waveform.length;
                const startIndex = Math.floor(exactIndex);
                
                let val = 0;

                // 3. Calculate Amplitude
                if (samplesPerPixel >= 1.0) {
                    // ZOOMED OUT: We have many samples per pixel. Find the Peak (Max).
                    // This creates the solid "wall" look.
                    const endIndex = Math.floor(startIndex + samplesPerPixel);
                    const safeEnd = Math.min(waveform.length, endIndex + 1); // +1 to ensure we read at least one
                    
                    for (let i = startIndex; i < safeEnd; i++) {
                        const absV = Math.abs(waveform[i]);
                        if (absV > val) val = absV;
                    }
                } else {
                    // ZOOMED IN: 1 sample covers many pixels. 
                    // Use Linear Interpolation to connect points sharply (no curves, no blocks).
                    const i = startIndex;
                    if (i >= 0 && i < waveform.length - 1) {
                        const v1 = Math.abs(waveform[i]);
                        const v2 = Math.abs(waveform[i+1]);
                        const t = exactIndex - i; // fractional part
                        val = v1 + (v2 - v1) * t; // Linear Lerp
                    } else if (i < waveform.length) {
                         val = Math.abs(waveform[i]);
                    }
                }

                // 4. Check Segments (Audible vs Silent coloring)
                let isAudible = false;
                if (this.segments) {
                    // Check if the center of this pixel time is inside a segment
                    const checkTime = pixelStartTime + (visibleDuration/w)/2;
                    isAudible = this.segments.some(seg => 
                        seg.type === 'audible' && seg.start <= checkTime && checkTime <= seg.end
                    );
                }

                // 5. Draw Vertical Line
                const barHeight = Math.max(1, val * normFactor * maxAmplitude);
                
                ctx.fillStyle = isAudible ? activeColor : dimColor;
                ctx.globalAlpha = isAudible ? 1.0 : 0.5;

                // Draw from center up and center down (Mirrored)
                // Using fillRect with width 1 creates a solid, sharp line.
                ctx.fillRect(x, trackCenterY - barHeight, 1, barHeight * 2);
            }
            ctx.globalAlpha = 1.0;
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

        // Segment display settings
        const topPadding = 5;
        const bottomPadding = 8; // Bottom padding as requested
        const segmentHeight = h - topPadding - bottomPadding; // Reduced height with padding

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

            // Determine color based on segment type, keep status, and AI decision
            // Initialize keep property if it doesn't exist
            if (segment.keep === undefined) {
                segment.keep = (segment.type === 'audible'); // Audible defaults to true, silent defaults to false
            }
            
            if (segment.type === 'audible') {
                // Audible segments: green if kept, otherwise check AI decision
                if (segment.keep) {
                    ctx.fillStyle = this.colors.keep; // Green: #2fb344
                } else {
                    // Determine color based on why it's being removed
                    // Backend uses lowercase: 'flag', 'uncertain', 'keep'
                    const aiDecision = (segment.ai_decision || '').toLowerCase();
                    if (aiDecision === 'flag') {
                        ctx.fillStyle = this.colors.aiFlag; // Purple: #9333ea - AI flagged
                    } else if (aiDecision === 'uncertain') {
                        ctx.fillStyle = this.colors.uncertain; // Orange: #f59e0b - Uncertain
                    } else {
                        ctx.fillStyle = this.colors.manualRemove; // Orange: #f59e0b - Manual removal
                    }
                }
            } else {
                // Silent segments: gray if kept, red if removed
                ctx.fillStyle = segment.keep ? this.colors.silentKeep : this.colors.remove; // Gray: #4a4a4a or Red: #ef4444
            }
            
            // Draw the segment rectangle (with padding)
            ctx.fillRect(x_start, topPadding, width, segmentHeight);
        }
    }

    bindClick() {
        // Attaches click and drag listeners to the segments canvas
        // Click toggles segments, drag seeks
        let isDragging = false;
        let dragStartX = 0;
        let hasMoved = false;
        
        const handleMouseDown = (event) => {
            if (this.duration === 0) return;
            isDragging = true;
            hasMoved = false;
            dragStartX = event.clientX;
        };
        
        const handleMouseMove = (event) => {
            if (!isDragging || this.duration === 0) return;
            
            // Check if mouse has moved significantly (more than 3 pixels)
            if (Math.abs(event.clientX - dragStartX) > 3) {
                hasMoved = true;
            }
            
            if (hasMoved) {
                // Dragging - seek to position
                const rect = this.segmentsCanvas.getBoundingClientRect();
                const scaleX = this.segmentsCanvas.width / rect.width;
                const x = (event.clientX - rect.left) * scaleX;
                const w = this.segmentsCanvas.width;
                const timeDragged = this.xToTime(x, w, this.duration);
                
                // Clamp time to valid range
                const clampedTime = Math.max(0, Math.min(this.duration, timeDragged));
                
                // Update playhead during drag
                this.playhead = clampedTime;
                this.ensurePlayheadVisible();
                this.redraw();
                
                // Seek to dragged position
                if (this.onSeek) {
                    this.onSeek(clampedTime);
                }
            }
        };
        
        const handleMouseUp = (event) => {
            if (!isDragging) return;
            isDragging = false;
            
            // If mouse didn't move much, treat as click (toggle segment)
            if (!hasMoved) {
                this.handleClick(event);
            }
        };
        
        this.segmentsCanvas.addEventListener('mousedown', handleMouseDown);
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        this.segmentsCanvas.addEventListener('mouseleave', () => {
            isDragging = false;
        });
        
        // Change cursor to indicate draggable
        this.segmentsCanvas.style.cursor = 'pointer';
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
        
        // Calculate X position using zoom/scroll (use ruler width as reference)
        const w = this.rulerCanvas.width;
        const x = this.timeToX(this.playhead, w, this.duration);
        
        // Only draw if visible
        if (x < 0 || x > w) {
            return;
        }

        // Draw on ruler canvas (called from drawRuler)
        const rulerCtx = this.rulerCtx;
        const rulerH = this.rulerCanvas.height;
        rulerCtx.strokeStyle = '#ef4444'; // Bright red
        rulerCtx.lineWidth = 3; // Thicker for better visibility
        rulerCtx.beginPath();
        rulerCtx.moveTo(x, 0);
        rulerCtx.lineTo(x, rulerH);
        rulerCtx.stroke();
    }

    updatePlayhead(timeSeconds) {
        this.playhead = timeSeconds;
        this.ensurePlayheadVisible();

        // Redraw everything to clear old playhead and draw new one
        if (this.duration > 0) {
            this.redraw();
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
    
    bindWaveformClick() {
        // Add click and drag handlers to waveform canvas for seeking
        let isDragging = false;
        
        const handleMouseDown = (event) => {
            if (this.duration === 0) return;
            isDragging = true;
            
            const rect = this.waveformCanvas.getBoundingClientRect();
            const scaleX = this.waveformCanvas.width / rect.width;
            const x = (event.clientX - rect.left) * scaleX;
            const w = this.waveformCanvas.width;
            const timeClicked = this.xToTime(x, w, this.duration);
            
            // Clamp time to valid range
            const clampedTime = Math.max(0, Math.min(this.duration, timeClicked));
            
            // Update playhead immediately
            this.playhead = clampedTime;
            this.redraw();
            
            // Seek to clicked position
            if (this.onSeek) {
                this.onSeek(clampedTime);
            }
        };
        
        const handleMouseMove = (event) => {
            if (!isDragging || this.duration === 0) return;
            
            const rect = this.waveformCanvas.getBoundingClientRect();
            const scaleX = this.waveformCanvas.width / rect.width;
            const x = (event.clientX - rect.left) * scaleX;
            const w = this.waveformCanvas.width;
            const timeDragged = this.xToTime(x, w, this.duration);
            
            // Clamp time to valid range
            const clampedTime = Math.max(0, Math.min(this.duration, timeDragged));
            
            // Update playhead during drag
            this.playhead = clampedTime;
            this.ensurePlayheadVisible();
            this.redraw();
            
            // Seek to dragged position
            if (this.onSeek) {
                this.onSeek(clampedTime);
            }
        };
        
        const handleMouseUp = () => {
            isDragging = false;
        };
        
        const handleMouseLeave = () => {
            isDragging = false;
        };
        
        // Add event listeners to waveform canvas only
        // Use document-level listeners for mousemove/mouseup so dragging works even outside canvas
        this.waveformCanvas.addEventListener('mousedown', handleMouseDown);
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        this.waveformCanvas.addEventListener('mouseleave', handleMouseLeave);
        
        // Change cursor to indicate draggable
        this.waveformCanvas.style.cursor = 'pointer';
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
            // Draw ruler (includes playhead on ruler canvas)
            this.drawRuler(this.duration);
            
            // Use multi-track waveforms if available, otherwise fall back to single waveform
            const waveformData = Object.keys(this.waveforms).length > 0 ? this.waveforms : this.waveformData;
            this.drawWaveform(waveformData);
            this.drawSegments();
            
            // Draw playhead on waveform and segments canvases (after they've been cleared and redrawn)
            this.drawPlayheadOnAllCanvases();
        }
    }
    
    drawPlayheadOnAllCanvases() {
        if (this.duration <= 0) {
            return;
        }
        
        // Calculate X position
        const w = this.rulerCanvas.width;
        const x = this.timeToX(this.playhead, w, this.duration);
        
        // Only draw if visible
        if (x < 0 || x > w) {
            return;
        }
        
        // Draw on waveform canvas
        const waveCtx = this.waveformCtx;
        const waveH = this.waveformCanvas.height;
        waveCtx.strokeStyle = '#ef4444';
        waveCtx.lineWidth = 3;
        waveCtx.beginPath();
        waveCtx.moveTo(x, 0);
        waveCtx.lineTo(x, waveH);
        waveCtx.stroke();
        
        // Draw on segments canvas
        const segCtx = this.segmentsCtx;
        const segH = this.segmentsCanvas.height;
        segCtx.strokeStyle = '#ef4444';
        segCtx.lineWidth = 3;
        segCtx.beginPath();
        segCtx.moveTo(x, 0);
        segCtx.lineTo(x, segH);
        segCtx.stroke();
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
            // Check if user is typing in an input field (don't intercept)
            const target = event.target;
            if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
                return;
            }
            
            // === PROJECT SAVE/LOAD SHORTCUTS ===
            
            // Ctrl+S or Cmd+S: Save Project
            if ((event.ctrlKey || event.metaKey) && event.key === 's' && !event.shiftKey) {
                event.preventDefault(); // Prevent browser's default save dialog
                console.log("Keyboard shortcut: Ctrl+S (Save Project)");
                this.handleSaveShortcut();
                return;
            }
            
            // Ctrl+Shift+S or Cmd+Shift+S: Save As
            if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'S') {
                event.preventDefault();
                console.log("Keyboard shortcut: Ctrl+Shift+S (Save As)");
                this.handleSaveAsShortcut();
                return;
            }
            
            // Ctrl+O or Cmd+O: Open Project
            if ((event.ctrlKey || event.metaKey) && event.key === 'o') {
                event.preventDefault(); // Prevent browser's default open dialog
                console.log("Keyboard shortcut: Ctrl+O (Open Project)");
                this.handleOpenShortcut();
                return;
            }
            
            // === TIMELINE NAVIGATION (existing functionality) ===
            
            // Only handle if we have a duration and the timeline is likely visible
            if (this.duration <= 0) return;
            
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
    
    /**
     * Handle Ctrl+S keyboard shortcut (Quick Save).
     * 
     * Calls the global saveProject function if available, or shows a message.
     */
    async handleSaveShortcut() {
        try {
            // Check if quickSave function is available globally
            if (typeof window.quickSave === 'function') {
                await window.quickSave(this);
            } else if (typeof window.saveProject === 'function') {
                // Fallback to regular saveProject
                await window.saveProject(this, { filepath: null, autoSave: false });
            } else if (window.app && typeof window.app.saveProject === 'function') {
                // Check if app has a save method
                await window.app.saveProject();
            } else {
                console.warn("Save function not available. Please import saveProject from timeline.js");
                this.showNotification("Save function not configured", "warning");
            }
        } catch (error) {
            console.error("Error in handleSaveShortcut:", error);
            this.showNotification("Save failed: " + error.message, "error");
        }
    }
    
    /**
     * Handle Ctrl+Shift+S keyboard shortcut (Save As).
     * 
     * Always shows save dialog.
     */
    async handleSaveAsShortcut() {
        try {
            if (typeof window.saveProject === 'function') {
                await window.saveProject(this, { filepath: null, autoSave: false });
            } else if (window.app && typeof window.app.saveProjectAs === 'function') {
                await window.app.saveProjectAs();
            } else {
                console.warn("Save As function not available");
                this.showNotification("Save As function not configured", "warning");
            }
        } catch (error) {
            console.error("Error in handleSaveAsShortcut:", error);
            this.showNotification("Save As failed: " + error.message, "error");
        }
    }
    
    /**
     * Handle Ctrl+O keyboard shortcut (Open Project).
     * 
     * Opens file picker to load a project.
     */
    async handleOpenShortcut() {
        try {
            if (typeof window.loadProject === 'function') {
                await window.loadProject(this, null); // null = show file picker
            } else if (window.app && typeof window.app.openProject === 'function') {
                await window.app.openProject();
            } else {
                console.warn("Open function not available. Please import loadProject from timeline.js");
                this.showNotification("Open function not configured", "warning");
            }
        } catch (error) {
            console.error("Error in handleOpenShortcut:", error);
            this.showNotification("Open failed: " + error.message, "error");
        }
    }
    
    /**
     * Setup auto-save for the project.
     * 
     * Automatically saves the project to a temporary file at regular intervals.
     * This helps prevent data loss in case of crashes or accidental closes.
     * 
     * @param {number} intervalMinutes - How often to auto-save (in minutes)
     * @returns {number} Interval ID (can be used with clearInterval to stop)
     */
    setupAutoSave(intervalMinutes = 5) {
        console.log(`Setting up auto-save every ${intervalMinutes} minutes`);
        
        // Clear any existing auto-save interval
        if (this._autoSaveInterval) {
            clearInterval(this._autoSaveInterval);
            console.log("Cleared previous auto-save interval");
        }
        
        // Create auto-save interval
        this._autoSaveInterval = setInterval(async () => {
            await this.performAutoSave();
        }, intervalMinutes * 60 * 1000);
        
        console.log(`✅ Auto-save enabled (every ${intervalMinutes} minutes)`);
        this.showNotification(`Auto-save enabled (every ${intervalMinutes} min)`, "info", 2000);
        
        return this._autoSaveInterval;
    }
    
    /**
     * Stop auto-save.
     * 
     * Clears the auto-save interval.
     */
    stopAutoSave() {
        if (this._autoSaveInterval) {
            clearInterval(this._autoSaveInterval);
            this._autoSaveInterval = null;
            console.log("Auto-save stopped");
            this.showNotification("Auto-save disabled", "info", 2000);
        }
    }
    
    /**
     * Perform an auto-save operation.
     * 
     * Saves to a temporary file without showing dialogs.
     * Called automatically by setupAutoSave().
     */
    async performAutoSave() {
        try {
            console.log("🔄 Auto-save triggered...");
            
            // Check if there's data to save
            if (!this.segments || this.segments.length === 0) {
                console.log("Auto-save skipped: No segments to save");
                return;
            }
            
            // Check if video is loaded
            if (!window.app || !window.app.currentVideoPath) {
                console.log("Auto-save skipped: No video loaded");
                return;
            }
            
            // Check if there are unsaved changes (if app tracks this)
            if (window.app && window.app.isDirty === false) {
                console.log("Auto-save skipped: No unsaved changes");
                return;
            }
            
            // Use the window.saveProject function with auto-save mode
            if (typeof window.saveProject === 'function') {
                const result = await window.saveProject(this, {
                    filepath: null,  // Will auto-generate filename
                    autoSave: true   // Enables auto-save mode (no dialog)
                });
                
                if (result.status === "success") {
                    console.log("💾 Auto-save completed:", result.filepath);
                    this.showNotification("Auto-saved", "success", 1500);
                } else {
                    console.error("Auto-save failed:", result.error);
                }
            } else {
                console.warn("Auto-save failed: saveProject function not available");
            }
        } catch (error) {
            console.error("Auto-save error:", error);
            // Don't show error notification for auto-save failures (to avoid annoying user)
        }
    }
    
    /**
     * Show a notification overlay on the timeline.
     * 
     * Displays a temporary message on the canvas for user feedback.
     * 
     * @param {string} message - Message to display
     * @param {string} type - Type of notification ("success", "error", "warning", "info")
     * @param {number} duration - How long to show the notification (ms, default 3000)
     */
    showNotification(message, type = "info", duration = 3000) {
        console.log(`[${type.toUpperCase()}] ${message}`);
        
        // Draw notification on segments canvas (NO external calls to avoid circular refs)
        if (!this.segmentsCanvas) {
            console.warn("Cannot show notification: No canvas available");
            return;
        }
        
        // Store notification data
        this._notification = {
            message: message,
            type: type,
            startTime: Date.now(),
            duration: duration
        };
        
        // Draw notification
        this.drawNotification();
        
        // Clear notification after duration
        setTimeout(() => {
            this._notification = null;
            this.drawSegments(); // Redraw to remove notification
        }, duration);
    }
    
    /**
     * Draw notification overlay on the segments canvas.
     * 
     * Called internally by showNotification().
     */
    drawNotification() {
        if (!this._notification) return;
        
        const ctx = this.segmentsCtx;
        const canvas = this.segmentsCanvas;
        
        // Calculate alpha based on time (fade out in last 500ms)
        const elapsed = Date.now() - this._notification.startTime;
        const remaining = this._notification.duration - elapsed;
        let alpha = 1.0;
        if (remaining < 500) {
            alpha = remaining / 500;
        }
        
        // Modern color scheme based on type
        const colors = {
            success: { bg: '#059669', border: '#10b981', text: '#ffffff', icon: '✓' },
            error: { bg: '#dc2626', border: '#ef4444', text: '#ffffff', icon: '✕' },
            warning: { bg: '#d97706', border: '#f59e0b', text: '#ffffff', icon: '⚠' },
            info: { bg: '#2563eb', border: '#3b82f6', text: '#ffffff', icon: 'ℹ' }
        };
        const color = colors[this._notification.type] || colors.info;
        
        // Measure text to calculate box width
        ctx.font = '600 13px Inter, -apple-system, sans-serif';
        const textWidth = ctx.measureText(this._notification.message).width;
        
        // Draw notification box with modern styling
        const padding = 16;
        const iconSize = 20;
        const boxHeight = 44;
        const boxWidth = Math.min(Math.max(textWidth + padding * 3 + iconSize, 200), canvas.width - 40);
        const x = (canvas.width - boxWidth) / 2;
        const y = 16;
        const borderRadius = 10;
        
        ctx.save();
        ctx.globalAlpha = alpha;
        
        // Shadow
        ctx.shadowColor = 'rgba(0, 0, 0, 0.25)';
        ctx.shadowBlur = 16;
        ctx.shadowOffsetY = 4;
        
        // Background with rounded corners
        ctx.fillStyle = color.bg;
        ctx.beginPath();
        ctx.roundRect(x, y, boxWidth, boxHeight, borderRadius);
        ctx.fill();
        
        // Border
        ctx.shadowBlur = 0;
        ctx.strokeStyle = color.border;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(x, y, boxWidth, boxHeight, borderRadius);
        ctx.stroke();
        
        // Icon circle
        const iconX = x + padding + iconSize / 2;
        const iconY = y + boxHeight / 2;
        ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.beginPath();
        ctx.arc(iconX, iconY, iconSize / 2 + 2, 0, Math.PI * 2);
        ctx.fill();
        
        // Icon
        ctx.fillStyle = color.text;
        ctx.font = 'bold 14px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(color.icon, iconX, iconY);
        
        // Text
        ctx.font = '600 13px Inter, -apple-system, sans-serif';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        const textX = x + padding + iconSize + 12;
        ctx.fillText(this._notification.message, textX, y + boxHeight / 2);
        
        ctx.restore();
    }
    
    /**
     * Get the current project state for saving.
     * 
     * This method collects all relevant timeline data that needs to be saved
     * to restore the editing session later.
     * 
     * @returns {Object} Project state object containing:
     *   - version: Project format version
     *   - timestamp: Current ISO timestamp
     *   - segments: All timeline segments
     *   - view_state: Current zoom and scroll position
     *   - video_signature: Placeholder for backend to fill with video metadata
     */
    getProjectState() {
        return {
            version: "1.0",
            timestamp: new Date().toISOString(),
            segments: this.segments || [],
            view_state: {
                zoom: this.zoom,
                scrollOffset: this.scrollOffset
            },
            video_signature: {
                // Placeholder - Backend will fill this with actual video metadata
                // (filename, duration, file_size, file_path, etc.)
                filename: null,
                duration: this.duration || 0,
                file_path: null,
                file_size: null
            }
        };
    }
    
    /**
     * Load project with strict validation.
     * 
     * This method validates that the project belongs to the currently loaded video
     * before restoring any state. This prevents loading the wrong project file.
     * 
     * @param {Object} projectData - Complete project data from load_project API
     * @returns {Object} Result object with {success: boolean, error?: string}
     */
    loadProject(projectData) {
        console.log("Timeline.loadProject: Starting project load with validation...");
        
        // === VALIDATION STEP ===
        
        // Check if project data exists
        if (!projectData) {
            const error = "Project data is null or undefined";
            console.error("Timeline.loadProject:", error);
            if (window.showModal) {
                window.showModal("Load Error", "Project file is empty or corrupted.", "error");
            } else {
                alert("Load Error: Project file is empty or corrupted.");
            }
            return { success: false, error: error };
        }
        
        // Handle legacy project files (check for expected structure)
        if (typeof projectData !== 'object') {
            const error = "Project data is not an object";
            console.error("Timeline.loadProject:", error);
            if (window.showModal) {
                window.showModal("Load Error", "Invalid project file format.", "error");
            } else {
                alert("Load Error: Invalid project file format.");
            }
            return { success: false, error: error };
        }
        
        // Check for minimum required fields
        if (!projectData.segments && !projectData.timeline_state) {
            console.warn("Timeline.loadProject: Project has no segments or timeline_state");
            // This might be a very old format, try to continue anyway
        }
        
        // === VIDEO DURATION VALIDATION (CRUCIAL) ===
        
        // Get duration from project data (check multiple possible locations for compatibility)
        let projectDuration = null;
        
        // Modern format: video_signature.duration
        if (projectData.video_signature && typeof projectData.video_signature.duration === 'number') {
            projectDuration = projectData.video_signature.duration;
        }
        // Alternative: video.duration (if using backend project structure)
        else if (projectData.video && typeof projectData.video.duration === 'number') {
            projectDuration = projectData.video.duration;
        }
        // Legacy format: direct duration field
        else if (typeof projectData.duration === 'number') {
            projectDuration = projectData.duration;
        }
        
        // If we have both durations, validate they match
        if (projectDuration !== null && this.duration > 0) {
            const durationDiff = Math.abs(projectDuration - this.duration);
            const tolerance = 0.1; // 0.1 seconds tolerance
            
            console.log(`Timeline.loadProject: Duration validation:
  - Current video: ${this.duration}s
  - Project video: ${projectDuration}s
  - Difference: ${durationDiff}s
  - Tolerance: ${tolerance}s`);
            
            if (durationDiff > tolerance) {
                const error = `Duration mismatch: Current video is ${this.duration}s, project is for ${projectDuration}s (diff: ${durationDiff}s)`;
                console.error("Timeline.loadProject:", error);
                
                // Show user-friendly error
                alert(
                    "❌ Project Mismatch: This project belongs to a different video.\n\n" +
                    `Current video duration: ${this.duration.toFixed(2)}s\n` +
                    `Project video duration: ${projectDuration.toFixed(2)}s\n\n` +
                    "Please load the correct video first, or choose a different project file."
                );
                
                return { success: false, error: error };
            }
            
            console.log("✅ Duration validation passed");
        } else {
            console.warn("Timeline.loadProject: Duration validation skipped (duration not available in project or timeline)");
        }
        
        // === RESTORATION STEP ===
        
        try {
            let segmentsRestored = false;
            let viewStateRestored = false;
            
            // Restore segments (check multiple possible locations)
            if (projectData.segments && Array.isArray(projectData.segments)) {
                this.segments = projectData.segments;
                segmentsRestored = true;
                console.log(`✅ Restored ${this.segments.length} segments`);
            } else if (projectData.timeline_state && projectData.timeline_state.segments) {
                // Legacy format compatibility
                this.segments = projectData.timeline_state.segments;
                segmentsRestored = true;
                console.log(`✅ Restored ${this.segments.length} segments (legacy format)`);
            } else {
                console.warn("⚠️ No segments found in project data");
                this.segments = [];
            }
            
            // Restore view state (zoom and scroll)
            const viewState = projectData.view_state || projectData.timeline_state;
            if (viewState) {
                // Restore zoom
                if (typeof viewState.zoom === 'number') {
                    this.zoom = Math.max(this.minZoom, Math.min(this.maxZoom, viewState.zoom));
                    console.log(`✅ Restored zoom to ${this.zoom.toFixed(2)}x`);
                    viewStateRestored = true;
                } else if (typeof viewState.zoom_level === 'number') {
                    // Alternative field name
                    this.zoom = Math.max(this.minZoom, Math.min(this.maxZoom, viewState.zoom_level));
                    console.log(`✅ Restored zoom to ${this.zoom.toFixed(2)}x`);
                    viewStateRestored = true;
                }
                
                // Restore scroll offset
                if (typeof viewState.scrollOffset === 'number') {
                    this.scrollOffset = Math.max(0, viewState.scrollOffset);
                    console.log(`✅ Restored scroll offset to ${this.scrollOffset.toFixed(2)}s`);
                    viewStateRestored = true;
                } else if (typeof viewState.scroll_position === 'number') {
                    // Alternative field name
                    this.scrollOffset = Math.max(0, viewState.scroll_position);
                    console.log(`✅ Restored scroll offset to ${this.scrollOffset.toFixed(2)}s`);
                    viewStateRestored = true;
                }
            } else {
                console.warn("⚠️ No view state found in project data");
            }
            
            // Update duration if not already set
            if (this.duration === 0 && projectDuration !== null) {
                this.duration = projectDuration;
                console.log(`✅ Set duration to ${this.duration}s from project`);
            }
            
            // === REDRAW UI ===
            
            this.redraw();
            console.log("✅ Timeline redrawn with restored state");
            
            // Summary
            console.log(`Timeline.loadProject: Success!
  - Segments restored: ${segmentsRestored} (${this.segments.length} segments)
  - View state restored: ${viewStateRestored}
  - Duration: ${this.duration}s
  - Zoom: ${this.zoom.toFixed(2)}x
  - Scroll: ${this.scrollOffset.toFixed(2)}s`);
            
            return { 
                success: true, 
                segmentsCount: this.segments.length,
                zoom: this.zoom,
                scrollOffset: this.scrollOffset
            };
            
        } catch (error) {
            const errorMsg = `Failed to restore project state: ${error.message}`;
            console.error("Timeline.loadProject:", error);
            alert(`Load Error: ${errorMsg}`);
            return { success: false, error: errorMsg };
        }
    }
    
    /**
     * Redraw the entire timeline (ruler, waveform, segments).
     * 
     * This is a convenience method that calls all draw methods.
     */
    redraw() {
        console.log("Timeline.redraw: Redrawing all layers...");
        this.drawRuler(this.duration);
        this.drawWaveform(this.waveformData || this.waveforms);
        this.drawSegments();
    }
    
    /**
     * Restore project state from loaded data (DEPRECATED - use loadProject instead).
     * 
     * This method applies saved project state back to the timeline,
     * restoring segments, zoom, scroll position, etc.
     * 
     * @deprecated Use loadProject() instead for better validation
     * @param {Object} projectState - Project state object from getProjectState()
     */
    restoreProjectState(projectState) {
        console.warn("Timeline.restoreProjectState is deprecated. Use loadProject() instead.");
        
        if (!projectState) {
            console.warn("Timeline.restoreProjectState: No project state provided");
            return;
        }
        
        // Restore segments
        if (projectState.segments) {
            this.segments = projectState.segments;
            console.log(`Timeline: Restored ${this.segments.length} segments`);
        }
        
        // Restore view state
        if (projectState.view_state) {
            if (typeof projectState.view_state.zoom === 'number') {
                this.zoom = Math.max(this.minZoom, Math.min(this.maxZoom, projectState.view_state.zoom));
                console.log(`Timeline: Restored zoom to ${this.zoom}`);
            }
            
            if (typeof projectState.view_state.scrollOffset === 'number') {
                this.scrollOffset = projectState.view_state.scrollOffset;
                console.log(`Timeline: Restored scroll offset to ${this.scrollOffset}s`);
            }
        }
        
        // Restore duration if available
        if (projectState.video_signature && typeof projectState.video_signature.duration === 'number') {
            this.duration = projectState.video_signature.duration;
        }
        
        // Redraw timeline with restored state
        this.redraw();
        
        console.log("Timeline: Project state restored successfully");
    }
}

/**
 * Save the current project to a .tbproj file.
 * 
 * This function collects the current state from the timeline and other app components,
 * then sends it to the Python backend for saving.
 * 
 * @param {Timeline} timeline - The Timeline instance
 * @param {Object} options - Save options
 * @param {string} options.filepath - Optional filepath (null = show save dialog)
 * @param {boolean} options.autoSave - Whether this is an auto-save (generates filename)
 * @returns {Promise<Object>} Response from backend with save status
 */
export async function saveProject(timeline, options = {}) {
    try {
        console.log("Starting project save...");
        
        // Get timeline state
        const timelineState = timeline.getProjectState();
        
        // Collect complete project data from the app
        // IMPORTANT: Only include JSON-serializable data (no DOM elements, no functions, no circular refs)
        const projectData = {
            // Timeline data
            timeline_state: {
                zoom_level: timelineState.view_state.zoom,
                scroll_position: timelineState.view_state.scrollOffset,
                selected_segments: []  // TODO: Add if you implement segment selection
            },
            
            // Segments from timeline (make a clean copy)
            segments: JSON.parse(JSON.stringify(timelineState.segments || [])),
            
            // Video metadata (will be fetched from backend)
            video: timelineState.video_signature,
            
            // Audio tracks (make a clean copy, only serializable data)
            audio_tracks: (window.app?.audioTracks || []).map(track => ({
                id: track.id,
                name: track.name,
                enabled: track.enabled
            })),
            
            // AI analysis history (make a clean copy)
            ai_analysis_history: JSON.parse(JSON.stringify(window.app?.aiAnalysisHistory || [])),
            
            // Settings - only include primitive values, not objects with circular refs
            settings: {
                silenceThreshold: window.app?.settings?.silenceThreshold,
                minSilenceDuration: window.app?.settings?.minSilenceDuration,
                paddingBefore: window.app?.settings?.paddingBefore,
                paddingAfter: window.app?.settings?.paddingAfter
            },
            
            // Metadata
            metadata: {
                timeline_version: timelineState.version,
                saved_at: timelineState.timestamp
            }
        };
        
        // If video path is available from window.app, use it
        if (window.app?.currentVideoPath) {
            // Get video metadata from backend
            console.log("Fetching video metadata...");
            const metadataResponse = await window.pywebview.api.get_video_metadata(
                window.app.currentVideoPath
            );
            
            if (metadataResponse.status === "success") {
                projectData.video = metadataResponse.metadata;
                console.log("Video metadata retrieved:", projectData.video.filename);
            } else {
                console.error("Failed to get video metadata:", metadataResponse.error);
                return {
                    status: "error",
                    error: "Failed to get video metadata: " + metadataResponse.error
                };
            }
        } else {
            console.warn("No video loaded - saving project without video metadata");
        }
        
        // Call backend save_project API
        console.log("Calling backend save_project...");
        const response = await window.pywebview.api.save_project(
            projectData,
            options.filepath || null,
            options.autoSave || false
        );
        
        if (response.status === "success") {
            console.log("✅ Project saved successfully!");
            console.log("   Filepath:", response.filepath);
            
            // Update UI or show notification
            if (window.showToast) {
                window.showToast("Project saved successfully!", "success");
            } else if (window.app?.showNotification) {
                window.app.showNotification("Project saved successfully!", "success");
            } else {
                // Fallback: console message
                console.log(`Project saved to: ${response.filepath}`);
            }
            
            return response;
        } else {
            console.error("❌ Project save failed:", response.error);
            
            // Show error to user with beautiful modal
            if (window.showModal) {
                await window.showModal("Save Failed", response.error, "error");
            } else if (window.app?.showNotification) {
                window.app.showNotification("Save failed: " + response.error, "error");
            } else {
                alert(`Failed to save project:\n\n${response.error}`);
            }
            
            return response;
        }
    } catch (error) {
        console.error("❌ Exception during project save:", error);
        
        // Show error to user
        const errorMessage = error.message || String(error);
        if (window.app?.showNotification) {
            window.app.showNotification("Save error: " + errorMessage, "error");
        } else {
            alert(`Error saving project:\n\n${errorMessage}`);
        }
        
        return {
            status: "error",
            error: errorMessage
        };
    }
}

/**
 * Load a project from a .tbproj file.
 * 
 * This function loads project data from the backend and restores the timeline
 * and app state with strict validation.
 * 
 * @param {Timeline} timeline - The Timeline instance
 * @param {string} filepath - Optional filepath (null = show open dialog)
 * @returns {Promise<Object>} Response from backend with project data
 */
export async function loadProject(timeline, filepath = null) {
    try {
        console.log("Starting project load...");
        
        // === PRE-CHECK: Require video to be loaded first ===
        // This prevents loading projects without a video, which causes issues with segments and waveform
        const hasVideo = window.app?.currentVideoPath && window.app?.currentVideoInfo;
        const hasTimelineDuration = timeline && timeline.duration > 0;
        
        if (!hasVideo && !hasTimelineDuration) {
            const message = "Please load a video first before opening a project.\n\n" +
                          "Steps:\n" +
                          "1. Click 'Load Video' button\n" +
                          "2. Select your video file\n" +
                          "3. Wait for the waveform to appear\n" +
                          "4. Then open your project file\n\n" +
                          "This ensures the project segments align correctly with your video.";
            
            if (window.showModal) {
                await window.showModal("Video Required", message, "warning");
            } else {
                alert(message);
            }
            
            return {
                status: "error",
                error: "No video loaded. Please load a video first before opening a project."
            };
        }
        
        // Call backend load_project API
        const response = await window.pywebview.api.load_project(filepath);
        
        if (response.status === "success") {
            const projectData = response.project_data;
            console.log("✅ Project loaded from backend successfully!");
            console.log("   Video:", projectData.video?.filename);
            console.log("   Segments:", projectData.segments?.length);
            
            // Show warnings if any
            // Show warnings only if they're important (not just missing video fields for old projects)
            if (response.warnings && response.warnings.length > 0) {
                // Filter out common "missing video field" warnings for old projects
                const importantWarnings = response.warnings.filter(w => 
                    !w.includes("Missing or empty video field") && 
                    !w.includes("Video file path is missing")
                );
                
                if (importantWarnings.length > 0) {
                    console.warn("⚠️ Warnings:");
                    importantWarnings.forEach(w => console.warn("  -", w));
                    
                    // Show only important warnings
                    const warningMessage = "Project loaded with warnings: " + 
                                         importantWarnings.slice(0, 2).join("; ");
                    if (window.showToast) {
                        window.showToast(warningMessage, "warning", 6000);
                    }
                }
            }
            
            // === STEP 1: Pre-load segments so they're preserved when video loads ===
            if (projectData.segments && Array.isArray(projectData.segments)) {
                timeline.segments = projectData.segments;
                console.log(`Pre-loaded ${timeline.segments.length} segments before video load`);
            }
            
            // === STEP 2: Restore video (if path exists and video not already loaded) ===
            if (projectData.video && projectData.video.file_path && projectData.video.exists) {
                console.log("Loading video:", projectData.video.file_path);
                
                // Check if this video is already loaded
                const isSameVideo = window.app?.currentVideoPath === projectData.video.file_path;
                
                if (!isSameVideo) {
                    try {
                        // Load video using the metadata from project
                        // Convert project video format to processVideoInfo format
                        const videoInfo = {
                            filePath: projectData.video.file_path,
                            fileName: projectData.video.filename || projectData.video.file_path.split(/[/\\]/).pop(),
                            duration: projectData.video.duration || 0,
                            audioTracks: projectData.audio_tracks || []
                        };
                        
                        // Call processVideoInfo (which will preserve existing segments via timeline.draw)
                        if (typeof window.processVideoInfo === 'function') {
                            await window.processVideoInfo(videoInfo);
                            console.log("✅ Video loaded, segments preserved");
                        } else {
                            console.warn("processVideoInfo not available - video not auto-loaded");
                            timeline._videoNotLoaded = true;
                        }
                    } catch (error) {
                        console.error("Failed to load video:", error);
                        if (window.showModal) {
                            await window.showModal("Video Load Failed", `Could not load video:\n\n${error.message || error}`, "error");
                        }
                        // Continue loading segments anyway
                        timeline._videoNotLoaded = true;
                    }
                } else {
                    console.log("Video already loaded, skipping video load");
                }
            } else if (projectData.video && projectData.video.file_path && !projectData.video.exists) {
                // Video file path exists but file doesn't exist on disk
                const videoPath = projectData.video.file_path;
                console.warn("Video file not found at:", videoPath);
                // Will show combined message at the end
                timeline._videoNotLoaded = true;
            } else if (!projectData.video || !projectData.video.file_path) {
                // No video info in project - this is common for old projects
                console.log("No video path in project, segments will be loaded without video");
                // Will show combined message at the end
                timeline._videoNotLoaded = true;
            }
            
            // === STEP 3: Load project into timeline with strict validation ===
            // (This will restore zoom/scroll, validate duration, and ensure segments are correct)
            console.log("Loading project data into timeline with validation...");
            const loadResult = timeline.loadProject(projectData);
            
            if (!loadResult.success) {
                // Validation failed, loadProject already showed error to user
                console.error("Timeline validation failed:", loadResult.error);
                return {
                    status: "error",
                    error: loadResult.error
                };
            }
            
            console.log(`✅ Timeline loaded: ${loadResult.segmentsCount} segments, zoom: ${loadResult.zoom}, scroll: ${loadResult.scrollOffset}`);
            
            // === STEP 3: Restore audio tracks (if available) ===
            if (projectData.audio_tracks && window.app) {
                window.app.audioTracks = projectData.audio_tracks;
                console.log(`✅ Restored ${projectData.audio_tracks.length} audio tracks`);
            }
            
            // === STEP 4: Restore AI analysis history (if available) ===
            if (projectData.ai_analysis_history && window.app) {
                window.app.aiAnalysisHistory = projectData.ai_analysis_history;
                console.log(`✅ Restored ${projectData.ai_analysis_history.length} AI analysis runs`);
                
                // Update AI history dropdown if it exists
                if (window.app.updateAIHistoryDropdown) {
                    window.app.updateAIHistoryDropdown();
                }
            }
            
            // === STEP 5: Restore settings (if available) ===
            if (projectData.settings && window.app) {
                Object.assign(window.app.settings || {}, projectData.settings);
                console.log("✅ Restored settings");
            }
            
            // === STEP 6: Show success notification ===
            const segmentCount = projectData.segments?.length || 0;
            
            // Check if video was loaded or not
            if (timeline._videoNotLoaded) {
                // Show single combined message
                const successMsg = `✓ ${segmentCount} segments loaded. Click "Load Video" to see waveform.`;
                if (window.showToast) {
                    window.showToast(successMsg, "success", 5000);
                }
                delete timeline._videoNotLoaded; // Clean up flag
            } else {
                // Video was loaded successfully
                const successMsg = `Project loaded! ${segmentCount} segments restored.`;
                if (window.showToast) {
                    window.showToast(successMsg, "success", 4000);
                }
            }
            
            return response;
        } else {
            console.error("❌ Project load failed:", response.error);
            
            // Show error to user (unless user cancelled)
            if (!response.error.includes("cancelled")) {
                if (window.showModal) {
                    await window.showModal("Load Failed", response.error, "error");
                } else if (window.app?.showNotification) {
                    window.app.showNotification("Load failed: " + response.error, "error");
                } else {
                    alert(`Failed to load project:\n\n${response.error}`);
                }
            }
            
            return response;
        }
    } catch (error) {
        console.error("❌ Exception during project load:", error);
        
        // Show error to user
        const errorMessage = error.message || String(error);
        if (window.app?.showNotification) {
            window.app.showNotification("Load error: " + errorMessage, "error");
        } else {
            alert(`Error loading project:\n\n${errorMessage}`);
        }
        
        return {
            status: "error",
            error: errorMessage
        };
    }
}

/**
 * Quick save to current project file (Ctrl+S equivalent).
 * 
 * @param {Timeline} timeline - The Timeline instance
 * @returns {Promise<Object>} Response from backend
 */
export async function quickSave(timeline) {
    console.log("Quick save (Ctrl+S)...");
    
    try {
        // First, check if there's a current project open
        const pathResponse = await window.pywebview.api.get_current_project_path();
        
        if (pathResponse.status === "success" && pathResponse.has_project) {
            // Use save_current_project for quick save
            const response = await window.pywebview.api.save_current_project();
            
            if (response.status === "success") {
                console.log("✅ Quick save successful!");
                if (window.app?.showNotification) {
                    window.app.showNotification("Saved!", "success");
                }
            }
            
            return response;
        } else {
            // No project open, do "Save As" instead
            console.log("No project open, showing Save As dialog...");
            return await saveProject(timeline, { filepath: null, autoSave: false });
        }
    } catch (error) {
        console.error("Quick save error:", error);
        return {
            status: "error",
            error: error.message || String(error)
        };
    }
}