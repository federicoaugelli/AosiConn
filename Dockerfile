# syntax=docker/dockerfile:1
FROM python:3.13-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libssl-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-install-project

# Copy application code
COPY core/app/ ./app/

# Create necessary directories
RUN mkdir -p /app/db /app/logs /app/threads

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DATABASE_URL=sqlite:///db/aosiconn.db
ENV JWT_SECRET_KEY=change-me-in-production
ENV CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/internal/ || exit 1

# Run the application using uv
WORKDIR /app/app
CMD ["uv", "run", "--", "python", "main.py"]
