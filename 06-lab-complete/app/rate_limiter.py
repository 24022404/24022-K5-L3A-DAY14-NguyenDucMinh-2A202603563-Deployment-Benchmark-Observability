"""Rate limiting (tiêu chí 7): sliding window trong Redis sorted set."""
import hashlib
import time
import uuid

from fastapi import HTTPException

from app.config import settings
from app.redis_client import get_redis

WINDOW_SECONDS = 60


def check_rate_limit(key: str) -> None:
    r = get_redis()
    rkey = "rl:" + hashlib.sha256(key.encode()).hexdigest()[:32]
    now = time.time()
    try:
        pipe = r.pipeline()
        pipe.zremrangebyscore(rkey, 0, now - WINDOW_SECONDS)
        pipe.zcard(rkey)
        _, count = pipe.execute()
        if count >= settings.rate_limit_per_minute:
            oldest = r.zrange(rkey, 0, 0, withscores=True)
            retry = WINDOW_SECONDS
            if oldest:
                retry = max(1, int(oldest[0][1] + WINDOW_SECONDS - now) + 1)
            raise HTTPException(
                status_code=429,
                detail={"error": "Rate limit exceeded", "limit": settings.rate_limit_per_minute},
                headers={"Retry-After": str(retry)},
            )
        pipe = r.pipeline()
        pipe.zadd(rkey, {f"{now}:{uuid.uuid4().hex[:8]}": now})
        pipe.expire(rkey, WINDOW_SECONDS + 5)
        pipe.execute()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Rate limiter unavailable (Redis)")
