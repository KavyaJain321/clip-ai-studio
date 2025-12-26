# 🚀 Deployment Guide: GitHub & Render

This guide will help you upload your ClipAI project to GitHub and deploy it on Render.

## 1. Push to GitHub

First, we need to upload your code to a repository.

1.  **Initialize Git** (if not done):
    ```bash
    git init
    git add .
    git commit -m "Initial commit"
    ```
2.  **Create a Repo**: Go to [GitHub.com/new](https://github.com/new) and create a repository (e.g., `clip-ai-studio`).
3.  **Push Code**:
    ```bash
    git remote add origin https://github.com/YOUR_USERNAME/clip-ai-studio.git
    git branch -M main
    git push -u origin main
    ```

---

## 2. Deploy Backend (Python + FFmpeg)

We will deploy the backend as a **Web Service** using Docker (to ensure FFmpeg is available).

1.  **Dashboard**: Go to [dashboard.render.com](https://dashboard.render.com).
2.  **New Resource**: Click **New +** -> **Web Service**.
3.  **Connect Repo**: Select your `clip-ai-studio` repo.
4.  **Configure**:
    *   **Name**: `clip-ai-backend`
    *   **Runtime**: **Docker** (Important! Do not select Python)
    *   **Root Directory**: `backend` (This tells Render the Dockerfile is inside the backend folder)
    *   **Region**: Closest to you (e.g., Oregon, Frankfurt).
    *   **Instance Type**: Free (or Starter).
5.  **Environment Variables**:
    *   Scroll down to "Environment Variables".
    *   Add Key: `GEMINI_API_KEY`
    *   Add Value: Paste your actual Gemini API Key from your `.env` file.
6.  **Deploy**: Click **Create Web Service**.

**Wait for it to finish.** Once live, copy the URL (e.g., `https://clip-ai-backend.onrender.com`).

---

## 3. Deploy Frontend (Next.js)

We will deploy the frontend as a separate **Web Service**.

1.  **New Resource**: Click **New +** -> **Web Service**.
2.  **Connect Repo**: Select your `clip-ai-studio` repo again.
3.  **Configure**:
    *   **Name**: `clip-ai-frontend`
    *   **Runtime**: **Node**
    *   **Root Directory**: `frontend`
    *   **Build Command**: `npm install && npm run build`
    *   **Start Command**: `npm start`
4.  **Environment Variables**:
    *   Add Key: `NEXT_PUBLIC_API_URL`
    *   Add Value: `https://clip-ai-backend.onrender.com` (The backend URL from Step 2, **with https**, no trailing slash if possible, though our code handles it).
5.  **Deploy**: Click **Create Web Service**.

---

## 🔍 Verification

1.  Open your **Frontend URL**.
2.  Upload a small video or paste a YouTube URL.
3.  Check if it processes correctly.
    *   If it fails, check the **Backend Logs** in Render Dashboard.
    *   Common issue: The backend free tier spins down after inactivity. The first request might take 50s.

## 💡 Troubleshooting

*   **CORS Issues**: If the frontend says "Network Error" immediately, check the Backend Logs. If you see CORS errors, you might need to update `backend/main.py` origins to include your new Frontend URL.
    *   *Quick Fix:* In `backend/main.py`, the `origins` list already includes `*`, so it should work anywhere.
*   **Build Failures**: Check the logs. If Frontend fails, ensure `package.json` has `next build`.
