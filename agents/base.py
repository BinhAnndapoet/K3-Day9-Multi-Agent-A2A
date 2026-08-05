"""Base class cho các domain agent.

Mỗi agent: (1) thu thập dữ liệu domain hẹp, (2) tính facts deterministic, (3) gọi LLM để lý giải +
đối chứng, (4) ghi nhận correction khi LLM lệch deterministic, (5) trả AgentReport để handoff.

Cấu trúc này đảm bảo có phân công thật + handoff + verify, không gộp vào 1 prompt.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from llm_client import LLMClient
from models import AgentReport, CaseContext


class BaseAgent(ABC):
    name: str = "base"

    def __init__(self) -> None:
        self.llm = LLMClient.get()

    @abstractmethod
    def system_prompt(self) -> str: ...

    @abstractmethod
    def build_user_message(self, ctx: CaseContext) -> tuple[str, dict[str, Any]]:
        """Trả (user_content, deterministic_facts)."""

    @abstractmethod
    def expected_schema(self) -> dict[str, Any]:
        """Mô tả các trường verdict LLM cần trả về (cho prompt)."""

    @abstractmethod
    def verify(self, ctx: CaseContext, facts: dict[str, Any], llm_verdict: dict[str, Any]) -> list[str]:
        """So sánh verdict LLM với facts deterministic → list correction."""

    # ---- luồng chung ----
    def run(self, ctx: CaseContext) -> AgentReport:
        user_msg, facts = self.build_user_message(ctx)
        system = self.system_prompt()
        schema = self.expected_schema()
        full_user = (
            user_msg
            + f"\n\nPhép tính deterministic (đã đúng, dùng để đối chứng): {facts}"
            + f"\n\nTrả JSON có ключ 'reasoning' và đúng các trường: {list(schema.keys())}."
        )
        verdict, reasoning, tokens = self.llm.chat_json(system, full_user)
        corrections = self.verify(ctx, facts, verdict)
        return AgentReport(
            agent=self.name,
            facts=facts,
            llm_reasoning=reasoning,
            llm_verdict=verdict,
            corrections=corrections,
            tokens=tokens,
        )
