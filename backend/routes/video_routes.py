from fastapi import APIRouter, UploadFile, File, HTTPException, Body, Depends
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import uuid

# Internal modules
from services.video_service import download_youtube_video, extract_audio, extract_clip
from services.transcription_service import transcribe_audio
from services.gemini_service import generate_summary
from utils.validators import validate_video_file, validate_youtube_url
from utils.storage import save_upload_file, get_file_path, UPLOADS_DIR, PROCESSED_DIR
from utils.metadata import save_metadata, get_all_videos

# Ensure directories exist
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

router = APIRouter(prefix="/api", tags=["Video Processing"])

@router.get("/history")
def get_history_endpoint():
    """Returns list of previously processed videos."""
    return get_all_videos()

# --- Models ---
class VideoRequest(BaseModel):
    url: str

class ClipRequest(BaseModel):
    video_filename: str
    keyword: str
    timestamp: float



# --- Endpoints ---

@router.post("/process-url")
def process_url_endpoint(request: VideoRequest):
    """
    Process a YouTube URL: download, extract audio, transcribe.
    """
    try:
        # 1. Validation
        validate_youtube_url(request.url)
        
        # 2. Download
        download_result = download_youtube_video(request.url, UPLOADS_DIR)
        video_path = download_result["file_path"]
        filename = os.path.basename(video_path)
        
        # Optional: verify video file exists
        if not os.path.exists(video_path):
             raise Exception("Download reported success but file missing.")
        
        # 3. Audio Extraction
        audio_filename = f"{os.path.splitext(filename)[0]}.wav"
        audio_path = os.path.join(UPLOADS_DIR, audio_filename)
        extract_audio(video_path, audio_path)
        
        # 4. Transcription
        try:
            transcript_data = transcribe_audio(audio_path)
            # Normalize words to match frontend expectation (text, start, end)
            raw_words = transcript_data.get("words", [])
            transcript = [
                {"text": w.get("word", ""), "start": w.get("start", 0), "end": w.get("end", 0), "confidence": w.get("confidence", 1.0)} 
                for w in raw_words
            ]
            # If "words" is empty, we might use "transcript" but UI expects array with start/end
            if not transcript:
                 # Fallback if structure is missing
                 transcript = [{"text": transcript_data.get("transcript", ""), "start": 0, "end": 0}]
        except Exception as e:
            print(f"Transcription failed (API Key issue?): {e}")
            transcript = [{"text": f"Transcription failed: {str(e)}", "start": 0, "end": 0}]
        
        # Save to History
        from utils.metadata import save_transcript
        save_transcript(filename, transcript)

        save_metadata({
            "type": "youtube",
            "source": request.url,
            "filename": filename,
            "video_url": f"/static/uploads/{filename}",
            "transcript_summary": transcript[0]["text"][:100] + "..." if transcript else "No transcript"
        })

        return {
            "video_filename": filename,
            "video_url": f"/static/uploads/{filename}",
            "transcript": transcript
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error processing URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
def upload_video_endpoint(file: UploadFile = File(...)):
    """
    Handle video file upload (max 500MB), extract audio, transcribe.
    """
    try:
        # 1. Validation
        validate_video_file(file)
        
        # 2. Save File
        file_path = save_upload_file(file)
        filename = os.path.basename(file_path)
        
        # 3. Audio Extraction
        audio_filename = f"{os.path.splitext(filename)[0]}.wav"
        audio_path = os.path.join(UPLOADS_DIR, audio_filename)
        extract_audio(file_path, audio_path)
        
        # 4. Transcription
        try:
            transcript_data = transcribe_audio(audio_path)
            # Normalize to flat structure
            raw_words = transcript_data.get("words", [])
            transcript = [
                {"text": w.get("word", ""), "start": w.get("start", 0), "end": w.get("end", 0), "confidence": w.get("confidence", 1.0)} 
                for w in raw_words
            ]
            if not transcript:
                 transcript = [{"text": transcript_data.get("transcript", ""), "start": 0, "end": 0}]
        except Exception as e:
            print(f"Transcription failed: {e}")
            transcript = [{"text": f"Transcription failed: {str(e)}", "start": 0, "end": 0}]
        
        # Save to History
        from utils.metadata import save_transcript
        save_transcript(filename, transcript)
        
        save_metadata({
            "type": "upload",
            "source": "file_upload",
            "filename": filename,
            "video_url": f"/static/uploads/{filename}",
            "transcript_summary": transcript[0]["text"][:100] + "..." if transcript else "No transcript"
        })

        return {
            "video_filename": filename,
            "video_url": f"/static/uploads/{filename}",
            "transcript": transcript
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error processing upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-clip")
def extract_clip_endpoint(request: ClipRequest):
    """
    Extract a 14s clip around the timestamp and generate a summary.
    """
    print(f"Received clip request: {request.dict()}")
    try:
        # 1. Locate Video
        safe_filename = os.path.basename(request.video_filename)
        video_path = os.path.join(UPLOADS_DIR, safe_filename)
        
        print(f"Looking for file at: {video_path}")
        if not os.path.exists(video_path):
             print("File not found.")
             raise HTTPException(status_code=404, detail=f"Video file not found: {safe_filename}")
        
        # 2. Extract Clip
        clip_filename = f"clip_{uuid.uuid4()}.mp4"
        clip_path = os.path.join(PROCESSED_DIR, clip_filename)
        
        # Returns {"video_clip": ..., "audio_clip": ..., ...}
        print(f"Extracting clip to: {clip_path}")
        extraction_result = extract_clip(video_path, request.timestamp, clip_path)
        print("Extraction complete.")
        
        # 3. Generate Summary
        # We need the transcript of the CLIP to generate a good summary.
        # Ideally we slice the main transcript, but for robustness we can just 
        # transcribe the short clip audio quickly if available.
        
        summary_data = {}
        try:
             # Fast transcription of the 14s clip
             audio_clip_path = extraction_result["audio_clip"]
             print(f"Transcribing clip audio for summary: {audio_clip_path}")
             
             # Using the robust transcription service would be better if imported, 
             # but gemini_service has a simple one too. 
             # Let's use `transcribe_audio` from transcription_service if possible, 
             # but to avoid circular deps or complexity, use the one we just ensured in gemini_service?
             # Actually `transcribe_audio` in gemini_service is now Legacy.
             # Let's use the `transcription_service.transcribe_audio` we already imported!
             
             clip_transcript_data = transcribe_audio(audio_clip_path) # Imported from transcription_service
             clip_text = clip_transcript_data.get("transcript", "")
             
             if not clip_text:
                  clip_text = "Audio content not clear."

             print(f"Clip Transcript: {clip_text}")
             
             summary_data = generate_summary(
                 clip_transcript=clip_text, 
                 keyword=request.keyword,
                 context_before="(Context not loaded from DB)", # TODO: Fetch from metadata
                 context_after="" 
             )
        except Exception as e:
             print(f"Summary generation failed: {e}")
             summary_data = {
                 "summary": "Summary unavailable.",
                 "topic": "Error",
                 "sentiment": "neutral",
                 "context": str(e)
             }

        return {
            "status": "success",
            "clip_url": f"/static/processed/{os.path.basename(extraction_result['video_clip'])}",
            "audio_url": f"/static/processed/{os.path.basename(extraction_result['audio_clip'])}",
            "start_time": extraction_result["start_time"],
            "end_time": extraction_result["end_time"],
            "duration": extraction_result["duration"],
            "summary": summary_data.get("summary"),
            "topic": summary_data.get("topic"),
            "sentiment": summary_data.get("sentiment"),
            "context": summary_data.get("context")
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error extracting clip: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-summary")
def generate_summary_endpoint(
    clip_transcript: str = Body(...), 
    keyword: str = Body(...),
    context_before: str = Body(""),
    context_after: str = Body("")
):
    """
    Direct endpoint to generate summary from text.
    """
    return generate_summary(clip_transcript, keyword, context_before, context_after)
    return generate_summary(clip_transcript, keyword, context_before, context_after)

# --- Library Management ---

@router.delete("/video/{filename}")
def delete_video_endpoint(filename: str):
    """
    Deletes a video, its transcript, and associated files.
    """
    from utils.metadata import delete_video_entry
    
    try:
        # 1. Check existence in metadata (optional but safe)
        videos = get_all_videos()
        if not any(v['filename'] == filename for v in videos):
            pass # Proceed to cleanup files anyway
        
        # 2. Delete actual files
        video_path = os.path.join(UPLOADS_DIR, filename)
        if os.path.exists(video_path):
            os.remove(video_path)
            
        audio_name = f"{os.path.splitext(filename)[0]}.wav"
        audio_path = os.path.join(UPLOADS_DIR, audio_name)
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        # 3. Remove metadata and transcript
        delete_video_entry(filename)
        
        return {"status": "success", "message": f"Deleted {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transcript/{filename}")
def get_transcript_endpoint(filename: str):
    """
    Retrieves the full transcript for a specific video.
    """
    from utils.metadata import get_transcript
    
    transcript = get_transcript(filename)
    if not transcript:
        # Try to find recent one in memory? No.
        # If no transcript file, maybe it wasn't saved with new system. 
        # Return empty or error?
        return {"transcript": []}
    
    return {"transcript": transcript}
