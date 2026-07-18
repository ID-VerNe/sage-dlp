import re

class RuleSegmenter:
    def __init__(self, processor):
        self.p = processor

    # @lat: [[Core#sage_logic_rule]]
    def process(self, flat_words):
        """v39: Physics First, Stability Boost, No Hanging Preps."""
        # 1. Natural grouping with Unyielding Bridge
        natural_units = self._group_into_natural_units(flat_words)

        # 2. Recursive split (Physics is the absolute LAW: 42 CPL)
        all_events_words = []
        for unit in natural_units:
            all_events_words.extend(self._recursive_split_to_events(unit))

        # 3. v39 Stabilization Merge (Threshold 28 chars)
        final_events = []
        i = 0
        while i < len(all_events_words):
            seg = all_events_words[i]
            dur = seg[-1]['end'] - seg[0]['start']
            text = " ".join([w['word'] for w in seg])

            if i < len(all_events_words) - 1:
                next_seg = all_events_words[i+1]
                merged_words = seg + next_seg
                merged_text = " ".join([w['word'] for w in merged_words])
                merged_dur = next_seg[-1]['end'] - seg[0]['start']
                gap = next_seg[0]['start'] - seg[-1]['end']

                # Rigid Hanging Check
                last_w = self.p._norm(seg[-1]['word'])
                is_hanging = (last_w in self.p.ARTICLES or
                              last_w in self.p.DETERMINERS or
                              last_w in self.p.SUBJECTS or
                              last_w in self.p.PREPOSITIONS or
                              last_w in self.p.CONJUNCTIONS or
                              last_w in self.p.AUXILIARIES or
                              last_w in {"which", "who", "where", "that", "so", "but", "and", "or"})

                # Stability Check (threshold 28 for v39)
                is_unstable = (len(text) < 28 or len(seg) < 6)

                # Forced Merge if hanging, unstable, or very short duration
                if (is_hanging or is_unstable or dur < self.p.MIN_DURATION_TARGET or (len(text) < 38 and gap < 0.25)) and \
                   len(merged_text) <= self.p.MAX_CPL and \
                   merged_dur <= 7.0:

                    all_events_words[i+1] = merged_words
                    i += 1
                    continue

            final_events.append(seg)
            i += 1

        subtitles = []
        for seg in final_events:
            text = " ".join([w['word'] for w in seg])
            subtitles.append({
                'start': seg[0]['start'],
                'end': seg[-1]['end'],
                'text': text,
                'words': seg
            })
        return subtitles

    def _group_into_natural_units(self, flat_words):
        """Rigid grouping with Preposition and Clause pulling."""
        units, current = [], []
        for i, w in enumerate(flat_words):
            current.append(w)
            word_text = w['word']
            is_end = word_text.endswith(('.', '?', '!', ':'))
            gap = 0
            if i < len(flat_words) - 1:
                gap = flat_words[i+1]['start'] - w['end']

            last_w = self.p._norm(word_text)
            is_hanging = (last_w in self.p.ARTICLES or
                          last_w in self.p.DETERMINERS or
                          last_w in self.p.SUBJECTS or
                          last_w in self.p.AUXILIARIES or
                          last_w in self.p.PREPOSITIONS or
                          last_w in self.p.CONJUNCTIONS or
                          last_w in {"which", "who", "where", "that", "so", "but", "and", "or"})

            if i < len(flat_words) - 1:
                next_w_raw = flat_words[i+1]['word']
                next_w = self.p._norm(next_w_raw)

                # Subordinate/Logic Bridge
                if (next_w in self.p.SUBJECTS or next_w in {"which", "who", "where", "that", "and", "but", "so", "if", "since"}) and gap < 2.0:
                    continue

                # Case-sensitive Proper Noun Sticky
                if word_text[0].isupper() and next_w_raw[0].isupper() and gap < 1.5:
                    continue

            # Absolute Hanging Ban
            if is_hanging and i < len(flat_words) - 1 and gap < 3.5:
                continue

            if (is_end and gap > 0.25) or gap > 1.8:
                if len(current) < 8 and gap < 2.5:
                    continue
                units.append(current)
                current = []
        if current: units.append(current)
        return units

    def _recursive_split_to_events(self, words):
        """Split with v39 Hard 42-CPL physics breaker."""
        if not words: return []
        text = " ".join([w['word'] for w in words])
        dur = words[-1]['end'] - words[0]['start']

        # Hard Physical Limit Check
        if len(text) <= self.p.MAX_CPL and dur <= 7.0:
            return [words]

        n = len(words)
        if n <= 1: return [words]

        best_score, best_idx = -5000000000, n // 2
        for i in range(max(1, int(n*0.05)), min(n, int(n*0.95))):
            left_text = " ".join([w['word'] for w in words[:i]])
            right_text = " ".join([w['word'] for w in words[i:]])

            # The Wall: 42 chars
            if len(left_text) > self.p.MAX_CPL or len(right_text) > self.p.MAX_CPL:
                score = -100000000000 # Absolute physics barrier
            else:
                # Grammar & Stability Score
                score = 10000 * (1.0 - abs(i - n/2)/(n/2))

                word_before, word_at = words[i-1]['word'], words[i]['word']
                score -= self.p._get_sticky_score_after(word_before, word_at)
                score += self.p._get_break_score_after(word_before)
                score += self.p._get_break_score_before(word_at, word_before)

                # Avoid tiny shards
                if len(left_text) < 25 or len(right_text) < 25:
                    score -= 50000

            if score > best_score:
                best_score, best_idx = score, i

        left, right = words[:best_idx], words[best_idx:]
        return self._recursive_split_to_events(left) + self._recursive_split_to_events(right)
