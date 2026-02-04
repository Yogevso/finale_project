#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

open_terminal() {
  local title="$1"
  local workdir="$2"
  local cmd="$3"

  osascript <<EOF
tell application "Terminal"
  activate
  set newWindow to do script "cd ${workdir} && echo '[${title}]' && ${cmd}"
end tell
EOF
}

open_terminal "backend" "$ROOT_DIR" "docker compose up --build backend"
open_terminal "collab" "$ROOT_DIR" "docker compose up --build collab-server"
open_terminal "frontend" "$ROOT_DIR" "docker compose up --build frontend"
