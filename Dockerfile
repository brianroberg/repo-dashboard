FROM ghcr.io/astral-sh/uv:0.7-python3.13-bookworm-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY src/ src/

# Install the project itself
RUN uv sync --frozen --no-dev

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "dashboard.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
