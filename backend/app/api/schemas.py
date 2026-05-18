"""Pydantic models for API request / response payloads."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------- #
# Query
# ---------------------------------------------------------------------- #


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The user's question")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of passages to retrieve")


class SourceHit(BaseModel):
    """One retrieved passage sent to the frontend."""

    rank: int
    text: str
    score: float | None = None
    title: str = ""
    source: str = ""
    language: str = ""
    doc_id: str = ""


class QueryResponse(BaseModel):
    """Non-streaming response (fallback for non-SSE clients)."""

    answer: str
    sources: list[SourceHit]
    cited_indices: list[int] = []
    language: str = ""
    strategy: str = ""
    model: str = ""


# ---------------------------------------------------------------------- #
# Ingest
# ---------------------------------------------------------------------- #


class IngestResponse(BaseModel):
    filename: str
    chunks: int
    message: str = "Ingested successfully"


# ---------------------------------------------------------------------- #
# Stats / Health
# ---------------------------------------------------------------------- #


class StatsResponse(BaseModel):
    index_size: int = Field(description="Number of vectors in the index")
    embedding_model: str
    embedding_dim: int
    faiss_index_type: str
    languages: list[str] = Field(default_factory=list, description="Languages detected in corpus")
    llm_provider: str = Field(default="", description="Human-readable LLM provider label")


class HealthResponse(BaseModel):
    status: str = "ok"
    index_loaded: bool = False
    llm_provider: str = ""
