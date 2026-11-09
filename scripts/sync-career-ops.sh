#!/usr/bin/env bash
# Refresh the vendored career-ops copy from upstream. Usage: sync-career-ops.sh [ref]  (default: main)
set -euo pipefail
REF="${1:-main}"
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$SKILL/career-ops"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git clone --depth 1 --branch "$REF" https://github.com/career-ops-hq/career-ops.git "$TMP/src"
SHA="$(git -C "$TMP/src" rev-parse --short HEAD)"
VER="$(head -1 "$TMP/src/VERSION" | awk '{print $1}')"
mkdir -p "$TMP/out"
git -C "$TMP/src" archive HEAD | tar -x -C "$TMP/out"
rm -rf "$TMP/out/.github" "$TMP/out/tests"
# keep local-only files across the refresh
for keep in .career-ops-data node_modules; do
  [ -e "$DEST/$keep" ] && mv "$DEST/$keep" "$TMP/out/$keep"
done
rm -rf "$DEST"
mv "$TMP/out" "$DEST"
echo "career-ops synced to $VER ($SHA). Update UPSTREAM.md, run 'npm ci' in $DEST if package-lock.json changed, then commit."
