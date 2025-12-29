from fastapi import APIRouter, UploadFile, File, HTTPException, Body, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os
import json
import uuid

# Internal modules
from services.video_service import extract_audio, extract_clip
from services.transcription_service import transcribe_audio
from services.gemini_service import generate_summary
from utils.validators import validate_video_file
from utils.storage import save_upload_file, get_file_path, UPLOADS_DIR, PROCESSED_DIR
from utils.storage import save_upload_file, get_file_path, UPLOADS_DIR, PROCESSED_DIR

# Ensure directories exist
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

router = APIRouter(prefix="/api", tags=["Video Processing"])



# --- Models ---


class ClipRequest(BaseModel):
    video_filename: str
    keyword: str
    timestamp: float



# --- Endpoints ---



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
        # 2. Extract Clip (local file only)
        safe_filename = os.path.basename(request.video_filename)
        video_path = os.path.join(UPLOADS_DIR, safe_filename)
        
        print(f"Looking for file at: {video_path}")
        if not os.path.exists(video_path):
                print("File not found.")
                raise HTTPException(status_code=404, detail=f"Video file not found: {safe_filename}")
        
        clip_filename = f"clip_{uuid.uuid4()}.mp4"
        clip_path = os.path.join(PROCESSED_DIR, clip_filename)
        
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


