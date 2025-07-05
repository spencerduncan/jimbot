"""
Main Claude AI advisor implementation for JimBot.

Provides strategic consultation and meta-analysis with intelligent
caching and rate limiting.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain.chat_models import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage

from .cache import StrategyCache
from .prompts import META_ANALYSIS_PROMPT, STRATEGY_PROMPT, SYSTEM_PROMPT
from .rate_limiting import RateLimiter

logger = logging.getLogger(__name__)


@dataclass
class Strategy:
    """Represents a strategic decision from Claude."""

    action: str
    target: Optional[str]
    reasoning: str
    confidence: float
    alternative: Optional[str]
    cache_key: str
    timestamp: datetime


@dataclass
class GameState:
    """Represents the current game state for decision making."""

    ante: int
    money: int
    jokers: List[Dict[str, Any]]
    hand: List[Dict[str, Any]]
    shop: List[Dict[str, Any]]
    deck_size: int
    discards_remaining: int
    hands_remaining: int
    current_blind: Dict[str, Any]
    score_target: int

    def to_prompt_context(self) -> str:
        """Convert game state to optimized prompt context."""
        # TODO: Implement context optimization
        return json.dumps(self.__dict__, default=str)


class ClaudeAdvisor:
    """
    Main advisor class integrating Claude AI for strategic decisions.

    Features:
    - Rate limiting (100 requests/hour)
    - Multi-tier caching
    - Async queue pattern
    - Fallback strategies
    - Meta-analysis capabilities
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-opus-20240229",
        requests_per_hour: int = 100,
        cache_size: int = 10000,
        confidence_threshold: float = 0.5,
    ):
        """Initialize the Claude advisor with rate limiting and caching."""
        self.llm = ChatAnthropic(
            anthropic_api_key=api_key,
            model=model,
            temperature=0.2,  # Lower temperature for consistency
            max_tokens=500,
        )

        self.rate_limiter = RateLimiter(requests_per_hour)
        self.cache = StrategyCache(max_size=cache_size)
        self.confidence_threshold = confidence_threshold

        # Async queue for non-blocking requests
        self.request_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.response_futures: Dict[str, asyncio.Future] = {}

        # Metrics
        self.total_requests = 0
        self.cache_hits = 0
        self.llm_requests = 0
        self.fallback_uses = 0

        # Start queue processor
        self._queue_processor_task = None

    async def start(self):
        """Start the async queue processor."""
        self._queue_processor_task = asyncio.create_task(self._process_queue())
        logger.info("Claude advisor started")

    async def stop(self):
        """Stop the async queue processor."""
        if self._queue_processor_task:
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Claude advisor stopped")

    async def get_strategy(self, game_state: GameState) -> Strategy:
        """
        Get strategic advice for the current game state.

        Uses caching and rate limiting to optimize costs.
        Falls back to heuristics if rate limited.
        """
        self.total_requests += 1

        # Check cache first
        if cached_strategy := await self.cache.get(game_state):
            self.cache_hits += 1
            logger.debug(f"Cache hit for game state ante={game_state.ante}")
            return cached_strategy

        # Check if we should request LLM based on confidence
        if not self._should_consult_llm(game_state):
            self.fallback_uses += 1
            return self._get_fallback_strategy(game_state)

        # Check rate limit
        if not await self.rate_limiter.can_request():
            logger.warning("Rate limit reached, using fallback strategy")
            self.fallback_uses += 1
            return self._get_fallback_strategy(game_state)

        # Queue request for LLM
        return await self._queue_llm_request(game_state)

    async def analyze_failure(self, game_history: List[GameState]) -> Dict[str, Any]:
        """
        Perform meta-analysis on a failed run.

        Identifies patterns and provides improvement suggestions.
        """
        if not await self.rate_limiter.can_request():
            logger.warning("Rate limit reached for meta-analysis")
            return {"status": "rate_limited", "suggestions": []}

        # Create analysis prompt
        context = self._create_meta_analysis_context(game_history)

        try:
            response = await self._query_claude(
                META_ANALYSIS_PROMPT.format(context=context)
            )
            await self.rate_limiter.consume()
            return json.loads(response)
        except Exception as e:
            logger.error(f"Meta-analysis failed: {e}")
            return {"status": "error", "suggestions": []}

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        consultation_rate = (
            self.llm_requests / self.total_requests * 100
            if self.total_requests > 0
            else 0
        )
        cache_hit_rate = (
            self.cache_hits / self.total_requests * 100
            if self.total_requests > 0
            else 0
        )

        return {
            "total_requests": self.total_requests,
            "llm_requests": self.llm_requests,
            "cache_hits": self.cache_hits,
            "fallback_uses": self.fallback_uses,
            "consultation_rate": consultation_rate,
            "cache_hit_rate": cache_hit_rate,
            "rate_limit_remaining": self.rate_limiter.get_remaining(),
        }

    async def _process_queue(self):
        """Process queued LLM requests asynchronously."""
        while True:
            try:
                # Batch requests within 100ms window
                batch = []
                deadline = asyncio.get_event_loop().time() + 0.1

                while len(batch) < 5:  # Max batch size
                    timeout = max(0, deadline - asyncio.get_event_loop().time())
                    if timeout <= 0:
                        break

                    try:
                        request = await asyncio.wait_for(
                            self.request_queue.get(), timeout=timeout
                        )
                        batch.append(request)
                    except asyncio.TimeoutError:
                        break

                if batch:
                    await self._process_batch(batch)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processor error: {e}")
                await asyncio.sleep(1)

    async def _process_batch(self, batch: List[tuple]):
        """Process a batch of requests."""
        # TODO: Implement batch processing
        for game_state, future in batch:
            try:
                strategy = await self._get_llm_strategy(game_state)
                future.set_result(strategy)
            except Exception as e:
                future.set_exception(e)

    async def _queue_llm_request(self, game_state: GameState) -> Strategy:
        """Queue a request for LLM processing."""
        future = asyncio.Future()
        request_id = f"{game_state.ante}_{datetime.now().timestamp()}"

        await self.request_queue.put((game_state, future))

        try:
            return await asyncio.wait_for(future, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("LLM request timeout, using fallback")
            self.fallback_uses += 1
            return self._get_fallback_strategy(game_state)

    async def _get_llm_strategy(self, game_state: GameState) -> Strategy:
        """Get strategy from Claude LLM."""
        context = game_state.to_prompt_context()
        prompt = STRATEGY_PROMPT.format(context=context)

        try:
            response = await self._query_claude(prompt)
            await self.rate_limiter.consume()
            self.llm_requests += 1

            # Parse response
            data = json.loads(response)
            strategy = Strategy(
                action=data["action"],
                target=data.get("target"),
                reasoning=data["reasoning"],
                confidence=data["confidence"],
                alternative=data.get("alternative"),
                cache_key=data["cache_key"],
                timestamp=datetime.now(),
            )

            # Cache the strategy
            await self.cache.put(game_state, strategy)

            return strategy

        except Exception as e:
            logger.error(f"LLM strategy error: {e}")
            self.fallback_uses += 1
            return self._get_fallback_strategy(game_state)

    async def _query_claude(self, prompt: str) -> str:
        """Query Claude with the given prompt."""
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]

        response = await self.llm.agenerate([messages])
        return response.generations[0][0].text

    def _should_consult_llm(self, game_state: GameState) -> bool:
        """Determine if we should consult the LLM for this decision."""
        # High-value decision criteria
        if len(game_state.jokers) >= 3:  # Complex synergies
            return True
        if game_state.ante >= 7:  # Late game decisions
            return True
        if "Boss" in game_state.current_blind.get("type", ""):  # Boss blinds
            return True
        if any(item.get("type") == "Spectral" for item in game_state.shop):
            return True

        # Otherwise use confidence threshold
        confidence = self._estimate_confidence(game_state)
        return confidence < self.confidence_threshold

    def _estimate_confidence(self, game_state: GameState) -> float:
        """Estimate confidence in making a decision without LLM."""
        # Simple heuristic based on game state
        confidence = 0.8  # Base confidence

        # Adjust based on ante
        if game_state.ante <= 3:
            confidence += 0.1
        elif game_state.ante >= 7:
            confidence -= 0.2

        # Adjust based on complexity
        if len(game_state.jokers) > 2:
            confidence -= 0.1

        return max(0, min(1, confidence))

    def _get_fallback_strategy(self, game_state: GameState) -> Strategy:
        """Get a heuristic-based fallback strategy."""
        # Simple rule-based strategy
        action = "skip"
        target = None
        reasoning = "Fallback strategy - conserving resources"

        # Basic heuristics
        if game_state.money >= 6 and len(game_state.jokers) < 5:
            if game_state.shop:
                for item in game_state.shop:
                    if (
                        item.get("type") == "Joker"
                        and item.get("cost", 999) <= game_state.money
                    ):
                        action = "buy_joker"
                        target = item.get("name")
                        reasoning = "Fallback - buying affordable joker"
                        break

        return Strategy(
            action=action,
            target=target,
            reasoning=reasoning,
            confidence=0.3,
            alternative=None,
            cache_key=f"fallback_{game_state.ante}",
            timestamp=datetime.now(),
        )

    def _create_meta_analysis_context(self, game_history: List[GameState]) -> str:
        """Create context for meta-analysis."""
        # TODO: Implement sophisticated context creation
        return json.dumps([gs.__dict__ for gs in game_history[-10:]], default=str)
