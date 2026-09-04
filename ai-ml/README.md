# StudyMind AI — Ingestion, Embedding & Quiz Generator Pipeline

StudyMind AI is a Retrieval-Augmented Generation (RAG) pipeline that turns raw content (YouTube videos, web articles, PDFs) into searchable knowledge — and then uses that knowledge to generate structured, factual quizzes.

The system is made up of **three modules** that work together:

| Module | Role |
|---|---|
| **Ingestion** | FastAPI server that receives and processes raw content (PDFs, articles, YouTube) |
| **Embedding** | Chunks text, generates embeddings, and stores them in MongoDB + Pinecone |
| **Quiz Generator** | Retrieves stored content via vector search and generates JSON quizzes using an LLM (Groq) |

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [1. Installation](#1-installation)
- [2. Environment Setup](#2-environment-setup)
- [3. Running Ingestion & Embedding](#3-running-ingestion--embedding)
- [4. Running the Quiz Generator](#4-running-the-quiz-generator)
- [5. Quiz JSON Output Schemas](#5-quiz-json-output-schemas)
- [6. Unit Testing](#6-unit-testing)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Technologies](#technologies)

---

## Architecture Overview

Data flows through the pipeline in two stages:

**Stage 1 — Ingest & Embed:**
`Source (YouTube / Article / PDF) → Ingestion Server → Chunking → Embedding → MongoDB + Pinecone`

**Stage 2 — Generate Quiz (RAG):**
`Topic Query → Pinecone Vector Search → MongoDB Chunk Retrieval → Groq LLM → Structured JSON Quiz`

The quiz generator doesn't guess answers — it retrieves the exact relevant chunks from your ingested content first, then asks the LLM to build questions strictly from that context.

---

## Prerequisites

Before starting, make sure you have:

- Python 3.9+ installed
- A [MongoDB Atlas](https://www.mongodb.com/atlas) cluster (or local MongoDB instance)
- A [Pinecone](https://www.pinecone.io/) account with an index created
- A [Groq](https://console.groq.com/) account and API key (for quiz generation)
- Content already ingested and embedded before attempting to generate quizzes

---

## 1. Installation

Open your terminal and navigate to the project root:

```bash
cd ai-ml
```

**Create and activate a virtual environment** (recommended):

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

---

## 2. Environment Setup

> **⚠️ Important: Never commit real API keys or credentials to GitHub.**
> This project uses a `.env.example` template in the root `ai-ml` folder — copy it locally and fill in your own secrets. All modules (ingestion, embedding, quiz_generator) read from this single `.env` file.

1. Locate the template file at `.env.example`.
2. Copy it and rename the copy to `.env`:

   ```bash
   cp .env.example .env
   ```

3. Open `.env` and fill in your own values:

   | Variable | Description |
   |---|---|
   | `MONGODB_URI` | Your MongoDB Atlas connection string |
   | `MONGODB_DB` | Database name (default: `studymind`) |
   | `MONGODB_COLLECTION` | Collection name for storing chunks (default: `chunks`) |
   | `PINECONE_API_KEY` | Your Pinecone API key |
   | `PINECONE_INDEX_NAME` | Name of your Pinecone index |
   | `PINECONE_CLOUD` | Pinecone cloud provider (default: `aws`) |
   | `PINECONE_REGION` | Pinecone region (default: `us-east-1`) |
   | `EMBEDDING_MODEL_NAME` | Local embedding model (default: `all-MiniLM-L6-v2`) |
   | `EMBEDDING_DIMENSION` | Embedding vector size (default: `384`) |
   | `CHUNK_SIZE` | Max characters/tokens per chunk (default: `300`) |
   | `CHUNK_OVERLAP` | Overlap between chunks (default: `50`) |
   | `GROQ_API_KEY` | Your Groq API key (used by the quiz generator) |
   | `GROQ_MODEL` | Groq model name (default: `llama-3.3-70b-versatile`) |

4. Double-check `.env` is listed in `.gitignore` so it's never accidentally pushed:

   ```gitignore
   .env
   ```

### `.env.example`

```dotenv
# MongoDB
MONGODB_URI=your-mongodb-connection-string
MONGODB_DB=studymind
MONGODB_COLLECTION=chunks

# Pinecone
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=studymind-embeddings
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# HF_TOKEN (Hugging Face token)
HF_TOKEN = hugging face API key (Token Access)
# Embedding model (local, free — no key needed)
EMBEDDING_DIMENSION=384

# Chunking
CHUNK_SIZE=300
CHUNK_OVERLAP=50

# Groq (Quiz Generator LLM)
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.3-70b-versatile
```

---

## 3. Running Ingestion & Embedding

Because ingestion and embedding are independent services, you'll need **two separate terminals** running at the same time.

### Terminal 1 — Start the Ingestion Server

```bash
cd ai-ml
python -m uvicorn ingestion.main:app --reload
```

> **Note:** You must use the `python -m` prefix for this to work correctly.

Wait until you see `Application startup complete`, then leave this terminal running.

- Server URL: `http://127.0.0.1:8000`
- Interactive API docs (Swagger UI): `http://127.0.0.1:8000/docs`

### Terminal 2 — Run the Embedding Module

Open a **second terminal**, and make sure you're also in the `ai-ml` folder:

```bash
cd ai-ml
```

With Terminal 1 still running, run the embedder against your desired source type:

**YouTube video:**
```bash
python -m embedding.embedder --youtube "https://youtube.com/watch?v=VIDEO_ID"
```

**Web article:**
```bash
python -m embedding.embedder --article "https://example.com/some-article"
```

**PDF file:**
```bash
python -m embedding.embedder --pdf "C:\path\to\file.pdf"
```

**Quick sanity check** (no external input, uses a hardcoded sample):
```bash
python -m embedding.embedder
```

Once this step is complete, your content is chunked, embedded, and stored in MongoDB + Pinecone — ready for quiz generation.

---

## 4. Running the Quiz Generator

The **AI Quiz Generator** is a Retrieval-Augmented module that searches your ingested content (via Pinecone + MongoDB) to generate accurate, structured quizzes — instead of relying on the LLM to guess facts.

### Key Features

- **Renamed Package:** `quiz_generator` (formerly `quiz-generator`) for full Python module compatibility.
- **Vector Store Linking:** Fully integrated with the `embedding` module to pull context from ingested PDFs, YouTube videos, and articles.
- **Strict JSON Output:** Uses Groq's `json_object` mode to guarantee valid JSON arrays, ready for immediate use in web/mobile apps.
- **Deep Context Retrieval:** Combines multiple relevant text chunks to ensure high-quality question coverage.

### Running the RAG Quiz System

Make sure content has already been ingested and embedded (see [Section 3](#3-running-ingestion--embedding)), then run the interactive CLI from the **root `ai-ml` folder**:

```bash
# Ensure Python can see the modules
$env:PYTHONPATH = "."      # PowerShell (Windows)
# export PYTHONPATH="."    # macOS / Linux

# Run the interactive CLI
python run_quiz.py
```

### Example Workflow

1. Enter Topic: `Artificial Intelligence`
2. Enter Type: `mcq`
3. Result: The system searches your stored PDFs/videos for "Artificial Intelligence" and generates a JSON quiz.

---

## 5. Quiz JSON Output Schemas

Every generator returns a clean list of JSON objects.

### Multiple Choice (MCQ)
```json
[
  {
    "question": "What is the capital of France?",
    "options": ["London", "Berlin", "Paris", "Madrid"],
    "answer": "Paris"
  }
]
```

### True/False
```json
[
  {
    "question": "The Earth is flat.",
    "answer": "False"
  }
]
```

---

## 6. Unit Testing

To test the quiz generators in isolation (without the database), run the updated unit tests from the **root `ai-ml` folder**:

```bash
python -m quiz_generator.tests.test_mcq_generator
python -m quiz_generator.tests.test_fill_blank_generator
```

---

## Project Structure

```
ai-ml/
├── ingestion/
│   ├── main.py                    # FastAPI ingestion server
│   └── ...
├── embedding/
│   ├── embedder.py                # Embedding module (CLI entry point)
│   └── requirements.txt
├── quiz_generator/
│   ├── app/
│   │   ├── generators/            # AI logic with strict JSON prompts
│   │   │   ├── base_generator.py
│   │   │   ├── mcq_generator.py
│   │   │   ├── true_false_generator.py
│   │   │   ├── fill_blank_generator.py
│   │   │   └── short_answer_generator.py
│   │   ├── services/
│   │   │   └── quiz_service.py    # Bridge: Searches Vectors -> Fetches Mongo -> Calls AI
│   │   └── config.py              # Loads .env from root and manages Groq settings
│   └── tests/                     # Unit tests for individual generators
├── run_quiz.py                    # Interactive CLI entry point for quiz generation
├── .env.example                   # Environment variable template
├── .env                           # Your local secrets (gitignored)
├── requirements.txt
└── README.md
```

---

## Troubleshooting

| Issue | Likely Cause / Fix |
|---|---|
| `uvicorn: command not found` | Forgot the `python -m` prefix, or dependencies not installed |
| Connection refused on `127.0.0.1:8000` | Terminal 1 (ingestion server) isn't running |
| Pinecone auth errors | Check `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `PINECONE_CLOUD`, and `PINECONE_REGION` in your `.env` |
| MongoDB connection timeout | Check `MONGODB_URI`, and confirm your IP is whitelisted in MongoDB Atlas Network Access |
| Quiz generator returns empty results | No content has been ingested/embedded yet for that topic — run Section 3 first |
| Groq API errors | Check `GROQ_API_KEY` and `GROQ_MODEL` are set correctly in `.env` |
| `ModuleNotFoundError` when running `run_quiz.py` | Set `PYTHONPATH` to the `ai-ml` root before running (see [Section 4](#4-running-the-quiz-generator)) |
| Missing module errors | Re-run `pip install -r requirements.txt` |

---

## Technologies

- **LLM:** Groq Llama 3.3 70B (state-of-the-art inference)
- **Database:** MongoDB (text/chunk storage)
- **Vector DB:** Pinecone (semantic search)
- **Embedding Model:** `all-MiniLM-L6-v2` (local, free, no API key needed)
- **Ingestion:** FastAPI
- **Output Format:** Strict JSON (`application/json`)

---

## Contributing

1. Fork the repo and create a new branch for your feature/fix.
2. Never commit `.env` or any real credentials.
3. Open a pull request with a clear description of your changes.