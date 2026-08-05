"""Entry point: chạy pipeline multi-agent cho 50 case.

- Đọc input/input/EC_*.json
- Chạy Coordinator (6 agent) cho từng case
- Ghi output/EC_*.json
- Ghi logging/trace.jsonl (OVERWRITE, không append)
- Ghi logging/metadata.json
"""
from __future__ import annotations

import json
import platform
import sys
import time
from collections import Counter
from pathlib import Path

from config import (
    INPUT_DIR,
    LOG_DIR,
    METADATA_PATH,
    MODEL_NAME,
    MODEL_PARAM_SIZE,
    OUTPUT_DIR,
    TRACE_PATH,
)
from coordinator import Coordinator


def _load_inputs() -> list[dict]:
    files = sorted(Path(INPUT_DIR).glob("EC_*.json"))
    cases = []
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            cases.append(json.load(f))
    return cases


def write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    cases = _load_inputs()
    print(f"[main] Đã load {len(cases)} case từ {INPUT_DIR}")

    coord = Coordinator()
    all_trace: list[dict] = []
    distribution = Counter()
    started = time.time()

    for case in cases:
        cid = case.get("case_id")
        output, trace = coord.run_case(case)
        write_json(OUTPUT_DIR / f"{cid}.json", output.to_dict())
        all_trace.extend(trace)
        distribution[output.assessment["primary_issue"]] += 1
        status = output.assessment["case_status"]
        refund = output.financial_resolution["recommended_refund_brl"]
        print(f"  {cid}: {output.assessment['primary_issue']:24s} [{status}] refund={refund}")

    # trace.jsonl — overwrite
    with open(TRACE_PATH, "w", encoding="utf-8") as f:
        for rec in all_trace:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # metadata.json
    metadata = {
        "model": MODEL_NAME,
        "parameter_size": MODEL_PARAM_SIZE,
        "framework": f"Python {platform.python_version()} + openai SDK (orchestration multi-agent tự viết, không framework nặng)",
        "runtime": f"CPython {platform.python_version()} on {platform.system()} {platform.release()}",
        "agent_count": 6,
        "agents": [
            "coordinator", "order_seller_agent", "payment_agent",
            "delivery_agent", "policy_agent", "verifier_agent",
        ],
        "policy_version": "EC_POLICY_V1",
        "case_count": len(cases),
        "elapsed_seconds": round(time.time() - started, 2),
        "primary_issue_distribution": dict(distribution),
    }
    write_json(METADATA_PATH, metadata)

    print("\n[main] Phân bố primary_issue:")
    for issue, n in distribution.most_common():
        print(f"  {issue:28s} {n}")
    print(f"\n[main] Xong. output={OUTPUT_DIR}, trace={TRACE_PATH}, metadata={METADATA_PATH}")
    print(f"[main] Thời gian: {metadata['elapsed_seconds']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
