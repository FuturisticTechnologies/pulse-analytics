FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first so code edits do not bust the layer cache.
COPY requirements.txt requirements-optional.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-optional.txt

COPY . .

# Non-root, as any reviewer would expect of a production image.
RUN useradd --create-home --uid 1000 pulse && chown -R pulse:pulse /app
USER pulse

CMD ["python", "-m", "etl.pipeline", "--help"]
