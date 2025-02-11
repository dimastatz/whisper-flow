FROM python:3.11-slim-buster

# Install system dependencies
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

RUN rm -rf .venv & python3 -m venv .venv & source .venv/bin/activate \
    & pip install --upgrade pip & pip install -r ./requirements.txt \ 
    & black whisperflow tests & pylint --fail-under=9.9 whisperflow tests \
    & pytest --ignore=tests/benchmark --cov-fail-under=95 --cov whisperflow -v tests


# Command to run the application (modify as needed)
CMD ["python", "app.py"]