import os
import logging
import assemblyai as aai
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def transcribe_audio(audio_path: str) -> Dict[str, Any]:
    """
    Transcribes audio using AssemblyAI.
    Returns structured JSON with text and word-level timestamps.
    """
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    
    if not api_key:
        raise ValueError("ASSEMBLYAI_API_KEY environment variable is missing")
    
    # Configure AssemblyAI
    aai.settings.api_key = api_key
    
    logger.info(f"Transcribing {audio_path} with AssemblyAI...")
    
    # Create transcriber
    config = aai.TranscriptionConfig(
        speech_model=aai.SpeechModel.best,
        language_code="en"
    )
    
    transcriber = aai.Transcriber(config=config)
    
    # Transcribe the audio file
    transcript = transcriber.transcribe(audio_path)
    
    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"AssemblyAI transcription failed: {transcript.error}")
    
    # Format response with word-level timestamps
    words = []
    if transcript.words:
        for word in transcript.words:
            words.append({
                "word": word.text,
                "start": word.start / 1000.0,  # Convert ms to seconds
                "end": word.end / 1000.0,
                "confidence": word.confidence
            })
    
    return {
        "transcript": transcript.text,
        "words": words
    }

if __name__ == "__main__":
    # Test
    pass
