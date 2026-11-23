"""
Rate limiting (tiêu chí 7).

Yêu cầu:
  • Mỗi API key tối đa RATE_LIMIT_PER_MINUTE request trong 60 giây (sliding window)
  • Vượt giới hạn → HTTP 429, nên kèm header Retry-After
  • State lưu trong Redis để mọi worker / instance dùng chung và vẫn còn sau khi
    restart agent (script chấm sẽ restart agent để kiểm tra)
"""


def check_rate_limit(key: str) -> None:
    # TODO: gợi ý dùng Redis sorted set: ZREMRANGEBYSCORE → ZCARD → ZADD → EXPIRE
    raise NotImplementedError("TODO: check_rate_limit")
