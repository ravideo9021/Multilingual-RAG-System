"""Centralized application settings loaded from environment / .env.

All path fields default to locations under ``backend/`` and are resolved
to absolute paths at import time, so settings work regardless of the
current working directory. Relative overrides supplied via env vars or
``.env`` are also resolved relative to the backend root (not the CWD).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# .../multilingual-rag/backend — the package's installable root.
# `__file__` = .../backend/app/config.py → parent.parent = backend/.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings.

    Loaded from a `.env` file at the backend working directory, or from the
    process environment. Unknown keys are ignored so the same `.env` can be
    shared with the frontend without breaking validation.
    """

    model_config = SettingsConfigDict(
        env_file=(
            _BACKEND_ROOT.parent / ".env",   # project root (multilingual-rag/.env)
            _BACKEND_ROOT / ".env",           # backend/.env (override if present)
        ),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ----- Paths -----
    # Defaults are anchored at ``backend/`` so the app works from any CWD.
    # Relative env overrides (e.g., DATA_DIR=custom_data) are resolved
    # against ``backend/`` too — see the validator below.
    data_dir: Path = Field(default=_BACKEND_ROOT / "data")
    models_dir: Path = Field(default=_BACKEND_ROOT / "data" / "models")
    index_dir: Path = Field(default=_BACKEND_ROOT / "data" / "index")

    # ----- Chunker -----
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 80
    tokenizer_name: str = "BAAI/bge-m3"

    # ----- Embeddings (Chunk B) -----
    embedding_model: Literal["bge-m3", "e5", "openai"] = "bge-m3"
    embedding_batch_size: int = 32
    device: Literal["auto", "cpu", "cuda", "mps"] = "auto"

    # ----- Retrieval (Chunks B/C) -----
    retrieval_top_k: int = 5
    rrf_k: int = 60
    relevance_threshold: float = 0.35
    faiss_index_type: Literal["flat", "ivfpq"] = "flat"

    # ----- Language classifier (Chunk C) -----
    # Path to fastText's lid.176.bin model (downloaded via scripts/download_models.sh).
    fasttext_model_path: Path = Field(default=_BACKEND_ROOT / "data" / "models" / "lid.176.bin")
    # Script-ratio thresholds for combining fastText output with Unicode
    # script counts. A script is "dominant" if its ratio exceeds
    # `lang_script_dominance`. fastText's top-language confidence must exceed
    # `lang_fasttext_confidence` to be trusted over script-only heuristics.
    # Both are tuned empirically; exposed as config so they can be adjusted
    # without code changes.
    lang_script_dominance: float = 0.7
    lang_fasttext_confidence: float = 0.6

    # ----- LLM (Chunk E) -----
    # Default is "openai" — but with ``openai_base_url`` set to OpenRouter,
    # this transparently uses OpenRouter's free DeepSeek via the OpenAI SDK.
    # Leave ``openai_base_url`` unset to talk to OpenAI directly.
    llm_provider: Literal["gemini", "openai"] = "openai"
    gemini_main_model: str = "gemini-3.6-flash"
    gemini_cheap_model: str = "gemini-3.6-flash"
    openai_main_model: str = "nvidia/nemotron-3-nano-30b-a3b:free"
    openai_cheap_model: str = "nvidia/nemotron-3-nano-30b-a3b:free"
    openai_base_url: str | None = "https://openrouter.ai/api/v1"
    gemini_api_key: str | None = None
    openai_api_key: str | None = None

    # ----- Logging -----
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ------------------------------------------------------------------ #
    # Validators
    # ------------------------------------------------------------------ #

    @field_validator("data_dir", "models_dir", "index_dir", "fasttext_model_path")
    @classmethod
    def _anchor_relative_to_backend(cls, v: Path) -> Path:
        """Resolve relative paths against the ``backend/`` root.

        Absolute paths are returned unchanged. Relative env overrides (e.g.,
        ``DATA_DIR=my_data``) become ``backend/my_data`` so the app is
        insensitive to CWD.
        """
        p = Path(v)
        if not p.is_absolute():
            p = _BACKEND_ROOT / p
        return p


settings = Settings()
