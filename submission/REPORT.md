# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: C11
- Repository URL: https://github.com/Binhdn04/Day13-K3-Observability-E403-C11
- Commit SHA cuối: ec04461305a799e0e180a565ac96c32b5aa3e0c5
- Thành viên và vai trò:
  - **Đoàn Nhật Bình** (MSSV: 2A202602018) — Vai trò: API & Middleware. Phụ trách cài đặt Middleware, gán Correlation ID, bổ sung Exception Handler (phần mở rộng).
  - **Phan Bá Khánh Linh** (MSSV: 2A202601989) — Vai trò: QA & Chief Investigator . Phụ trách chạy load test, bọc trace cho sub-component RAG/LLM (phần mở rộng), dẫn dắt điều tra Challenge (CP3) và hoàn thiện báo cáo.
  - **Nguyễn Minh Thu** (MSSV: 2A202601631) — Vai trò: SRE & Alerts Engineer. Phụ trách thiết lập SLO, viết Alerts rules và Alert Runbook xử lý sự cố.
  - **Bùi Duy Hải** (MSSV: 2A202601878) — Vai trò: Security Engineer. Phụ trách cài đặt PII Scrubbing, regex patterns và kiểm chứng log không lộ PII.
  - **Lê Trung Hiếu** (MSSV: 2A202601917) — Vai trò: Metrics & Dashboard. Phụ trách đo đếm `error_rate_pct` và thiết kế spec Dashboard 6 nhóm chỉ số.

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (Đạt điểm tối đa ở CP1)
- Tổng số traces: >15 traces được ghi nhận thành công trên Langfuse
- Số PII leak còn lại: 0 (Đã kiểm chứng che giấu hoàn toàn CCCD, thẻ tín dụng, email, điện thoại, hộ chiếu, địa chỉ Việt Nam)
- Link/đường dẫn dashboard: `submission/evidence/dashboard.png` (dashboard runtime trên Langfuse); đặc tả đầy đủ 6 nhóm chỉ số nằm tại `docs/dashboard-spec.md`, và dashboard FastAPI tham chiếu trực tiếp endpoint `/metrics` được triển khai trong `app/dashboard.py`.

## 3. Logging và tracing

- Evidence correlation ID: Correlation ID được truyền dạng `req-<8-char-hex>` (ví dụ: `req-e724658b`) xuất hiện đồng nhất trong logs và headers phản hồi `x-request-id`.
- Evidence PII redaction: Chuỗi nhạy cảm trong log tự động thay thế bằng nhãn dạng `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]`,... thông qua structlog processor.
- Evidence trace waterfall: `submission/evidence/trace_waterfall.jpg` chụp vết trace chi tiết.
- Giải thích một span đáng chú ý: Span `rag_retrieve` trong trace của challenge `rag_slow` có độ trễ lớn (~2500ms) vì do kịch bản incident giả lập hàm `time.sleep(2.5)` đồng bộ gây nghẽn luồng.

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: Version 1 (labels: `baseline`, `production`)
- Version/label candidate: Version 2 (label: `candidate`)
- Trace ID của mỗi version: Trace ID của v1 dùng label `baseline`/`production` và v2 dùng label `candidate` được thể hiện cụ thể trên giao diện Langfuse.
- Bằng chứng đổi label hoặc rollback: `submission/evidence/prompts_version.png` chụp các phiên bản prompt và `submission/evidence/rollback.png` ghi nhận thao tác rollback trên Langfuse.

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: HỢP LỆ 6/6 panel.
- Evidence dashboard: `submission/evidence/dashboard.png` chụp dashboard runtime trên Langfuse. Thiết kế đầy đủ 6 nhóm Latency, Traffic, Error, Cost, Tokens và Quality, cùng field nguồn, đơn vị và threshold, được mô tả trong `docs/dashboard-spec.md`. Endpoint `/metrics` và dashboard FastAPI trong `app/dashboard.py` là phần triển khai kỹ thuật dùng để kiểm chứng spec.
- SLO đã chọn và lý do (`config/slo.yaml`):
  - `latency_p95_ms` objective 3000ms: baseline đo bằng `python scripts/load_test.py` cho p95 ~1075-1165ms, p99 ~1246ms; khi bật incident `rag_slow` p95 tăng lên ~3600ms, vượt ngưỡng. Giữ 3000ms để có khoảng đệm với baseline nhưng vẫn bắt đúng sự cố.
  - `error_rate_pct` objective 2%: khớp với threshold panel `errors` trong `config/dashboard.yaml` để không lệch số giữa các artifact.
  - `daily_cost_usd` objective 2.5 USD/ngày: baseline ~0.0021 USD/request (~1190 request/ngày mới chạm ngưỡng); khi bật `cost_spike` chi phí/request tăng lên ~0.0078 USD (~3.7 lần).
  - `quality_score_avg` objective 0.75: quality proxy đo được ổn định ~0.88 qua cả baseline lẫn 3 kịch bản sự cố (fake LLM không đổi theo incident).
- Alert rules và runbook (`config/alert_rules.yaml`, `docs/alerts.md`):
  - `high_latency_p95` (warning) — `latency_p95_ms > 3000` trong 5 phút, ứng với incident practice `rag_slow`.
  - `elevated_error_rate` (critical) — `error_rate_pct > 2` trong 5 phút, ứng với incident practice `tool_fail` (khi bật, error rate batch test lên 100%, lỗi `RuntimeError`).
  - `cost_budget_exceeded` (warning) — `daily_cost_usd > 2.5`, ứng với incident practice `cost_spike`.
  - Mỗi alert trong `docs/alerts.md` có 3 bước kiểm tra đầu tiên theo luồng Metrics → Traces → Logs và mitigation tạm thời, dựa trên kết quả chạy thử `python scripts/inject_incident.py --scenario <name>` thật.

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1`
- Triệu chứng từ metrics: Khi bắt đầu chạy tải challenge (`load_test.py --challenge --concurrency 5`), độ trễ P95 của API `refund` tăng vọt từ mức baseline (~150ms) lên tới hơn **13.2 giây** ở phía client và ghi nhận **~2.65 giây** ở phía server.
- Trace ID liên quan: `84f1d385f9709834dfffd1e2f2839cc6`
- Log line/correlation ID liên quan: `req-dba5223d`
- Root cause: Sự cố `rag_slow` kích hoạt việc chạy hàm `time.sleep(2.5)` đồng bộ bên trong phương thức `retrieve` tại file [mock_rag.py](file:///d:/MyLab/Day13-K3-Observability-E403-C11/app/mock_rag.py). Vì Uvicorn/FastAPI chạy đơn luồng cho các hàm đồng bộ thông thường nếu không được chạy trong ThreadPool, lệnh sleep đồng bộ này đã chặn đứng (block) toàn bộ Event Loop chính. Khi gửi đồng thời 5 request (`--concurrency 5`), các request bị nghẽn cổ chai xếp hàng nối đuôi nhau, dẫn đến độ trễ lũy kế ở phía client tăng dần (5 x 2.65s ≈ 13.2s).
- Fix action: Chuyển hàm `retrieve` thành hàm bất đồng bộ (`async def retrieve(...)`) và sử dụng lệnh ngủ bất đồng bộ `await asyncio.sleep(2.5)` để nhường luồng cho các request khác xử lý song song. Hoặc sử dụng `run_in_executor` để chạy hàm đồng bộ này trên một thread pool riêng biệt.
- Preventive measure: Thiết lập quy chuẩn kiểm duyệt mã nguồn (code review guidelines) nghiêm ngặt để cấm sử dụng các lệnh block đồng bộ (`time.sleep()`, synchronous database drivers, synchronous HTTP clients) trên luồng chính của FastAPI. Ưu tiên sử dụng các thư viện async hoàn toàn.

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| **Đoàn Nhật Bình**<br>(MSSV: 2A202602018) | **API & Middleware**: Viết `CorrelationIdMiddleware`, xử lý correlation ID cho request/response và ghi log contextvars; cài đặt Exception Handler mở rộng. | `fa06fc3` | Cách quản lý contextvars trong ứng dụng async FastAPI; cách bắt lỗi toàn cục và trả về thông tin lỗi chuẩn hóa không lộ PII kèm x-request-id. |
| **Bùi Duy Hải**<br>(MSSV: 2A202601878) | **Security Engineer**: Cài đặt PII Scrubbing, tối ưu regex patterns cho Passport/Địa chỉ VN, tích hợp processor làm sạch log trước khi ghi file. | `3eef846` | Thiết kế regex hiệu quả cho các loại PII đặc thù của Việt Nam; cơ chế hoạt động của logging processor trong structlog. |
| **Lê Trung Hiếu**<br>(MSSV: 2A202601917) | **Metrics & Dashboard**: Chuẩn hóa `traffic` và `error_rate_pct` theo tổng request; xây dashboard FastAPI đọc trực tiếp `/metrics` với 6 nhóm chỉ số, đơn vị và threshold; hoàn thiện `docs/dashboard-spec.md`; bổ sung unit test cho metrics và dashboard. | `a9d000c` | Cách tính error rate trên tổng request; ý nghĩa của P50/P95/P99; cách ánh xạ snapshot `/metrics` thành dashboard và phân biệt metrics tích lũy từ lúc API khởi động với dữ liệu time series. |
| **Nguyễn Minh Thu**<br>(MSSV: 2A202601631) | **SRE & Alerts Engineer**: Thiết lập SLO (`config/slo.yaml`), viết alert rules (`config/alert_rules.yaml`) và runbook xử lý sự cố (`docs/alerts.md`) dựa trên baseline và incident practice. | `4ad611f` | Cách đặt ngưỡng SLO dựa trên dữ liệu thực tế đo đạc; symptom-based alert bám sát SLO thay vì tên implementation; thiết kế runbook cho SRE. |
| **Phan Bá Khánh Linh**<br>(MSSV: 2A202601989) | **QA & Chief Investigator (Bạn)**: Thiết lập môi trường, bọc tracing cho RAG/LLM thành các span con, chạy tải load test challenge và phân tích root cause sự cố nghẽn luồng Event Loop. | `44398f4` | Hiểu rõ cơ chế nghẽn luồng (Event Loop blocking) của FastAPI khi gọi các hàm đồng bộ nặng; cách sử dụng decorator `@observe` để phân tích độ trễ của từng bước (RAG vs LLM) trên biểu đồ waterfall trace. |
