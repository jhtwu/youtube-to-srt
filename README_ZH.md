# 中文使用指南（簡化管線）

## 整體概念
- 提供「下載 → 自動挑選較佳聲道 → 轉成雙單聲道 → 轉錄為 SRT」的一條龍流程。
- 目的：避免單耳/單聲道播放時的相位抵消問題，提升 ASR（語音轉文字）穩定性與可聽性。

## 專案結構
- `scripts/auto_simple_pipeline.py`：一鍵流程入口（建議執行這支）。
- `scripts/select_best_channel.py`：以 VAD+SNR 自動評分左右聲道，輸出「雙單聲道」MP3。
- `scripts/transcribe_simple.py`：使用 Faster‑Whisper 全檔轉錄為 SRT（無切塊、無強化）。
- `requirements.txt`：依賴套件（`yt-dlp`、`faster-whisper`、`webrtcvad`、`soundfile`）。
- `downloads/`：下載與輸出目錄（音檔、字幕檔）。

## 安裝需求
- Python 3.10+（建議虛擬環境）
- `ffmpeg`（必要）
- 可存取網路（下載模型與 YouTube）
- 安裝依賴：`pip install -r requirements.txt`

## 使用方式
- 一鍵流程（推薦）
  - `python scripts/auto_simple_pipeline.py "<YOUTUBE_URL>" -o downloads -m small --device auto`
  - 產出：
    - 音檔：`downloads/<title>.dualmono.mp3`
    - 字幕：`downloads/<title>.dualmono.srt`
- 拆步驟（進階）
  - 自動選聲道並輸出雙單聲道：
    - `python scripts/select_best_channel.py "in.mp3" -o "out.dualmono.mp3" --sample-seconds 60`
  - 轉錄：
    - `python scripts/transcribe_simple.py "out.dualmono.mp3" -o "out.srt" -m small --device auto`

## 流程與原理
- 聲道評分（`select_best_channel.py`）
  - 抽取左右聲道為 16kHz 單聲道 WAV。
  - 用 WebRTC VAD 判定語音比例（speech ratio），計算語音/噪音 RMS 與 SNR（dB）。
  - 比較規則：SNR > 語音比例 > 整體音量，選出較佳聲道。
  - 產出「雙單聲道」：將較佳聲道複製到左右聲道，避免單耳/單聲道時的相位抵消。
- 轉錄（`transcribe_simple.py`）
  - 使用 Faster‑Whisper（Whisper 的高效推論版）全檔轉錄，預設 `beam_size=5`、`temperature=0.0`。
  - 可指定 `-m tiny/base/small/medium/large-v3`、語言 `-l zh`、裝置與 `--compute-type`。

## 常用參數
- `-m/--model`：建議 `small`（準確/速度折衷）；困難音訊可用 `medium/large-v3`。
- `--device`：`auto/cpu/cuda`；有 NVIDIA GPU 建議 `cuda`。
- `--compute-type`（精度/量化）：
  - CPU：`int8`（快、占記憶體小），或 `float32`（較準但慢）。
  - GPU：`float16`（多數情況最佳折衝）；記憶體吃緊可試 `int8_float16`（若支援）。
- `--sample-seconds`（選聲道分析時間）：預設 60 秒，加速評分；設 0 代表全檔分析。

## 為什麼要雙單聲道
- 某些片段（例：13:52 後）左右聲道可能近乎反相，單耳/單聲道播放時 L+R 混音會互相抵消而近乎無聲。
- 雙單聲道能避免此問題，對播放與轉錄都更穩定。

## 建議與延伸
- 想要更高準確度：改 `-m medium` 或 `-m large-v3`（GPU 更佳）。
- 想要更快：CPU 用 `--compute-type int8`；GPU 用 `--compute-type float16`。
- 若遇到模型下載慢或網路受限，可改為本地檔案轉錄（跳過下載）或先行離線快取模型。
