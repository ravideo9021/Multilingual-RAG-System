# CLAUDE.md — Multilingual RAG System

## Project overview
Production-grade Hindi-English cross-lingual RAG system. Three-column single-page UI (Sources | Chat | Stats). Backend: FastAPI + FAISS + BGE-M3. Frontend: standalone HTML/JS served by Python HTTP server. LLM: Gemini primary, OpenAI fallback.

## Commands
- `make install` — Install deps via uv
- `make test` — Run tests (276 pass, 5 skip). Uses KMP_DUPLICATE_LIB_OK=TRUE for macOS torch/faiss.
- `make run` — Start backend at :8000
- `make frontend` — Start frontend HTTP server at :7860 (backend must be running first)
- `make docker-up` / `make docker-down` — Docker compose
- Run tests in batches to avoid FAISS SIGABRT on macOS:
  - Batch 1: `uv run pytest -v tests/test_chunker.py tests/test_config.py tests/test_rrf.py tests/test_threshold.py tests/test_language_classifier.py tests/test_embeddings.py tests/test_eval_metrics.py tests/test_eval_benchmark.py tests/test_eval_report.py tests/test_llm_providers.py tests/test_generation.py tests/test_api.py`
  - Batch 2: `uv run pytest -v tests/test_vector_store.py tests/test_retriever.py tests/test_query_router.py`

## Architecture
```
multilingual-rag/
├── backend/app/          # FastAPI backend
│   ├── ingestion/        # chunker.py — Devanagari-aware recursive chunker
│   ├── embeddings/       # BGE-M3, e5, OpenAI wrappers + factory
│   ├── retrieval/        # FAISS store, retriever, RRF, language classifier, query router
│   ├── generation/       # Gemini/OpenAI providers + factory, RAG generator, translator
│   ├── api/              # FastAPI routes (/health, /stats, /ingest, /query SSE)
│   └── eval/             # RAGAS, cross-lingual benchmark, embedding comparison
├── frontend/app.py       # Minimal Python HTTP server (serves index.html on :7860)
├── frontend/index.html   # Self-contained HTML/CSS/JS frontend (talks to backend :8000)
└── docker-compose.yml
```

## Key constraints
- Two servers required: backend (:8000) must be running before frontend (:7860) works
- Frontend makes cross-origin fetch() calls to backend — CORS is configured in backend/app/main.py
- No API calls on page load — stats load on button click only
- LLM keys optional — system works for retrieval without them, shows graceful error for generation
- Tests mock all LLM calls — zero real API calls in pytest
- BGE-M3 smoke tests gated behind RUN_SLOW_TESTS=1
- IVF-PQ tests skipped on macOS (torch/faiss OpenMP conflict)
- FAISS SIGABRT when all 276 tests run in single process on macOS — run in batches

## Tech versions (pinned in pyproject.toml)
torch==2.4.1, sentence-transformers==3.2.1, faiss-cpu==1.8.0.post1, fastapi==0.115.4, google-generativeai==0.8.3, openai==1.54.4
Frontend: zero dependencies (vanilla HTML/JS/CSS, served by Python stdlib http.server)

## Style
- Python: ruff for linting, type hints everywhere
- Logging: use logging module, never print() in library code
- Errors: handle gracefully, never crash the UI
