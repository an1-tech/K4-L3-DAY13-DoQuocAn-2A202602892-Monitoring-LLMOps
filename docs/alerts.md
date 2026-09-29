# Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: `HighUserVisibleLatency`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack
- SLI/SLO liên quan: latency P95 không vượt quá 3000 ms.
- Điều kiện và thời gian duy trì: `latency_p95_ms > 3000` liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu để nhận câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Xác định khoảng thời gian bất thường trên panel latency.
  2. Lọc `response_sent` có latency cao và lấy `correlation_id`.
  3. Mở trace cùng `correlation_id` và so sánh retrieval với generation.
- Mitigation tạm thời: giảm concurrency; dùng retrieval fallback nếu retrieval chậm; giới hạn output nếu generation chậm.
- Owner: `ai-platform`

## Alert 2

- Tên: `HighRequestErrorRate`
- Severity: `critical`
- Duration: `5m`
- Kênh thông báo: Slack
- SLI/SLO liên quan: error rate không vượt quá 2%.
- Điều kiện và thời gian duy trì: `error_rate_pct > 2` liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: request trả HTTP 500 hoặc không có câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra error breakdown và retrieval success.
  2. Lọc `request_failed`, lấy `error_type`, `tool_name` và `correlation_id`.
  3. Mở trace tương ứng để xác định observation lỗi.
- Mitigation tạm thời: tắt incident; retry có giới hạn hoặc dùng fallback khi retrieval không khả dụng.
- Owner: `ai-platform`

## Alert 3

- Tên: `QualityDegradation`
- Severity: `warning`
- Duration: `15m`
- Kênh thông báo: Slack
- SLI/SLO liên quan: quality proxy trung bình tối thiểu 0.75.
- Điều kiện và thời gian duy trì: `quality_score_avg < 0.75` liên tục trong 15 phút.
- Ảnh hưởng tới người dùng: câu trả lời có thể thiếu căn cứ hoặc không đáp ứng câu hỏi.
- Ba bước kiểm tra đầu tiên:
  1. Xác định thời gian quality giảm và prompt version đang hoạt động.
  2. Kiểm tra retrieval context, output token và generation trace.
  3. So sánh với trace của prompt baseline.
- Mitigation tạm thời: rollback label `production`, kiểm tra retrieval context và chạy lại cùng workload.
- Owner: `llm-operations`
