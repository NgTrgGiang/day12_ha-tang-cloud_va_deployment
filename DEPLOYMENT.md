# Deployment Information

## Public URL
https://day12-ha-tang-cloud-va-deployment-axaq.onrender.com

## Platform
**Render** (gói Free, region Singapore, runtime Docker)
Root Directory: `06-lab-complete`

> ⚠️ Gói Free của Render tự ngủ sau 15 phút không có request.
> Request đầu tiên sau khi ngủ mất ~50 giây để "đánh thức" — đây là hành vi bình thường.

## Test Commands

### 1. Health check (public, không cần key)
```bash
curl https://day12-ha-tang-cloud-va-deployment-axaq.onrender.com/health
```
Kết quả thực tế:
```json
{"status":"ok","version":"1.0.0","environment":"production","uptime_seconds":112.3,"total_requests":13,"checks":{"llm":"mock"}}
```

### 2. Gọi /ask KHÔNG có API key → bị chặn 401
```bash
curl -X POST https://day12-ha-tang-cloud-va-deployment-axaq.onrender.com/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'
```
→ **401 Unauthorized** (đúng như thiết kế: bắt buộc xác thực).

### 3. Gọi /ask CÓ API key → 200 OK
```bash
curl -X POST https://day12-ha-tang-cloud-va-deployment-axaq.onrender.com/ask \
  -H "X-API-Key: lab12-secret-key-aicb" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is deployment?"}'
```
Kết quả thực tế:
```json
{"question":"What is deployment?","answer":"Deployment là quá trình đưa code từ máy bạn lên server để người khác dùng được.","model":"gpt-4o-mini"}
```

> Trên Windows PowerShell, thay `curl` bằng:
> ```powershell
> Invoke-RestMethod "https://day12-ha-tang-cloud-va-deployment-axaq.onrender.com/ask" -Method POST -ContentType "application/json" -Headers @{"X-API-Key"="lab12-secret-key-aicb"} -Body '{"question":"What is deployment?"}'
> ```

## Environment Variables (set trên Render Dashboard, KHÔNG commit vào code)
| Biến | Mục đích |
|------|----------|
| `AGENT_API_KEY` | Chìa khóa xác thực cho endpoint `/ask` |
| `JWT_SECRET` | Khóa ký JWT (bắt buộc ở chế độ production) |
| `ENVIRONMENT` | `production` |

## Endpoints
| Method | Path | Auth | Mô tả |
|--------|------|------|-------|
| GET | `/` | Không | Thông tin app |
| GET | `/health` | Không | Liveness probe |
| GET | `/ready` | Không | Readiness probe |
| POST | `/ask` | **Có (X-API-Key)** | Hỏi agent |
| GET | `/metrics` | Có | Thống kê (uptime, cost, requests) |
