"""FastAPI application entry point.

Lifespan handler loads the FAISS index and initializes the LLM provider
on startup. All heavy objects are stored on ``app.state`` and accessed
by route handlers via ``request.app.state``.
"""

from __future__ import annotations

# On macOS, the default multiprocessing start method is 'fork', which causes
# SIGSEGV when C extensions (FAISS, fastText, PyTorch) are loaded and a child
# process forks. Set 'spawn' before any of these libraries are imported.
import multiprocessing as _mp
import sys as _sys

if _sys.platform == "darwin":
    try:
        _mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_setup import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load index, embedder, LLM.  Shutdown: nothing to clean up."""
    configure_logging(settings.log_level)
    logger.info("Starting multilingual-rag backend")

    # -- Embedder --
    try:
        from app.embeddings import get_embedder

        embedder = get_embedder(settings.embedding_model, device=settings.device)
        # Warm-up: force the underlying model to load eagerly so it's fully
        # resident before FAISS/fastText load. Lazy loading during a request
        # causes SIGSEGV on macOS due to fork-after-load conflicts.
        embedder.encode(["warmup"], batch_size=1, show_progress=False)
        app.state.embedder = embedder
        logger.info("Loaded embedder: %s (dim=%d)", embedder.name, embedder.dim)
    except Exception as exc:
        logger.warning("Embedder init failed (%s) — /ingest and /query will be unavailable", exc)
        app.state.embedder = None

    # -- FAISS store --
    index_path = settings.index_dir / settings.embedding_model
    try:
        if (index_path / "index.faiss").exists():
            from app.retrieval.vector_store import FaissStore

            store = FaissStore.load(index_path)
            app.state.store = store
            app.state.index_loaded = True
            logger.info("Loaded FAISS index from %s (ntotal=%d)", index_path, len(store))
        else:
            # Create empty store so /ingest works without a pre-built index.
            from app.retrieval.vector_store import FaissStore

            dim = app.state.embedder.dim if app.state.embedder else 1024
            store = FaissStore(dim=dim, index_type=settings.faiss_index_type)
            app.state.store = store
            app.state.index_loaded = False
            logger.info("No pre-built index at %s — starting with empty store", index_path)
    except Exception as exc:
        logger.warning("FAISS store init failed (%s)", exc)
        app.state.store = None
        app.state.index_loaded = False

    # -- Chunker --
    try:
        from app.ingestion.chunker import ScriptAwareRecursiveChunker

        app.state.chunker = ScriptAwareRecursiveChunker(
            chunk_size=settings.chunk_size_tokens,
            overlap=settings.chunk_overlap_tokens,
            tokenizer_name=settings.tokenizer_name,
        )
    except Exception as exc:
        logger.warning("Chunker init failed (%s)", exc)
        app.state.chunker = None

    # -- LLM provider --
    app.state.llm_provider_name = ""
    app.state.generator = None
    try:
        from app.generation.factory import get_llm

        llm = get_llm()
        # Pretty label for the UI: "OpenRouter (deepseek)" / "Gemini (...)"
        # rather than the raw model slug. The display helper introspects
        # settings to pick the best label.
        from app.api.routes import _llm_provider_display

        app.state.llm_provider_name = _llm_provider_display() or llm.model

        from app.generation.generator import RAGGenerator

        app.state.generator = RAGGenerator(llm)
        logger.info("LLM provider ready: %s", llm.model)
    except Exception as exc:
        logger.warning("LLM init failed (%s) — /query generation unavailable", exc)

    # -- Query router --
    app.state.query_router = None
    if app.state.embedder is not None and app.state.store is not None:
        try:
            from app.retrieval.language_classifier import LanguageClassifier
            from app.retrieval.query_router import QueryRouter
            from app.retrieval.retriever import DenseRetriever

            retriever = DenseRetriever(app.state.embedder, app.state.store)

            # Use LLM translator if LLM is available, else identity.
            translator = None
            try:
                from app.generation.factory import get_llm_cheap
                from app.generation.translator import LLMTranslator

                cheap_llm = get_llm_cheap()
                translator = LLMTranslator(cheap_llm)
                logger.info("LLM translator ready (model=%s)", cheap_llm.model)
            except Exception:
                logger.info("LLM translator unavailable — using identity translator")

            classifier = LanguageClassifier(
                model_path=str(settings.fasttext_model_path),
                script_dominance=settings.lang_script_dominance,
                fasttext_confidence=settings.lang_fasttext_confidence,
            )
            # Warm up fastText model eagerly — loading it lazily after
            # PyTorch/FAISS are resident causes SIGSEGV on macOS (fork issue).
            classifier.classify("warmup")

            app.state.query_router = QueryRouter(
                classifier=classifier,
                retriever=retriever,
                translator=translator,
                top_k=settings.retrieval_top_k,
                threshold=settings.relevance_threshold,
                rrf_k=settings.rrf_k,
            )
            logger.info("Query router ready")
        except Exception as exc:
            logger.warning("Query router init failed (%s)", exc)

    yield
    logger.info("Shutting down multilingual-rag backend")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Multilingual RAG — Hindi/English",
        description="Cross-lingual retrieval-augmented generation",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow localhost dev servers.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:7860",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:7860",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.routes import router

    app.include_router(router)

    return app


app = create_app()
