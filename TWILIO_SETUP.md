# Twilio Clinic Assistant

This project includes a Czech phone assistant for clinic appointment requests.

## Run locally

```bash
cd /Users/bobbysixkiller/vioce/whisper-flow
.venv/bin/uvicorn twilio_clinic_assistant:APP --host 127.0.0.1 --port 8000
```

## Expose to Twilio

Twilio must reach your local webhook over HTTPS. The simplest local tunnel is ngrok:

```bash
ngrok http 8000
```

Use the HTTPS URL from ngrok, for example:

```text
https://example.ngrok-free.app/voice
```

## Configure Twilio

In Twilio Console, open your phone number and set:

- Voice configuration: `A call comes in`
- Webhook method: `POST`
- Webhook URL: `https://example.ngrok-free.app/voice`
- Enable call recording for this number or Voice configuration.
- Recording status callback URL: `https://example.ngrok-free.app/recording-status`
- Recording status callback method: `POST`

The webhook returns TwiML with `<Gather input="speech dtmf" language="cs-CZ">`.
Twilio sends recognized Czech speech back as `SpeechResult`.

## Appointment output

Confirmed requests are saved to:

```text
clinic_appointments.db
```

The webhook automatically stores Twilio's `From` phone number in the
`caller_phone` column so the doctor can call the patient back. VS Code-friendly
exports are refreshed after every saved request:

```text
clinic_appointments.json
clinic_appointments.csv
```

For speech quality, the webhook uses Czech speech hints and stores confidence
scores for each collected field. If Twilio reports low confidence, the assistant
asks the patient to repeat the answer once before moving on. The exported
columns `name_confidence`, `reason_confidence`, `requested_time_confidence`, and
`raw_transcript_json` help the office spot answers that may need a callback.

Whole-call recordings are stored by Twilio. The app stores recording metadata in
the appointment export when Twilio calls `/recording-status`: `recording_sid`,
`recording_url`, `recording_status`, `recording_duration`, `recording_channels`,
`recording_track`, and `recording_start_time`. The `recording_url` points to the
audio file in Twilio; access to the file requires the Twilio account credentials.

You can inspect saved requests while the server is running:

```text
http://127.0.0.1:8000/appointments
```

## Current scope

This is an appointment intake assistant. It does not yet check a real calendar,
reserve a specific slot, send SMS confirmations, or integrate with medical
software. The next production step is to connect the confirmation step to a
calendar or scheduling backend.
