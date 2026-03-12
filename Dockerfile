# ═══════════════════════════════════════════════════════════════
# RAMO PUB - PRODUCTION DOCKERFILE (Multi-Stage Build)
# ═══════════════════════════════════════════════════════════════

# Build Stage
FROM python:3.11-slim as builder

# Build arguments
ARG BUILD_ENV=production
ARG SENTRY_DSN

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --upgrade pip

# Copy and install Python dependencies
COPY requirements/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ═══════════════════════════════════════════════════════════════
# Production Stage
# ═══════════════════════════════════════════════════════════════
FROM python:3.11-slim as production

# Labels for metadata
LABEL maintainer="Ramo Pub Team"
LABEL version="1.0.0"
LABEL description="Ramo Pub Restaurant Management System"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FLASK_DEBUG=false \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    netcat-openbsd \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create app directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r app && useradd -r -g app app

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads /app/static && \
    chown -R app:app /app

# Copy application code
COPY --chown=app:app . /app/

# Set permissions
RUN chmod +x /app/docker-entrypoint.sh

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Expose port
EXPOSE 5000

# Entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command (can be overridden)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--timeout", "120", "--keepalive", "2", "--max-requests", "1000", "--max-requests-jitter", "100", "web.app:app"]

# ═══════════════════════════════════════════════════════════════
# Development Stage (Optional)
# ═══════════════════════════════════════════════════════════════
FROM production as development

# Override environment for development
ENV FLASK_ENV=development \
    FLASK_DEBUG=true

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-flask black flake8

# Development command
CMD ["python", "web_app.py"]
