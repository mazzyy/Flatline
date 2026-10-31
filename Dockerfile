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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY warden ./warden
COPY fixtures ./fixtures
COPY alembic.ini .
COPY scripts ./scripts
COPY --from=dashboard /src/dist ./dashboard/dist
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PAYPAL_ENVIRONMENT=MOCK
ENV LLM_MODE=mock
EXPOSE 8000
CMD ["uvicorn", "warden.ingest.app:app", "--host", "0.0.0.0", "--port", "8000"]
