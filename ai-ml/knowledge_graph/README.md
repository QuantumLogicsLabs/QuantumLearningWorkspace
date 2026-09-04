# Knowledge Graph — Team Lambda

Connects related content a user has ingested, by reusing the vectors already
produced by the embedding pipeline. Two layers:

- **Document graph** — connects whole documents that are topically related.
- **Topic graph** — finer connections between individual chunks, within and
  across documents.

## Where this fits

```
ai-ml/
├── ingestion/
├── embedding/
├── quiz_generator/
└── knowledge_graph/   ← this module
```

## Install

From `ai-ml/`:

```bash
pip install -r knowledge_graph/requirements.txt
```

(Most of these are likely already installed via `embedding/requirements.txt`
— this file just makes the module's own dependencies explicit.)

## Run the API

```bash
cd ai-ml
uvicorn knowledge_graph.app.api.graph_routes:app --reload --port 8005
```

Docs: http://127.0.0.1:8005/docs

All endpoints require `Authorization: Bearer <jwt>`, same as quiz_generator.

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | No auth — basic liveness check |
| `/graph` | GET | Returns the authenticated user's current graph (nodes + edges) |
| `/graph/rebuild` | POST | Rebuilds the graph from the user's current embedded content |
| `/graph` | DELETE | Deletes all graph edges for the authenticated user |

## Run the tests

```bash
cd ai-ml
pytest knowledge_graph/tests/ -v
```

14 tests, covering: utility math (vectorizer, similarity, labeling), graph
building against a real Chroma collection, related vs. unrelated document
detection, empty-user handling, and delete behavior.

## How it works, briefly

1. `document_graph_builder.py` groups a user's chunks by document, averages
   each document's chunk vectors, and compares every pair using cosine
   similarity (`utils/similarity.py`).
2. Pairs above `SIMILARITY_THRESHOLD_DOCUMENT` (default 0.5, see `config.py`)
   become edges, each labeled with shared keywords (`utils/topic_labeler.py`
   — no LLM, no paid API).
3. `topic_graph_builder.py` does the same at the individual-chunk level.
4. `graph_service.py` orchestrates both builders and persists edges via
   `storage/graph_store.py` — a JSON file living alongside the existing
   shared ChromaDB data directory (no new database introduced).
5. `api/graph_routes.py` exposes it all over HTTP, authenticated with the
   same JWT pattern as quiz_generator (`quiz_generator.app.auth`).

## Not included in this version

- Frontend visualization (this module returns data, not a rendered graph)
- LLM-based relationship explanations (labeling uses keyword overlap only,
  to avoid requiring a paid API key)

## Known limitation

`storage/graph_store.py` uses a simple JSON file, not a proper database —
fine for how this is used today (rebuilt on-demand per user), but not
safe under heavy concurrent writes. Worth revisiting if usage grows.
