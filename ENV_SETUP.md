# Environment Variable Setup

This guide explains how to set up environment variables for the Video Production Suite, particularly for AI content analysis features.

## Quick Start

### Option 1: Use .env File (Recommended for Development)

1. **Install python-dotenv** (if not already installed):
   ```bash
   pip install python-dotenv
   ```

2. **Create a `.env` file** in the project root (`video_production_by_tooboooring/.env`):
   ```bash
   # together.ai API Key for AI Content Analysis
   TOGETHER_API_KEY=your_actual_api_key_here
   
   # Optional: Customize AI settings
   WHISPER_MODEL=base
   TOGETHER_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
   CONTEXT_WINDOW_SECONDS=30.0
   ```

3. **The `.env` file is automatically ignored by git** (already in `.gitignore`)

### Option 2: System Environment Variables

**Windows:**
```cmd
setx TOGETHER_API_KEY "your_api_key_here"
```

**macOS/Linux:**
```bash
export TOGETHER_API_KEY="your_api_key_here"
# Add to ~/.bashrc or ~/.zshrc to persist
```

### Option 3: Manual Entry (Current Default)

Simply enter your API key in the UI settings panel each session. This is the most secure option for shared computers.

---

## Getting Your API Key

1. Sign up at https://together.ai
2. Navigate to API Keys in your dashboard
3. Create a new API key
4. Copy the key (it will only be shown once!)

---

## Security Best Practices

✅ **DO:**
- Use `.env` files for local development
- Add `.env` to `.gitignore` (already done)
- Use system environment variables for production
- Rotate API keys regularly
- Use different keys for development and production

❌ **DON'T:**
- Commit API keys to version control
- Share API keys in screenshots or logs
- Hardcode API keys in source code
- Use production keys for testing

---

## For Code Modifications

If you want to implement automatic `.env` loading in the application:

```python
# At the top of web_main.py or orchestrator.py
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get API key from environment, fall back to UI input
api_key = os.getenv("TOGETHER_API_KEY", "")
if not api_key:
    # Use the UI-provided key as fallback
    api_key = user_provided_api_key
```

---

## Troubleshooting

**"python-dotenv not found"**
```bash
pip install python-dotenv
```

**".env file not loading"**
- Ensure `.env` is in the correct directory (project root)
- Check file name is exactly `.env` (not `.env.txt`)
- Verify no extra spaces in variable assignments
- Make sure `load_dotenv()` is called before accessing variables

**"API key still required in UI"**
- Current implementation doesn't auto-load from `.env`
- This is by design for security
- See "For Code Modifications" section to implement auto-loading

---

## Related Documentation

See `AI_ANALYSIS_IMPLEMENTATION_SUMMARY.md` for complete AI analysis feature documentation.

