"""FastAPI route definitions.

All routes are registered on a single router and mounted by ``app.main``.

SSE event types for ``/query``:
    * ``sources``   — JSON array of retrieved passages
    * ``token``     — one text chunk from the LLM stream
    * ``citations`` — JSON array of cited source indices
    * ``error``     — error message string
    * ``done``      — empty; signals the stream is complete
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from fastapi import APIRouter, Request, UploadFile
from sse_starlette.sse import EventSourceResponse

from app.api.schemas import (
    HealthResponse,
    IngestResponse,
    QueryRequest,
    SourceHit,
    StatsResponse,
)
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _llm_provider_display() -> str:
    """Best-effort human-readable label for the configured LLM."""
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return f"Gemini ({settings.gemini_main_model})"
    if settings.openai_api_key:
        if settings.openai_base_url and "openrouter" in settings.openai_base_url.lower():
            family = settings.openai_main_model.split("/", 1)[0] or "model"
            return f"OpenRouter ({family})"
        return f"OpenAI ({settings.openai_main_model})"
    if settings.gemini_api_key:
        return f"Gemini ({settings.gemini_main_model})"
    return ""


# ---------------------------------------------------------------------- #
# Health
# ---------------------------------------------------------------------- #


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    state = request.app.state
    # Prefer the live model name set during startup (proves the key is good);
    # fall back to the config-derived label so the UI still shows something
    # informative when the LLM init failed.
    label = getattr(state, "llm_provider_name", "") or _llm_provider_display()
    return HealthResponse(
        status="ok",
        index_loaded=getattr(state, "index_loaded", False),
        llm_provider=label,
    )


# ---------------------------------------------------------------------- #
# Stats
# ---------------------------------------------------------------------- #


@router.get("/stats", response_model=StatsResponse)
def stats(request: Request) -> StatsResponse:
    state = request.app.state
    store = getattr(state, "store", None)
    embedder = getattr(state, "embedder", None)
    languages: list[str] = []
    index_size = 0

    if store is not None:
        index_size = len(store)
        # Query distinct languages from metadata store.
        try:
            rows = store._meta.execute(
                "SELECT DISTINCT language FROM chunks"
            ).fetchall()
            languages = sorted(r[0] for r in rows if r[0] and r[0] != "unknown")
        except Exception:
            pass

    label = getattr(state, "llm_provider_name", "") or _llm_provider_display()
    return StatsResponse(
        index_size=index_size,
        embedding_model=getattr(embedder, "name", "unknown"),
        embedding_dim=getattr(embedder, "dim", 0),
        faiss_index_type=getattr(store, "index_type", "unknown") if store else "unknown",
        languages=languages,
        llm_provider=label,
    )


# ---------------------------------------------------------------------- #
# Ingest
# ---------------------------------------------------------------------- #


@router.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile, request: Request) -> IngestResponse:
    """Accept a text/PDF/HTML file upload, chunk it, embed, and add to the index."""
    from fastapi import HTTPException

    state = request.app.state
    embedder = getattr(state, "embedder", None)
    store = getattr(state, "store", None)
    chunker = getattr(state, "chunker", None)

    if embedder is None or store is None or chunker is None:
        raise HTTPException(status_code=503, detail="Index not loaded")

    from app.ingestion.extractors import ExtractionError, extract_text

    content = await file.read()
    filename = file.filename or "upload"

    try:
        text = extract_text(filename, content)
    except ExtractionError as exc:
        # 422 = unprocessable entity. The file is valid HTTP but we can't
        # extract anything useful from it (image-only PDF, corrupt, etc.).
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    chunks = chunker.chunk_text(text, source=filename)
    if not chunks:
        return IngestResponse(filename=filename, chunks=0, message="No chunks produced")

    texts = [c.text for c in chunks]
    vecs = embedder.encode_passages(texts, batch_size=32, show_progress=False)
    metadatas = [
        {
            "text": c.text,
            "source": c.source,
            "language": c.language,
            "doc_id": f"{filename}:{c.chunk_index}",
            "title": filename,
        }
        for c in chunks
    ]
    store.add(vecs, metadatas=metadatas)
    state.index_loaded = True

    logger.info("Ingested %s: %d chunks", filename, len(chunks))
    return IngestResponse(filename=filename, chunks=len(chunks))


# ---------------------------------------------------------------------- #
# Query (SSE)
# ---------------------------------------------------------------------- #


def _source_hit(rank: int, hit: dict[str, Any]) -> dict:
    """Convert a retrieval hit dict to a SourceHit-compatible dict."""
    return SourceHit(
        rank=rank,
        text=hit.get("text", ""),
        score=hit.get("score"),
        title=hit.get("title", ""),
        source=hit.get("source", ""),
        language=hit.get("language", ""),
        doc_id=hit.get("doc_id", ""),
    ).model_dump()


@router.post("/query")
async def query(body: QueryRequest, request: Request):
    """SSE-streamed RAG query.

    Behavior:
        * If no documents are indexed, skip retrieval and chat directly with
          the LLM (no sources, no citations).
        * If documents are indexed but retrieval finds nothing relevant,
          stream a "couldn't find specifics, here's what I know" answer.
        * Otherwise, do full RAG: retrieve → ground answer in passages.

    Event types emitted: sources, token, citations, error, done
    """
    state = request.app.state
    router_obj = getattr(state, "query_router", None)
    generator = getattr(state, "generator", None)
    store = getattr(state, "store", None)

    async def _event_stream():
        t0 = time.perf_counter()
        try:
            store_empty = store is None or len(store) == 0

            # ---- No-docs path: pure chat, no retrieval ----
            if store_empty:
                yield {"event": "sources", "data": "[]"}
                if generator is None:
                    yield {
                        "event": "error",
                        "data": "No LLM provider configured. Set OPENAI_API_KEY (with optional OPENAI_BASE_URL for OpenRouter) or GEMINI_API_KEY in .env.",
                    }
                else:
                    # Best-effort language detection so the prompt nudges the
                    # right reply language. If the router/classifier isn't
                    # available, default to "en".
                    lang = "en"
                    if router_obj is not None:
                        try:
                            lang = router_obj._classifier.classify(body.query).language
                        except Exception:
                            pass
                    async for token in generator.chat_stream(body.query, language=lang):
                        yield {"event": "token", "data": token}
                    yield {"event": "citations", "data": "[]"}
                return

            # ---- Documents are indexed: route through retrieval ----
            if router_obj is None:
                yield {"event": "error", "data": "Service not ready — embedder not loaded"}
                return

            routed = router_obj.route(body.query)
            sources = [_source_hit(i + 1, h) for i, h in enumerate(routed.results)]
            yield {"event": "sources", "data": json.dumps(sources, ensure_ascii=False)}

            if generator is None:
                yield {
                    "event": "error",
                    "data": "No LLM provider configured. Set OPENAI_API_KEY (with optional OPENAI_BASE_URL for OpenRouter) or GEMINI_API_KEY in .env.",
                }
                return

            # ---- No relevant passages: chatty fallback, not a dead-end ----
            if not routed.results:
                async for token in generator.fallback_stream(
                    body.query, language=routed.language
                ):
                    yield {"event": "token", "data": token}
                yield {"event": "citations", "data": "[]"}
                return

            # ---- Normal RAG path ----
            full_answer = ""
            async for token in generator.stream(
                body.query,
                routed.results,
                language=routed.language,
            ):
                full_answer += token
                yield {"event": "token", "data": token}

            from app.generation.generator import extract_citations

            cited = extract_citations(full_answer, len(routed.results))
            yield {"event": "citations", "data": json.dumps(cited)}
        except Exception as exc:
            logger.exception("Error during query streaming")
            yield {"event": "error", "data": str(exc)}
        finally:
            elapsed = round((time.perf_counter() - t0) * 1000)
            yield {"event": "done", "data": json.dumps({"elapsed_ms": elapsed})}

    return EventSourceResponse(_event_stream())
