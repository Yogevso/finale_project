#!/bin/sh
set -eu

LOCKFILE="/app/package-lock.json"
HASHFILE="/app/node_modules/.package-lock.sha256"

ensure_dependencies() {
  if [ ! -f "$LOCKFILE" ]; then
    echo "package-lock.json not found, running npm install"
    npm install --legacy-peer-deps
    return
  fi

  current_hash="$(sha256sum "$LOCKFILE" | awk '{print $1}')"
  installed_hash=""

  if [ -f "$HASHFILE" ]; then
    installed_hash="$(cat "$HASHFILE")"
  fi

  if [ "$current_hash" != "$installed_hash" ]; then
    echo "Dependencies changed, installing npm packages"
    npm install --legacy-peer-deps
    mkdir -p /app/node_modules
    echo "$current_hash" > "$HASHFILE"
  fi
}

ensure_dependencies
exec npm run dev -- --host 0.0.0.0
