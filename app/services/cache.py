import redis
import json
from app.core.config import settings

try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False
    print("WARNING: Redis unavailable — caching disabled")

def get_cached_report(user_id: str, month: str):
    if not REDIS_AVAILABLE:
        return None
    try:
        key = f"summary:{user_id}:{normalize_month(month)}"
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except:
        return None

def normalize_month(month: str) -> str:
    parts = month.split("-")
    return f"{parts[0]}-{parts[1].zfill(2)}"

def set_cached_report(user_id: str, month: str, data: dict):
    if not REDIS_AVAILABLE:
        return
    try:
        key = f"summary:{user_id}:{normalize_month(month)}"
        redis_client.setex(key, 86400, json.dumps(data))
    except:
        pass

def invalidate_report_cache(user_id: str, month: str):
    if not REDIS_AVAILABLE:
        return
    try:
        key = f"summary:{user_id}:{normalize_month(month)}"
        redis_client.delete(key)
    except:
        pass

def get_redis_client():
    if not REDIS_AVAILABLE:
        return None
    return redis_client