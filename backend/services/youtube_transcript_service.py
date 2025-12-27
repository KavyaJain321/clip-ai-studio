import logging
import re
import os
import base64
import tempfile
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
        
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
            
    if re.match(r'^[0-9A-Za-z_-]{11}$', url):
        return url
        
    raise ValueError(f"Could not extract video ID from URL: {url}")

def get_cookies_file_path() -> Optional[str]:
    """
    Decodes YOUTUBE_COOKIES env var and writes to a temp file.
    Returns the path to the temp file or None.
    """
    cookies_b64 = os.getenv("YOUTUBE_COOKIES")
    if not cookies_b64:
        return None
        
    try:
        logger.info("Found YOUTUBE_COOKIES, creating temp cookie file...")
        # Decode base64 cookies
        cookies_data = base64.b64decode(cookies_b64).decode('utf-8')
        
        # Create temp file
        tf = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        tf.write(cookies_data)
        tf.close()
        return tf.name
    except Exception as e:
        logger.error(f"Failed to process YOUTUBE_COOKIES: {e}")
        return None

def get_youtube_captions(video_id: str, languages: List[str] = ['en']) -> Dict[str, Any]:
    """
    Fetches auto-generated or manual captions from YouTube.
    Supports YOUTUBE_COOKIES to bypass 429/bot detection.
    """
    cookies_file = None
    try:
        logger.info(f"Fetching YouTube captions for video: {video_id}")
        
        # 1. Setup Cookies
        cookies_file = get_cookies_file_path()
        if cookies_file:
            logger.info(f"Using cookies from: {cookies_file}")

        transcript_obj = None
        
        # 2. Fetch Transcript
        try:
            # list_transcripts supports cookies
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookies_file)
            
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
                logger.info("No transcript found in list. Trying get_transcript fallback.")
                caption_data = YouTubeTranscriptApi.get_transcript(video_id, languages=languages, cookies=cookies_file)

        except AttributeError:
             # Fallback if list_transcripts is missing
             logger.warning("list_transcripts missing. Using get_transcript.")
             caption_data = YouTubeTranscriptApi.get_transcript(video_id, languages=languages, cookies=cookies_file)
            
        # 3. Process Data
        full_text = " ".join([entry['text'] for entry in caption_data])
        
        words = []
        for entry in caption_data:
            phrase = entry['text']
            start_time = entry['start']
            duration = entry['duration']
            
            phrase = phrase.replace('\n', ' ')
            phrase_words = phrase.split()
            if not phrase_words:
                continue
            
            time_per_word = duration / len(phrase_words)
            
            for i, word in enumerate(phrase_words):
                words.append({
                    "word": word,
                    "start": round(start_time + (i * time_per_word), 2),
                    "end": round(start_time + (i * time_per_word) + time_per_word, 2)
                })
        
        logger.info(f"Successfully extracted {len(words)} words")
        
        return {
            "transcript": full_text,
            "words": words
        }
        
    except Exception as e:
        logger.error(f"Error fetching YouTube captions: {e}")
        error_str = str(e)
        if "Too Many Requests" in error_str or "429" in error_str:
            raise Exception("YouTube blocked request (429). Please update YOUTUBE_COOKIES.")
        elif "Sign in" in error_str:
             raise Exception("YouTube requires sign-in. Please update YOUTUBE_COOKIES.")
        
        raise Exception(f"Failed to fetch captions: {str(e)}")
        
    finally:
        # Cleanup temp cookie file
        if cookies_file and os.path.exists(cookies_file):
            try:
                os.unlink(cookies_file)
            except:
                pass

def get_youtube_captions_from_url(url: str, languages: List[str] = ['en']) -> Dict[str, Any]:
    """
    Convenience function to get captions directly from YouTube URL.
    """
    video_id = extract_video_id(url)
    return get_youtube_captions(video_id, languages)
