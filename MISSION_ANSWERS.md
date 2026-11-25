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

### Exercise 2.1: Đọc `02-docker/develop/Dockerfile`

1. **Base image:** `python:3.11` (bản đầy đủ, khoảng 1 GB).
2. **Working directory:** `/app`.
3. **Vì sao `COPY requirements.txt` trước `COPY app.py`:** Docker cache theo từng layer. Requirements ít đổi, nên layer `pip install` được dùng lại; chỉ khi sửa code thì mới copy lại phần code, không phải cài lại thư viện.
4. **CMD và ENTRYPOINT:** `CMD ["python", "app.py"]` là lệnh mặc định, có thể bị ghi đè khi `docker run <image> <lệnh khác>`. ENTRYPOINT là lệnh cố định của container, tham số truyền vào được nối thêm sau nó.

### Exercise 2.2-2.3: Build và so sánh image (đo thật bằng `docker images`)

```
$ docker images | grep my-agent
my-agent:advanced      0249a31b522b        240MB         57.7MB
my-agent:develop       46922c8581f8       1.67GB          427MB
```

| Image | Kích thước | Ghi chú |
| --- | --- | --- |
| `my-agent:develop` (single-stage, `python:3.11`) | 1.67 GB | cột thứ nhất của Docker Desktop |
| `my-agent:advanced` (multi-stage, `python:3.11-slim`) | 240 MB | chạy bằng user `appuser`, không phải root |

Chênh lệch: (1.67 GB ≈ 1710 MB) giảm xuống 240 MB, tức giảm khoảng 86%. Multi-stage giảm dung lượng vì stage runtime chỉ copy `site-packages` đã cài, không mang theo build tools; thêm vào đó base `-slim` nhỏ hơn nhiều so với bản đầy đủ.

Gọi container production (`docker run -d -p 8000:8000 my-agent:advanced`), bản này nhận JSON:

```
$ curl -s localhost:8000/health
{"status":"ok","uptime_seconds":12.4,"version":"2.0.0","timestamp":"2026-11-25T09:45:35.682583"}
$ curl -s -X POST localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"Hello"}'
{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

Lần đầu mình gọi `/ask?question=Hello` (query string) thì server trả 500 vì code đọc JSON body (`request.json()`); đổi sang gửi JSON thì chạy. Mình chưa chạy container của image develop, nên không có output gọi bản develop.

**Chỉnh sửa vì môi trường:** mạng của mình chặn `apt-get` trong lúc build (lỗi `401 VG-AuthenticationRequired`). `requirements.txt` của bản production chỉ có `fastapi` và `uvicorn` (không cần biên dịch), nên mình xóa bước `RUN apt-get ... gcc libpq-dev` khỏi `02-docker/production/Dockerfile`, rồi build lại thành công.

### Exercise 2.4: Stack Docker Compose

Sơ đồ:

```
Client --> Nginx (cổng 80/443) --> agent (FastAPI, cổng 8000 nội bộ)
                                      |--> redis  (cache, rate limit)
                                      |--> qdrant (vector DB)
```

Cả 4 service chung network `internal`; chỉ Nginx mở cổng ra ngoài. Agent chờ redis và qdrant `healthy` mới khởi động (`depends_on` + `condition: service_healthy`).

Kết quả thật khi gọi qua Nginx:

```
$ curl -s localhost/health
{"status":"ok","uptime_seconds":92.6,"version":"2.0.0","timestamp":"2026-11-25T09:52:31.676074"}
$ curl -s -X POST localhost/ask -H "Content-Type: application/json" -d '{"question":"Hello"}'
{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
$ docker compose ps
production-agent-1    Up (healthy)   8000/tcp
production-nginx-1    Up             0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
production-qdrant-1   Up (healthy)   6333-6334/tcp
production-redis-1    Up (healthy)   6379/tcp
```

**Chỉnh sửa vì môi trường:** Docker Desktop không mount được `nginx/nginx.conf` từ Debian-Lab (lỗi `not a directory`, cả khi chép sang `/mnt/d`). Mình chạy stack trong bản sao `/mnt/d/lab14`, thêm `Dockerfile.nginx` (`FROM nginx:alpine` + `COPY nginx/nginx.conf`) và đổi service nginx sang `build`, bỏ dòng mount. Chỉ sửa trong bản sao, repo gốc không đổi phần này.

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
