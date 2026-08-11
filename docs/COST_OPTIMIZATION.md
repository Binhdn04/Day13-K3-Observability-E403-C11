# Tối ưu chi phí và bằng chứng

## Biện pháp giảm thiểu đã triển khai

* `MAX_OUTPUT_TOKENS=120` giới hạn số completion token tốn kém. Chỉ đặt thành `0` khi thực hiện một lần chạy đối chứng có kiểm soát để so sánh trước tối ưu.
* `RESPONSE_CACHE_ENABLED=true` lưu cache cho các tổ hợp prompt/model/giới hạn token giống nhau. Khi cache hit, hệ thống trả về câu trả lời đã lưu mà không phát sinh thêm token mới.
* Ứng dụng ghi sự kiện `config_changed` khi khởi động và các sự kiện bật/tắt incident vào `data/audit.jsonl` (được cấu hình bởi `AUDIT_LOG_PATH`).

## Kết quả đo được

Khi bật `cost_spike` và chạy cùng một bài load test gồm 10 truy vấn:

| Lần chạy | Cấu hình                           | total_cost_usd |
| -------- | ---------------------------------- | -------------: |
| Trước    | `MAX_OUTPUT_TOKENS=0`, cache tắt   |         0.069 |
| Sau      | `MAX_OUTPUT_TOKENS=120`, cache bật |         0.0190 |

Chi phí giảm **75.5%**. Giới hạn output token là yếu tố tạo ra mức giảm xác định trong bài load test sử dụng các truy vấn duy nhất này; caching giúp tiết kiệm thêm chi phí đối với các prompt được lặp lại.

## Tái hiện kết quả và chụp ảnh bằng chứng

Khi API đang chạy, mở `http://127.0.0.1:8001/metrics` trên trình duyệt sau mỗi lần load test và chụp toàn bộ JSON response. Lưu hai ảnh với tên:

* `submission/evidence/cost_before.png`
* `submission/evidence/cost_after.png`

Các lệnh cho server đã tối ưu chạy tại port 8001:

```powershell
python scripts/inject_incident.py --scenario cost_spike --base-url http://127.0.0.1:8001
python scripts/load_test.py --base-url http://127.0.0.1:8001
```

Với port mặc định 8000, bỏ tham số `--base-url`. Chạy `python scripts/inject_incident.py --scenario cost_spike --disable` khi kết thúc phần demo.

## Tự động hóa

```powershell
python scripts/detect_anomalies.py
```

Hệ thống tự động quét `data/logs.jsonl` để phát hiện email, số điện thoại Việt Nam, CCCD và thông tin thẻ tín dụng chưa được che (redact), đồng thời đánh dấu các bản ghi `response_sent` có độ trễ vượt quá latency SLO được định nghĩa trong `config/slo.yaml`. Mọi cảnh báo phát hiện được sẽ được ghi vào `data/anomaly_alerts.jsonl`.
