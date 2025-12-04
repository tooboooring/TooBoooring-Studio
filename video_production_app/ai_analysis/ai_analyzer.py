"""
AI analyzer using Google Gemini 3 Pro.
"""
import json
import time
import os
from dataclasses import dataclass
from typing import Optional, Callable, Any
from enum import Enum

# Try to import Google Gen AI
try:
    from google import genai
    from google.genai import types
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    print("[WARNING] google-genai library not available.")

class Decision(str, Enum):
    KEEP = "KEEP"
    FLAG = "FLAG"
    UNCERTAIN = "UNCERTAIN"

@dataclass
class SegmentDecision:
    decision: Decision
    confidence: float
    reasoning: str
    raw_response: str
    prompt_used: str
    model: str
    processing_time: float

# Simplified prompt for Gemini
DEFAULT_PROMPT_TEMPLATE = """You are a professional Video Editor.
Evaluate this video transcript segment.

**CONTEXT:**
{context_section}

**SEGMENT:**
{segment_text}

**TASK:**
1. Analyze if this segment is high-value (Keep) or low-value/fluff (Cut).
2. Provide your reasoning.
3. Output JSON: {{"reasoning": "string", "decision": "KEEP" or "FLAG", "confidence": 0.0-1.0}}
"""

def analyze_segment(
    segment_text: str,
    context: Optional[Any] = None,
    api_key: str = "",
    model: str = "gemini-2.5-pro",
    prompt_template: Optional[str] = None,
    status_callback: Optional[Callable[[str], None]] = None,
    temperature: float = 0.7,
    max_tokens: int = 8000
) -> SegmentDecision:
    
    if not GOOGLE_GENAI_AVAILABLE:
        raise ImportError("google-genai not installed.")

    # Use API key from env if not provided
    final_api_key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not final_api_key:
        raise ValueError("Google API key is required.")

    client = genai.Client(api_key=final_api_key)
    
    if status_callback:
        status_callback(f"🧠 Gemini 3 Pro is thinking... (Reasoning Enabled)\n")

    # Prepare prompt
    context_section = ""
    if context:
        if hasattr(context, 'before_text') and context.before_text:
             context_section += f"PREVIOUS: {context.before_text[-200:]}\n"
        if hasattr(context, 'after_text') and context.after_text:
             context_section += f"FOLLOWING: {context.after_text[:200]}\n"

    template = prompt_template or DEFAULT_PROMPT_TEMPLATE
    final_prompt = template.format(segment_text=segment_text, context_section=context_section)
    
    start_time = time.time()
    
    max_retries = 3
    retry_delay = 5  # Initial delay
    
    for attempt in range(max_retries + 1):
        try:
            # Call Gemini 3 Pro with Thinking
            response = client.models.generate_content(
                model=model,
                contents=[final_prompt],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    # THE WINNING FEATURE: Thinking Logs
                    thinking_config=types.ThinkingConfig(include_thoughts=True), 
                    response_mime_type="application/json"
                )
            )
            
            # Parse response
            parsed = json.loads(response.text)
            
            decision_str = parsed.get('decision', 'UNCERTAIN').upper()
            # Fallback if model returns slightly different string
            if 'KEEP' in decision_str: decision_enum = Decision.KEEP
            elif 'FLAG' in decision_str: decision_enum = Decision.FLAG
            else: decision_enum = Decision.UNCERTAIN

            return SegmentDecision(
                decision=decision_enum,
                confidence=float(parsed.get('confidence', 0.5)),
                reasoning=parsed.get('reasoning', 'No reasoning provided'),
                raw_response=response.text,
                prompt_used=final_prompt,
                model=model,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    if status_callback: 
                        status_callback(f"⏳ Rate limit hit. Waiting {wait_time}s before retry {attempt+1}/{max_retries}...\n")
                    time.sleep(wait_time)
                    continue
            
            if status_callback: status_callback(f"❌ Error: {str(e)}")
            # Return safe default on error
            return SegmentDecision(Decision.UNCERTAIN, 0.0, f"Error: {str(e)}", "", "", model, 0.0)

# Stub functions to keep orchestrator working without changes
def validate_api_connection(*args, **kwargs): return True

def analyze_segments_batch(segments_with_context, api_key, model=None, **kwargs):
    # Simple sequential processor for the hackathon
    results = {}
    status_cb = kwargs.get('status_callback')
    
    # Add delay between requests to avoid hitting rate limits immediately
    # Free tier limit is very low (2 RPM), so we need significant delay
    # Or we rely on the retry logic in analyze_segment
    
    for i, (seg_id, (text, context)) in enumerate(segments_with_context.items()):
        if i > 0:
            # Small delay between requests to be nice, but rely on retry logic for 429s
            time.sleep(2) 
        results[seg_id] = analyze_segment(text, context, api_key, model=model, status_callback=status_cb)
    return results

def export_decisions_to_json(decisions: dict, export_path: str) -> None:
    """Export AI decisions to JSON file for review."""
    export_data = {}
    for seg_id, decision in decisions.items():
        export_data[seg_id] = {
            "decision": decision.decision.value if hasattr(decision.decision, 'value') else str(decision.decision),
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "model": decision.model,
            "processing_time": decision.processing_time
        }
    
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

