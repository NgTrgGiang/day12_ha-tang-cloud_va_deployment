"""
FAQ Chatbot Agent — server chính.

Chatbot tư vấn câu hỏi thường gặp (FAQ) cho shop online "ShopMini",
có lưu lịch sử hội thoại theo từng phiên (session).

Tính năng production:
  - API key authentication, rate limiting, cost guard  (xem security.py)
  - Health (/health) + readiness (/ready) probe
  - Graceful shutdown khi nhận SIGTERM
  - Cấu hình từ biến môi trường (12-factor), không hardcode secret
  - Structured JSON logging
"""
import json
import logging
import signal
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from settings import settings
from security import (
    require_api_key,
    enforce_rate_limit,
    enforce_budget_then_charge,
    budget_status,
)
from faq_brain import answer as faq_answer

# ── Logging dạng JSON ──────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
)
log = logging.getLogger("faq-agent")

# ── Trạng thái toàn cục ────────────────────────────────────
STARTED_AT = time.time()
_ready = False
_total_chats = 0

# Lịch sử hội thoại theo phiên (lưu trong RAM).
# Ghi chú: khi scale nhiều instance nên chuyển sang Redis để stateless.
_sessions: dict[str, list] = defaultdict(list)


# ── Vòng đời app: khởi động & tắt ──────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ready
    # Fail-fast: không cho chạy production với key mặc định
    if settings.environment == "production" and settings.api_key == "dev-key-doi-trong-production":
        raise RuntimeError("API_KEY phải được đổi khác mặc định khi chạy production!")
    log.info(json.dumps({"event": "startup", "app": settings.app_name, "env": settings.environment}))
    _ready = True
    yield
    _ready = False
    log.info(json.dumps({"event": "shutdown"}))


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list(),
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)


# ── Middleware: security headers + log mỗi request ─────────
@app.middleware("http")
async def add_headers_and_log(request: Request, call_next):
    start = time.time()
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if "server" in response.headers:          # ẩn thông tin server
        del response.headers["server"]
    log.info(json.dumps({
        "event": "http",
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "ms": round((time.time() - start) * 1000, 1),
    }))
    return response


# ── Models: kiểm tra dữ liệu vào/ra ────────────────────────
class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    session_id: str | None = None  # None = tạo phiên mới


class ChatOut(BaseModel):
    session_id: str
    reply: str
    turn: int
    spent_usd: float


# ── Endpoints ──────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "env": settings.environment,
        "info": "POST /chat kèm header X-API-Key để trò chuyện với trợ lý ShopMini.",
    }


@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, key: str = Depends(require_api_key)):
    """
    Gửi tin nhắn, nhận câu trả lời FAQ. Lưu lịch sử theo session_id.

    - **Auth:** header `X-API-Key`
    - Truyền lại `session_id` ở các lượt sau để tiếp tục hội thoại.
    """
    global _total_chats
    enforce_rate_limit(key[:8])                       # cửa 2: giới hạn tốc độ

    input_tokens = len(body.message.split()) * 2
    reply = faq_answer(body.message)                  # gọi "bộ não" FAQ
    output_tokens = len(reply.split()) * 2
    spent = enforce_budget_then_charge(input_tokens, output_tokens)  # cửa 3: ngân sách

    # Lưu lịch sử hội thoại
    sid = body.session_id or str(uuid.uuid4())
    history = _sessions[sid]
    history.append({"role": "user", "text": body.message})
    history.append({"role": "bot", "text": reply})
    if len(history) > 40:                             # giữ tối đa 20 lượt
        del history[:-40]

    _total_chats += 1
    log.info(json.dumps({"event": "chat", "session": sid, "msg_len": len(body.message)}))
    return ChatOut(session_id=sid, reply=reply, turn=len(history) // 2, spent_usd=spent)


@app.get("/chat/{session_id}/history")
def get_history(session_id: str, key: str = Depends(require_api_key)):
    """Xem lại lịch sử hội thoại của một phiên."""
    messages = _sessions.get(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên này (có thể đã hết hạn).")
    return {"session_id": session_id, "messages": messages, "count": len(messages)}


@app.get("/health")
def health():
    """Liveness probe — cloud restart container nếu endpoint này hỏng."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "env": settings.environment,
        "uptime_s": round(time.time() - STARTED_AT, 1),
        "total_chats": _total_chats,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready():
    """Readiness probe — 503 khi agent chưa khởi động xong."""
    if not _ready:
        raise HTTPException(status_code=503, detail="Agent chưa sẵn sàng.")
    return {"ready": True}


@app.get("/metrics")
def metrics(key: str = Depends(require_api_key)):
    """Thống kê (cần API key)."""
    return {
        "uptime_s": round(time.time() - STARTED_AT, 1),
        "total_chats": _total_chats,
        "active_sessions": len(_sessions),
        **budget_status(),
    }


# ── Graceful shutdown ──────────────────────────────────────
def _on_sigterm(signum, _frame):
    log.info(json.dumps({"event": "sigterm", "signum": signum}))


signal.signal(signal.SIGTERM, _on_sigterm)


if __name__ == "__main__":
    import uvicorn
    log.info(f"Khởi động {settings.app_name} tại {settings.host}:{settings.port}")
    uvicorn.run(
        "server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=20,
    )
