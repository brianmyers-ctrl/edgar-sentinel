FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[web,cloud]"
ENV STORAGE_BACKEND=firestore GOOGLE_CLOUD_PROJECT=edgar-sentinel
EXPOSE 8080
CMD ["python", "-m", "edgar_sentinel.dashboard.app"]
