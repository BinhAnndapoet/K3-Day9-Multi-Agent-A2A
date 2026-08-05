"""Verifier Agent.

Kiểm chứng chéo cuối cùng: (1) tính lại Decision bằng rules engine độc lập, (2) lắp CaseOutput, (3)
validate evidence ID (dạng + tồn tại), số tiền, schema và các giới hạn cứng. Nếu LLM/Policy lệch,
verifier đè bằng kết quả deterministic. Trả về CaseOutput cuối cùng + report corrections.
"""
from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent
from models import AgentReport, CaseContext, CaseOutput, Decision
import output_builder
import rules


class VerifierAgent(BaseAgent):
    name = "verifier_agent"

    def system_prompt(self) -> str:
        return (
            "Bạn là Verifier Agent. Kiểm tra xem CaseOutput có: đúng schema, evidence ID đúng dạng "
            "(order/item/payment/seller/policy), số tiền khớp tính toán, case_status hợp lệ, "
            "confidence trong [0,1]. Trả 'ok': true/false và list 'issues'."
        )

    def expected_schema(self) -> dict[str, Any]:
        return {"ok": "bool", "issues": "list[str]"}

    def build_user_message(self, ctx: CaseContext, output: CaseOutput) -> tuple[str, dict[str, Any]]:
        t = rules.totals(ctx)
        facts = {
            "item_total": t["item_total"],
            "freight_total": t["freight_total"],
            "payment_total": t["payment_total"],
            "recommended_refund_should_be": output.financial_resolution["recommended_refund_brl"],
        }
        msg = (
            f"Case {ctx.case_id}.\n"
            f"Output cần kiểm tra: {json.dumps(output.to_dict(), ensure_ascii=False)}\n"
            f"Kiểm tra schema, evidence ID, số tiền, giới hạn."
        )
        return msg, facts

    def verify(self, ctx: CaseContext, facts: dict[str, Any], llm_verdict: dict[str, Any], output: CaseOutput) -> list[str]:
        # code-level validation là nguồn chính; LLM chỉ bổ sung
        code_issues = output_builder.validate(output, ctx)
        llm_issues = llm_verdict.get("issues", []) if isinstance(llm_verdict, dict) else []
        merged: list[str] = list(code_issues)
        for iss in llm_issues:
            if isinstance(iss, str) and iss not in merged:
                merged.append(f"LLM:{iss}")
        return merged

    def run(self, ctx: CaseContext, policy_decision: Decision, policy_report: AgentReport) -> tuple[CaseOutput, AgentReport]:
        # (1) nguồn sự thật độc lập — tính lại decision
        ground_truth = rules.classify(ctx)
        corrections: list[str] = []
        if ground_truth.primary_issue != policy_decision.primary_issue:
            corrections.append(
                f"policy.primary_issue={policy_decision.primary_issue} vs verifier={ground_truth.primary_issue} (đã đè)"
            )
        decision = ground_truth  # luôn lấy deterministic

        # (2) lắp output
        output = output_builder.build_case_output(ctx, decision)

        # (3) LLM cross-check (best effort)
        msg, facts = self.build_user_message(ctx, output)
        system = self.system_prompt()
        schema = self.expected_schema()
        full_user = msg + f"\nFacts tính lại: {facts}\nTrả JSON có các trường: {list(schema.keys())}."
        verdict, reasoning, tokens = self.llm.chat_json(system, full_user)

        corrections.extend(self.verify(ctx, facts, verdict, output))

        return output, AgentReport(
            agent=self.name,
            facts=facts,
            llm_reasoning=reasoning,
            llm_verdict=verdict,
            corrections=corrections,
            tokens=tokens,
        )
