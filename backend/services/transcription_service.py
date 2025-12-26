import os
import json
import logging
import google.generativeai as genai
from typing import List, Dict, Any, Optional

# Try importing whisper, but don't fail if not installed (soft dependency for now)
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def transcribe_audio_gemini(audio_path: str, api_key: str) -> Dict[str, Any]:
    """
    Transcribes audio using Google Gemini 1.5 Flash.
    Returns structured JSON with text and word-level timestamps.
    """
    if not api_key:
        raise ValueError("Gemini API Key is missing")

    genai.configure(api_key=api_key)
    
    logger.info(f"Uploading {audio_path} to Gemini...")
    audio_file = genai.upload_file(path=audio_path, mime_type="audio/wav")
    
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    
    # Prompt for structured output
    prompt = """
    Transcribe this audio file accurately.
    Return a valid JSON object with the following structure:
    {
        "transcript": "Full text of the transcription",
        "words": [
            {"word": "word1", "start": 0.0, "end": 0.5},
            {"word": "word2", "start": 0.5, "end": 1.0}
        ]
    }
    Ensure the "words" array covers the entire speech.
    Timestamps should be floats in seconds.
    RETURN ONLY RAW JSON. NO MARKDOWN.
    """
    
    response = model.generate_content([prompt, audio_file])
    response_text = response.text.strip()
    
    # Clean cleanup logic
    if response_text.startswith("```json"):
        response_text = response_text.split("\n", 1)[1]
    if response_text.endswith("```"):
        response_text = response_text.rsplit("\n", 1)[0]
        
    return json.loads(response_text)

def transcribe_audio_whisper(audio_path: str, model_size: str = "base") -> Dict[str, Any]:
    """
    Transcribes audio using OpenAI Whisper (Local).
    """
    if not WHISPER_AVAILABLE:
        raise ImportError("openai-whisper is not installed. fallback unavailable.")
        
    logger.info(f"Loading Whisper model '{model_size}'...")
    model = whisper.load_model(model_size)
    
    logger.info(f"Transcribing {audio_path} with Whisper...")
    # Optimize for CPU usage (fp16=False) and English language
    result = model.transcribe(
        audio_path, 
        word_timestamps=True, 
        fp16=False, 
        language="en"
    )
    
    # Format to match Gemini output
    words = []
    for segment in result.get('segments', []):
        # Calculate averge confidence for the segment
        # Whisper returns logprobs, so we can use exp(avg_logprob) or just use the segment probability if available? 
        # Actually segment has no confidence score field? 
        # Wait, segments have 'avg_logprob'. Confidence ~= exp(avg_logprob)
        # But for words, newer whisper versions might have probability.
        
        # Let's check word level probability if available, else segment level.
        segment_conf = 0.0 # Placeholder if needed
        
        for w in segment.get('words', []):
            words.append({
                "word": w['word'],
                "start": w['start'],
                "end": w['end'],
                "confidence": w.get('probability', 0.9) # Whisper provides probability for words
            })
            
    return {
        "transcript": result.get('text', '').strip(),
        "words": words
    }

def transcribe_audio(audio_path: str) -> Dict[str, Any]:
    """
    Main entry point. Tries Gemini first, falls back to Whisper.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    
    # 1. Try Gemini
    try:
        logger.info("Attempting Gemini Transcription...")
        return transcribe_audio_gemini(audio_path, api_key)
    except Exception as e:
        logger.error(f"Gemini Transcription failed: {e}")
        
        # 2. Try Whisper Fallback
        if WHISPER_AVAILABLE:
            logger.info("Falling back to Whisper (Local)...")
            try:
                return transcribe_audio_whisper(audio_path)
            except Exception as we:
                logger.error(f"Whisper Transcription failed: {we}")
                raise RuntimeError(f"Both Gemini and Whisper failed. Gemini Error: {e}")
        else:
            logger.warning("Whisper not installed, skipping fallback.")
            raise e

if __name__ == "__main__":
    # Test
    pass
