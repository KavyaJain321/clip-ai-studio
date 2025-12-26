"use client";

import { useEffect, useState } from 'react';
import { getHistory, HistoryItem } from '../api';
import { Play, FileVideo, Calendar } from 'lucide-react';
import Link from 'next/link';

export default function LibraryPage() {
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getHistory()
            .then(setHistory)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    const API_HOST = "http://localhost:8000";

    return (
        <main className="min-h-screen bg-gray-950 text-white font-sans selection:bg-purple-500 selection:text-white p-6">
            <div className="max-w-7xl mx-auto">
                <header className="mb-12 flex justify-between items-center">
                    <div>
                        <h1 className="text-4xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-pink-600 mb-2">
                            Your Library
                        </h1>
                        <p className="text-gray-400">Manage your previous uploads and generations.</p>
                    </div>
                    <Link href="/" className="px-6 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-white transition-all">
                        ← Back to Studio
                    </Link>
                </header>

                {loading ? (
                    <div className="text-center text-gray-500 py-20">Loading history...</div>
                ) : history.length === 0 ? (
                    <div className="text-center text-gray-500 py-20 bg-gray-900/50 rounded-2xl border border-gray-800">
                        <FileVideo size={48} className="mx-auto mb-4 opacity-50" />
                        <p>No videos found. Go upload some content!</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {history.map((item, idx) => (
                            <div key={idx} className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden hover:border-purple-500/50 transition-all group">
                                <div className="aspect-video bg-black relative">
                                    <video src={`${API_HOST}${item.video_url}`} className="w-full h-full object-cover opacity-60 group-hover:opacity-100 transition-all" />
                                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all">
                                        <Play className="text-white drop-shadow-lg" size={48} fill="currentColor" />
                                    </div>
                                </div>
                                <div className="p-4">
                                    <h3 className="font-bold text-gray-200 truncate mb-1" title={item.filename}>{item.filename}</h3>
                                    <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
                                        <span className={`px-2 py-0.5 rounded ${item.type === 'youtube' ? 'bg-red-900/30 text-red-400' : 'bg-blue-900/30 text-blue-400'}`}>
                                            {item.type.toUpperCase()}
                                        </span>
                                        <span className="flex items-center gap-1"><Calendar size={12} /> {new Date(item.created_at).toLocaleDateString()}</span>
                                    </div>
                                    <p className="text-sm text-gray-400 line-clamp-2">
                                        {item.transcript_summary || "No transcript available."}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </main>
    );
}
