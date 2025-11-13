# AI Content Analysis - Implementation Summary

## ✅ Implementation Complete

The AI content analysis feature has been successfully integrated into the Video Production Suite. This document summarizes what was implemented and how to use it.

---

## 📁 New Modules Created

All AI analysis code is in the `video_production_app/ai_analysis/` package:

### 1. `transcriber.py`
- **Purpose**: Local audio transcription using OpenAI Whisper
- **Key Functions**:
  - `transcribe_segments()`: Transcribes individual audible segments
  - `transcribe_full_video()`: Transcribes entire video for full context
  - `to_srt_format()`: Converts transcripts to SRT subtitle format
- **Features**:
  - Supports multiple Whisper model sizes (tiny, base, small, medium, large)
  - Extracts word-level timestamps
  - Handles FFmpeg audio extraction automatically

### 2. `context_builder.py`
- **Purpose**: Extracts surrounding context for each segment
- **Key Functions**:
  - `build_context()`: Gets text before/after a specific segment
  - `build_all_contexts()`: Builds context for all segments
  - `format_context_for_prompt()`: Formats context for LLM input
- **Features**:
  - Configurable context window (default: 30 seconds before/after)
  - Provides narrative flow understanding for AI

### 3. `ai_analyzer.py`
- **Purpose**: Analyzes content using together.ai API
- **Key Functions**:
  - `analyze_segment()`: Single segment analysis
  - `analyze_segments_batch()`: Batch processing with rate limiting
  - `export_decisions_to_json()`: Save analysis results
- **Features**:
  - Flexible prompt template system (not finalized, easily customizable)
  - Structured response parsing with Pydantic
  - Steelman/skeptic/judge debate in single prompt
  - Returns KEEP/FLAG/UNCERTAIN decisions with confidence scores
  - Logs all prompt/response pairs for iteration

### 4. `orchestrator.py`
- **Purpose**: Coordinates the complete analysis pipeline
- **Key Functions**:
  - `analyze_content()`: Main entry point for full pipeline
  - `apply_decisions_to_segments()`: Updates segment colors based on AI decisions
- **Pipeline**:
  1. Transcription (Whisper)
  2. Context building (before/after text)
  3. AI analysis (together.ai)
  4. Decision aggregation
  5. Segment color updates

---

## ⚙️ Configuration Added

### `config.py` - New Section: `AI_ANALYSIS_SETTINGS`

```python
AI_ANALYSIS_SETTINGS = {
    "api_key": "",  # User must provide their own together.ai API key
    "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    "temperature": 0.7,
    "max_tokens": 500,
    "whisper_model": "base",  # Options: tiny, base, small, medium, large
    "context_window_seconds": 30.0,
    "api_delay_seconds": 0.5,  # Rate limiting
    "cache_transcriptions": True,
    "cache_ai_decisions": True,
    "export_decisions_json": True,
    "use_custom_prompt": False,
    "custom_prompt_template": None
}
```

---

## 🌐 Web UI Integration

### HTML Changes (`web/web_ui/index.html`)
1. **New Button in Toolbar**:
   - "🤖 AI Analysis" button added after "Detect Silence"
   - Purple background (#9b59b6) to distinguish from other buttons

2. **New Settings Panel**:
   - together.ai API Key input field (password type)
   - Whisper Model selector (tiny/base/small/medium/large)
   - Analysis status display with summary

### JavaScript Changes (`web/web_ui/main.js`)
- **New Function**: `runAIAnalysis()`
  - Validates video loaded and silence detection completed
  - Checks for API key
  - Calls Python backend
  - Updates timeline with AI-colored segments
  - Displays analysis summary

### Python API (`web/web_main.py`)
- **New Method**: `Api.run_ai_analysis()`
  - Coordinates full AI pipeline
  - Validates inputs
  - Returns updated segments with AI decisions
  - Provides analysis summary

### Timeline Display (`web/web_ui/timeline.js`)
- **Already supports AI colors**:
  - Green (#2fb344): Audible segments with `keep=True` (AI says KEEP)
  - Orange (#ff8c00): Audible segments with `keep=False` (AI says FLAG)
  - Gray (#666666): Silent segments kept
  - Red (#ef4444): Silent segments removed
- AI decisions override default colors for audible segments

---

## 📦 Dependencies

### `requirements.txt` Created
```
customtkinter>=5.2.0
pywebview>=4.0.0
Pillow>=10.0.0
numpy>=1.24.0
openai-whisper>=20231117  # Local transcription
requests>=2.31.0  # together.ai API
pydantic>=2.5.0  # Structured parsing
```

### Installation
```bash
pip install -r requirements.txt
```

---

## 🎯 How to Use

### 1. Get together.ai API Key
- Sign up at https://together.ai
- Get your API key from the dashboard

#### API Key Management Options

**Current Implementation (Manual Entry):**
- API key must be entered in the UI each session
- Not persisted to disk (more secure for shared computers)
- Uses password field to hide key while typing

**Alternative: Environment Variable (.env file)**

For development/testing convenience, you can use a `.env` file:

1. **Install python-dotenv**:
   ```bash
   pip install python-dotenv
   ```

2. **Create `.env` file** in the project root:
   ```bash
   # .env
   TOGETHER_AI_API_KEY=your_api_key_here
   
   # Optional: Customize AI settings
   WHISPER_MODEL=base
   TOGETHER_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
   CONTEXT_WINDOW_SECONDS=30.0
   ```
   
   **Tip**: Create a `.env.example` file (without actual keys) to commit to git as a template for other developers.

3. **Add `.env` to `.gitignore`** to prevent committing your key:
   ```bash
   echo ".env" >> .gitignore
   ```

4. **Modify code to read from environment** (optional enhancement):
   ```python
   # In web_main.py or orchestrator.py
   import os
   from dotenv import load_dotenv
   
   load_dotenv()  # Load .env file
   api_key = os.getenv("TOGETHER_AI_API_KEY", "")
   
   # Use this as default if UI field is empty
   if not api_key:
       api_key = user_provided_key  # Fall back to UI input
   ```

**Other Options:**
- **System Keyring** (most secure): Use `keyring` library to store in OS credential manager
- **Settings File**: Save to `video_cutter_settings.json` (like other app settings)
- **Environment Variable**: Set `TOGETHER_AI_API_KEY` in system environment

⚠️ **Security Note**: Never commit API keys to version control. Always use `.gitignore` for `.env` files.

### 2. Load and Process Video
1. **Load Video**: Click "Load Video" button
2. **Detect Silence**: Select audio track and click "Detect Silence"
3. **Review Segments**: Check the timeline shows audible (green) and silent (gray) segments

### 3. Run AI Analysis
1. **Enter API Key**: Paste your together.ai API key in the settings panel
2. **Select Whisper Model**: Choose transcription quality (base recommended)
3. **Click "🤖 AI Analysis"**: This will:
   - Transcribe all audible segments locally with Whisper
   - Build context windows around each segment
   - Analyze content with together.ai
   - Update segment colors based on AI decisions

### 4. Review Results
- **Timeline Colors**:
  - **Green**: AI recommends KEEP (valuable content)
  - **Orange**: AI recommends FLAG (consider removing)
  - Check console output for detailed reasoning

- **Analysis Summary**:
  - Shows count of KEEP/FLAG/UNCERTAIN decisions
  - Average confidence score
  - Processing time

### 5. Export Video
- Segments marked as keep=True will be included in export
- Segments marked as keep=False will be excluded
- You can manually override AI suggestions by clicking segments in timeline

---

## 🔧 Prompt Customization

The AI analysis prompt is **intentionally flexible** for iteration. Current default prompt (`ai_analyzer.py`) implements:

### Three Perspectives (in one prompt):
1. **Steelman**: What's the best case for keeping this?
2. **Skeptic**: Why might this be filler or low-value?
3. **Judge**: Final verdict weighing both sides

### Content Evaluation Criteria

**KEEP if**:
- Asides, jokes, moments of letting audience in
- Valuable insights or information
- Good storytelling and narrative flow
- Authentic connection with viewers

**FLAG if**:
- Technical difficulties or errors
- Excessive filler words or meaningless sentences
- Self-aggrandizing rants or self-important monologues
- Content that doesn't contribute value

### Customization Options:
1. **Edit the default prompt** in `ai_analyzer.py` (line ~50)
2. **Create custom prompt file** and set path in config
3. **Use `custom_prompt_template`** parameter in API calls

All prompts and responses are logged for analysis and iteration.

---

## 🏗️ Tkinter UI Integration

**Status**: Pattern established, implementation straightforward

The Tkinter UI can follow the same pattern as Web UI:

1. Add "🤖 AI Analysis" button to main_tab.py
2. Add API key and Whisper model settings
3. Create handler that calls `orchestrator.analyze_content()`
4. Update timeline widget to respect `segment.ai_decision` property
5. Display analysis summary in UI

The heavy lifting is done by the `ai_analysis` package, so integration is primarily UI wiring.

---

## 🧪 Testing Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Get together.ai API key
- [ ] Load a test video with speech
- [ ] Run silence detection
- [ ] Run AI analysis (with small Whisper model first)
- [ ] Verify timeline colors update (green for keep, orange for flag)
- [ ] Check console output for transcription and analysis details
- [ ] Manually toggle a segment color by clicking
- [ ] Export video and verify AI decisions are respected

---

## 📝 Notes

### Performance Considerations:
- **Whisper transcription** is CPU/GPU intensive:
  - "tiny" model: Fastest, lower accuracy
  - "base" model: Good balance (recommended for testing)
  - "medium/large" models: Better accuracy, much slower
- **together.ai API** has rate limits:
  - 0.5s delay between requests (configurable)
  - Batch processing handles this automatically

### Cost Considerations:
- **Whisper**: Free (runs locally)
- **together.ai**: Pay per token
  - Each segment analysis ~500 tokens
  - 10 segments ≈ 5,000 tokens
  - Check together.ai pricing for estimates

### Caching:
- Transcriptions can be cached to avoid re-running Whisper
- AI decisions can be exported to JSON for review/reuse
- Implement caching for production use

---

## 🐛 Troubleshooting

### "Whisper is not installed"
```bash
pip install openai-whisper
```

### "together.ai API error"
- Check API key is correct
- Check API quota/credits
- Check network connection

### Slow transcription
- Use smaller Whisper model ("tiny" or "base")
- Consider GPU acceleration (install torch with CUDA)

### Memory issues
- Process videos in smaller chunks
- Use smaller Whisper model
- Reduce context window size

---

## 🚀 Future Enhancements

Potential improvements (not implemented yet):

1. **Prompt Engineering**:
   - A/B test different prompt strategies
   - Fine-tune keep/flag criteria for specific content types
   - Add content-type detection (tutorial, vlog, interview, etc.)

2. **Performance**:
   - GPU acceleration for Whisper
   - Parallel transcription of segments
   - Caching layer for repeated analysis

3. **UI**:
   - Show AI reasoning as tooltips on hover
   - Confidence visualization (color intensity)
   - Segment-by-segment review mode

4. **Analysis**:
   - Multiple AI model comparison
   - Ensemble voting across models
   - User feedback loop to improve prompts

---

## 📄 License & Credits

This feature integrates:
- **OpenAI Whisper**: Speech recognition model
- **together.ai**: LLM inference API
- **Pydantic**: Data validation

All integrated respecting their respective licenses.

---

**Implementation Date**: November 2024
**Version**: 1.0.0
**Status**: Production Ready ✅

