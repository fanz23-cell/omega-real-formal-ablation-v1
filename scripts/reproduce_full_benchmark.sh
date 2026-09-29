#!/usr/bin/env bash
# Level 3: requires YOUR OWN Anthropic API key. Reruns case generation, all B0/B1/C provider
# calls, scoring, and analysis fresh. Never embeds credentials -- you supply the key path.
set -euo pipefail
if [ $# -lt 1 ]; then
    echo "Usage: $0 /path/to/your/anthropic_key.txt [calibration|confirmatory]" >&2
    exit 1
fi
KEY_PATH="$1"
MODE="${2:-calibration}"

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../harness" && pwd)"
cd "$HARNESS_DIR"

echo "=== Prerequisite: isolated Omega/MeTTa runtime must be running (see docker/) ==="
docker inspect omega_isolated_benchmark_20260928 >/dev/null 2>&1 || {
    echo "Isolated container not found -- see docker/IMAGE_PROVENANCE.md to recreate it." >&2
    exit 1
}

echo "=== Running $MODE with a fresh, never-before-drawn seed pool ==="
python3 run_confirmatory.py "$KEY_PATH" "$MODE"

echo
echo "=== Recomputing analysis on the fresh run ==="
OUT_FILE="152_calibration_rows.json"
[ "$MODE" = "confirmatory" ] && OUT_FILE="153_confirmatory_rows.json"
python3 analyze.py "$OUT_FILE"

echo
echo "REPRODUCE_FULL_BENCHMARK ($MODE): DONE"
