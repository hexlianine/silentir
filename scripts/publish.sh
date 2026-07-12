#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# publish.sh — build and publish silentir to PyPI with secure token handling
#
# Token lookup order:
#   1. .pypi-token file in the project root (recommended; gitignored)
#   2. PYPI_TOKEN environment variable
#   3. UV_PUBLISH_TOKEN environment variable
#
# Usage:
#   ./scripts/publish.sh               # build + publish
#   ./scripts/publish.sh --build-only  # only build, skip publish
#   ./scripts/publish.sh --dry-run     # build + check what would be published
# ---------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

# ── token resolution ────────────────────────────────────────────────────────
TOKEN=""

# 1) .pypi-token file (most secure — never in shell history or env)
TOKEN_FILE="$PROJECT_DIR/.pypi-token"
if [[ -f "$TOKEN_FILE" ]]; then
    TOKEN="$(<"$TOKEN_FILE")"
    # Strip trailing newline
    TOKEN="${TOKEN%$'\n'}"
    echo "[publish] Using token from .pypi-token"
fi

# 2) PYPI_TOKEN env var
if [[ -z "$TOKEN" ]] && [[ -n "${PYPI_TOKEN:-}" ]]; then
    TOKEN="$PYPI_TOKEN"
    echo "[publish] Using token from PYPI_TOKEN env var"
fi

# 3) UV_PUBLISH_TOKEN env var (uv's native variable)
if [[ -z "$TOKEN" ]] && [[ -n "${UV_PUBLISH_TOKEN:-}" ]]; then
    TOKEN="$UV_PUBLISH_TOKEN"
    echo "[publish] Using token from UV_PUBLISH_TOKEN env var"
fi

# ── arg parsing ─────────────────────────────────────────────────────────────
BUILD_ONLY=false
DRY_RUN=false

for arg in "$@"; do
    case "$arg" in
        --build-only) BUILD_ONLY=true ;;
        --dry-run)    DRY_RUN=true ;;
        --help|-h)
            echo "Usage: $0 [--build-only] [--dry-run]"
            echo ""
            echo "  --build-only   Build dist artifacts, skip publish"
            echo "  --dry-run      Build + check publish without uploading"
            echo ""
            echo "Place your PyPI token in \`.pypi-token\` (gitignored) or set"
            echo "PYPI_TOKEN / UV_PUBLISH_TOKEN in your environment."
            exit 0
            ;;
        *)
            echo "Unknown flag: $arg" >&2
            exit 1
            ;;
    esac
done

# ── build ───────────────────────────────────────────────────────────────────
echo "[publish] Building..."
rm -rf dist/
uv build
echo "[publish] Build complete:"
ls -lh dist/

# ── publish ──────────────────────────────────────────────────────────────────
if $BUILD_ONLY; then
    echo "[publish] --build-only set, skipping publish."
    exit 0
fi

if [[ -z "$TOKEN" ]]; then
    cat >&2 <<'EOF'
[publish] ERROR: No PyPI token found.
  Provide it one of these ways:
    1. echo "pypi-xxxxxxxx" > .pypi-token   (recommended, gitignored)
    2. export PYPI_TOKEN=pypi-xxxxxxxx
    3. export UV_PUBLISH_TOKEN=pypi-xxxxxxxx
EOF
    exit 1
fi

if $DRY_RUN; then
    echo "[publish] Dry run — checking what would be published..."
    UV_PUBLISH_TOKEN="$TOKEN" uv publish --dry-run
    echo "[publish] Dry run OK — no errors."
else
    echo "[publish] Publishing to PyPI..."
    UV_PUBLISH_TOKEN="$TOKEN" uv publish
    echo "[publish] Done! https://pypi.org/project/silentir/"
fi
