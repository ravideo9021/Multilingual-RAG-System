# Evaluation Report — Multilingual RAG (Hindi / English)

_This file is a **template**. All metric values below are placeholders until
you run `bash scripts/run_full_eval.sh` — the eval runner overwrites this
file with real numbers. The project policy is **no faked numbers**, so any
placeholder you see here has not yet been replaced with measured data._

## Executive summary

- **Corpus:** hand-curated matched Hindi/English Wikipedia pairs
  (`backend/data/sample_corpus/`), ingested and indexed with BGE-M3.
- **Gold benchmark:** scaled-down mini versions of MIRACL-hi and XOR-TyDi
  (see "Methodology" below). Not directly comparable to the published
  numbers for either dataset — reproducible and internally consistent.
- **Target:** ≥ 80% Recall@5 (aspirational; real number below).

## Embedding comparison

Benchmark: **miracl-hi+xortydi (mini)** — `<TO_BE_FILLED_BY_RUNNER>` queries

| Embedder | Recall@1 | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---|---|---|---|---|
| bge-m3 | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` |
| e5 (multilingual) | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` |
| openai (text-embedding-3-large) | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` |

## By sub-dataset (MIRACL-hi vs XOR-TyDi)

| Sub-dataset | N | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---|---|---|---|---|
| miracl-hi | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` |
| xor-tydi | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` | `<TO_BE_FILLED_BY_RUNNER>` |

## RAGAS generation-quality metrics

_Requires valid LLM API credentials because RAGAS uses a judge model. Populate
these values only from a real run; keep placeholders when no run has been
performed._

| Metric | Value |
|---|---|
| Faithfulness | `<TO_BE_FILLED_BY_RUNNER>` |
| Answer relevancy | `<TO_BE_FILLED_BY_RUNNER>` |
| Context precision | `<TO_BE_FILLED_BY_RUNNER>` |
| Context recall | `<TO_BE_FILLED_BY_RUNNER>` |

Judge: `gpt-4o-mini`. Sample size: `<TO_BE_FILLED_BY_RUNNER>` queries.

## Methodology

### Data sources

- **MIRACL-hi** (`miracl/miracl`, `hi` / `dev`). The benchmark spec and its
  Wikipedia corpus are released under CC-BY-SA; using them here for
  research / educational purposes.
- **XOR-TyDi** (`akariasai/xor_tydi_qa`, `validation`, filtered to Hindi).
  Cross-lingual questions: English questions with Hindi gold evidence.
- **Demo corpus:** a small hand-curated set of matched
  Hindi/English Wikipedia articles on ~25 topics
  (`scripts/download_sample_corpus.py`).

### Mini-benchmark construction

`scripts/prepare_benchmark.py` samples up to `--max-queries` queries per
source dataset (default 100 each) and builds a compact corpus consisting of:

1. Every gold passage referenced by any sampled query.
2. `--distractors` randomly-chosen passages (default 2000) that are *not*
   relevant to any sampled query.

This is a **scaled-down** evaluation — the full MIRACL-hi corpus is ~500K
passages, which is infeasible to embed with BGE-M3 on CPU for a portfolio
demo. The numbers here reflect retrieval quality on the compact corpus,
not on the full published benchmark.

### Metrics

- **Recall@k**: fraction of queries where *any* gold doc appears in the
  top-k (binary per query, averaged).
- **MRR@10**: reciprocal rank of the first gold doc in the top-10.
- **nDCG@10**: standard formula with binary relevance, truncated at 10.

### Configuration

| Setting | Value |
|---|---|
| Primary embedder | `bge-m3` (1024-d, FlagEmbedding) |
| Comparison embedders | `multilingual-e5-large` (1024-d), `text-embedding-3-large` (3072-d) |
| Vector store | FAISS `IndexFlatIP` wrapped in `IndexIDMap2` |
| Chunk size / overlap | 512 / 80 tokens (BGE-M3 tokenizer) |
| RRF k | 60 |
| Relevance threshold | 0.35 |
| Retrieval top-k | 5 |

### Reproducing

```bash
cd multilingual-rag
bash scripts/run_full_eval.sh
```

Or step by step:

```bash
# 1. Pull runtime models (fastText lid.176.bin)
bash scripts/download_models.sh

# 2. Build the mini benchmark
cd backend && uv run python ../scripts/prepare_benchmark.py \
    --max-queries 100 --distractors 2000

# 3. Run the embedder comparison
uv run python ../scripts/run_eval.py --compare --embedders bge-m3 e5
```

Raw per-query results land in `eval_results/*.json` alongside this report.

## Documentation sync checklist

When this report is regenerated, also check whether the following files need
matching updates:

- `README.md` evaluation tables and disclosed sample sizes.
- `docs/LOCAL_DEVELOPMENT.md` evaluation commands or prerequisites.
- `docs/API.md` if retrieval or generation behavior changes the API contract.

## License attribution

- MIRACL: Lee et al., 2023. CC-BY-SA 4.0. <https://huggingface.co/datasets/miracl/miracl>
- XOR-TyDi: Asai et al., 2021. CC-BY-SA 4.0. <https://nlp.cs.washington.edu/xorqa/>
- Wikipedia content: CC-BY-SA 4.0. <https://dumps.wikimedia.org/>
