#!/usr/bin/env bash
# Level 2: no paid LLM call needed. Re-proves the real MeTTa/NAL component chain works,
# using the exact same isolated-container pattern as doc 147/149. Requires Docker.
set -euo pipefail
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../harness" && pwd)"
cd "$HARNESS_DIR"

echo "=== Running $0 real negative/gating controls (section 16) ==="
python3 negative_controls.py

echo
echo "=== Running real_metta_runner.py self-test (G6 geometry witness) ==="
python3 real_metta_runner.py

echo
echo "COMPONENT_WITNESS: PASS (if no errors printed above)"
