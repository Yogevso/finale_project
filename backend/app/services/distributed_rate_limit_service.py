"""Generic distributed rate limiting with Redis fallback."""

from __future__ import annotations

import logging
import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)

_CHECK_AND_RECORD_LUA = """
local zkey = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_req = tonumber(ARGV[3])

redis.call('ZREMRANGEBYSCORE', zkey, '-inf', now - window)

local cnt = redis.call('ZCARD', zkey)
if cnt >= max_req then
    local oldest = redis.call('ZRANGE', zkey, 0, 0, 'WITHSCORES')
    local retry_after = 1
    if oldest[2] then
        retry_after = math.ceil((tonumber(oldest[2]) + window) - now)
        if retry_after < 1 then
            retry_after = 1
        end
    end
    redis.call('EXPIRE', zkey, math.ceil(window))
    return {0, retry_after}
end

redis.call('ZADD', zkey, now, tostring(now) .. ':' .. tostring(math.random(1, 2147483647)))
redis.call('EXPIRE', zkey, math.ceil(window))
return {1, 0}
"""


def _get_redis_client():
    from app.middleware.rate_limit import _get_redis_client as _rl_redis

    return _rl_redis()


@dataclass
class SlidingWindowBucket:
    requests: deque[float] = field(default_factory=deque)


class DistributedRateLimitService:
    """Redis-backed sliding-window limiter with in-memory fallback."""

    _buckets: dict[str, SlidingWindowBucket] = defaultdict(SlidingWindowBucket)
    _lock = Lock()

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._buckets.clear()

    @classmethod
    def check_and_record(
        cls,
        *,
        scope: str,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        normalized_key = f"{scope}:{(key or '_').strip().lower() or '_'}"
        redis_client = _get_redis_client()
        if redis_client is not None:
            return cls._redis_check_and_record(
                redis_client,
                normalized_key,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )
        return cls._memory_check_and_record(
            normalized_key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

    @classmethod
    def _redis_check_and_record(
        cls,
        redis_client,
        key: str,
        *,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        try:
            result = redis_client.eval(
                _CHECK_AND_RECORD_LUA,
                1,
                f"ratelimit:{key}",
                time.time(),
                window_seconds,
                max_requests,
            )
            allowed = int(result[0]) == 1
            retry_after = max(int(result[1]), 0)
            return allowed, retry_after
        except Exception:  # policy: DEGRADED — Redis distributed limiter may fall back to in-memory safely
            logger.warning("Redis distributed rate-limit failed, falling back to in-memory")
            return cls._memory_check_and_record(
                key,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )

    @classmethod
    def _memory_check_and_record(
        cls,
        key: str,
        *,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        now = time.time()
        with cls._lock:
            bucket = cls._buckets[key]
            while bucket.requests and now - bucket.requests[0] >= window_seconds:
                bucket.requests.popleft()

            if len(bucket.requests) >= max_requests:
                retry_after = int(
                    math.ceil((bucket.requests[0] + window_seconds) - now)
                )
                return False, max(retry_after, 1)

            bucket.requests.append(now)
            return True, 0
