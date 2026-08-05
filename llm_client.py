"""LLM client wrapper: gpt-4o-mini qua OpenAI SDK.

Mọi agent gọi qua ``LLMClient.chat_json`` để lấy verdict dạng JSON + reasoning. Hàm này fail-soft:
nếu API lỗi/thiếu key, trả verdict rỗng để pipeline vẫn chạy được bằng nhánh deterministic
(đảm bảo không bao giờ đứt luồng 50 case vì lý do mạng).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from config import LLM_MAX_TOKENS, LLM_TEMPERATURE, LLM_TIMEOUT, MODEL_NAME, OPENAI_API_KEY, OPENAI_BASE_URL

log = logging.getLogger("llm")


class LLMClient:
    _instance: "LLMClient | None" = None

    def __init__(self) -> None:
        self.client: OpenAI | None = None
        if OPENAI_API_KEY:
            try:
                self.client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL, timeout=LLM_TIMEOUT)
            except Exception as exc:  # pragma: no cover
                log.warning("Không khởi tạo được OpenAI client: %s", exc)
                self.client = None
        else:
            log.warning("OPENAI_API_KEY trống — pipeline sẽ chạy nhánh deterministic (không gọi LLM).")

    @classmethod
    def get(cls) -> "LLMClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def available(self) -> bool:
        return self.client is not None

    def chat_json(self, system: str, user: str) -> tuple[dict[str, Any], str, dict[str, int]]:
        """Trả (verdict_dict, reasoning_str, tokens). Fail-soft → ({}, "", {}) khi lỗi."""
        if self.client is None:
            return {}, "", {}
        try:
            resp = self.client.chat.completions.create(
                model=MODEL_NAME,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            content = resp.choices[0].message.content or "{}"
            data = json.loads(content)
            usage = resp.usage
            tokens = {
                "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                "completion_tokens": getattr(usage, "completion_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            } if usage else {}
            reasoning = str(data.get("reasoning", "")).strip()
            verdict = {k: v for k, v in data.items() if k != "reasoning"}
            return verdict, reasoning, tokens
        except Exception as exc:  # pragma: no cover
            log.warning("LLM call failed (%s) — dùng nhánh deterministic.", exc)
            return {}, "", {}
