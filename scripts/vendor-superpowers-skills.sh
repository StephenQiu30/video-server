#!/usr/bin/env bash
# Vendor obra/superpowers skills into the repo-native skills directory only.
# Does not use .agents/ — output goes directly to .claude/skills/ (or override DEST).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-$ROOT/.claude/skills}"
REPO="https://github.com/obra/superpowers.git"
SKILLS=(
  using-superpowers
  writing-plans
  test-driven-development
  executing-plans
  systematic-debugging
  verification-before-completion
  requesting-code-review
)

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

git clone --depth 1 "$REPO" "$tmpdir/superpowers"

mkdir -p "$DEST"
for skill in "${SKILLS[@]}"; do
  src="$tmpdir/superpowers/skills/$skill"
  if [[ ! -d "$src" ]]; then
    echo "missing skill in upstream: $skill" >&2
    exit 1
  fi
  rm -rf "$DEST/$skill"
  cp -R "$src" "$DEST/$skill"
  echo "vendored $skill -> $DEST/$skill"
done

echo "Done. Superpowers skills are in $DEST (no .agents copy required)."
