#!/usr/bin/env bash
# Download runtime models that are NOT pulled via HuggingFace on-demand.
#
# Currently: fastText lid.176.bin (~125 MB) for language identification.
# The embedding models (BGE-M3, multilingual-e5) come from HuggingFace on
# first use and are cached by the transformers library itself — no action
# needed here for them.
#
# Run once after cloning:
#     bash scripts/download_models.sh
#
# Safe to re-run; skips downloads if the file already exists at the target
# size.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODELS_DIR="${REPO_ROOT}/backend/data/models"

mkdir -p "${MODELS_DIR}"

# ---------------------------------------------------------------------- #
# fastText lid.176.bin
# ---------------------------------------------------------------------- #

LID_URL="https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"
LID_PATH="${MODELS_DIR}/lid.176.bin"
LID_EXPECTED_MIN_SIZE=100000000  # ~125 MB actual; guard against partial download

if [[ -f "${LID_PATH}" ]]; then
    actual_size=$(stat -f%z "${LID_PATH}" 2>/dev/null || stat -c%s "${LID_PATH}")
    if [[ "${actual_size}" -gt "${LID_EXPECTED_MIN_SIZE}" ]]; then
        echo "[skip] ${LID_PATH} already present (${actual_size} bytes)"
    else
        echo "[warn] ${LID_PATH} exists but is only ${actual_size} bytes — redownloading"
        rm -f "${LID_PATH}"
    fi
fi

if [[ ! -f "${LID_PATH}" ]]; then
    echo "[fetch] lid.176.bin → ${LID_PATH}"
    if command -v curl >/dev/null 2>&1; then
        curl --fail --location --progress-bar -o "${LID_PATH}" "${LID_URL}"
    elif command -v wget >/dev/null 2>&1; then
        wget --progress=bar:force -O "${LID_PATH}" "${LID_URL}"
    else
        echo "error: neither curl nor wget is installed" >&2
        exit 1
    fi
fi

echo "[done] models ready in ${MODELS_DIR}"
