"""Kết nối Redis (lazy) + kiểm tra sức khỏe cho /ready."""
import redis

from app.config import settings

_client = None


def get_redis():
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
    return _client


def redis_healthy() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:
        return False
