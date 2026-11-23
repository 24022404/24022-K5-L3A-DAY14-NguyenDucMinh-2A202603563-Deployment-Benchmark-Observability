"""
Kết nối Redis dùng chung cho rate limiter và cost guard.

Yêu cầu:
  • Đọc REDIS_URL từ config
  • App vẫn phải KHỞI ĐỘNG ĐƯỢC khi Redis chưa sẵn sàng (đừng ping Redis lúc import)
  • redis_healthy() dùng cho GET /ready: Redis không kết nối được → False
"""

r = None  # TODO: tạo client, vd redis.from_url(settings.redis_url, decode_responses=True)


def redis_healthy() -> bool:
    # TODO: ping Redis; lỗi kết nối → False
    return False
