.PHONY: install test lint run frontend eval docker-up docker-down clean help

help:
	@echo "Multilingual RAG System — common commands"
	@echo ""
	@echo "  make install     Install Python dependencies via uv"
	@echo "  make test        Run the backend test suite"
	@echo "  make lint        Run ruff linter"
	@echo "  make run         Start FastAPI dev server (port 8000)"
	@echo "  make frontend    Start frontend server (port 7860)"
	@echo "  make eval        Run full evaluation pipeline"
	@echo "  make docker-up   docker-compose up --build"
	@echo "  make docker-down docker-compose down"
	@echo "  make clean       Remove caches"

install:
	cd backend && uv sync --extra dev

test:
	cd backend && KMP_DUPLICATE_LIB_OK=TRUE uv run pytest -v

lint:
	cd backend && uv run ruff check app tests

run:
	cd backend && TOKENIZERS_PARALLELISM=false OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES \
		uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && python3 app.py

eval:
	bash scripts/run_full_eval.sh

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf backend/.pytest_cache backend/.ruff_cache
