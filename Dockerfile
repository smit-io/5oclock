# =========================
# Build stage
# =========================
FROM python:3.11-slim AS builder

WORKDIR /app

# Build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --no-compile -r requirements.txt \
    && find /usr/local -type f -name '*.pyc' -delete \
    && find /usr/local -name '__pycache__' -type d -prune -exec rm -rf {} +

# =========================
# Runtime stage
# =========================
FROM python:3.11-slim

WORKDIR /app

# Runtime deps (gosu is required for UID/GID switching)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Copy only runtime artifacts from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages \
    /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Runtime configuration (UID/GID are overridable at runtime)
ENV UID=1000 \
    GID=1000 \
    TARGET_24H=17 \
    POP_LIMIT=500 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Application files
COPY . .

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create runtime directories (ownership fixed at startup)
RUN mkdir -p /app/geonames /app/cities

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
