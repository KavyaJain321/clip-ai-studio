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

def get_all_videos() -> List[Dict[str, Any]]:
    return load_metadata()

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

