#!/usr/bin/env bash
# Fetch LFS dist files using the GitHub LFS batch API.
#
# This script is an escape hatch for users who want to populate the
# dist cache without running `scout view`. It uses the same Python
# resolver that the server uses at startup.
#
# Usage:
#   ./scripts/fetch-dist.sh
#
# The script:
#   1. Checks if dist/ contains LFS pointer files
#   2. If so, downloads real files to ~/.cache/inspect_scout/dist/
#   3. If dist/ already contains real files, does nothing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$REPO_DIR/src/inspect_scout/_view/dist"

if [[ ! -d "$DIST_DIR" ]]; then
    echo "Error: dist/ directory not found at $DIST_DIR"
    echo "Run 'pnpm build' from src/inspect_scout/_view/frontend/ to build the frontend."
    exit 1
fi

INDEX_HTML="$DIST_DIR/index.html"
if [[ ! -f "$INDEX_HTML" ]]; then
    echo "Error: index.html not found in dist/"
    exit 1
fi

# Check if index.html is an LFS pointer.
if ! head -1 "$INDEX_HTML" | grep -q "^version https://git-lfs.github.com/spec/v1$"; then
    echo "dist/ already contains real files. Nothing to fetch."
    exit 0
fi

echo "dist/ contains LFS pointer files. Downloading real files..."

# Use the Python resolver to populate the cache.
"$REPO_DIR/.venv/bin/python" -c "
from pathlib import Path
from inspect_scout._view._lfs import resolve_dist_directory

repo_dist = Path('$DIST_DIR')
cache_dir = resolve_dist_directory(repo_dist)
print(f'Done. LFS files cached at {cache_dir}')
"
