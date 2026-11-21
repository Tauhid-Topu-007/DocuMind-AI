# Deployment Guide

Production architecture:

```
Browser -> Vercel (React) -> Render (FastAPI) -> Groq API      (LLM)
                                              -> Qdrant Cloud  (vectors)
                                              -> MongoDB Atlas (metadata)
                                              -> FastEmbed     (embeddings, runs inside the backend)
```

> Your local Ollama runs on your own computer. Render **cannot** reach `localhost:11434`.
> Production must use Groq + FastEmbed + Qdrant + MongoDB Atlas.

Do the steps in this order (the backend needs the DB/vector/LLM credentials first; the frontend needs the backend URL;
the backend then needs the frontend URL for CORS).

## 1. Push to GitHub

```bash
cd DocuMind-AI
git init
git add .
git commit -m "Initial DocuMind AI implementation"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/DocuMind-AI.git
git push -u origin main
```
`.env` files are git-ignored. Never commit keys.

## 2. MongoDB Atlas

1. https://www.mongodb.com/atlas -> create a free cluster (M0).
2. **Database Access** -> add a database user (strong generated password; avoid special characters or URL-encode them).
3. **Network Access** -> Render's free tier has no fixed outbound IP, so add `0.0.0.0/0`. This is why a strong password matters.
4. **Connect -> Drivers** -> copy the URI:
   `mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`

## 3. Qdrant Cloud

1. https://cloud.qdrant.io -> create a free cluster.
2. Copy the **cluster URL** (e.g. `https://xxxx.region.cloud.qdrant.io:6333`) and create an **API key**.
3. Nothing else: the backend creates the collection (`documind_fastembed_baai_bge_small_en_v1_5`, 384 dims) on first upload.

## 4. Groq

1. https://console.groq.com -> create an API key.
2. Pick a currently supported model ID from https://console.groq.com/docs/models (don't copy an old name from a tutorial).

## 5. Deploy the backend on Render

1. https://render.com -> **New -> Web Service** -> connect the GitHub repo.
2. Settings:

| Setting | Value |
|---|---|
| Runtime | Python 3 |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

3. **Environment variables:**

```env
PYTHON_VERSION=3.12.8
APP_ENV=production
AI_PROVIDER=groq
GROQ_API_KEY=...
GROQ_MODEL=<model id from the Groq console>
EMBEDDING_PROVIDER=fastembed
FASTEMBED_MODEL=BAAI/bge-small-en-v1.5
VECTOR_DB=qdrant
QDRANT_URL=...
QDRANT_API_KEY=...
MONGODB_URI=...
DATABASE_NAME=documind
SECRET_KEY=<long random string>
ALLOWED_ORIGINS=http://localhost:5173
```
(`ALLOWED_ORIGINS` is updated again in step 7. Alternatively use the included `render.yaml` as a Blueprint: **New -> Blueprint**.)

4. Deploy, then open `https://<your-service>.onrender.com/health` -> `{"status":"ok"}`.
   Also open `/api/v1/models` (needs header `X-User-Id`, so use `/docs`) or check Groq in the app's Settings page later.

With `APP_ENV=production` the backend refuses to start without a working `MONGODB_URI`, so a bad URI shows up in the deploy logs immediately.

## 6. Deploy the frontend on Vercel

1. https://vercel.com -> **Add New -> Project** -> import the repo.
2. Framework **Vite**, **Root Directory `frontend`**, Build `npm run build`, Output `dist`.
3. Environment variable:
   `VITE_API_BASE_URL=https://<your-service>.onrender.com/api/v1`
4. Deploy. `frontend/vercel.json` already contains the SPA rewrite so `/chat/...` URLs survive a refresh.

## 7. Connect them (CORS)

In Render, set:
```env
ALLOWED_ORIGINS=https://<your-app>.vercel.app
```
(comma-separate to also keep `http://localhost:5173`; no trailing slash). Render redeploys automatically.
If you use a custom domain or Vercel preview URLs, add those origins too.

## 8. Test

1. Open the Vercel URL -> **Settings**: backend env should say `production`, Groq `configured`.
2. Upload a small text PDF -> wait for status **processed** (first upload is slower: FastEmbed downloads its model once).
3. Ask a question -> answer streams in with citations.
4. Add a public article URL -> ask about it.

## Production caveats

- **Free Render instances sleep** after inactivity: the first request can take ~30-60 s. A document being indexed when the
  instance sleeps/redeploys is marked inconsistent; use *Reprocess* (or upload again).
- **Render's disk is ephemeral.** Vectors and metadata are safe (Qdrant, Atlas), but the uploaded PDF files are lost on
  redeploy, so *Reprocess* only works for files still on disk. For permanent originals add object storage (S3/Cloudinary).
- **Memory:** the free 512 MB instance can run FastEmbed (small model) and normal PDFs; very large PDFs may need a bigger plan.
- **Embedding changes:** switching `FASTEMBED_MODEL` creates a new collection; re-index documents.
- **Not authentication:** see README. Add login before real users upload private files.
- **Costs/limits:** Groq, Qdrant and Atlas free tiers have quotas; hitting them shows as errors in chat/indexing.

## Troubleshooting

| Problem | Fix |
|---|---|
| Browser shows CORS error | `ALLOWED_ORIGINS` must exactly equal the Vercel origin (https, no trailing slash); wait for redeploy |
| Frontend says "Cannot reach the backend" | Wrong `VITE_API_BASE_URL` (must end in `/api/v1`); redeploy Vercel after changing it |
| Render deploy fails on start | Logs: usually `MONGODB_URI` missing/invalid or Atlas network access not open |
| `Groq is not configured` | Set both `GROQ_API_KEY` and `GROQ_MODEL` |
| Groq model not found / 400 | Model ID retired; choose a current one from the Groq console |
| Document stays `failed` | Hover/read the error under it: scanned PDF, encrypted PDF, or Qdrant/embedding problem |
| Vector dimension mismatch | A collection exists with another dimension; delete it in Qdrant or change embedding model name consistently and re-index |
| Website fails to ingest | JS-rendered, paywalled or bot-blocking site, or a private/internal address (blocked on purpose) |
