# Member Role Report — Day 9: Multi Agent A2A

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                                                                                     |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Họ và tên       | Nguyễn Tiến Đạt                                                                                                              |
| MSSV            | 01039                                                                                                                        |
| Khóa/Lớp        | K3                                                                                                                           |
| Vai trò chính   | Phát triển Data Layer, Rule Oracle (Policy Engine), Multi-Agent Pipeline (6 agent + message bus + trace) và Kiểm thử tự động |
| Ngày hoàn thành | 2026-08-05                                                                                                                   |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable                                                 | File/hàm phụ trách                                  | Input nhận vào                                             | Output bàn giao                                                                                                            | Trạng thái |
| ------------------------------------------------------------------ | --------------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ---------- |
| Data layer (nạp CSV, index, tool máy móc)                          | `src/data/store.py`, `src/data/tools.py`            | 4 CSV Olist (orders, order_items, order_payments, sellers) | Tool`get_order`, `get_items`, `get_seller`, `get_order_timestamps`, `get_payments`, `get_item_totals`, `reconcile_payment` | Hoàn thành |
| Rule oracle EC_POLICY_V1 (đường dẫn quyết định độc lập, không LLM) | `src/policy/ladder.py`                              | `DataStore` + `order_id`                                   | `OracleVerdict` áp đúng 6 luật theo thứ tự ưu tiên, kèm evidence/entity/tiền đã tính sẵn                                   | Hoàn thành |
| Schema validator output                                            | `src/policy/schema.py`                              | JSON output ứng viên                                       | Danh sách lỗi (rỗng = hợp lệ), enum/regex/giới hạn theo README §6                                                          | Hoàn thành |
| 6 agent + message bus + trace                                      | `src/agents/*.py`, `src/bus.py`, `src/llm.py`       | `input/EC_*.json`, evidence bundle giữa các agent          | Handoff thật giữa Coordinator → 3 investigator → Policy → Verifier, ghi`logging/trace.jsonl`                               | Hoàn thành |
| CLI chạy pipeline + đóng gói nộp bài                               | `src/run.py`, `scripts/make_submission.py`          | 50 case input                                              | `output/EC_001..050.json`, `output.zip`                                                                                    | Hoàn thành |
| Test tự động (không cần API key)                                   | `tests/test_data.py`, `tests/test_ladder_golden.py` | —                                                          | 23 test pass, xác nhận oracle khớp 8/8/8/9/8/9 trên cả 50 case thật trước khi viết agent                                   | Hoàn thành |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện. Liên hệ rõ phần việc của bạn với đầu vào, đầu ra và các thành viên phụ thuộc vào phần đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                 | Thành viên/module được hỗ trợ | Kết quả                 |
| ------------------------- | ----------------------------- | ----------------------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module]             | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                                                                | File/hàm/artifact liên quan                 | Kết quả bàn giao                                                                                                                    | Cách xác minh                                            |
| ------------------------------------------------------------------------------------ | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| Khảo sát 50 case thật trước khi code, xác định phân bố 6 nhánh luật                  | `docs/superpowers/specs/2026-08-05-*.md` §1 | Phân bố`8/8/8/9/8/9` dùng làm golden snapshot                                                                                       | `pytest tests/test_ladder_golden.py -q`                  |
| Cài rule oracle độc lập, xác nhận đúng cả bẫy ưu tiên EC_008 (canceled + seller trễ) | `src/policy/ladder.py`                      | `OracleVerdict.primary_issue == "canceled_order_paid"` cho EC_008                                                                   | `test_ec008_priority_trap_canceled_beats_late_seller`    |
| Chạy full pipeline 50 case với LLM thật (gpt-4o-mini)                                | `src/run.py`, `logging/trace.jsonl`         | 200 LLM call, 137,205 token, 0 disagreement, 54 sự kiện verifier_repair (44 bổ sung evidence thiếu, 10 loại ID ngoài bộ tham chiếu) | `python -m src.run` (53.8s), xem `logging/metadata.json` |
| Đóng gói bài nộp                                                                     | `scripts/make_submission.py`                | `output.zip` chứa đúng 50 file `EC_001.json..EC_050.json`, không kèm code/.env                                                      | `python scripts/make_submission.py`                      |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

`logging/trace.jsonl` dòng case `EC_008`: Order & Seller Agent (LLM) đúng khi báo `seller_handoff_late: true`, nhưng Policy Agent (cùng LLM, prompt khác) vẫn chọn đúng `canceled_order_paid` thay vì `late_delivery_seller` vì áp đúng thứ tự ưu tiên EC_POLICY_V1 — chứng minh hệ thống không chỉ lặp lại claim của investigator mà thực sự áp luật.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Xây rule engine + 6 agent để 50 khiếu nại "giao trễ" được phân loại đúng 1 trong 6 `primary_issue`, đúng bên chịu trách nhiệm, đúng số tiền hoàn — trong khi model được phép dùng (`gpt-4o-mini`, giữ nguyên theo yêu cầu dù không chứng minh được ≤10B tham số) có thể tính sai số học hoặc áp sai thứ tự ưu tiên nếu để nó tự do quyết định toàn bộ.

### Cách triển khai

Nguyên tắc xuyên suốt: **mọi phép tính máy móc (cộng tiền, làm tròn, so sánh timestamp) nằm hoàn toàn trong Python** (`src/data/tools.py`), LLM chỉ đọc fact đã tính sẵn và phán quyết phần cần diễn giải (chọn 1 trong 6 `primary_issue`). Để ép handoff thật thay vì một prompt độc thoại, mỗi agent chỉ được cấp một tập tool hẹp (Order & Seller không thấy ngày giao khách; Delivery không thấy seller/status; Payment không thấy seller_id) — không investigator nào tự đủ dữ liệu kết luận case, Policy Agent thậm chí không có tool CSV nào.

An toàn điểm số nằm ở Verifier: nó chạy lại đúng 6 luật bằng Python thuần (`policy/ladder.py`, độc lập hoàn toàn với LLM) và so với đề xuất của Policy Agent. Khớp → chấp nhận. Không khớp → gửi lại Policy một gợi ý không tiết lộ đáp án ("áp lần lượt luật 1-6"), cho phán lại 1 lần. Vẫn không khớp → dùng thẳng kết quả oracle. Một khi `primary_issue` đã được chốt, mọi field còn lại (cause_code, action, party, entity, tiền) đều là hàm xác định của nó — không suy ra lại từ JSON LLM nữa, trừ `evidence_ids` (membership đối chiếu với bộ evidence tham chiếu của oracle, Policy Agent giữ quyền quyết định thứ tự).

### Input, output và contract

| Thành phần              | Mô tả                                                                                                                                                                                         |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input                   | `input/EC_001..050.json` (case_id, claimed_order_id, customer message) + 4 CSV Olist                                                                                                          |
| Output                  | `output/EC_001..050.json` đúng schema README §6, đã qua `policy/schema.py::validate_output`                                                                                                   |
| Module phụ thuộc        | `src/data/store.py` (CSV → index), `.env` (`OPENAI_API_KEY`, đọc qua `src/llm.py`)                                                                                                            |
| Module sử dụng output   | `scripts/make_submission.py` (đóng gói zip); `logging/trace.jsonl`/`metadata.json` dùng để audit                                                                                              |
| Điều kiện lỗi cần xử lý | LLM trả JSON hỏng (retry 2 lần rồi fallback oracle), API lỗi/timeout (backoff), agent ném exception (Coordinator bắt, case đó rơi về oracle, run tiếp), order không tồn tại/không có item row |

### Cách xác minh

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe -m src.run --dry-run
.venv/Scripts/python.exe -m src.run --cases EC_001,EC_005,EC_008
.venv/Scripts/python.exe -m src.run
.venv/Scripts/python.exe scripts/make_submission.py
```

- **Kết quả mong đợi:** 23 test pass; dry-run và full run đều cho phân bố `primary_issue` khớp `late_delivery_seller:8, unsupported_late_claim:9, canceled_order_paid:8, valid_split_payment:9, unavailable_order_paid:8, late_delivery_logistics:8`; zip chứa đúng 50 file.
- **Kết quả thực tế:** Khớp đúng như trên ở cả dry-run (oracle) và full run (LLM thật, 53.8s, 0 disagreement, 54 verifier_repair đều thuộc nhóm sửa evidence, 0 exception).
- **Artifact/log:** `logging/trace.jsonl` (1588 dòng), `logging/metadata.json`, `output/EC_*.json`, `output.zip`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Với model nhỏ (`gpt-4o-mini`, không kiểm chứng được ≤10B tham số) và luật nghiệp vụ deterministic 100% trên dữ liệu, cần quyết định LLM được quyền quyết định tới đâu trong pipeline.
- **Các phương án đã cân nhắc:** (1) LLM làm tất, kể cả tự cộng/so sánh số liệu từ CSV thô; (2) Python quyết định 100%, LLM chỉ viết narrative; (3) Tool Python tính toán, LLM đọc fact đã tính sẵn để phán quyết phần diễn giải (chọn `primary_issue`, `refund_basis`, evidence).
- **Phương án đã chọn:** (3).
- **Lý do:** Phương án (1) rủi ro cao nhất — model nhỏ dễ cộng sai float hoặc so sai timestamp, ảnh hưởng trực tiếp 20% điểm financial_resolution. Phương án (2) an toàn tuyệt đối nhưng vi phạm tinh thần đề bài ("không có điểm cho việc chỉ đặt tên nhiều agent nhưng toàn bộ xử lý nằm trong một prompt duy nhất" — ở đây là "toàn bộ xử lý nằm trong Python thuần"). Phương án (3) tách đúng ranh giới: LLM chỉ làm việc cần diễn giải (không có công thức máy móc để thay thế), mọi thứ có công thức rõ ràng đều do Python đảm nhiệm.
- **Bằng chứng quyết định phù hợp:** Lượt chạy 50 case thật cho 0 `oracle_fallback`, 0 `disagreement` không giải quyết được — Policy Agent khớp oracle 50/50 ngay lần đầu (`logging/metadata.json: policy_agreements_first_try: 50`). Đồng thời 13 case vẫn có `verifier_repair` vì LLM bịa evidence ID sai định dạng (`delivery:<order_id>`) — xác nhận nếu để LLM tự do hoàn toàn (không có Verifier chặn) thì output đã có ID không tồn tại trong CSV, tính là false positive theo README §5.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `UnicodeEncodeError: 'charmap' codec can't encode character 'ạ' in position 1: character maps to <undefined>` khi chạy `python -m src.run --dry-run` lần đầu.
- **Lệnh hoặc bước tái hiện:** `.venv/Scripts/python.exe -m src.run --dry-run` trên PowerShell/Git Bash Windows, ngay ở dòng `print(f"Nạp {len(cases)} case...")`.
- **Nguyên nhân gốc:** Console Windows mặc định dùng codepage `cp1252`, không encode được ký tự tiếng Việt có dấu (`ạ`, `ậ`...) mà script in ra qua `print()`.
- **Cách xử lý:** Thêm đoạn ép `sys.stdout`/`sys.stderr` sang UTF-8 khi encoding hiện tại không phải UTF-8, ở đầu `src/run.py` và `scripts/make_submission.py` (`sys.stdout.reconfigure(encoding="utf-8")`).
- **Cách xác minh sau khi sửa:** Chạy lại `python -m src.run --dry-run` — in đúng tiếng Việt có dấu, không còn traceback; xác nhận thêm ở `python scripts/make_submission.py`.
- **Điều học được:** Không giả định môi trường chạy dùng UTF-8 mặc định — trên Windows, `print()` tiếng Việt cần ép encoding tường minh thay vì chỉ test trên môi trường có sẵn UTF-8 (WSL/Linux CI).

## 7. Hiểu biết về luồng end-to-end

> ⚠️ 5 câu hỏi gốc trong mục này (Crossref, vector index, retrieval/answer quality, freshness monitoring, baseline/corrupted/repaired) thuộc về một bài lab RAG/embedding khác, không khớp với bài Multi-Agent Dispute Resolution (Olist) đang làm. Có thể template bị copy nhầm giữa hai lab. Phần trả lời dưới đây mô tả luồng end-to-end thật của bài này; nên đối chiếu lại với giảng viên/nhóm xem mục 7 cần thay bằng bộ câu hỏi đúng hay giữ nguyên.

**Luồng end-to-end thực tế của bài Multi-Agent Dispute Resolution:**

1. `src/run.py` đọc `input/EC_001..050.json`, với mỗi case lấy `claimed_order_id` giao cho `CoordinatorAgent`.
2. Coordinator fan-out 3 investigator (Order & Seller, Delivery, Payment) chạy song song, mỗi agent chỉ gọi tool hẹp trong `src/data/tools.py` (đọc từ `DataStore` đã nạp 4 CSV Olist), rồi gọi LLM để khẳng định finding của mình.
3. Ba finding được gộp thành `EvidenceBundle` (không có tool CSV) chuyển cho Policy Agent — agent này áp `EC_POLICY_V1` (đã nhúng vào system prompt) để chọn `primary_issue` + `refund_basis` + evidence.
4. Verifier Agent chạy `policy/ladder.py` (đường dẫn Python độc lập, không LLM) để tính đáp án tham chiếu, so với đề xuất của Policy. Khớp thì nhận; không khớp thì cho Policy phán lại 1 lần với gợi ý (không lộ đáp án); vẫn không khớp thì dùng thẳng oracle.
5. Một khi `primary_issue` chốt xong, mọi field còn lại (tiền, entity, cause, action, party) suy ra xác định từ oracle — Verifier chỉ giữ lại `evidence_ids` của Policy sau khi lọc ID sai định dạng/không tồn tại trong CSV.
6. Kết quả ghi vào `output/EC_xxx.json`; toàn bộ sự kiện (tool call, LLM call, handoff, disagreement, repair) ghi vào `logging/trace.jsonl` qua `src/bus.py::TraceWriter`.
7. Trước khi động vào bất kỳ agent nào, oracle ở bước 4 đã được test riêng (`tests/test_ladder_golden.py`) trên cả 50 case thật để xác nhận phân bố đúng và bẫy ưu tiên (EC_008) được xử lý đúng — đây là "ground truth" duy nhất dùng để đo hệ thống có đúng không, tương tự vai trò của một test set cố định trong các bài lab khác.

**Câu trả lời:**

[Xem 7 điểm ở trên; nếu mục này cần thay bằng bộ câu hỏi RAG/Crossref đúng của lab, vui lòng cập nhật lại theo đề bài thật.]

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Tiến Đạt
**Ngày xác nhận:** 2026-08-05
