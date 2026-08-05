"""Order & Seller Agent.

Domain: trạng thái đơn, danh sách item, seller, và mốc carrier nhận hàng vs shipping_limit_date
của từng item (xác định seller có bàn giao muộn hay không). Evidence: order, item, seller.
"""
from __future__ import annotations

from typing import Any

from agents.base import BaseAgent
from models import CaseContext
from rules import late_seller_ids


class OrderSellerAgent(BaseAgent):
    name = "order_seller_agent"

    def system_prompt(self) -> str:
        return (
            "Bạn là Order & Seller Agent trong hệ thống giải khiếu nại Olist. "
            "Chỉ phân tích domain ĐƠN HÀNG & SELLER: order_status, danh sách item, seller_id, "
            "shipping_limit_date và order_delivered_carrier_date. "
            "KHÔNG bàn về payment hay estimated delivery date (domain khác phụ trách). "
            "Quy ước: seller bị coi bàn giao muộn nếu order_delivered_carrier_date > shipping_limit_date "
            "của item đó (so sánh chuỗi timestamp). Chỉ đưa kết luận dựa trên dữ liệu cho, không bịa."
        )

    def expected_schema(self) -> dict[str, Any]:
        return {
            "order_status": "str",
            "item_count": "int",
            "seller_ids": "list[str]",
            "late_handoff_seller_ids": "list[str]",
            "seller_handoff_late": "bool",
        }

    def build_user_message(self, ctx: CaseContext) -> tuple[str, dict[str, Any]]:
        order = ctx.order
        items = ctx.items
        late_ids = late_seller_ids(order, items) if order else []
        facts = {
            "order_status": order.order_status if order else None,
            "order_delivered_carrier_date": order.order_delivered_carrier_date if order else None,
            "item_count": len(items),
            "seller_ids": list(dict.fromkeys(it.seller_id for it in items)),
            "items": [
                {
                    "order_item_id": it.order_item_id,
                    "seller_id": it.seller_id,
                    "shipping_limit_date": it.shipping_limit_date,
                    "price": it.price,
                    "freight_value": it.freight_value,
                }
                for it in items
            ],
            "late_handoff_seller_ids": late_ids,
            "seller_handoff_late": len(late_ids) > 0,
        }
        msg = (
            f"Case {ctx.case_id}, order_id={ctx.claimed_order_id}.\n"
            f"Đơn hàng: status={facts['order_status']}, "
            f"carrier_date={facts['order_delivered_carrier_date']}, "
            f"số item={facts['item_count']}. Hãy xác nhận seller nào bàn giao muộn."
        )
        return msg, facts

    def verify(self, ctx: CaseContext, facts: dict[str, Any], llm_verdict: dict[str, Any]) -> list[str]:
        corrections: list[str] = []
        expected_late = sorted(facts.get("late_handoff_seller_ids", []))
        got = llm_verdict.get("late_handoff_seller_ids", [])
        got_sorted = sorted(got) if isinstance(got, list) else []
        if got and got_sorted != expected_late:
            corrections.append(
                f"late_handoff_seller_ids: LLM={got_sorted} vs deterministic={expected_late}"
            )
        if "seller_handoff_late" in llm_verdict and bool(llm_verdict["seller_handoff_late"]) != bool(expected_late):
            corrections.append(
                f"seller_handoff_late: LLM={llm_verdict['seller_handoff_late']} vs deterministic={bool(expected_late)}"
            )
        return corrections
