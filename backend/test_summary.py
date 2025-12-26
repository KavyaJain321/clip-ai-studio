import os
import sys
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_summary_generation():
    print("=== Summary Generation Test ===")
    
    try:
        sys.path.append(os.getcwd())
        from services.gemini_service import generate_summary
        
        # Test Data
        clip_transcript = "We were walking down the beach and saw the most vibrant sunset. The colors were orange and purple."
        keyword = "vibrant"
        context_before = "Topics discussed: nature, photography."
        
        print(f"Input: {clip_transcript}")
        print(f"Keyword: {keyword}")
        
        result = generate_summary(
            clip_transcript=clip_transcript,
            keyword=keyword,
            context_before=context_before
        )
        
        print("\n--- Result ---")
        print(json.dumps(result, indent=2))
        
        if result["status"] == "success":
             print("\nTEST PASS: Summary generated successfully.")
        else:
             print(f"\nTEST WARN: Status is {result['status']}")

    except ImportError:
        print("ERROR: Could not import services.gemini_service. Run from backend root.")
    except Exception as e:
        print(f"TEST FAIL: {e}")

if __name__ == "__main__":
    test_summary_generation()
