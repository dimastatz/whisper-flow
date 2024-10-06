
# Demo 1: Performance Benchmark of WHisper-Flow

## Prompt:
Write a scenario for a demo where presenter shows how Whisper-Flow works and shows performance benchamrk
where latency for partial and non-partial results is demonstrated

1. Presenter clones repo from by running
    ```bash git clone https://github.com/dimastatz/whisper-flow.git ```
2. Then he builds the local virtual env
```bash 
cd whisper-flow
./run.sh -local
source .venv/bin/activate
```
3. Then he starts Whisper-Flow server
```bash
uvicorn whisperflow.fast_server:app --host 0.0.0.0 --port 8181
```
4. And finally, he runs python script that captures local microphones
and he says the text: Now please pay attention, as I speak, Whisper-Flow transcribes text in Real Time. And you can see 
partial and non-partial results. 
