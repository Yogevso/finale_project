"""Authentication-specific rate limiting service."""

import logging
import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)


def _get_redis_client():
    """Reuse the Redis client from the rate-limit middleware if available."""
    from app.middleware.rate_limit import _get_redis_client as _rl_redis
    return _rl_redis()


@dataclass
class AuthRateBucket:
    """Sliding-window attempts bucket with optional lock timestamp."""

    attempts: deque[float] = field(default_factory=deque)
    locked_until: float = 0.0


class AuthRateLimitService:
    """In-memory auth endpoint rate limiter keyed by IP + identifier."""

    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_WINDOW_SECONDS = 5 * 60
    LOGIN_LOCK_SECONDS = 5 * 60

    FORGOT_MAX_ATTEMPTS = 8
    FORGOT_WINDOW_SECONDS = 15 * 60
    FORGOT_LOCK_SECONDS = 5 * 60

    _buckets: dict[str, AuthRateBucket] = defaultdict(AuthRateBucket)
    _lock = Lock()
    _cleanup_counter = 0

    @classmethod
    def reset(cls) -> None:
        """Reset limiter state (useful for tests)."""
        with cls._lock:
            cls._buckets.clear()
            cls._cleanup_counter = 0

    @classmethod
    def _make_key(cls, scope: str, client_ip: str, identifier: str) -> str:
        normalized_ip = (client_ip or "unknown").strip().lower() or "unknown"
        normalized_identifier = (identifier or "_").strip().lower() or "_"
        return f"{scope}:{normalized_ip}:{normalized_identifier}"

    @classmethod
    def _prune_bucket(cls, bucket: AuthRateBucket, now_ts: float, window_seconds: int) -> None:
        while bucket.attempts and now_ts - bucket.attempts[0] > window_seconds:
            bucket.attempts.popleft()

    @classmethod
    def _clear_expired_lock(cls, bucket: AuthRateBucket, now_ts: float) -> None:
        if bucket.locked_until > 0 and bucket.locked_until <= now_ts:
            # Start a fresh window after lock expiry so lock duration is honored.
            bucket.locked_until = 0.0
            bucket.attempts.clear()

    @classmethod
    def _cleanup_stale_buckets(cls, now_ts: float, stale_after_seconds: int) -> None:
        cls._cleanup_counter += 1
        if cls._cleanup_counter < 200:
            return
        cls._cleanup_counter = 0

        stale_keys: list[str] = []
        for key, bucket in cls._buckets.items():
            cls._prune_bucket(bucket, now_ts, stale_after_seconds)
            if not bucket.attempts and bucket.locked_until <= now_ts:
                stale_keys.append(key)
        for key in stale_keys:
            del cls._buckets[key]

    @classmethod
    def _check_allowed(
        cls,
        key: str,
        *,
        max_attempts: int,
        window_seconds: int,
        lock_seconds: int,
    ) -> tuple[bool, int]:
        rclient = _get_redis_client()
        if rclient is not None:
            return cls._redis_check_allowed(rclient, key, max_attempts=max_attempts, window_seconds=window_seconds, lock_seconds=lock_seconds)
        return cls._memory_check_allowed(key, max_attempts=max_attempts, window_seconds=window_seconds, lock_seconds=lock_seconds)

    @classmethod
    def _redis_check_allowed(
        cls,
        rclient,
        key: str,
        *,
        max_attempts: int,
        window_seconds: int,
        lock_seconds: int,
    ) -> tuple[bool, int]:
        try:
            lock_key = f"authrl:lock:{key}"
            locked_until = rclient.get(lock_key)
            if locked_until:
                locked_until_ts = float(locked_until)
                now = time.time()
                if locked_until_ts > now:
                    return False, max(int(math.ceil(locked_until_ts - now)), 1)
                rclient.delete(lock_key)
            return True, 0
        except Exception:
            logger.warning("Redis auth rate-limit check failed, falling back to in-memory")
            return cls._memory_check_allowed(key, max_attempts=max_attempts, window_seconds=window_seconds, lock_seconds=lock_seconds)

    @classmethod
    def _memory_check_allowed(
        cls,
        key: str,
        *,
        max_attempts: int,
        window_seconds: int,
        lock_seconds: int,
    ) -> tuple[bool, int]:
        now_ts = time.time()
        with cls._lock:
            bucket = cls._buckets[key]
            cls._prune_bucket(bucket, now_ts, window_seconds)
            cls._clear_expired_lock(bucket, now_ts)

            if bucket.locked_until > now_ts:
                retry_after = int(math.ceil(bucket.locked_until - now_ts))
                cls._cleanup_stale_buckets(now_ts, max(window_seconds, lock_seconds) * 2)
                return False, max(retry_after, 1)

            cls._cleanup_stale_buckets(now_ts, max(window_seconds, lock_seconds) * 2)
            return True, 0

    @classmethod
    def _record_failure(
        cls,
        key: str,
        *,
        max_attempts: int,
        window_seconds: int,
        lock_seconds: int,
    ) -> int:
        rclient = _get_redis_client()
        if rclient is not None:
            return cls._redis_record_failure(rclient, key, max_attempts=max_attempts, window_seconds=window_seconds, lock_seconds=lock_seconds)
        return cls._memory_record_failure(key, max_attempts=max_attempts, window_seconds=window_seconds, lock_seconds=lock_seconds)

    @classmethod
    def _redis_record_failure(
        cls,
        rclient,
        key: str,
        *,
        max_attempts: int,
        window_seconds: int,
        lock_seconds: int,
    ) -> int:
        try:
            now = time.time()
            zkey = f"authrl:attempts:{key}"
            # Remove attempts outside the window
            rclient.zremrangebyscore(zkey, 0, now - window_seconds)
            # Add current attempt
            rclient.zadd(zkey, {str(now): now})
            rclient.expire(zkey, window_seconds + lock_seconds)
            count = rclient.zcard(zkey)
            if count >= max_attempts:
                locked_until = now + lock_seconds
                lock_key = f"authrl:lock:{key}"
                rclient.set(lock_key, str(locked_until), ex=lock_seconds)
                return max(int(math.ceil(lock_seconds)), 1)
            return 0
        except Exception:
            logger.warning("Redis auth rate-limit record failed, falling back to in-memory")
            return cls._memory_record_failure(key, max_attempts=max_attempts, window_seconds=window_seconds, lock_seconds=lock_seconds)

    @classmethod
    def _memory_record_failure(
        cls,
        key: str,
        *,
        max_attempts: int,
        window_seconds: int,
        lock_seconds: int,
    ) -> int:
        now_ts = time.time()
        with cls._lock:
            bucket = cls._buckets[key]
            cls._prune_bucket(bucket, now_ts, window_seconds)
            cls._clear_expired_lock(bucket, now_ts)
            bucket.attempts.append(now_ts)

            if len(bucket.attempts) >= max_attempts:
                bucket.locked_until = max(bucket.locked_until, now_ts + lock_seconds)
                retry_after = int(math.ceil(bucket.locked_until - now_ts))
                cls._cleanup_stale_buckets(now_ts, max(window_seconds, lock_seconds) * 2)
                return max(retry_after, 1)

            cls._cleanup_stale_buckets(now_ts, max(window_seconds, lock_seconds) * 2)
            return 0

    @classmethod
    def _record_success(cls, key: str) -> None:
        rclient = _get_redis_client()
        if rclient is not None:
            try:
                rclient.delete(f"authrl:attempts:{key}", f"authrl:lock:{key}")
                return
            except Exception:
                logger.warning("Redis auth rate-limit success record failed, falling back to in-memory")
        now_ts = time.time()
        with cls._lock:
            if key in cls._buckets:
                del cls._buckets[key]
            cls._cleanup_stale_buckets(now_ts, cls.LOGIN_WINDOW_SECONDS * 2)

    @classmethod
    def check_login_allowed(cls, client_ip: str, username: str) -> tuple[bool, int]:
        """Check whether login should be processed."""
        key = cls._make_key("login", client_ip, username)
        return cls._check_allowed(
            key,
            max_attempts=cls.LOGIN_MAX_ATTEMPTS,
            window_seconds=cls.LOGIN_WINDOW_SECONDS,
            lock_seconds=cls.LOGIN_LOCK_SECONDS,
        )

    @classmethod
    def record_login_failure(cls, client_ip: str, username: str) -> int:
        """Record failed login and return retry-after if lock just started."""
        key = cls._make_key("login", client_ip, username)
        return cls._record_failure(
            key,
            max_attempts=cls.LOGIN_MAX_ATTEMPTS,
            window_seconds=cls.LOGIN_WINDOW_SECONDS,
            lock_seconds=cls.LOGIN_LOCK_SECONDS,
        )

    @classmethod
    def record_login_success(cls, client_ip: str, username: str) -> None:
        """Reset login limiter for a successful authentication."""
        key = cls._make_key("login", client_ip, username)
        cls._record_success(key)

    @classmethod
    def check_forgot_password_allowed(cls, client_ip: str, identifier: str) -> tuple[bool, int]:
        """Check whether forgot-password request should be processed."""
        key = cls._make_key("forgot-password", client_ip, identifier)
        return cls._check_allowed(
            key,
            max_attempts=cls.FORGOT_MAX_ATTEMPTS,
            window_seconds=cls.FORGOT_WINDOW_SECONDS,
            lock_seconds=cls.FORGOT_LOCK_SECONDS,
        )

    @classmethod
    def record_forgot_password_request(cls, client_ip: str, identifier: str) -> int:
        """Record forgot-password request and return retry-after if locked."""
        key = cls._make_key("forgot-password", client_ip, identifier)
        return cls._record_failure(
            key,
            max_attempts=cls.FORGOT_MAX_ATTEMPTS,
            window_seconds=cls.FORGOT_WINDOW_SECONDS,
            lock_seconds=cls.FORGOT_LOCK_SECONDS,
        )
