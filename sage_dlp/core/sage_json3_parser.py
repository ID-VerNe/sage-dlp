"""
YouTube json3 caption format → flat_words converter.

YouTube's json3 format:
  events[].tStartMs       - event start time (milliseconds)
  events[].dDurationMs    - event duration (milliseconds)
  events[].segs[].utf8        - text segment (leading space = new word start)
  events[].segs[].tOffsetMs   - offset from tStartMs (milliseconds)

Output:
  [{'word': str, 'start': float(seconds), 'end': float(seconds)}, ...]
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any


def _clean_word(word: str) -> str:
    """在送入断句/LLM 之前清洗单个 word。

    清除内容：
      - ASR 指示符号：>>, >（通常出现在 event 首个 seg，如 '>> Back'）
      - 方括号标注：[music], [applause], [laughter], [音乐], [掌声] 等
        （可能独立成 word，也可能嵌在文本中间，如 'done [music] just'）
    清除后压缩多余空白，返回空字符串则该 word 被丢弃。
    """
    # 去除行首/行中的 >> 前缀（如 '>> Back' → 'Back', '>> [music]' → '[music]'）
    word = re.sub(r'>+\s*', '', word)
    # 去除方括号标注（含中英文）
    word = re.sub(r'\[\s*[^\]]*\s*\]', '', word)
    # 压缩清除后可能产生的多余空白
    word = re.sub(r'\s{2,}', ' ', word)
    return word.strip()


# @lat: [[Core#sage_json3_parser]]
def parse_yt_json3_to_flat_words(json3_data: dict) -> List[Dict[str, Any]]:
    """
    Convert YouTube json3 caption format to flat word list with timestamps.

    Word boundaries are detected via leading spaces in segs[].utf8.
    End times are estimated from the next word's offset or the event's duration.

    在解析阶段就清洗 >> 和 [...] 标记，确保送入断句/LLM 的是干净文本。
    """
    flat_words = []
    for event in json3_data.get('events', []):
        event_start = event.get('tStartMs', 0) / 1000.0
        event_duration = event.get('dDurationMs', 0) / 1000.0
        event_end = event_start + event_duration

        current_word = ''
        word_start = None
        segs = event.get('segs', [])

        for seg_idx, seg in enumerate(segs):
            text = seg.get('utf8', '')
            offset = seg.get('tOffsetMs', 0) / 1000.0
            abs_time = event_start + offset

            # Leading space marks a new word boundary
            if text.startswith(' ') and current_word:
                if current_word.strip():
                    # 清洗后再入列：纯标记 word（如 '>> [music]'）清洗后为空，自动丢弃
                    cleaned = _clean_word(current_word.strip())
                    if cleaned:
                        flat_words.append({
                            'word': cleaned,
                            'start': word_start or event_start,
                            'end': abs_time,
                        })
                current_word = ''
                text = text.lstrip()
                word_start = abs_time

            if not current_word:
                word_start = abs_time
            current_word += text

        # Flush remaining word
        if current_word.strip():
            cleaned = _clean_word(current_word.strip())
            if cleaned:
                flat_words.append({
                    'word': cleaned,
                    'start': word_start or event_start,
                    'end': event_end,
                })

    # Fix timestamp overlaps (LLMSegmenter tolerates but better to pre-fix)
    for i in range(len(flat_words) - 1):
        if flat_words[i]['end'] >= flat_words[i + 1]['start']:
            flat_words[i]['end'] = flat_words[i + 1]['start'] - 0.001

    return flat_words


def load_json3(path: Path) -> dict:
    """Load a json3 file from disk."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
