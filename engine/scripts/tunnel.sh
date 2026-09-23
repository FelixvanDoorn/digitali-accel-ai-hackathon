#!/usr/bin/env bash
# Runs the engine on this laptop and exposes it through a tunnel, so the website on Vercel can call it.
# If the VERCEL_* keys are set in engine/.env, it also sets ENGINE_URL and ENGINE_API_KEY on the Vercel
# project and redeploys it (the tunnel URL changes on every run).
#
# Usage (from engine/): scripts/tunnel.sh
#   TUNNEL=ssh          (default) SSH tunnel through localhost.run; nothing to install
#   TUNNEL=cloudflared  Cloudflare quick tunnel (brew install cloudflared)
#   TUNNEL=none PUBLIC_URL=https://...  you run your own tunnel (e.g. ssh -R to your own server)
#   PORT=8000           local port for the engine
# Ctrl+C stops the engine and the tunnel.

set -euo pipefail

cd "$(dirname "$0")/.."
PORT="${PORT:-8000}"
TUNNEL="${TUNNEL:-ssh}"
LOG_DIR="$(mktemp -d)"

# Read single keys from .env; sourcing the whole file would mangle JSON values like ALLOWED_ORIGINS.
env_value() {
  [ -f .env ] || return 0
  { grep -E "^$1=" .env || true; } | tail -n 1 | cut -d= -f2- | sed -e "s/^[\"']//" -e "s/[\"']$//"
}

need() {
  command -v "$1" >/dev/null || { echo "Missing '$1'. Install it with: brew install $1" >&2; exit 1; }
}
need uv
need curl
need jq
case "$TUNNEL" in
  ssh) need ssh ;;
  cloudflared) need cloudflared ;;
  none) [ -n "${PUBLIC_URL:-}" ] || { echo "TUNNEL=none needs PUBLIC_URL=<your tunnel's https URL>." >&2; exit 1; } ;;
  *) echo "Unknown TUNNEL=$TUNNEL (use ssh, cloudflared or none)." >&2; exit 1 ;;
esac

ENGINE_API_KEY="$(env_value ENGINE_API_KEY)"
if [ -z "$ENGINE_API_KEY" ]; then
  echo "ENGINE_API_KEY is not set in engine/.env. Without it anyone with the tunnel URL can use your" >&2
  echo "Token Factory credits. Add one, e.g.: echo \"ENGINE_API_KEY=\$(openssl rand -hex 32)\" >> .env" >&2
  exit 1
fi
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

URL="${PUBLIC_URL:-}"
if [ "$TUNNEL" != none ]; then
  echo "Opening $TUNNEL tunnel..."
  if [ "$TUNNEL" = ssh ]; then
    ssh -tt -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -o ExitOnForwardFailure=yes \
      -R "80:localhost:$PORT" nokey@localhost.run >"$LOG_DIR/tunnel.log" 2>&1 &
    PATTERN='https://[a-z0-9.-]+\.(lhr\.life|localhost\.run)'
  else
    cloudflared tunnel --no-autoupdate --url "http://localhost:$PORT" >"$LOG_DIR/tunnel.log" 2>&1 &
    PATTERN='https://[a-z0-9-]+\.trycloudflare\.com'
  fi
  TUNNEL_PID=$!
  for _ in $(seq 60); do
    URL="$(grep -oE "$PATTERN" "$LOG_DIR/tunnel.log" | grep -v 'admin\.localhost\.run' | head -n 1 || true)"
    [ -n "$URL" ] && break
    kill -0 "$TUNNEL_PID" 2>/dev/null || { cat "$LOG_DIR/tunnel.log" >&2; exit 1; }
    sleep 0.5
  done
  [ -n "$URL" ] || { echo "Tunnel did not report a URL. Log: $LOG_DIR/tunnel.log" >&2; exit 1; }
fi
URL="${URL%/}"

# A new hostname can take a few seconds to resolve.
for _ in $(seq 30); do
  curl -sf -o /dev/null "$URL/health" && break
  sleep 1
done
echo "Engine is public at: $URL"
curl -s "$URL/health" | jq -c . || echo "(health check through the tunnel failed; see $LOG_DIR/tunnel.log)"

VERCEL_TOKEN="$(env_value VERCEL_TOKEN)"
VERCEL_PROJECT_ID="$(env_value VERCEL_PROJECT_ID)"
VERCEL_TEAM_ID="$(env_value VERCEL_TEAM_ID)"
VERCEL_DEPLOY_HOOK="$(env_value VERCEL_DEPLOY_HOOK)"

set_vercel_env() {
  curl -sf -X POST \
    "https://api.vercel.com/v10/projects/$VERCEL_PROJECT_ID/env?upsert=true${VERCEL_TEAM_ID:+&teamId=$VERCEL_TEAM_ID}" \
    -H "Authorization: Bearer $VERCEL_TOKEN" -H "Content-Type: application/json" \
    -d "$(jq -n --arg key "$1" --arg value "$2" --arg type "$3" \
      '{key: $key, value: $value, type: $type, target: ["production", "preview"]}')" \
    >/dev/null || { echo "Vercel rejected $1. Check VERCEL_TOKEN, VERCEL_PROJECT_ID and VERCEL_TEAM_ID." >&2; exit 1; }
}

if [ -n "$VERCEL_TOKEN" ] && [ -n "$VERCEL_PROJECT_ID" ]; then
  echo "Setting ENGINE_URL and ENGINE_API_KEY on Vercel..."
  set_vercel_env ENGINE_URL "$URL" plain
  set_vercel_env ENGINE_API_KEY "$ENGINE_API_KEY" encrypted
  if [ -n "$VERCEL_DEPLOY_HOOK" ]; then
    curl -sf -X POST "$VERCEL_DEPLOY_HOOK" >/dev/null \
      && echo "Redeploy triggered; the site uses this engine once the build finishes (about a minute)."
  else
    echo "VERCEL_DEPLOY_HOOK is not set: redeploy the site yourself so it picks up the new URL."
  fi
else
  echo "VERCEL_* keys not set in engine/.env. On the Vercel project, set ENGINE_URL=$URL and"
  echo "ENGINE_API_KEY (same value as in engine/.env), then redeploy."
fi

echo "Engine log: $LOG_DIR/engine.log. Press Ctrl+C to stop."
wait "$ENGINE_PID"
