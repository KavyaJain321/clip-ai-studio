import os
import json
from datetime import datetime
from typing import List, Dict, Any

METADATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "metadata.json")

def load_metadata() -> List[Dict[str, Any]]:
    if not os.path.exists(METADATA_FILE):
        return []
    try:
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_metadata(entry: Dict[str, Any]):
    data = load_metadata()
    # Add timestamp if not present
    if "created_at" not in entry:
        entry["created_at"] = datetime.now().isoformat()
    
    # Prepend new entry
    data.insert(0, entry)
    
    with open(METADATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "uploads")

def get_all_videos() -> List[Dict[str, Any]]:
    """
    Returns all video metadata, filtering out files that don't exist locally
    (unless they are YouTube videos which don't have local files).
    """
    raw_data = load_metadata()
    valid_data = []
    
    for entry in raw_data:
        # Determine if it's a YouTube video
        is_youtube = entry.get("type") == "youtube" or entry.get("video_url", "").startswith("/youtube/")
        
        if is_youtube:
            # YouTube videos are valid as long as they have a video_id
            if entry.get("video_id"):
                valid_data.append(entry)
        else:
            # Local uploads must have a file that exists
            filename = entry.get("filename")
            if not filename:
                continue
                
            file_path = os.path.join(UPLOADS_DIR, filename)
            if os.path.exists(file_path):
                valid_data.append(entry)
            else:
                # Optional: We could remove it from metadata file permanently here
                # but for safety just filtering for now
                pass
                
    return valid_data

def save_transcript(filename: str, transcript: List[Dict]):
    """Saves the full transcript to a separate JSON file."""
    transcript_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "transcripts", f"{filename}.json")
    os.makedirs(os.path.dirname(transcript_path), exist_ok=True)
    try:
        with open(transcript_path, "w") as f:
            json.dump(transcript, f)
    except Exception as e:
        print(f"Error saving transcript: {e}")

def get_transcript(filename: str) -> List[Dict]:
    """Retrieves the full transcript."""
    transcript_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "transcripts", f"{filename}.json")
    if not os.path.exists(transcript_path):
        return []
    try:
        with open(transcript_path, "r") as f:
            return json.load(f)
    except Exception:
        return []

def delete_video_entry(filename: str):
    """Removes a video from metadata and deletes its transcript file."""
    entries = load_metadata()
    entries = [e for e in entries if e.get("filename") != filename]
    
    with open(METADATA_FILE, "w") as f:
        json.dump(entries, f, indent=2)
        
    # Delete transcript
    transcript_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "transcripts", f"{filename}.json")
    if os.path.exists(transcript_path):
        os.remove(transcript_path)

def get_video_metadata(filename: str) -> Dict[str, Any]:
    """Retrieves metadata for a specific video by filename."""
    entries = load_metadata()
    for entry in entries:
        if entry.get("filename") == filename:
            return entry
    return None
