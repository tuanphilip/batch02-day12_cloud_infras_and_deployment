"""
Stateless Cost Guard with Redis Support
"""
import time
import redis
import logging
from fastapi import HTTPException
from app.config import settings

logger = logging.getLogger(__name__)

# GPT-4o-mini rates
PRICE_PER_1K_INPUT_TOKENS = 0.00015
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006

class RedisCostGuard:
    def __init__(self, daily_budget_usd: float = 5.0, redis_url: str = ""):
        self.daily_budget_usd = daily_budget_usd
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
        self._memory_store = {}

    def _get_today_key(self, user_id: str) -> tuple[str, str]:
        today = time.strftime("%Y-%m-%d")
        return f"cost:{user_id}:{today}", today

    def check_budget(self, user_id: str) -> None:
        """
        Kiểm tra ngân sách đã dùng của user trong ngày.
        Raise HTTP 402 nếu vượt hạn mức.
        """
        key, today = self._get_today_key(user_id)
        current_cost = 0.0
        
        if self.use_redis:
            try:
                val = self._redis.get(key)
                if val:
                    current_cost = float(val)
            except Exception:
                current_cost = self._memory_store.get(key, 0.0)
        else:
            current_cost = self._memory_store.get(key, 0.0)
            
        if current_cost >= self.daily_budget_usd:
            logger.warning(f"User {user_id} exceeded daily budget limit of ${self.daily_budget_usd}")
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Daily budget exceeded",
                    "used_usd": round(current_cost, 6),
                    "budget_usd": self.daily_budget_usd,
                    "resets_at": "midnight UTC",
                }
            )

    def record_usage(self, user_id: str, input_tokens: int, output_tokens: int) -> float:
        """Ghi nhận chi phí sau cuộc gọi LLM."""
        cost = (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS + (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
        key, today = self._get_today_key(user_id)
        
        if self.use_redis:
            try:
                # Add to redis and set expire for 2 days to auto cleanup
                new_cost = self._redis.incrbyfloat(key, cost)
                self._redis.expire(key, 172800) # 2 days
                logger.info(f"Cost recorded (Redis): user={user_id} added=${cost:.6f} total=${new_cost:.6f}")
                return new_cost
            except Exception:
                pass
                
        # Fallback to in-memory
        old_cost = self._memory_store.get(key, 0.0)
        new_cost = old_cost + cost
        self._memory_store[key] = new_cost
        logger.info(f"Cost recorded (Memory): user={user_id} added=${cost:.6f} total=${new_cost:.6f}")
        return new_cost

    def get_cost(self, user_id: str) -> float:
        """Lấy chi phí hiện tại."""
        key, today = self._get_today_key(user_id)
        if self.use_redis:
            try:
                val = self._redis.get(key)
                return float(val) if val else 0.0
            except Exception:
                pass
        return self._memory_store.get(key, 0.0)

# Instantiate singleton
cost_guard = RedisCostGuard(
    daily_budget_usd=settings.daily_budget_usd,
    redis_url=settings.redis_url
)
