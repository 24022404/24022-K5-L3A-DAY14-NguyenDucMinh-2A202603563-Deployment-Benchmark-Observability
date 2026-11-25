"""Cost guard (tiêu chí 8): cộng dồn chi phí theo ngày trong Redis, vượt budget -> 402."""
from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import settings
from app.redis_client import get_redis

# Giá USD / 1K tokens (tham khảo gpt-4o-mini)
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006


def _key() -> str:
    return "cost:" + datetime.now(timezone.utc).strftime("%Y-%m-%d")


def check_budget() -> None:
    """Gọi TRƯỚC khi gọi LLM. Hết budget -> 402."""
    try:
        spent = float(get_redis().get(_key()) or 0.0)
    except Exception:
        raise HTTPException(status_code=503, detail="Cost guard unavailable (Redis)")
    if settings.daily_budget_usd <= 0 or spent >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily budget exceeded")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    """Gọi SAU khi gọi LLM. Cộng chi phí vào tổng ngày, trả về chi phí của request."""
    cost = (input_tokens / 1000) * PRICE_INPUT_PER_1K + (output_tokens / 1000) * PRICE_OUTPUT_PER_1K
    try:
        r = get_redis()
        r.incrbyfloat(_key(), cost)
        r.expire(_key(), 2 * 24 * 3600)
    except Exception:
        pass
    return cost
