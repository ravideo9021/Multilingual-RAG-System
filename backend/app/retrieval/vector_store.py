"""FAISS-backed vector store with stable IDs, deletion, and metadata.

Supports two index types:

* ``"flat"`` — :class:`faiss.IndexFlatIP`.
  Exact cosine (inner product of L2-normalized vectors). Use for ≤ ~100K chunks.
* ``"ivfpq"`` — :class:`faiss.IndexIVFPQ`.
  Approximate, trains on first batch. Use for > ~1M chunks.

Note: This store does NOT use ``IndexIDMap2`` because of a known macOS
SIGSEGV when ``IndexIDMap*`` is combined with sentence-transformers and
fastText in the same process. Instead, FAISS uses sequential internal IDs
and the sqlite metadata layer tracks the custom-to-FAISS-ID mapping.

Vectors are assumed L2-normalized (the embedders in :mod:`app.embeddings`
guarantee this). Cosine similarity == inner product under that assumption.

Metadata is stored in an in-memory SQLite database (stdlib, no extra dep),
persisted to a sidecar file on :meth:`save`.

Layout on disk after :meth:`save`::

    <path>/
    ├── index.faiss
    ├── metadata.sqlite
    └── config.json
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Literal

import numpy as np

logger = logging.getLogger(__name__)

IndexType = Literal["flat", "ivfpq"]


class FaissStore:
    """Vector store with stable IDs and deletion support.

    Parameters
    ----------
    dim:
        Embedding dimensionality.
    index_type:
        ``"flat"`` (exact) or ``"ivfpq"`` (approximate, requires training).
    ivfpq_nlist:
        Number of Voronoi cells for IVF-PQ. Rule of thumb: 4 × √N.
    ivfpq_m:
        Number of subquantizers for product quantization. Must divide ``dim``.
    ivfpq_nbits:
        Bits per subquantizer code (typically 8).
    nprobe:
        Number of cells probed at search time for IVF-PQ. Higher → more
        accurate, slower. Ignored for flat indexes.
    """

    def __init__(
        self,
        dim: int,
        index_type: IndexType = "flat",
        ivfpq_nlist: int = 100,
        ivfpq_m: int = 16,
        ivfpq_nbits: int = 8,
        nprobe: int = 8,
    ) -> None:
        if dim < 1:
            raise ValueError(f"dim must be >= 1, got {dim}")
        if index_type not in ("flat", "ivfpq"):
            raise ValueError(f"index_type must be 'flat' or 'ivfpq', got {index_type!r}")
        if index_type == "ivfpq" and dim % ivfpq_m != 0:
            raise ValueError(
                f"ivfpq_m ({ivfpq_m}) must divide dim ({dim}) for product quantization"
            )

        self.dim = dim
        self.index_type: IndexType = index_type
        self.ivfpq_nlist = ivfpq_nlist
        self.ivfpq_m = ivfpq_m
        self.ivfpq_nbits = ivfpq_nbits
        self.nprobe = nprobe

        self._index = self._build_index()
        self._meta: sqlite3.Connection = sqlite3.connect(":memory:")
        self._setup_schema()
        self._next_id = 1

    # ------------------------------------------------------------------ #
    # Index construction
    # ------------------------------------------------------------------ #

    def _build_index(self):
        import faiss

        if self.index_type == "flat":
            return faiss.IndexFlatIP(self.dim)
        else:  # ivfpq
            quantizer = faiss.IndexFlatIP(self.dim)
            idx = faiss.IndexIVFPQ(
                quantizer,
                self.dim,
                self.ivfpq_nlist,
                self.ivfpq_m,
                self.ivfpq_nbits,
            )
            idx.metric_type = faiss.METRIC_INNER_PRODUCT
            idx.nprobe = self.nprobe
            return idx

    def _setup_schema(self) -> None:
        self._meta.executescript(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY,
                faiss_idx INTEGER NOT NULL,
                text TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                language TEXT NOT NULL DEFAULT 'unknown',
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_faiss ON chunks(faiss_idx);
            CREATE INDEX IF NOT EXISTS idx_source ON chunks(source);
            CREATE INDEX IF NOT EXISTS idx_language ON chunks(language);
            """
        )
        self._meta.commit()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def __len__(self) -> int:
        return int(self._index.ntotal)

    @property
    def is_trained(self) -> bool:
        return bool(self._index.is_trained)

    def add(
        self,
        embeddings: np.ndarray,
        metadatas: list[dict[str, Any]] | None = None,
    ) -> list[int]:
        """Add ``embeddings`` to the index.

        Parameters
        ----------
        embeddings:
            ``(N, dim)`` float32 array. Assumed L2-normalized.
        metadatas:
            Optional list of per-row metadata dicts. Recognized keys:
            ``text``, ``source``, ``language``. Other keys are serialized to
            a JSON blob and round-tripped intact.

        Returns
        -------
        list[int]
            The stable IDs assigned to the inserted rows.
        """
        embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)
        if embeddings.ndim != 2 or embeddings.shape[1] != self.dim:
            raise ValueError(
                f"expected ({self.dim},)-dim embeddings, got shape {embeddings.shape}"
            )
        n = embeddings.shape[0]
        if n == 0:
            return []
        if metadatas is None:
            metadatas = [{} for _ in range(n)]
        if len(metadatas) != n:
            raise ValueError(
                f"metadatas length ({len(metadatas)}) != embeddings count ({n})"
            )

        # IVF-PQ needs training on the first add.
        if self.index_type == "ivfpq" and not self.is_trained:
            logger.info("Training IVF-PQ index on %d vectors", n)
            self._index.train(embeddings)

        # Plain IndexFlatIP uses sequential auto-IDs (0-based).
        # Record the FAISS internal position for each row.
        faiss_start = int(self._index.ntotal)
        self._index.add(embeddings)

        ids = np.arange(self._next_id, self._next_id + n, dtype=np.int64)
        self._next_id += n

        rows = []
        for i, (id_, meta) in enumerate(zip(ids, metadatas, strict=True)):
            text = meta.get("text", "")
            source = meta.get("source", "")
            language = meta.get("language", "unknown")
            extra = {
                k: v for k, v in meta.items() if k not in ("text", "source", "language")
            }
            rows.append(
                (
                    int(id_),
                    faiss_start + i,
                    text,
                    source,
                    language,
                    json.dumps(extra, ensure_ascii=False),
                )
            )
        self._meta.executemany(
            "INSERT OR REPLACE INTO chunks (id, faiss_idx, text, source, language, metadata_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        self._meta.commit()
        logger.info("Added %d vectors to %s index (ntotal=%d)", n, self.index_type, len(self))
        return ids.tolist()

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for the top-``k`` nearest neighbors of a single query.

        Parameters
        ----------
        query_embedding:
            ``(dim,)`` or ``(1, dim)`` float32 vector.
        k:
            Number of neighbors to return.

        Returns
        -------
        list[dict]
            Each dict has keys ``id``, ``score``, ``text``, ``source``,
            ``language``, plus any extra metadata fields originally supplied.
            Ordered best-to-worst by score. Shorter than ``k`` if the index
            holds fewer than ``k`` usable vectors.
        """
        q = np.ascontiguousarray(query_embedding, dtype=np.float32)
        if q.ndim == 1:
            q = q[np.newaxis, :]
        if q.shape[1] != self.dim:
            raise ValueError(f"expected dim={self.dim}, got {q.shape[1]}")
        if len(self) == 0:
            return []
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k}")

        scores, faiss_ids = self._index.search(q, k)
        valid = [
            (float(s), int(fi))
            for s, fi in zip(scores[0], faiss_ids[0], strict=True)
            if fi != -1
        ]
        if not valid:
            return []

        faiss_idx_list = [fi for _, fi in valid]
        score_by_faiss = {fi: s for s, fi in valid}
        placeholders = ",".join("?" * len(faiss_idx_list))
        rows = self._meta.execute(
            f"SELECT faiss_idx, id, text, source, language, metadata_json "
            f"FROM chunks WHERE faiss_idx IN ({placeholders})",
            faiss_idx_list,
        ).fetchall()
        row_by_faiss = {r[0]: r[1:] for r in rows}

        results: list[dict[str, Any]] = []
        for faiss_idx in faiss_idx_list:
            row = row_by_faiss.get(faiss_idx)
            if row is None:
                continue
            id_, text, source, language, meta_json = row
            extra = json.loads(meta_json) if meta_json else {}
            results.append(
                {
                    "id": int(id_),
                    "score": score_by_faiss[faiss_idx],
                    "text": text,
                    "source": source,
                    "language": language,
                    **extra,
                }
            )
        return results

    def delete(self, ids: list[int]) -> int:
        """Delete metadata by ID.

        Note: With plain IndexFlatIP (no IndexIDMap), vectors cannot be removed
        from the FAISS index. Deleted entries are removed from the sqlite
        metadata layer and will be skipped during search results.

        Returns the number of metadata rows deleted.
        """
        if not ids:
            return 0

        placeholders = ",".join("?" * len(ids))
        cursor = self._meta.execute(
            f"DELETE FROM chunks WHERE id IN ({placeholders})",
            [int(i) for i in ids],
        )
        n_removed = cursor.rowcount
        self._meta.commit()
        logger.info("Deleted %d metadata rows (requested %d)", n_removed, len(ids))
        return n_removed

    def stats(self) -> dict[str, Any]:
        """Summary of the current index state."""
        row = self._meta.execute(
            "SELECT language, COUNT(*) FROM chunks GROUP BY language"
        ).fetchall()
        by_language = {lang: cnt for lang, cnt in row}
        return {
            "index_type": self.index_type,
            "dim": self.dim,
            "ntotal": len(self),
            "is_trained": self.is_trained,
            "by_language": by_language,
            "next_id": self._next_id,
        }

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def save(self, path: str | Path) -> None:
        """Persist the index, metadata, and config to a directory."""
        import faiss

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self._index, str(path / "index.faiss"))

        # sqlite3.Connection.backup(dest) copies self → dest
        disk = sqlite3.connect(str(path / "metadata.sqlite"))
        try:
            self._meta.backup(disk)
        finally:
            disk.close()

        config = {
            "dim": self.dim,
            "index_type": self.index_type,
            "ivfpq_nlist": self.ivfpq_nlist,
            "ivfpq_m": self.ivfpq_m,
            "ivfpq_nbits": self.ivfpq_nbits,
            "nprobe": self.nprobe,
            "next_id": self._next_id,
        }
        (path / "config.json").write_text(
            json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("Saved FaissStore (ntotal=%d) to %s", len(self), path)

    @classmethod
    def load(cls, path: str | Path) -> "FaissStore":
        """Load a previously-saved store."""
        import faiss

        path = Path(path)
        config = json.loads((path / "config.json").read_text(encoding="utf-8"))

        store = cls(
            dim=config["dim"],
            index_type=config["index_type"],
            ivfpq_nlist=config.get("ivfpq_nlist", 100),
            ivfpq_m=config.get("ivfpq_m", 16),
            ivfpq_nbits=config.get("ivfpq_nbits", 8),
            nprobe=config.get("nprobe", 8),
        )
        # Replace the freshly-built empty index with the persisted one.
        store._index = faiss.read_index(str(path / "index.faiss"))
        store._next_id = config.get("next_id", 1)

        # Restore metadata: sqlite3 backup copies self → dest, so load via
        # disk.backup(memory).
        disk = sqlite3.connect(str(path / "metadata.sqlite"))
        try:
            disk.backup(store._meta)
        finally:
            disk.close()

        logger.info("Loaded FaissStore (ntotal=%d) from %s", len(store), path)
        return store
