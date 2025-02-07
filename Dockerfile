# syntax=docker/dockerfile:1

FROM python:3.11-slim-buster

# Combine multiple apt-get to reduce docker layres
RUN apt-get update && apt-get install -y \
    libasound-dev libportaudio2 libportaudiocpp0 portaudio19-dev \
    ffmpeg 
    
    
WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
COPY . .

RUN black whisperflow tests
RUN pylint --fail-under=9.9 whisperflow tests
RUN pytest --cov-fail-under=95 --cov whisperflow -v tests

ENTRYPOINT ["python3"]
CMD ["./whisperflow/app.py" ]