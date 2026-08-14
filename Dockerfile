FROM python:3.10-slim AS base

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    postgresql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Create logs directory and set permissions
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

FROM base AS dev

# Install development dependencies
RUN pip install --no-cache-dir pytest black flake8 mypy

# Switch to non-root user
USER appuser

# Set default command for dev (can override in docker-compose)
CMD ["tail", "-f", "/dev/null"]

FROM base AS prod

# Switch to non-root user
USER appuser

# Set default command for prod (can override in docker-compose)
CMD ["tail", "-f", "/dev/null"]

