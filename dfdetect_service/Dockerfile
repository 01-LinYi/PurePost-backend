FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY app.py inference.py ./


RUN mkdir -p /app/model


EXPOSE 5555


HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5555/health || exit 1


CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5555", "--workers", "2"]