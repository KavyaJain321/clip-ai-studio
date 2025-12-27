from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os
import json
import uuid

# Internal modules
from services.video_service import extract_audio, extract_clip, get_youtube_stream_urls, extract_clip_from_stream
from services.transcription_service import transcribe_audio
from services.youtube_transcript_service import extract_video_id
from services.gemini_service import generate_summary
from services.ultimate_youtube_service import UltimateYouTubeService
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
    transcript: Optional[str] = None  # Manual override

class ClipRequest(BaseModel):
    video_filename: str
    keyword: str
    timestamp: float



# --- Endpoints ---

@router.post("/process-url")
async def process_url_endpoint(request: VideoRequest):
    """
    Process a YouTube URL using streaming architecture (NO DOWNLOAD).
    Uses 4-layer robust fallback to bypass rate limits.
    """
    try:
        # 1. Validation
        validate_youtube_url(request.url)
        
        # 2. Extract video ID
        video_id = extract_video_id(request.url)
        filename = f"{video_id}.mp4"  # Virtual filename for metadata
        
        # 3. Try Ultimate Transcript Fetching
        transcript_data = None
        method_used = "unknown"
        
        print(f"Attempting to fetch transcript for {video_id} using Ultimate Service...")
        youtube_service = UltimateYouTubeService()
        
        # Pass manual transcript if provided
        result = youtube_service.get_transcript(video_id, manual_transcript=request.transcript)
        
        if result["success"]:
            # Format to match expected structure for frontend
            transcript = [
                {
                    "text": w["text"],
                    "start": w["start"],
                    "end": w["end"],
                    "confidence": 1.0
                }
                for w in result["words"]
            ]
            
            method_used = result.get("method", "unknown")
            print(f"✅ Successfully fetched transcript using {method_used.upper()}")
            transcript_data = transcript
            
        else:
            # 4. Handle Failure with Instructions
            print(f"⚠️ Ultimate transcript fetch failed. Errors: {result.get('errors')}")
            
            # Return special 400 error that triggers manual input on frontend
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Could not fetch transcript automatically.",
                    "suggestion": "Please provide the transcript manually from YouTube.",
                    "error_type": "transcript_fetch_failed",
                    "instructions": [
                        "1. Open the video on YouTube",
                        "2. Click 'Show transcript' below the video description",
                        "3. Copy all the text",
                        "4. Paste it into the 'Manual Transcript' box below and click Process again"
                    ]
                }
            )
        
        # 5. Get stream URLs for later clip extraction (NO DOWNLOAD)
        # We handle this AFTER successful transcript
        stream_info = get_youtube_stream_urls(request.url)
        
        # 6. Save metadata
        from utils.metadata import save_transcript
        save_transcript(filename, transcript_data)
        
        save_metadata({
            "type": "youtube",
            "source": request.url,
            "filename": filename,
            "video_id": video_id,
            "stream_url": stream_info["video_url"],
            "title": stream_info["title"],
            "duration": stream_info["duration"],
            "video_url": f"/youtube/{video_id}",
            "transcript_summary": transcript_data[0]["text"][:100] + "..." if transcript_data else "No transcript"
        })

        return {
            "video_filename": filename,
            "video_url": f"/youtube/{video_id}",
            "transcript": transcript_data,
            "title": stream_info.get("title", "Unknown"),
            "duration": stream_info.get("duration", 0),
            "method": method_used
        }

    except Exception as e:
        print(f"Error processing URL: {e}")
        import traceback
        traceback.print_exc()
        # Ensure we don't double-wrap HTTPException
        if isinstance(e, HTTPException): raise e
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
    Supports both uploaded videos and YouTube streams.
    """
    print(f"Received clip request: {request.dict()}")
    try:
        # 1. Check if this is a YouTube video (has stream_url in metadata)
        from utils.metadata import get_video_metadata
        metadata = get_video_metadata(request.video_filename)
        
        clip_filename = f"clip_{uuid.uuid4()}.mp4"
        clip_path = os.path.join(PROCESSED_DIR, clip_filename)
        
        # 2. Extract Clip (either from stream or local file)
        if metadata and metadata.get("stream_url"):
            # YouTube video - extract from stream
            print(f"Extracting clip from YouTube stream...")
            stream_url = metadata["stream_url"]
            extraction_result = extract_clip_from_stream(
                stream_url,
                request.timestamp,
                clip_path,
                duration=14.0
            )
            print("Stream extraction complete.")
        else:
            # Uploaded video - extract from local file
            safe_filename = os.path.basename(request.video_filename)
            video_path = os.path.join(UPLOADS_DIR, safe_filename)
            
            print(f"Looking for file at: {video_path}")
            if not os.path.exists(video_path):
                 print("File not found.")
                 raise HTTPException(status_code=404, detail=f"Video file not found: {safe_filename}")
            
            print(f"Extracting clip from local file...")
            extraction_result = extract_clip(video_path, request.timestamp, clip_path)
            print("Extraction complete.")
        
        # 3. Generate Summary
        summary_data = {}
        try:
             # Fast transcription of the 14s clip
             audio_clip_path = extraction_result["audio_clip"]
             print(f"Transcribing clip audio for summary: {audio_clip_path}")
             
             clip_transcript_data = transcribe_audio(audio_clip_path)
             clip_text = clip_transcript_data.get("transcript", "")
             
             if not clip_text:
                  clip_text = "Audio content not clear."

             print(f"Clip Transcript: {clip_text}")
             
             summary_data = generate_summary(
                 clip_transcript=clip_text, 
                 keyword=request.keyword,
                 context_before="(Context not loaded from DB)",
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
