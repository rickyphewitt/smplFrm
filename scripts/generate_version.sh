#!/usr/bin/env bash
# Resolves git tag or short hash and writes to VERSION file.
# Usage: ./scripts/generate_version.sh [output_path]
# Default output_path: VERSION (project root)

OUTPUT="${1:-VERSION}"

if ! command -v git &>/dev/null || ! git rev-parse --git-dir &>/dev/null 2>&1; then
    echo "unknown" > "$OUTPUT"
    exit 0
fi

TAG=$(git tag --points-at HEAD | grep -E '^v[0-9]' | head -n 1)

if [ -n "$TAG" ]; then
    echo "$TAG" > "$OUTPUT"
else
    echo "$(git rev-parse --short HEAD)" > "$OUTPUT"
fi
