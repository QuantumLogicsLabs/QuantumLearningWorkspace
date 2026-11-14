# Running StudyMind AI locally

An operational runbook for getting all 8 services up on a developer machine.
For production, container and CI topics see [DEPLOYMENT.md](DEPLOYMENT.md); for
the full environment-variable reference see its §4. This file is the shortest
path from a clean checkout to a working stack.

---

## 1. Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | **3.12** | What the project targets (see the README badge). `chromadb` and `sentence-transformers` often have no prebuilt wheels for very new releases — if `pip install` starts compiling from source, you are on too new an interpreter. |
| Node.js | 20 or 22 | Vite 8 + React 19. |
| Git | any | `chatbot/`, `web/backend/` and `web/frontend/` are each a **submodule**. |
| MongoDB | optional | Atlas, a local `mongod`, or neither — see §5. |

Check what you have:

```bash
python --version
node -v && npm -v
```

---

## 2. One-time setup

### 2.1 Get the code including the submodules

Three directories are separate repositories, wired in as submodules:

| Path | Repository |
|------|------------|
| `chatbot/` | `QuantumLearningWorkspace-Chatbot` |
| `web/backend/` | `QuantumLearningWorkspace-Backend` |
| `web/frontend/` | `QuantumLearningWorkspace-Frontend` |

A plain `git clone` leaves all three empty, which means no backend, no frontend
and no RAG service. Note that each has its **own** `.gitignore`, so a rule
added to the root `.gitignore` does not protect files inside them.

```bash
git clone --recurse-submodules https://github.com/QuantumLogicsLabs/QuantumLearningWorkspace.git
# already cloned without it:
git submodule update --init --recursive
```

### 2.2 Create the virtual environment

`start_servers.bat` looks for an interpreter in this order: `web/backend/.venv`,
then `.venv` at the repo root, then whatever `python` is on `PATH`. Create the
first one:

```powershell
py -3.12 -m venv web\backend\.venv
web\backend\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 2.3 Install dependencies

Three requirement files, one shared venv:

```powershell
pip install -r web\backend\requirements.txt
pip install -r ai-ml\requirements.txt
pip install -r chatbot\requirements.txt
cd web\frontend
npm install
cd ..\..
```

The chatbot install pulls `sentence-transformers` and its Torch dependency —
expect a few hundred MB and several minutes. The embedding model
(`all-MiniLM-L6-v2`, ~90 MB) downloads on first use rather than at install
time, so the first ingestion or chat request after a fresh setup is slow.

### 2.4 Environment files

Five `.env` files are **already present and complete** in this checkout. All
five are gitignored — never commit them.

| File | Read by | cwd that makes it load |
|------|---------|------------------------|
| `.env` | shared base: `chatbot/embedding`, the RAG engine's first layer | repo root |
| `web/backend/.env` | backend API | `web/backend` |
| `ai-ml/.env` | ingestion, quiz, weak-topic, roadmap, graph | `ai-ml` |
| `chatbot/rag-engine/.env` | RAG chat API | `chatbot/rag-engine` |
| `web/frontend/.env` | Vite (`VITE_*` only) | `web/frontend` |

> **Why the per-service files matter.** `database.py` and `auth_utils.py` call
> bare `load_dotenv()`, which resolves **relative to the working directory**,
> and `start_servers.bat` launches each service from its own directory. So the
> backend reads `web/backend/.env` — *not* the repo-root `.env`. A value set
> only at the root is invisible to it. The RAG engine is the exception: it
> explicitly layers root → `chatbot/.env` → `chatbot/rag-engine/.env`, last
> one winning.

On a fresh clone, copy the templates instead:

```bash
cp .env.example .env
cp web/backend/.env.example web/backend/.env
cp ai-ml/.env.example ai-ml/.env
cp chatbot/rag-engine/.env.example chatbot/rag-engine/.env
cp web/frontend/.env.example web/frontend/.env
```

Then generate secrets and paste **the same `JWT_SECRET_KEY`** into `.env`,
`web/backend/.env`, `ai-ml/.env` and `chatbot/rag-engine/.env` — the backend
signs tokens and the RAG engine verifies them, so a mismatch means every chat
request returns 401:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"   # JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"   # INTERNAL_SERVICE_KEY
```

Also set `CHROMA_DB_PATH` to **your** absolute path to `chroma_data/`. The
in-code default is a stale `C:\Dev\...` path that will not exist on your
machine.

---

## 3. Start everything

### Windows, all 8 services

```powershell
.\start_servers.bat
```

It kills stale `python.exe` / `node.exe` processes, then opens one terminal
window per service. `stop_servers.bat` shuts them down and frees the ports.

### Manual, any OS

Each service needs a **specific working directory** — the ASGI import paths and
the `.env` layering both depend on it. Run each in its own terminal, with the
venv activated:

| # | Service | cwd | Command |
|---|---------|-----|---------|
| 1 | Backend API | `web/backend` | `python -m uvicorn main:app --port 5000 --reload` |
| 2 | Frontend | `web/frontend` | `npm run dev` |
| 3 | RAG chat | `chatbot/rag-engine` | `python -m uvicorn main:app --port 8000` |
| 4 | Ingestion | `ai-ml` | `python -m uvicorn ingestion.main:app --port 8001` |
| 5 | Quiz generator | `ai-ml` | `python -m uvicorn quiz_generator.app.main:app --port 8002` |
| 6 | Weak-topic detection | `ai-ml` | `python -m uvicorn weak_topic_detection.app.main:app --port 8003` |
| 7 | Roadmap generator | `ai-ml` | `python -m uvicorn roadmap_generator.app.main:app --port 8004` |
| 8 | Knowledge graph | `ai-ml` | `python -m uvicorn knowledge_graph.app.api.graph_routes:app --port 8005` |

Then open **http://localhost:5173**.

### Minimum useful subset

You do not need all 8 to work on most things. Backend + frontend (1 and 2)
covers auth, upload and the dashboard. Add ingestion (4) and RAG chat (3) to
chat with a document.

---

## 4. Verify

```bash
curl http://localhost:5000/health      # backend
curl http://localhost:8000/health      # RAG chat
curl http://localhost:8002/health      # quiz
curl http://localhost:8003/health      # weak-topic
curl http://localhost:8004/health      # roadmap
curl http://localhost:8005/health      # knowledge graph
curl http://localhost:8001/            # ingestion — root, it has no /health
```

Interactive API docs: http://localhost:5000/docs

Flashcard AI wiring specifically: `curl http://localhost:5000/flashcards/ai-status`

---

## 5. What is not configured in this checkout

The stack starts and the UI works with all of the following as-is. Each is a
deliberate empty value that triggers a documented fallback, not a bug.

| Setting | Current state | Effect | To enable |
|---------|---------------|--------|-----------|
| `MONGODB_URI` | empty | `database.py` uses its in-memory fallback. Everything works, but **every user, upload and quiz result is lost when the backend restarts.** | An Atlas URI, or a local `mongod` **plus** `USE_LOCAL_MONGO=1` — without that flag `database.py` treats `mongodb://localhost:27017` as a placeholder and silently stays in memory. |
| `GROQ_API_KEY` | empty | Flashcards fall back to generic template cards; the RAG engine cannot synthesise answers. | A key from https://console.groq.com/keys, in `web/backend/.env`, `ai-ml/.env` and `chatbot/rag-engine/.env`. |
| Google / GitHub OAuth | commented out | The social buttons redirect to `?error=..._oauth_not_configured`. Email + password signup works normally. | Client id and secret in `web/backend/.env`; the redirect URIs must match what you registered with the provider exactly. |
| Chroma `study_chunks` | collection exists, **0 vectors** | Chat and quiz have nothing to retrieve until you ingest something. | Upload a PDF through the UI with the ingestion service running. |
| SMTP | configured | OTP email sends for real via Gmail. | Clear `SMTP_USER` / `SMTP_PASSWORD` to make OTPs log to the console instead. |

---

## 6. Troubleshooting

**Backend exits immediately with `RuntimeError: JWT_SECRET_KEY environment
variable is missing! Server halting.`**
`web/backend/.env` is missing, or you started uvicorn from the repo root
instead of from `web/backend`. `auth_utils.py` raises this at import time.

**Every chat request returns 401 even though login works.**
`JWT_SECRET_KEY` differs between `web/backend/.env` and
`chatbot/rag-engine/.env`. They must be byte-identical.

**Frontend requests go to `undefined/upload`.**
`VITE_API_BASE_URL` is unset — the components have no fallback for it. Vite
reads `.env` at startup, so restart `npm run dev` after editing it.

**Chroma errors, or an empty knowledge graph.**
`CHROMA_DB_PATH` is pointing at the stale default. Set it to your absolute
`chroma_data/` path in all four backend-side `.env` files.

**Ingestion or quiz retrieval fails with a Chroma Cloud authentication error.**
`ai-ml/embedding/chroma_store.py` calls `chromadb.CloudClient()`
unconditionally and ignores `CHROMA_DB_PATH` entirely, unlike the equivalent
file under `chatbot/`. Until that is fixed in code, those two services need
`CHROMA_API_KEY`, `CHROMA_TENANT` and `CHROMA_DATABASE` set. Known issue.

**A port is already in use.**
`stop_servers.bat` frees all eight. To find one holder:
`netstat -ano | findstr :5000`

**`ModuleNotFoundError: No module named 'web'`.**
You ran the backend from the wrong directory. `main.py` inserts the repo root
on `sys.path` itself, but only when launched as `main:app` from `web/backend`.

**Data disappears on every restart.**
Expected — see `MONGODB_URI` in §5.
