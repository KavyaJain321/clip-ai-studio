import requests
import logging
import os
import uuid
from typing import Optional
from services.transcription_service import transcribe_audio

logger = logging.getLogger(__name__)

def download_via_cobalt(video_id: str) -> Optional[dict]:
    """
    Download video audio using cobalt.tools API.
    This bypasses YouTube rate limits because Cobalt does the collection server-side.
    We then transcribe the audio with AssemblyAI.
    """
    temp_file = None
    try:
        logger.info(f"Trying Cobalt Tools for {video_id}...")
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Cobalt API request
        # Using a public instance or official one
        response = requests.post(
            'https://api.cobalt.tools/api/json',
            json={
                'url': url,
                'videoQuality': '720',
                'filenameStyle': 'basic',
                'downloadMode': 'audio'  # Audio only for transcription
            },
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            timeout=30
        )
        
        audio_url = None
        if response.status_code == 200:
            result = response.json()
            audio_url = result.get('url')
        
        if not audio_url:
             logger.warning(f"Cobalt returned no URL. Status: {response.status_code}, Resp: {response.text[:100]}")
             return None
             
        # Download the audio file to temp
        temp_dir = os.path.join(os.getcwd(), "temp_audio")
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, f"{uuid.uuid4()}.mp3")
        
        logger.info("Downloading Cobalt stream...")
        with requests.get(audio_url, stream=True) as r:
            r.raise_for_status()
            with open(temp_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        # Transcribe
        logger.info("Transcribing Cobalt result...")
        transcript_data = transcribe_audio(temp_file)
        
        # Format
        raw_words = transcript_data.get("words", [])
        words = []
        for w in raw_words:
             words.append({
                "text": w.get("text") or w.get("word"),
                "start": w.get("start"), # transcription_service returns seconds
                "end": w.get("end")
            })
            
        return {
            "transcript": transcript_data.get("transcript"),
            "words": words
        }

    except Exception as e:
        logger.warning(f"Cobalt download/transcribe failed: {e}")
        return None
        
    finally:
        # Cleanup
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
