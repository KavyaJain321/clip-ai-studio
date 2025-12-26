@echo off
echo Setting up Whisper requirements...
cd backend
venv\Scripts\python -m pip install openai-whisper torch numpy

echo.
echo Installing FFmpeg (if missing)...
where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo FFmpeg not found. Attempting install via winget...
    winget install ffmpeg
) else (
    echo FFmpeg is already installed.
)

echo.
echo Setup Complete!
pause
