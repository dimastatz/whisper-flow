<div align="center">
<h1 align="center"> Whisper Flow </h1> 
<h3>Real-Time Transcription Using OpenAI Whisper</br></h3>
<img src="https://img.shields.io/badge/Progress-1%25-red"> <img src="https://img.shields.io/badge/Feedback-Welcome-green">
</br>
</br>
<kbd>
<img src="/docs/imgs/whisper-flow.png" width="256px"> 
</kbd>
</div>


## About The Project

### OpenAI Whisper 
OpenAI [Whisper](https://github.com/openai/whisper) is a versatile speech recognition model designed for general use. Trained on a vast and varied audio dataset, Whisper can handle tasks such as multilingual speech recognition, speech translation, and language identification. It is commonly used for batch transcription, where you provide the entire audio or video file to Whisper, which then converts the speech into text. This process is not done in real-time; instead, Whisper processes the files and returns the text afterward, similar to handing over a recording and receiving the transcript later.

### Whisper Flow 
Using Whisper Flow, you can generate real-time transcriptions for your media content. Unlike batch transcriptions, where media files are uploaded and processed, streaming media is delivered to Whisper Flow in real time, and the service returns a transcript immediately.

### How it works
Streaming content is sent as a series of sequential data packets, or 'chunks,' which Whisper Flow transcribes on the spot. The benefits of using streaming over batch processing include the ability to incorporate real-time speech-to-text functionality into your applications and achieving faster transcription times. However, this speed may come at the expense of accuracy in some cases.

[TBD]()


## How To Use it


