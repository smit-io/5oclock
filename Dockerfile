# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --no-compile -r requirements.txt \
    && find /usr/local -type f -name '*.pyc' -delete \
    && find /usr/local -name '__pycache__' -type d -prune -exec rm -rf {} +

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy only runtime deps from builder (no build tools)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Minimal runtime system deps (if needed; test without first)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

ENV TARGET_24H=17 \
    POP_LIMIT=500 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY . .
RUN mkdir -p geonames cities

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
