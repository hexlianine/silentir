#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# publish.sh — build and publish silentir to PyPI with secure token handling
#
# Token lookup order:
#   1. .pypi-token file in the project root (gitignored)
#   2. PYPI_TOKEN environment variable
#   3. UV_PUBLISH_TOKEN environment variable
#   4. Interactive prompt (input hidden, never in history or on disk)
#
# Usage:
#   ./scripts/publish.sh                 # build + publish
#   ./scripts/publish.sh --save-token    # securely save token to .pypi-token
#   ./scripts/publish.sh --build-only    # only build, skip publish
#   ./scripts/publish.sh --dry-run       # build + check without uploading
# ---------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TOKEN_FILE="$PROJECT_DIR/.pypi-token"

cd "$PROJECT_DIR"

# ── secure token input ──────────────────────────────────────────────────────
# Reads a PyPI token from the terminal without echoing it to screen.
# The token NEVER appears in command-line arguments, shell history, or ps output.
_secure_read_token() {
    local prompt="$1"
    local token
    # Use /dev/tty to read directly from the terminal even if stdin is piped
    read -r -s -p "$prompt" token < /dev/tty
    echo "" > /dev/tty  # newline after hidden input
    printf '%s' "$token"
}

# ── save-token mode ─────────────────────────────────────────────────────────
if [[ "${1:-}" == "--save-token" ]]; then
    echo "Enter your PyPI token (input will be hidden):"
    TOKEN="$(_secure_read_token "Token: ")"

    if [[ -z "$TOKEN" ]]; then
        echo "ERROR: No token entered." >&2
        exit 1
    fi

    printf '%s' "$TOKEN" > "$TOKEN_FILE"
    chmod 600 "$TOKEN_FILE"
    echo "[publish] Token saved to .pypi-token (permissions: 600, gitignored)"
    exit 0
fi

# ── token resolution ────────────────────────────────────────────────────────
TOKEN=""

# 1) .pypi-token file (most secure — never in shell history or env)
if [[ -f "$TOKEN_FILE" ]]; then
    TOKEN="$(<"$TOKEN_FILE")"
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
            echo "Usage: $0 [--save-token] [--build-only] [--dry-run]"
            echo ""
            echo "  --save-token   Securely save a PyPI token to .pypi-token"
            echo "  --build-only   Build dist artifacts, skip publish"
            echo "  --dry-run      Build + check publish without uploading"
            echo ""
            echo "Token lookup order:"
            echo "  1) .pypi-token file (save with --save-token, gitignored)"
            echo "  2) PYPI_TOKEN env var"
            echo "  3) UV_PUBLISH_TOKEN env var"
            echo "  4) Interactive prompt (input hidden, never stored)"
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

# 4) Interactive fallback — prompt user securely (input hidden, never stored)
if [[ -z "$TOKEN" ]]; then
    echo ""
    echo "No token found in .pypi-token, PYPI_TOKEN, or UV_PUBLISH_TOKEN."
    echo "Enter your PyPI token to publish (input will be hidden):"
    TOKEN="$(_secure_read_token "Token: ")"

    if [[ -z "$TOKEN" ]]; then
        echo "ERROR: No token provided. Publish aborted." >&2
        echo "  Hint: run \`$0 --save-token\` to save your token for next time." >&2
        exit 1
    fi
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
