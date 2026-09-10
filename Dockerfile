# SAMADHAN GRID - container image
# Works unchanged on Hugging Face Spaces, Render, Koyeb, Fly.io, Railway or any VM.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so this layer is cached between code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY static/ ./static/
COPY run.py .

# Free hosts run the container as a non-root user and give it a writable /tmp only.
# UPLOAD_DIR is configurable so evidence files land somewhere writable.
RUN mkdir -p /app/uploads && chmod 777 /app/uploads
ENV UPLOAD_DIR=/app/uploads

# Most platforms inject PORT. 7860 is the Hugging Face Spaces default.
ENV HOST=0.0.0.0 \
    PORT=7860
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','7860')+'/api/health')"

CMD ["python", "run.py"]
