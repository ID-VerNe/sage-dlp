import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from .sage_llm_client import LLMClient
from .sage_grammar_constants import (
    ARTICLES, PREPOSITIONS, AUXILIARIES, CONJUNCTIONS, NEGATIONS
)

class LLMSegmenter:
    def __init__(self, processor):
        self.p = processor
        self.SOFT_LIMIT = 70 # 理想上限 (不算末词)
        self.HARD_LIMIT = 85 # 绝对上限 (算上末词)

        # Persistent client for the entire task
        config = getattr(self.p, 'llm_config', {})
        if isinstance(config, str):
            try: config = json.loads(config)
            except json.JSONDecodeError: config = {}
        self.client = LLMClient(config)

        # Grammar protection sets (from shared constants)
        self.ARTICLES = ARTICLES
        self.PREPOSITIONS = PREPOSITIONS
        self.AUXILIARIES = AUXILIARIES
        self.CONJUNCTIONS = CONJUNCTIONS
        self.NEGATIONS = NEGATIONS

    def _norm_word(self, word):
        """标准化单词用于语法规则匹配：去除标点并转小写"""
        return re.sub(r"^[^\w']+|[^\w']+$", "", word).lower()

    def _is_bad_cut(self, words, cut_idx):
        """
        检测断点是否违反语法规则。
        cut_idx 表示断在 words[cut_idx] 之后，即 left = words[:cut_idx+1], right = words[cut_idx+1:]
        """
        if cut_idx < 0 or cut_idx >= len(words) - 1:
            return True

        curr = self._norm_word(words[cut_idx]['word'])
        next_ = self._norm_word(words[cut_idx + 1]['word'])

        if not curr or not next_:
            return False

        # 禁止冠词 + 名词之间断开
        if curr in self.ARTICLES:
            return True

        # 禁止介词 + 宾语之间断开
        if curr in self.PREPOSITIONS:
            return True

        # 禁止助动词/情态动词 + 动词之间断开
        if curr in self.AUXILIARIES:
            return True

        # 禁止连词后立刻断开（连词应该在下一行开头，不应挂在行尾）
        if curr in self.CONJUNCTIONS:
            return True

        # 禁止否定词 + 动词/形容词之间断开
        if curr in self.NEGATIONS or curr.endswith("n't"):
            return True

        # 禁止所有格 + 名词之间断开
        if curr.endswith("'s") or next_ in {"'s", "s"}:
            return True

        return False

    def _accept_llm_cut(self, words, cut_idx):
        """
        验证 LLM 返回的断点是否可接受。
        检查：语法合法性、长度合理性、不产生太短的片段
        """
        if cut_idx < 0 or cut_idx >= len(words) - 1:
            return False

        # 语法检查
        if self._is_bad_cut(words, cut_idx):
            return False

        left = words[:cut_idx + 1]
        right = words[cut_idx + 1:]

        left_len, _ = self._get_lens(left)
        right_len, _ = self._get_lens(right)

        # 避免产生太短的片段（至少 8 个字符）
        if left_len < 8 or right_len < 8:
            return False

        # 左侧不能超过 HARD_LIMIT
        if left_len > self.HARD_LIMIT:
            return False

        return True

    def _get_lens(self, words):
        """返回 (总长, 去掉末词后的长度)"""
        if not words: return 0, 0
        full_text = " ".join([w['word'] for w in words])
        total_len = self.p.calc_len(full_text)

        if len(words) <= 1:
            return total_len, 0

        prefix_text = " ".join([w['word'] for w in words[:-1]])
        prefix_len = self.p.calc_len(prefix_text)
        return total_len, prefix_len

    def _is_acceptable(self, words):
        """判定句子是否满足 70-85 弹性规则"""
        if not words: return True
        total_len, prefix_len = self._get_lens(words)
        if prefix_len <= self.SOFT_LIMIT and total_len <= self.HARD_LIMIT:
            return True
        return False

    def process(self, flat_words):
        # Step 1: 物理断句 (.?!)
        blocks = self._split_by_terminal_punct(flat_words)
        total_blocks = len(blocks)
        if total_blocks == 0:
            self.p.progress(98, "LLM 七步断句法：无可处理片段")
            return []

        max_workers = int(getattr(self.p, 'llm_config', {}).get('max_workers', 10))
        workers = max(1, min(max_workers, total_blocks))
        self.p.progress(76, f"LLM 断句并发开始: 0/{total_blocks} (workers={workers})")
        results_nested = [None] * total_blocks
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self._recursive_split_logic, block): idx
                for idx, block in enumerate(blocks)
            }
            done = 0
            for future in as_completed(futures):
                idx = futures[future]
                results_nested[idx] = future.result()
                done += 1
                progress = min(97, 76 + int((done / total_blocks) * 21))
                self.p.progress(progress, f"LLM 断句并发处理中: {done}/{total_blocks}")

        final_units = [u for sub in results_nested for u in sub if u]
        self.p.progress(98, "LLM 七步断句法 (单点迭代版) 完成")

        subtitles = []
        for seg in final_units:
            text = " ".join([w['word'] for w in seg])
            subtitles.append({
                'start': seg[0]['start'],
                'end': seg[-1]['end'],
                'text': text,
                'words': seg
            })
        return subtitles

    def _recursive_split_logic(self, words, depth=0):
        if not words: return []
        if depth > 12:
            # 12 levels support ~4096 words worst-case (2^12), sufficient for subtitles
            return [words]

        # Step 2: 弹性长度校验
        if self._is_acceptable(words):
            return [words]

        # Step 3: 标点回溯切分
        split_idx = self._find_last_suitable_punctuation(words)
        if split_idx != -1:
            left = words[:split_idx+1]
            right = words[split_idx+1:]
            return self._recursive_split_logic(left, depth+1) + self._recursive_split_logic(right, depth+1)

        # Step 5: LLM 单点切分 (3 次重试，低延迟模式)
        llm_parts = self._get_breath_units_llm_with_retry(words)

        # 如果 LLM 没切，走语义保底
        if len(llm_parts) == 1:
            return self._semantic_split_fallback(words)

        # Step 7: 对切出来的部分递归迭代
        refined = []
        for p in llm_parts:
            # 只有当片段依然不合格时才递归
            if not self._is_acceptable(p):
                # 递归收敛检查
                if len(p) < len(words):
                    refined.extend(self._recursive_split_logic(p, depth + 1))
                else:
                    refined.extend(self._semantic_split_fallback(p))
            else:
                refined.append(p)
        return refined

    def _get_breath_units_llm_with_retry(self, words):
        """LLM 迭代单点切分，重试 2 次"""
        raw_text = " ".join([w['word'] for w in words])

        for attempt in range(2):
            res_parts = self._get_single_cut_llm(raw_text, words)
            if len(res_parts) == 2:
                return res_parts
        return [words]

    def _get_single_cut_llm(self, raw_text, original_words):
        """核心单点切分逻辑：增强版 prompt + 本地复核"""
        prompt = f"""
## Role
You are a professional subtitle line-break editor.

## Task
Insert EXACTLY ONE `[br]` marker into the input text to split it into two subtitle chunks.

## Hard Rules
1. Return the original text with ONLY ONE `[br]` inserted.
2. Do NOT rewrite, remove, add, reorder, normalize, or correct any word.
3. Do NOT change punctuation, capitalization, contractions, quotes, or wording.
4. The output must contain exactly one `[br]`.
5. The split must be between two existing words, never inside a word.
6. Do not add explanations, labels, bullet points, or alternative versions.

## Subtitle Quality Rules
Choose the most natural reading break for subtitles.

Prefer splitting:
- after a complete phrase, clause, or natural speech unit
- after punctuation such as a comma, semicolon, colon, dash, or closing quote
- before a new clause introduced by words like "but", "because", "which", "that", "when", "if", "so", or "and"
- at a point where both chunks are easy to read on screen
- where the first chunk is roughly 40-70 characters if possible, as long as grammar remains natural

Avoid splitting:
- between an article and its noun: "a car", "an instructor", "the road"
- between a preposition and its object: "in the car", "with a gauge", "on the road"
- between an auxiliary or modal verb and the main verb: "is running", "should check", "can see"
- between a negation and the word it modifies: "not allowed", "didn't turn"
- between a possessive and its noun: "James's car", "driver's seat"
- between adjective chains and their noun when the phrase is short
- immediately after conjunctions or clause starters: "and", "but", "because", "which", "that", "if", "when"
- leaving only one or two short words in either chunk
- creating a split that sounds like the speaker was cut off mid-phrase

## Decision Priority
1. Preserve the exact original text.
2. Preserve grammar and phrase integrity.
3. Make the subtitle comfortable to read.
4. Prefer a visually balanced split.
5. Aim for the first chunk to be roughly 40-70 characters only when it does not conflict with the rules above.

## Input Text
{raw_text}

## Output Format
Return ONLY the text with exactly one `[br]`.
""".strip()

        # Reduced timeout to 15s for segmentation tasks
        res = self._call_llm(prompt, timeout=15, max_retries=2)
        if not res or '[br]' not in res:
            return [original_words]

        # 映射逻辑：将 [br] 前后的文本与原始单词列表进行模糊匹配
        def clean_token(t): return re.sub(r"[^\w]", "", t).lower()

        parts = res.split('[br]')
        left_text = parts[0].strip()

        # 统计 [br] 前面大概有多少个单词
        res_tokens_left = [clean_token(t) for t in left_text.split() if clean_token(t)]
        num_left = len(res_tokens_left)

        if num_left <= 0 or num_left >= len(original_words):
            return [original_words]

        # 验证单词序列是否大体匹配 (容忍标点差异)
        orig_tokens_clean = [clean_token(w['word']) for w in original_words if clean_token(w['word'])]
        res_tokens_all = [clean_token(t) for t in res.replace('[br]', ' ').split() if clean_token(t)]

        # 如果总词数严重不符，说明模型改写了，拒绝
        if abs(len(res_tokens_all) - len(orig_tokens_clean)) > 2:
            return [original_words]

        # 本地复核：检查断点质量
        cut_idx = num_left - 1
        if not self._accept_llm_cut(original_words, cut_idx):
            return [original_words]

        return [original_words[:num_left], original_words[num_left:]]

    def _semantic_split_fallback(self, words):
        """语义权重保底截断 + 语法保护"""
        if len(words) <= 1: return [words]
        best_score, best_idx = -999999, 0

        for i in range(len(words) - 1):
            left_part = words[:i+1]
            if not self._is_acceptable(left_part): break

            w_curr, w_next = words[i]['word'], words[i+1]['word']

            # 基础得分：break score 和 sticky score
            b_score = self.p._get_break_score_after(w_curr) + self.p._get_break_score_before(w_next, w_curr)
            s_score = self.p._get_sticky_score_after(w_curr, w_next)

            # 偏向中间
            balance = abs(len(words)//2 - (i+1)) * 50

            # 基础得分
            score = b_score - s_score - balance

            # 语法保护：严格惩罚糟糕断点
            if self._is_bad_cut(words, i):
                score -= 100000

            # 短边惩罚：避免第二行太短
            right_part = words[i+1:]
            left_len, _ = self._get_lens(left_part)
            right_len, _ = self._get_lens(right_part)

            if right_len < 12:
                score -= 500
            if left_len < 12:
                score -= 300

            # 标点奖励：优先在标点后断开
            if self._is_comma_like(w_curr):
                score += 200

            if score > best_score:
                best_score, best_idx = score, i

        left, right = words[:best_idx+1], words[best_idx+1:]
        return [left] + self._recursive_split_logic(right, depth=10)

    def _find_last_suitable_punctuation(self, words):
        for i in range(len(words) - 2, 1, -1):
            if self._is_comma_like(words[i]['word']):
                if self._is_acceptable(words[:i+1]): return i
        return -1

    def _is_terminal(self, word):
        return bool(re.search(r"[.!?。？！]$", word))

    def _is_comma_like(self, word):
        return bool(re.search(r"[,，;；:]$", word))

    def _split_by_terminal_punct(self, flat_words):
        units, current = [], []
        for w in flat_words:
            current.append(w)
            if self._is_terminal(w['word']):
                units.append(current); current = []
        if current: units.append(current)
        return units

    def _call_llm(self, prompt, timeout=None, max_retries=None):
        try:
            return self.client.chat_text(
                prompt=prompt,
                system_prompt="Subtitle Architect: Single-cut precision engine.",
                timeout=timeout,
                max_retries=max_retries
            )
        except Exception:
            return None
