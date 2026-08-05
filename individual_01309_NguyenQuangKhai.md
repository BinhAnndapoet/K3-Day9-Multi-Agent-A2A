# Báo cáo cá nhân — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Nguyen Quang Khai |
| MSSV | 2A202601309 |
| Khóa/Lớp | K3 |
| Vai trò chính | Architecture / Multi-Agent Pipeline |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

| Module/deliverable | File phụ trách | Input | Output | Trạng thái |
|---|---|---|---|---|
| Domain contracts và deterministic facts | `domain/models.py`, `data/catalog.py`, `data/fact_builder.py` | Case JSON, Olist CSV | Typed `CaseFacts` và evidence registry | Hoàn thành |
| Policy và validation | `policy/engine.py`, `validation/verifier.py` | Facts và agent findings | Locked decision, schema-valid output | Hoàn thành |
| Agent và orchestration | `agents/`, `graph/` | Least-privilege views | LangGraph fan-out/fan-in, resolution và repair | Hoàn thành |
| Batch và audit artifacts | `runner.py`, `observability/` | 50 case | 50 output, trace, metadata | Hoàn thành |
| Tài liệu kiến trúc | `architecture.md` | Implemented graph | Sơ đồ, role, access và handoff | Hoàn thành |

Phần hỗ trợ tích hợp gồm chẩn đoán `.env`, khóa structured schema riêng cho từng agent role, cô lập checkpoint state giữa các batch và recovery năm case thiếu policy evidence.

## 3. Kết quả bàn giao

| Nhiệm vụ | Artifact | Kết quả | Cách xác minh |
|---|---|---|---|
| Xử lý toàn bộ input | `output/EC_001.json` đến `EC_050.json` | 50/50 hợp lệ | `py -3.11 -m olist_dispute.runner validate` |
| Multi-agent audit | `trace.jsonl` | 590 event, đủ 50 case | Parse từng JSONL row và đếm case/node |
| Model/runtime declaration | `metadata.json` | OpenAI, gpt-4o-mini, LangGraph 1.2.10, Python 3.11.9 | Đọc JSON metadata |
| Policy coverage | 50 output | 8/8/8/8/9/9 case trên sáu branch | Thống kê `assessment.primary_issue` |

Kết quả validator thực tế:

```text
valid: 50
errors: []
success: true
```

## 4. Giải thích kỹ thuật

### Vấn đề cần giải quyết

Pipeline phải phân tích khiếu nại bằng nhiều agent nhưng không được cho model tự quyết định join, tiền, policy hoặc evidence. Một order có thể có nhiều item/payment row; policy còn phụ thuộc thứ tự ưu tiên và so sánh timestamp nghiêm ngặt.

### Cách triển khai

Catalog load bốn CSV một lần bằng `csv.DictReader` và tạo index read-only. Fact builder join theo `claimed_order_id`, dùng `Decimal` với `ROUND_HALF_UP`, tính tổng item/freight/payment, payment tolerance 0.10 BRL, giao trễ và seller handoff trễ. Mỗi row sinh evidence ID allow-listed.

LangGraph fan-out ba typed view cho Order/Seller, Payment và Delivery. Mỗi role có structured response schema riêng để model không thể trả nhầm `agent_name`. Fan-in kiểm tra đủ đúng ba handoff. Policy engine áp sáu early-return guard đúng thứ tự README, tạo `PolicyDecision` khóa. Resolution agent viết rationale và đề xuất evidence; output builder phát hành bộ evidence canonical từ registry rồi dựng lại business fields từ facts. Writer dùng temporary file và `os.replace`.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | `CaseRequest` theo `EC_POLICY_V1`, bốn Olist CSV |
| Output | `CaseOutput` đúng schema README |
| Module phụ thuộc | Catalog, fact builder, agent gateway, policy, verifier |
| Module sử dụng output | Atomic writer và submission validator |
| Điều kiện lỗi | Missing order, seller không tồn tại, unsupported policy, invalid evidence, policy/money mutation, provider failure |

### Cách xác minh

```powershell
py -3.11 -m compileall -q src
py -3.11 -m olist_dispute.runner run --case-concurrency 3
py -3.11 -m olist_dispute.runner validate
```

- Kết quả mong đợi: đúng 50 output, zero validation errors.
- Kết quả thực tế: 50 output hợp lệ, đủ sáu policy branch.
- Artifact: `output/`, `trace.jsonl`, `metadata.json`.

Theo yêu cầu triển khai, không tạo automated test suite; thay vào đó đã chạy compile/import smoke, một graph smoke với gateway giả, một graph smoke bằng OpenAI thật và validator độc lập trên toàn bộ 50 output.

## 5. Quyết định kỹ thuật quan trọng

- Bối cảnh: LLM linh hoạt trong phân tích nhưng không đáng tin cho tiền, ID và rule priority.
- Phương án cân nhắc: orchestration hoàn toàn bằng prompt; custom Python coordinator; LangGraph hybrid.
- Phương án chọn: LangGraph hybrid với deterministic business core.
- Lý do: graph thể hiện rõ agent/handoff/retry/checkpoint, trong khi policy lock và verifier bảo đảm reproducibility.
- Bằng chứng: validator recompute từ CSV đạt 50/50; output phân bố đúng cả sáu rule.

## 6. Lỗi và blocker đã xử lý

- Triệu chứng: API ban đầu trả connection/401 dù `.env` đã cập nhật.
- Nguyên nhân gốc: process giữ `OPENAI_API_KEY` cũ; `load_dotenv()` mặc định không override environment.
- Cách xử lý: dùng repository-local `.env` làm nguồn có chủ đích với `override=True`, đồng thời chuẩn hóa key một dòng tại config boundary.
- Xác minh: OpenAI model-list preflight thành công, real graph smoke thành công.

Lỗi orchestration tiếp theo là additive `agent_findings` giữ state giữa các batch do root `checkpoint_ns` bị reset thành rỗng. Runtime thread key được đổi sang `<run_id>:<case_id>`, còn trace vẫn ghi `thread_id=case_id`. Năm case thiếu policy evidence được sửa bằng cách để deterministic output builder thêm evidence policy đã khóa, sau đó recovery và validate lại 50/50.

## 7. Hiểu biết về luồng end-to-end

1. Batch runner đọc case, catalog join order/items/payments/sellers và Fact Builder tạo typed facts.
2. Ba domain agent nhận ba lát cắt least-privilege và handoff `AgentFinding` vào merge node.
3. Policy engine deterministic chọn đúng branch ưu tiên, khóa cause/party/refund/status/action.
4. Resolution agent tổng hợp rationale; verifier dựng và recompute output, repair tối đa một lần nếu lỗi evidence/schema có thể sửa.
5. Output hợp lệ được atomic-write, trace ghi node/handoff, metadata ghi model/framework/runtime.
6. Submission validator đọc lại đủ 50 file, dựng facts từ CSV và so sánh toàn bộ decision/output trước khi trả exit code 0.

## 8. Cam kết

- [x] Báo cáo phản ánh đúng phần triển khai và kết quả đã xác minh.
- [x] Có thể giải thích luồng end-to-end và contract giữa các module.
- [x] Không ghi thành công cho bước chưa được kiểm chứng.
- [x] Không chứa API key, token hoặc giá trị secret.
- [x] Nội dung là báo cáo cá nhân cho pipeline Olist hiện tại.

**Họ và tên:** Nguyen Quang Khai  
**Ngày xác nhận:** 2026-08-05
