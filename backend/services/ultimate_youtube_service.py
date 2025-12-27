import logging
import re
from typing import Dict, Any, List, Optional

# Import strategies
from services.improved_invidious_client import ImprovedInvidiousClient
from services.embed_caption_extractor import get_captions_from_embed
from services.cobalt_downloader import download_via_cobalt

logger = logging.getLogger(__name__)

class UltimateYouTubeService:
    """
    Ultimate orchestrator for fetching YouTube transcripts.
    Implements 4 layers of fallback to bypass aggressive rate limiting.
    """
    
    def __init__(self):
        self.invidious = ImprovedInvidiousClient()
        self.strategies = [
            ("Live Invidious Instances", self.try_live_invidious),
            ("YouTube Embed API", self.try_embed_api),
            ("Cobalt Tools Download", self.try_cobalt_download)
        ]
    
    def get_transcript(self, video_id: str, manual_transcript: str = None) -> Dict[str, Any]:
        """
        Try all methods until one works.
        """
        # 1. Manual User Input (Guaranteed)
        if manual_transcript:
            logger.info("Using manual transcript provided by user.")
            return {
                "success": True,
                "transcript": manual_transcript,
                "words": self._parse_manual_text(manual_transcript),
                "method": "manual_input"
            }
        
        errors = []
        
        # 2. Automated Strategies
        for strategy_name, strategy_func in self.strategies:
            try:
                logger.info(f"Trying Strategy: {strategy_name} for {video_id}...")
                result = strategy_func(video_id)
                
                if result: # result is list of words or dict
                    # Normalize result
                    if isinstance(result, list):
                        words = result
                        full_text = " ".join([w['text'] for w in words])
                    else:
                        words = result['words']
                        full_text = result['transcript']
                        
                    return {
                        "success": True,
                        "transcript": full_text,
                        "words": words,
                        "method": strategy_name
                    }
            except Exception as e:
                msg = f"{strategy_name} failed: {e}"
                logger.warning(msg)
                errors.append(msg)
        
        # 3. All Failed
        logger.error(f"All strategies failed for {video_id}. Errors: {errors}")
        return {
            "success": False,
            "errors": errors,
            "user_action_required": True,
            "message": "Could not fetch transcript automatically. Please use the manual input option."
        }
    
    def try_live_invidious(self, video_id: str):
        """Layer 1: Use improved Invidious with live instance list"""
        return self.invidious.get_captions(video_id)
    
    def try_embed_api(self, video_id: str):
        """Layer 2: Use YouTube embed player API"""
        return get_captions_from_embed(video_id)
    
    def try_cobalt_download(self, video_id: str):
        """Layer 3: Download via Cobalt.tools and transcribe"""
        return download_via_cobalt(video_id)
    
    def _parse_manual_text(self, text: str) -> List[Dict]:
        """
        Simple word splitter for manual text.
        Assigns fake timestamps since we don't have them.
        """
        words = []
        raw_words = text.split()
        if not raw_words: return []
        
        # Assume roughly 150 words per minute (2.5 words/sec)
        time_per_word = 0.4
        current_time = 0.0
        
        for w in raw_words:
            words.append({
                "text": w,
                "start": round(current_time, 2),
                "end": round(current_time + time_per_word, 2)
            })
            current_time += time_per_word
            
        return words
