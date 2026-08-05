# Architecture — Multi-Agent E-commerce Dispute Resolution (K3 Day 09)

Hệ thống giải quyết 50 khiếu nại thương mại điện tử trên dataset Olist. Mỗi case được điều tra
bởi một pipeline 6 agent có **phân công domain riêng**, **handoff bằng chứng** và **kiểm chứng chéo**
giữa các agent trước khi ghi file output.

- **Model (khai báo trong code, không trong `.env`):** `gpt-4o-mini` (OpenAI, qua `OPENAI_API_KEY` trong `.env`).
- **Framework:** Python 3.11 + OpenAI Python SDK (`openai`), không dùng framework agent nặng để giữ
  quyền kiểm soát hoàn toàn với prompt, handoff và verification.
- **Runtime:** local Python process (`python main.py`), tuần tự theo case, song song agent theo luồng
  handoff cố định.

---

## 1. Nguyên tắc thiết kế cốt lõi

1. **Phân công thật, không đặt tên suông.** Mỗi agent có system prompt riêng, domain dữ liệu riêng và
   chỉ trả lời về domain đó. Không có agent nào "biết hết".
2. **Handoff bằng chứng (`evidence_ids`).** Mỗi agent xuất ra một report JSON + danh sách evidence ID
   dựng được từ CSV. Coordinator gộp các report này thành input cho Policy Agent.
3. **Ưu tiên dữ liệu kiểm chứng được.** Agent chỉ được nộp evidence ID có thể dựng trực tiếp từ CSV
   (xem mục Evidence ID của README). Mọi phép so sánh thời gian/tiền được tính lại bằng code từ giá
   trị nguyên bản trong CSV, không tin mù lời khiếu nại và không bịa sự kiện.
4. **Kiểm chứng chéo (defense in depth).** Mỗi agent chạy LLM để **lý giải** rồi **tự đối chiếu** với
   phép tính deterministic cùng domain. Verifier Agent tính lại toàn bộ decision bằng rules engine
   độc lập và đè lên kết quả nếu LLM lệch. Nhờ vậy output luôn đúng nghiệp vụ kể cả khi LLM nhỏ sai
   số học — đây là chìa khoá để đạt điểm tối đa trên 50 case.

> Vì tiêu chí chấm là **sự chính xác của JSON output** trên từng case, các quyết định nghiệp vụ
> (primary issue, refund, action, evidence) được giữ làm **source of truth bằng rules engine**; LLM
> đóng vai trò lý giải, đối chứng và sinh trace minh bạch. Đây không phải "toàn bộ xử lý trong 1
> prompt" — mỗi agent có prompt/domain riêng và có bước verify độc lập.

---

## 2. Sơ đồ agent và luồng handoff

```
                         ┌──────────────────────────┐
   input/EC_*.json ───▶  │   Coordinator Agent      │  ───▶ output/EC_*.json
                         │  (phân case, gộp, ghi)    │
                         └─────────────┬────────────┘
                                       │ handoff (case + order_id)
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                               ▼
 ┌──────────────┐             ┌────────────────┐              ┌────────────────┐
 │ Order&Seller │             │ Payment Agent  │              │ Delivery Agent │
 │    Agent     │             │ (payment rows) │              │ (ngày giao vs  │
 │ (status, item│             │                │              │  estimated,    │
 │  seller, hand│             │                │              │  handoff vs    │
 │  -off date)  │             │                │              │  shipping limit)│
 └──────┬───────┘             └───────┬────────┘              └───────┬────────┘
        │ evidence:                   │ evidence:                    │ evidence:
        │ order/item/seller           │ payment:*                    │ (dùng lại order)
        ▼                             ▼                              ▼
        └────────────────────► ┌──────────────┐ ◄─────────────────────┘
                               │ Policy Agent │  áp dụng EC_POLICY_V1
                               │ (6 quy tắc)  │  → primary_issue, refund, action
                               └──────┬───────┘
                                      │ draft output
                                      ▼
                               ┌────────────────┐
                               │ Verifier Agent │  re-compute deterministic,
                               │                │  validate schema/ID/amount/limit
                               └──────┬─────────┘
                                      │ final output
                       ┌──────────────┴──────────────┐
                       ▼                             ▼
                 output/EC_xx.json            logging/trace.jsonl
```

Handoff là **luồng cố định có trạng thái**: Coordinator đóng gói `CaseContext`, mỗi agent nhận
context + dữ liệu domain, trả `AgentReport`; report của agent trước được ghép vào context của agent
sau (Order → Delivery dùng chung order dates; cả 3 report vào Policy; Policy draft vào Verifier).

---

## 3. Vai trò và quyền truy cập dữ liệu từng agent

| Agent | Domain / câu hỏi trả lời | Đọc CSV nào | Xuất evidence ID | Handoff cho |
|---|---|---|---|---|
| **Coordinator** | Nhận case, truy xuất order, phân việc, gộp report, ghi output + trace | `orders`, `customers` (lookup) | — | tất cả agent |
| **Order & Seller Agent** | `order_status`? có item không? seller nào? `carrier_date` vs `shipping_limit_date` của từng item có muộn không? | `orders`, `order_items`, `sellers` | `order:*`, `item:*`, `seller:*` | Delivery, Policy |
| **Payment Agent** | Có bao nhiêu payment row? tổng payment? khớp item+freight trong sai số 0.10 BRL? | `order_payments` | `payment:*` | Policy |
| **Delivery Agent** | `delivered_customer_date` có sau `estimated_delivery_date` không (giao trễ)? | `orders` (dates) | (dùng order) | Policy |
| **Policy Agent** | Áp 6 quy tắc theo thứ tự ưu tiên → `primary_issue`, `root_cause_code`, responsible party, refund, action, confidence | — (dùng report) | `policy:<root_cause_code>` | Verifier |
| **Verifier Agent** | Tính lại decision bằng `rules.py` độc lập; validate evidence ID, số tiền, schema, giới hạn (5/10/3/3/5); đè kết quả nếu lệch | `orders`, `order_items`, `order_payments` | — | Coordinator (ghi) |

### Nguyên tắc "least privilege"
Một agent **không thấy** domain khác: Payment Agent chỉ nhận các row payment, không thấy shipping
date; Order & Seller Agent không thấy payment value. Coordinator là nơi duy nhất gộp — mô phỏng một
nhân viên CSKH điều phối các bộ phận riêng biệt.

---

## 4. Quy tắc nghiệp vụ & root-cause mapping

Áp dụng **theo thứ tự ưu tiên** (xem README mục 4). Mọi tiền làm tròn 2 chữ số thập phân.

| # | `primary_issue` | Điều kiện (tính bằng code) | Responsible | Refund | Action | Root-cause code |
|---|---|---|---|---:|---|---|
| 1 | `canceled_order_paid` | `order_status=canceled` và tổng payment > 0 | `platform`/`OLIST_PLATFORM` | tổng payment | `issue_full_refund` | `ORDER_CANCELED_AFTER_PAYMENT` |
| 2 | `unavailable_order_paid` | `order_status=unavailable` và tổng payment > 0 | `platform`/`OLIST_PLATFORM` | tổng payment | `issue_full_refund` | `ORDER_UNAVAILABLE_AFTER_PAYMENT` |
| 3 | `late_delivery_seller` | `delivered > estimated` VÀ tồn tại item có `carrier_date > shipping_limit_date` | `seller`/id vi phạm | tổng freight | `refund_freight` | `SELLER_HANDOFF_AFTER_LIMIT` |
| 4 | `late_delivery_logistics` | `delivered > estimated` VÀ không có item muộn handoff | `logistics_provider`/`LOGISTICS_PROVIDER` | tổng freight | `refund_freight` | `CARRIER_DELIVERED_AFTER_ESTIMATE` |
| 5 | `valid_split_payment` | ≥2 payment row VÀ \|tổng payment − (item+freight)\| ≤ 0.10 BRL | không có | 0 | `explain_valid_split_payment` | `MULTIPLE_PAYMENTS_RECONCILED` |
| 6 | `unsupported_late_claim` | `delivered ≤ estimated` VÀ payment khớp | không có | 0 | `reject_late_refund` | `DELIVERY_WITHIN_ESTIMATE` |

So sánh timestamp theo **giá trị chuỗi trong CSV** (định dạng `YYYY-MM-DD HH:MM:SS` zero-padded →
so lexical = so thời gian), đúng như README yêu cầu (không đổi múi giờ).

---

## 5. Evidence ID (chỉ dạng dựng được từ CSV)

```
order:<order_id>
item:<order_id>:<order_item_id>
payment:<order_id>:<payment_sequential>
seller:<seller_id>
policy:<root_cause_code>
```

Verifier kiểm tra mỗi ID khớp regex và tồn tại trong dữ liệu; ID sai dạng hoặc không tồn tại bị
loại (tránh false positive). Ưu tiên nộp: `policy` → `order` → seller liên quan → item → payment,
giới hạn 10 evidence / case.

---

## 6. Output schema & giới hạn cứng (Verifier enforce)

- `case_status` ∈ {`action_required`, `no_action`}.
- `confidence` ∈ [0, 1].
- Giới hạn: ≤5 ID mỗi entity set, ≤10 evidence, ≤3 root causes, ≤3 responsible parties, ≤5 actions.
- Order không có item row → `item_ids`, `seller_ids` rỗng; `item_total_brl`, `freight_total_brl` = 0.0.
- `item_total_brl = Σ price`, `freight_total_brl = Σ freight_value`, `payment_total_brl = Σ payment_value`.

---

## 7. Trace & metadata

- `logging/trace.jsonl`: mỗi dòng = một bước agent cho một case (`case_id`, `agent`, `input`,
  `output`, `tokens`, `verifier_corrections`). **Overwrite** mỗi lần chạy (không append).
- `logging/metadata.json`: model, parameter size, framework, runtime (xem README mục 8).

---

## 8. Cấu trúc thư mục nguồn

```
config.py              # load .env, MODEL_NAME = "gpt-4o-mini"
data_layer.py          # load 9 CSV, index, lookup theo order_id/seller_id
models.py              # dataclass CaseContext, AgentReport, Decision, OutputSchema
rules.py               # rules engine deterministic (source of truth)
llm_client.py          # wrap OpenAI client (gpt-4o-mini, json mode, temp 0)
coordinator.py         # orchestrate 6 agent + handoff
main.py                # entry: đọc input/, chạy 50 case, ghi output/ + trace + metadata
agents/
  base.py
  order_seller_agent.py
  payment_agent.py
  delivery_agent.py
  policy_agent.py
  verifier_agent.py
```
