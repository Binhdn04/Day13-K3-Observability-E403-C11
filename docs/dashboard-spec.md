# Dashboard spec — CP2

## Mục tiêu và nguồn dữ liệu

Dashboard CP2 dùng trực tiếp snapshot JSON từ endpoint `GET /metrics` của API tại `http://127.0.0.1:8000/metrics`.

- Công cụ: dashboard local viết bằng FastAPI trong `app/dashboard.py`.
- Refresh mặc định: 30 giây.
- Khoảng quan sát mặc định: từ lúc API process khởi động đến hiện tại.
- Lý do: metrics hiện được giữ trong bộ nhớ và reset khi API restart; chúng không phải time series 60 phút.
- Dashboard runtime: `http://127.0.0.1:8501`.

## Đặc tả sáu nhóm chỉ số

| # | Panel | Field từ `/metrics` | Cách hiển thị | Đơn vị | Threshold/SLO line |
|---|---|---|---|---|---|
| 1 | Latency percentiles | `latency_p50`, `latency_p95`, `latency_p99` | Ba single values P50/P95/P99 | ms | P95 ≤ 3000 ms |
| 2 | Request traffic | `traffic` | Counter tổng request từ lúc API start | requests | Traffic ≥ 1 request |
| 3 | Error rate and breakdown | `error_rate_pct`, `error_breakdown` | Tỷ lệ lỗi và bảng count theo loại exception | percent | Error rate ≤ 2% |
| 4 | Current cost | `total_cost_usd`, `avg_cost_usd` | Tổng chi phí và chi phí trung bình/request thành công | USD | Total cost ≤ 2.5 USD |
| 5 | Input and output tokens | `tokens_in_total`, `tokens_out_total` | Hai counter input/output riêng | tokens | Mỗi field ≤ 50000 tokens |
| 6 | Quality proxy | `quality_avg` | Single value trung bình | score 0–1 | Mean ≥ 0.75 |

## Công thức Error rate

Trong `app/metrics.py`:

```text
request_total = successful_requests + failed_requests
error_rate_pct = failed_requests / request_total × 100
```

Khi chưa có request, `error_rate_pct = 0`. `error_breakdown` đếm lỗi theo tên exception.

## Cách chạy

Chạy các lệnh sau từ thư mục gốc repository, sau khi đã kích hoạt virtual environment hoặc Conda environment và cài đặt `requirements.txt`.

Terminal 1 — API:

```powershell
python -m uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8000
```

Terminal 2 — tạo 10 request:

```powershell
python scripts\load_test.py --concurrency 5
```

Terminal 3 — dashboard:

```powershell
python -m uvicorn app.dashboard:app --host 127.0.0.1 --port 8501
```

Kiểm tra snapshot nguồn:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/metrics | ConvertTo-Json -Depth 5
```

Hoặc trên macOS/Linux:

```bash
curl -s http://127.0.0.1:8000/metrics | python -m json.tool
```

## Evidence CP2 của dashboard

Ảnh dashboard cần nhìn thấy:

- Đủ tên sáu panel.
- Nguồn `/metrics`.
- Khoảng quan sát `Since API startup`.
- Refresh 30 giây.
- Đơn vị và threshold của từng panel.
- Baseline có `traffic > 0`, `error_rate_pct = 0`.
- Practice `tool_fail` có error rate tăng và breakdown `RuntimeError`.

Lưu ảnh trong `submission/evidence/` và dẫn đường dẫn tương đối trong `submission/REPORT.md`.
