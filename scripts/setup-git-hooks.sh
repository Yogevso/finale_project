#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

git config core.hooksPath .githooks
chmod +x .githooks/pre-push

echo "Git hooks path set to .githooks"
echo "pre-push hook is executable"
echo "You can bypass once with: SKIP_PRE_PUSH=1 git push"
