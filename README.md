# DocuMind AI

AI-powered PDF & website question-answering assistant using Retrieval-Augmented Generation (RAG).
Upload PDFs, add website URLs, ask questions in natural language, get answers with real source citations.

- **Frontend:** React 18 + Vite + Tailwind CSS + Framer Motion
- **Backend:** FastAPI (Python 3.11+), PyMuPDF, Trafilatura
- **LLMs:** Ollama (local) or Groq (cloud), switchable per request
- **Embeddings:** Ollama (`mxbai-embed-large`) locally, FastEmbed (`bge-small-en-v1.5`) in the cloud
- **Vector DB:** ChromaDB (local) / Qdrant Cloud (production)
- **Metadata DB:** MongoDB Atlas (production) / JSON file (quick local dev)

## What is implemented

PDF upload (multi-file, background indexing, page-level citations) · website ingestion (SSRF-protected) ·
streaming chat with history · per-conversation sources · source filter · provider/model selector ·
document management (status, reprocess, delete) · summarize button · rate limiting · per-user data isolation.

Citations (`filename`, `page_number`, `url`, `title`) are built from **retrieved chunk metadata**, never from the LLM output.

## Quick start (local)

Prerequisites: Python 3.11+, Node 20+ (22 recommended), [Ollama](https://ollama.com/).

```bash
# 1. Models
ollama pull qwen2.5:latest
ollama pull mxbai-embed-large:latest
# lighter machines: ollama pull llama3.2:3b && ollama pull nomic-embed-text:latest
#   and set OLLAMA_CHAT_MODEL / OLLAMA_EMBED_MODEL accordingly in backend/.env

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate            # Windows PowerShell: .\venv\Scripts\Activate.ps1  | Git Bash: source venv/Scripts/activate
pip install -r requirements-local.txt
cp .env.example .env                # Windows: copy .env.example .env
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173 · API docs at http://localhost:8000/docs

With an empty `MONGODB_URI` the backend stores metadata in `backend/storage/db.json`, so MongoDB is optional locally.

Run tests: `cd backend && pytest` (no Ollama needed; embeddings and LLM are faked).

## Important notes

- **Switching embedding model = re-index.** Each embedding config uses its own vector collection
  (`documind_<provider>_<model>`). Documents indexed with one model are invisible to another; use *Reprocess*.
- **Ollama model names** are lowercase (`qwen2.5:latest`).
- **Groq:** set `GROQ_MODEL` to a current ID from the Groq console. With `GROQ_API_KEY` set, `GET /api/v1/models` lists the IDs your key can use.
- **Scanned PDFs** have no text layer; they fail with a clear message (OCR is a future improvement).
- **Identity:** the browser generates an anonymous id sent as `X-User-Id`; all data is scoped by it. This isolates
  normal users from each other but is **not authentication**. Add real auth (Phase 4) before storing sensitive documents publicly.
- Rate limiting is in-memory (per process). Use a shared store (Redis) if you scale to several instances.
- Website fetching validates DNS results and every redirect hop. A determined DNS-rebinding attacker could still race the check; for a
  high-risk public deployment, put the scraper behind an egress proxy / isolated network.

## Deployment

See **[DEPLOYMENT.md](DEPLOYMENT.md)** (Vercel + Render + MongoDB Atlas + Qdrant Cloud + Groq).

## Project structure

```
backend/app/{api/routes, core, services, database, schemas}, tests/
frontend/src/{components, pages, services, hooks, context, layouts}
render.yaml  DEPLOYMENT.md
```

## License

Choose a license before public distribution.

Author: Tauhidul Islam Topu · https://github.com/Tauhid-Topu-007
