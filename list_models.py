
import os
import google.genai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not found in environment variables.")
    exit(1)

try:
    client = genai.Client(api_key=api_key)
    print("Listing available models...")
    # The SDK might have a different way to list models, let's try the standard way if possible or just try a generation to see if we can get a better error or success with a known model.
    # Actually, the error message suggested "Call ListModels".
    # In the new google-genai SDK, it might be client.models.list()
    
    # Let's try to list models if the SDK supports it easily, otherwise we'll try a few known candidates.
    # Based on documentation for google-genai (v0.2.1+), it should be client.models.list()
    
    for model in client.models.list():
        print(f"Model: {model.name}")
        # print(f"  DisplayName: {model.display_name}") 
    
except Exception as e:
    print(f"Error listing models: {e}")

    # Fallback: Try to generate with 'models/' prefix
    print("\nTrying fallback generation with 'models/gemini-1.5-flash'...")
    try:
        response = client.models.generate_content(
            model="models/gemini-1.5-flash",
            contents="Hello, are you working?"
        )
        print(f"Success! Response: {response.text}")
    except Exception as e2:
        print(f"Fallback failed: {e2}")
