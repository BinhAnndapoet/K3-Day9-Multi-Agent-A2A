"""Delivery Agent.

Domain: so sánh delivered_customer_date với estimated_delivery_date (có giao trễ không).
"""
from __future__ import annotations

from typing import Any

from agents.base import BaseAgent
from models import CaseContext
from rules import is_late_delivery


class DeliveryAgent(BaseAgent):
    name = "delivery_agent"

    def system_prompt(self) -> str:
        return (
            "Bạn là Delivery Agent trong hệ thống giải khiếu nại Olist. "
            "Chỉ trả lời: đơn có giao TRỄ hay không, bằng cách so order_delivered_customer_date "
            "với order_estimated_delivery_date (so sánh chuỗi timestamp). "
            "KHÔNG kết luận ai chịu trách nhiệm — chỉ xác nhận độ trễ."
        )

    def expected_schema(self) -> dict[str, Any]:
        return {
            "delivered_customer_date": "str",
            "estimated_delivery_date": "str",
            "is_late_delivery": "bool",
        }

    def build_user_message(self, ctx: CaseContext) -> tuple[str, dict[str, Any]]:
        order = ctx.order
        facts = {
            "delivered_customer_date": order.order_delivered_customer_date if order else None,
            "estimated_delivery_date": order.order_estimated_delivery_date if order else None,
            "is_late_delivery": is_late_delivery(order) if order else False,
        }
        msg = (
            f"Case {ctx.case_id}, order_id={ctx.claimed_order_id}. "
            f"delivered={facts['delivered_customer_date']}, estimated={facts['estimated_delivery_date']}. "
            f"Đơn có giao sau estimated date không?"
        )
        return msg, facts

    def verify(self, ctx: CaseContext, facts: dict[str, Any], llm_verdict: dict[str, Any]) -> list[str]:
        corrections: list[str] = []
        if "is_late_delivery" in llm_verdict and bool(llm_verdict["is_late_delivery"]) != bool(facts["is_late_delivery"]):
            corrections.append(
                f"is_late_delivery: LLM={llm_verdict['is_late_delivery']} vs deterministic={facts['is_late_delivery']}"
            )
        return corrections
