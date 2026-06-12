# Day 12 Lab — Mission Answers

> **Họ tên:** Nguyễn Trường Giang   
> **MSSV:** 2A202600624 
> **Ngày:** 2026-06-12

---

## Part 1: Localhost vs Production

### Exercise 1.1: Các anti-pattern tìm được trong `01-localhost-vs-production/develop/app.py`

1. **Hardcode secret trong code** — `OPENAI_API_KEY = "sk-hardcoded-fake-key..."` và `DATABASE_URL` chứa mật khẩu. Push lên GitHub là lộ ngay.
2. **Không có config management** — `DEBUG`, `MAX_TOKENS` viết cứng trong code, muốn đổi phải sửa code.
3. **Dùng `print()` thay vì logging** — và còn `print` cả API key ra log (lộ secret trong log).
4. **Không có health check endpoint** — platform không biết khi nào agent chết để restart.
5. **Port và host viết cứng** — `host="localhost"` (không nhận kết nối ngoài container), `port=8000` (không đọc từ biến môi trường `PORT` mà Railway/Render tự cấp).
6. **Bật `reload=True`** — chế độ debug, không được dùng trong production (tốn tài nguyên, không an toàn).

### Exercise 1.3: Bảng so sánh basic vs production

| Feature | Basic (develop) | Production | Tại sao quan trọng? |
|---------|-----------------|------------|---------------------|
| Config | Hardcode trong code | Đọc từ environment variables (`config.py`) | Đổi cấu hình dev/prod không cần sửa code; không lộ secret |
| Health check | Không có | Có `/health`, `/ready`, `/metrics` | Platform tự restart khi agent chết; load balancer biết khi nào route traffic |
| Logging | `print()` (lộ cả secret) | JSON structured logging, không log secret | Dễ parse trong hệ thống log (Datadog/Loki); an toàn |
| Shutdown | Tắt đột ngột | Graceful (bắt SIGTERM, hoàn thành request đang chạy) | Không làm rớt request của user khi deploy/restart |
| Host/Port | `localhost:8000` cứng | `0.0.0.0` + `PORT` từ env | Chạy được trong container và trên cloud |

---

## Part 2: Docker

### Exercise 2.1: Câu hỏi về Dockerfile (`02-docker/develop/Dockerfile`)

1. **Base image là gì?** `python:3.11` — bản Python đầy đủ (~1 GB).
2. **Working directory là gì?** `/app` (đặt bằng `WORKDIR /app`).
3. **Tại sao COPY requirements.txt trước?** Để tận dụng **Docker layer cache**. Nếu code đổi nhưng requirements không đổi, Docker dùng lại layer cài dependencies đã cache → build nhanh hơn nhiều.
4. **CMD vs ENTRYPOINT khác nhau thế nào?** `CMD` đặt lệnh mặc định, **có thể bị ghi đè** khi `docker run <image> <lệnh khác>`. `ENTRYPOINT` đặt lệnh **luôn chạy**, các tham số thêm vào sau sẽ được nối vào ENTRYPOINT thay vì thay thế.

### Exercise 2.3: So sánh kích thước image

- Develop (single-stage, `python:3.11`): ~1 GB (base image Python đầy đủ)
- Production (multi-stage, `python:3.11-slim`): **247 MB** (đo thực tế khi build image multi-stage của `06-lab-complete`) → đạt yêu cầu < 500 MB ✅
- **Tại sao production nhỏ hơn?** Multi-stage build: stage `builder` chứa gcc + build tools để cài deps, nhưng stage `runtime` cuối cùng **chỉ copy site-packages đã cài**, bỏ hết build tools. Cộng với base image `slim` nhẹ hơn nhiều.

---

## Part 3: Cloud Deployment

### Exercise 3.1: Deploy lên Cloud (dùng Render thay cho Railway)

> Agent nộp bài là **FAQ Chatbot Agent** em tự xây ở thư mục `faq-chatbot-agent/`
> (không dùng bài giải mẫu `06-lab-complete`). Chi tiết trong `DEPLOYMENT.md`.

- **Platform:** Render (Free, region Singapore, runtime Docker, Root Directory = `faq-chatbot-agent`)
- **Public URL:** https://faq-chatbot-agent.onrender.com
- **Kiểm chứng (chạy thật):**
  - `GET /health` → 200, `env: production`
  - `POST /chat` không có key → **401** (bị chặn)
  - `POST /chat` có header `X-API-Key` → **200** + trả lời FAQ
- **Screenshot:** 

### Exercise 3.2: So sánh `render.yaml` và `railway.toml`

| | railway.toml | render.yaml |
|---|---|---|
| Định dạng | TOML | YAML |
| Build | Tự detect (Nixpacks) hoặc Dockerfile | `buildCommand: pip install -r requirements.txt` |
| Start command | `uvicorn app:app --host 0.0.0.0 --port $PORT` | Tương tự |
| Health check | `healthcheckPath = "/health"` | `healthCheckPath: /health` |
| Khác biệt chính | Cấu hình tối giản, chỉ build + deploy + restart policy | Khai báo nhiều dịch vụ trong 1 file (web + Redis), hỗ trợ `generateValue` (tự sinh secret) và `sync: false` (set secret thủ công trên dashboard) |

---

## Part 4: API Security

### Exercise 4.1: API Key authentication
- API key được kiểm tra trong hàm `verify_api_key()` qua header `X-API-Key`.
- Sai/thiếu key → trả về **401** (thiếu) hoặc **403** (sai key).
- Rotate key: đổi giá trị biến môi trường `AGENT_API_KEY` rồi restart — không cần sửa code.

**Kết quả test (trên service đã deploy):**
```
POST /ask  (không key)        -> 401 Unauthorized   ✅ bị chặn
POST /ask  (X-API-Key đúng)   -> 200 OK + câu trả lời ✅
```

### Exercise 4.2 & 4.3: JWT + Rate limiting
- **JWT flow** (`auth.py`): `POST /auth/token` đổi username/password lấy token → gửi token qua header `Authorization: Bearer <token>` → server verify chữ ký, lấy ra user/role mà không cần truy vấn DB mỗi request.
- **Rate limiter** (`rate_limiter.py`): dùng thuật toán **Sliding Window Counter** (lưu timestamp trong `deque`, loại bỏ timestamp cũ ngoài cửa sổ 60s). Limit: **user 10 req/phút, admin 100 req/phút**. Vượt → trả **429**. Admin bypass nhờ dùng instance limiter riêng (tier cao hơn).

**Kết quả test (chạy `06-lab-complete` local, limit mặc định 20 req/phút):**
```
Gọi 25 request liên tiếp -> 19 request đầu: 200 OK
                            6 request sau:  429 Too Many Requests  ✅
```

### Exercise 4.4: Cost guard
Logic trong `cost_guard.py`:
- Mỗi user có ngân sách ngày (mặc định **$1/ngày**), cộng thêm **ngân sách global $10/ngày**.
- Trước khi gọi LLM → `check_budget()`: vượt budget user trả **402 (Payment Required)**, vượt global trả **503**.
- Sau khi gọi → `record_usage()` cộng dồn token đã dùng và quy ra tiền theo giá `$0.15/1M` input và `$0.60/1M` output (GPT-4o-mini).
- Cảnh báo khi dùng tới 80% budget. Reset theo ngày.

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks
- `/health` (**liveness**): agent còn sống không → trả 200. Platform restart container nếu fail.
- `/ready` (**readiness**): agent sẵn sàng nhận traffic chưa → trả 503 khi đang khởi động hoặc Redis chưa kết nối được. Load balancer dùng cái này để quyết định có route traffic vào không.

### Exercise 5.2: Graceful shutdown
Bắt tín hiệu **SIGTERM** (platform gửi khi muốn tắt container) → ngừng nhận request mới, hoàn thành request đang chạy, đóng kết nối rồi mới thoát. Uvicorn được cấu hình `timeout_graceful_shutdown=30`.

### Exercise 5.3: Stateless design
- **Anti-pattern:** lưu conversation history trong biến memory → khi scale ra nhiều instance, mỗi instance có memory riêng, user gọi request sau rơi vào instance khác → mất history.
- **Đúng:** lưu session/history trong **Redis** (`05-scaling-reliability/production/app.py`). Bất kỳ instance nào cũng đọc được → có thể scale vô hạn.

### Exercise 5.4 & 5.5: Load balancing & test stateless
- Chạy nhiều instance sau Nginx: `docker compose up --scale agent=3`. Nginx round-robin phân tán request.
- `test_stateless.py` gửi nhiều request trong cùng 1 session, in ra `served_by` (instance phục vụ) → chứng minh dù request rơi vào instance khác nhau, history vẫn nguyên vẹn nhờ Redis.

**Ghi chú:** phần stateless + Redis + load balancing (`05-scaling-reliability/production`) cần `docker compose up --scale agent=3` để chạy multi-instance. Lab nộp tập trung vào agent đơn ở `06-lab-complete` (đã deploy thật trên Render), đã verify health/readiness/auth/rate-limit hoạt động đúng.

---

## Ghi chú thêm — các bug đã phát hiện & sửa trong khi làm lab

1. **Lỗi 500 ở mọi request** (`06-lab-complete/app/main.py`): dùng
   `response.headers.pop("server", None)` nhưng Starlette `MutableHeaders` không có
   method `.pop()` → đã sửa thành `del response.headers["server"]`.

2. **Thiếu `utils/`**: `06-lab-complete` không có thư mục `utils/` (mock LLM) nên không
   chạy/deploy độc lập được → đã copy `utils/` vào trong `06-lab-complete`.

3. **Container build được nhưng không chạy** (`06-lab-complete/Dockerfile`): home của user
   là `/app` nhưng thư viện copy vào `/home/agent/.local` → Python báo
   `ModuleNotFoundError: No module named 'uvicorn'`. Đã sửa `PYTHONPATH` trỏ đúng
   site-packages. Đồng thời sửa `CMD` để đọc cổng từ `$PORT` (Render/Railway tự inject)
   thay vì ghim cứng 8000.

Sau khi sửa: `check_production_ready.py` đạt **20/20 (100%)**, Docker image **247 MB**,
container chạy thật và service đã **deploy thành công lên Render** (xem `DEPLOYMENT.md`).
