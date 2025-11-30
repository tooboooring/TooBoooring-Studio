/**
 * JavaScript Example: Using the Project Save/Load System
 * 
 * This file demonstrates how to call the Python backend project management
 * functions from the JavaScript frontend.
 * 
 * All functions are exposed via window.pywebview.api and return Promises.
 */

// ============================================================================
// EXAMPLE 1: Get Video Metadata
// ============================================================================
async function exampleGetVideoMetadata() {
    const videoPath = "C:/Users/Videos/my_video.mp4";
    
    try {
        const response = await window.pywebview.api.get_video_metadata(videoPath);
        
        if (response.status === "success") {
            const metadata = response.metadata;
            console.log("Video Metadata:");
            console.log(`  Filename: ${metadata.filename}`);
            console.log(`  Duration: ${metadata.duration}s`);
            console.log(`  File Size: ${(metadata.file_size / 1024 / 1024).toFixed(2)} MB`);
            console.log(`  Path: ${metadata.file_path}`);
            return metadata;
        } else {
            console.error("Error:", response.error);
            return null;
        }
    } catch (error) {
        console.error("Exception:", error);
        return null;
    }
}

// ============================================================================
// EXAMPLE 2: Save Project (with Save Dialog)
// ============================================================================
async function exampleSaveProject() {
    // Prepare project data
    const projectData = {
        video: {
            filename: "my_video.mp4",
            file_path: "C:/Users/Videos/my_video.mp4",
            file_size: 12345678,
            duration: 120.5
        },
        audio_tracks: [
            { index: 0, codec: "aac", channels: "stereo" }
        ],
        segments: [
            { start: 0, end: 10.5, type: "audible", action: "keep" },
            { start: 10.5, end: 12.0, type: "silence", action: "remove" },
            { start: 12.0, end: 25.3, type: "audible", action: "keep" }
        ],
        ai_analysis_history: [
            {
                model: "Llama 3.3 70B (Recommended)",
                timestamp: new Date().toISOString(),
                segments_analyzed: 50,
                keep_count: 45,
                flag_count: 5
            }
        ],
        settings: {
            silence_db: -40,
            silence_duration: 0.7,
            whisper_model: "base"
        },
        timeline_state: {
            zoom_level: 1.5,
            scroll_position: 100,
            selected_segments: []
        }
    };
    
    try {
        // filepath=null will show save dialog
        const response = await window.pywebview.api.save_project(projectData, null, false);
        
        if (response.status === "success") {
            console.log("✅ Project saved successfully!");
            console.log(`Saved to: ${response.filepath}`);
            return response.filepath;
        } else {
            console.error("❌ Save failed:", response.error);
            return null;
        }
    } catch (error) {
        console.error("Exception:", error);
        return null;
    }
}

// ============================================================================
// EXAMPLE 3: Save Project to Specific Path (No Dialog)
// ============================================================================
async function exampleSaveProjectToPath(projectData, filepath) {
    try {
        const response = await window.pywebview.api.save_project(
            projectData, 
            filepath,
            false  // auto_save=false
        );
        
        if (response.status === "success") {
            console.log("✅ Project saved!");
            return response.filepath;
        } else {
            console.error("❌ Save failed:", response.error);
            return null;
        }
    } catch (error) {
        console.error("Exception:", error);
        return null;
    }
}

// ============================================================================
// EXAMPLE 4: Auto-Save (with automatic filename generation)
// ============================================================================
async function exampleAutoSave(projectData) {
    try {
        const response = await window.pywebview.api.save_project(
            projectData,
            null,  // No filepath provided
            true   // auto_save=true (generates filename automatically)
        );
        
        if (response.status === "success") {
            console.log("💾 Auto-saved to:", response.filepath);
            return response.filepath;
        } else {
            console.error("❌ Auto-save failed:", response.error);
            return null;
        }
    } catch (error) {
        console.error("Exception:", error);
        return null;
    }
}

// ============================================================================
// EXAMPLE 5: Load Project (with Open Dialog)
// ============================================================================
async function exampleLoadProject() {
    try {
        // filepath=null will show open dialog
        const response = await window.pywebview.api.load_project(null);
        
        if (response.status === "success") {
            const projectData = response.project_data;
            console.log("✅ Project loaded successfully!");
            console.log(`Loaded from: ${response.filepath}`);
            console.log(`Video: ${projectData.video.filename}`);
            console.log(`Segments: ${projectData.segments.length}`);
            console.log(`AI Runs: ${projectData.ai_analysis_history.length}`);
            
            // Check for warnings
            if (response.warnings && response.warnings.length > 0) {
                console.warn("⚠️ Warnings:");
                response.warnings.forEach(w => console.warn(`  - ${w}`));
            }
            
            return projectData;
        } else {
            console.error("❌ Load failed:", response.error);
            return null;
        }
    } catch (error) {
        console.error("Exception:", error);
        return null;
    }
}

// ============================================================================
// EXAMPLE 6: Load Project from Specific Path (No Dialog)
// ============================================================================
async function exampleLoadProjectFromPath(filepath) {
    try {
        const response = await window.pywebview.api.load_project(filepath);
        
        if (response.status === "success") {
            console.log("✅ Project loaded from:", filepath);
            return response.project_data;
        } else {
            console.error("❌ Load failed:", response.error);
            return null;
        }
    } catch (error) {
        console.error("Exception:", error);
        return null;
    }
}

// ============================================================================
// EXAMPLE 7: Get Recent Projects
// ============================================================================
async function exampleGetRecentProjects() {
    try {
        const response = await window.pywebview.api.get_recent_projects(10);
        
        if (response.status === "success") {
            const projects = response.projects;
            console.log(`Found ${projects.length} recent projects:`);
            
            projects.forEach((project, index) => {
                console.log(`\n${index + 1}. ${project.filename}`);
                console.log(`   Video: ${project.video_filename}`);
                console.log(`   Modified: ${project.modified}`);
                console.log(`   Path: ${project.filepath}`);
            });
            
            return projects;
        } else {
            console.error("❌ Failed to get recent projects:", response.error);
            return [];
        }
    } catch (error) {
        console.error("Exception:", error);
        return [];
    }
}

// ============================================================================
// EXAMPLE 8: Quick Save (Ctrl+S equivalent)
// ============================================================================
async function exampleQuickSave() {
    try {
        const response = await window.pywebview.api.save_current_project();
        
        if (response.status === "success") {
            console.log("💾 Quick save successful!");
            return true;
        } else {
            console.error("❌ Quick save failed:", response.error);
            // If no project is open, show "Save As" dialog instead
            if (response.error.includes("No project file open")) {
                console.log("No project open, use save_project() with dialog instead");
            }
            return false;
        }
    } catch (error) {
        console.error("Exception:", error);
        return false;
    }
}

// ============================================================================
// EXAMPLE 9: Validate Project File
// ============================================================================
async function exampleValidateProject(filepath) {
    try {
        const response = await window.pywebview.api.validate_project_file(filepath);
        
        if (response.status === "success") {
            const validation = response;
            
            if (validation.valid) {
                console.log("✅ Project file is valid");
            } else {
                console.error("❌ Project file is invalid:");
                validation.errors.forEach(err => console.error(`  - ${err}`));
            }
            
            if (validation.warnings && validation.warnings.length > 0) {
                console.warn("⚠️ Warnings:");
                validation.warnings.forEach(w => console.warn(`  - ${w}`));
            }
            
            return validation;
        } else {
            console.error("❌ Validation failed:", response.error);
            return null;
        }
    } catch (error) {
        console.error("Exception:", error);
        return null;
    }
}

// ============================================================================
// EXAMPLE 10: Export Project Summary
// ============================================================================
async function exampleExportSummary(filepath = null) {
    try {
        const response = await window.pywebview.api.export_project_summary(filepath);
        
        if (response.status === "success") {
            console.log(response.summary);
            return response.summary;
        } else {
            console.error("❌ Summary export failed:", response.error);
            return null;
        }
    } catch (error) {
        console.error("Exception:", error);
        return null;
    }
}

// ============================================================================
// EXAMPLE 11: Check Current Project Path
// ============================================================================
async function exampleGetCurrentProjectPath() {
    try {
        const response = await window.pywebview.api.get_current_project_path();
        
        if (response.status === "success") {
            if (response.has_project) {
                console.log("Current project:", response.filepath);
            } else {
                console.log("No project currently open");
            }
            return response.filepath;
        } else {
            console.error("❌ Failed:", response.error);
            return null;
        }
    } catch (error) {
        console.error("Exception:", error);
        return null;
    }
}

// ============================================================================
// INTEGRATED WORKFLOW EXAMPLE: Complete Save/Load Workflow
// ============================================================================
class ProjectWorkflowManager {
    constructor() {
        this.currentProjectData = null;
        this.currentProjectPath = null;
        this.isDirty = false;  // Track if project has unsaved changes
    }
    
    // Collect all current state from your app
    collectCurrentState() {
        // This should collect data from your actual app state
        // For example, from timeline segments, AI analysis results, settings, etc.
        return {
            video: window.app.currentVideo || null,
            audio_tracks: window.app.audioTracks || [],
            segments: window.app.segments || [],
            ai_analysis_history: window.app.aiAnalysisHistory || [],
            settings: window.app.currentSettings || {},
            timeline_state: {
                zoom_level: window.app.timeline?.zoomLevel || 1.0,
                scroll_position: window.app.timeline?.scrollPosition || 0,
                selected_segments: window.app.timeline?.selectedSegments || []
            }
        };
    }
    
    // Mark project as modified
    markDirty() {
        this.isDirty = true;
        // Update UI to show unsaved indicator (e.g., asterisk in title)
        this.updateTitle();
    }
    
    // Update window title
    updateTitle() {
        const dirtyIndicator = this.isDirty ? "*" : "";
        const projectName = this.currentProjectPath 
            ? this.currentProjectPath.split(/[\\/]/).pop() 
            : "Untitled";
        document.title = `${dirtyIndicator}${projectName} - TooBoooring Studio`;
    }
    
    // Save project (Ctrl+S)
    async save() {
        const projectData = this.collectCurrentState();
        
        if (!this.currentProjectPath) {
            // No project path, show "Save As" dialog
            return await this.saveAs();
        }
        
        try {
            const response = await window.pywebview.api.save_project(
                projectData,
                this.currentProjectPath,
                false
            );
            
            if (response.status === "success") {
                this.currentProjectData = projectData;
                this.isDirty = false;
                this.updateTitle();
                console.log("✅ Saved:", response.filepath);
                return true;
            } else {
                alert(`Failed to save: ${response.error}`);
                return false;
            }
        } catch (error) {
            console.error("Save error:", error);
            alert(`Error: ${error}`);
            return false;
        }
    }
    
    // Save As (Ctrl+Shift+S)
    async saveAs() {
        const projectData = this.collectCurrentState();
        
        try {
            const response = await window.pywebview.api.save_project(
                projectData,
                null,  // Show save dialog
                false
            );
            
            if (response.status === "success") {
                this.currentProjectPath = response.filepath;
                this.currentProjectData = projectData;
                this.isDirty = false;
                this.updateTitle();
                console.log("✅ Saved as:", response.filepath);
                return true;
            } else if (response.error !== "Save cancelled by user") {
                alert(`Failed to save: ${response.error}`);
            }
            return false;
        } catch (error) {
            console.error("Save error:", error);
            alert(`Error: ${error}`);
            return false;
        }
    }
    
    // Open project (Ctrl+O)
    async open() {
        // Check for unsaved changes
        if (this.isDirty) {
            const save = confirm("You have unsaved changes. Save before opening?");
            if (save) {
                const saved = await this.save();
                if (!saved) return false;
            }
        }
        
        try {
            const response = await window.pywebview.api.load_project(null);
            
            if (response.status === "success") {
                const projectData = response.project_data;
                
                // Apply loaded data to app
                this.applyProjectData(projectData);
                
                this.currentProjectPath = response.filepath;
                this.currentProjectData = projectData;
                this.isDirty = false;
                this.updateTitle();
                
                console.log("✅ Loaded:", response.filepath);
                
                // Show warnings if any
                if (response.warnings && response.warnings.length > 0) {
                    alert("Warnings:\n" + response.warnings.join("\n"));
                }
                
                return true;
            } else if (response.error !== "Load cancelled by user") {
                alert(`Failed to load: ${response.error}`);
            }
            return false;
        } catch (error) {
            console.error("Load error:", error);
            alert(`Error: ${error}`);
            return false;
        }
    }
    
    // Apply loaded project data to app UI
    applyProjectData(projectData) {
        // This should update your actual app state
        // For example:
        
        // Load video
        if (projectData.video && projectData.video.exists) {
            window.app.loadVideo(projectData.video.file_path);
        }
        
        // Restore segments
        if (projectData.segments) {
            window.app.segments = projectData.segments;
            window.app.timeline?.renderSegments();
        }
        
        // Restore AI analysis history
        if (projectData.ai_analysis_history) {
            window.app.aiAnalysisHistory = projectData.ai_analysis_history;
        }
        
        // Restore settings
        if (projectData.settings) {
            Object.assign(window.app.currentSettings, projectData.settings);
        }
        
        // Restore timeline state
        if (projectData.timeline_state) {
            if (window.app.timeline) {
                window.app.timeline.zoomLevel = projectData.timeline_state.zoom_level;
                window.app.timeline.scrollPosition = projectData.timeline_state.scroll_position;
            }
        }
    }
    
    // Auto-save every N minutes
    startAutoSave(intervalMinutes = 5) {
        setInterval(async () => {
            if (this.isDirty && this.currentProjectData) {
                console.log("🔄 Auto-saving...");
                const projectData = this.collectCurrentState();
                
                try {
                    await window.pywebview.api.save_project(
                        projectData,
                        null,
                        true  // auto_save=true
                    );
                    console.log("💾 Auto-save complete");
                } catch (error) {
                    console.error("Auto-save failed:", error);
                }
            }
        }, intervalMinutes * 60 * 1000);
    }
}

// ============================================================================
// USAGE: Setup keyboard shortcuts and workflow manager
// ============================================================================
function setupProjectManagement() {
    const workflow = new ProjectWorkflowManager();
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl+S or Cmd+S: Save
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            workflow.save();
        }
        
        // Ctrl+Shift+S or Cmd+Shift+S: Save As
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'S') {
            e.preventDefault();
            workflow.saveAs();
        }
        
        // Ctrl+O or Cmd+O: Open
        if ((e.ctrlKey || e.metaKey) && e.key === 'o') {
            e.preventDefault();
            workflow.open();
        }
    });
    
    // Start auto-save (every 5 minutes)
    workflow.startAutoSave(5);
    
    // Warn before closing with unsaved changes
    window.addEventListener('beforeunload', (e) => {
        if (workflow.isDirty) {
            e.preventDefault();
            e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
        }
    });
    
    return workflow;
}

// Export for use in main app
window.ProjectWorkflowManager = ProjectWorkflowManager;
window.setupProjectManagement = setupProjectManagement;

console.log("📦 Project Management System loaded!");
console.log("Use setupProjectManagement() to initialize");

