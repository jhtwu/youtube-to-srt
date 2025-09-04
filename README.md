# YouTube Audio → Dual‑Mono → SRT (Simple Pipeline)

## Overview
This repo provides a minimal, reliable pipeline to:
- Download audio from YouTube.
- Auto‑select the better speech channel (L/R) using VAD+SNR.
- Produce a dual‑mono MP3 to avoid mono/earbud phase cancellation.
- Transcribe the audio to SRT using Faster‑Whisper.

For a full Chinese guide, see `README_ZH.md`.

## Requirements
- Python 3.10+
- `ffmpeg`
- Network access (download models and YouTube media)
- Install deps: `pip install -r requirements.txt`

## One‑Command Pipeline
- Activate your venv, then run:
  - `python scripts/auto_simple_pipeline.py "<YOUTUBE_URL>" -o downloads -m small --device auto`
- Outputs:
  - Audio: `downloads/<title>.dualmono.mp3`
  - Subtitles: `downloads/<title>.dualmono.srt`

## Components
- `scripts/auto_simple_pipeline.py`: Orchestrates download → best channel → dual‑mono → SRT.
- `scripts/select_best_channel.py`: Scores L/R via WebRTC VAD + SNR and writes dual‑mono.
- `scripts/transcribe_simple.py`: Full‑file SRT transcription via Faster‑Whisper (no chunking/enhance).

## Notes
- Models: `tiny/base/small/medium/large-v3`. Default `small` balances speed/accuracy.
- Device: `--device auto|cpu|cuda`; with NVIDIA GPU, prefer `cuda`.
- Compute type:
  - CPU: `int8` (fast, compact) or `float32` (slower, slightly more accurate).
  - GPU: `float16` is a solid default; `int8_float16` if supported and memory‑constrained.
- Why dual‑mono? Some videos contain near‑out‑of‑phase stereo segments; mono/one‑ear playback can cancel speech. Dual‑mono prevents this and improves ASR stability.
