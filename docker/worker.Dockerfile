FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml .
RUN mkdir -p app && touch app/__init__.py && pip install --no-cache-dir . && rm -rf app

COPY apps/api/ .

CMD ["python", "-m", "app.workers.scheduler"]
