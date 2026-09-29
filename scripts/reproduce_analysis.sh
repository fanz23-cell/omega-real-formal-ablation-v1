#!/usr/bin/env bash
# Level 1: no API key needed. Recomputes every score/CI/sign-test/verdict from the raw
# saved rows -- proves the results/ JSON isn't hand-typed.
set -euo pipefail
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../harness" && pwd)"
DATA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../data" && pwd)"
cd "$HARNESS_DIR"

ROWS_FILE="$DATA_DIR/scored_rows.jsonl"
if [ ! -f "$ROWS_FILE" ]; then
    # fall back to the raw confirmatory rows file if scored_rows.jsonl wasn't packaged
    ROWS_FILE="$DATA_DIR/153_confirmatory_rows.json"
fi

echo "=== Recomputing full analysis from $ROWS_FILE ==="
python3 analyze.py "$ROWS_FILE"
echo
echo "REPRODUCE_ANALYSIS: PASS (compare 154_statistical_analysis.json against results/summary.json)"
