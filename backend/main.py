import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

# Import Routers and Config
from routes import video_routes
from utils.storage import UPLOADS_DIR, PROCESSED_DIR

# Initialize App
app = FastAPI(
    title="Video Transcription & Clip Extraction API",
    description="API for processing videos, generating transcripts, and extracting clips with AI summaries.",
    version="1.0.0"
)

# CORS Configuration
# Allow all for development; restrict in production
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "*", # For ease of testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Directories
app.mount("/static/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/static/processed", StaticFiles(directory=PROCESSED_DIR), name="processed")

# Include Routers
app.include_router(video_routes.router)

# Global Error Handler (Optional middleware-style)
@app.middleware("http")
async def global_exception_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        # In a real app, log error ID here
        print(f"Unhandled Exception: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "Clip Extraction API is running"}
