# Benchmark & Observability Report — Day 14

**Họ tên:** Nguyễn Đức Minh (2A202603563)
**Ngày chạy:** 2026-11-25
**Môi trường:** Windows + WSL2 (Debian), Docker Desktop. Chưa đo thông số CPU/RAM cụ thể của máy.

> Mọi con số trong mục 2 và 3 lấy từ các file `reports/*.json` do `load_test.py` và `run_eval.py` ghi ra. Mục 4 và 5 (stack quan sát, Locust scale) **chưa làm**, sẽ điền khi chạy xong.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | < 500 ms | Mặc định của `load_test.py`. Người dùng cảm nhận độ chậm qua đuôi phân phối, không qua trung bình; mock LLM bình thường trả lời khoảng 150-220 ms nên 500 ms còn dư chỗ cho vài request chậm |
| Error rate `/ask` | < 2 % | Mặc định của `load_test.py`; ngưỡng alert nên lỏng hơn SLO một chút để tránh báo động giả |
| Accuracy trên golden dataset | ≥ 80 % | Ngưỡng của quality gate trong `run_eval.py`, kèm điều kiện không có câu nào regression so với baseline |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

Mỗi lần chạy 300 request vào agent v2 (cổng 8002).

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 3.79 | 190.7 | 728.8 | 1703.3 | 2.00% (6/300) | FAIL |
| 10 | 37.33 | 192.8 | 225.8 | 1714.8 | 1.67% (5/300) | PASS |
| 50 | 101.28 | 210.9 | 356.9 | 1700.4 | 1.33% (4/300) | PASS |
| 100 | 52.84 | 1064.2 | 4874.5 | 5309.5 | 2.00% (6/300) | FAIL |

(Nguồn: `reports/load_v2_c1.json`, `c10`, `c50`, `c100`. Lỗi đều là HTTP 503.)

**Nhận xét:** RPS **không** tăng tuyến tính. Từ concurrency 1 lên 10, RPS tăng khoảng 9,9 lần (gần tuyến tính, vì mỗi request chủ yếu chờ 150-200 ms nên chạy song song hiệu quả). Từ 10 lên 50 chỉ tăng khoảng 2,7 lần, và ở 100 thì RPS **giảm** xuống 52,84 trong khi p95 vọt lên 4874 ms: hệ thống đã quá tải, request xếp hàng chờ nên latency tăng mà thông lượng không tăng. Mình chưa đo CPU nên chưa chỉ ra được tài nguyên cụ thể là nút thắt (nghi ngờ là chỉ có một tiến trình uvicorn xử lý mọi request). Ở concurrency 1, p95 cao (728,8 ms) vì chỉ có 300 mẫu chạy tuần tự và có một số request chậm khoảng 1,7 s (p99 = 1703 ms), nên p95 phụ thuộc nhiều vào số request chậm rơi vào mẫu.

Ngoài ra, mọi lần chạy đều có khoảng 1-2% lỗi 503 (kể cả khi `MOCK_SLOW_RATE=0`, xem 2.2). Mình chưa kiểm tra giá trị mặc định của `MOCK_ERROR_RATE` nên chỉ ghi nhận hiện tượng này, chưa xác định nguyên nhân.

### 2.2 Tail latency

Chạy với concurrency 20, 300 request, khởi động lại v2 cho mỗi mức `MOCK_SLOW_RATE`.

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 188.1 | 218.0 | 228.7 |
| 0.03 (mặc định) | 242.8 | 236.2 | 1699.4 |
| 0.1 | 366.5 | 1687.7 | 1720.8 |

(Nguồn: `reports/load_v2_slow_0.json`, `load_v2_slow_0.03.json`, `load_v2_slow_0.1.json`.)

**Nhận xét:** Chỉ số nhạy nhất với request chậm là p99. Với 3% request chậm, avg chỉ tăng từ 188,1 lên 242,8 ms (khoảng +29%) trong khi p99 tăng từ 228,7 lên 1699,4 ms (khoảng 7,4 lần). Khi tỉ lệ chậm lên 10% thì p95 cũng vọt lên 1687,7 ms và SLO p95 bị vi phạm (FAIL), còn avg (366,5 ms) vẫn trông "chấp nhận được". Vì vậy SLO nên đặt theo p95/p99: trung bình che mất nhóm người dùng bị chờ gần 2 giây.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.3% (1/23) | 91.3% (21/23) | 100% (23/23) |
| Avg tokens / câu | 56.0 | 108.8 | 113.7 |
| Tổng cost (USD) | 0.000388 | 0.000757 | 0.000790 |
| Cost / câu đúng (USD) | 0.000388 | 0.0000361 | 0.0000343 (tính: 0.000790 / 23) |
| Latency p95 (ms) | 190.7 | 209.6 | 215.2 |
| Quality gate | FAIL | PASS | PASS (ngưỡng 100%, 0 regression) |

(Nguồn: `reports/eval_v1.json`, `eval_v2.json`, `eval_v2_fixed.json`. Cost/câu đúng của v1 và v2 lấy từ output của `run_eval.py`; của bản đã sửa tự tính từ tổng cost chia 23.)

**Những câu v2 trả lời sai ban đầu và cách sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| `security-02` ("JWT khác gì API key?") | token, hết hạn, chữ ký | Thêm vào `KNOWLEDGE_BASE` (trong `utils/mock_llm.py`) một tài liệu cho từ khóa `jwt`: API key là chuỗi cố định không tự hết hạn; JWT là token có chữ ký số, chứa thông tin user và thời điểm hết hạn |
| `scaling-03` ("Kubernetes HPA scale dựa trên chỉ số nào?") | cpu, memory, custom metrics | Thêm tài liệu cho từ khóa `hpa`/`kubernetes`/`autoscal`: HPA scale số pod theo CPU, memory hoặc custom metrics như RPS, độ dài hàng đợi |

Sau khi sửa và khởi động lại v2, eval chạy với `--min-accuracy 1.0 --baseline reports/eval_v2.json`: 2 câu được cải thiện, **0 câu regression**.

**Nhận xét về trade-off:** v2 dùng nhiều token hơn khoảng gấp đôi mỗi câu (108,8 so với 56,0) và p95 cao hơn chút (209,6 so với 190,7 ms), nhưng accuracy tăng từ 4,3% lên 91,3%. Vì v1 gần như không trả lời đúng câu nào, "cost / câu" (v2 đắt hơn) gây hiểu nhầm; "cost / câu đúng" cho thấy v2 rẻ hơn khoảng 10 lần (0,0000361 so với 0,000388 USD). Sau khi sửa KB, cost và token tăng nhẹ nhưng cost/câu đúng còn giảm thêm vì có thêm 2 câu đúng.

**Quality gate trong CI (Exercise 7.3):** `run_eval.py` trả exit code 1 khi accuracy dưới ngưỡng hoặc có regression so với baseline, nên một job GitHub Actions chạy `python eval/run_eval.py --url http://localhost:8000 --min-accuracy 0.85 --baseline ...` sẽ fail và chặn merge PR. Mình chưa tạo file workflow trong repo này.

---

## 4. Observability stack (production)

(Chưa làm.)

## 5. Benchmark scaling (production, Locust headless)

(Chưa làm.)

---

## 6. Kết luận

- Đã học được: (1) SLO nên đặt theo p95/p99 chứ không theo trung bình, vì chỉ 3% request chậm đã làm p99 tăng khoảng 7 lần trong khi avg tăng khoảng 29%; (2) so sánh hai phiên bản agent bằng "cost / câu đúng" công bằng hơn "cost / câu"; (3) tăng concurrency không làm RPS tăng mãi: đến một mức hệ thống bão hòa và latency tăng vọt.
