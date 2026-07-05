import json
import re
import time
import threading
import urllib.request
import urllib.error
from collections import OrderedDict
from typing import Any, Callable, Dict, Optional, Tuple


Validator = Optional[Callable[[Dict[str, Any]], Dict[str, str]]]


class LRUCache:
    """Thread-safe LRU cache with max size."""

    def __init__(self, max_size: int = 128):
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Tuple) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def set(self, key: Tuple, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)
            self._cache[key] = value

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

# Global cache to persist across instances
_GLOBAL_LLM_CACHE = LRUCache(max_size=256)

class LLMClient:
    """OpenAI-compatible chat client with retry, validation and LRU cache."""

    def __init__(self, llm_config: Optional[Dict[str, Any]] = None):
        cfg = llm_config or {}
        base_url = cfg.get("url", "http://localhost:8000")
        self.url = self._normalize_chat_url(base_url)
        self.api_key = cfg.get("api_key", "")
        self.model = cfg.get("model", "gpt-4.1")
        self.timeout = int(cfg.get("timeout", 60))
        self.max_retries = int(cfg.get("max_retries", 3))
        self.temperature = float(cfg.get("temperature", 0.1))
        self._cache = _GLOBAL_LLM_CACHE

    @staticmethod
    def _normalize_chat_url(url: str) -> str:
        if url.endswith("/v1/chat/completions"):
            return url
        return f"{url.rstrip('/')}/v1/chat/completions"

    def chat_text(self, prompt: str, system_prompt: Optional[str] = None, timeout: Optional[int] = None, max_retries: Optional[int] = None) -> str:
        cache_key = (system_prompt or "", prompt, False, self.model)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        retries = max_retries if max_retries is not None else self.max_retries
        t_out = timeout if timeout is not None else self.timeout

        # Validate API key is configured when using a non-local endpoint
        if not self.api_key and not self.url.startswith("http://localhost"):
            raise RuntimeError(
                "LLM API key is not configured. "
                "Please set your API key in Settings > LLM Configuration before using this feature."
            )

        last_error: Optional[Exception] = None
        for i in range(retries):
            try:
                content = self._request(prompt, system_prompt=system_prompt, force_json=False, timeout=t_out)
                self._cache.set(cache_key, content)
                return content
            except Exception as e:
                last_error = e
                # Check for rate limit or server error to apply backoff
                is_rate_limit = False
                if isinstance(e, urllib.error.HTTPError) and e.code == 429:
                    is_rate_limit = True

                if i < retries - 1:
                    wait_time = (2 ** i) + (1 if is_rate_limit else 0)
                    time.sleep(wait_time)
        raise RuntimeError(f"LLM text request failed after {retries} retries: {last_error}")

    def chat_json(self, prompt: str, system_prompt: Optional[str] = None, validate: Validator = None, timeout: Optional[int] = None, max_retries: Optional[int] = None) -> Dict[str, Any]:
        cache_key = (system_prompt or "", prompt, True, self.model)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        retries = max_retries if max_retries is not None else self.max_retries
        t_out = timeout if timeout is not None else self.timeout

        last_error: Optional[Exception] = None
        for i in range(retries):
            try:
                content = self._request(prompt, system_prompt=system_prompt, force_json=True, timeout=t_out)
                payload = self._parse_json(content)
                if validate:
                    verdict = validate(payload)
                    if verdict.get("status") != "success":
                        raise ValueError(verdict.get("message", "json validation failed"))
                self._cache.set(cache_key, payload)
                return payload
            except Exception as e:
                last_error = e
                # Check for rate limit or server error to apply backoff
                is_rate_limit = False
                if isinstance(e, urllib.error.HTTPError) and e.code == 429:
                    is_rate_limit = True

                if i < retries - 1:
                    wait_time = (2 ** i) + (1 if is_rate_limit else 0)
                    time.sleep(wait_time)
        raise RuntimeError(f"LLM JSON request failed after {retries} retries: {last_error}")

    def _request(self, prompt: str, system_prompt: Optional[str], force_json: bool, timeout: Optional[int] = None) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if force_json:
            body["response_format"] = {"type": "json_object"}

        req = urllib.request.Request(
            self.url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as response:
            raw = json.loads(response.read().decode("utf-8"))
        return raw["choices"][0]["message"]["content"]

    def _parse_json(self, content: str) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        fence = re.search(r"```json\s*(.*?)\s*```", content, flags=re.DOTALL | re.IGNORECASE)
        if fence:
            return json.loads(fence.group(1))

        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
        raise ValueError("No valid JSON object found in LLM response")
