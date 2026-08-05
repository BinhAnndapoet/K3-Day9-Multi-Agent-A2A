# Member Role Report — Day 9: Multi Agent A2A

<<<<<<< Updated upstream:individual_5SoCuoiMHV_HoVaTen.md
> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung     |
| --------------- | ------------ |
| Họ và tên       | [Họ và tên]  |
| MSSV            | [MSSV]       |
| Khóa/Lớp        | [K3]         |
| Vai trò chính   | [Vai trò]    |
| Ngày hoàn thành | [YYYY-MM-DD] |
=======
## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                   |
| --------------- | ---------------------------------------------------------- |
| Họ và tên       | Nguyễn Trần Hội Thắng                                      |
| MSSV            | 01163                                                      |
| Khóa/Lớp        | K3 / E402                                                  |
| Vai trò chính   | Thiết kế kiến trúc & triển khai pipeline multi-agent (A2A) |
| Ngày hoàn thành | 2026-08-05                                                 |
>>>>>>> Stashed changes:01163_NguyenTranHoiThang.md

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

<<<<<<< Updated upstream:individual_5SoCuoiMHV_HoVaTen.md
| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao   | Trạng thái                            |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| [Phần việc]        | [File/hàm]         | [Input]        | [Output/artifact] | [Hoàn thành/Một phần/Chưa hoàn thành] |
| [Phần việc]        | [File/hàm]         | [Input]        | [Output/artifact] | [Hoàn thành/Một phần/Chưa hoàn thành] |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện. Liên hệ rõ phần việc của bạn với đầu vào, đầu ra và các thành viên phụ thuộc vào phần đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                 | Thành viên/module được hỗ trợ | Kết quả                 |
| ------------------------- | ----------------------------- | ----------------------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module]             | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao          | Cách xác minh   |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| [Mô tả cụ thể]        | [Đường dẫn file]            | [Artifact/metrics/report] | [Lệnh/artifact] |
| [Mô tả cụ thể]        | [Đường dẫn file]            | [Artifact/metrics/report] | [Lệnh/artifact] |
=======
| Module/deliverable     | File/hàm phụ trách                                          | Input nhận vào                  | Output bàn giao                                       | Trạng thái |
| ---------------------- | ----------------------------------------------------------- | ------------------------------- | ----------------------------------------------------- | ---------- |
| Lõi deterministic      | `src/data_store.py`, `src/facts.py`, `src/policy_engine.py` | 4 CSV Olist +`claimed_order_id` | `Facts`, `Decision` (kết quả EC_POLICY_V1)            | Hoàn thành |
| Evidence & schema      | `src/evidence.py`, `src/schema.py`, `src/core.py`           | `Facts`, `Decision`             | `CaseOutput` hợp lệ (đã ép cap/format)                | Hoàn thành |
| Multi-agent A2A layer  | `src/tools.py`, `src/agent_defs.py`, `src/tracing.py`       | case (`case_id`,`order_id`)     | 6 agent + handoff chain +`trace.jsonl`                | Hoàn thành |
| Orchestration & runner | `src/pipeline.py`, `src/run.py`                             | 50 file`input/EC_*.json`        | 50`output/EC_*.json`, `metadata.json`                 | Hoàn thành |
| Score-tuning harness   | `scripts/experiment.py`                                     | 50 input + convention           | Sinh biến thể output/zip để A/B test trên leaderboard | Hoàn thành |
| Test & tài liệu        | `tests/test_policy.py`, `architecture.md`, `pyproject.toml` | —                               | 103 test pass, sơ đồ kiến trúc, môi trường`uv`        | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                                                    |
| --------------------------------- | ----------------------------- | ---------------------------------------------------------- |
| Thiết lập môi trường`uv` + deps   | Toàn nhóm                     | `pyproject.toml`, `uv sync` chạy được (openai-agents 0.19) |
| Xử lý rate-limit khi chạy 50 case | Pipeline                      | Thêm retry + backoff → 50/50 agent-run thành công          |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                    | File/artifact liên quan          | Kết quả bàn giao                             | Cách xác minh                                    |
| ---------------------------------------- | -------------------------------- | -------------------------------------------- | ------------------------------------------------ |
| Engine 6 rule EC_POLICY_V1 theo priority | `src/policy_engine.py`           | Phân loại đúng 50 case: 9/9/8/8/8/8          | `uv run pytest -q` (103 pass)                    |
| Chuỗi handoff A2A 6 agent + trace        | `src/agent_defs.py`,`tracing.py` | `trace.jsonl` 50 dòng, mỗi dòng đủ 5 handoff | Đọc`logging/trace.jsonl`                         |
| Sinh 50 output đúng schema               | `src/run.py`                     | `output/EC_001..050.json`, 0 lỗi schema/cap  | Script validate qua Pydantic + đối chiếu CSV     |
| Nộp & tinh chỉnh điểm trên leaderboard   | `scripts/experiment.py`          | Điểm competition (E402):**94.4109**          | Bảng xếp hạng trực tiếp N7 Competition, lớp E402 |
>>>>>>> Stashed changes:01163_NguyenTranHoiThang.md

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

[Mô tả artifact, metric, report hoặc kết quả tích hợp.]

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

[Phần của bạn giải quyết vấn đề gì trong pipeline?]

### Cách triển khai

[Mô tả thuật toán, quy tắc dữ liệu, orchestration hoặc quyết định chính. Không chỉ chép lại tên hàm.]

### Input, output và contract

<<<<<<< Updated upstream:individual_5SoCuoiMHV_HoVaTen.md
| Thành phần              | Mô tả                                  |
| ----------------------- | -------------------------------------- |
| Input                   | [Schema, artifact hoặc tham số]        |
| Output                  | [Schema, artifact hoặc giá trị trả về] |
| Module phụ thuộc        | [Module/file liên quan]                |
| Module sử dụng output   | [Module/file liên quan]                |
| Điều kiện lỗi cần xử lý | [Trường hợp thực tế]                   |
=======
| Thành phần              | Mô tả                                                                                  |
| ----------------------- | -------------------------------------------------------------------------------------- |
| Input                   | `input/EC_xxx.json` (`case_id`, `customer_request.claimed_order_id`, `policy_version`) |
| Output                  | `output/EC_xxx.json` theo schema README §6 (`CaseOutput` Pydantic)                     |
| Module phụ thuộc        | `data_store` → `facts` → `policy_engine`/`evidence` → `schema`/`core`                  |
| Module sử dụng output   | `pipeline.py` (agent chain) và `run.py` (ghi file, metadata, trace)                    |
| Điều kiện lỗi cần xử lý | order không có item (item/seller rỗng, total=0.0); rate-limit 429 (retry + fallback)   |
>>>>>>> Stashed changes:01163_NguyenTranHoiThang.md

### Cách xác minh

```bash
[Ghi lệnh thực tế đã chạy]
```

- **Kết quả mong đợi:** [Mô tả.]
- **Kết quả thực tế:** [Mô tả.]
- **Artifact/log:** [Đường dẫn; không chứa secret.]

## 5. Một quyết định kỹ thuật quan trọng

<<<<<<< Updated upstream:individual_5SoCuoiMHV_HoVaTen.md
- **Bối cảnh:** [Vấn đề hoặc lựa chọn cần quyết định.]
- **Các phương án đã cân nhắc:** [Ít nhất hai phương án.]
- **Phương án đã chọn:** [Lựa chọn.]
- **Lý do:** [Trade-off về correctness, data quality, reproducibility, cost hoặc độ phức tạp.]
- **Bằng chứng quyết định phù hợp:** [Metric, artifact hoặc kết quả thử nghiệm.]
=======
- **Bối cảnh:** Để LLM tự suy luận ra số tiền/ID, hay để Python tính rồi LLM chỉ điều phối?
- **Các phương án đã cân nhắc:** (1) LLM tự tính toàn bộ trong prompt; (2) Deterministic core +
  agent gọi tool; (3) Lai — LLM tính, tool kiểm tra.
- **Phương án đã chọn:** (2) Deterministic core, agent orchestration + verification.
- **Lý do:** Chấm exact-match (financial 20%, entities 20%, evidence 15%) rất nhạy với sai số/sai
  ID. Deterministic core cho reproducibility 100% và loại bỏ ảo giác, trong khi vẫn giữ đúng tinh
  thần multi-agent (phân công + handoff + verifier) theo README §7.
- **Bằng chứng quyết định phù hợp:** 103/103 test pass; 50/50 case đúng phân bố kỳ vọng; 0 lỗi khi
  validate lại output với dữ liệu CSV; điểm competition 94.41 (E402).
>>>>>>> Stashed changes:01163_NguyenTranHoiThang.md

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** [Che toàn bộ secret trước khi ghi.]
- **Lệnh hoặc bước tái hiện:** [Lệnh/bước.]
- **Nguyên nhân gốc:** [Root cause, không chỉ mô tả triệu chứng.]
- **Cách xử lý:** [Thay đổi cụ thể.]
- **Cách xác minh sau khi sửa:** [Lệnh và kết quả.]
- **Điều học được:** [Bài học kỹ thuật.]

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** [Module/artifact.]
- **Những gì đã loại trừ:** [Các giả thuyết đã kiểm tra.]
- **Bước tiếp theo:** [Hành động có thể kiểm chứng.]

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

[Viết câu trả lời tại đây.]

## 8. Cam kết của thành viên

<<<<<<< Updated upstream:individual_5SoCuoiMHV_HoVaTen.md
Đánh dấu sau khi tự kiểm tra:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.
=======
- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.
>>>>>>> Stashed changes:01163_NguyenTranHoiThang.md

**Họ và tên:** Nguyễn Trần Hội Thắng
**Ngày xác nhận:** 2026-08-05
