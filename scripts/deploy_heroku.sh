#!/usr/bin/env bash
# Deploy Flatline to Heroku as one container (landing page and dashboard at /, shop at /shop).
#
#   scripts/deploy_heroku.sh <app-name>
#
# Needs the Heroku CLI, logged in (heroku login), and a clean git tree: Heroku builds what
# is committed, not what is on disk. Secrets are read from .env and sent straight to
# Heroku's config; none of them is printed. Safe to run again: it updates the same app.
set -euo pipefail

APP="${1:-}"
[ -n "$APP" ] || { echo "usage: scripts/deploy_heroku.sh <app-name>"; exit 1; }
cd "$(dirname "$0")/.."
[ -f .env ] || { echo ".env not found. Copy .env.example to .env and fill in the sandbox keys."; exit 1; }
command -v heroku >/dev/null || { echo "Heroku CLI not found. Install it: brew tap heroku/brew && brew install heroku"; exit 1; }
heroku auth:whoami >/dev/null 2>&1 || { echo "Not logged in to Heroku. Run: heroku login"; exit 1; }
if [ -n "$(git status --porcelain)" ]; then
  echo "There are uncommitted changes. Heroku deploys the last commit, so commit first."; exit 1
fi

# Read one value from .env without printing it.
val() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' || true; }

echo "1/5 app"
if heroku apps:info -a "$APP" >/dev/null 2>&1; then
  heroku stack:set container -a "$APP" >/dev/null
else
  heroku create "$APP" --stack container >/dev/null
fi
URL="$(heroku apps:info -a "$APP" --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["app"]["web_url"].rstrip("/"))')"

echo "2/5 database"
if ! heroku config:get DATABASE_URL -a "$APP" | grep -q .; then
  heroku addons:create heroku-postgresql:essential-0 -a "$APP" --wait >/dev/null
fi

echo "3/5 settings"
SETTINGS=(
  RUN_SHOP=true RUN_WORKERS=true DEMO_MODE=true VERIFY_MINUTES=1
  PAYPAL_ENVIRONMENT=SANDBOX LLM_MODE=live "APP_BASE_URL=$URL"
)
for key in PAYPAL_CLIENT_ID PAYPAL_CLIENT_SECRET PAYPAL_WEBHOOK_ID PAYPAL_SANDBOX_PLAN_ID PAYPAL_SANDBOX_PRODUCT_ID \
           GEMINI_API_KEY MODEL_FAST MODEL_REASONING DASHBOARD_PASSCODE INJECT_TOKEN \
           AZURE_API_KEY AZURE_API_BASE AZURE_API_VERSION; do
  value="$(val "$key")"
  if [ -n "$value" ]; then SETTINGS+=("$key=$value"); else echo "    (no $key in .env, skipped)"; fi
done
# A local Ollama model can not be reached from Heroku; keep only hosted fallbacks.
fallbacks="$(val MODEL_FALLBACKS | tr ',' '\n' | grep -v '^ollama' | paste -sd, - || true)"
[ -n "$fallbacks" ] && SETTINGS+=("MODEL_FALLBACKS=$fallbacks")
for required in PAYPAL_CLIENT_ID PAYPAL_CLIENT_SECRET; do
  [ -n "$(val "$required")" ] || { echo "$required is empty in .env. The sandbox needs it."; exit 1; }
done
heroku config:set -a "$APP" "${SETTINGS[@]}" >/dev/null

echo "4/5 build and release (this takes a few minutes)"
heroku git:remote -a "$APP" >/dev/null
git push heroku HEAD:main

echo "5/5 check"
for _ in $(seq 1 30); do
  if curl -sf "$URL/healthz" >/dev/null; then break; fi
  sleep 5
done
curl -sf "$URL/healthz" && echo
echo
echo "Live:      $URL"
echo "Shop:      $URL/shop"
echo "Webhook:   set the PayPal sandbox webhook to $URL/webhooks/paypal"
echo "Logs:      heroku logs --tail -a $APP"
echo "Full test: python scripts/live_check.py --url $URL"
