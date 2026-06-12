"""
Security — gom 3 lớp bảo vệ vào một chỗ cho gọn:

  1. API key authentication  — kiểm tra header X-API-Key
  2. Rate limiting           — sliding window theo từng key (req/phút)
  3. Cost guard              — chặn khi vượt ngân sách USD trong ngày

Cả 3 đều ném HTTPException với mã lỗi phù hợp để FastAPI tự trả về cho client.
"""
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException

from settings import settings


# ─────────────────────────────────────────────
# 1. Authentication
# ─────────────────────────────────────────────
def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    """Dependency: bắt buộc header X-API-Key đúng, nếu không trả 401."""
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="Thiếu hoặc sai API key. Gửi kèm header: X-API-Key: <key>",
        )
    return x_api_key


# ─────────────────────────────────────────────
# 2. Rate limiter (sliding window 60 giây)
# ─────────────────────────────────────────────
_hits: dict[str, deque] = defaultdict(deque)


def enforce_rate_limit(client_key: str) -> None:
    """Mỗi client_key chỉ được gọi tối đa N lần trong 60 giây gần nhất."""
    now = time.time()
    window = _hits[client_key]

    # Bỏ các mốc thời gian cũ hơn 60 giây
    while window and window[0] < now - 60:
        window.popleft()

    if len(window) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Vượt giới hạn {settings.rate_limit_per_minute} request/phút.",
            headers={"Retry-After": "60"},
        )
    window.append(now)


# ─────────────────────────────────────────────
# 3. Cost guard (ngân sách theo ngày)
# ─────────────────────────────────────────────
_spent = {"day": time.strftime("%Y-%m-%d"), "usd": 0.0}

PRICE_PER_INPUT_TOKEN = 0.00015 / 1000   # tham khảo giá GPT-4o-mini
PRICE_PER_OUTPUT_TOKEN = 0.0006 / 1000


def enforce_budget_then_charge(input_tokens: int, output_tokens: int) -> float:
    """Chặn nếu đã hết ngân sách ngày; còn thì cộng dồn chi phí. Trả về tổng đã tiêu."""
    today = time.strftime("%Y-%m-%d")
    if today != _spent["day"]:           # sang ngày mới → reset
        _spent["day"], _spent["usd"] = today, 0.0

    if _spent["usd"] >= settings.daily_budget_usd:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail="Đã hết ngân sách trong ngày. Vui lòng thử lại vào ngày mai.",
        )

    cost = input_tokens * PRICE_PER_INPUT_TOKEN + output_tokens * PRICE_PER_OUTPUT_TOKEN
    _spent["usd"] += cost
    return round(_spent["usd"], 6)


def budget_status() -> dict:
    """Trạng thái ngân sách hiện tại (cho endpoint /metrics)."""
    return {
        "date": _spent["day"],
        "spent_usd": round(_spent["usd"], 6),
        "budget_usd": settings.daily_budget_usd,
    }
