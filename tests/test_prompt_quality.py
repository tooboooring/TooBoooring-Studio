"""
Test script for comparing different prompt engineering personas.

This script tests three different editing personas (STRICT_RETENTION, NARRATIVE_FLOW,
AUDIENCE_CONNECTION) against the same transcript sample to see how each persona
evaluates content differently.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add temp_repo to Python path so we can import video_production_app
_current_file = Path(__file__).resolve()
_temp_repo = _current_file.parent.parent  # tests/ -> temp_repo/
if str(_temp_repo) not in sys.path:
    sys.path.insert(0, str(_temp_repo))

from video_production_app.config import AI_ANALYSIS_SETTINGS
from video_production_app.ai_analysis.ai_analyzer import analyze_segment

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

# Sample transcript with mixed content: good info, filler words, and a tangent
SAMPLE_TRANSCRIPT = """
So, um, I've been thinking about this for a while, like, you know, and I think 
quantum computing is really fascinating. Like, the way particles can exist in 
multiple states simultaneously is just mind-blowing. But honestly, I have to say, 
and this might sound a bit ranty, but I'm so tired of people who don't understand 
the basics trying to explain quantum mechanics. Like, come on, do your research 
first! Anyway, back to the point - quantum computers could revolutionize 
cryptography, which is pretty cool. And, um, I guess that's all I wanted to say 
about that.
"""


def test_prompt_personas():
    """Test all prompt templates and compare results."""
    
    # Get API key
    api_key = os.getenv("TOGETHER_API_KEY") or AI_ANALYSIS_SETTINGS.get("api_key", "")
    
    if not api_key:
        print("❌ Error: TOGETHER_API_KEY not found.")
        print("   Please set it in your .env file or environment variables.")
        return
    
    # Get model settings
    model = AI_ANALYSIS_SETTINGS.get("model", "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo")
    temperature = AI_ANALYSIS_SETTINGS.get("temperature", 0.7)
    max_tokens = AI_ANALYSIS_SETTINGS.get("max_tokens", 500)
    
    # Get prompt templates
    prompt_templates = AI_ANALYSIS_SETTINGS.get("PROMPT_TEMPLATES", {})
    
    if not prompt_templates:
        print("❌ Error: PROMPT_TEMPLATES not found in AI_ANALYSIS_SETTINGS.")
        return
    
    print("=" * 80)
    print("PROMPT PERSONA COMPARISON TEST")
    print("=" * 80)
    print(f"\nModel: {model}")
    print(f"Sample Transcript:")
    print(f"{'-' * 80}")
    print(SAMPLE_TRANSCRIPT.strip())
    print(f"{'-' * 80}\n")
    
    results = []
    
    # Test each persona
    for persona_name, prompt_template in prompt_templates.items():
        print(f"Testing: {persona_name}...")
        
        try:
            decision = analyze_segment(
                segment_text=SAMPLE_TRANSCRIPT.strip(),
                context=None,
                api_key=api_key,
                model=model,
                prompt_template=prompt_template,
                status_callback=None,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            results.append({
                "persona": persona_name,
                "decision": decision.decision.value,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning
            })
            
            print(f"  ✓ Completed: {decision.decision.value} (confidence: {decision.confidence:.2f})\n")
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}\n")
            results.append({
                "persona": persona_name,
                "decision": "ERROR",
                "confidence": 0.0,
                "reasoning": str(e)
            })
    
    # Print comparison table
    print("\n" + "=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)
    print()
    
    # Table header
    print(f"{'Persona':<25} | {'Decision':<12} | {'Confidence':<12} | {'Reasoning (first 100 chars)'}")
    print("-" * 80)
    
    # Table rows
    for result in results:
        persona = result["persona"]
        decision = result["decision"]
        confidence = f"{result['confidence']:.2f}" if result['confidence'] > 0 else "N/A"
        reasoning = result["reasoning"][:100] + "..." if len(result["reasoning"]) > 100 else result["reasoning"]
        
        print(f"{persona:<25} | {decision:<12} | {confidence:<12} | {reasoning}")
    
    print("\n" + "=" * 80)
    
    # Summary statistics
    keep_count = sum(1 for r in results if r["decision"] == "KEEP")
    flag_count = sum(1 for r in results if r["decision"] == "FLAG")
    error_count = sum(1 for r in results if r["decision"] == "ERROR")
    
    print("\nSummary:")
    print(f"  KEEP decisions: {keep_count}/{len(results)}")
    print(f"  FLAG decisions: {flag_count}/{len(results)}")
    if error_count > 0:
        print(f"  Errors: {error_count}/{len(results)}")
    
    avg_confidence = sum(r["confidence"] for r in results if r["confidence"] > 0) / max(1, len([r for r in results if r["confidence"] > 0]))
    print(f"  Average confidence: {avg_confidence:.2f}")


if __name__ == "__main__":
    test_prompt_personas()

