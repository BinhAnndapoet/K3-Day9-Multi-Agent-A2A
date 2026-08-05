"""Payment Agent.

Domain: đối soát payment rows với item + freight. Evidence: payment:<order_id>:<payment_sequential>.
"""
from __future__ import annotations

from typing import Any

from agents.base import BaseAgent
from config import PAYMENT_TOLERANCE_BRL
from models import CaseContext
from rules import totals


class PaymentAgent(BaseAgent):
    name = "payment_agent"

    def system_prompt(self) -> str:
        return (
            "Bạn là Payment Agent trong hệ thống giải khiếu nại Olist. "
            "Chỉ phân tích domain THANH TOÁN: số payment row, payment_type, tổng payment_value, "
            "và đối soát với item_total + freight_total (cho phép sai số <= "
            f"{PAYMENT_TOLERANCE_BRL} BRL). "
            "KHÔNG bàn về trạng thái đơn hay ngày giao. Không bịa payment row."
        )

    def expected_schema(self) -> dict[str, Any]:
        return {
            "payment_row_count": "int",
            "payment_total": "float",
            "expected_total": "float",
            "payment_matches": "bool",
            "is_split_payment": "bool",
        }

    def build_user_message(self, ctx: CaseContext) -> tuple[str, dict[str, Any]]:
        t = totals(ctx)
        facts = {
            "payment_rows": [
                {
                    "payment_sequential": p.payment_sequential,
                    "payment_type": p.payment_type,
                    "payment_value": p.payment_value,
                }
                for p in ctx.payments
            ],
            "payment_row_count": len(ctx.payments),
            "payment_total": t["payment_total"],
            "expected_total": t["expected_total"],
            "payment_matches": abs(t["payment_total"] - t["expected_total"]) <= PAYMENT_TOLERANCE_BRL,
            "is_split_payment": len(ctx.payments) >= 2,
        }
        msg = (
            f"Case {ctx.case_id}, order_id={ctx.claimed_order_id}. "
            f"{facts['payment_row_count']} payment row, tổng {facts['payment_total']} BRL, "
            f"kỳ vọng {facts['expected_total']} BRL. Khách lo bị thu trùng — đối soát giúp."
        )
        return msg, facts

    def verify(self, ctx: CaseContext, facts: dict[str, Any], llm_verdict: dict[str, Any]) -> list[str]:
        corrections: list[str] = []
        for key in ("payment_total", "expected_total", "payment_row_count"):
            if key in llm_verdict:
                try:
                    if abs(float(llm_verdict[key]) - float(facts[key])) > 1e-6 and key != "payment_row_count":
                        corrections.append(f"{key}: LLM={llm_verdict[key]} vs deterministic={facts[key]}")
                    elif key == "payment_row_count" and int(llm_verdict[key]) != int(facts[key]):
                        corrections.append(f"{key}: LLM={llm_verdict[key]} vs deterministic={facts[key]}")
                except (TypeError, ValueError):
                    corrections.append(f"{key}: LLM={llm_verdict[key]} không parse được")
        if "payment_matches" in llm_verdict and bool(llm_verdict["payment_matches"]) != bool(facts["payment_matches"]):
            corrections.append(
                f"payment_matches: LLM={llm_verdict['payment_matches']} vs deterministic={facts['payment_matches']}"
            )
        return corrections
