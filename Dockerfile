FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[llm,cloud]"

# Cloud Run Jobs get fresh filesystems per execution; durable state lives in
# Firestore and Cloud Storage. /tmp keeps local artifacts out of the image.
ENV DATA_DIR=/tmp/data
# Line-flushed stdout so Cloud Logging shows pipeline stages as they happen.
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "edgar_sentinel.agent"]
