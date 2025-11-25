"""
Test script for DeepSeek R1 model connection via Together.ai API.

This script tests the connection to the DeepSeek Reasoner model and displays
the full JSON response including any reasoning fields.
"""

import requests
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Find .env file relative to this script's location
script_dir = Path(__file__).parent
env_path = script_dir / '.env'

# Load .env file if it exists
if env_path.exists():
    # Handle UTF-8 BOM if present (Windows sometimes adds this)
    try:
        content = env_path.read_text(encoding='utf-8-sig')  # utf-8-sig automatically strips BOM
        env_path.write_text(content, encoding='utf-8')  # Rewrite without BOM
    except Exception:
        pass  # If we can't fix it, try loading anyway
    
    load_dotenv(dotenv_path=env_path, override=True)
    print(f"✓ Loading .env from: {env_path}")
else:
    print(f"⚠ Warning: .env file not found at: {env_path}")
    print(f"  Please create a .env file with your TOGETHER_API_KEY")
    print(f"  You can copy .env.example to .env and add your API key")
    # Try loading anyway (might be in environment already)
    load_dotenv(dotenv_path=env_path)

def test_deepseek_connection():
    """Test connection to DeepSeek R1 model via Together.ai API."""
    
    # Get API key from environment
    api_key = os.getenv("TOGETHER_API_KEY")
    
    if not api_key:
        print("\n❌ Failure: TOGETHER_API_KEY not found in environment variables.")
        print(f"   Expected .env file location: {env_path}")
        print("   Please create a .env file with: TOGETHER_API_KEY=your_key_here")
        return False
    
    # API endpoint
    url = "https://api.together.xyz/v1/chat/completions"
    
    # Model ID for DeepSeek Reasoner
    model = "deepseek-ai/DeepSeek-R1"
    
    # Test prompt
    prompt = "Hello, explain quantum physics in one sentence"
    
    # Request headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Request payload
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        print(f"Testing connection to {model}...")
        print(f"Prompt: {prompt}\n")
        
        # Make API request
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        # Check if request was successful
        if response.status_code == 200:
            print("Success: API request completed successfully!\n")
            
            # Parse and pretty-print the JSON response
            response_data = response.json()
            print("Full JSON Response:")
            print(json.dumps(response_data, indent=2))
            
            # Extract and display key information
            if "choices" in response_data and len(response_data["choices"]) > 0:
                choice = response_data["choices"][0]
                
                # Check for reasoning field (if present in DeepSeek R1)
                if "reasoning" in choice.get("message", {}):
                    print("\n--- Reasoning Content ---")
                    print(choice["message"]["reasoning"])
                
                # Display the main content
                if "content" in choice.get("message", {}):
                    print("\n--- Response Content ---")
                    print(choice["message"]["content"])
            
            return True
        else:
            print(f"Failure: API request failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Failure: Request exception occurred: {str(e)}")
        return False
    except json.JSONDecodeError as e:
        print(f"Failure: Failed to parse JSON response: {str(e)}")
        print(f"Raw response: {response.text}")
        return False
    except Exception as e:
        print(f"Failure: Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_deepseek_connection()
    exit(0 if success else 1)

