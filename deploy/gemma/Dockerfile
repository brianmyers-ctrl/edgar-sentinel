# Ollama + Gemma triage service for Cloud Run (CPU, scale-to-zero).
# The model weights are baked into the image so cold starts don't re-download.
FROM ollama/ollama:latest

ENV OLLAMA_HOST=0.0.0.0:8080 \
    OLLAMA_MODELS=/models \
    OLLAMA_KEEP_ALIVE=-1 \
    OLLAMA_NUM_PARALLEL=1

RUN ollama serve & \
    sleep 5 && \
    ollama pull gemma3:4b && \
    pkill ollama || true

EXPOSE 8080
ENTRYPOINT ["ollama", "serve"]
