# SoulCraft - AI Persona Synthesis Pipeline
# Multi-stage build for production efficiency

# --- Build stage ---
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies (if needed for any native packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# --- Production stage ---
FROM python:3.12-slim AS production

WORKDIR /app

# Create non-root user for security
RUN groupadd -r soulcraft && useradd -r -g soulcraft soulcraft

# Copy installed packages from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Copy application code
COPY soulcraft/ ./soulcraft/
COPY app.py .
COPY requirements.txt .

# Create data directory and set permissions
RUN mkdir -p /app/.soulcraft && \
    chown -R soulcraft:soulcraft /app

# Switch to non-root user
USER soulcraft

# Expose the application port
EXPOSE 3110

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request, json; r=urllib.request.urlopen('http://localhost:3110/api/health'); d=json.loads(r.read()); exit(0 if d.get('status')=='ok' else 1)"

# Run the application
CMD ["python", "app.py"]
