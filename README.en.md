# SageDLP

Download YouTube videos, extract audio, and process raw caption data through grammar-aware or LLM-powered segmentation into polished SRT subtitles.

[中文](README.md)

## Quick Install

```bash
pip install sage-dlp
```

Requires Python 3.10-3.14. The application manages its own runtime dependencies (FFmpeg, yt-dlp) on first launch, so no manual toolchain setup is needed.

## Features

- **Subtitle-optimized segmentation engine.** Two competing algorithms: a physics-based rule engine (42 CPL hard limit, grammar-aware "Unyielding Bridge" grouping, stabilization merges) and an LLM-powered segmenter using any OpenAI-compatible API. Both enforce rigid timing constraints (minimum 1.0s display, maximum 7.0s, target 14 CPS) and refuse to strand articles, prepositions, or conjunctions at the end of a line.

- **LLM integration as a first-class feature.** Full OpenAI-compatible chat client with retry, timeout, LRU caching (256 entries), and JSON response validation. The `segment_with_llm()` orchestrator chains json3 parsing, LLM segmentation, and SRT generation into a single call.

- **json3-to-SRT conversion pipeline.** Reads YouTube's proprietary `.json3` caption format, parses it into flat word sequences, then processes through the segmenter to produce properly-timed, grammatically-correct SRT files.

- **Self-contained dependency bootstrap.** Downloads and verifies FFmpeg (zip or 7z), and yt-dlp with SHA256 checksums. No pre-installed toolchain required.

- **Companion browser extension.** Chrome/Edge extension that auto-detects cookies on YouTube tabs and pushes them to a local HTTP server, eliminating manual cookie file exports.

- **Rich download GUI.** Format selection, playlist browsing, subtitle track picking, audio preview, and download history -- all built with PySide6.

## Quick Start

1. Install via pip, then run `sage-dlp`.

2. On first run, the app downloads FFmpeg and yt-dlp automatically.

3. Paste a YouTube URL. The app fetches available formats and subtitle tracks.

4. Select your preferred format and subtitle language, then click download.

5. For LLM-powered subtitle segmentation, configure your API endpoint and key in Settings.

## Cookie Bridge

The companion browser extension (shipped in `browser_ext/`) listens for cookies on YouTube tabs and POSTs them to a local HTTP server at `127.0.0.1:9876`. The server saves them to timestamped files and emits a Qt signal so the GUI activates them in real time. This eliminates the manual step of exporting cookie files for authenticated downloads.

## LLM Segmentation

SageDLP's `sage_llm_segmenter.py` takes raw word sequences from YouTube's json3 captions and sends them to an OpenAI-compatible API for intelligent segmentation. The LLM respects grammar constants (articles, prepositions, auxiliaries, determiners, conjunctions) shared with the rule engine, ensuring both approaches produce linguistically consistent output. The `SubtitlesProcessor` supports both `mode='rule'` and `mode='llm'` with weighted character-length calculations (CJK 1.75x, Korean 1.5x) for proper bilingual subtitle timing.

## License

MIT. [GitHub](https://github.com/ID-VerNe/sage-dlp)