"""
Rate limiting implementation for Claude API calls.

Implements token bucket algorithm with hourly limits and
monitoring capabilities.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after:.1f} seconds.")


@dataclass
class TokenBucket:
    """
    Token bucket implementation for rate limiting.

    Tokens are added at a fixed rate up to a maximum capacity.
    Each request consumes one token.
    """

    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from the bucket.

        Returns True if successful, False if not enough tokens.
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def can_consume(self, tokens: int = 1) -> bool:
        """Check if tokens can be consumed without actually consuming them."""
        self._refill()
        return self.tokens >= tokens

    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate seconds until the requested tokens will be available."""
        self._refill()

        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def get_remaining(self) -> int:
        """Get the number of tokens currently available."""
        self._refill()
        return int(self.tokens)


class RateLimiter:
    """
    Rate limiter for Claude API calls with monitoring and statistics.

    Features:
    - Token bucket algorithm
    - Hourly rate limits
    - Request history tracking
    - Burst protection
    - Monitoring and alerts
    """

    def __init__(
        self,
        requests_per_hour: int = 100,
        burst_size: Optional[int] = None,
        enable_monitoring: bool = True,
    ):
        """
        Initialize the rate limiter.

        Args:
            requests_per_hour: Maximum requests allowed per hour
            burst_size: Maximum burst size (defaults to 10% of hourly limit)
            enable_monitoring: Enable detailed monitoring and statistics
        """
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size or max(10, requests_per_hour // 10)

        # Token bucket for rate limiting
        refill_rate = requests_per_hour / 3600.0  # tokens per second
        self.bucket = TokenBucket(capacity=self.burst_size, refill_rate=refill_rate)

        # Monitoring
        self.enable_monitoring = enable_monitoring
        self.request_history: deque = deque(maxlen=requests_per_hour)
        self.denied_requests = 0
        self.total_requests = 0

        # Sliding window for accurate hourly counting
        self.window_start = time.time()

        # Lock for thread safety
        self.lock = asyncio.Lock()

        logger.info(
            f"Rate limiter initialized: {requests_per_hour}/hour, "
            f"burst size: {self.burst_size}"
        )

    async def acquire(self, timeout: Optional[float] = None) -> None:
        """
        Acquire permission to make a request.

        Waits if necessary until a token is available.

        Args:
            timeout: Maximum time to wait in seconds

        Raises:
            RateLimitExceeded: If timeout is reached
        """
        start_time = time.time()

        async with self.lock:
            while True:
                if self.bucket.consume():
                    self._record_request()
                    return

                wait_time = self.bucket.time_until_available()

                if timeout and (time.time() - start_time + wait_time) > timeout:
                    self.denied_requests += 1
                    raise RateLimitExceeded(wait_time)

                # Wait for token to be available
                await asyncio.sleep(min(wait_time, 0.1))

    async def can_request(self) -> bool:
        """
        Check if a request can be made without waiting.

        Does not consume a token.
        """
        async with self.lock:
            return self.bucket.can_consume()

    async def consume(self) -> None:
        """
        Consume a token without waiting.

        Raises:
            RateLimitExceeded: If no tokens available
        """
        async with self.lock:
            if not self.bucket.consume():
                self.denied_requests += 1
                wait_time = self.bucket.time_until_available()
                raise RateLimitExceeded(wait_time)

            self._record_request()

    def get_remaining(self) -> int:
        """Get the number of requests remaining in the current period."""
        return self.bucket.get_remaining()

    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed rate limiting statistics."""
        now = time.time()

        # Count requests in the last hour
        hour_ago = now - 3600
        recent_requests = sum(
            1 for timestamp in self.request_history if timestamp > hour_ago
        )

        # Calculate rates
        elapsed_hours = (now - self.window_start) / 3600
        avg_rate = self.total_requests / max(1, elapsed_hours)

        return {
            "current_tokens": self.bucket.get_remaining(),
            "burst_capacity": self.burst_size,
            "requests_last_hour": recent_requests,
            "total_requests": self.total_requests,
            "denied_requests": self.denied_requests,
            "denial_rate": self.denied_requests / max(1, self.total_requests),
            "average_rate_per_hour": avg_rate,
            "time_until_token": self.bucket.time_until_available(),
            "uptime_hours": elapsed_hours,
        }

    async def wait_until_available(self) -> float:
        """
        Wait until a request can be made.

        Returns the time waited in seconds.
        """
        start_time = time.time()
        await self.acquire()
        return time.time() - start_time

    def reset(self):
        """Reset the rate limiter state."""
        self.bucket.tokens = float(self.bucket.capacity)
        self.bucket.last_refill = time.time()
        self.request_history.clear()
        self.denied_requests = 0
        self.total_requests = 0
        self.window_start = time.time()
        logger.info("Rate limiter reset")

    def _record_request(self):
        """Record a successful request for monitoring."""
        self.total_requests += 1

        if self.enable_monitoring:
            self.request_history.append(time.time())

            # Alert if approaching limit
            if self.bucket.get_remaining() < 10:
                logger.warning(
                    f"Rate limit warning: Only {self.bucket.get_remaining()} "
                    f"requests remaining"
                )

            # Alert if high denial rate
            if self.total_requests > 100:
                denial_rate = self.denied_requests / self.total_requests
                if denial_rate > 0.1:  # More than 10% denials
                    logger.warning(
                        f"High denial rate: {denial_rate:.1%} of requests denied"
                    )


class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive rate limiter that adjusts limits based on usage patterns.

    Features:
    - Dynamic burst size adjustment
    - Usage pattern learning
    - Predictive throttling
    """

    def __init__(
        self, requests_per_hour: int = 100, adaptation_period: int = 3600, **kwargs
    ):
        super().__init__(requests_per_hour, **kwargs)
        self.adaptation_period = adaptation_period
        self.usage_patterns: deque = deque(maxlen=24)  # 24 hours of history
        self.last_adaptation = time.time()

    async def consume(self) -> None:
        """Consume a token with adaptive adjustment."""
        await super().consume()

        # Check if we should adapt
        if time.time() - self.last_adaptation > self.adaptation_period:
            self._adapt_limits()

    def _adapt_limits(self):
        """Adapt rate limits based on usage patterns."""
        if len(self.usage_patterns) < 2:
            return

        # Calculate usage statistics
        avg_usage = sum(self.usage_patterns) / len(self.usage_patterns)
        peak_usage = max(self.usage_patterns)

        # Adjust burst size based on patterns
        if peak_usage > self.burst_size * 0.9:
            # Increase burst size if we're hitting limits
            new_burst = min(self.requests_per_hour // 2, int(self.burst_size * 1.2))
            logger.info(f"Increasing burst size: {self.burst_size} → {new_burst}")
            self.burst_size = new_burst
            self.bucket.capacity = new_burst

        elif avg_usage < self.burst_size * 0.3:
            # Decrease burst size if underutilized
            new_burst = max(10, int(self.burst_size * 0.8))
            logger.info(f"Decreasing burst size: {self.burst_size} → {new_burst}")
            self.burst_size = new_burst
            self.bucket.capacity = new_burst

        self.last_adaptation = time.time()

    def predict_usage(self, hours_ahead: int = 1) -> float:
        """Predict future usage based on patterns."""
        if not self.usage_patterns:
            return self.requests_per_hour * hours_ahead

        # Simple moving average prediction
        recent_usage = list(self.usage_patterns)[-6:]  # Last 6 hours
        if recent_usage:
            avg_recent = sum(recent_usage) / len(recent_usage)
            return avg_recent * hours_ahead

        return sum(self.usage_patterns) / len(self.usage_patterns) * hours_ahead
