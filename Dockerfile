FROM ghcr.io/astral-sh/uv:alpine3.22

ENV UV_NO_DEV=1

RUN apk add --no-cache git

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --locked

COPY franking ./franking
COPY templates ./templates

CMD ["uv", "run", "uvicorn", "franking.main:app", "--host", "0.0.0.0", "--port", "8000"]
