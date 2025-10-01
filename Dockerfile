# Multi-stage build for optimal image size
FROM python:3.13-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./
COPY commitloom/ ./commitloom/

# Create virtual environment and install dependencies
RUN uv venv .venv && \
    . .venv/bin/activate && \
    uv sync --frozen

# Final stage
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY commitloom/ ./commitloom/
COPY pyproject.toml ./

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Create a non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Entry point
ENTRYPOINT ["python", "-m", "commitloom"]