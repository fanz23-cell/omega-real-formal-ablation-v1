#!/usr/bin/env bash
# Level 1: no API key needed. Verifies every hash in MANIFEST.sha256 matches the actual
# packaged files -- proves nothing was silently altered after the freeze.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f MANIFEST.sha256 ]; then
    echo "MANIFEST.sha256 not found -- run this from an extracted release package." >&2
    exit 1
fi

echo "=== Verifying MANIFEST.sha256 ==="
sha256sum -c MANIFEST.sha256
echo
echo "VERIFY_PACKAGE: PASS"
