# Local Development

## Prerequisites

- Python 3.11
- `uv`
- Docker and Docker Compose if you want containerized services
- An LLM API key for generated answers

Install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setup

```bash
cd multilingual-rag
make install
cp .env.example .env
bash scripts/download_models.sh
```

Edit `.env` before running the app:

- Use OpenRouter or another OpenAI-compatible endpoint by setting
  `OPENAI_API_KEY` and `OPENAI_BASE_URL`.
- Use OpenAI directly by setting `OPENAI_API_KEY` and leaving
  `OPENAI_BASE_URL` empty.
- Use Gemini by setting `LLM_PROVIDER=gemini` and `GEMINI_API_KEY`.

## Run The App

Start the backend:

```bash
make run
```

Start the frontend in a second terminal:

```bash
make frontend
```

Open `http://localhost:7860`. The frontend calls the backend on
`http://localhost:8000`.

## Docker

```bash
make docker-up
```

Docker Compose starts the backend and frontend, persists backend data in a named
volume, and waits for the backend health check before starting the frontend.

## Indexing Content

You can upload files from the frontend or call the API directly:

```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@backend/data/sample_corpus/india.en.txt"
```

For repeatable sample data, download the sample corpus:

```bash
cd backend
uv run python ../scripts/download_sample_corpus.py
```

To build a persisted FAISS index from a JSONL corpus, pass explicit input and
output paths:

```bash
cd backend
uv run python ../scripts/build_index.py \
  --corpus data/benchmark/corpus.jsonl \
  --out data/index/bge-m3
```

## Testing And Linting

```bash
make test
make lint
```

The test suite mocks LLM APIs and avoids real API calls. On macOS, the Makefile
sets `KMP_DUPLICATE_LIB_OK=TRUE` to avoid the common torch/faiss OpenMP conflict
during tests.

## Evaluation

```bash
make eval
```

The full evaluation downloads MIRACL-hi and XOR-TyDi samples, builds a compact
benchmark corpus, runs embedding comparisons, and updates `REPORT.md`.

## Troubleshooting

| Symptom | Check |
|---|---|
| Frontend says connection failed | Confirm `make run` is active and `curl http://localhost:8000/health` returns `ok` |
| Queries return no citations | Confirm documents were ingested and `/stats` shows a nonzero index size |
| Generation is unavailable | Confirm `.env` contains a valid `OPENAI_API_KEY` or `GEMINI_API_KEY` |
| Language detection fails at startup | Run `bash scripts/download_models.sh` and confirm `backend/data/models/lid.176.bin` exists |
| Slow first request | BGE-M3, tokenizer, FAISS, and fastText load lazily or warm up during startup |
| Repeated queries still slow | Embedding cache (128 entries) eliminates re-encoding; restart the server to clear it |

## Performance (v0.2.0)

The backend includes several optimizations enabled by default:

- **GZip compression** — responses > 500 bytes are compressed automatically
- **Response timing** — every response includes an `X-Response-Time` header
- **Batched metadata lookups** — vector store search uses a single SQL query instead of per-result lookups
- **Embedding cache** — an LRU cache (128 entries) skips the embedding model for repeated queries
- **Zero-latency streaming** — Gemini provider uses `asyncio.Queue` instead of polling for instant token delivery
- **Elapsed time** — the SSE `done` event includes `elapsed_ms` so the frontend can display query latency
