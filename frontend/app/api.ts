import axios from 'axios';

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') + '/api';

export interface TranscriptSegment {
  text: string;
  word?: string; // Support word-level from Whisper/Gemini
  start: number;
  end: number;
  confidence?: number;
}

export interface VideoResponse {
  video_filename: string;
  video_url: string;
  transcript: TranscriptSegment[];
}

export interface ClipResponse {
  clip_url: string;
  summary: string;
}

export interface HistoryItem {
  type: string;
  source: string;
  filename: string;
  video_url: string;
  transcript_summary: string;
  created_at: string;
}



export const uploadVideo = async (
  file: File,
  onProgress?: (percent: number) => void
): Promise<VideoResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const res = await axios.post(`${API_BASE}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    }
  });
  return res.data;
};

export const extractClip = async (video_filename: string, keyword: string, timestamp: number): Promise<ClipResponse> => {
  const res = await axios.post(`${API_BASE}/extract-clip`, {
    video_filename,
    keyword,
    timestamp
  });
  return res.data;
};

export const getHistory = async (): Promise<HistoryItem[]> => {
  const res = await axios.get(`${API_BASE}/history`);
  return res.data;
};

export const deleteVideo = async (filename: string): Promise<void> => {
  await axios.delete(`${API_BASE}/video/${filename}`);
};

export const getTranscript = async (filename: string): Promise<TranscriptSegment[]> => {
  try {
    const res = await axios.get(`${API_BASE}/transcript/${filename}`);
    return res.data.transcript || [];
  } catch (error) {
    console.error("Error fetching transcript:", error);
    return [];
  }
};
