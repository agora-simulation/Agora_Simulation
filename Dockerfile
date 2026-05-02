# =============================================================================
# Agora — Multi-Stage Docker Build
# Stage 1: Angular Frontend bauen
# Stage 2: Python Dependencies installieren
# Stage 3: Runtime (FastAPI + Static Frontend)
# =============================================================================

# --- Stage 1: Frontend Build ---
FROM node:22-slim AS frontend-builder

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ .
RUN npx ng build --configuration production


# --- Stage 2: Python Dependencies ---
FROM python:3.12-slim AS backend-builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- Stage 3: Runtime ---
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN addgroup --system agora && adduser --system --ingroup agora agora

WORKDIR /app

# Python dependencies
COPY --from=backend-builder /install /usr/local

# Backend code
COPY --chown=agora:agora app/ ./app/
COPY --chown=agora:agora alembic/ ./alembic/
COPY --chown=agora:agora alembic.ini ./
COPY --chown=agora:agora requirements.txt ./

# Frontend dist (Angular build output)
COPY --from=frontend-builder --chown=agora:agora /frontend/dist/frontend/browser/ ./static/

USER agora

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
