#!/usr/bin/env bash
# Runs the engine on this laptop and exposes it through a Cloudflare quick tunnel, so the deployed
# Vercel frontend can call it. If the VERCEL_* keys are set in engine/.env, it also points the
# frontend's VITE_ENGINE_URL at the tunnel and redeploys it (the tunnel URL changes on every run).
#
# Usage (from engine/): scripts/tunnel.sh
# Ctrl+C stops the engine and the tunnel. While it runs, anyone with the URL can use the engine.

set -euo pipefail

cd "$(dirname "$0")/.."
PORT="${PORT:-8000}"
LOG_DIR="$(mktemp -d)"

# Read single keys from .env; sourcing the whole file would mangle JSON values like ALLOWED_ORIGINS.
env_value() {
  [ -f .env ] || return 0
  grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- | sed -e "s/^[\"']//" -e "s/[\"']$//"
}

for cmd in cloudflared uv curl jq; do
  if ! command -v "$cmd" >/dev/null; then
    echo "Missing '$cmd'. Install it with: brew install $cmd" >&2
    exit 1
  fi
done
if curl -s -o /dev/null "http://localhost:$PORT/health"; then
  echo "Something is already running on port $PORT. Stop it, or run with PORT=<other port>." >&2
  exit 1
fi

cleanup() {
  trap - EXIT INT TERM
  echo
  echo "Stopping engine and tunnel."
  kill "${ENGINE_PID:-}" "${TUNNEL_PID:-}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting engine on port $PORT..."
uv run uvicorn app.main:app --port "$PORT" >"$LOG_DIR/engine.log" 2>&1 &
ENGINE_PID=$!
for _ in $(seq 60); do
  curl -s -o /dev/null "http://localhost:$PORT/health" && break
  kill -0 "$ENGINE_PID" 2>/dev/null || { cat "$LOG_DIR/engine.log" >&2; exit 1; }
  sleep 0.5
done

echo "Opening tunnel..."
cloudflared tunnel --no-autoupdate --url "http://localhost:$PORT" >"$LOG_DIR/tunnel.log" 2>&1 &
TUNNEL_PID=$!
URL=""
for _ in $(seq 60); do
  URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG_DIR/tunnel.log" | head -n 1 || true)"
  [ -n "$URL" ] && break
  kill -0 "$TUNNEL_PID" 2>/dev/null || { cat "$LOG_DIR/tunnel.log" >&2; exit 1; }
  sleep 0.5
done
[ -n "$URL" ] || { echo "Tunnel did not report a URL. Log: $LOG_DIR/tunnel.log" >&2; exit 1; }

# The new hostname can take a few seconds to resolve.
for _ in $(seq 30); do
  curl -sf -o /dev/null "$URL/health" && break
  sleep 1
done
echo "Engine is public at: $URL"
curl -s "$URL/health" | jq -c . || true

VERCEL_TOKEN="$(env_value VERCEL_TOKEN)"
VERCEL_PROJECT_ID="$(env_value VERCEL_PROJECT_ID)"
VERCEL_TEAM_ID="$(env_value VERCEL_TEAM_ID)"
VERCEL_DEPLOY_HOOK="$(env_value VERCEL_DEPLOY_HOOK)"

if [ -n "$VERCEL_TOKEN" ] && [ -n "$VERCEL_PROJECT_ID" ]; then
  echo "Setting VITE_ENGINE_URL on Vercel..."
  curl -sf -X POST \
    "https://api.vercel.com/v10/projects/$VERCEL_PROJECT_ID/env?upsert=true${VERCEL_TEAM_ID:+&teamId=$VERCEL_TEAM_ID}" \
    -H "Authorization: Bearer $VERCEL_TOKEN" -H "Content-Type: application/json" \
    -d "$(jq -n --arg url "$URL" '{key: "VITE_ENGINE_URL", value: $url, type: "plain", target: ["production", "preview"]}')" \
    >/dev/null || { echo "Vercel rejected the update. Check VERCEL_TOKEN, VERCEL_PROJECT_ID and VERCEL_TEAM_ID." >&2; exit 1; }

  if [ -n "$VERCEL_DEPLOY_HOOK" ]; then
    curl -sf -X POST "$VERCEL_DEPLOY_HOOK" >/dev/null && echo "Redeploy triggered; the site uses the tunnel once the build finishes (about a minute)."
  else
    echo "VERCEL_DEPLOY_HOOK is not set: redeploy the frontend yourself so it picks up the new URL."
  fi
else
  echo "VERCEL_* keys not set in engine/.env: set VITE_ENGINE_URL=$URL on the frontend and redeploy."
fi

echo "Make sure the site's domain is allowed: ALLOWED_ORIGINS or ALLOWED_ORIGIN_REGEX in engine/.env."
echo "Engine log: $LOG_DIR/engine.log. Press Ctrl+C to stop."
wait "$ENGINE_PID"
