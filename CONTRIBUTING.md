# Contributing

Thanks for your interest in contributing to the Multilingual RAG System.

## Dev setup

```bash
# Prerequisites: Python 3.11+, uv (https://docs.astral.sh/uv/)
git clone <repo-url>
cd multilingual-rag

# Install backend deps (including dev tools: pytest, ruff)
cd backend && uv sync --extra dev && cd ..

# Copy environment config
cp .env.example .env
# Edit .env to add your GEMINI_API_KEY and/or OPENAI_API_KEY

# Run the test suite
make test

# Run the linter
make lint
```

## Running locally

```bash
# Backend (FastAPI on port 8000)
make run

# Frontend (standalone HTML/JS server on port 7860, in a separate terminal)
make frontend
```

## Project layout

| Directory | Purpose |
|---|---|
| `backend/app/` | Main application code (ingestion, embeddings, retrieval, generation, API) |
| `backend/tests/` | pytest suite with mocked external APIs |
| `frontend/` | Standalone HTML/CSS/JS UI served by `frontend/app.py` |
| `docs/` | API and local development documentation |
| `scripts/` | Data download, benchmark preparation, evaluation runner |

## Testing

All tests mock external dependencies (LLM APIs, FAISS in some cases). No real API calls are made during testing.

```bash
# Run all tests
make test

# Run specific test files
cd backend && uv run pytest -v tests/test_generation.py

# Run tests in batches (avoids FAISS memory pressure on macOS)
cd backend && uv run pytest -v tests/test_chunker.py tests/test_config.py tests/test_rrf.py
cd backend && uv run pytest -v tests/test_vector_store.py tests/test_retriever.py
```

## Code style

- **Linter:** ruff (configured in `pyproject.toml`)
- **Line length:** 100 characters
- **Imports:** sorted by ruff (isort-compatible)
- Library code uses `logging.getLogger(__name__)`, never `print`

## Evaluation

Benchmark numbers are never fabricated. All values in REPORT.md use
`<TO_BE_FILLED_BY_RUNNER>` placeholders until real evaluation results are
available. To run the full evaluation:

```bash
make eval
```

This downloads benchmark datasets (MIRACL-hi, XOR-TyDi), builds a mini
benchmark, and runs the embedding comparison. Results land in `eval_results/`
and `REPORT.md`.

## Documentation

When changing runtime behavior, update the relevant docs in the same change:

- `README.md` for user-facing setup, architecture, and project structure.
- `docs/API.md` for endpoint behavior or request/response contract changes.
- `docs/LOCAL_DEVELOPMENT.md` for setup, test, evaluation, or troubleshooting changes.
- `REPORT.md` for evaluation methodology or generated benchmark output.
