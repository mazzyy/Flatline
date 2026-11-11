#!/bin/sh
# Container entry point. By default it runs the API (and the dashboard it serves).
# With RUN_SHOP=true it also starts the demo shop inside the same container and
# serves it under /shop, so the whole demo is one container behind one port:
#   /        the landing page and the dashboard
#   /shop    Lumen Coffee Co., the demo shop
set -e
PORT="${PORT:-8000}"
if [ "${RUN_SHOP:-false}" = "true" ]; then
  # Worked out before the shop's own PORT is set: on one line the shell would
  # put the shop's port into this address and the shop would talk to itself.
  API_URL="http://127.0.0.1:${PORT}"
  (
    cd /app/demo-shop
    PORT=3000 SHOP_BASE_PATH=/shop FLATLINE_API_URL="$API_URL" FLATLINE_PUBLIC_URL=/ node server.js
  ) &
  export SHOP_INTERNAL_URL="http://127.0.0.1:3000"
  export SHOP_PUBLIC_URL="/shop"
fi
exec uvicorn flatline.ingest.app:app --host 0.0.0.0 --port "${PORT}"
