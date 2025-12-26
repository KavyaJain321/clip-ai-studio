import os
import json
import time
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core import exceptions

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY or "your_gemini_api_key" in API_KEY:
    logger.warning("GEMINI_API_KEY not set or is placeholder.")
else:
    genai.configure(api_key=API_KEY)

def transcribe_audio(audio_path: str) -> str:
    """
    Legacy function: Uploads audio to Gemini and requests a transcription.
    (Consider moving completely to transcription_service.py)
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
    logger.info(f"Uploading {audio_path} to Gemini...")
    audio_file = genai.upload_file(path=audio_path, mime_type="audio/wav")
    
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    
    prompt = "Transcribe this audio file exactly. Return plain text."
    
    try:
        response = model.generate_content([prompt, audio_file])
        return response.text
    except Exception as e:
        logger.error(f"Legacy transcription failed: {e}")
        raise

def generate_summary(clip_transcript: str = "", keyword: str = "", context_before: str = "", context_after: str = "") -> dict:
    """
    Generates a structured summary for a video clip using Gemini.
    Retries on failure up to 3 times.
    Returns: {summary, context, topic, sentiment}
    """
    model_name = "gemini-1.5-flash"
    
    # Validation
    if not API_KEY:
        logger.error("API Key missing.")
        return _fallback_summary(clip_transcript, keyword, "API Key missing")

    prompt = f"""
   Analyze this video clip segment:
   
   CLIP TRANSCRIPT (14 seconds around keyword "{keyword}"):
   {clip_transcript}
   
   SURROUNDING CONTEXT (30 seconds before and after):
   {context_before}
   ...
   {context_after}
   
   TASK:
   1. Provide a 2-3 sentence summary of what's being discussed in this clip
   2. Explain the broader context (what topic is being covered)
   3. Identify the main subject/theme
   4. Determine the sentiment (positive/neutral/negative/informative)
   
   Return your response in this EXACT JSON format:
   {{
     "summary": "brief summary here",
     "context": "broader context explanation",
     "topic": "main topic",
     "sentiment": "positive/neutral/negative/informative"
   }}
   """

    logger.info(f"Generating summary for keyword: {keyword}")
    logger.debug(f"Prompt sent to Gemini:\n{prompt}")

    max_retries = 3
    # Confirmed available model: models/gemini-2.5-flash
    candidate_models = ["models/gemini-2.5-flash", "models/gemini-1.5-flash", "models/gemini-1.5-flash-latest", "gemini-pro"]
    
    current_model = "models/gemini-2.5-flash"
    
    # Simple fallback loop inside the retry loop or outside?
    # Better to iterate models if 404/Found error occurs.
    
    for attempt in range(max_retries):
        try:
            # Try to use the current selected model
            # On first attempt, or if we switched models
            
            logger.info(f"Attempting summary with model: {current_model}")
            model = genai.GenerativeModel(current_model)
            response = model.generate_content(prompt)
            
            logger.info("Gemini response received.")
            logger.debug(f"Raw response: {response.text}")
            
            # Parse JSON
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)
            
            return {
                "status": "success",
                "summary": data.get("summary", "No summary provided."),
                "context": data.get("context", "No context provided."),
                "topic": data.get("topic", "Unknown"),
                "sentiment": data.get("sentiment", "neutral")
            }
            
        except exceptions.NotFound as e:
            logger.warning(f"Model {current_model} not found: {e}")
            # Try next model in list if available
            if candidate_models:
                 current_model = candidate_models.pop(0)
                 logger.info(f"Switching to fallback model: {current_model}")
                 continue # Retry immediately with new model
            else:
                 return _fallback_summary(clip_transcript, keyword, "All models failed (404)")

        except exceptions.ResourceExhausted:
            logger.warning(f"Quota exceeded (Attempt {attempt+1}/{max_retries}). Retrying in 5s...")
            time.sleep(5)
        except exceptions.ServiceUnavailable:
             logger.warning(f"Service unavailable (Attempt {attempt+1}/{max_retries}). Retrying in 2s...")
             time.sleep(2)
        except json.JSONDecodeError:
             logger.error("Failed to parse Gemini JSON response.")
             return {
                 "status": "partial_success", 
                 "summary": response.text[:200], 
                 "context": "JSON Parse Error", 
                 "topic": "Unknown", 
                 "sentiment": "Unknown"
             }
        except Exception as e:
            logger.error(f"Gemini API Error (Attempt {attempt+1}/{max_retries}): {str(e)}")
            # Check if it is a 400 invalid argument which might also mean model issue
            if "not found" in str(e).lower() or "not supported" in str(e).lower():
                  if candidate_models:
                     current_model = candidate_models.pop(0)
                     logger.info(f"Switching to fallback model: {current_model}")
                     continue
            
            if attempt == max_retries - 1:
                return _fallback_summary(clip_transcript, keyword, str(e))
            time.sleep(1)

    return _fallback_summary(clip_transcript, keyword, "Max retries exceeded")

def _fallback_summary(transcript, keyword, reason):
    """Returns a basic local summary when API fails."""
    logger.warning(f"Using fallback summary. Reason: {reason}")
    summary_text = transcript if transcript else f"Clip containing '{keyword}'"
    return {
        "status": "fallback",
        "summary": f"Content discussing '{keyword}'. (Automated fallback: {reason})",
        "context": "Detailed context unavailable due to AI service interruption.",
        "topic": f"Keyword: {keyword}",
        "sentiment": "informative"
    }

# Backwards compatibility
summarize_clip_context = lambda clip_path, keyword: generate_summary(keyword=keyword).get("summary")
# Note: usage of summarize_clip_context in video_routes passed (clip_path, keyword). 
# However, the NEW requirement asks for (clip_transcript, keyword, context...). 
# Since we are REPLACING the old logic which used a file upload, 
# we need to be careful. The OLD logic uploaded the video clip. 
# The NEW logic takes TEXT input (transcripts). 
# This means video_routes.py need to change SIGNIFICANTLY to provide transcript text 
# instead of just a file path. 
# 
# Wait, the user prompt says: "Input: {clip_transcript, keyword, timestamp, full_transcript_context}"
# BUT previous video_routes.py step 458 lines 182 called:
# usage: `summary = summarize_clip_context(extraction_result["video_clip"], request.keyword)`
# 
# If I change the signature of `summarize_clip_context` or `generate_summary` to expect TEXT, 
# I MUST update `video_routes.py` to EXTRACT that text from somewhere (maybe the DB or re-transcribe the clip? 
# or just slice the original transcript?).
# 
# The user already has a full transcript for the video in `transcript_data` (in memory during processing? No, stored in metadata?).
# Actually, the `/extract-clip` endpoint DOES NOT receive the full transcript. 
# The `request` object (ClipRequest) has `video_filename`, `keyword`, `timestamp`.
# 
# To fulfill the Requirement "Input: {clip_transcript...}" I have to fetch the transcript.
# 
# Option 1: Retrieve transcript from metadata store (if available).
# Option 2: Fallback to the old method (upload clip) if transcript not available, BUT the user explicitly asked for proper template using text.
# 
# Let's adjust `summarize_clip_context` to handle the simpler case (file path) by *transcribing it* quickly 
# OR (better) updated `video_routes.py` to fetch the cached transcript.
# 
# For now, to keep `video_routes.py` happy without massive logic changes in this step,
# I will make `summarize_clip_context` a wrapper that might transcribe the clip audio briefly if text is missing,
# OR I'll assume I update `video_routes.py` in the next step to pass text.
# 
# Let's define `generate_summary` clearly as requested.
# And `summarize_clip_context` as a wrapper that expects `clip_path`? 
# No, easier: I will update `video_routes` to call `generate_summary`. 
# But where does video_routes get the transcript?
# It doesn't right now.
# 
# I'll stick to implementing `generate_summary` as requested. 
# And I'll leave `summarize_clip_context` as a deprecated wrapper that tries to use the file if possible (maybe transcribe it first?), 
# or just fails gently.
# 
# Actually, maybe the simplest way to get "clip_transcript" inside `video_routes` 
# is to assume we just transcribe the *short clip* we just made. 
# That's fast (14s). 
# 
# So:
# 1. extract_clip makes a .wav
# 2. transcribe_audio(clip.wav) -> text
# 3. generate_summary(text, ...)
# 
# That works! `gemini_service.py` has `transcribe_audio`.
# I will use that plan.

# Final check of code below.

