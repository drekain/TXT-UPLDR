FROM python:3.10-slim-bullseye

# Install system dependencies
RUN apt-get update -y && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        libcurl4-openssl-dev \
        python3-dev \
        musl-dev \
        ffmpeg \
        aria2 \
        mediainfo \
        curl \
        pkg-config \
        build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app/
WORKDIR /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade -r requirements.txt
RUN pip install --no-cache-dir pytube

# Environment variable
ENV COOKIES_FILE_PATH="youtube_cookies.txt"

# Start both gunicorn + bot
CMD gunicorn app:app --bind 0.0.0.0:8000 & python3 main.py
