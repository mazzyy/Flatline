FROM node:20-alpine AS dashboard
WORKDIR /src
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci
COPY dashboard/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates nodejs npm \
    && rm -rf /var/lib/apt/lists/*
# requirements-live.txt pulls in requirements.txt plus the live model stack
# (LiteLLM, MCP); mock mode never imports them.
COPY requirements.txt requirements-live.txt ./
RUN pip install --no-cache-dir -r requirements-live.txt
COPY flatline ./flatline
COPY fixtures ./fixtures
COPY alembic.ini .
COPY scripts ./scripts
# The demo shop, for one-container hosting (RUN_SHOP=true). Compose runs it separately.
COPY demo-shop/package.json ./demo-shop/package.json
RUN cd demo-shop && npm install --omit=dev --no-audit --no-fund
COPY demo-shop ./demo-shop
COPY --from=dashboard /src/dist ./dashboard/dist
# Download the PayPal MCP server at build time; this run exits on purpose.
RUN npx -y @paypal/mcp@1.8.1 --tools=none >/dev/null 2>&1 || true
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PAYPAL_ENVIRONMENT=MOCK
ENV LLM_MODE=mock
EXPOSE 8000
# Render passes PORT; locally it is 8000.
CMD ["sh", "scripts/start.sh"]
