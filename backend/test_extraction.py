import os
import sys
import logging
import shutil
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_ffmpeg():
    """Checks if FFmpeg is installed and accessible."""
    logger.info("Checking FFmpeg installation...")
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        logger.info(f"PASS: FFmpeg found at {ffmpeg_path}")
        # Check version (optional)
        try:
            result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            logger.info(f"FFmpeg Version:\n{result.stdout.splitlines()[0]}")
        except Exception:
            logger.warning("Could not determine FFmpeg version.")
    else:
        logger.error("FAIL: FFmpeg not found!")
        sys.exit(1)

    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path:
        logger.info(f"PASS: FFprobe found at {ffprobe_path}")
    else:
        logger.error("FAIL: FFprobe not found!")
        sys.exit(1)

def test_video_file(video_path):
    """Checks if a sample video file exists."""
    logger.info(f"Checking video file: {video_path}")
    if os.path.exists(video_path):
        logger.info("PASS: Video file exists.")
        return True
    else:
        logger.error("FAIL: Video file not found. Please place a test video at this path.")
        return False

def get_duration(video_path):
    """Tests duration extraction."""
    logger.info("Testing duration extraction...")
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        duration = float(result.stdout.strip())
        logger.info(f"PASS: Duration extracted: {duration} seconds")
        return duration
    except Exception as e:
        logger.error(f"FAIL: Duration extraction failed: {e}")
        return None

def test_extraction(video_path):
    """Tests clip extraction."""
    logger.info("Testing clip extraction...")
    
    # Define test parameters
    timestamp = 10.0
    output_path = "test_clip.mp4"
    
    # Import our actual service function (assuming we are in the root or can import)
    # Since this script is standalone, we'll try to replicate the logic or just import if in backend
    try:
        sys.path.append(os.getcwd())
        from services.video_service import extract_clip
        
        logger.info(f"Attempting to extract clip at {timestamp}s...")
        result = extract_clip(video_path, timestamp, output_path)
        
        if os.path.exists(result["video_clip"]) and os.path.exists(result["audio_clip"]):
             logger.info(f"PASS: Clip extracted successfully.\nVideo: {result['video_clip']}\nAudio: {result['audio_clip']}")
             # Cleanup
             # os.remove(result["video_clip"])
             # os.remove(result["audio_clip"])
        else:
             logger.error("FAIL: Clip files not created.")

    except ImportError:
        logger.warning("Could not import 'services.video_service'. Running standalone mock test if needed, or ensure you run this from 'backend/' folder.")
    except Exception as e:
        logger.error(f"FAIL: Extraction threw an exception: {e}")

if __name__ == "__main__":
    print("=== Extraction Verification Script ===")
    check_ffmpeg()
    
    # Use a dummy path or ask user to provide one. 
    # For automation, we'll try to find a file in uploads
    upload_dir = os.path.join("uploads")
    sample_video = None
    
    if os.path.exists(upload_dir):
        files = [f for f in os.listdir(upload_dir) if f.endswith(('.mp4', '.mkv', '.mov'))]
        if files:
            sample_video = os.path.join(upload_dir, files[0])
    
    if not sample_video:
        sample_video = "test_video.mp4" # Fallback
        
    if test_video_file(sample_video):
        get_duration(sample_video)
        test_extraction(sample_video)
    else:
        logger.warning("Skipping extraction test as no video file was found.")
