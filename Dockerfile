FROM python:3.12-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies including the build-time ones we verified
RUN pip install --upgrade pip wheel && \
    pip install "setuptools<70" && \
    pip install -r requirements.txt

# Copy the source code
COPY . .

# Install the local package
RUN pip install whisperflow

RUN python -c "import whisperflow; print('whisper-flow installed OK')"

