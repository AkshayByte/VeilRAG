FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

RUN python -m spacy download en_core_web_lg

COPY . .

EXPOSE 8000

CMD ["python", "-m", "src.rag.cli"]
