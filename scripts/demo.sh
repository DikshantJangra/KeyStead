#!/usr/bin/env bash
# One command: init, set secret, register, run the gate.
#   SWITCH_URL=http://localhost:8000 KEYSTEAD_REG_TOKEN=... ./scripts/demo.sh
# CLOUDFLARE_TOKEN may be set to skip the hidden prompt (it is read from the env, never echoed).
set -euo pipefail
cd "$(dirname "$0")/.."

command -v uv >/dev/null || { echo "install uv: https://docs.astral.sh/uv/" >&2; exit 1; }
uv sync --quiet

[ -f .env ] || cp .env.example .env
uv run keystead init

set -a; . ./.env; set +a
: "${SWITCH_URL:?set SWITCH_URL in .env}"
code=$(curl -s -o /dev/null -w '%{http_code}' "$SWITCH_URL/health" || true)
[ "$code" = 200 ] || { echo "GET $SWITCH_URL/health returned $code (401 = right host, wrong path). Is Switch running?" >&2; exit 1; }

if ! uv run keystead secret list | grep -qx cloudflare_token; then
  if [ -n "${CLOUDFLARE_TOKEN:-}" ]; then
    printf '%s\n' "$CLOUDFLARE_TOKEN" | uv run keystead secret set cloudflare_token
  else
    uv run keystead secret set cloudflare_token
  fi
fi

if [ ! -f "${KEYSTEAD_DATA_DIR:-./data}/agent.json" ]; then
  : "${KEYSTEAD_REG_TOKEN:?set KEYSTEAD_REG_TOKEN (the client Switch registration token) in .env}"
  uv run keystead register
  echo
  echo "Now add @keystead to the room from Switch Console (or create the room from"
  echo "templates/keystead-room.template.yaml), then press Enter."
  read -r _
fi

exec uv run keystead run
