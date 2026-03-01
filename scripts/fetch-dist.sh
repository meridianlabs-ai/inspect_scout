#!/usr/bin/env bash
# Fetch LFS dist files using the GitHub LFS batch API.
#
# This script is an escape hatch for users who want to populate the
# dist cache without running `scout view`. It uses the same Python
# resolver that the server uses at startup.
#
# Usage:
#   ./scripts/fetch-dist.sh

set -euo pipefail

usage() {
    echo "Usage: $0"
    echo ""
    echo "Fetch LFS dist files using the GitHub LFS batch API."
    echo ""
    echo "Options:"
    echo "  -h, --help  Show this help message"
}

for arg in "$@"; do
    case "$arg" in
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown argument: $arg"; usage; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

"$REPO_DIR/.venv/bin/python" -c "
from inspect_scout._view.server import resolve_dist_directory
resolve_dist_directory()
"
