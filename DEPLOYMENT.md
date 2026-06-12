# Deployment Information

> Agent nộp bài: **FAQ Chatbot Agent** (tự xây từ đầu, thư mục `faq-chatbot-agent/`).
> Đây là chatbot tư vấn câu hỏi thường gặp cho shop online ShopMini, có lưu lịch sử hội thoại theo phiên.

## Public URL
https://faq-chatbot-agent.onrender.com

## Platform
**Render** (gói Free, region Singapore, runtime Docker)
Root Directory: `faq-chatbot-agent`

> ⚠️ Gói Free của Render tự ngủ sau 15 phút không có request.
> Request đầu tiên sau khi ngủ mất ~50 giây để "đánh thức" — đây là hành vi bình thường.

## Test Commands

### 1. Health check (public, không cần key)
```bash
curl https://faq-chatbot-agent.onrender.com/health
```
Kết quả thực tế:
```json
{"status":"ok","version":"1.0.0","env":"production","uptime_s":115.7,"total_chats":0}
```

### 2. Gọi /chat KHÔNG có API key → bị chặn 401
```bash
curl -X POST https://faq-chatbot-agent.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"shop giao hang bao lau?"}'
```
→ **401 Unauthorized** (đúng thiết kế: bắt buộc xác thực).

### 3. Gọi /chat CÓ API key → 200 OK
```bash
curl -X POST https://faq-chatbot-agent.onrender.com/chat \
  -H "X-API-Key: faq-secret-key-aicb" \
  -H "Content-Type: application/json" \
  -d '{"message":"shop giao hang bao lau?"}'
```
Kết quả thực tế:
```json
{"session_id":"...","reply":"ShopMini giao nội thành trong 1-2 ngày, ngoại tỉnh 3-5 ngày. Phí ship đồng giá 25.000đ, miễn phí cho đơn trên 300.000đ.","turn":1,"spent_usd":0.0}
```

> Trên Windows PowerShell:
> ```powershell
> Invoke-RestMethod "https://faq-chatbot-agent.onrender.com/chat" -Method POST -ContentType "application/json" -Headers @{"X-API-Key"="faq-secret-key-aicb"} -Body '{"message":"shop giao hang bao lau?"}'
> ```

## Environment Variables (set trên Render Dashboard, KHÔNG commit vào code)
| Biến | Mục đích |
|------|----------|
| `API_KEY` | Chìa khóa xác thực cho `/chat`, `/metrics` |
| `ENVIRONMENT` | `production` |

## Endpoints
| Method | Path | Auth | Mô tả |
|--------|------|------|-------|
| GET | `/` | Không | Thông tin app |
| GET | `/health` | Không | Liveness probe |
| GET | `/ready` | Không | Readiness probe |
| POST | `/chat` | **Có (X-API-Key)** | Gửi tin nhắn, nhận trả lời FAQ |
| GET | `/chat/{session_id}/history` | **Có** | Xem lịch sử hội thoại |
| GET | `/metrics` | Có | Thống kê (uptime, chats, ngân sách) |

---

## Ghi chú
- Image Docker: **277 MB** (multi-stage + python:3.11-slim, < 500 MB).
- Agent chạy bằng non-root user, đọc cổng từ `$PORT` Render cấp.
- (Tham khảo) Bài giải mẫu `06-lab-complete` cũng từng được deploy tại
  https://day12-ha-tang-cloud-va-deployment-axaq.onrender.com — nhưng bài nộp chính
  là **FAQ Chatbot Agent** tự xây ở trên.
