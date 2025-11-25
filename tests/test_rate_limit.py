"""
Rate limit test for AI analyzer.

Tests that the rate limiting delay between API requests is working correctly
to prevent 429 (Too Many Requests) errors.
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Add temp_repo to Python path so we can import video_production_app
_current_file = Path(__file__).resolve()
_temp_repo = _current_file.parent.parent  # tests/ -> temp_repo/
if str(_temp_repo) not in sys.path:
    sys.path.insert(0, str(_temp_repo))

from video_production_app.ai_analysis.ai_analyzer import analyze_segments_batch, Decision
from video_production_app.config import AI_ANALYSIS_SETTINGS

# Load environment variables
script_dir = Path(__file__).parent
env_path = script_dir / '.env'
if env_path.exists():
    try:
        content = env_path.read_text(encoding='utf-8-sig')
        env_path.write_text(content, encoding='utf-8')
    except Exception:
        pass
    load_dotenv(dotenv_path=env_path, override=True)

# Rate limiting delay (seconds between requests)
DELAY = 1.0


def create_dummy_segments(num_segments: int = 10) -> dict:
    """
    Create dummy segments for testing.
    
    Args:
        num_segments: Number of segments to create
        
    Returns:
        Dictionary mapping segment_id to (text, context) tuples
    """
    segments = {}
    for i in range(1, num_segments + 1):
        segment_id = f"seg_{i}"
        text = f"test segment {i}"
        segments[segment_id] = (text, None)  # No context for simplicity
    
    return segments


def test_rate_limiting():
    """Test that rate limiting is working correctly."""
    
    print("=" * 80)
    print("RATE LIMIT TEST")
    print("=" * 80)
    print()
    
    # Get API key
    api_key = os.getenv("TOGETHER_API_KEY") or AI_ANALYSIS_SETTINGS.get("api_key", "")
    
    if not api_key:
        print("❌ Error: TOGETHER_API_KEY not found.")
        print("   Please set it in your .env file or environment variables.")
        return False
    
    # Get model settings
    model = AI_ANALYSIS_SETTINGS.get("model", "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo")
    
    # Create dummy segments
    num_segments = 10
    segments = create_dummy_segments(num_segments)
    
    print(f"Configuration:")
    print(f"  Number of segments: {num_segments}")
    print(f"  Delay between requests: {DELAY} seconds")
    print(f"  Model: {model}")
    print()
    
    # Calculate expected minimum duration
    # With 10 segments and 1 second delay, we should have 9 delays (between segments)
    expected_min_duration = (num_segments - 1) * DELAY
    
    print(f"Expected minimum duration: {expected_min_duration:.2f} seconds")
    print(f"  (This accounts for {num_segments - 1} delays between {num_segments} segments)")
    print()
    
    # Run batch analysis
    print("Starting batch analysis...")
    print()
    
    start_time = time.time()
    
    try:
        decisions = analyze_segments_batch(
            segments_with_context=segments,
            api_key=api_key,
            model=model,
            prompt_template=None,
            status_callback=None,  # Suppress status messages
            progress_callback=None,
            delay_between_requests=DELAY
        )
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        print()
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()
        
        print(f"Total duration: {total_duration:.2f} seconds")
        print(f"Expected minimum: {expected_min_duration:.2f} seconds")
        print()
        
        # Verification 1: Check timing
        if total_duration < expected_min_duration:
            print("❌ FAIL: Rate limiting not working")
            print(f"   Actual duration ({total_duration:.2f}s) is less than expected minimum ({expected_min_duration:.2f}s)")
            print(f"   This suggests delays are not being applied correctly.")
            return False
        else:
            print("✓ PASS: Rate limiting timing check")
            print(f"   Actual duration ({total_duration:.2f}s) >= expected minimum ({expected_min_duration:.2f}s)")
        
        print()
        
        # Verification 2: Check for rate limit errors
        rate_limit_hit = False
        api_errors = []
        
        for segment_id, decision in decisions.items():
            reasoning_lower = decision.reasoning.lower()
            raw_response_lower = decision.raw_response.lower() if decision.raw_response else ""
            
            # Check for 429 errors or rate limit indicators
            if "429" in reasoning_lower or "429" in raw_response_lower:
                rate_limit_hit = True
                api_errors.append(f"{segment_id}: 429 Rate Limit Error")
            
            # Check for API errors that might indicate rate limiting
            if "api error" in reasoning_lower or "rate limit" in reasoning_lower:
                if "429" not in reasoning_lower:  # Already counted above
                    api_errors.append(f"{segment_id}: {decision.reasoning[:50]}")
        
        if rate_limit_hit:
            print("❌ FAIL: Hit Rate Limit")
            print("   One or more requests returned 429 (Too Many Requests) errors:")
            for error in api_errors:
                print(f"   - {error}")
            return False
        else:
            print("✓ PASS: No rate limit errors detected")
        
        print()
        
        # Additional statistics
        successful_decisions = sum(1 for d in decisions.values() if d.decision != Decision.UNCERTAIN)
        uncertain_decisions = sum(1 for d in decisions.values() if d.decision == Decision.UNCERTAIN)
        
        print(f"Statistics:")
        print(f"  Successful decisions: {successful_decisions}/{num_segments}")
        print(f"  Uncertain decisions: {uncertain_decisions}/{num_segments}")
        
        if uncertain_decisions > 0:
            print()
            print("⚠ Warning: Some decisions are UNCERTAIN. This might indicate:")
            print("   - API errors (check reasoning field)")
            print("   - Parsing issues")
            print("   - Network problems")
        
        print()
        print("=" * 80)
        print("✅ PASS: Rate limiting successful")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_rate_limiting()
    exit(0 if success else 1)

