import logging
import re
from typing import Dict, Any, List, Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_video_id(url: str) -> str:
    """
    Extracts YouTube video ID from various URL formats.
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError(f"Could not extract video ID from URL: {url}")

def get_youtube_captions(video_id: str, languages: List[str] = ['en']) -> Dict[str, Any]:
    """
    Fetches auto-generated or manual captions from YouTube.
    
    Args:
        video_id: YouTube video ID
        languages: List of language codes to try (default: ['en'])
    
    Returns:
        {
            "transcript": "full text",
            "words": [{"text": "word", "start": 0.0, "end": 1.0}]
        }
    
    Raises:
        TranscriptsDisabled: If video has no captions
        NoTranscriptFound: If requested language not available
    """
    try:
        logger.info(f"Fetching YouTube captions for video: {video_id}")
        
        # Get transcript list
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to find transcript in requested languages
        transcript = None
        for lang in languages:
            try:
                transcript = transcript_list.find_transcript([lang])
                logger.info(f"Found {lang} transcript for {video_id}")
                break
            except NoTranscriptFound:
                continue
        
        # If no manual transcript, try auto-generated
        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript(languages)
                logger.info(f"Using auto-generated transcript for {video_id}")
            except NoTranscriptFound:
                raise NoTranscriptFound(f"No transcript found for languages: {languages}")
        
        # Fetch the actual transcript data
        caption_data = transcript.fetch()
        
        # Format into our standard structure
        full_text = " ".join([entry['text'] for entry in caption_data])
        
        words = []
        for entry in caption_data:
            # YouTube captions are phrase-based, not word-based
            # Split each phrase into words and estimate timestamps
            phrase = entry['text']
            start_time = entry['start']
            duration = entry['duration']
            
            # Split phrase into words
            phrase_words = phrase.split()
            if not phrase_words:
                continue
            
            # Estimate time per word
            time_per_word = duration / len(phrase_words)
            
            # Create word entries with estimated timestamps
            for i, word in enumerate(phrase_words):
                word_start = start_time + (i * time_per_word)
                word_end = word_start + time_per_word
                
                words.append({
                    "word": word,
                    "start": round(word_start, 2),
                    "end": round(word_end, 2)
                })
        
        logger.info(f"Successfully extracted {len(words)} words from captions")
        
        return {
            "transcript": full_text,
            "words": words
        }
        
    except TranscriptsDisabled:
        logger.error(f"Transcripts are disabled for video: {video_id}")
        raise
    except NoTranscriptFound as e:
        logger.error(f"No transcript found for video {video_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error fetching YouTube captions: {e}")
        raise

def get_youtube_captions_from_url(url: str, languages: List[str] = ['en']) -> Dict[str, Any]:
    """
    Convenience function to get captions directly from YouTube URL.
    
    Args:
        url: YouTube video URL
        languages: List of language codes to try
    
    Returns:
        Caption data with transcript and word-level timestamps
    """
    video_id = extract_video_id(url)
    return get_youtube_captions(video_id, languages)
