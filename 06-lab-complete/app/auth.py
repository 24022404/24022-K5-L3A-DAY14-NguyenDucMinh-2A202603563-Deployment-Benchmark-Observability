"""
API Key authentication (tiêu chí 6).

Yêu cầu:
  • Client gửi header  X-API-Key: <key>
  • Key phải trùng biến môi trường AGENT_API_KEY
  • Thiếu hoặc sai key → HTTP 401 (không phải 403 hay 422)
"""


def verify_api_key() -> str:
    """Dependency cho FastAPI — dùng trong /ask: Depends(verify_api_key)."""
    # TODO: đọc header X-API-Key (gợi ý: fastapi.security.APIKeyHeader),
    #       so sánh với settings.agent_api_key; thiếu/sai → raise HTTPException(status_code=401)
    raise NotImplementedError("TODO: verify_api_key")
