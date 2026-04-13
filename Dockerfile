# --- Stage 1: Build Vue Frontend with pnpm ---
FROM node:22-slim AS frontend-builder

# Enable pnpm via Corepack
RUN corepack enable && corepack prepare pnpm@10.2.0 --activate

WORKDIR /frontend

# Copy lockfile first for better layer caching
COPY frontend/pnpm-lock.yaml frontend/package.json ./
RUN pnpm install --no-frozen-lockfile

COPY frontend/ ./
RUN pnpm run build

# --- Stage 2: Setup FastAPI Backend ---
FROM ghcr.io/astral-sh/uv:alpine3.22
ENV UV_NO_DEV=1

RUN apk add --no-cache git cups-client

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock .

RUN uv sync --locked
COPY backend/ .

# # Copy the static assets from the pnpm builder
COPY --from=frontend-builder /frontend/dist ./static

# RUN mkdir -p ./static/assets

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

