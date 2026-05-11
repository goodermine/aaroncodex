# VOX Python Worker

This worker provides the first production transcription stage for VOX:

- `POST /health`
- `POST /separate`

It runs beside the Node backend and is responsible for stem separation using `python-audio-separator`.

## Requirements

- Python 3.10+
- `ffmpeg` available on `PATH`

## Install

```bash
cd python_worker
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```bash
cd /root/.codex/worktrees/8b06/CodeTest
python3 -m uvicorn python_worker.app:app --host 127.0.0.1 --port 8797
```

## Endpoints

### `POST /health`

Returns:

- `ok`
- `service`
- `version`
- `pythonVersion`

### `POST /separate`

Request body:

```json
{
  "jobId": "job_20260409_abc123",
  "inputPath": "/abs/path/input.wav",
  "outputDir": "/abs/path/storage/jobs/job_20260409_abc123/stems",
  "stemMode": "vocals_instrumental",
  "cleanupIntermediate": false
}
```

Response body:

```json
{
  "ok": true,
  "jobId": "job_20260409_abc123",
  "engine": {
    "name": "python-audio-separator",
    "version": "0.30.1",
    "model": "model_mel_band_roformer_ep_3005_sdr_11.4360.ckpt"
  },
  "outputs": {
    "vocals": {
      "path": "/abs/path/.../vocals.wav",
      "format": "wav",
      "sampleRate": 44100,
      "channels": 2,
      "durationSec": 12.34
    },
    "instrumental": {
      "path": "/abs/path/.../instrumental.wav",
      "format": "wav",
      "sampleRate": 44100,
      "channels": 2,
      "durationSec": 12.34
    }
  },
  "warnings": []
}
```

## Notes

- The worker uses the separator library directly rather than shelling out to the CLI.
- The default model can be overridden from Node with `VOX_SEPARATOR_MODEL_FILENAME`.
- The next phase adds `/transcribe/basic-pitch` on top of this scaffold.
