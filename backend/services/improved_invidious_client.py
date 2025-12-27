import requests
import logging
import time
import random
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class ImprovedInvidiousClient:
    """
    Advanced Invidious client that fetches LIVE working instances
    to bypass rate limits and downtime.
    """
    
    def __init__(self):
        self.working_instances = []
        self.last_check = 0
        self.check_interval = 3600  # 1 hour
        # Fallback hardcoded list
        self.fallback_instances = [
            'https://vid.puffyan.us',
            'https://invidious.privacydev.net',
            'https://invidious.projectsegfau.lt',
            'https://inv.riverside.rocks',
            'https://invidious.drgns.space',
            'https://y.com.sb',
            'https://invidious.sethforprivacy.com',
            'https://invidious.tiekoetter.com',
            'https://inv.bp.projectsegfau.lt',
            'https://invidious.nerdvpn.de',
            'https://yewtu.be'
        ]
    
    def get_live_instances(self) -> List[str]:
        """
        Fetch currently working Invidious instances from official API
        """
        try:
            logger.info("Fetching live Invidious instances...")
            # Official Invidious instances API
            response = requests.get(
                'https://api.invidious.io/instances.json',
                timeout=5
            )
            
            if response.status_code == 200:
                instances_data = response.json()
                
                # Filter for working instances with API enabled
                working = []
                for instance in instances_data:
                    # Structure is [domain, metadata]
                    if len(instance) >= 2:
                        url = instance[1].get('uri', '')
                        api_enabled = instance[1].get('api', False)
                        type_str = instance[1].get('type', '')
                        
                        # Only use HTTPS instances with API enabled and running https
                        if url.startswith('https://') and api_enabled and type_str == 'https':
                            working.append(url)
                
                if working:
                    logger.info(f"Found {len(working)} live instances.")
                    # Return top 15 to have good variety
                    return working[:15]
        except Exception as e:
            logger.warning(f"Failed to fetch live instances: {e}")
        
        return self.fallback_instances
    
    def get_captions(self, video_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Try multiple Invidious instances with better error handling.
        Returns formatted words list or None.
        """
        # Refresh instance list if needed
        current_time = time.time()
        if not self.working_instances or (current_time - self.last_check > self.check_interval):
            self.working_instances = self.get_live_instances()
            self.last_check = current_time
        
        # Shuffle to distribute load
        instances = list(self.working_instances)
        random.shuffle(instances)
        
        # Limit retries to 5 different instances to avoid long waits
        for instance in instances[:8]:
            try:
                # Try to fetch captions list
                url = f"{instance}/api/v1/captions/{video_id}"
                
                logger.info(f"Trying Invidious: {instance}")
                response = requests.get(
                    url,
                    timeout=8,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    caption_list = data.get('captions', [])
                    
                    # Find English captions
                    target_url = None
                    for caption in caption_list:
                        label = caption.get('label', '').lower()
                        lang = caption.get('languageCode', '')
                        if 'english' in label or lang == 'en':
                            target_url = caption.get('url')
                            break
                    
                    # Fallback to first if no English (unlikely but safe)
                    if not target_url and caption_list:
                         target_url = caption_list[0].get('url')

                    if target_url:
                        if not target_url.startswith('http'):
                            target_url = instance + target_url
                        
                        # Fetch transcripts
                        # Invidious usually provides VTT or JSON if fmt specified
                        
                        # Try JSON first
                        try:
                            t_resp = requests.get(target_url + "&fmt=json", timeout=8)
                            if t_resp.status_code == 200:
                                return self.parse_json_captions(t_resp.json())
                        except:
                            pass
                            
                        # Try raw (VTT)
                        t_resp = requests.get(target_url, timeout=8)
                        if t_resp.status_code == 200:
                            # If it's VTT, we need a simple parser
                            if "WEBVTT" in t_resp.text:
                                return self.parse_vtt(t_resp.text)
            
            except Exception as e:
                # logger.debug(f"Instance {instance} failed: {e}")
                continue
        
        return None
    
    def parse_json_captions(self, data: List[Dict]) -> List[Dict]:
        words = []
        for entry in data:
            text = entry.get('content', '')
            start = float(entry.get('start', 0))
            duration = float(entry.get('duration', 0))
            
            phrase_words = text.split()
            if not phrase_words: continue
            
            time_per_word = duration / len(phrase_words)
            for i, w in enumerate(phrase_words):
                words.append({
                    "text": w,
                    "start": round(start + i*time_per_word, 2),
                    "end": round(start + (i+1)*time_per_word, 2)
                })
        return words

    def parse_vtt(self, vtt_text: str) -> List[Dict]:
        # Minimal VTT parser
        lines = vtt_text.splitlines()
        words = []
        current_start = 0.0
        current_end = 0.0
        
        # Regex for timestamp: 00:00:00.000
        # Simplification: split by -->
        for line in lines:
            if "-->" in line:
                parts = line.split("-->")
                if len(parts) == 2:
                    current_start = self._vtt_time_to_seconds(parts[0].strip())
                    current_end = self._vtt_time_to_seconds(parts[1].strip())
            elif line.strip() and not line.strip().isdigit() and "WEBVTT" not in line:
                # Text line
                text = line.strip()
                phrase_words = text.split()
                if not phrase_words: continue
                
                duration = max(0.1, current_end - current_start)
                time_per_word = duration / len(phrase_words)
                
                for i, w in enumerate(phrase_words):
                    words.append({
                        "text": w,
                        "start": round(current_start + i*time_per_word, 2),
                        "end": round(current_start + (i+1)*time_per_word, 2)
                    })
        return words

    def _vtt_time_to_seconds(self, time_str: str) -> float:
        try:
            parts = time_str.split(':')
            seconds = 0.0
            if len(parts) == 3:
                seconds += float(parts[0]) * 3600
                seconds += float(parts[1]) * 60
                seconds += float(parts[2])
            elif len(parts) == 2:
                seconds += float(parts[0]) * 60
                seconds += float(parts[1])
            return seconds
        except:
            return 0.0
