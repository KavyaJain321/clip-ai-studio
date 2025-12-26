"use client";

import { useState, useRef, useEffect } from 'react';
import { processUrl, uploadVideo, extractClip, VideoResponse, ClipResponse, TranscriptSegment, getHistory, deleteVideo, getTranscript, HistoryItem } from './api';
import Link from 'next/link';
import { Upload, Link as LinkIcon, Search, Play, Scissors, Layers, LayoutGrid, Trash2, ExternalLink } from 'lucide-react';

// --- Library Component (Internal) ---
function LibraryView({ onSelect, onDelete }: { onSelect: (item: HistoryItem) => void, onDelete: () => void }) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    setLoading(true);
    getHistory()
      .then(setHistory)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleDelete = async (filename: string) => {
    if (!confirm("Are you sure you want to delete this video?")) return;
    try {
      await deleteVideo(filename);
      refresh();
      onDelete(); // Notify parent
    } catch (e) {
      alert("Failed to delete video");
    }
  }

  const API_HOST = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  if (loading) return <div className="text-center text-gray-500 py-20">Loading library...</div>;

  if (history.length === 0) return (
    <div className="text-center text-gray-500 py-20 bg-gray-900/50 rounded-2xl border border-gray-800">
      <p>No videos in library.</p>
    </div>
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-in fade-in zoom-in-95 duration-300">
      {history.map((item, idx) => (
        <div key={idx} className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden hover:border-purple-500/50 transition-all group relative">
          {/* Visuals */}
          <div className="aspect-video bg-black relative">
            <video src={`${API_HOST}${item.video_url}#t=1.0`} className="w-full h-full object-cover opacity-60" preload="metadata" />
            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all">
              <button onClick={() => onSelect(item)} className="bg-purple-600 hover:bg-purple-500 text-white rounded-full p-4 transform hover:scale-110 transition-all shadow-xl">
                <Play size={24} fill="currentColor" />
              </button>
            </div>
          </div>
          {/* Content */}
          <div className="p-4">
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-bold text-gray-200 truncate flex-1" title={item.filename}>{item.filename}</h3>
              <button onClick={() => handleDelete(item.filename)} className="text-gray-600 hover:text-red-400 p-1">
                <Trash2 size={16} />
              </button>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
              <span className={`px-2 py-0.5 rounded ${item.type === 'youtube' ? 'bg-red-900/30 text-red-400' : 'bg-blue-900/30 text-blue-400'}`}>
                {item.type.toUpperCase()}
              </span>
              <span>{new Date(item.created_at).toLocaleDateString()}</span>
            </div>
            <button
              onClick={() => onSelect(item)}
              className="w-full mt-2 bg-gray-800 hover:bg-gray-700 text-sm py-2 rounded-lg text-gray-300 flex items-center justify-center gap-2"
            >
              <ExternalLink size={14} /> Open in Studio
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}


export default function Home() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'url' | 'upload'>('url');

  // View State: 'studio' or 'library'
  const [activeView, setActiveView] = useState<'studio' | 'library'>('studio');

  // Inputs
  const [urlInput, setUrlInput] = useState('');

  // Data
  const [videoData, setVideoData] = useState<VideoResponse | null>(null);
  const [clipData, setClipData] = useState<ClipResponse | null>(null);

  // Clip state
  const [searchKeyword, setSearchKeyword] = useState('');
  const [selectedTimestamp, setSelectedTimestamp] = useState<number | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);

  // --- Actions ---

  const handleProcess = async () => {
    setLoading(true);
    setError(null);
    setVideoData(null);
    setClipData(null);
    try {
      const data = await processUrl(urlInput);
      setVideoData(data);
    } catch (err: any) {
      setError(err.message || "Failed to process video");
    } finally {
      setLoading(false);
    }
  };

  const loadFromLibrary = async (item: HistoryItem) => {
    setLoading(true);
    setActiveView('studio'); // Switch back
    // Keep existing data briefly or clear it? Better clear to show loading state if needed.
    // But we want to preserve upload state if we were uploading?
    // Wait, if I click "Open" I am *replacing* the current studio content.
    // That's fine.

    setVideoData(null);
    setClipData(null);
    setError(null);

    try {
      // Fetch full transcript
      const transcript = await getTranscript(item.filename);

      setVideoData({
        video_filename: item.filename,
        video_url: item.video_url,
        transcript: transcript
      });

    } catch (err: any) {
      setError("Failed to load video details.");
    } finally {
      setLoading(false);
    }
  };

  // Progress State
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    setLoading(true);
    setError(null);
    setVideoData(null);
    setClipData(null);
    setUploadProgress(0);
    try {
      const data = await uploadVideo(e.target.files[0], (percent) => {
        setUploadProgress(percent);
      });
      setVideoData(data);
    } catch (err: any) {
      setError(err.message || "Failed to upload video");
    } finally {
      setLoading(false);
      setUploadProgress(0);
    }
  };

  const handleSeek = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      videoRef.current.play();
      setSelectedTimestamp(time);
    }
  };

  const handleExtractClip = async () => {
    if (!videoData || !selectedTimestamp || !searchKeyword) return;
    setLoading(true);
    try {
      const data = await extractClip(videoData.video_filename, searchKeyword, selectedTimestamp);
      setClipData(data);
    } catch (err: any) {
      setError(err.message || "Failed to extract clip");
    } finally {
      setLoading(false);
    }
  };

  const API_HOST = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  return (
    <main className="min-h-screen bg-gray-950 text-white font-sans selection:bg-purple-500 selection:text-white">
      {/* Background Gradients */}
      <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-purple-600 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
        <div className="absolute top-[-10%] right-[-10%] w-96 h-96 bg-pink-600 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute bottom-[-20%] left-[20%] w-96 h-96 bg-blue-600 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto p-6">
        <header className="mb-12 text-center relative">
          <button
            onClick={() => setActiveView(activeView === 'studio' ? 'library' : 'studio')}
            className="absolute right-0 top-0 px-4 py-2 bg-gray-900/50 border border-gray-800 rounded-lg hover:bg-gray-800 transition-all text-sm text-gray-300 flex items-center gap-2"
          >
            {activeView === 'studio' ? <><LayoutGrid size={16} /> My Library</> : <><Play size={16} /> Back to Studio</>}
          </button>
          <h1 className="text-5xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-pink-600 mb-4">
            {activeView === 'library' ? 'Your Library' : 'ClipAI Studio'}
          </h1>
          <p className="text-gray-400 text-lg">Transcribe, Search, and Extract viral clips in seconds.</p>
        </header>

        {/* --- VIEW SWITCHER (Using display:none to preserve state) --- */}

        {/* STUDIO VIEW */}
        <div style={{ display: activeView === 'studio' ? 'block' : 'none' }}>

          {/* Input Section */}
          <div className="max-w-3xl mx-auto mb-16">
            <div className="bg-gray-900/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6 shadow-2xl">
              <div className="flex gap-4 mb-6 border-b border-gray-800 pb-4">
                <button
                  onClick={() => setActiveTab('url')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${activeTab === 'url' ? 'bg-purple-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'}`}
                >
                  <LinkIcon size={18} /> YouTube URL
                </button>
                <button
                  onClick={() => setActiveTab('upload')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${activeTab === 'upload' ? 'bg-purple-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'}`}
                >
                  <Upload size={18} /> Upload Video
                </button>
              </div>

              <div className="flex gap-4">
                {activeTab === 'url' ? (
                  <>
                    <input
                      type="text"
                      placeholder="Paste YouTube URL here..."
                      className="flex-1 bg-gray-950 border border-gray-800 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all text-gray-200"
                      value={urlInput}
                      onChange={(e) => setUrlInput(e.target.value)}
                    />
                    <button
                      onClick={handleProcess}
                      disabled={loading}
                      className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white px-8 py-3 rounded-xl font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-purple-500/25"
                    >
                      {loading ? 'Processing...' : 'Analyze Video'}
                    </button>
                  </>
                ) : (
                  <div className="w-full">
                    <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-700 border-dashed rounded-xl cursor-pointer bg-gray-800/50 hover:bg-gray-800 transition-all">
                      <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        <Upload className="w-10 h-10 mb-3 text-gray-400" />
                        <p className="mb-2 text-sm text-gray-400"><span className="font-semibold">Click to upload</span> or drag and drop</p>
                      </div>
                      <input type="file" className="hidden" accept="video/*" onChange={handleUpload} />
                    </label>
                  </div>
                )}
              </div>
              {loading && (
                <div className="mt-4 w-full bg-gray-800 rounded-xl p-4 border border-gray-700 animate-pulse">
                  {uploadProgress < 100 ? (
                    <>
                      <div className="flex justify-between text-xs text-gray-400 mb-2">
                        <span>Uploading Video...</span>
                        <span>{uploadProgress}%</span>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-2">
                        <div className="bg-purple-600 h-2 rounded-full transition-all duration-300" style={{ width: `${uploadProgress}%` }}></div>
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center justify-center gap-3 text-purple-300">
                      <div className="w-5 h-5 border-2 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-sm font-medium">Processing & Transcribing... (This may take a minute)</span>
                    </div>
                  )}
                </div>
              )}
              {error && <p className="mt-4 text-red-400 bg-red-900/20 p-3 rounded-lg border border-red-900/50 text-center">{error}</p>}
            </div>
          </div>

          {videoData && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
              {/* Left Column: Video & Clip Controls */}
              <div className="space-y-8">
                {/* Main Video Player */}
                <div className="bg-gray-900/50 backdrop-blur-xl border border-gray-800 rounded-2xl overflow-hidden shadow-2xl">
                  <div className="p-4 border-b border-gray-800 flex items-center justify-between">
                    <h2 className="font-bold text-gray-200 flex items-center gap-2"><Play size={20} className="text-purple-500" /> Source Video</h2>
                    <span className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded">{videoData.video_filename}</span>
                  </div>
                  <video
                    ref={videoRef}
                    src={`${API_HOST}${videoData.video_url}`}
                    controls
                    className="w-full aspect-video bg-black"
                  />
                </div>

                {/* Clip Extraction Control */}
                <div className="bg-gradient-to-br from-gray-900 via-gray-900 to-purple-900/20 backdrop-blur-xl border border-gray-700 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
                  <div className="relative z-10">
                    <h3 className="font-bold text-xl mb-4 flex items-center gap-2"><Scissors className="text-pink-500" /> Create Clip</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm text-gray-400 mb-2">Target Keyword</label>
                        <div className="relative">
                          <input
                            type="text"
                            value={searchKeyword}
                            onChange={(e) => setSearchKeyword(e.target.value)}
                            placeholder="e.g. 'artificial intelligence'"
                            className="w-full bg-gray-950/50 border border-gray-700 rounded-lg px-4 py-3 pl-10 focus:ring-2 focus:ring-pink-500 outline-none"
                          />
                          <Search className="absolute left-3 top-3.5 text-gray-500" size={18} />
                        </div>
                      </div>

                      <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                        <p className="text-sm text-gray-400 mb-1">Selected Timestamp:</p>
                        <p className="text-2xl font-mono text-purple-400">
                          {selectedTimestamp !== null ? `${selectedTimestamp.toFixed(2)}s` : '--'}
                        </p>
                        <p className="text-xs text-gray-500 mt-2">
                          Click on a transcript line to select a timestamp. The clip will include 7s before and after.
                        </p>
                      </div>

                      <button
                        onClick={handleExtractClip}
                        disabled={loading || !selectedTimestamp || !searchKeyword}
                        className="w-full bg-pink-600 hover:bg-pink-500 text-white font-bold py-3 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg shadow-pink-900/20"
                      >
                        {loading ? 'Processing...' : 'Extract Clip & Summarize'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column: Transcript & Results */}
              <div className="space-y-8">

                {/* Transcript */}
                <div className="bg-gray-900/50 backdrop-blur-xl border border-gray-800 rounded-2xl h-[600px] flex flex-col shadow-2xl">
                  <div className="p-6 border-b border-gray-800">
                    <h2 className="font-bold text-gray-200 flex items-center gap-2"><Layers size={20} className="text-blue-500" /> Transcript</h2>
                    <p className="text-sm text-gray-500">Click text to jump to video timestamp</p>
                  </div>
                  <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
                    {videoData.transcript.map((seg, idx) => (
                      <div
                        key={idx}
                        onClick={() => handleSeek(seg.start)}
                        className={`p-4 rounded-xl cursor-pointer transition-all border ${selectedTimestamp === seg.start
                          ? 'bg-purple-900/30 border-purple-500/50'
                          : 'bg-gray-800/30 border-gray-800 hover:bg-gray-800 hover:border-gray-700'
                          }`}
                      >
                        <div className="flex justify-between text-xs text-gray-500 mb-1 font-mono">
                          <span>{seg.start.toFixed(1)}s</span>
                          <span>{seg.end.toFixed(1)}s</span>
                        </div>
                        <p className="text-gray-300 leading-relaxed">
                          {searchKeyword && seg.text.toLowerCase().includes(searchKeyword.toLowerCase()) ? (
                            <span className="bg-yellow-500/20 text-yellow-200 px-1 rounded">
                              {seg.text}
                            </span>
                          ) : (
                            seg.text
                          )}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Generated Clip Result */}
                {clipData && (
                  <div className="bg-gray-900/80 backdrop-blur-xl border border-green-900/30 rounded-2xl p-6 shadow-2xl ring-1 ring-green-500/50 animate-in zoom-in-95 duration-300">
                    <h3 className="font-bold text-green-400 mb-4 flex items-center gap-2">✨ Generated Clip</h3>
                    <video
                      src={`${API_HOST}${clipData.clip_url}`}
                      controls
                      className="w-full rounded-lg mb-4 bg-black border border-gray-800"
                    />
                    <div className="bg-gray-800/50 p-4 rounded-xl border border-gray-700">
                      <p className="text-xs text-green-400 font-bold mb-1 uppercase tracking-wider">AI Summary</p>
                      <p className="text-gray-300">{clipData.summary}</p>
                    </div>
                  </div>
                )}

              </div>
            </div>
          )}
        </div>

        {/* LIBRARY VIEW */}
        <div style={{ display: activeView === 'library' ? 'block' : 'none' }}>
          <LibraryView
            onSelect={loadFromLibrary}
            onDelete={() => {
              // Optional: clear current data if deleted
              setVideoData(null);
            }}
          />
        </div>

      </div>
    </main>
  );
}
