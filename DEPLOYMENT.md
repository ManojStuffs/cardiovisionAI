# CardioVision AI — Production Deployment Guide

This guide details all methods for deploying **CardioVision AI** to the cloud or exposing it externally for evaluators, presentations, and production usage.

---

## Deployment Architecture Overview

* **Frontend:** React 19 + TypeScript + Vite (compiled to static production assets in `frontend/dist`).
* **Backend:** Python Flask REST API (`backend/server.py`) serving both API endpoints (`/api/*`) and SPA assets (`/`).
* **AI Model:** Hybrid inference using Vision Transformer (`adilsaleem/ecg-image-multilabel-classification`), signal Pan-Tompkins R-peak detector, and Arrhythmia telemetry.
* **WSGI Production Server:** Gunicorn with 4 worker threads.
* **Containerized:** Multi-stage Docker build with non-root security user (`appuser`).

---

---

## Option 1: Hugging Face Spaces (Recommended Cloud Hosting)

Hugging Face Spaces is the premier platform for AI models. You can deploy CardioVision AI in two ways:

### Sub-option 1A: Gradio Space (100% Free with ZeroGPU Support)
*Best for free personal accounts — ZeroGPU is free for up to 2 Spaces!*
1. Go to [huggingface.co/new-space](https://huggingface.co/new-space).
2. Set:
   - **Space Name:** `cardiovision-afib`
   - **Space SDK:** Select **Gradio**
   - **Hardware:** Select **ZeroGPU** (`zero-a10g`) or **CPU**
   - **Visibility:** Public
3. Push your repository:
   ```bash
   git remote add space https://huggingface.co/spaces/<YOUR_HF_USERNAME>/<SPACE_NAME>
   git push space master:main
   ```
4. **Done!** Hugging Face runs `app.py` directly with interactive ECG waveform visualization, multi-condition probabilities, and MCP tool capabilities.

### Sub-option 1B: Docker Space (Full React + Flask Web App)
*Best if you have a Pro account or wish to host the complete full-stack React UI.*
1. Go to [huggingface.co/new-space](https://huggingface.co/new-space).
2. Set:
   - **Space SDK:** Select **Docker** (Blank)
   - **Visibility:** Public
3. Push code to the Space repository.
4. **Done!** Hugging Face runs the multi-stage Dockerfile containing both the compiled React 19 UI and Flask backend.

---

## Option 2: Render.com (Free Web Service)

Render allows easy container deployment directly from your GitHub repository.

### External Work for You:
1. Push your repository to **GitHub**:
   ```bash
   git push origin master
   ```
2. Log into [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** > **Web Service**.
4. Select **Build and deploy from a Git repository** and connect your GitHub repo.
5. In the configuration settings:
   - **Name:** `cardiovision-ai`
   - **Region:** Any close to you (e.g., Oregon or Frankfurt)
   - **Environment:** `Docker`
   - **Plan:** Free
6. Click **Create Web Service**.
7. Render will build the Docker container and give you a public URL (e.g., `https://cardiovision-ai.onrender.com`).

---

## Option 3: Local or VPS Deployment via Docker Compose

If you have Docker Desktop (Windows/Mac) or a Linux VPS (Ubuntu/Debian/AWS EC2/DigitalOcean):

### External Work for You:
Run a single command in your terminal:
```bash
docker compose up --build -d
```
The application will be live at:
- Local: `http://localhost:7860`
- External VPS: `http://<YOUR_VPS_PUBLIC_IP>:7860`

To stop:
```bash
docker compose down
```

---

## Option 4: Instant Public URL for External Examiner / Viva / Presentation (30 Seconds)

If you need an immediate **external public HTTPS link** to demonstrate the project to an external examiner, evaluator, or on your mobile phone without cloud deployment:

### External Work for You:
1. Double-click `run_local.bat` (or run `python backend/server.py`). The app runs at `http://localhost:5000`.
2. In a second terminal window or by double-clicking `share_public.bat`:
   - **Using LocalTunnel (No signup required):**
     ```bash
     npx localtunnel --port 5000
     ```
     *Output:* `your url is: https://funny-cardio-test.loca.lt`
   - **Or using Cloudflare Tunnel (No signup required):**
     ```bash
     cloudflared tunnel --url http://localhost:5000
     ```
   - **Or using Ngrok:**
     ```bash
     ngrok http 5000
     ```
3. Share the generated HTTPS link with your external evaluator or open it on your phone!

---

## Optional Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `7860` (Docker) / `5000` (Local) | HTTP listening port (automatically set by Render/HF) |
| `HF_TOKEN` | *None* | Optional Hugging Face API access token for cloud fallback |
| `HOST` | `0.0.0.0` | Bind host address |
