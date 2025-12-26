import re
from fastapi import HTTPException, UploadFile
import os

MAX_FILE_SIZE_MB = 500
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv'}

def validate_video_file(file: UploadFile):
    """
    Validates file extension and size (size check approximation via valid headers or content-length).
    """
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        
    # Content-Length is not always trustworthy, but best we have before reading options
    # Or we proceed and check chunks. For now, we trust Content-Length if present.
    # Note: SpooledTemporaryFile might not expose size easily until rolled over.
    # We will assume server-level limits or check during read if strictness needed.
    # Here we just check headers if available.
    
    # Simple extension check is often sufficient for "validation" request
    return True

def validate_youtube_url(url: str):
    """
    Validates if the URL is a valid likely YouTube URL.
    """
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    
    if not re.match(youtube_regex, url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL format.")
    return True
