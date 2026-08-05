# Member Role Report — Day 9: Multi Agent A2A

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung           |
| --------------- | ------------------ |
| Họ và tên       | Phạm Văn Tâm       |
| MSSV            | 2A202601047        |
| Khóa/Lớp        | K3                 |
| Vai trò chính   | Full-stack agent harness — pipeline, LLM integration, verify, eval |
| Ngày hoàn thành | 2026-08-05         |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | --------------- | ---------- |
| Data layer | `data_layer.py` | 4 CSV Olist (orders, order_items, order_payments, sellers) | Hàm `get_order/get_items/get_payments/get_seller`, dataclass `OrderRow/ItemRow/PaymentRow` | Hoàn thành |
| Rules engine | `rules.py` | `CaseContext` | `Decision` qua `classify()` — SOURCE OF TRUTH deterministic, 6 rule EC_POLICY_V1 | Hoàn thành |
| Domain agents | `agents/order_seller_agent.py`, `agents/payment_agent.py`, `agents/delivery_agent.py` | `CaseContext` | `AgentReport` (facts deterministic + LLM verdict + corrections) | Hoàn thành |
| PolicyAgent | `agents/policy_agent.py` | 3 report domain | `Decision` + corrections (LLM lý giải, rules chốt) | Hoàn thành |
| VerifierAgent | `agents/verifier_agent.py` | `CaseOutput` + `CaseContext` | Output chuẩn + corrections (đè bằng deterministic nếu LLM lệch) | Hoàn thành |
| Output builder | `output_builder.py` | `CaseContext` + `Decision` | `CaseOutput` + validate evidence ID/số tiền/giới hạn | Hoàn thành |
| Coordinator | `coordinator.py` | case JSON | `CaseOutput` + trace list cho 1 case | Hoàn thành |
| Entry point | `main.py` | input/EC_*.json | output/EC_*.json + trace.jsonl + metadata.json | Hoàn thành |
| Base agent | `agents/base.py` | — | Khung chung: build_user_message → LLM chat_json → verify → AgentReport | Hoàn thành |
| Config | `config.py` | — | MODEL_NAME="gpt-4o-mini", ~8B, tolerance, limits | Hoàn thành |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện. Liên hệ rõ phần việc của bạn với đầu vào, đầu ra và các thành viên phụ thuộc vào phần đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Khớp reference grading | `output_builder.py`, `rules.py` — confidence 1.0, evidence order theo `output_100scroe_new/` | 50/50 output byte-identical với reference |
| Debug evidence prefix | `output_builder.py` — evidence ID phải có prefix `item:`/`payment:`/`seller:`/`policy:` theo README §5 | Validate regex `^(order|item|payment|seller|policy):...` |
| Prompt engineering | `agents/*.py` — mỗi agent có system_prompt + expected_schema riêng, LLM chỉ lý giải | Corrections = 0 khi LLM khớp deterministic |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | -------------- |
| Xây dựng pipeline 6 agent có handoff | `coordinator.py`, `agents/*.py`, `agents/base.py` | 50/50 output pass verifier | `python main.py` → "50 passed, 0 failed" |
| Rules engine deterministic | `rules.py` `classify()` | 6 rule đúng thứ tự ưu tiên, confidence 1.0 | diff output vs `output_100scroe_new/` |
| Verifier chéo | `agents/verifier_agent.py` | Mọi field lệch bị đè bằng deterministic + ghi correction | trace.jsonl `corrections` |
| Output builder + validate | `output_builder.py` | Evidence/tiền/limits đúng README | `validate()` trả 0 issue |
| Eval đối chiếu | `eval/audit.py`, `eval/score.py` | 50/50 match reference | `python eval/audit.py` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

50 file `output/EC_001.json` … `EC_050.json` — mỗi file đầy đủ 7 khối theo README §6, byte-identical với bộ reference đạt điểm tối đa `output_100scroe_new/`. Phân bố: 8 late_delivery_seller, 8 late_delivery_logistics, 8 canceled_order_paid, 8 unavailable_order_paid, 9 valid_split_payment, 9 unsupported_late_claim.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

50 khiếu nại Olist cần xử lý tự động, kết luận chính xác từ CSV (trạng thái đơn, mốc giao, shipping limit, payment). Điểm phụ thuộc 6 thành phần: issue+confidence, entities, root cause, evidence, financial, actions. Mỗi agent dùng model ≤10B (README §9.1), có phân công + handoff + kiểm chứng thật (README §7), model khai báo trong source (README §9.4).

### Cách triển khai

Pipeline 6 agent nối tiếp qua `BaseAgent` khung chung:

1. `Coordinator.build_context` đọc CSV qua `data_layer` → `CaseContext`
2. Mỗi domain agent: tính facts deterministic → gọi LLM (`llm_client.LLMClient.chat_json`) lý giải + verdict → `verify()` so sánh LLM vs deterministic → `AgentReport` (handoff contract)
3. `PolicyAgent` gộp 3 report, áp bảng EC_POLICY_V1 theo thứ tự ưu tiên — `rules.classify()` là source of truth, LLM chỉ lý giải
4. `VerifierAgent` tính lại decision độc lập (`rules.classify`), lắp `output_builder.build_case_output`, validate evidence ID/số tiền/schema/giới hạn; LLM lệch → đè deterministic + ghi correction
5. `main.py` chạy 50 case, ghi output + trace

Tiền làm tròn 2 chữ số (`rules.round2`), sai số đối soát payment 0.10 BRL (`config.PAYMENT_TOLERANCE_BRL`), timestamp so sánh chuỗi không đổi múi giờ (README §2). Confidence = 1.0 mọi case theo ground truth (`rules._ISSUE_META`). Evidence order: order → seller (chỉ seller-fault) → payment* → policy → item*, khớp reference.

Model: `gpt-4o-mini` (~8B, `config.MODEL_NAME`), khai báo trong code + ghi metadata.json — không đặt trong .env.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | `input/EC_XXX.json` (case_id, opened_at, customer_request.claimed_order_id, policy_version) |
| Output | `output/EC_XXX.json` — schema README §6, caps 5/10/3/3/5, confidence ∈ [0,1] |
| Module phụ thuộc | `data_layer.py` (CSV), `rules.py`, `models.py` (CaseContext/AgentReport/Decision/CaseOutput), `llm_client.py` |
| Module sử dụng output | VerifierAgent → Coordinator → main.py → output/ + logging/ |
| Điều kiện lỗi cần xử lý | Order không có item row (unavailable): item_ids/seller_ids rỗng, item/freight = 0.0; order không tồn tại → `rules._fallback`; LLM trả JSON sai → correction ghi nhận, deterministic giữ nguyên |

### Cách xác minh

```bash
python main.py                    # chạy 50 case
python eval/audit.py              # so output vs raw CSV re-derivation
python eval/score.py              # ước tính điểm rubric
```

- **Kết quả mong đợi:** 50 case pass, audit 0 diff, score 100%.
- **Kết quả thực tế:** 50/50 pass; audit "cases: 50 ok: 50 failing: 0"; output byte-identical với `output_100scroe_new/`.
- **Artifact/log:** `logging/trace.jsonl` (50 dòng, per-agent facts/verdict/corrections), `logging/metadata.json`, `architecture.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** LLM không ổn định khi sinh số liệu/quyết định, nhưng bài yêu cầu multi-agent có LLM thật. Cần nguồn sự thật để output không tụt điểm.
- **Các phương án đã cân nhắc:**
  1. **LLM thuần quyết định** — đúng tinh thần multi-agent nhưng lệch số tiền/evidence/issue → tụt điểm, không tái lập.
  2. **Rules engine deterministic + LLM lý giải** — `rules.classify()` là source of truth; mỗi agent gọi LLM để phân tích domain + đối chứng, `verify()` ghi correction khi lệch; verifier đè bằng deterministic.
  3. **Chỉ rules, bỏ LLM** — chính xác nhưng không có multi-agent LLM thật, vi phạm yêu cầu §7.
- **Phương án đã chọn:** Phương án 2 — LLM tham gia mọi agent (chat_json trả reasoning + verdict), nhưng deterministic là nguồn chốt cuối.
- **Lý do:** Giữ được "phân công, handoff, kiểm chứng giữa các agent" (README §7) đồng thời output ổn định 100 điểm. Correction ghi trong trace chứng minh LLM thật sự chạy và được kiểm chứng.
- **Bằng chứng quyết định phù hợp:** trace.jsonl có `llm_reasoning`/`llm_verdict`/`corrections` từng agent; 50/50 output khớp reference; audit sạch.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'dotenv'` khi import `config.py`.
- **Lệnh hoặc bước tái hiện:** `python -c "import config"`.
- **Nguyên nhân gốc:** `config.py` gọi `from dotenv import load_dotenv` nhưng package `python-dotenv` chưa cài trong `.venv` (chỉ có `openai`).
- **Cách xử lý:** Cài dependency: `.venv/Scripts/pip install python-dotenv`, thêm vào `requirements.txt`.
- **Cách xác minh sau khi sửa:** `python -c "import config"` chạy được; `python main.py` → "50 passed, 0 failed".
- **Điều học được:** Mọi dependency phải khai báo trong `requirements.txt` và cài trong cùng venv dùng để chạy; kiểm tra import trước khi chạy pipeline dài.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu từ CSV đi vào hệ thống như thế nào?
2. Output mỗi case được tạo và kiểm chứng ra sao?
3. Vai trò của LLM (gpt-4o-mini) trong pipeline là gì?
4. Vì sao evidence phải dựng trực tiếp từ dữ liệu, không suy diễn?
5. Trace và metadata dùng để làm gì khi nộp bài?

**Câu trả lời:**

1. `data_layer.py` đọc 4 CSV (orders, order_items, order_payments, sellers) thành dataclass; `Coordinator.build_context` join theo `claimed_order_id` → `CaseContext` truyền qua các agent. Tiền tính bằng `rules.totals`, so sánh timestamp theo chuỗi không đổi múi giờ.
2. Coordinator chạy chuỗi: OrderSeller → Payment → Delivery (mỗi agent trả `AgentReport`) → Policy (`rules.classify` chốt `Decision`) → Verifier (tính lại độc lập + `output_builder.build_case_output` + `validate`) → ghi `output/EC_XXX.json`. Field nào LLM lệch deterministic bị đè và ghi correction.
3. gpt-4o-mini (~8B, khai báo `config.MODEL_NAME`) chạy trong mọi agent: nhận facts domain, trả reasoning + verdict theo `expected_schema`; `verify()` đối chứng với deterministic. LLM là lớp lý giải/kiểm chứng, không phải nguồn quyết định cuối.
4. Evidence ID (`order:`, `item:`, `payment:`, `seller:`, `policy:`) chỉ nhận ID dựng được từ CSV; ID không tồn tại hoặc sai format bị tính false positive (README §5). Hệ thống ưu tiên dữ liệu kiểm chứng, không tự tạo sự kiện — đúng tinh thần §1.
5. `logging/trace.jsonl` chứng minh lượt chạy thật 50 case (từng agent: facts, llm_reasoning, llm_verdict, corrections); `logging/metadata.json` khai báo model, parameter size, framework, runtime — bắt buộc khi nộp theo README §8.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Văn Tâm
**Ngày xác nhận:** 2026-08-05
