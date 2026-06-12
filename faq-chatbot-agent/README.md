# FAQ Chatbot Agent — ShopMini

Chatbot tư vấn câu hỏi thường gặp (FAQ) cho shop online, có lưu lịch sử hội thoại
theo phiên. Đây là agent production-ready được xây cho Lab Day 12.

## Tính năng
- 🔑 API key authentication (header `X-API-Key`)
- ⏱️ Rate limiting (sliding window, mặc định 15 req/phút)
- 💰 Cost guard (ngân sách USD/ngày)
- ❤️ Health check `/health` + readiness `/ready`
- 🧹 Graceful shutdown (SIGTERM)
- ⚙️ Config từ biến môi trường (12-factor), không hardcode secret
- 🐳 Dockerfile multi-stage, chạy bằng non-root user

## Cấu trúc
```
faq-chatbot-agent/
├── server.py        # FastAPI app + các endpoint
├── settings.py      # cấu hình (pydantic-settings, đọc từ env)
├── security.py      # auth + rate limit + cost guard
├── faq_brain.py     # "bộ não" trả lời FAQ (thay cho LLM)
├── Dockerfile       # multi-stage, dùng virtualenv
├── render.yaml      # deploy Render
├── requirements.txt
├── .env.example
└── .dockerignore
```

## Chạy local
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env       # rồi sửa API_KEY nếu muốn
python server.py
```

## Các endpoint
| Method | Path | Auth | Mô tả |
|--------|------|------|-------|
| GET | `/` | Không | Thông tin app |
| GET | `/health` | Không | Liveness probe |
| GET | `/ready` | Không | Readiness probe |
| POST | `/chat` | **Có** | Gửi tin nhắn, nhận trả lời |
| GET | `/chat/{session_id}/history` | **Có** | Xem lịch sử phiên |
| GET | `/metrics` | **Có** | Thống kê |

## Ví dụ gọi /chat
```bash
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: dev-key-doi-trong-production" \
  -H "Content-Type: application/json" \
  -d '{"message": "shop giao hàng bao lâu?"}'
```

## Deploy Render
1. Push code lên GitHub.
2. Render → New → Web Service → chọn repo.
3. **Root Directory = `faq-chatbot-agent`**, Runtime = Docker, Instance = Free.
4. Thêm biến `ENVIRONMENT=production` và `API_KEY=<key-bí-mật-của-bạn>`.
5. Create → đợi "Live" → lấy URL.
