"""Các dataclass dùng chung: context truyền giữa agent, report của từng agent, và decision cuối.

Các cấu trúc này chính là **hợp đồng handoff** giữa các agent (coordinator -> domain agents ->
policy -> verifier). Giữ typed để dễ verify và để trace rõ ràng.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class OrderRow:
    order_id: str
    customer_id: str
    order_status: str
    order_purchase_timestamp: str
    order_approved_at: str
    order_delivered_carrier_date: str
    order_delivered_customer_date: str
    order_estimated_delivery_date: str


@dataclass
class ItemRow:
    order_id: str
    order_item_id: int
    product_id: str
    seller_id: str
    shipping_limit_date: str
    price: float
    freight_value: float


@dataclass
class PaymentRow:
    order_id: str
    payment_sequential: int
    payment_type: str
    payment_installments: int
    payment_value: float


# ---------------------------------------------------------------------------
# Case context (coordinator đóng gói rồi handoff)
# ---------------------------------------------------------------------------
@dataclass
class CaseContext:
    case_id: str
    opened_at: str
    language: str
    message: str
    claimed_order_id: str
    policy_version: str
    order: OrderRow | None = None
    items: list[ItemRow] = field(default_factory=list)
    payments: list[PaymentRow] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Report của từng domain agent
# ---------------------------------------------------------------------------
@dataclass
class AgentReport:
    agent: str
    facts: dict[str, Any]           # phép tính deterministic (source of truth)
    llm_reasoning: str = ""         # lý giải của LLM
    llm_verdict: dict[str, Any] = field(default_factory=dict)  # verdict LLM trả về
    corrections: list[str] = field(default_factory=list)       # chênh giữa LLM và deterministic
    tokens: dict[str, int] = field(default_factory=dict)


@dataclass
class Decision:
    """Kết quả áp EC_POLICY_V1 (từ rules engine — source of truth)."""
    primary_issue: str
    root_cause_code: str
    responsible_parties: list[dict[str, str]]  # [{party_type, party_id}]
    case_status: str                            # action_required | no_action
    refund: float
    actions: list[str]
    confidence: float


# ---------------------------------------------------------------------------
# Output schema cuối (map 1-1 với yêu cầu README mục 6)
# ---------------------------------------------------------------------------
@dataclass
class CaseOutput:
    case_id: str
    assessment: dict[str, Any]
    affected_entities: dict[str, list[str]]
    root_cause_analysis: dict[str, Any]
    evidence_ids: list[str]
    financial_resolution: dict[str, Any]
    resolution_actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
