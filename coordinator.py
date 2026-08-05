"""Coordinator Agent: nhận case, truy xuất dữ liệu, phân việc cho 5 domain agent theo luồng handoff
cố định, gộp kết quả, ghi trace. Đây là "nhân viên CSKH" điều phối các bộ phận riêng biệt.
"""
from __future__ import annotations

from typing import Any

from agents.delivery_agent import DeliveryAgent
from agents.order_seller_agent import OrderSellerAgent
from agents.payment_agent import PaymentAgent
from agents.policy_agent import PolicyAgent
from agents.verifier_agent import VerifierAgent
from data_layer import get_items, get_order, get_payments
from models import AgentReport, CaseContext, CaseOutput, Decision
import output_builder
import rules


class Coordinator:
    def __init__(self) -> None:
        self.order_seller = OrderSellerAgent()
        self.payment = PaymentAgent()
        self.delivery = DeliveryAgent()
        self.policy = PolicyAgent()
        self.verifier = VerifierAgent()

    # ---- xây context từ case JSON ----
    @staticmethod
    def build_context(case: dict[str, Any]) -> CaseContext:
        cr = case.get("customer_request", {})
        order_id = cr.get("claimed_order_id", "")
        order = get_order(order_id)
        items = get_items(order_id) if order else []
        payments = get_payments(order_id) if order else []
        return CaseContext(
            case_id=case.get("case_id", ""),
            opened_at=case.get("opened_at", ""),
            language=cr.get("language", ""),
            message=cr.get("message", ""),
            claimed_order_id=order_id,
            policy_version=case.get("policy_version", ""),
            order=order,
            items=items,
            payments=payments,
        )

    # ---- luồng chính cho 1 case ----
    def run_case(self, case: dict[str, Any]) -> tuple[CaseOutput, list[dict[str, Any]]]:
        ctx = self.build_context(case)
        trace: list[dict[str, Any]] = []
        cid = ctx.case_id

        def log(agent: str, report: AgentReport, extra: dict[str, Any] | None = None) -> None:
            trace.append({
                "case_id": cid,
                "agent": agent,
                "input_summary": {"claimed_order_id": ctx.claimed_order_id, "order_status": ctx.order.order_status if ctx.order else None},
                "facts": report.facts,
                "llm_reasoning": report.llm_reasoning,
                "llm_verdict": report.llm_verdict,
                "corrections": report.corrections,
                "tokens": report.tokens,
                **(extra or {}),
            })

        # Order không tìm thấy → output tối thiểu 
        if ctx.order is None:
            output = self._missing_order_output(ctx)
            trace.append({
                "case_id": cid,
                "agent": "coordinator",
                "warning": "claimed_order_id không có trong orders CSV",
                "output": output.to_dict(),
            })
            return output, trace

        # 1. Order & Seller
        r1 = self.order_seller.run(ctx)
        log("order_seller_agent", r1)

        # 2. Payment
        r2 = self.payment.run(ctx)
        log("payment_agent", r2)

        # 3. Delivery
        r3 = self.delivery.run(ctx)
        log("delivery_agent", r3)

        # 4. Policy (handoff 3 report)
        reports = {
            "order_seller_agent": r1,
            "payment_agent": r2,
            "delivery_agent": r3,
        }
        decision, r4 = self.policy.run(ctx, reports)
        log("policy_agent", r4, {"decision": _decision_dict(decision)})

        # 5. Verifier (handoff policy decision) → output cuối
        output, r5 = self.verifier.run(ctx, decision, r4)
        log("verifier_agent", r5, {"final_output": output.to_dict()})

        return output, trace

    @staticmethod
    def _missing_order_output(ctx: CaseContext) -> CaseOutput:
        decision = Decision(
            primary_issue="unsupported_late_claim",
            root_cause_code="DELIVERY_WITHIN_ESTIMATE",
            responsible_parties=[],
            case_status="no_action",
            refund=0.0,
            actions=["reject_late_refund"],
            confidence=1.0,
        )
        return output_builder.build_case_output(ctx, decision)


def _decision_dict(d: Decision) -> dict[str, Any]:
    return {
        "primary_issue": d.primary_issue,
        "root_cause_code": d.root_cause_code,
        "responsible_parties": d.responsible_parties,
        "case_status": d.case_status,
        "refund": rules.round2(d.refund),
        "actions": d.actions,
        "confidence": d.confidence,
    }
