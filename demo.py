"""Demo (Streamlit) — nhập case / order_id, pipeline multi-agent điều tra và trả kết quả.

Chạy:
    streamlit run demo.py

Tính năng:
- Chọn 1 trong 50 case có sẵn, HOẶC nhập order_id + nội dung khiếu nại tự do.
- Bấm "Điều tra case" → 6 agent chạy (Order&Seller → Payment → Delivery → Policy → Verifier).
- Xem kết quả: assessment, financial, evidence, root cause + responsible, actions,
  và chi tiết từng bước agent (facts deterministic, LLM reasoning/verdict, corrections).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from config import INPUT_DIR, MODEL_NAME
from coordinator import Coordinator
from llm_client import LLMClient
from models import CaseOutput

# Đặt trước mọi lệnh st.* khác.
st.set_page_config(
    page_title="K3 Day09 — Dispute Resolution",
    page_icon="🛒",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_cases() -> list[dict[str, Any]]:
    files = sorted(Path(INPUT_DIR).glob("EC_*.json"))
    out: list[dict[str, Any]] = []
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            out.append(json.load(f))
    return out


@st.cache_resource(show_spinner=False)
def get_coordinator() -> Coordinator:
    return Coordinator()


def build_custom_case(order_id: str, message: str, language: str) -> dict[str, Any]:
    return {
        "case_id": f"CUSTOM_{(order_id or 'x')[:8]}",
        "opened_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "customer_request": {
            "language": language,
            "message": message,
            "claimed_order_id": (order_id or "").strip(),
        },
        "policy_version": "EC_POLICY_V1",
    }


# ---------------------------------------------------------------------------
# Hiển thị
# ---------------------------------------------------------------------------
_STATUS_ICON = {"action_required": "⚠️", "no_action": "✅"}


def render_top_metrics(output: CaseOutput, elapsed: float) -> None:
    a = output.assessment
    fin = output.financial_resolution
    rca = output.root_cause_analysis
    icon = _STATUS_ICON.get(a["case_status"], "")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Primary issue", a["primary_issue"])
    c2.metric("Case status", f"{icon} {a['case_status']}")
    c3.metric("Confidence", f"{a['confidence']:.2f}")
    c4.metric("Refund đề xuất", f"{fin['recommended_refund_brl']:.2f} {fin['currency']}")

    st.caption(
        f"⏱ Thời gian: {elapsed:.2f}s · "
        f"Item total {fin['item_total_brl']:.2f} · Freight {fin['freight_total_brl']:.2f} · "
        f"Payment {fin['payment_total_brl']:.2f}"
    )

    parties = rca.get("responsible_parties", [])
    causes = rca.get("ranked_causes", [])
    pcol, ccol = st.columns(2)
    with pcol:
        st.markdown("**Bên chịu trách nhiệm**")
        if parties:
            for p in parties:
                st.markdown(f"- `{p['party_type']}` → `{p['party_id']}`")
        else:
            st.markdown("- _không bên nào_")
    with ccol:
        st.markdown("**Root cause**")
        if causes:
            for c in causes:
                st.markdown(f"- `{c['cause_code']}` (rank {c['rank']})")
        else:
            st.markdown("- _không có_")


def render_entities_and_evidence(output: CaseOutput) -> None:
    e = output.affected_entities
    ec1, ec2 = st.columns(2)
    with ec1:
        st.markdown("**Affected entities**")
        for key in ("order_ids", "item_ids", "seller_ids", "payment_ids"):
            vals = e.get(key, [])
            st.caption(f"{key} ({len(vals)})")
            if vals:
                st.code("\n".join(vals), language=None)
            else:
                st.caption("_rỗng_")
    with ec2:
        st.markdown(f"**Evidence IDs ({len(output.evidence_ids)})**")
        if output.evidence_ids:
            st.code("\n".join(output.evidence_ids), language=None)
        else:
            st.caption("_rỗng_")

    actions = output.resolution_actions
    st.markdown(f"**Resolution actions ({len(actions)})**")
    st.markdown(", ".join(f"`{a}`" for a in actions) if actions else "_rỗng_")


def render_trace(trace: list[dict[str, Any]]) -> None:
    n_corr_total = 0
    with st.expander(f"🔎 Chi tiết pipeline ({len(trace)} bước agent)", expanded=False):
        for rec in trace:
            agent = rec.get("agent", "?")
            corrections = rec.get("corrections") or []
            n_corr_total += len(corrections)
            title = f"**{agent}**"
            if corrections:
                title += f" · ⚠ {len(corrections)} correction"
            with st.expander(title, expanded=False):
                # facts
                facts = rec.get("facts") or {}
                if facts:
                    st.caption("Facts (deterministic — source of truth)")
                    st.json(facts)

                # reasoning
                reasoning = (rec.get("llm_reasoning") or "").strip()
                if reasoning:
                    st.caption("LLM reasoning")
                    if reasoning.startswith("{") or reasoning.startswith("["):
                        try:
                            st.json(json.loads(reasoning))
                        except Exception:
                            st.write(reasoning)
                    else:
                        st.write(reasoning)

                # verdict
                verdict = rec.get("llm_verdict") or {}
                if verdict:
                    st.caption("LLM verdict")
                    st.json(verdict)

                # decision (policy)
                if "decision" in rec:
                    st.caption("Decision")
                    st.json(rec["decision"])

                # final output (verifier)
                if "final_output" in rec:
                    st.caption("Final output")
                    st.json(rec["final_output"])

                # corrections
                if corrections:
                    st.warning("LLM lệch deterministic → đã đè bằng kết quả đúng:")
                    for c in corrections:
                        st.markdown(f"- {c}")
                elif rec.get("llm_verdict") or rec.get("llm_reasoning"):
                    st.success("LLM khớp deterministic.")

                tokens = rec.get("tokens") or {}
                if tokens:
                    st.caption(f"tokens: {tokens}")

                if "warning" in rec:
                    st.info(rec["warning"])

    return n_corr_total


def render_result(case: dict, output: CaseOutput, trace: list[dict], elapsed: float) -> None:
    cr = case.get("customer_request", {})
    st.subheader(f"Kết quả — {case.get('case_id', '?')}")
    st.caption(
        f"order_id: `{cr.get('claimed_order_id', '')}` · "
        f"language: {cr.get('language', '')}"
    )
    msg = cr.get("message", "")
    if msg:
        with st.expander("Nội dung khiếu nại", expanded=False):
            st.write(msg)

    render_top_metrics(output, elapsed)
    st.divider()
    render_entities_and_evidence(output)

    n_corr = render_trace(trace)
    st.caption(f"Tổng số correction (LLM bị đè): {n_corr} · Verifier luôn lấy deterministic làm source of truth.")

    with st.expander(" Raw output JSON", expanded=False):
        st.json(output.to_dict())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    st.title("🛒 Multi-Agent E-commerce Dispute Resolution")
    st.caption(
        f"K3 Day 09 · Model `{MODEL_NAME}` · 6 agent (Coordinator → Order&Seller → Payment → "
        "Delivery → Policy → Verifier) · rules engine là source of truth."
    )

    cases = load_cases()
    by_id: dict[str, dict] = {c.get("case_id", ""): c for c in cases}

    # ---------------- Sidebar: nhập query ----------------
    with st.sidebar:
        st.header("Nhập query")
        mode = st.radio(
            "Chế độ",
            ["Chọn case có sẵn (50)", "Nhập order_id tự do"],
            index=0,
        )

        case: dict[str, Any] | None = None
        if mode == "Chọn case có sẵn (50)":
            cid = st.selectbox("Case ID", options=list(by_id), index=0)
            case = by_id[cid]
            cr = case.get("customer_request", {})
            st.caption(f"order_id: `{cr.get('claimed_order_id', '')}`")
            st.caption(f"opened_at: {case.get('opened_at', '')}")
            st.text_area(
                "message", value=cr.get("message", ""), height=90, disabled=True
            )
        else:
            order_id = st.text_input(
                "claimed_order_id (Olist order_id)",
                placeholder="vd: e2a03ccf5ea816036608b2d8c3ab8e60",
            )
            message = st.text_area(
                "Nội dung khiếu nại (tuỳ chọn)",
                placeholder="vd: Đơn hàng của tôi giao trễ, kiểm tra nguyên nhân và quyền lợi.",
                height=90,
            )
            language = st.selectbox("Ngôn ngữ", ["vi", "en", "pt"], index=0)
            if order_id.strip():
                case = build_custom_case(order_id, message, language)

        st.divider()
        llm_on = LLMClient.get().available
        st.caption("LLM: " + ("🟢 ON (gọi gpt-4o-mini)" if llm_on else "🟡 OFF — nhánh deterministic"))
        run = st.button("🔍 Điều tra case", type="primary", use_container_width=True)
        st.caption("ℹ Demo không ghi file output/trace.")

    # ---------------- Chạy ----------------
    if run:
        if not case or not case.get("customer_request", {}).get("claimed_order_id", "").strip():
            st.warning("Vui lòng nhập order_id hợp lệ.")
            return
        with st.spinner("Pipeline đang điều tra (Order → Payment → Delivery → Policy → Verifier)..."):
            import time as _t

            coord = get_coordinator()
            t0 = _t.time()
            try:
                output, trace = coord.run_case(case)
            except Exception as exc:
                st.error(f"Pipeline lỗi: {exc}")
                return
            elapsed = _t.time() - t0
        st.session_state["last"] = (case, output, trace, elapsed)

    last = st.session_state.get("last")
    if last:
        render_result(*last)
    else:
        st.info("👆 Chọn/ nhập query ở thanh bên rồi bấm **Điều tra case**.")


if __name__ == "__main__":
    main()
