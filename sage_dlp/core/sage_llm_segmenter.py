"""
LLM Segmentation wrapper for SageDLP.

Combines json3 parsing + SubtitlesProcessor + SRT output into a single call.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

from .sage_json3_parser import parse_yt_json3_to_flat_words
from .sage_subtitle_processor import SubtitlesProcessor, save_srt


def _default_llm_config() -> Dict[str, Any]:
    """返回默认断句配置（不依赖外部 LLM 服务，使用 rule 模式）。

    当用户选了字幕但未显式配置 LLM 断句时，用此配置兜底，
    确保 pipeline 始终能跑通。
    """
    return {
        "mode": "rule",
        "url": "",
        "api_key": "",
        "model": "gpt-4.1",
        "temperature": 0.1,
        "max_workers": 10,
        "timeout": 60,
        "max_retries": 3,
        "segmentation_params": {
            "SOFT_LIMIT": 70,
            "HARD_LIMIT": 85,
            "TARGET_CPS": 14,
            "LIMIT_CPS": 18,
        },
    }


# @lat: [[Core#sage_llm_segmenter]]
def segment_with_llm(
    json3_path: Path,
    output_srt_path: Path,
    lang: str = 'en',
    llm_config: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable] = None,
) -> List[Dict[str, Any]]:
    """
    Read json3 → parse → LLM segment → output SRT.

    Args:
        json3_path: Path to the .en.json3 file downloaded by yt-dlp
        output_srt_path: Output path for the .srt file
        lang: Language code ('en', 'zh', ...)
        llm_config: LLM configuration dict (url, api_key, model, params)
        progress_callback: Progress callback fn(value, text)

    Returns:
        subtitles: [{start, end, text, words}, ...]
    """
    # 1. Read json3
    with open(json3_path, 'r', encoding='utf-8') as f:
        json3_data = json.load(f)

    # 2. json3 → flat_words
    flat_words = parse_yt_json3_to_flat_words(json3_data)
    if not flat_words:
        raise ValueError('No words found in json3 file')

    # 3. Wrap into SubtitlesProcessor format
    segments = [{'words': flat_words}]

    # 4. Determine mode based on config
    mode = 'rule'  # default
    if llm_config:
        mode = llm_config.get('mode', 'rule')

    # 5. Create processor and run segmentation
    processor = SubtitlesProcessor(
        segments=segments,
        lang=lang,
        mode=mode,
        llm_config=llm_config or {},
        callback_progress=progress_callback or (lambda v, t: None),
    )
    subtitles = processor.process_segments()

    # 6. Output SRT
    save_srt(subtitles, str(output_srt_path))

    return subtitles


def get_json3_path(output_dir: Path, video_id: str) -> Optional[Path]:
    """Find the json3 subtitle file in the output directory."""
    # First try: match by video_id（video_id 为空时直接用 *.json3，避免产生 **.json3 非法 pattern）
    if video_id:
        json3_files = list(output_dir.glob(f'*{video_id}*.json3'))
        if json3_files:
            # 取最新的（按修改时间）
            return max(json3_files, key=lambda p: p.stat().st_mtime)

    # Fallback: any json3 file（取最新的，避免误抓到旧视频的 json3）
    json3_files = list(output_dir.glob('*.json3'))
    if json3_files:
        return max(json3_files, key=lambda p: p.stat().st_mtime)

    return None
