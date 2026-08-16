# 🚀 Dhanvantari AI Doctor - Cloud Deployment Guide

## 🌐 1. Instant Public Access (Active Now)

Your local Dhanvantari AI Doctor instance is currently exposed to the worldwide web via Cloudflare Secure HTTPS Tunnel:

- **Live Public URL:** [https://triple-jacket-compiled-warrior.trycloudflare.com](https://triple-jacket-compiled-warrior.trycloudflare.com)
- **Features Active:**
  - 🌌 3D Holographic AI Doctor Visualizer (Three.js WebGL)
  - 🎙️ `tarun7r/vibevoice-hindi-1.5B` & Neural Doctor Voice Synthesis
  - 📋 End-of-Visit Telehealth Prescription & PDF Generator
  - 🔬 Multimodal CXR & Medical Document Ingestion
  - 🔐 DPDP Act 2023 Consent & Audit Layer

---

## ☁️ 2. Permanent 24/7 Cloud Hosting Options

### Option A: Render.com (1-Click Free Web Service)
1. Push this repository to GitHub.
2. Go to [https://render.com](https://render.com) and click **New Web Service**.
3. Select your repository and choose **Docker** runtime (using the included `Dockerfile`).
4. In **Environment Variables**, add:
   ```env
   GROQ_API_KEY=your_groq_api_key
   OPENROUTER_API_KEY=your_openrouter_api_key
   HF_TOKEN=your_huggingface_token
   VIBEVOICE_MODEL_ID=tarun7r/vibevoice-hindi-1.5B
   ```
5. Click **Deploy Web Service**.

---

### Option B: Railway.app
1. Install Railway CLI or connect via GitHub on [railway.app](https://railway.app).
2. Run `railway up`.
3. Add environment variables in the Railway dashboard.

---

### Option C: Hugging Face Spaces (Free Cloud GPU / CPU Docker)
1. Create a new Space on [huggingface.co/spaces](https://huggingface.co/spaces) with **Docker** SDK.
2. Push this repo.
3. Configure `HF_TOKEN`, `GROQ_API_KEY`, and `OPENROUTER_API_KEY` in Space Secrets.

---

## 🐳 3. Local / Server Docker Run

```bash
# Build the container
docker build -t dhanvantari-ai-doctor .

# Run on port 8000
docker run -d -p 8000:8000 --env-file .env --name dhanvantari dhanvantari-ai-doctor
```
