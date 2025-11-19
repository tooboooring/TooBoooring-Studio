"""
AI analyzer using together.ai API.

This module handles communication with together.ai for semantic content analysis.
Prompt strategy is intentionally flexible to support iteration and experimentation.
"""

import json
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Callable
from enum import Enum

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("[WARNING] requests library not available. AI analysis will not work.")

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


class Decision(str, Enum):
    """Decision values for content analysis."""
    KEEP = "KEEP"
    FLAG = "FLAG"
    UNCERTAIN = "UNCERTAIN"


@dataclass
class SegmentDecision:
    """Represents an AI decision about a content segment."""
    decision: Decision
    confidence: float  # 0.0 to 1.0
    reasoning: str
    raw_response: str  # Full LLM response for debugging
    prompt_used: str   # The prompt template used
    model: str
    processing_time: float  # Seconds


# Pydantic model for structured output (if available)
if PYDANTIC_AVAILABLE:
    class SegmentAnalysisResponse(BaseModel):
        """Structured response format for segment analysis."""
        decision: str = Field(description="KEEP, FLAG, or UNCERTAIN")
        confidence: float = Field(ge=0.0, le=1.0, description="Confidence level 0-1")
        reasoning: str = Field(description="Explanation of the decision")
        key_points: list[str] = Field(default_factory=list, description="Main points discussed")
        content_type: str = Field(default="", description="Type of content (e.g., 'aside', 'filler', 'joke')")


# Default prompt template (can be overridden via config)
DEFAULT_PROMPT_TEMPLATE = """You are analyzing a transcript segment from a video to determine if it should be kept or flagged for removal.

Your task is to evaluate the content using three perspectives (steelman, skeptic, judge) and reach a decision:

**KEEP if the content is:**
- Asides, jokes, or moments that let the audience in
- Valuable insights or information
- Good storytelling or narrative flow
- Authentic connection with viewers

**FLAG if the content is:**
- Technical difficulties or errors
- Excessive filler words or meaningless filler sentences
- Self-aggrandizing rants or self-important monologues
- Content that doesn't contribute to the main value

---

**SEGMENT TRANSCRIPT:**
{segment_text}

{context_section}

---

**ANALYSIS INSTRUCTIONS:**

1. **STEELMAN PERSPECTIVE**: What's the best case for keeping this content? What value might it provide?

2. **SKEPTIC PERSPECTIVE**: What are the reasons this might be filler or low-value content?

3. **JUDGE PERSPECTIVE**: Weighing both sides, what's the verdict?

**OUTPUT FORMAT (JSON):**
```json
{{
  "decision": "KEEP" or "FLAG",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of your decision",
  "key_points": ["point1", "point2"],
  "content_type": "aside|filler|joke|insight|technical_issue|rant|other"
}}
```

Respond ONLY with the JSON object, no additional text.
"""


def validate_api_connection(
    api_key: str,
    model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    timeout: int = 60
) -> bool:
    """
    Validate API connection and authentication before starting analysis.
    
    Makes a minimal API request to verify:
    - API key is valid (not 401/403)
    - Network connection is working
    - API endpoint is reachable
    
    This is called BEFORE transcription to "fail fast" on invalid credentials.
    
    NOTE: Timeouts during validation are CRITICAL and abort the process.
    Timeouts during actual analysis (analyze_segment) are treated as recoverable
    and return UNCERTAIN to allow processing of remaining segments.
    
    Args:
        api_key: together.ai API key to validate
        model: Model ID to test (default: Llama 3.1 8B)
        timeout: Request timeout in seconds (default: 60)
        
    Returns:
        True if validation succeeds
        
    Raises:
        ImportError: If requests library is not available
        ValueError: If API key is invalid (401/403 response)
        ConnectionError: If network is unavailable or cannot reach API
        TimeoutError: If validation request times out
        RuntimeError: For other unexpected errors
    """
    if not REQUESTS_AVAILABLE:
        raise ImportError("requests library is required. Install with: pip install requests")
    
    if not api_key:
        raise ValueError("together.ai API key is required")
    
    # Prepare minimal API request (just a ping)
    api_url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "ping"
            }
        ],
        "max_tokens": 1,  # Minimal response to save costs
        "temperature": 0.0
    }
    
    try:
        # Make validation request
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        # Check for authentication errors
        if response.status_code in [401, 403]:
            raise ValueError("Authentication Failed: Invalid or expired together.ai API key")
        
        # Check for other errors
        response.raise_for_status()
        
        # Validation successful
        return True
        
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(f"Network error: Cannot reach together.ai API - {str(e)}")
    
    except requests.exceptions.Timeout as e:
        raise TimeoutError(f"API validation timeout: Request took longer than {timeout} seconds - {str(e)}")
    
    except requests.exceptions.HTTPError as e:
        # Re-raise HTTP errors (already handled above for 401/403)
        raise RuntimeError(f"API validation failed with HTTP error: {str(e)}")
    
    except ValueError:
        # Re-raise ValueError (authentication errors)
        raise
    
    except Exception as e:
        raise RuntimeError(f"Unexpected error during API validation: {str(e)}")


def analyze_segment(
    segment_text: str,
    context: Optional[Any] = None,
    api_key: str = "",
    model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    prompt_template: Optional[str] = None,
    status_callback: Optional[Callable[[str], None]] = None,
    temperature: float = 0.7,
    max_tokens: int = 500
) -> SegmentDecision:
    """
    Analyze a segment using together.ai API.
    
    Args:
        segment_text: The transcript text to analyze
        context: Optional ContextWindow object with before/after text
        api_key: together.ai API key
        model: Model ID to use (default: Llama 3.1 8B)
        prompt_template: Custom prompt template (uses default if None)
        status_callback: Optional callback for status messages
        temperature: LLM temperature (0.0-1.0)
        max_tokens: Maximum response tokens
        
    Returns:
        SegmentDecision object with analysis results
        OR SegmentDecision with UNCERTAIN for recoverable errors:
        - 5xx server errors (API temporarily unavailable)
        - Timeout errors (API slow or rate limited)
        - JSON parse errors (malformed response)
        
    Raises:
        ImportError: If requests library is not available
        ValueError: If API key is invalid (401/403 response)
        ConnectionError: If network is unavailable or cannot reach API
        RuntimeError: For unexpected errors during analysis
        
    Note:
        Timeouts during analysis are treated as recoverable and return UNCERTAIN.
        This allows batch processing to continue even if some segments are slow.
    """
    if not REQUESTS_AVAILABLE:
        raise ImportError("requests library is required. Install with: pip install requests")
    
    if not api_key:
        raise ValueError("together.ai API key is required")
    
    def log(msg: str):
        if status_callback:
            status_callback(msg)
    
    # Use provided template or default
    template = prompt_template or DEFAULT_PROMPT_TEMPLATE
    
    # Build context section if available
    context_section = ""
    if context:
        from .context_builder import format_context_for_prompt, ContextWindow
        if isinstance(context, ContextWindow):
            # Only include context in a note, not full text to avoid token bloat
            if context.before_text or context.after_text:
                context_section = f"\n**CONTEXT NOTE:**\n"
                if context.before_text:
                    context_section += f"Previous content: {context.before_text[:200]}...\n"
                if context.after_text:
                    context_section += f"Following content: {context.after_text[:200]}...\n"
    
    # Format the prompt
    prompt = template.format(
        segment_text=segment_text,
        context_section=context_section
    )
    
    # Prepare API request
    api_url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a content analysis assistant that evaluates video transcript segments."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"} if "json" in model.lower() else None
    }
    
    # Make API request
    start_time = time.time()
    try:
        log(f"🤖 Analyzing segment with {model}...\n")
        
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        # Check for authentication errors BEFORE raise_for_status
        if response.status_code in [401, 403]:
            log(f"   ❌ Authentication failed: Invalid API key\n")
            raise ValueError("Authentication Failed: Invalid or expired together.ai API key")
        
        response.raise_for_status()
        
        processing_time = time.time() - start_time
        result = response.json()
        
        # Extract the response text
        if 'choices' not in result or len(result['choices']) == 0:
            raise Exception("No response from API")
        
        raw_response = result['choices'][0]['message']['content']
        
        # Parse the JSON response
        try:
            # Try to extract JSON from response (handle cases where LLM adds extra text)
            json_start = raw_response.find('{')
            json_end = raw_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = raw_response[json_start:json_end]
                parsed = json.loads(json_str)
            else:
                # No JSON found, create default response
                parsed = {
                    "decision": "UNCERTAIN",
                    "confidence": 0.5,
                    "reasoning": "Could not parse structured response",
                    "key_points": [],
                    "content_type": "unknown"
                }
        except json.JSONDecodeError as e:
            log(f"   ⚠️ Failed to parse JSON response: {e}\n")
            # Create default response
            parsed = {
                "decision": "UNCERTAIN",
                "confidence": 0.5,
                "reasoning": f"JSON parse error: {str(e)}",
                "key_points": [],
                "content_type": "unknown"
            }
        
        # Validate decision value
        decision_str = parsed.get('decision', 'UNCERTAIN').upper()
        try:
            decision = Decision(decision_str)
        except ValueError:
            decision = Decision.UNCERTAIN
        
        # Extract confidence (ensure it's in range)
        confidence = float(parsed.get('confidence', 0.5))
        confidence = max(0.0, min(1.0, confidence))
        
        # Extract reasoning
        reasoning = parsed.get('reasoning', 'No reasoning provided')
        
        # Build key points summary if available
        key_points = parsed.get('key_points', [])
        content_type = parsed.get('content_type', 'unknown')
        
        if key_points or content_type != 'unknown':
            reasoning += f"\n[Type: {content_type}]"
            if key_points:
                reasoning += f"\n[Points: {', '.join(key_points[:3])}]"
        
        log(f"   ✓ Decision: {decision.value} (confidence: {confidence:.2f})\n")
        log(f"     📝 Reasoning: {reasoning}\n")
        
        return SegmentDecision(
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            raw_response=raw_response,
            prompt_used=prompt,
            model=model,
            processing_time=processing_time
        )
        
    except requests.exceptions.ConnectionError as e:
        # Critical error: No internet connection - abort immediately
        log(f"   ❌ Connection error: No internet or cannot reach API\n")
        raise ConnectionError(f"Network error: Cannot reach together.ai API - {str(e)}")
    
    except requests.exceptions.Timeout as e:
        # Timeout during analysis - treat as recoverable, return UNCERTAIN
        # (This can happen due to rate limiting or slow API response)
        log(f"   ⚠️ Request timeout: API took too long to respond (>60s)\n")
        return SegmentDecision(
            decision=Decision.UNCERTAIN,
            confidence=0.0,
            reasoning=f"API timeout: Request exceeded 60 seconds - {str(e)}",
            raw_response="",
            prompt_used=prompt,
            model=model,
            processing_time=time.time() - start_time
        )
    
    except requests.exceptions.HTTPError as e:
        # Check for server errors (5xx) - these are recoverable, return UNCERTAIN
        if hasattr(e.response, 'status_code') and 500 <= e.response.status_code < 600:
            log(f"   ⚠️ Server error {e.response.status_code}: API temporarily unavailable\n")
            return SegmentDecision(
                decision=Decision.UNCERTAIN,
                confidence=0.0,
                reasoning=f"Server error {e.response.status_code}: API temporarily unavailable",
                raw_response="",
                prompt_used=prompt,
                model=model,
                processing_time=time.time() - start_time
            )
        else:
            # Other HTTP errors (4xx except 401/403) - abort
            log(f"   ❌ HTTP error: {e}\n")
            raise
    
    except requests.exceptions.RequestException as e:
        # Other request errors - abort to be safe
        log(f"   ❌ Request error: {e}\n")
        raise
    
    except ValueError as e:
        # ValueError is used for authentication errors - re-raise
        raise
    
    except json.JSONDecodeError as e:
        # Minor error: Malformed JSON response - return UNCERTAIN
        log(f"   ⚠️ Failed to parse API response as JSON: {e}\n")
        return SegmentDecision(
            decision=Decision.UNCERTAIN,
            confidence=0.0,
            reasoning=f"Failed to parse API response: {str(e)}",
            raw_response="",
            prompt_used=prompt,
            model=model,
            processing_time=time.time() - start_time
        )
    
    except Exception as e:
        # Unexpected error - abort to be safe
        log(f"   ❌ Unexpected error: {e}\n")
        raise RuntimeError(f"Unexpected error during AI analysis: {str(e)}")


def analyze_segments_batch(
    segments_with_context: Dict[str, tuple],  # {segment_id: (text, context)}
    api_key: str,
    model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    prompt_template: Optional[str] = None,
    status_callback: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    delay_between_requests: float = 0.5,
    temperature: float = 0.7,
    max_tokens: int = 500
) -> Dict[str, SegmentDecision]:
    """
    Analyze multiple segments in batch.
    
    Args:
        segments_with_context: Dictionary mapping segment_id to (text, context) tuples
        api_key: together.ai API key
        model: Model ID to use
        prompt_template: Optional custom prompt template
        status_callback: Optional status message callback
        progress_callback: Optional progress callback (current, total)
        delay_between_requests: Delay in seconds between API calls (rate limiting)
        temperature: LLM temperature (0.0=deterministic, 0.7=creative, 1.0=very random)
        max_tokens: Maximum response tokens
        
    Returns:
        Dictionary mapping segment_id to SegmentDecision
    """
    def log(msg: str):
        if status_callback:
            status_callback(msg)
    
    log(f"🤖 Starting batch analysis of {len(segments_with_context)} segments...\n")
    
    decisions = {}
    total = len(segments_with_context)
    
    for idx, (segment_id, (text, context)) in enumerate(segments_with_context.items(), start=1):
        log(f"   [{idx}/{total}] Analyzing {segment_id}...\n")
        
        if progress_callback:
            progress_callback(idx, total)
        
        decision = analyze_segment(
            segment_text=text,
            context=context,
            api_key=api_key,
            model=model,
            prompt_template=prompt_template,
            status_callback=None,  # Suppress per-segment logs
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        decisions[segment_id] = decision
        
        # Rate limiting delay
        if idx < total and delay_between_requests > 0:
            time.sleep(delay_between_requests)
    
    log(f"✅ Batch analysis complete: {len(decisions)} segments analyzed\n")
    return decisions


def export_decisions_to_json(
    decisions: Dict[str, SegmentDecision],
    output_path: str
) -> None:
    """
    Export decisions to JSON file for review and debugging.
    
    Args:
        decisions: Dictionary of SegmentDecision objects
        output_path: Path to save JSON file
    """
    export_data = {}
    
    for segment_id, decision in decisions.items():
        export_data[segment_id] = {
            'decision': decision.decision.value,
            'confidence': decision.confidence,
            'reasoning': decision.reasoning,
            'model': decision.model,
            'processing_time': decision.processing_time,
            'raw_response': decision.raw_response
        }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)


def load_decisions_from_json(input_path: str) -> Dict[str, SegmentDecision]:
    """
    Load previously saved decisions from JSON file.
    
    Args:
        input_path: Path to JSON file
        
    Returns:
        Dictionary of SegmentDecision objects
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    decisions = {}
    for segment_id, dec_data in data.items():
        decisions[segment_id] = SegmentDecision(
            decision=Decision(dec_data['decision']),
            confidence=dec_data['confidence'],
            reasoning=dec_data['reasoning'],
            raw_response=dec_data.get('raw_response', ''),
            prompt_used='',  # Not saved
            model=dec_data.get('model', 'unknown'),
            processing_time=dec_data.get('processing_time', 0.0)
        )
    
    return decisions

