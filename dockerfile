FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Create cache directory for TTS audio files
RUN mkdir -p /app/tts_cache

EXPOSE 8000
CMD ["bash","start.sh"]
