# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: C11
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`:
baseline: 30/100 
- Tổng số traces:
- Số PII leak còn lại:
- Link/đường dẫn dashboard:

## 3. Logging và tracing

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name:
- Version/label baseline:
- Version/label candidate:
- Trace ID của mỗi version:
- Bằng chứng đổi label hoặc rollback:

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: HỢP LỆ 6/6 panel.
- Evidence dashboard: `submission/evidence/member-c-dashboard-metrics.png` (trạng thái healthy, đủ threshold theo `config/slo.yaml`: latency ≤3000ms, traffic ≥1, error ≤2%, cost ≤2.5 USD, tokens ≤50000, quality ≥0.75) và `submission/evidence/member-c-dashboard-error.png` (panel error rate chuyển sang BREACHED ở 33.33% khi có `RuntimeError`, khớp kịch bản `tool_fail` đã test).
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

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Thu | SRE & Alerts Engineer: thiết lập SLO (`config/slo.yaml`), viết alert rules (`config/alert_rules.yaml`) và runbook xử lý sự cố (`docs/alerts.md`) dựa trên baseline load test và 3 kịch bản practice thật | `4ad611f` | Cách đặt ngưỡng SLO dựa trên dữ liệu đo thật thay vì đoán; symptom-based alert phải bám theo SLO thay vì tên implementation nội bộ; sự khác biệt giữa alert tức thời (latency/error rate) và alert tích lũy (cost) trong việc chọn cửa sổ thời gian duy trì |
| | | | |
