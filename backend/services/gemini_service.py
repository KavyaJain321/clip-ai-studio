import os
import json
import logging
from dotenv import load_dotenv

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def generate_summary(clip_transcript: str = "", keyword: str = "", context_before: str = "", context_after: str = "") -> dict:
    """
    Generates a structured summary for a video clip.
    Uses a simple rule-based approach since we removed Gemini.
    For production, you could integrate OpenAI, Anthropic, or AssemblyAI's LeMUR.
    
    Returns: {summary, context, topic, sentiment}
    """
    logger.info(f"Generating summary for keyword: {keyword}")
    
    # Simple rule-based summary (fallback)
    if not clip_transcript:
        clip_transcript = f"Clip containing '{keyword}'"
    
    # Extract a brief summary (first 150 chars of transcript)
    brief_summary = clip_transcript[:150] + "..." if len(clip_transcript) > 150 else clip_transcript
    
    # Build context from surrounding text
    context_text = ""
    if context_before:
        context_text += f"Before: {context_before[:100]}... "
    if context_after:
        context_text += f"After: {context_after[:100]}..."
    
    if not context_text:
        context_text = "No additional context available."
    
    # Determine sentiment based on simple keyword matching
    sentiment = "informative"  # Default
    positive_words = ["great", "awesome", "excellent", "good", "love", "amazing"]
    negative_words = ["bad", "terrible", "awful", "hate", "poor", "worst"]
    
    transcript_lower = clip_transcript.lower()
    if any(word in transcript_lower for word in positive_words):
        sentiment = "positive"
    elif any(word in transcript_lower for word in negative_words):
        sentiment = "negative"
    
    return {
        "status": "success",
        "summary": f"Discussion about '{keyword}': {brief_summary}",
        "context": context_text,
        "topic": keyword,
        "sentiment": sentiment
    }

def _fallback_summary(transcript, keyword, reason):
    """Returns a basic local summary when API fails."""
    logger.warning(f"Using fallback summary. Reason: {reason}")
    summary_text = transcript if transcript else f"Clip containing '{keyword}'"
    return {
        "status": "fallback",
        "summary": f"Content discussing '{keyword}'. (Automated fallback: {reason})",
        "context": "Detailed context unavailable.",
        "topic": f"Keyword: {keyword}",
        "sentiment": "informative"
    }

# Backwards compatibility
summarize_clip_context = lambda clip_path, keyword: generate_summary(keyword=keyword).get("summary")
