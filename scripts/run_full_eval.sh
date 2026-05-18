#!/usr/bin/env bash
# End-to-end evaluation pipeline.
#
# Steps:
#   1. Ensure runtime models are downloaded (fastText lid.176.bin)
#   2. Prepare the mini benchmark (MIRACL-hi + XOR-TyDi → unified JSONL)
#   3. Run the embedder comparison
#   4. Emit REPORT.md + eval_results/*.json
#
# Idempotent: step 1 skips if the model exists; step 2 is overwrite-safe;
# step 3 always runs (it's the point of invoking this script).
#
# Tunables via env vars (all optional):
#   MAX_QUERIES   — queries sampled per source dataset (default 100)
#   DISTRACTORS   — random non-relevant passages added (default 2000)
#   EMBEDDERS     — space-separated list for --compare (default "bge-m3 e5")
#   DEVICE        — "cpu" / "cuda" / "mps" / "auto" (default settings.device)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

MAX_QUERIES="${MAX_QUERIES:-100}"
DISTRACTORS="${DISTRACTORS:-2000}"
EMBEDDERS="${EMBEDDERS:-bge-m3 e5}"
DEVICE_FLAG=""
if [[ -n "${DEVICE:-}" ]]; then
    DEVICE_FLAG="--device ${DEVICE}"
fi

echo "=== [1/3] Download runtime models ==="
bash "${SCRIPT_DIR}/download_models.sh"
echo

echo "=== [2/3] Prepare mini benchmark (MIRACL-hi + XOR-TyDi) ==="
echo "max_queries=${MAX_QUERIES} distractors=${DISTRACTORS}"
if [[ -f "${REPO_ROOT}/backend/data/benchmark/queries.jsonl" && -f "${REPO_ROOT}/backend/data/benchmark/corpus.jsonl" ]]; then
    echo "[skip] benchmark already prepared. Delete backend/data/benchmark/ to rebuild."
else
    (cd backend && uv run python "${SCRIPT_DIR}/prepare_benchmark.py" \
        --max-queries "${MAX_QUERIES}" --distractors "${DISTRACTORS}")
fi
echo

echo "=== [3/3] Run embedder comparison ==="
echo "embedders: ${EMBEDDERS}"
# shellcheck disable=SC2086
(cd backend && uv run python "${SCRIPT_DIR}/run_eval.py" \
    --compare --embedders ${EMBEDDERS} ${DEVICE_FLAG})
echo

echo "=== Done ==="
echo "- REPORT.md       → ${REPO_ROOT}/REPORT.md"
echo "- eval_results/   → ${REPO_ROOT}/eval_results/"
