# ---- IntuitivePromptEngine backend API ------------------------------------
# Runs the FastAPI/uvicorn server headless. The webcam pipeline is a host-only
# concern (see README "Docker" section); the container serves the REST + WS API,
# health checks, config, and stored generations.
FROM python:3.11-slim AS runtime

# System libraries OpenCV/MediaPipe link against even in headless use.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Bind to all interfaces so the container is reachable; data on a volume.
    SERVER_HOST=0.0.0.0 \
    DATA_DIR=/data

WORKDIR /app

# Dependencies first for layer caching.
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Application code.
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY config.yaml run.py ./

# Run as an unprivileged user; own the data volume mount point.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data
USER appuser

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else 1)"

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
