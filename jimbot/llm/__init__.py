"""
JimBot LLM Integration Module

Provides Claude AI integration for strategic consultation and meta-analysis
with strict rate limiting and cost optimization.
"""

from .cache.strategy_cache import StrategyCache
from .claude_advisor import ClaudeAdvisor
from .rate_limiting.rate_limiter import RateLimiter

__all__ = ["ClaudeAdvisor", "RateLimiter", "StrategyCache"]

# Version info
__version__ = "0.1.0"
