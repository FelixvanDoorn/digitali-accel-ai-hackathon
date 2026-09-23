#!/usr/bin/env bash
# Deploys the engine to its own Vercel project (default name: digitali-engine) as a Python function.
# Also run by .github/workflows/engine.yml on pull requests (preview) and pushes to main (production).
#
# Usage (from engine/): scripts/deploy_vercel.sh [--preview]
#   --preview                  preview deployment instead of production
#   VERCEL_SCOPE=<team slug>   deploy to a team instead of your personal account
#   PROJECT=<name>             Vercel project name (default: digitali-engine)
#   VERCEL_TOKEN, VERCEL_ORG_ID, VERCEL_PROJECT_ID   for CI, instead of `vercel login` and `vercel link`
# The last line of output is DEPLOYMENT_URL=<url of this deployment>.
#
# One-time setup on the Vercel project (Settings > Environment Variables, Production and Preview):
#   NEBIUS_API_KEY, VISION_MODEL (e.g. openbmb/MiniCPM-V-4_5), ENGINE_API_KEY
# The website's project then needs ENGINE_URL=<production URL> and the same ENGINE_API_KEY.

set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT="${PROJECT:-digitali-engine}"
PROD_FLAG="--prod"
[ "${1:-}" = "--preview" ] && PROD_FLAG=""

vercel() {
  local args=()
  [ -n "${VERCEL_SCOPE:-}" ] && args+=(--scope "$VERCEL_SCOPE")
  [ -n "${VERCEL_TOKEN:-}" ] && args+=(--token "$VERCEL_TOKEN")
  npx --yes vercel@59 ${args[@]+"${args[@]}"} "$@"
}

command -v uv >/dev/null || { echo "Missing 'uv'. Install it with: brew install uv" >&2; exit 1; }
command -v npx >/dev/null || { echo "Missing 'npx'. Install Node.js first." >&2; exit 1; }
if ! whoami_output="$(vercel whoami 2>&1)"; then
  echo "$whoami_output" >&2
  if [ -n "${VERCEL_TOKEN:-}" ]; then
    echo "Vercel rejected VERCEL_TOKEN. Check it is valid and scoped to the account that owns $PROJECT." >&2
  else
    echo "Not logged in to Vercel. Run: npx vercel login" >&2
  fi
  exit 1
fi

cleanup() { rm -rf templates prompts requirements.txt; }
trap cleanup EXIT
# Vercel only uploads engine/, but the engine reads these from the repo root (see app/config.py).
cleanup
cp -R ../templates ../prompts .
uv export --frozen --no-dev --no-hashes --no-emit-project --quiet -o requirements.txt

# In CI, VERCEL_ORG_ID and VERCEL_PROJECT_ID select the project instead of a linked .vercel/ folder.
[ -n "${VERCEL_PROJECT_ID:-}" ] || [ -f .vercel/project.json ] || vercel link --yes --project "$PROJECT"
output="$(vercel deploy $PROD_FLAG --yes 2>&1)" || { echo "$output" >&2; exit 1; }
echo "$output"
url="$(grep -oE "https://$PROJECT-[a-z0-9-]+\.vercel\.app" <<<"$output" | head -n 1 || true)"
echo "DEPLOYMENT_URL=$url"
