import requests
import logging
import re
import json
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

def get_captions_from_embed(video_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    Extract captions using YouTube embed player API.
    This endpoint is often less rate-limited than the main watch page or API.
    """
    try:
        logger.info(f"Trying Embed API for {video_id}...")
        
        # Get video page as embed
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # Increased timeout for reliability
        response = requests.get(embed_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            html = response.text
            
            # Find captionTracks in the embed page configuration
            # Format: "captionTracks": [...]
            pattern = r'"captionTracks":\s*(\[.*?\])'
            match = re.search(pattern, html)
            
            if match:
                try:
                    caption_tracks = json.loads(match.group(1))
                    
                    # Find English track
                    target_url = None
                    for track in caption_tracks:
                        lang = track.get('languageCode', '')
                        # Some tracks have 'name': {'simpleText': 'English'}
                        name = track.get('name', {}).get('simpleText', '').lower()
                        
                        if lang == 'en' or 'english' in name:
                            target_url = track.get('baseUrl')
                            break
                    
                    # Fallback to first available
                    if not target_url and caption_tracks:
                         target_url = caption_tracks[0].get('baseUrl')
                         
                    if target_url:
                        # Fetch the actual captions (usually XML format from baseUrl)
                        # We specifically want JSON format to simplify parsing
                        json_url = f"{target_url}&fmt=json3"
                        
                        caption_response = requests.get(json_url, timeout=10)
                        
                        if caption_response.status_code == 200:
                            return parse_youtube_json3(caption_response.json())
                except Exception as e:
                    logger.warning(f"Failed to parse embed captions: {e}")
        
    except Exception as e:
        logger.warning(f"Embed API failed: {e}")
        
    return None

def parse_youtube_json3(data: Dict) -> List[Dict]:
    """
    Parse YouTube's internal JSON3 caption format.
    """
    words = []
    events = data.get('events', [])
    
    for event in events:
        # Each event can have multiple segments
        start_ms = event.get('tStartMs', 0)
        duration_ms = event.get('dDurationMs', 0)
        segs = event.get('segs', [])
        
        # Combine segments into full text or keep separate?
        # Standard YouTube format is phrase-based.
        # JSON3 usually has segments for words if available, or just one segment.
        
        current_time = start_ms / 1000.0
        
        full_text = "".join([s.get('utf8', '') for s in segs])
        full_text = full_text.strip()
        
        if not full_text or full_text == '\n':
            continue

        # If we have strict word segmentation in segments:
        # Check if segments look like words (short, no spaces)
        # But usually simpler to just re-split the full phrase to be consistent
        # with other parsers.
        
        phrase_words = full_text.split()
        if not phrase_words: continue
        
        duration = duration_ms / 1000.0
        time_per_word = duration / len(phrase_words)
        
        for i, w in enumerate(phrase_words):
             words.append({
                "text": w,
                "start": round(current_time + i*time_per_word, 2),
                "end": round(current_time + (i+1)*time_per_word, 2)
            })
            
    return words
