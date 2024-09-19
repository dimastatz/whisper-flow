<div align="center">
<h1 align="center"> Whisper Flow </h1> 
<h3>Real-Time Transcription Using OpenAI Whisper</br></h3>
<img src="https://img.shields.io/badge/Progress-97%25-red"> <img src="https://img.shields.io/badge/Feedback-Welcome-green">
</br>
</br>
<kbd>
<img src="https://github.com/dimastatz/whisper-flow/blob/main/docs/imgs/whisper-flow.png" width="256px"> 
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
<img src="/docs/imgs/streaming.png"> 
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

### How To Use it

#### As a Web Server
To run WhisperFlow as a web server, start by cloning the repository to your local machine.
```bash
git clone https://github.com/dimastatz/whisper-flow.git
```
Then navigate to WhisperFlow folder, create a local venv with all dependencies and run the web server on port 8181.
```bash
cd whisper-flow
./run.sh -local
source .venv/bin/activate
./run.sh -benchmark
```

#### As a Python Package
Set up a WebSocket endpoint for real-time transcription by retrieving the transcription model and creating asynchronous functions for transcribing audio chunks and sending JSON responses. Manage the WebSocket connection by continuously processing incoming audio data. Handle terminate exception to stop the session and close the connection if needed.

Start with installing whisper python package

```bash
pip install whisperflow
```

Now import whsiperflow and transcriber modules

```Python
import whisperflow.streaming as st
import whisperflow.transcriber as ts

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    model = ts.get_model()

    async def transcribe_async(chunks: list):
        return await ts.transcribe_pcm_chunks_async(model, chunks)

    async def send_back_async(data: dict):
        await websocket.send_json(data)

    try:
        await websocket.accept()
        session = st.TrancribeSession(transcribe_async, send_back_async)

        while True:
            data = await websocket.receive_bytes()
            session.add_chunk(data)
    except Exception as exception:
        await session.stop()
        await websocket.close()
```
#### Roadmap
- [X] Release v1.0-RC - Includes transcription streaming implementation.
- [X] Release v1.1 - Bug fixes and implementation of the most requested changes.
- [ ] Release v1.2 - Prepare the package for integration with the py-speech package.
