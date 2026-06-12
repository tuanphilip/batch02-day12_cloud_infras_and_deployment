"""
Stateless Rate Limiter with Redis Support
"""
import time
import redis
from collections import defaultdict, deque
from fastapi import HTTPException
from app.config import settings

class RedisRateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60, redis_url: str = ""):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis_url = redis_url
        self._redis = None
        self.use_redis = False
        
        if redis_url:
            try:
                self._redis = redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
                self.use_redis = True
            except Exception:
                self.use_redis = False
                
        # In-memory fallback
        self._windows = defaultdict(deque)

    def check(self, user_id: str) -> None:
        """
        Kiểm tra rate limit của user.
        Bảo vệ ứng dụng khỏi request spam.
        """
        if self.use_redis:
            now = time.time()
            key = f"rate_limit:{user_id}"
            try:
                # Remove expired records
                clear_before = now - self.window_seconds
                self._redis.zremrangebyscore(key, 0, clear_before)
                
                # Count current window requests
                count = self._redis.zcard(key)
                
                if count >= self.max_requests:
                    # Get oldest to calculate Retry-After
                    oldest_list = self._redis.zrange(key, 0, 0, withscores=True)
                    retry_after = 60
                    if oldest_list:
                        oldest_time = oldest_list[0][1]
                        retry_after = int(oldest_time + self.window_seconds - now) + 1
                    
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded: {self.max_requests} req/min. Retry after {retry_after}s.",
                        headers={"Retry-After": str(retry_after)},
                    )
                
                # Record this request
                self._redis.zadd(key, {str(now): now})
                self._redis.expire(key, self.window_seconds * 2)
            except HTTPException:
                raise
            except Exception:
                # Fail open to memory if Redis connection drops at runtime
                self._check_in_memory(user_id)
        else:
            self._check_in_memory(user_id)

    def _check_in_memory(self, user_id: str) -> None:
        now = time.time()
        window = self._windows[user_id]
        while window and window[0] < now - self.window_seconds:
            window.popleft()
        if len(window) >= self.max_requests:
            oldest = window[0]
            retry_after = int(oldest + self.window_seconds - now) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {self.max_requests} req/min. Retry after {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )
        window.append(now)

# Instantiate singleton
rate_limiter = RedisRateLimiter(
    max_requests=settings.rate_limit_per_minute,
    window_seconds=60,
    redis_url=settings.redis_url
)
