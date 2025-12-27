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
    """
    if not url:
        raise ValueError("URL cannot be empty")
        
    # Standard format: https://www.youtube.com/watch?v=VIDEO_ID
    # Short format: https://youtu.be/VIDEO_ID
    # Embed format: https://www.youtube.com/embed/VIDEO_ID
    # Mobile format: https://m.youtube.com/watch?v=VIDEO_ID
    
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
            
    # Fallback: check if the input itself is a video ID (11 chars)
    if re.match(r'^[0-9A-Za-z_-]{11}$', url):
        return url
        
    raise ValueError(f"Could not extract video ID from URL: {url}")

def get_youtube_captions(video_id: str, languages: List[str] = ['en']) -> Dict[str, Any]:
    """
    Fetches auto-generated or manual captions from YouTube using a robust approach.
    Handles 'list_transcripts' missing attribute error by falling back to 'get_transcript'.
    """
    try:
        logger.info(f"Fetching YouTube captions for video: {video_id}")
        
        transcript_obj = None
        
        # Method 1: Try list_transcripts (Newer API, more features)
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to find transcript in requested languages
            for lang in languages:
                try:
                    transcript_obj = transcript_list.find_transcript([lang])
                    logger.info(f"Found {lang} transcript for {video_id}")
                    break
                except NoTranscriptFound:
                    continue
            
            # If no manual transcript, try auto-generated
            if not transcript_obj:
                try:
                    transcript_obj = transcript_list.find_generated_transcript(languages)
                    logger.info(f"Using auto-generated transcript for {video_id}")
                except NoTranscriptFound:
                    logger.warning(f"No auto-generated transcript found for languages: {languages}")

            if transcript_obj:
                caption_data = transcript_obj.fetch()
            else:
                # Fallback to direct get_transcript if list_transcripts didn't yield result
                logger.info("Falling back to get_transcript method...")
                caption_data = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)

        except AttributeError:
            # Fallback for older versions or if list_transcripts is missing
            logger.warning("YouTubeTranscriptApi.list_transcripts not available. Using get_transcript fallback.")
            caption_data = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        except Exception as e:
            # Try one last resort: get_transcript direct call
            logger.warning(f"Error in list_transcripts flow: {e}. Trying direct get_transcript.")
            caption_data = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
            
        # Format into our standard structure
        full_text = " ".join([entry['text'] for entry in caption_data])
        
        words = []
        for entry in caption_data:
            phrase = entry['text']
            start_time = entry['start']
            duration = entry['duration']
            
            # Clean up text (unescape HTML entities if needed, though lib usually handles it)
            phrase = phrase.replace('\n', ' ')
            
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
        error_msg = f"Transcripts are disabled for video: {video_id}"
        logger.error(error_msg)
        raise Exception(error_msg)
    except NoTranscriptFound:
        error_msg = f"No transcript found for video {video_id} in languages: {languages}"
        logger.error(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        logger.error(f"Error fetching YouTube captions: {e}")
        raise Exception(f"Failed to fetch captions: {str(e)}")

def get_youtube_captions_from_url(url: str, languages: List[str] = ['en']) -> Dict[str, Any]:
    """
    Convenience function to get captions directly from YouTube URL.
    """
    video_id = extract_video_id(url)
    return get_youtube_captions(video_id, languages)
