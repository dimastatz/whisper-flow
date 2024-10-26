
# Demo 1: Performance Benchmark of WHisper-Flow

## Prompt:

### Slide 1: Introduction to Whisper-Flow Demo
"Welcome, everyone! In this demo, I’m going to show you how Whisper-Flow works and highlight its performance, particularly focusing on the latency of partial and non-partial transcription results."

### Slide 2: Cloning the Repository
"First, let’s start by cloning the Whisper-Flow repository from GitHub. This is a simple step, and here’s the command I’ll use:"

```bash
git clone https://github.com/dimastatz/whisper-flow.git 
```
"This gives us access to all the necessary files to run Whisper-Flow locally."

### Slide 3: Setting Up the Local Environment
"Now that we have the repository, I’m going to set up the local environment. Here’s what I’ll do:"
```bash
Copy code
cd whisper-flow  
./run.sh -local  
source .venv/bin/activate  
```

"This creates a virtual environment and installs all dependencies. We’re almost ready to run the server."

### Slide 4: Starting the Whisper-Flow Server
"Next, I’m going to start the Whisper-Flow server. It will run locally on my machine, listening for requests on port 8181. Here’s the command:"
```bash
Copy code
uvicorn whisperflow.fast_server:app --host 0.0.0.0 --port 8181
```

"Now that the server is running, we’re ready to capture audio from my microphone and transcribe it in real-time."

### Slide 5: Real-Time Transcription in Action
"Now, let’s see Whisper-Flow in action. I’m going to run a Python script that captures audio from my local microphone. As I speak, Whisper-Flow will transcribe my speech in real-time, and you’ll see both partial and non-partial results appearing on the screen."
"Here’s the sentence I’m going to speak:"
"Now please pay attention, as I speak, Whisper-Flow transcribes text in real-time. You will see both partial and non-partial results appearing on the screen."
[Pause here to begin speaking and show the transcription on the screen]
"Notice how the partial results start appearing as I speak. These partial results give immediate feedback on what the system predicts, even before I’ve finished my sentence."
"Once I finish speaking, you’ll see the non-partial results. These are the final transcriptions, where Whisper-Flow refines and confirms the text for higher accuracy."
[Allow time for the transcription to finalize and explain further]
"This demonstrates the low latency and high performance of Whisper-Flow, which handles real-time speech processing with very little delay. Partial results show up instantly, and non-partial results provide the finalized, more accurate transcription once the input is complete."

### Slide 6: Conclusion
"So, in this demo, we’ve seen how Whisper-Flow transcribes audio in real-time, showcasing both partial and non-partial results with minimal latency. This capability is key for use cases where immediate feedback and accuracy are critical, such as live captioning or voice-assisted applications."
"Thank you for your attention, and I’m happy to answer any questions!"
 