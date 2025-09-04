#!/usr/bin/env python3
import argparse
import contextlib
import io
import math
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np
import webrtcvad


def ensure_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg not found. Please install ffmpeg and retry.")


def extract_channel_wav(src: Path, chan: str, dest: Path) -> None:
    """Extract a single channel to 16k mono PCM WAV.
    chan: 'left' or 'right'
    """
    if chan not in {"left", "right"}:
        raise ValueError("chan must be 'left' or 'right'")
    pan = "pan=mono|c0=c0" if chan == "left" else "pan=mono|c0=c1"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        str(src),
        "-af",
        pan,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@dataclass
class ChannelMetrics:
    speech_ratio: float
    snr_db: float
    speech_rms: float
    noise_rms: float
    overall_rms: float


def read_wav_int16(path: Path) -> np.ndarray:
    import soundfile as sf  # soundfile comes with many envs via libs; fallback to ffmpeg if missing

    data, sr = sf.read(str(path), dtype="int16")
    if sr != 16000:
        raise SystemExit(f"Unexpected sample rate {sr}, expected 16000")
    if data.ndim != 1:
        data = data[:, 0]
    return data


def compute_metrics_int16_mono(signal: np.ndarray, frame_ms: int = 20, vad_mode: int = 2) -> ChannelMetrics:
    vad = webrtcvad.Vad(vad_mode)
    sr = 16000
    frame_len = int(sr * frame_ms / 1000)
    # Ensure multiple of frame_len
    n = len(signal) - (len(signal) % frame_len)
    if n <= 0:
        return ChannelMetrics(0.0, -120.0, 1e-9, 1e-9, 1e-9)
    signal = signal[:n]
    # Frame bytes for VAD
    frames = signal.reshape(-1, frame_len)
    speech_flags = []
    speech_energies = []
    noise_energies = []
    for f in frames:
        # Convert to bytes little-endian
        fb = f.astype(np.int16).tobytes()
        is_speech = vad.is_speech(fb, sr)
        speech_flags.append(is_speech)
        rms = np.sqrt(np.mean((f.astype(np.float32)) ** 2) + 1e-12)
        if is_speech:
            speech_energies.append(rms)
        else:
            noise_energies.append(rms)
    speech_ratio = float(np.mean(speech_flags)) if speech_flags else 0.0
    speech_rms = float(np.mean(speech_energies)) if speech_energies else 1e-9
    noise_rms = float(np.mean(noise_energies)) if noise_energies else 1e-9
    overall_rms = float(np.sqrt(np.mean((signal.astype(np.float32)) ** 2) + 1e-12))
    snr_db = 20.0 * math.log10(max(speech_rms, 1e-9) / max(noise_rms, 1e-9))
    return ChannelMetrics(speech_ratio, snr_db, speech_rms, noise_rms, overall_rms)


def choose_channel(mL: ChannelMetrics, mR: ChannelMetrics) -> Tuple[str, ChannelMetrics]:
    # Primary: higher SNR
    if abs(mL.snr_db - mR.snr_db) > 1.0:
        return ("left", mL) if mL.snr_db > mR.snr_db else ("right", mR)
    # Secondary: higher speech ratio
    if abs(mL.speech_ratio - mR.speech_ratio) > 0.02:
        return ("left", mL) if mL.speech_ratio > mR.speech_ratio else ("right", mR)
    # Tertiary: higher overall RMS (louder)
    return ("left", mL) if mL.overall_rms >= mR.overall_rms else ("right", mR)


def make_dualmono(src: Path, use_channel: str, out_path: Path, bitrate: str = "192k") -> None:
    mapping = "pan=stereo|c0=c0|c1=c0" if use_channel == "left" else "pan=stereo|c0=c1|c1=c1"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        str(src),
        "-af",
        mapping,
        "-c:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description="Pick the better speech channel (L/R) using VAD+SNR and optionally output a dual-mono MP3")
    ap.add_argument("input", help="Path to input .mp3/.wav/.m4a/.mp4 (audio extractable)")
    ap.add_argument("-o", "--out", help="Output dual-mono MP3 path (optional)")
    ap.add_argument("--prefer", choices=["auto", "left", "right"], default="auto", help="Force a channel or auto-pick (default auto)")
    ap.add_argument("--bitrate", default="192k", help="Output bitrate for MP3 (default 192k)")
    ap.add_argument("--sample-seconds", type=float, default=0.0, help="Analyze only first N seconds (0 = full)")
    args = ap.parse_args()

    ensure_ffmpeg()
    src = Path(args.input).expanduser().resolve()
    work = src.parent
    # Optional trim for speed
    if args.sample_seconds and args.sample_seconds > 0:
        sampled = work / (src.stem + ".sample.wav")
        cmd = [
            "ffmpeg", "-hide_banner", "-y",
            "-t", f"{args.sample_seconds}",
            "-i", str(src),
            "-ac", "2", "-ar", "16000", "-c:a", "pcm_s16le",
            str(sampled),
        ]
        subprocess.run(cmd, check=True)
        base_input = sampled
    else:
        base_input = src

    left_wav = work / (src.stem + ".left.wav")
    right_wav = work / (src.stem + ".right.wav")
    extract_channel_wav(base_input, "left", left_wav)
    extract_channel_wav(base_input, "right", right_wav)

    # Load and score
    try:
        import soundfile as sf  # type: ignore
    except Exception as e:
        raise SystemExit("Python package 'soundfile' is required for analysis.") from e

    dataL, srL = sf.read(str(left_wav), dtype="int16")
    dataR, srR = sf.read(str(right_wav), dtype="int16")
    if srL != 16000 or srR != 16000:
        raise SystemExit("Unexpected sample rate (expected 16000 Hz)")
    if dataL.ndim != 1:
        dataL = dataL[:, 0]
    if dataR.ndim != 1:
        dataR = dataR[:, 0]

    mL = compute_metrics_int16_mono(dataL)
    mR = compute_metrics_int16_mono(dataR)

    if args.prefer == "left":
        chosen, metrics = "left", mL
    elif args.prefer == "right":
        chosen, metrics = "right", mR
    else:
        chosen, metrics = choose_channel(mL, mR)

    print("Channel metrics:")
    print(f"  left : speech_ratio={mL.speech_ratio:.2f} snr={mL.snr_db:.1f}dB rms_s={mL.speech_rms:.5f} rms_n={mL.noise_rms:.5f}")
    print(f"  right: speech_ratio={mR.speech_ratio:.2f} snr={mR.snr_db:.1f}dB rms_s={mR.speech_rms:.5f} rms_n={mR.noise_rms:.5f}")
    print(f"Chosen channel: {chosen}")

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        make_dualmono(src, chosen, out_path, bitrate=args.bitrate)
        print(f"Dual-mono written: {out_path}")


if __name__ == "__main__":
    main()

