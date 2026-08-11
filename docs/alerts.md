# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: high_latency_p95
- Severity: warning
- SLI/SLO liên quan: `latency_p95_ms` (objective 3000ms, `config/slo.yaml`)
- Điều kiện và thời gian duy trì: `latency_p95_ms > 3000` liên tục trong 5 phút (tránh bắt các đợt tăng đột ngột nhất thời)
- Ảnh hưởng tới người dùng: request bị chậm rõ rệt, có nguy cơ timeout ở client hoặc trải nghiệm chat bị đơ
- Ba bước kiểm tra đầu tiên:
  1. Xem panel `latency` trên dashboard để xác nhận p95/p99 đang vượt ngưỡng và từ thời điểm nào.
  2. Mở trace tương ứng trên Langfuse trong khoảng thời gian đó, khoanh vùng span nào chiếm phần lớn thời gian (retrieval/RAG, LLM call, tool call).
  3. Đối chiếu log `data/logs.jsonl` theo `correlation_id` của các request chậm để xem có pattern chung (cùng feature, cùng loại câu hỏi) không.
  - Ghi chú thực nghiệm: khi bật `python scripts/inject_incident.py --scenario rag_slow`, latency p95 đo được tăng từ baseline ~1165ms lên ~3600ms, vượt ngưỡng alert này.
- Mitigation tạm thời: nếu xác định do bước RAG chậm, có thể tạm tắt/giảm phạm vi retrieval hoặc chuyển sang fallback không dùng RAG cho tới khi fix; disable incident bằng `python scripts/inject_incident.py --scenario rag_slow --disable` nếu đang ở môi trường practice.
- Owner: Thu

## Alert 2

- Tên: elevated_error_rate
- Severity: critical
- SLI/SLO liên quan: `error_rate_pct` (objective 2%, `config/slo.yaml`)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` liên tục trong 5 phút
- Ảnh hưởng tới người dùng: một phần request nhận lỗi 500, không nhận được câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Xem panel `errors` trên dashboard để lấy `error_type` chiếm đa số trong `error_breakdown`.
  2. Mở trace của các request lỗi trên Langfuse, xác định span nào ném exception (tool call, agent step nào).
  3. Tìm log `request_failed` tương ứng trong `data/logs.jsonl`, đối chiếu `error_type` và payload để xác nhận root cause (vd tool ngoài bị fail).
  - Ghi chú thực nghiệm: khi bật `python scripts/inject_incident.py --scenario tool_fail`, toàn bộ request trong batch test trả lỗi 500 `RuntimeError`, error rate batch đó là 100%.
- Mitigation tạm thời: nếu do một tool/dependency ngoài bị lỗi, tạm thời tắt/bypass tool đó hoặc trả fallback response thay vì để request fail hoàn toàn; disable incident bằng `python scripts/inject_incident.py --scenario tool_fail --disable` ở môi trường practice.
- Owner: Thu

## Alert 3

- Tên: cost_budget_exceeded
- Severity: warning
- SLI/SLO liên quan: `daily_cost_usd` (objective 2.5 USD/ngày, `config/slo.yaml`)
- Điều kiện và thời gian duy trì: `daily_cost_usd > 2.5` (không cần cửa sổ duy trì vì đây là tổng tích lũy trong ngày, không phải rate tức thời — vượt ngưỡng là vượt ngân sách ngày đó)
- Ảnh hưởng tới người dùng: không ảnh hưởng trực tiếp UX, nhưng là rủi ro chi phí vận hành nếu không kiểm soát
- Ba bước kiểm tra đầu tiên:
  1. Xem panel `cost` trên dashboard, xác nhận thời điểm chi phí bắt đầu tăng bất thường.
  2. Xem panel `tokens` cùng thời điểm — chi phí tăng do số lượng request tăng hay do mỗi request tốn nhiều token hơn.
  3. Mở trace các request chi phí cao trên Langfuse để xem model/feature nào đang gọi tốn kém bất thường.
  - Ghi chú thực nghiệm: khi bật `python scripts/inject_incident.py --scenario cost_spike`, chi phí trung bình mỗi request tăng từ baseline ~0.0021 USD lên ~0.0078 USD (~3.7 lần).
- Mitigation tạm thời: giới hạn tạm số token đầu ra tối đa hoặc chuyển feature bị ảnh hưởng sang model rẻ hơn trong lúc điều tra; disable incident bằng `python scripts/inject_incident.py --scenario cost_spike --disable` ở môi trường practice.
- Owner: Thu
