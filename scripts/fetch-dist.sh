#!/usr/bin/env bash
# Fetch LFS dist files using the GitHub LFS batch API.
#
# This script is an escape hatch for users who want to populate the
# dist cache without running `scout view`. It uses the same Python
# resolver that the server uses at startup.
#
# Usage:
#   ./scripts/fetch-dist.sh [--force-cache]

set -euo pipefail

FORCE_CACHE=False
for arg in "$@"; do
    case "$arg" in
        --force-cache) FORCE_CACHE=True ;;
        *) echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$REPO_DIR/src/inspect_scout/_view/dist"

"$REPO_DIR/.venv/bin/python" -c "
from pathlib import Path
from inspect_scout._util.appdirs import scout_cache_dir
from inspect_scout._lfs import resolve_lfs_directory

source = Path('$DIST_DIR')
result = resolve_lfs_directory(
    source,
    cache_dir=scout_cache_dir('dist'),
    repo_url='https://github.com/meridianlabs-ai/inspect_scout.git',
    force_cache=$FORCE_CACHE,
)
if result == source:
    print('dist/ already contains real files. Nothing to fetch.')
else:
    print(f'Done. LFS files cached at {result}')
"
