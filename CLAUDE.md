# CLAUDE.md — Multilingual RAG System

## Project overview
Production-grade Hindi-English cross-lingual RAG system. Two-column UI (Sources sidebar | Chat) built with React + TypeScript + Tailwind CSS + Framer Motion. Features model picker with 6 OpenRouter models, drag-drop file upload with progress tracking, streaming responses with word-blur animation, and thinking animation. Backend: FastAPI + FAISS + BGE-M3 with GZip compression, LRU embedding cache, batched SQLite lookups, and zero-latency Gemini streaming. LLM: Gemini primary, OpenAI fallback.

## Commands
- `make install` — Install deps via uv
- `make test` — Run tests (277 pass, 3 skip). Uses KMP_DUPLICATE_LIB_OK=TRUE for macOS torch/faiss.
- `make run` — Start backend at :8000
- `cd frontend && npm run dev` — Start frontend dev server at :7860 (proxies API to backend :8000)
- `cd frontend && npm run build` — Build frontend for production
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
├── frontend/             # React + TypeScript + Vite (port 7860)
│   ├── src/components/   # UI components (ChatInput, Header, Welcome, StreamingMessage, etc.)
│   ├── src/components/ui/# Shared UI primitives (FileUpload, Skeleton)
│   ├── src/lib/          # api.ts (SSE streaming), utils.ts (markdown, lang detect)
│   └── src/types/        # TypeScript types, model definitions
└── docker-compose.yml
```

## Key constraints
- Two servers required: backend (:8000) must be running before frontend works
- Frontend dev server proxies /health, /stats, /ingest, /query to backend :8000 (configured in vite.config.ts)
- LLM keys optional — system works for retrieval without them, shows graceful error for generation
- Tests mock all LLM calls — zero real API calls in pytest
- BGE-M3 smoke tests gated behind RUN_SLOW_TESTS=1
- IVF-PQ tests skipped on macOS (torch/faiss OpenMP conflict)
- FAISS SIGABRT when all 277 tests run in single process on macOS — run in batches

## Frontend stack
- React 18, TypeScript, Vite (dev server + build)
- Tailwind CSS v3 with shadcn CSS variable system (HSL tokens)
- Framer Motion for animations (word-blur streaming, dropdown, page transitions)
- lucide-react for icons
- Model picker: 6 OpenRouter models (Gemini, GPT-4o Mini, Llama, Mistral, Qwen, Nemotron)

## Performance optimizations
- GZip compression middleware (minimum_size=500) in main.py
- X-Response-Time header on all responses
- Batched SQLite WHERE IN query in vector_store.py search()
- asyncio.Queue replaces polling in gemini_provider.py stream()
- LRU embedding cache (128 entries) in retriever.py
- SSE done event carries elapsed_ms for frontend latency display

## Tech versions
Backend: torch==2.4.1, sentence-transformers==3.2.1, faiss-cpu==1.8.0.post1, fastapi==0.115.4, google-generativeai==0.8.3, openai==1.54.4
Frontend: react@18.3.1, framer-motion@11.15.0, tailwindcss@3, vite@6, typescript@5.7

## Style
- Python: ruff for linting, type hints everywhere
- TypeScript: strict mode, no any
- Logging: use logging module, never print() in library code
- Errors: handle gracefully, never crash the UI
