#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import List

from faster_whisper import WhisperModel


def srt_timestamp(ms: int) -> str:
    hh = ms // 3_600_000
    mm = (ms % 3_600_000) // 60_000
    ss = (ms % 60_000) // 1000
    mmm = ms % 1000
    return f"{hh:02}:{mm:02}:{ss:02},{mmm:03}"


def write_srt(path: Path, segments, base_offset_ms: int = 0) -> None:
    lines: List[str] = []
    for i, s in enumerate(segments, 1):
        st = int(s.start * 1000) + base_offset_ms
        et = int(s.end * 1000) + base_offset_ms
        txt = (s.text or "").strip()
        lines.append(str(i))
        lines.append(f"{srt_timestamp(st)} --> {srt_timestamp(et)}")
        lines.append(txt)
        lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Simple full-file transcription to SRT using Faster-Whisper")
    p.add_argument("input", help="Path to input audio/video (mp3, wav, m4a, mp4)")
    p.add_argument("-o", "--out", help="Output SRT path (defaults to <input>.srt)")
    p.add_argument("-m", "--model", default="small", help="Model: tiny/base/small/medium/large-v3 (default small)")
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"], help="Device to run on")
    p.add_argument("--compute-type", default="int8", help="Compute type (e.g., int8, float16, float32)")
    p.add_argument("-l", "--language", help="Language code (e.g., zh). Default: auto-detect")
    args = p.parse_args()

    src = Path(args.input).expanduser().resolve()
    out = Path(args.out).expanduser().resolve() if args.out else src.with_suffix(".srt")

    device = args.device
    if device == "auto":
        try:
            import torch  # type: ignore
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"

    print(f"Loading Faster-Whisper model {args.model} on {device} ({args.compute_type})...")
    model = WhisperModel(args.model, device=device, compute_type=args.compute_type)

    options = dict(beam_size=5, temperature=0.0)
    if args.language:
        options["language"] = args.language

    segments, info = model.transcribe(str(src), **options)
    seg_list = list(segments)
    print(f"Detected language: {info.language} (prob={info.language_probability:.2f})")
    write_srt(out, seg_list)
    print(f"Saved SRT: {out}")


if __name__ == "__main__":
    main()

