#!/usr/bin/env bash
set -euo pipefail

required_vars=(
  DEPLOY_HOST
  DEPLOY_USER
  DEPLOY_KEY
  DEPLOY_PATH
  GHCR_USERNAME
  GHCR_TOKEN
  BACKEND_IMAGE
  FRONTEND_IMAGE
  COLLAB_SERVER_IMAGE
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "[release] Missing required environment variable: ${var_name}" >&2
    exit 1
  fi
done

REGISTRY="${REGISTRY:-ghcr.io}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE:-.env.prod}"

mkdir -p "${HOME}/.ssh"
key_file="$(mktemp)"
cleanup() {
  rm -f "${key_file}"
}
trap cleanup EXIT

printf '%s\n' "${DEPLOY_KEY}" > "${key_file}"
chmod 600 "${key_file}"

ssh-keyscan -H "${DEPLOY_HOST}" >> "${HOME}/.ssh/known_hosts" 2>/dev/null

ssh -i "${key_file}" -o StrictHostKeyChecking=yes "${DEPLOY_USER}@${DEPLOY_HOST}" \
  "mkdir -p '${DEPLOY_PATH}'"

scp -i "${key_file}" -o StrictHostKeyChecking=yes \
  "${COMPOSE_FILE}" \
  "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/${COMPOSE_FILE}"

ssh -i "${key_file}" -o StrictHostKeyChecking=yes "${DEPLOY_USER}@${DEPLOY_HOST}" \
  "export REGISTRY='${REGISTRY}' \
   GHCR_USERNAME='${GHCR_USERNAME}' \
   GHCR_TOKEN='${GHCR_TOKEN}' \
   DEPLOY_PATH='${DEPLOY_PATH}' \
   COMPOSE_FILE='${COMPOSE_FILE}' \
   COMPOSE_ENV_FILE='${COMPOSE_ENV_FILE}' \
   BACKEND_IMAGE='${BACKEND_IMAGE}' \
   FRONTEND_IMAGE='${FRONTEND_IMAGE}' \
   COLLAB_SERVER_IMAGE='${COLLAB_SERVER_IMAGE}' ; \
   bash -s" <<'REMOTE'
set -euo pipefail

cd "${DEPLOY_PATH}"

if [[ ! -f "${COMPOSE_ENV_FILE}" ]]; then
  echo "[release] Missing compose env file: ${DEPLOY_PATH}/${COMPOSE_ENV_FILE}" >&2
  exit 1
fi

printf '%s\n' "${GHCR_TOKEN}" | docker login "${REGISTRY}" -u "${GHCR_USERNAME}" --password-stdin

export BACKEND_IMAGE FRONTEND_IMAGE COLLAB_SERVER_IMAGE

docker compose -f "${COMPOSE_FILE}" --env-file "${COMPOSE_ENV_FILE}" pull redis backend frontend collab-server
docker compose -f "${COMPOSE_FILE}" --env-file "${COMPOSE_ENV_FILE}" up -d --no-build redis backend frontend collab-server

curl -fsS http://127.0.0.1:8001/ready >/dev/null
curl -fsS http://127.0.0.1:8080/ >/dev/null
curl -fsS http://127.0.0.1:8003/health >/dev/null

docker compose -f "${COMPOSE_FILE}" --env-file "${COMPOSE_ENV_FILE}" ps
docker image prune -f >/dev/null || true
REMOTE
