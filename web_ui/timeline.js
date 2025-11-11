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
            keep: '#2fb344',   // Green
            remove: '#ef4444',  // Red
            keep_silent: '#666666' // Gray
        };
        
        this.segments = [];
        this.waveformData = [];
        this.duration = 0;
        this.playhead = 0;
        this.zoom = 1.0;
        
        // This is the new scrollable wrapper from index.html
        this.scrollWrapper = document.getElementById('timeline-scroll-wrapper');
        
        this.onSeek = null; // Callback
    }

    // This is the new, combined resize and draw function
    resizeAndRedraw() {
        // 1. Calculate the base width from the *parent* panel
        const baseWidth = this.scrollWrapper.offsetWidth;
        // 2. Calculate the zoomed width
        const canvasWidth = baseWidth * this.zoom;
        
        // 3. Set the width of the canvases
        this.rulerCanvas.width = canvasWidth;
        this.waveformCanvas.width = canvasWidth;
        this.segmentsCanvas.width = canvasWidth;
        
        // 4. Redraw everything with the new sizes
        this.draw(this.segments, this.duration, this.waveformData);
    }
    
    // Main function to update timeline
    draw(segments, duration, waveformData) {
        // Store data
        this.segments = segments || this.segments;
        this.duration = duration || this.duration;
        this.waveformData = waveformData || this.waveformData;
        
        // Redraw all components
        this.drawRuler();
        this.drawWaveform();
        this.drawSegments();
    }

    drawRuler() {
        const ctx = this.rulerCtx;
        const w = this.rulerCanvas.width;
        const h = this.rulerCanvas.height;
        const duration = this.duration;

        ctx.fillStyle = this.colors.background;
        ctx.fillRect(0, 0, w, h);

        ctx.fillStyle = this.colors.text;
        ctx.font = '12px sans-serif';
        
        // Simple tick logic
        const tickCount = 10 * this.zoom;
        for (let i = 0; i <= tickCount; i++) {
            const x = (w / tickCount) * i;
            const time = (duration / tickCount) * i;
            
            ctx.strokeStyle = this.colors.line;
            ctx.beginPath();
            ctx.moveTo(x, h);
            ctx.lineTo(x, h - 10);
            ctx.stroke();
            
            ctx.fillText(time.toFixed(1) + 's', x + 5, h - 15);
        }
        
        this.drawPlayhead();
    }

    drawWaveform() {
        const ctx = this.waveformCtx;
        const w = this.waveformCanvas.width;
        const h = this.waveformCanvas.height;
        const data = this.waveformData;

        ctx.fillStyle = this.colors.background;
        ctx.fillRect(0, 0, w, h);

        if (!data || data.length === 0) return;

        ctx.strokeStyle = '#3b82f6'; // Blue
        ctx.lineWidth = 1;
        
        const mid_h = h / 2;
        
        ctx.beginPath();
        for (let i = 0; i < w; i++) {
            // Map pixel 'i' to a data point
            const dataIndex = Math.floor((i / w) * data.length);
            const amplitude = data[dataIndex] * mid_h;
            
            // Draw a single vertical line per pixel
            ctx.moveTo(i, mid_h - amplitude);
            ctx.lineTo(i, mid_h + amplitude);
        }
        ctx.stroke();
    }

    drawSegments() {
        const ctx = this.segmentsCtx;
        const w = this.segmentsCanvas.width;
        const h = this.segmentsCanvas.height;

        ctx.fillStyle = this.colors.background;
        ctx.fillRect(0, 0, w, h);

        if (!this.segments || this.segments.length === 0 || this.duration === 0) {
            return;
        }

        for (const segment of this.segments) {
            const x_start = (segment.start / this.duration) * w;
            const x_end = (segment.end / this.duration) * w;
            const width = Math.max(1, x_end - x_start); // Ensure min 1px width

            if (segment.type === 'audible') {
                ctx.fillStyle = segment.keep ? this.colors.keep : '#f59e0b'; // Green or Orange
            } else { // 'silent'
                ctx.fillStyle = segment.keep ? this.colors.keep_silent : this.colors.remove; // Gray or Red
            }
            ctx.fillRect(x_start, 5, width, h - 10);
        }
    }

    drawPlayhead() {
        const ctx = this.rulerCtx;
        const w = this.rulerCanvas.width;
        const h = this.rulerCanvas.height;

        const x = (this.playhead / this.duration) * w;

        ctx.strokeStyle = '#ef4444'; // Red
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
    }
    
    updatePlayhead(timeSeconds) {
        this.playhead = timeSeconds;
        if (this.duration > 0) {
            this.drawRuler();
        }
    }

    // --- Click/Drag/Zoom Handlers ---

    handleClick(event) {
        if (!this.segments || this.segments.length === 0 || this.duration === 0) return;

        const rect = this.segmentsCanvas.getBoundingClientRect();
        const x = event.clientX - rect.left + this.scrollWrapper.scrollLeft;
        const w = this.segmentsCanvas.width;
        const timeClicked = (x / w) * this.duration;

        let clickedSegment = null;
        for (const segment of this.segments) {
            if (timeClicked >= segment.start && timeClicked <= segment.end) {
                clickedSegment = segment;
                break;
            }
        }

        if (clickedSegment) {
            // Allow toggling *any* segment
            clickedSegment.keep = !clickedSegment.keep;
            this.drawSegments();
            console.log(`Toggled segment: ${clickedSegment.start.toFixed(2)}s, New status: ${clickedSegment.keep}`);
        }
        
        if (this.onSeek) {
            this.onSeek(timeClicked);
        }
    }

    handleRulerClick(event) {
        if (this.duration === 0) return;
        
        const rect = this.rulerCanvas.getBoundingClientRect();
        const x = event.clientX - rect.left + this.scrollWrapper.scrollLeft;
        const w = this.rulerCanvas.width;
        const timeClicked = (x / w) * this.duration;
        
        if (this.onSeek) {
            this.onSeek(timeClicked);
        }
    }

    bindClick() {
        this.segmentsCanvas.addEventListener('click', this.handleClick.bind(this));
    }

    bindRulerClick() {
        this.rulerCanvas.addEventListener('click', this.handleRulerClick.bind(this));
    }

    bindWheelEvents() {
        this.scrollWrapper.addEventListener('wheel', (event) => {
            if (event.ctrlKey) {
                event.preventDefault();
                const zoomAmount = event.deltaY * -0.01;
                this.setZoom(this.zoom + zoomAmount);
            }
        }, { passive: false });
    }

    bindKeyEvents() {
        window.addEventListener('keydown', (event) => {
            let newTime = this.playhead;
            let seek = false;

            if (event.key === 'ArrowLeft') {
                newTime = Math.max(0, this.playhead - 1);
                seek = true;
            } else if (event.key === 'ArrowRight') {
                newTime = Math.min(this.duration, this.playhead + 1);
                seek = true;
            } else if (event.key === 'Home') {
                newTime = 0;
                seek = true;
            } else if (event.key === 'End') {
                newTime = this.duration;
                seek = true;
            }

            if (seek && this.onSeek) {
                event.preventDefault();
                this.onSeek(newTime);
            }
        });
    }
    
    setZoom(newZoom) {
        this.zoom = Math.max(1.0, newZoom);
        
        // Get the new width for the *internal* canvases
        const baseWidth = this.scrollWrapper.offsetWidth;
        const canvasWidth = baseWidth * this.zoom;
        
        // Apply the new width
        this.rulerCanvas.width = canvasWidth;
        this.waveformCanvas.width = canvasWidth;
        this.segmentsCanvas.width = canvasWidth;
        
        // Also update the canvas STYLE to match. This is important.
        this.rulerCanvas.style.width = canvasWidth + 'px';
        this.waveformCanvas.style.width = canvasWidth + 'px';
        this.segmentsCanvas.style.width = canvasWidth + 'px';
        
        // Redraw everything
        this.drawRuler();
        this.drawWaveform();
        this.drawSegments();
    }

    scrollToStart() {
        this.scrollWrapper.scrollLeft = 0;
    }

    scrollToEnd() {
        this.scrollWrapper.scrollLeft = this.scrollWrapper.scrollWidth;
    }
}