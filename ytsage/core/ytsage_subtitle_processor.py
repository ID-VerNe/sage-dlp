import re
import json
from .ytsage_grammar_constants import (
    ARTICLES, DETERMINERS, SUBJECTS, AUXILIARIES,
    PREPOSITIONS, CONJUNCTIONS
)
from .ytsage_logic_rule import RuleSegmenter
from .ytsage_logic_llm import LLMSegmenter


class SubtitlesProcessor:
    def __init__(self, segments, lang='en', mode='rule', llm_config=None, callback_progress=None, max_lines=1):
        self.segments = segments
        self.lang = lang
        self.mode = mode
        self.llm_config = llm_config or {}
        self.callback_progress = callback_progress or (lambda v, t: None)
        self.max_lines = max_lines

        # Support Check: Only 'en' and 'zh' have advanced segmentation logic
        if self.lang not in ['en', 'zh']:
            if self.mode != 'rule':
                print(f"[Processor] Warning: Language '{self.lang}' not supported for AI segmentation. Falling back to 'rule' mode.")
                self.mode = 'rule'

        # v39 Specs - Rigid Physics & Slow Reading
        self.MAX_CPL = 50
        self.MAX_LINES = 1
        self.MIN_DURATION_HARD = 1.0
        self.MIN_DURATION_TARGET = 2.4 # Increased for bilingual comfort
        self.MAX_DURATION_HARD = 7.0
        self.GAP_THRESHOLD = 0.083
        self.TARGET_CPS = 14 # Slower for dual-lang processing
        self.LIMIT_CPS = 18  # Hard ceiling
        self._apply_segmentation_params()

        # v39 Advanced Grammar Tables (imported from shared constants)
        self.ARTICLES = ARTICLES
        self.DETERMINERS = DETERMINERS
        self.SUBJECTS = SUBJECTS
        self.AUXILIARIES = AUXILIARIES
        self.PREPOSITIONS = PREPOSITIONS
        self.CONJUNCTIONS = CONJUNCTIONS

        # v39 Strong Compounds (Never Split)
        self.COMPOUND_FIXED = {
            "according to", "as well as", "because of", "next to", "due to", "in order to", "out of",
            "instead of", "rather than", "the fact that", "the way that", "sort of", "kind of",
            "more than", "less than", "once and for all", "broken down into", "in the", "at the",
            "on the", "of the", "to the", "isn't it", "wasn't it", "don't know", "have to", "has to",
            "had to", "want to", "going to", "used to", "look at", "look for",
            "supposed to", "supposed to be",
            "remote control",
            "look like", "much of", "so that", "to be had", "which is"
        }

    def _apply_segmentation_params(self):
        params = self.llm_config.get("segmentation_params", {})
        if not isinstance(params, dict):
            return
        if "MAX_CPL" in params: self.MAX_CPL = float(params["MAX_CPL"])
        if "MAX_LINES" in params: self.MAX_LINES = int(params["MAX_LINES"])
        if "MIN_DURATION_HARD" in params: self.MIN_DURATION_HARD = float(params["MIN_DURATION_HARD"])
        if "MIN_DURATION_TARGET" in params: self.MIN_DURATION_TARGET = float(params["MIN_DURATION_TARGET"])
        if "MAX_DURATION_HARD" in params: self.MAX_DURATION_HARD = float(params["MAX_DURATION_HARD"])
        if "GAP_THRESHOLD" in params: self.GAP_THRESHOLD = float(params["GAP_THRESHOLD"])
        if "TARGET_CPS" in params: self.TARGET_CPS = float(params["TARGET_CPS"])
        if "LIMIT_CPS" in params: self.LIMIT_CPS = float(params["LIMIT_CPS"])

    def calc_len(self, text: str) -> float:
        """VideoLingo-style weighted character length calculation."""
        text = str(text)
        def char_weight(char):
            code = ord(char)
            if 0x4E00 <= code <= 0x9FFF or 0x3040 <= code <= 0x30FF:  # Chinese and Japanese
                return 1.75
            elif 0xAC00 <= code <= 0xD7A3 or 0x1100 <= code <= 0x11FF:  # Korean
                return 1.5
            elif 0x0E00 <= code <= 0x0E7F:  # Thai
                return 1
            elif 0xFF01 <= code <= 0xFF5E:  # full-width symbols
                return 1.75
            else:  # other characters (English, etc.)
                return 1
        return sum(char_weight(char) for char in text)

    def progress(self, value, text=None):
        self.callback_progress(value, text)

    def _norm(self, word):
        return re.sub(r"[^\w']", "", word.lower())

    def _get_sticky_score_after(self, word, next_word=None):
        w = self._norm(word)
        if next_word:
            nw = self._norm(next_word)
            combined = w + " " + nw
            if word[0].isupper() and next_word[0].isupper(): return 12000
            for atom in self.COMPOUND_FIXED:
                if atom.lower().startswith(combined.lower()): return 10000

        if w in self.ARTICLES or w in self.DETERMINERS: return 9000
        if w in self.SUBJECTS: return 8000
        if w in self.AUXILIARIES: return 7000
        if w in self.PREPOSITIONS: return 6500
        return 0

    def _get_break_score_before(self, word, prev_word=None):
        w = self._norm(word)
        if prev_word:
            pw = self._norm(prev_word)
            combined = pw + " " + w
            for atom in self.COMPOUND_FIXED:
                if atom.lower().endswith(combined.lower()): return -20000
                if atom.lower().startswith(w.lower()) and atom.lower() != w.lower(): return -20000

        if w in self.CONJUNCTIONS: return 7000
        if w in self.PREPOSITIONS: return 6000
        if w in self.SUBJECTS: return 5000
        return 0

    def _get_break_score_after(self, word):
        if word.endswith(('.', '?', '!', ':')): return 6000
        if word.endswith((',', ';')): return 3000
        return 0

    # Configurable ASR repair patterns (pattern, replacement, flags)
    DEFAULT_ASR_REPAIRS = [
        (r"\bhave to electric\b", "have two electric", re.IGNORECASE),
        (r"\bget car\b", "get in the car", re.IGNORECASE),
        (r"\bthat really the case\b", "that is really the case", re.IGNORECASE),
        (r"\bit's it started\b", "it started", re.IGNORECASE),
        (r"\bto had\b", "to be had", re.IGNORECASE),
        (r"\bclick link\b", "click the link", re.IGNORECASE),
        (r"\bBuddy gave me\b", "the guy gave me", re.IGNORECASE),
        (r"Leno,'s", "Leno's", 0),
        (r"\bapp\. to\b", "app to", re.IGNORECASE),
    ]

    def _clean_asr_artifacts(self, text):
        # Ellipsis Normalize
        text = text.replace('...', '…').replace('..', '…')
        if self.lang == 'en':
            text = "".join([c for c in text if ord(c) < 128 or c == '…'])

        # Apply configurable ASR repairs
        asr_repairs = self.llm_config.get('asr_repairs', self.DEFAULT_ASR_REPAIRS)
        for pattern, replacement, flags in asr_repairs:
            text = re.sub(pattern, replacement, text, flags=flags)

        # Grammar: Fix solitary 'i'
        text = re.sub(r'\b i \b', ' I ', text)

        # Bridge Conjunctions: lower case mid-sentence
        text = re.sub(r'([a-z0-9]),\s+(And|But|So|Because|Which|Who|Where|That)\b',
                      lambda m: f"{m.group(1)}, {m.group(2).lower()}", text)

        # Clean stutters
        text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(And|But|So|To|Which|Because|With|That|Upon|Where|If|When)\.\s+', r'\1 ', text)

        return text.strip()

    def _split_into_two_lines(self, words):
        """Split a segment of words into two lines based on sticky scores."""
        if not words: return ""
        n = len(words)
        best_score, best_idx = -10000, n // 2

        for i in range(1, n):
            left = " ".join([w['word'] for w in words[:i]])
            right = " ".join([w['word'] for w in words[i:]])

            # Physics: prefer balanced lines
            balance_penalty = abs(self.calc_len(left) - self.calc_len(right)) * 0.5

            # Grammar: prefer splitting at natural boundaries
            sticky_score = self._get_sticky_score_after(words[i-1]['word'], words[i]['word'])
            break_score = self._get_break_score_after(words[i-1]['word']) + self._get_break_score_before(words[i]['word'], words[i-1]['word'])

            score = break_score - sticky_score - balance_penalty

            if score > best_score:
                best_score, best_idx = score, i

        line1 = " ".join([w['word'] for w in words[:best_idx]])
        line2 = " ".join([w['word'] for w in words[best_idx:]])
        return f"{line1}\n{line2}"

    def process_segments(self):
        if self.mode == 'raw':
            subtitles = []
            for seg in self.segments:
                subtitles.append({
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': seg['text'],
                    'words': seg.get('words', [])
                })
            return subtitles

        raw_words = []
        for segment in self.segments:
            for w in segment.get('words', []):
                if 'start' in w and 'end' in w:
                    w['word'] = re.sub(r'[^\x00-\x7F\w\s\'\.,\?!\:\;\-…-]', '', w.get('word','')).strip()
                    if w['word'] and w['start'] < w['end']:  # skip zero-width words
                        raw_words.append(w)

        # Stable sort by start time
        raw_words.sort(key=lambda x: (x['start'], x['end']))

        flat_words = []
        for w in raw_words:
            if flat_words and w['start'] < flat_words[-1]['start']:
                w['start'] = flat_words[-1]['start'] + 0.001
            flat_words.append(w)

        # Multi-round timestamp overlap repair
        for _ in range(3):
            fixed = False
            for i in range(len(flat_words) - 1):
                if flat_words[i]['end'] > flat_words[i + 1]['start']:
                    flat_words[i]['end'] = flat_words[i + 1]['start']
                    fixed = True
            if not fixed:
                break

        if self.mode == 'llm':
            segmenter = LLMSegmenter(self)
        elif self.mode == 'semantic':
            # Lazy import to avoid requiring spacy when not needed
            from .videolingo.engine import SemanticEngine
            segmenter = SemanticEngine(self)
        else:
            segmenter = RuleSegmenter(self)

        subtitles = segmenter.process(flat_words)

        final_list = []
        for k in range(len(subtitles)):
            sub = subtitles[k]
            sub['text'] = self._clean_asr_artifacts(sub['text'])
            char_count = self.calc_len(sub['text']) # Use weighted length

            # v39 Minimal Frame Window
            if char_count > 10:
                min_vis = 1.4 if char_count < 22 else 1.8
                if (sub['end'] - sub['start']) < min_vis:
                    sub['end'] = sub['start'] + min_vis

            duration = sub['end'] - sub['start']

            # Global CPS Normalization
            if duration > 0 and (char_count / duration) > self.LIMIT_CPS:
                if k < len(subtitles) - 1:
                    max_extend = subtitles[k+1]['start'] - sub['end'] - self.GAP_THRESHOLD
                    if max_extend > 0:
                        needed = (char_count / self.TARGET_CPS) - duration
                        sub['end'] += min(needed, max_extend)
                        duration = sub['end'] - sub['start']

            if duration > 0 and (char_count / duration) > self.LIMIT_CPS:
                if k > 0:
                    gap = sub['start'] - final_list[k-1]['end'] - self.GAP_THRESHOLD
                    if gap > 0:
                        needed = (char_count / self.TARGET_CPS) - duration
                        sub['start'] -= min(needed, gap)
                        duration = sub['end'] - sub['start']

            # CPS calibration failure warning
            if duration > 0 and (char_count / duration) > self.LIMIT_CPS:
                print(f"[CPS Warning] 字幕#{k+1} 无法降至 LIMIT_CPS={self.LIMIT_CPS}，当前={char_count / duration:.1f}, text='{sub['text'][:40]}'")

            if duration < self.MIN_DURATION_HARD:
                sub['end'] = sub['start'] + self.MIN_DURATION_HARD

            # Anti-overlap hard shift
            if k > 0 and sub['start'] < final_list[k-1]['end'] + self.GAP_THRESHOLD:
                sub['start'] = final_list[k-1]['end'] + self.GAP_THRESHOLD
                if sub['end'] < sub['start'] + self.MIN_DURATION_HARD:
                    sub['end'] = sub['start'] + self.MIN_DURATION_HARD

            final_list.append(sub)

        # Multi-pass anti-overlap
        for _ in range(3):
            fixed = False
            for k in range(1, len(final_list)):
                if final_list[k]['start'] < final_list[k-1]['end'] + self.GAP_THRESHOLD:
                    final_list[k]['start'] = final_list[k-1]['end'] + self.GAP_THRESHOLD
                    if final_list[k]['end'] < final_list[k]['start'] + self.MIN_DURATION_HARD:
                        final_list[k]['end'] = final_list[k]['start'] + self.MIN_DURATION_HARD
                    fixed = True
            if not fixed: break
        return final_list


def save_srt(subtitles, filename):
    def format_ts(s):
        ms = round((s % 1) * 1000) % 1000
        s = int(s)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    with open(filename, 'w', encoding='utf-8') as f:
        for i, sub in enumerate(subtitles, 1):
            f.write(f"{i}\n{format_ts(sub['start'])} --> {format_ts(sub['end'])}\n{sub['text']}\n\n")
