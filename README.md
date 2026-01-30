<div align="center">
<h1 align="center"> Whisper Flow </h1> 
<h3>Real-Time Transcription Using OpenAI Whisper</br></h3>
<img src="https://img.shields.io/badge/Progress-100%25-red"> <img src="https://img.shields.io/badge/Feedback-Welcome-green">
</br>
</br>
<kbd>
<img src="https://github.com/dimastatz/whisper-flow/blob/da8b67c6180566b987854b2fb94670fee92e6682/docs/imgs/whisper-flow.png?raw=true" width="256px"> 
</kbd>
</div>

## About The Project

### OpenAI Whisper 
OpenAI [Whisper](https://github.com/openai/whisper) is a versatile speech recognition model designed for general use. Trained on a vast and varied audio dataset, Whisper can handle tasks such as multilingual speech recognition, speech translation, and language identification. It is commonly used for batch transcription, where you provide the entire audio or video file to Whisper, which then converts the speech into text. This process is not done in real-time; instead, Whisper processes the files and returns the text afterward, similar to handing over a recording and receiving the transcript later.

### Whisper Flow 
Using Whisper Flow, you can generate real-time transcriptions for your media content. Unlike batch transcriptions, where media files are uploaded and processed, streaming media is delivered to Whisper Flow in real time, and the service returns a transcript immediately.

### What is Streaming
Streaming content is sent as a series of sequential data packets, or 'chunks,' which Whisper Flow transcribes on the spot. The benefits of using streaming over batch processing include the ability to incorporate real-time speech-to-text functionality into your applications and achieving faster transcription times. However, this speed may come at the expense of accuracy in some cases.

### Stream Windowing
In scenarios involving time-streaming, it's typical to perform operations on data within specific time frames known as temporal windows. One common approach is using the [tumbling window](https://learn.microsoft.com/en-us/azure/stream-analytics/stream-analytics-window-functions#tumbling-window) technique, which involves gathering events into segments until a certain condition is met.

<div align="center">
<img src="https://github.com/dimastatz/whisper-flow/blob/main/docs/imgs/streaming.png?raw=true"> 
<div>Tumbling Window</div>
</div><br/>

### Streaming Results
Whisper Flow splits the audio stream into segments based on natural speech patterns, like speaker changes or pauses. The transcription is sent back as a series of events, with each response containing more transcribed speech until the entire segment is complete.

| Transcript                                    | EndTime  | IsPartial |
| :-------------------------------------------- | :------: | --------: |
| Reality                                       |   0.55   | True      |
| Reality is created                            |   1.05   | True      |
| Reality is created by the                     |   1.50   | True      |
| Reality is created by the mind                |   2.15   | True      |
| Reality is created by the mind                |   2.65   | False     |
| we can                                        |   3.05   | True      |
| we can change                                 |   3.45   | True      |
| we can change reality                         |   4.05   | True      |
| we can change reality by changing             |   4.45   | True      |
| we can change reality by changing our mind    |   5.05   | True      |
| we can change reality by changing our mind    |   5.55   | False     |

### Benchmarking
The evaluation metrics for comparing the performance of Whisper Flow are Word Error Rate (WER) and latency. Latency is measured as the time between two subsequent partial results, with the goal of achieving sub-second latency. We're not starting from scratch, as several quality benchmarks have already been performed for different ASR engines. I will rely on the research article ["Benchmarking Open Source and Paid Services for Speech to Text"](https://www.frontiersin.org/articles/10.3389/fdata.2023.1210559/full) for guidance. For benchmarking the current implementation of Whisper Flow, I use [LibriSpeech](https://www.openslr.org/12).

```bash
| Partial | Latency | Result |

True  175.47  when we took
True  185.14  When we took her.
True  237.83  when we took our seat.
True  176.42  when we took our seats.
True  198.59  when we took our seats at the
True  186.72  when we took our seats at the
True  210.04  when we took our seats at the breakfast.
True  220.36  when we took our seats at the breakfast table.
True  203.46  when we took our seats at the breakfast table.
True  242.63  When we took our seats at the breakfast table, it will
True  237.41  When we took our seats at the breakfast table, it was with
True  246.36  When we took our seats at the breakfast table, it was with the
True  278.96  When we took our seats at the breakfast table, it was with the feeling.
True  285.03  When we took our seats at the breakfast table, it was with the feeling of being.
True  295.39  When we took our seats at the breakfast table, it was with the feeling of being no
True  270.88  When we took our seats at the breakfast table, it was with the feeling of being no longer
True  320.43  When we took our seats at the breakfast table, it was with the feeling of being no longer looked
True  303.66  When we took our seats at the breakfast table, it was with the feeling of being no longer looked upon.
True  470.73  When we took our seats at the breakfast table, it was with the feeling of being no longer
True  353.25  When we took our seats at the breakfast table, it was with the feeling of being no longer looked upon as connected.
True  345.74  When we took our seats at the breakfast table, it was with the feeling of being no longer looked upon as connected in any way.
True  368.66  When we took our seats at the breakfast table, it was with the feeling of being no longer looked upon as connected in any way with the
True  400.25  When we took our seats at the breakfast table, it was with the feeling of being no longer looked upon as connected in any way with this case.
True  382.71  When we took our seats at the breakfast table, it was with the feeling of being no longer looked upon as connected in any way with this case.
False 405.02  When we took our seats at the breakfast table, it was with the feeling of being no longer looked upon as connected in any way with this case.
```

When running this benchmark on a MacBook Air with an [M1 chip and 16GB of RAM](https://support.apple.com/en-il/111883#:~:text=Testing%20conducted%20by%20Apple%20in,to%208%20clicks%20from%20bottom.), we achieve impressive performance metrics. The latency is consistently well below 500ms, ensuring real-time responsiveness. Additionally, the word error rate is around 7%, demonstrating the accuracy of the transcription.

```bash
Latency Stats:
count     26.000000
mean     275.223077
std       84.525695
min      154.700000
25%      205.105000
50%      258.620000
75%      339.412500
max      470.700000
```

### Prerequisites

Before installing WhisperFlow, ensure you have the following:

- **Python**: 3.8 or higher (tested with Python 3.12)
- **PortAudio**: Required for PyAudio (audio I/O library)

#### Installing PortAudio

**macOS** (using Homebrew):
```bash
brew install portaudio
```

**Linux** (Ubuntu/Debian):
```bash
sudo apt-get install portaudio19-dev
```

**Linux** (Fedora/RHEL):
```bash
sudo dnf install portaudio-devel
```

**Windows**:
PortAudio is typically bundled with PyAudio wheels on Windows. If you encounter issues, refer to the [PyAudio documentation](https://people.csail.mit.edu/hubert/pyaudio/).

### How To Use it

## Quick Start

Get WhisperFlow running in under 5 minutes:

```bash
# Clone the repository
git clone https://github.com/dimastatz/whisper-flow.git
cd whisper-flow

# Setup environment, install dependencies, and run tests
./run.sh -local

# Activate the virtual environment
source .venv/bin/activate

# Start the server on port 8181
./run.sh -run-server
```

The server will be available at `http://localhost:8181`. Visit `http://localhost:8181/health` to verify it's running.

---

## Development Setup

For contributors and developers:

### 1. Initial Setup
```bash
# Clone and enter the directory
git clone https://github.com/dimastatz/whisper-flow.git
cd whisper-flow

# Setup environment: creates .venv, installs dependencies, runs tests
./run.sh -local
```

**What `-local` does:**
- Creates a fresh virtual environment (`.venv`)
- Installs all dependencies from `requirements.txt`
- Runs `black` formatter on code
- Runs `pylint` linter (requires 9.9/10 score)
- Runs all unit tests (requires 95% coverage)

### 2. Running Tests
```bash
# Activate environment
source .venv/bin/activate

# Run tests only (formatting + linting + unit tests)
./run.sh -test
```

### 3. Running the Server
```bash
# Activate environment
source .venv/bin/activate

# Start the FastAPI server on port 8181
./run.sh -run-server
```

The server provides:
- **WebSocket endpoint**: `ws://localhost:8181/ws` - Real-time streaming transcription
- **Health check**: `GET http://localhost:8181/health` - Server status
- **Batch transcription**: `POST http://localhost:8181/transcribe_pcm_chunk` - Process PCM audio files

### 4. Running Benchmarks
```bash
# Activate environment
source .venv/bin/activate

# Run benchmark tests (starts server, runs tests, stops server)
./run.sh -benchmark
```

This measures transcription latency and word error rate (WER) using LibriSpeech test data.

---

## Docker Deployment

### Using Docker
```bash
# Build and run the Docker container
./run.sh -docker
```

**What `-docker` does:**
- Stops and removes any existing `whisperflow-container`
- Removes the old `whisperflow-image`
- Builds a fresh Docker image with all dependencies
- Runs the container on port 8888

### Manual Docker Setup
```bash
# Build the image
docker build -t whisperflow-image --file Dockerfile.test .

# Run the container
docker run --name whisperflow-container -p 8181:8181 -d whisperflow-image

# Check logs
docker logs whisperflow-container

# Stop the container
docker stop whisperflow-container
```

---

## Using as a Python Library

Install WhisperFlow as a package to integrate real-time transcription into your own applications:

### Installation
```bash
pip install whisperflow
```

### Basic Usage

Create a WebSocket endpoint for real-time streaming transcription:

```python
from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect
import whisperflow.streaming as st
import whisperflow.transcriber as ts

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Load the Whisper model (default: tiny.en.pt)
    model = ts.get_model()
    
    # Define transcription callback
    async def transcribe_async(chunks: list):
        return await ts.transcribe_pcm_chunks_async(model, chunks)
    
    # Define response callback
    async def send_back_async(data: dict):
        await websocket.send_json(data)
    
    try:
        await websocket.accept()
        
        # Create transcription session
        session = st.TranscribeSession(transcribe_async, send_back_async)
        
        # Process incoming audio chunks
        while True:
            data = await websocket.receive_bytes()
            session.add_chunk(data)
            
    except WebSocketDisconnect:
        # Client disconnected
        await session.stop()
    except Exception as exception:
        # Handle errors
        await session.stop()
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close()
```

### API Reference

**Transcriber Module** (`whisperflow.transcriber`):
- `get_model(file_name="tiny.en.pt")` - Load a Whisper model
- `transcribe_pcm_chunks(model, chunks, lang="en")` - Synchronous transcription
- `transcribe_pcm_chunks_async(model, chunks, lang="en")` - Async transcription

**Streaming Module** (`whisperflow.streaming`):
- `TranscribeSession(transcribe_fn, send_back_fn)` - Create a streaming session
- `session.add_chunk(audio_data)` - Add audio chunk for processing
- `session.stop()` - Stop the transcription session

### Audio Format Requirements

WhisperFlow expects PCM audio data with the following specifications:
- **Sample Rate**: 16 kHz
- **Channels**: Mono (1 channel)
- **Format**: 16-bit signed integer (int16)

---

## Available Commands

All commands are available through `./run.sh`:

| Command | Description |
|---------|-------------|
| `./run.sh -local` | Setup environment, install dependencies, run tests |
| `./run.sh -test` | Run formatter, linter, and unit tests |
| `./run.sh -run-server` | Start the FastAPI server on port 8181 |
| `./run.sh -benchmark` | Run performance benchmark tests |
| `./run.sh -docker` | Build and run Docker container |

---
#### Roadmap
- [X] Release v1.0-RC - Includes transcription streaming implementation.
- [X] Release v1.1 - Bug fixes and implementation of the most requested changes.
- [ ] Release v1.2 - Prepare the package for integration with the py-speech package.
