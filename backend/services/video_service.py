import os
import shutil
import subprocess
import json
import logging
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_ffmpeg():
    """Verifies that FFmpeg is installed and accessible."""
    if not shutil.which("ffmpeg"):
         raise EnvironmentError(
            "FFmpeg not found. Please install FFmpeg and add it to your PATH."
        )
    if not shutil.which("ffprobe"):
         raise EnvironmentError(
            "FFprobe not found. Please install FFmpeg (which includes ffprobe) and add it to your PATH."
        )

def get_video_duration(video_path: str) -> float:
    """Gets video duration using ffprobe."""
    check_ffmpeg()
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"Failed to get duration for {video_path}: {e}")
        raise RuntimeError(f"Could not determine video duration: {e}")

def download_youtube_video(url: str, output_dir: str) -> dict:
    """
    Downloads a YouTube video using yt-dlp with robust error handling.
    Returns a dictionary containing the file path and metadata.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Progress hook to log download status
    def progress_hook(d):
        if d['status'] == 'downloading':
            print(f"Downloading: {d.get('_percent_str')} | ETA: {d.get('_eta_str')}")
        elif d['status'] == 'finished':
            print("Download complete, processing...")

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [progress_hook],
        # Bypass YouTube bot detection
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'nocheckcertificate': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Extract Info (metadata)
            info = ydl.extract_info(url, download=True)
            
            # 2. Get Filename
            filename = ydl.prepare_filename(info)
            abs_path = os.path.abspath(filename)
            
            # 3. Return Metadata + Path
            return {
                "file_path": abs_path,
                "title": info.get('title', 'Unknown'),
                "duration": info.get('duration', 0),
                "thumbnail": info.get('thumbnail', ''),
                "author": info.get('uploader', 'Unknown')
            }

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Sign in to confirm" in error_msg or "not a bot" in error_msg:
            raise Exception(
                "YouTube is blocking automated downloads due to bot detection. "
                "Please download the video manually and upload it directly instead. "
                "Direct video upload works perfectly!"
            )
        elif "Video unavailable" in error_msg:
             raise Exception("Video is unavailable or invalid URL.")
        elif "Private video" in error_msg:
             raise Exception("Video is private.")
        else:
             raise Exception(f"YouTube Download Error: {error_msg}")
    except Exception as e:
        raise Exception(f"Unexpected Error: {str(e)}")

def extract_audio(video_path: str, output_path: str) -> str:
    """
    Extracts audio from video file to WAV format (16kHz, Mono) using FFmpeg subprocess.
    """
    check_ffmpeg()

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # 2. Build FFmpeg command
    command = [
        "ffmpeg", 
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "-y",
        output_path
    ]

    try:
        # 3. Run Command
        result = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            check=True
        )
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Audio extraction failed: {e.stderr}")
        raise RuntimeError(f"FFmpeg extraction failed: {e.stderr}")
    except Exception as e:
        logger.error(f"Unexpected audio extraction error: {e}")
        raise RuntimeError(f"Unexpected audio extraction error: {str(e)}")

def extract_clip(video_path: str, keyword_time: float, output_path: str) -> dict:
    """
    Extracts a 14s clip centered on the keyword timestamp using FFmpeg.
    Calculates boundaries, validates duration, and handles edge cases.
    Returns: {"video_clip": str, "audio_clip": str, "start_time": float, "end_time": float, "duration": float}
    """
    check_ffmpeg()
    
    if not os.path.exists(video_path):
         logger.error(f"Video file not found for extraction: {video_path}")
         raise FileNotFoundError(f"Video file not found: {video_path}")

    # 1. Get Duration & Validate
    total_duration = get_video_duration(video_path)
    if keyword_time < 0 or keyword_time > total_duration:
         raise ValueError(f"Invalid timestamp {keyword_time}. Video duration is {total_duration}s.")

    # 2. Calculate Boundaries
    start_time = max(0, keyword_time - 7)
    end_time = min(total_duration, keyword_time + 7)
    duration = end_time - start_time
    
    logger.info(f"Extracting clip: {video_path} | Time: {start_time}-{end_time} ({duration}s)")
    
    # 3. Output Paths
    video_clip_path = output_path
    base, ext = os.path.splitext(output_path)
    audio_clip_path = f"{base}.wav"
    
    try:
        # 4. Extract Video Clip (Copy Codec - Fast)
        cmd_video = [
            "ffmpeg",
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(duration),
            "-c:v", "libx264", # Re-encode video to ensure compatibility and correct cuts
            "-c:a", "aac",     # Re-encode audio
            "-y",
            video_clip_path
        ]
        
        logger.debug(f"Running FFmpeg: {' '.join(cmd_video)}")
        
        subprocess.run(
            cmd_video,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        # 5. Extract Audio Clip (WAV for AI)
        cmd_audio = [
            "ffmpeg",
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(duration),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            audio_clip_path
        ]
        
        subprocess.run(
            cmd_audio,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        logger.info(f"Clip extracted successfully: {video_clip_path}")
        
        return {
            "video_clip": video_clip_path,
            "audio_clip": audio_clip_path,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration
        }
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg extraction failed: {e.stderr}")
        raise RuntimeError(f"FFmpeg Clip Extraction Failed: {e.stderr}")
    except Exception as e:
        logger.error(f"General extraction error: {e}")
        raise RuntimeError(f"Clip Extraction Error: {str(e)}")

# Backwards compatibility
cut_video_clip = extract_clip
