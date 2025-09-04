#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

import yt_dlp as ytdlp


def download_audio(url: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ydl_opts = {
        # best audio only; fallbacks as needed
        "format": "bestaudio/best",
        "outtmpl": str(out_dir / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
    }
    with ytdlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))
        # Some formats may be .webm/.m4a; return path as-is
        return path


def main():
    p = argparse.ArgumentParser(description="Download → select best channel → dual-mono → full transcription to SRT")
    p.add_argument("url", help="YouTube URL")
    p.add_argument("-o", "--out-dir", default="downloads", help="Output directory")
    p.add_argument("-m", "--model", default="small", help="Faster-Whisper model (tiny/base/small/medium/large-v3)")
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"], help="Device")
    p.add_argument("--compute-type", default="int8", help="Compute type (int8/float16/float32)")
    p.add_argument("--analyze-seconds", type=float, default=60.0, help="Seconds to analyze for best channel (default 60)")
    args = p.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Download best audio
    audio_path = download_audio(args.url, out_dir)
    print(f"Audio downloaded: {audio_path}")

    # 2) Pick best channel and write dual-mono MP3
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from select_best_channel import main as pick_main  # type: ignore

    best_dual = out_dir / f"{audio_path.stem}.dualmono.mp3"
    # Reinvoke selector as a function via argv emulation
    argv_backup = sys.argv[:]  # save
    try:
        sys.argv = ["select_best_channel.py", str(audio_path), "-o", str(best_dual), "--sample-seconds", str(args.analyze_seconds)]
        pick_main()
    finally:
        sys.argv = argv_backup
    print(f"Dual-mono audio: {best_dual}")

    # 3) Transcribe (simple, no chunking/enhance)
    from transcribe_simple import main as ts_main  # type: ignore
    srt_out = out_dir / f"{audio_path.stem}.dualmono.srt"
    argv_backup = sys.argv[:]
    try:
        sys.argv = [
            "transcribe_simple.py",
            str(best_dual),
            "-o",
            str(srt_out),
            "-m",
            args.model,
            "--device",
            args.device,
            "--compute-type",
            args.compute_type,
        ]
        ts_main()
    finally:
        sys.argv = argv_backup

    print("Pipeline done.")
    print(f"SRT: {srt_out}")
    print(f"Artifacts in: {out_dir}")


if __name__ == "__main__":
    main()

