# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Đỗ Quốc An
- **MSSV:** 2A202602892
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/an1-tech/K4-L3-DAY13-DoQuocAn-2A202602892-Monitoring-LLMOps
- **Commit SHA cuối:** `300cb0bbd50c3b81864af739e0965ec1fbcb355b`
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602892`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | [01-pytest.txt](evidence/01-pytest.txt) |
| Log validator | [02-log-validator.txt](evidence/02-log-validator.txt) |
| Dashboard validator | [03-dashboard-validator.txt](evidence/03-dashboard-validator.txt) |
| Structured log | [04-structured-log.png](evidence/04-structured-log.png) |
| PII redaction | [05-pii-redaction.png](evidence/05-pii-redaction.png) |
| Trace list | [06-trace-list.png](evidence/06-trace-list.png) |
| Trace waterfall | [07-trace-waterfall.png](evidence/07-trace-waterfall.png) |
| Trace metadata | [08a-trace-metadata.png](evidence/08a-trace-metadata.png), [08b-generation-usage-cost.png](evidence/08b-generation-usage-cost.png) |
| Prompt versions | [09-prompt-versions.png](evidence/09-prompt-versions.png) |
| Prompt rollback | [10-prompt-rollback.png](evidence/10-prompt-rollback.png) |
| Dashboard runtime | [11-dashboard-overview.png](evidence/11-dashboard-overview.png) |
| Incident metric | [12-incident-metric.txt](evidence/12-incident-metric.txt), [12-incident-metric.png](evidence/12-incident-metric.png) |
| Incident log | [13-incident-log.txt](evidence/13-incident-log.txt), [13-incident-log.png](evidence/13-incident-log.png) |
| Incident trace | [14-incident-trace.txt](evidence/14-incident-trace.txt), [14-incident-trace.png](evidence/14-incident-trace.png) |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 80/100 | 100/100 | Đủ schema, correlation, enrichment và PII scrubbing |
| `validate_dashboard.py` | 6/6 | 6/6 | Dashboard contract hợp lệ |
| `pytest` | 20 passed | 24 passed | Toàn bộ public tests pass |
| Số traces hợp lệ | 10 | 30 | Trace có root/retrieval/generation |
| Số PII leak | Chưa đo | 0 | Validator không phát hiện PII |
| Latency P95 / TTFT P95 | Chưa ghi | 1320 ms / 50 ms | Cửa sổ dashboard 60 phút lúc chạy cuối |
| Retrieval success rate | Chưa ghi | 100% | Không có retrieval failure trong baseline cuối |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware nhận `x-request-id` nếu có, nếu không thì sinh `req-<8-hex>`, bind vào structlog context, lưu trong request state và trả lại qua response header.
- **Các metadata được ghi vào structured log:** `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env`, latency, TTFT, token, cost, quality và trạng thái retrieval.
- **Cách bảo đảm PII được scrub trước khi ghi:** `scrub_event` được đặt trước `JsonlFileProcessor`, đệ quy qua các payload lồng nhau và thay email, điện thoại, CCCD, thẻ bằng marker redaction.
- **Cách kiểm chứng kết quả:** Chạy workload, kiểm tra response header và chạy `scripts/validate_logs.py`; kết quả hiện tại là 100/100 và không phát hiện PII leak.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Chạy `scripts/load_test.py` từ repository này và xác nhận các trace mới trong project `day13-k4-l3a-2A202602892` cùng thời gian chạy.
- **Cấu trúc root/retrieval/generation observations:** Root `lab-agent-run` loại agent có hai child observations là `retrieval` loại retriever và `fake-llm-generation` loại generation.
- **Cách nối trace với log:** Dùng cùng giá trị `correlation_id` trong structured log và trace metadata.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1, labels `baseline` và `production` sau rollback.
- **Version/label candidate:** Version 2, label `candidate`.
- **Trace ID của mỗi version:** Baseline v1: `a8e9414bf79e4b792970daa201245eee`; candidate v2: `9f44d9544bfe4c6302674e5ec605f682`.
- **Cách promote và rollback `production`:** Chuyển `production` sang v2 và tạo trace `b2ed38ee0b46005f524554a917dcf8c3`, sau đó chuyển `production` về v1 và xác nhận bằng trace `914ca012c3d2057eb3be4acb6964178d`.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Streamlit đọc `data/logs.jsonl`, time range 60 phút và refresh 30 giây; gồm latency P50/P95/P99 + TTFT, traffic, error/retrieval success, cost, input/output tokens và quality proxy. Mỗi panel hiển thị đơn vị cùng threshold/SLO tương ứng.
- **SLO và lý do chọn:** 99.5% request trong cửa sổ 28 ngày phải có `response_sent` và latency không vượt quá 3000 ms, nhằm bảo vệ trải nghiệm chờ câu trả lời của người dùng.
- **Cách tính error budget:** 28 ngày có 40.320 phút; 0,5% của cửa sổ là 201,6 phút không đạt SLI.
- **Ba alert và runbook tương ứng:** `HighUserVisibleLatency`, `HighRequestErrorRate`, `QualityDegradation`; runbook tại `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`.
- **Khoảng thời gian điều tra:** `2026-09-29T08:58:00.848309Z` đến `2026-09-29T08:58:23.208242Z`.
- **Triệu chứng từ metrics:** 5 request challenge có latency P50 `2657 ms`, P95 `3637 ms`, P99 `3833 ms`, max `3882 ms`; P95 vượt SLO `3000 ms`.
- **Log line và correlation ID liên quan:** `response_sent` lúc `2026-09-29T08:58:12.537181Z`, `correlation_id=req-f5c6c9de`, `latency_ms=3882`, `tool_name=retrieval`, `tool_success=true`.
- **Trace ID và span gây ảnh hưởng:** Trace `a675427ee7a7b79c45beb6011af138ff` có root `lab-agent-run` khoảng `3.889 s`; child `retrieval` khoảng `2.509 s`, trong khi `fake-llm-generation` chỉ khoảng `0.157 s`. Metadata trace có cùng `correlation_id=req-f5c6c9de`.
- **Root cause:** Incident `rag_slow` làm retrieval chậm; retrieval chiếm phần lớn waterfall và đẩy latency request vượt SLO. LLM generation không phải nút thắt chính.
- **Fix action:** Tắt incident `rag_slow`, khôi phục retrieval bình thường; khi triển khai thật cần timeout cho retriever và fallback/cache khi backend retrieval chậm.
- **Preventive measure:** Alert khi P95 latency vượt `3000 ms` liên tục 5 phút, theo dõi riêng duration/success của span retrieval và bổ sung regression load test cho retrieval timeout/fallback.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Đưa PII scrubber vào pipeline logging trước file writer và tắt capture input/output mặc định của trace để dữ liệu nhạy cảm không rời khỏi ứng dụng.
- **Một lỗi/blocker đã gặp:** Langfuse Cloud v4 không cho organization mới dùng legacy Trace API và yêu cầu Observations API v2 với field groups rõ ràng.
- **Cách tìm nguyên nhân và xử lý:** Đọc thông báo lỗi API, chuyển sang `observations.get_many` với các nhóm `core,basic,metadata,model,usage,metrics,trace_context,prompt`, sau đó đối chiếu trace bằng `correlation_id`.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics xác định cửa sổ có P95 bất thường; log trong đúng cửa sổ cung cấp `correlation_id`; trace có cùng ID cho biết retrieval `2.509 s` chậm hơn generation `0.157 s`, từ đó khoanh vùng root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Prompt version cho phép so sánh và rollback có kiểm soát; token/cost kiểm soát chi phí; SLO và error budget chuyển chỉ số kỹ thuật thành ngưỡng vận hành có thể alert.
- **Điều quan trọng nhất đã học:** Không kết luận sự cố chỉ từ một tín hiệu; phải nối cùng một request qua metrics, structured log và trace waterfall.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Không còn hạng mục kỹ thuật bắt buộc chưa hoàn thành. Dashboard, trace và prompt evidence đã được kiểm tra để không chứa API key, secret hoặc PII thô.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
