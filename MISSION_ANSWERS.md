# MISSION_ANSWERS — Day 14

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-pattern trong `01-localhost-vs-production/develop/app.py`

1. **Hardcode secret:** `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` và `DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"`. Push lên GitHub là lộ ngay.
2. **Config viết cứng trong code:** `DEBUG = True`, `MAX_TOKENS = 500`. Muốn đổi giữa các môi trường phải sửa code.
3. **Log ra secret:** `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")`. Chạy thật thì key nằm trong log.
4. **Dùng `print()` thay vì logging có cấu trúc:** khó lọc, khó gom log.
5. **Không có health check:** không có `/health`, nên platform không biết khi nào agent chết để restart.
6. **Port cố định:** `port=8000`, không đọc biến môi trường `PORT` mà Railway/Render cấp.
7. **`host="localhost"`:** chỉ nhận kết nối từ chính máy, container hoặc máy khác không vào được.
8. **`reload=True`:** chế độ reload của debug còn bật khi chạy thật.
9. **Không xử lý SIGTERM:** khi platform tắt container, request đang chạy bị cắt đột ngột.

### Exercise 1.2: Chạy bản develop

Chạy trong WSL (Debian), `python app.py` trong `01-localhost-vs-production/develop`. Bản này nhận `question` qua query string.

```
$ curl -X POST "http://localhost:8000/ask?question=Hello"
{"answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}
```

Log của server (đo được từ lần chạy này):

```
Starting agent on localhost:8000...
[DEBUG] Got question: Hello
[DEBUG] Using key: sk-hardcoded-fake-key-never-do-this
[DEBUG] Response: Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.
INFO:     127.0.0.1:55032 - "POST /ask?question=Hello HTTP/1.1" 200 OK
```

Nhận xét: bản này chạy và trả lời được, nhưng key bị in ra log (anti-pattern 3), chỉ lắng nghe trên `localhost` (anti-pattern 7). "Chạy được" chưa có nghĩa là sẵn sàng cho production.

### Exercise 1.3: So sánh với bản production

Chạy `production/app.py` (đã `cp .env.example .env`). Bản này nhận JSON. Kết quả:

```
$ curl -s localhost:8000/health
{"status":"ok","uptime_seconds":3.8,"version":"1.0.0","environment":"development","timestamp":"2026-11-25T09:07:54.982344+00:00"}
$ curl -s localhost:8000/ready
{"ready":true}
$ curl -s -X POST localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"Hello"}'
{"question":"Hello","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","model":"gpt-4o-mini"}
```

Gửi SIGTERM (`pkill -TERM -f "python app.py"`), log ghi:

```
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [122]
```

Server lắng nghe trên `http://0.0.0.0:8000` (bản develop là `localhost:8000`).

Ghi chú trung thực: trong lần chạy này, các dòng log JSON do code của app ghi (`logger.info(json.dumps(...))`) không xuất hiện trong `/tmp/prod.log`, chỉ thấy log của uvicorn. Mình chưa kiểm tra nguyên nhân, nên phần "logging JSON" trong bảng dưới dựa trên đọc code (`logging.basicConfig(... format='{"time":...}')`), không phải trên log đã quan sát.

| Feature | Basic (develop) | Advanced (production) | Tại sao quan trọng? |
| --- | --- | --- | --- |
| Config | Hardcode trong code (`DEBUG = True`, `MAX_TOKENS = 500`) | Đọc từ biến môi trường qua `config.py` (`settings`) | Đổi cấu hình giữa dev/staging/prod không cần sửa code; không commit secret |
| Secret | `OPENAI_API_KEY = "sk-..."`, mật khẩu DB trong code | Biến môi trường, chỉ commit `.env.example` | Secret trong repo là bị lộ vĩnh viễn trong lịch sử git |
| Host / Port | `localhost`, `8000` cố định | `settings.host` (0.0.0.0), `settings.port` từ `PORT` | Container cần nghe `0.0.0.0`; Railway/Render cấp `PORT` động |
| Health check | Không có | `GET /health` (liveness), `GET /ready` (readiness) | Platform biết khi nào restart, khi nào được route traffic |
| Logging | `print()`, có in cả secret | `logging` với định dạng JSON, không log secret | Log có cấu trúc dễ tìm kiếm; log không được chứa secret |
| Shutdown | Tắt đột ngột | Có `lifespan`, bắt SIGTERM, chờ request đang chạy | Không mất request khi deploy lại hoặc scale |
| Reload | `reload=True` luôn bật | Chỉ bật khi `DEBUG=true` | Reload tốn tài nguyên và không an toàn khi chạy thật |
| Khác | Không có | CORS giới hạn origin, `GET /metrics` | Giảm bề mặt tấn công; có số liệu để giám sát |

**Tự kiểm tra (CP1):** anti-pattern `host="localhost"` và `port=8000` trong `develop/app.py` đã được `production/app.py` sửa thành `host=settings.host` và `port=settings.port`; `reload=True` sửa thành `reload=settings.debug`.

## Part 2: Docker

(chưa làm)

## Part 3: Cloud Deployment

(chưa làm)

## Part 4: API Security

(chưa làm)

## Part 5: Scaling & Reliability

(chưa làm)

## Output `check_production_ready.py`

(chưa làm)

## AI log

- **Part 1 (Exercise 1.1):** hỏi Claude đọc `develop/app.py` và liệt kê anti-pattern. Nhận danh sách 9 mục. Mình tự đối chiếu từng mục với đoạn code tương ứng trong file.
- **Môi trường:** nhờ Claude hướng dẫn dựng WSL2 (Debian từ image Docker Python 3.11) và bật Docker trong WSL. Mình tự chạy lệnh và kiểm tra bằng `python3 --version`, `docker version`, `docker compose version`, `docker run --rm hello-world`.
- **Exercise 1.2, 1.3:** lệnh chạy do Claude gợi ý; mình tự chạy, kết quả ở trên là output thật.
