"""Lắp ráp CaseOutput cuối cùng từ ctx + Decision, kèm validate evidence ID & giới hạn.

Tách riêng để cả Verifier và (khi cần) các test đều dùng chung một nguồn dựng output → tránh lệch.
"""
from __future__ import annotations

import re

from config import (
    LIMIT_ACTIONS,
    LIMIT_ENTITY_IDS,
    LIMIT_EVIDENCE,
    LIMIT_RESPONSIBLE,
    LIMIT_ROOT_CAUSES,
)
from data_layer import load_orders, load_sellers
from models import CaseOutput, Decision
import rules

VALID_ROOT_CAUSES = {
    "SELLER_HANDOFF_AFTER_LIMIT",
    "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "ORDER_CANCELED_AFTER_PAYMENT",
    "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "MULTIPLE_PAYMENTS_RECONCILED",
    "DELIVERY_WITHIN_ESTIMATE",
}

_EVIDENCE_RE = re.compile(r"^(order|item|payment|seller|policy):([^:]+(:[^:]+)?)$")


def _evidence_exists(eid: str, ctx) -> bool:
    prefix, _, body = eid.partition(":")
    if prefix == "order":
        return body in load_orders()
    if prefix == "seller":
        return body in load_sellers()
    if prefix == "policy":
        return body in VALID_ROOT_CAUSES
    if prefix == "item":
        oid, _, iid = body.partition(":")
        return any(it.order_id == oid and str(it.order_item_id) == iid for it in ctx.items) if ctx.items else False
        # note: items belong to claimed order
    if prefix == "payment":
        oid, _, seq = body.partition(":")
        return any(p.order_id == oid and str(p.payment_sequential) == seq for p in ctx.payments) if ctx.payments else False
    return False


def build_evidence(ctx, decision: Decision) -> list[str]:
    order_id = ctx.claimed_order_id
    evidence: list[str] = []

    def add(e: str) -> None:
        if e not in evidence and _evidence_exists(e, ctx):
            evidence.append(e)

    # Thứ tự + quy tắc theo ground-truth chuẩn:
    #   order → seller (CHỈ khi seller chịu trách nhiệm) → payment(s) → policy → item(s)
    if ctx.order is not None:
        add(f"order:{order_id}")

    responsible_sellers = [p["party_id"] for p in decision.responsible_parties if p["party_type"] == "seller"]
    for sid in responsible_sellers:
        add(f"seller:{sid}")

    for p in ctx.payments:
        add(f"payment:{order_id}:{p.payment_sequential}")

    add(f"policy:{decision.root_cause_code}")

    for it in ctx.items:
        add(f"item:{order_id}:{it.order_item_id}")

    return evidence[:LIMIT_EVIDENCE]


def build_case_output(ctx, decision: Decision) -> CaseOutput:
    order_id = ctx.claimed_order_id
    t = rules.totals(ctx)

    item_ids = [f"{order_id}:{it.order_item_id}" for it in ctx.items][:LIMIT_ENTITY_IDS]
    seller_ids = [sid for sid in dict.fromkeys(it.seller_id for it in ctx.items)][:LIMIT_ENTITY_IDS]
    payment_ids = [f"{order_id}:{p.payment_sequential}" for p in ctx.payments][:LIMIT_ENTITY_IDS]
    order_ids = [order_id] if ctx.order is not None else []

    return CaseOutput(
        case_id=ctx.case_id,
        assessment={
            "primary_issue": decision.primary_issue,
            "case_status": decision.case_status,
            "confidence": round(float(decision.confidence), 2),
        },
        affected_entities={
            "order_ids": order_ids,
            "item_ids": item_ids,
            "seller_ids": seller_ids,
            "payment_ids": payment_ids,
        },
        root_cause_analysis={
            "ranked_causes": [{"cause_code": decision.root_cause_code, "rank": 1}][:LIMIT_ROOT_CAUSES],
            "responsible_parties": decision.responsible_parties[:LIMIT_RESPONSIBLE],
        },
        evidence_ids=build_evidence(ctx, decision),
        financial_resolution={
            "currency": "BRL",
            "item_total_brl": t["item_total"],
            "freight_total_brl": t["freight_total"],
            "payment_total_brl": t["payment_total"],
            "recommended_refund_brl": rules.round2(decision.refund),
        },
        resolution_actions=decision.actions[:LIMIT_ACTIONS],
    )


def validate(output: CaseOutput, ctx) -> list[str]:
    """Trả danh sách lỗi schema/ID/giới hạn phát hiện được (rỗng = OK)."""
    issues: list[str] = []
    if output.assessment["case_status"] not in ("action_required", "no_action"):
        issues.append("case_status sai giá trị")
    if not (0.0 <= output.assessment["confidence"] <= 1.0):
        issues.append("confidence ngoài [0,1]")
    if len(output.evidence_ids) > LIMIT_EVIDENCE:
        issues.append("evidence > 10")
    for eid in output.evidence_ids:
        if not _EVIDENCE_RE.match(eid):
            issues.append(f"evidence sai dạng: {eid}")
        elif not _evidence_exists(eid, ctx):
            issues.append(f"evidence không tồn tại: {eid}")
    for key in ("order_ids", "item_ids", "seller_ids", "payment_ids"):
        if len(output.affected_entities[key]) > LIMIT_ENTITY_IDS:
            issues.append(f"{key} > 5")
    if len(output.root_cause_analysis["ranked_causes"]) > LIMIT_ROOT_CAUSES:
        issues.append("ranked_causes > 3")
    if len(output.root_cause_analysis["responsible_parties"]) > LIMIT_RESPONSIBLE:
        issues.append("responsible_parties > 3")
    if len(output.resolution_actions) > LIMIT_ACTIONS:
        issues.append("actions > 5")
    return issues
