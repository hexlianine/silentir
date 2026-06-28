#!/usr/bin/env bash
#
# install-skill.sh — Install the `silentir` agent skill onto this machine.
#
# Copies (or symlinks) skills/silentir/ into ~/.agents/skills/<name>/ and
# creates a ~/.claude/skills/<name> symlink so Claude Code, Codex, Copilot
# CLI, and Gemini CLI all pick it up. The YAML `name:` field in the
# installed SKILL.md is rewritten to match the requested name so the slash
# command matches the install name (e.g. `--name video-notes` -> `/video-notes`).
#
# Usage:
#   bash scripts/install-skill.sh                       # install as `silentir`
#   bash scripts/install-skill.sh --name video-notes    # install under a custom slash-command name
#   bash scripts/install-skill.sh --symlink             # symlink source instead of copy (dev mode)
#   bash scripts/install-skill.sh --force               # overwrite an existing install
#   bash scripts/install-skill.sh --uninstall [--name N] # remove a previously installed skill
#   bash scripts/install-skill.sh --help

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." &>/dev/null && pwd)"
SKILL_SRC="$REPO_ROOT/skills/silentir"

DEFAULT_NAME="silentir"
NAME="$DEFAULT_NAME"
AGENTS_ROOT="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"
CLAUDE_ROOT="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
MODE="copy"
FORCE=0
UNINSTALL=0

usage() {
  # Print the leading comment block (skip the shebang) as help text.
  awk '
    NR == 1 && /^#!/ { next }
    /^#/ { sub(/^# ?/, ""); print; next }
    { exit }
  ' "${BASH_SOURCE[0]}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)
      NAME="${2:?--name requires a value}"
      shift 2
      ;;
    --name=*)
      NAME="${1#--name=}"
      shift
      ;;
    --symlink)
      MODE="symlink"
      shift
      ;;
    --copy)
      MODE="copy"
      shift
      ;;
    --force | -f)
      FORCE=1
      shift
      ;;
    --uninstall)
      UNINSTALL=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! [[ "$NAME" =~ ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ ]]; then
  echo "error: skill name must match [a-zA-Z0-9][a-zA-Z0-9_-]* (got: $NAME)" >&2
  exit 2
fi

AGENTS_TARGET="$AGENTS_ROOT/$NAME"
CLAUDE_LINK="$CLAUDE_ROOT/$NAME"

if [[ $UNINSTALL -eq 1 ]]; then
  removed=0
  if [[ -L "$CLAUDE_LINK" || -e "$CLAUDE_LINK" ]]; then
    rm -f "$CLAUDE_LINK"
    echo "removed: $CLAUDE_LINK"
    removed=1
  fi
  if [[ -e "$AGENTS_TARGET" || -L "$AGENTS_TARGET" ]]; then
    rm -rf "$AGENTS_TARGET"
    echo "removed: $AGENTS_TARGET"
    removed=1
  fi
  if [[ $removed -eq 0 ]]; then
    echo "nothing to remove for skill name '$NAME'"
  fi
  exit 0
fi

if [[ ! -f "$SKILL_SRC/SKILL.md" || ! -f "$SKILL_SRC/handler.py" ]]; then
  echo "error: expected SKILL.md and handler.py inside $SKILL_SRC" >&2
  exit 1
fi

if [[ -e "$AGENTS_TARGET" || -L "$AGENTS_TARGET" ]]; then
  if [[ $FORCE -eq 1 ]]; then
    rm -rf "$AGENTS_TARGET"
  else
    echo "error: $AGENTS_TARGET already exists. Re-run with --force to overwrite, or --uninstall first." >&2
    exit 1
  fi
fi

mkdir -p "$AGENTS_ROOT" "$CLAUDE_ROOT"

case "$MODE" in
  symlink)
    ln -s "$SKILL_SRC" "$AGENTS_TARGET"
    echo "linked:  $AGENTS_TARGET -> $SKILL_SRC"
    ;;
  copy)
    mkdir -p "$AGENTS_TARGET"
    # Copy only the skill payload — install-skill.sh deliberately stays out
    # of the installed directory; re-run it from this repo to update or remove.
    cp "$SKILL_SRC/SKILL.md" "$AGENTS_TARGET/SKILL.md"
    cp "$SKILL_SRC/handler.py" "$AGENTS_TARGET/handler.py"
    echo "copied:  $SKILL_SRC -> $AGENTS_TARGET"
    ;;
esac

# Rewrite the YAML `name:` field so the installed slash command matches --name.
# Symlink installs skip this (would mutate the source); document the gotcha.
if [[ "$MODE" == "copy" && "$NAME" != "$DEFAULT_NAME" ]]; then
  SKILL_FILE="$AGENTS_TARGET/SKILL.md"
  # Replace only the first `name:` line inside the YAML frontmatter.
  python3 - "$SKILL_FILE" "$NAME" <<'PYEOF'
import sys, pathlib, re
path = pathlib.Path(sys.argv[1])
new_name = sys.argv[2]
text = path.read_text()
parts = text.split("---\n", 2)
if len(parts) < 3 or parts[0] != "":
    sys.exit("could not locate YAML frontmatter in " + str(path))
front = re.sub(r"^name:.*$", f"name: {new_name}", parts[1], count=1, flags=re.M)
path.write_text("---\n" + front + "---\n" + parts[2])
PYEOF
  echo "renamed: SKILL.md name field -> $NAME"
elif [[ "$MODE" == "symlink" && "$NAME" != "$DEFAULT_NAME" ]]; then
  echo "warning: --symlink keeps SKILL.md's name field as '$DEFAULT_NAME'." >&2
  echo "         The slash command exposed will be /$DEFAULT_NAME, not /$NAME." >&2
  echo "         Use --copy if you want the slash command renamed." >&2
fi

# Mirror into ~/.claude/skills/ via symlink (matches the existing convention here).
if [[ -L "$CLAUDE_LINK" || -e "$CLAUDE_LINK" ]]; then
  rm -f "$CLAUDE_LINK"
fi
ln -s "$AGENTS_TARGET" "$CLAUDE_LINK"
echo "linked:  $CLAUDE_LINK -> $AGENTS_TARGET"

echo
echo "Installed. Invoke with:  /$NAME source=\"<URL or local file path>\""
echo "Requires \`uvx\` on PATH (https://docs.astral.sh/uv/getting-started/installation/)."
