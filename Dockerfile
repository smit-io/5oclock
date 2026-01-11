FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set Environment Variables
# These act as the defaults if nothing is provided in docker-compose
ENV TARGET_24H=17
ENV POP_LIMIT=500
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application (Respecting .dockerignore)
COPY . .

# Ensure empty directories exist for volume mounting
RUN mkdir -p geonames cities

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]