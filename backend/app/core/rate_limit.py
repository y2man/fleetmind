import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import HTTPException, Request
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger("fleetmind.rate_limit")
_hits: dict[tuple[str, str], deque] = defaultdict(deque)
_redis: Redis | None = None

_REDIS_SLIDING_WINDOW = """
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
local count = redis.call('ZCARD', KEYS[1])
if count >= limit then
  local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
  return {0, math.max(1, math.ceil((tonumber(oldest[2]) + window - now) / 1000))}
end
redis.call('ZADD', KEYS[1], now, ARGV[4])
redis.call('PEXPIRE', KEYS[1], window)
return {1, 0}
"""


def _redis_client() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            get_settings().redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis


def reset() -> None:
    _hits.clear()


def _check_redis_limit(name: str, client_host: str, limit: int, window_seconds: int) -> None:
    now_ms = int(time.time() * 1000)
    window_ms = window_seconds * 1000
    key = f"fleetmind:rate-limit:{name}:{client_host}"
    try:
        allowed, retry_after = _redis_client().eval(
            _REDIS_SLIDING_WINDOW,
            1,
            key,
            now_ms,
            window_ms,
            limit,
            uuid.uuid4().hex,
        )
    except RedisError as exc:
        logger.error("Redis rate limiter unavailable error_type=%s", type(exc).__name__)
        raise HTTPException(503, "Rate limiting service is unavailable") from exc
    if not int(allowed):
        raise HTTPException(
            429,
            "Too many requests. Please try again shortly.",
            headers={"Retry-After": str(int(retry_after))},
        )


def rate_limit(name: str, limit: int, window_seconds: int):
    def dep(request: Request) -> None:
        client_host = request.client.host if request.client else "unknown"
        if get_settings().rate_limit_backend == "redis":
            _check_redis_limit(name, client_host, limit, window_seconds)
            return
        key = (name, client_host)
        now = time.monotonic()
        q = _hits[key]
        while q and now - q[0] > window_seconds:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(429, "Too many requests. Please try again shortly.", headers={"Retry-After": str(window_seconds)})
        q.append(now)

    return dep
