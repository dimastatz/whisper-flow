#!/bin/bash

abort()
{
    echo "*** FAILED ***" >&2
    exit 1
}

if [ "$#" -eq 0 ]; then
    echo "No arguments provided. Usage: 
    1. '-local' to build local environment
    2. '-docker' to build and run docker container
    3. '-test' to run linter, formatter and tests"
elif [ $1 = "-local" ]; then
    trap 'abort' 0
    set -e
    echo "Running format, linter and tests"
    rm -rf .venv
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r ./requirements.txt

    black whisperflow tests
    pylint --fail-under=9.9 whisperflow tests
    pytest --cov-fail-under=95 --cov whisperflow -v tests
elif [ $1 = "-test" ]; then
    trap 'abort' 0
    set -e
    
    echo "Running format, linter and tests"
    source .venv/bin/activate
    black whisperflow tests
    pylint --fail-under=9.9 whisperflow tests
    pytest --ignore=tests/benchmark --cov-fail-under=95 --cov --log-cli-level=INFO whisperflow -v tests
elif [ $1 = "-docker" ]; then
    echo "Building and running docker image"
    docker stop whisperflow-container
    docker rm whisperflow-container
    docker rmi whisperflow-image
    # build docker and run
    docker build --tag whisperflow-image --build-arg CACHEBUST=$(date +%s) .
    docker run --name whisperflow-container -p 8888:8888 -d whisperflow-image
elif [ $1 = "-run" ]; then
    echo "Running WhisperFlow server"
    kill $(lsof -t -i:8181) 
    nohup uvicorn whisperflow.fast_server:app --host 0.0.0.0 --port 8181 &
    sleep 2s
    python ./tests/benchmark.py
    kill $(lsof -t -i:8181)
else
  echo "Wrong argument is provided. Usage:
    1. '-local' to build local environment
    2. '-docker' to build and run docker container
    3. '-test' to run linter, formatter and tests"
fi

trap : 0
echo >&2 '*** DONE ***'