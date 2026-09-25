# Deployment Guide — StudyMind AI (Quantum Learning Workspace)

This guide describes how to deploy StudyMind AI, from a clean checkout to a
running local stack, and on to production. The project is a **polyglot
monorepo**: a React/Vite frontend, a FastAPI backend, and a set of Python
AI/ML microservices, backed by MongoDB, a ChromaDB vector store, and the Groq
LLM API.

> **Read this first if you only change one thing:** never commit a real `.env`.
> The repo's `.gitignore` already excludes it, but the secrets used for
> development must be **regenerated** for any shared or production environment
> (see [Security checklist](#security-checklist)).

---

## 1. Service topology

The system is composed of **8 services**. In development they run as separate
processes on distinct ports (see `start_servers.bat` at the repo root); in
production each can be deployed independently.

| # | Service | Team | Directory | ASGI app (module:attr) | Port |
|---|---------|------|-----------|------------------------|------|
| 1 | Frontend (React + Vite) | Pluto | `web/frontend` | — (static build) | 5173 |
| 2 | Backend API (FastAPI) | Pluto | `web/backend` | `web.backend.main:app` | 5000 |
| 3 | Chatbot RAG engine | Mu | `chatbot/rag-engine` | `main:app` | 8000 |
| 4 | Ingestion | Lambda | `ai-ml` | `ingestion.main:app` | 8001 |
| 5 | Quiz generator | Lambda | `ai-ml` | `quiz_generator.app.main:app` | 8002 |
| 6 | Weak-topic detection | Lambda | `ai-ml` | `weak_topic_detection.app.main:app` | 8003 |
| 7 | Roadmap generator | Lambda | `ai-ml` | `roadmap_generator.app.main:app` | 8004 |
| 8 | Knowledge graph | Kappa | `ai-ml` | `knowledge_graph.app.api.graph_routes:app` | 8005 |

**External dependencies** (not part of the repo):

| Dependency | Purpose | Local option | Managed option |
|------------|---------|--------------|----------------|
| MongoDB | User accounts, uploads, chat history, quiz/flashcard data | `mongod` on `:27017` | MongoDB Atlas |
| ChromaDB | Vector store for embeddings (`study_chunks` collection) | local dir `chroma_data/` | Chroma Cloud |
| Groq API | LLM for chat, flashcards, quiz generation | — | Groq Cloud (`GROQ_API_KEY`) |
| Redis *(optional)* | Chatbot cache / rate-limiting | `redis` on `:6379` | any managed Redis |

---

## 2. Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| **Python** | **3.11 or 3.12** | **Not 3.13/3.14** — `chroma-hnswlib` has no prebuilt wheel for them and the native build fails without a compiler. Verify with `python --version`. |
| **Node.js** | 18+ (20 LTS recommended) | Vite 8 + React 19 frontend |
| **Git** | any recent | Required — `chatbot/` is a **submodule** (see below) |
| **MongoDB** | 6+ | Local `mongod` or an Atlas cluster |
| **Tesseract OCR** | any | Needed by `ai-ml` (`pytesseract`) for image/scanned-PDF OCR |
| **A C build toolchain** | — | `build-essential` (Linux) / Build Tools for Visual Studio (Windows), for native wheels |

First run of any service that uses `sentence-transformers` downloads the
`all-MiniLM-L6-v2` model (~90 MB) into the HuggingFace cache. Ensure outbound
network access (or pre-seed the cache) on first boot.

---

## 3. Get the code (including the submodule)

`chatbot/` is a Git submodule pointing at
`QuantumLogicsLabs/QuantumLearningWorkspace-Chatbot`. Clone with submodules, or
initialise them after a plain clone:

```bash
# Fresh clone
git clone --recurse-submodules https://github.com/QuantumLogicsLabs/QuantumLearningWorkspace.git
cd QuantumLearningWorkspace

# Or, if you already cloned without --recurse-submodules:
git submodule update --init --recursive
```

If `chatbot/` is empty, the submodule was not initialised — the RAG service
will not start.

---

## 4. Environment variables

Configuration is **layered**. The repo-root `.env` holds shared values; each
service may override them with its own `.env`:

```
.env                         # shared: secrets, Groq, Chroma, Mongo, CORS
web/backend/.env             # backend overrides (JWT_SECRET_KEY MUST match root)
ai-ml/.env                   # ai-ml service overrides
chatbot/rag-engine/.env      # RAG engine overrides
web/frontend/.env            # Vite build-time vars (VITE_*)
```

Start from the checked-in examples:

```bash
cp .env.example .env
cp web/frontend/.env.example web/frontend/.env
```

### 4.1 Backend / services (`.env` at repo root)

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SECRET_KEY` | ✅ | Signs/verifies auth tokens. **Must be byte-identical** across the backend and the RAG engine (backend issues, RAG verifies). RAG **refuses to start** without it. |
| `INTERNAL_SERVICE_KEY` | ✅ | Shared secret for service-to-service calls. |
| `GROQ_API_KEY` | recommended | Groq LLM key. **Empty →** the code takes its documented "AI not configured" fallback instead of erroring. |
| `GROQ_MODEL` | — | LLM model id (default `openai/gpt-oss-120b`). |
| `CHROMA_DB_PATH` | ✅ | Absolute path to the local Chroma directory (`chroma_data/`). **Set explicitly** — the in-code default is a stale path and will not exist. |
| `CHROMA_API_KEY` / `CHROMA_TENANT` / `CHROMA_DATABASE` | optional | Use Chroma Cloud instead of the local dir (all three required together). |
| `EMBEDDING_MODEL_NAME` | ✅ | Must match what the store was built with (`all-MiniLM-L6-v2`). |
| `EMBEDDING_DIMENSION` | ✅ | `384` for the model above. |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | ✅ | Chunking config (`300` / `50`). Must match the store. |
| `MONGODB_URI` | recommended | Atlas/local connection string. **Empty →** in-memory fallback (works, but **all data is lost on restart** — never do this in production). |
| `MONGODB_DB_NAME` | — | Target database (default `study_mind_db`). |
| `CORS_ORIGINS` | ✅ | Comma-separated allowed origins (e.g. the frontend URL). |
| `FRONTEND_URL` | ✅ | Frontend origin, used in emails/redirects. |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | optional | Email OTP verification. For Gmail use a 16-char app password. Optional for local dev. |

### 4.2 Frontend (`web/frontend/.env`) — baked at **build** time

Vite inlines `VITE_*` variables when you run `vite build`, so these must be set
**before building** for production (not at runtime):

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend API base URL (dev `http://localhost:5000`). **No in-code fallback** — required. |
| `VITE_GRAPH_API_BASE_URL` | Knowledge-graph service base URL (dev `http://localhost:8005`). |

---

## 5. Local deployment

### 5.1 Quick start (Windows)

The repo ships `start_servers.bat` / `stop_servers.bat`, which launch all 8
services in separate terminals.

> ⚠️ Before using it, **edit the `ROOT` variable** at the top of
> `start_servers.bat` to your actual checkout path and confirm the `PYTHON`
> path points at your backend virtualenv. Then:

```bat
start_servers.bat
:: ... work ...
stop_servers.bat
```

### 5.2 Manual start (any OS)

Use **one virtualenv per area** (backend, ai-ml, chatbot) — their dependency
sets differ. Create with Python 3.11/3.12.

**Backend API — port 5000** (run from the repo root so `web.backend.*` imports resolve):

```bash
python -m venv web/backend/.venv
source web/backend/.venv/bin/activate        # Windows: web\backend\.venv\Scripts\activate
pip install -r web/backend/requirements.txt
uvicorn web.backend.main:app --host 0.0.0.0 --port 5000 --reload
```

**Chatbot RAG engine — port 8000:**

```bash
python -m venv chatbot/.venv && source chatbot/.venv/bin/activate
pip install -r chatbot/requirements.txt
cd chatbot/rag-engine
uvicorn main:app --host 0.0.0.0 --port 8000
```

**AI/ML services — ports 8001–8005** (share one venv; run from the `ai-ml` dir):

```bash
python -m venv ai-ml/.venv && source ai-ml/.venv/bin/activate
pip install -r ai-ml/requirements.txt
cd ai-ml
uvicorn ingestion.main:app                      --host 0.0.0.0 --port 8001 &
uvicorn quiz_generator.app.main:app             --host 0.0.0.0 --port 8002 &
uvicorn weak_topic_detection.app.main:app       --host 0.0.0.0 --port 8003 &
uvicorn roadmap_generator.app.main:app          --host 0.0.0.0 --port 8004 &
uvicorn knowledge_graph.app.api.graph_routes:app --host 0.0.0.0 --port 8005 &
```

**Frontend — port 5173:**

```bash
cd web/frontend
npm install
npm run dev            # dev server on http://localhost:5173
```

Open **http://localhost:5173**.

---

## 6. Production deployment

### 6.1 Frontend → Vercel (current target)

The frontend is deployed to Vercel (`quantum-learning-workspace.vercel.app` is
already in the backend's CORS allow-list).

1. Import the repo into Vercel and set the **Root Directory** to `web/frontend`.
2. Build settings: **Build Command** `npm run build`, **Output Directory** `dist` (Vite defaults).
3. Add the `VITE_API_BASE_URL` and `VITE_GRAPH_API_BASE_URL` **Environment
   Variables** pointing at your **public** backend / graph URLs (not
   `localhost`). Vite bakes them at build time, so redeploy after changing them.
4. Add the resulting Vercel domain to the backend's `CORS_ORIGINS`.

Any static host (Netlify, Cloudflare Pages, S3+CloudFront, nginx) works the
same way: `npm run build`, then serve `web/frontend/dist`.

### 6.2 Backend + AI/ML services → containers or VM

There is no single "web" Dockerfile yet, so run each Python service with a
production ASGI setup behind a reverse proxy. Recommended pattern per service:

```bash
# Example: backend, from the repo root
gunicorn web.backend.main:app \
  -k uvicorn.workers.UvicornWorker \
  --workers 2 --bind 0.0.0.0:5000
```

Guidelines:

- **Drop `--reload`** in production; size `--workers` to CPU (start with `2×cores + 1`).
- Put **nginx / Caddy / a cloud load balancer** in front for TLS termination and
  routing (`/api` → 5000, `/rag` → 8000, `/graph` → 8005, …). Only the frontend
  needs to be publicly reachable; keep internal services on a private network.
- Run each service under a process manager — **systemd**, **supervisor**, or a
  container orchestrator (Docker Compose / Kubernetes) — with auto-restart.
- Set **`CORS_ORIGINS` / `FRONTEND_URL`** to the public frontend origin.

### 6.3 Chatbot → Docker (Dockerfile provided)

The chatbot ships a production `Dockerfile` (`chatbot/Dockerfile`, Python 3.12,
exposes 8000, has a `/health` HEALTHCHECK). Build from the `chatbot/` directory:

```bash
cd chatbot
docker build -t studymind-chatbot .
docker run -d --name studymind-chatbot -p 8000:8000 \
  --env-file ../.env \
  studymind-chatbot
```

### 6.4 Managed data services

- **MongoDB Atlas** — create a cluster, allow-list your server IPs, and set
  `MONGODB_URI` + `MONGODB_DB_NAME`. The driver uses `certifi` for TLS, so no
  extra CA config is needed.
- **ChromaDB** — for a single host, ship the `chroma_data/` directory on a
  persistent volume and point `CHROMA_DB_PATH` at it. For multi-host, use
  **Chroma Cloud** (`CHROMA_API_KEY` / `CHROMA_TENANT` / `CHROMA_DATABASE`).
  The embedding model/dimension/chunking env vars **must match** what the store
  was built with, or retrieval breaks.
- **Groq** — set `GROQ_API_KEY` and `GROQ_MODEL`.

---

## 7. CI/CD

GitHub Actions run tests on push/PR (see `.github/workflows/`):

- `chatbot.yml` — checks out with `submodules: true`, Python 3.12, installs
  `chatbot/requirements.txt`, runs `pytest rag-engine/tests`. Requires the
  `JWT_SECRET_KEY` repo secret.
- `ai-ml.yml` — tests for the `ai-ml` services.

Extend these to add deploy steps (e.g. build & push the chatbot image, trigger
a Vercel deploy hook) once your hosting targets are chosen.

---

## 8. Post-deploy verification

After bringing the stack up, confirm each tier:

```bash
# Backend API is up (FastAPI serves interactive docs)
curl -f http://<backend-host>:5000/docs   >/dev/null && echo "backend OK"

# Chatbot RAG health endpoint (used by the Docker HEALTHCHECK)
curl -f http://<chatbot-host>:8000/health && echo "chatbot OK"

# Knowledge graph service
curl -f http://<graph-host>:8005/docs >/dev/null && echo "graph OK"
```

Then, end-to-end from the UI:

1. Sign up / log in (exercises JWT + MongoDB, and SMTP if OTP is enabled).
2. Upload a PDF (exercises the backend upload path + ingestion + Chroma).
3. Ask a question in the chatbot (exercises RAG retrieval + Groq).
4. Generate flashcards / a quiz (exercises Groq; with an empty `GROQ_API_KEY`
   you should see the "AI not configured" fallback, confirming graceful
   degradation).

---

## 9. Security checklist

- [ ] **Regenerate all secrets for production.** The `JWT_SECRET_KEY` and
      `INTERNAL_SERVICE_KEY` values used in development must not be reused.
      Generate fresh ones, e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- [ ] **`JWT_SECRET_KEY` is identical** in the backend and RAG-engine
      environments (mismatch → all authenticated RAG calls fail).
- [ ] **Never commit `.env`** (already git-ignored) — inject secrets via your
      host's secret manager / CI secrets, not files in the image.
- [ ] **Lock down `CORS_ORIGINS`** to your real frontend origin(s); do not ship
      `localhost` or `*` to production.
- [ ] **Expose only the frontend** publicly; keep backend, RAG, and AI/ML
      services on a private network / behind the proxy.
- [ ] **Use a real MongoDB** (`MONGODB_URI` set) — the in-memory fallback loses
      all data on restart.
- [ ] **Terminate TLS** at the proxy/CDN for every public endpoint.
- [ ] Uploaded files and `chroma_data/` live on **persistent, backed-up
      storage** (both are git-ignored).

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `chroma-hnswlib` build fails on install | Python 3.13/3.14 | Recreate the venv with Python 3.11 or 3.12. |
| `chatbot/` directory is empty | Submodule not initialised | `git submodule update --init --recursive`. |
| RAG engine won't start | Missing/blank `JWT_SECRET_KEY` | Set it (identical to the backend's). |
| Authenticated RAG calls all fail | `JWT_SECRET_KEY` differs across services | Make the two values byte-identical. |
| Frontend calls go to `undefined`/`localhost` in prod | `VITE_API_BASE_URL` not set at build | Set the `VITE_*` vars, then **rebuild** (Vite bakes them in). |
| Retrieval returns nothing / errors | `CHROMA_DB_PATH` unset or embedding config mismatch | Point at `chroma_data/`; ensure `EMBEDDING_*` / `CHUNK_*` match the store. |
| Data disappears after restart | `MONGODB_URI` empty (in-memory fallback) | Configure MongoDB. |
| Chat/quiz replies say "AI not configured" | `GROQ_API_KEY` empty | Set a valid Groq key. |
| CORS errors in the browser | Frontend origin not in `CORS_ORIGINS` | Add the exact origin and restart the backend. |

---

*Related docs: [`architecture.md`](./architecture.md) · [`api-contracts.md`](./api-contracts.md) · root [`README.md`](../README.md) · [`chatbot/rag-engine/SETUP.md`](../chatbot/rag-engine/SETUP.md)*
