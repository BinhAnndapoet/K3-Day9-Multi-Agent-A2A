"""Policy Agent.

Nhận 3 report domain (order&seller, payment, delivery), áp bảng quy tắc EC_POLICY_V1 theo thứ tự
ưu tiên → ra Decision. LLM lý giải + chốt verdict; rules engine deterministic là source of truth và
được dùng để đối chứng (verify). Trả Decision đã đúng nghiệp vụ kèm corrections.
"""
from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from models import AgentReport, CaseContext, Decision
import rules


POLICY_TABLE = """EC_POLICY_V1 (áp dụng theo THỨ TỰ Ưu tiên từ trên xuống):
1. canceled_order_paid:    order_status=canceled VÀ tổng payment>0   → platform, refund=tổng payment, action=issue_full_refund,   root=ORDER_CANCELED_AFTER_PAYMENT
2. unavailable_order_paid: order_status=unavailable VÀ tổng payment>0 → platform, refund=tổng payment, action=issue_full_refund,   root=ORDER_UNAVAILABLE_AFTER_PAYMENT
3. late_delivery_seller:   delivered>estimated VÀ có seller handoff muộn (carrier_date>shipping_limit_date) → seller vi phạm, refund=tổng freight, action=refund_freight, root=SELLER_HANDOFF_AFTER_LIMIT
4. late_delivery_logistics:delivered>estimated VÀ KHÔNG có seller handoff muộn → logistics_provider, refund=tổng freight, action=refund_freight, root=CARRIER_DELIVERED_AFTER_ESTIMATE
5. valid_split_payment:    >=2 payment row VÀ |tổng payment-(item+freight)|<=0.10 BRL → không bên, refund=0, action=explain_valid_split_payment, root=MULTIPLE_PAYMENTS_RECONCILED
6. unsupported_late_claim: delivered<=estimated VÀ payment khớp → không bên, refund=0, action=reject_late_refund, root=DELIVERY_WITHIN_ESTIMATE"""


class PolicyAgent(BaseAgent):
    name = "policy_agent"

    def system_prompt(self) -> str:
        return (
            "Bạn là Policy Agent. Áp dụng bảng chính sách EC_POLICY_V1 (đính kèm) theo đúng thứ tự "
            "ưu tiên để ra quyết định duy nhất cho case. Chọn quy tắc đầu tiên thoả mãn. "
            "Không bịa số liệu; chỉ dùng facts domain agent cung cấp."
        )

    def expected_schema(self) -> dict[str, Any]:
        return {
            "primary_issue": "str",
            "root_cause_code": "str",
            "responsible_parties": "list[{party_type,party_id}]",
            "case_status": "str",
            "recommended_refund": "float",
            "resolution_actions": "list[str]",
            "matched_rule_index": "int",
        }

    def build_user_message(self, ctx: CaseContext, reports: dict[str, AgentReport]) -> tuple[str, dict[str, Any]]:
        # gộp facts từ 3 report domain
        os_facts = reports["order_seller_agent"].facts
        pay_facts = reports["payment_agent"].facts
        del_facts = reports["delivery_agent"].facts
        consolidated = {
            "order_status": os_facts.get("order_status"),
            "seller_handoff_late": os_facts.get("seller_handoff_late"),
            "late_handoff_seller_ids": os_facts.get("late_handoff_seller_ids", []),
            "payment_row_count": pay_facts.get("payment_row_count"),
            "payment_total": pay_facts.get("payment_total"),
            "expected_total": pay_facts.get("expected_total"),
            "payment_matches": pay_facts.get("payment_matches"),
            "is_late_delivery": del_facts.get("is_late_delivery"),
        }
        msg = (
            f"{POLICY_TABLE}\n\n"
            f"Case {ctx.case_id}, order_id={ctx.claimed_order_id}.\n"
            f"Facts domain: {json.dumps(consolidated, ensure_ascii=False)}\n"
            f"Áp quy tắc và trả quyết định."
        )
        return msg, consolidated

    def verify(self, ctx: CaseContext, facts: dict[str, Any], llm_verdict: dict[str, Any], decision: Decision) -> list[str]:
        corrections: list[str] = []
        mapping = {
            "primary_issue": decision.primary_issue,
            "root_cause_code": decision.root_cause_code,
            "case_status": decision.case_status,
        }
        for k, expected in mapping.items():
            if k in llm_verdict and str(llm_verdict[k]) != str(expected):
                corrections.append(f"{k}: LLM={llm_verdict[k]} vs deterministic={expected}")
        if "recommended_refund" in llm_verdict:
            try:
                if abs(float(llm_verdict["recommended_refund"]) - float(decision.refund)) > 0.01:
                    corrections.append(
                        f"recommended_refund: LLM={llm_verdict['recommended_refund']} vs deterministic={decision.refund}"
                    )
            except (TypeError, ValueError):
                corrections.append("recommended_refund: LLM không parse được")
        return corrections

    # ---- chạy riêng (cần reports) ----
    def run(self, ctx: CaseContext, reports: dict[str, AgentReport]) -> tuple[Decision, AgentReport]:
        user_msg, consolidated = self.build_user_message(ctx, reports)
        system = self.system_prompt()
        schema = self.expected_schema()
        full_user = (
            user_msg
            + f"\n\nTrả JSON có 'reasoning' và các trường: {list(schema.keys())}."
        )
        verdict, reasoning, tokens = self.llm.chat_json(system, full_user)

        # SOURCE OF TRUTH: rules engine deterministic
        decision = rules.classify(ctx)
        corrections = self.verify(ctx, consolidated, verdict, decision)
        return decision, AgentReport(
            agent=self.name,
            facts={**consolidated, "decision_primary_issue": decision.primary_issue},
            llm_reasoning=reasoning,
            llm_verdict=verdict,
            corrections=corrections,
            tokens=tokens,
        )
