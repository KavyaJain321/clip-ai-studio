import os
import shutil
from fastapi import UploadFile
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")

# Ensure dirs exist
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

def save_upload_file(file: UploadFile) -> str:
    """
    Saves an uploaded file to the uploads directory with a unique name.
    Returns the absolute path to the saved file.
    """
    try:
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOADS_DIR, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return file_path
    except Exception as e:
        raise OSError(f"Failed to save file: {str(e)}")

def get_file_path(filename: str, directory: str = "uploads") -> str:
    """
    Safe simple path joiner.
    """
    target_dir = UPLOADS_DIR if directory == "uploads" else PROCESSED_DIR
    return os.path.join(target_dir, os.path.basename(filename))
