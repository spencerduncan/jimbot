"""
Multi-tier caching system for LLM strategies.

Provides exact match, similarity-based, and pattern-based caching
to minimize API calls and improve response times.
"""

import asyncio
import hashlib
import json
import logging
from collections import OrderedDict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class CacheTier(Enum):
    """Cache tier levels."""

    EXACT = "exact"
    SIMILARITY = "similarity"
    PATTERN = "pattern"


@dataclass
class CacheEntry:
    """Represents a cached strategy entry."""

    strategy: Any  # Strategy object
    game_state_hash: str
    game_state_vector: Optional[np.ndarray]
    pattern_key: Optional[str]
    timestamp: datetime
    hits: int = 0
    success_rate: float = 0.0

    def is_expired(self, ttl_hours: int = 24) -> bool:
        """Check if cache entry is expired."""
        return datetime.now() - self.timestamp > timedelta(hours=ttl_hours)

    def update_stats(self, success: bool):
        """Update entry statistics."""
        self.hits += 1
        # Exponential moving average for success rate
        alpha = 0.1
        self.success_rate = (
            alpha * (1.0 if success else 0.0) + (1 - alpha) * self.success_rate
        )


class StrategyCache:
    """
    Multi-tier strategy cache implementation.

    Features:
    - Exact match caching (Tier 1)
    - Similarity-based caching (Tier 2)
    - Pattern-based caching (Tier 3)
    - LRU eviction with performance weighting
    - Async-safe operations
    """

    def __init__(
        self,
        max_size: int = 10000,
        similarity_threshold: float = 0.85,
        ttl_hours: int = 24,
    ):
        """Initialize the strategy cache."""
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.ttl_hours = ttl_hours

        # Tier 1: Exact match cache
        self.exact_cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Tier 2: Similarity cache (game state vectors)
        self.similarity_cache: List[CacheEntry] = []

        # Tier 3: Pattern cache
        self.pattern_cache: Dict[str, CacheEntry] = {}

        # Lock for thread safety
        self.lock = asyncio.Lock()

        # Metrics
        self.tier_hits = {tier: 0 for tier in CacheTier}
        self.total_lookups = 0

    async def get(self, game_state: Any) -> Optional[Any]:
        """
        Get cached strategy for a game state.

        Checks all three cache tiers in order.
        """
        async with self.lock:
            self.total_lookups += 1

            # Tier 1: Exact match
            state_hash = self._hash_game_state(game_state)
            if entry := self.exact_cache.get(state_hash):
                if not entry.is_expired(self.ttl_hours):
                    self.tier_hits[CacheTier.EXACT] += 1
                    entry.hits += 1
                    # Move to end (LRU)
                    self.exact_cache.move_to_end(state_hash)
                    logger.debug(f"Cache hit (exact): {state_hash[:8]}")
                    return entry.strategy
                else:
                    del self.exact_cache[state_hash]

            # Tier 2: Similarity match
            state_vector = self._vectorize_game_state(game_state)
            if similar_entry := self._find_similar(state_vector):
                self.tier_hits[CacheTier.SIMILARITY] += 1
                similar_entry.hits += 1
                logger.debug(
                    f"Cache hit (similarity): confidence={similar_entry.strategy.confidence}"
                )
                return similar_entry.strategy

            # Tier 3: Pattern match
            pattern_key = self._extract_pattern(game_state)
            if pattern_entry := self.pattern_cache.get(pattern_key):
                if not pattern_entry.is_expired(
                    self.ttl_hours * 2
                ):  # Patterns last longer
                    self.tier_hits[CacheTier.PATTERN] += 1
                    pattern_entry.hits += 1
                    logger.debug(f"Cache hit (pattern): {pattern_key}")
                    return pattern_entry.strategy
                else:
                    del self.pattern_cache[pattern_key]

            return None

    async def put(self, game_state: Any, strategy: Any):
        """
        Cache a strategy for a game state.

        Updates all applicable cache tiers.
        """
        async with self.lock:
            state_hash = self._hash_game_state(game_state)
            state_vector = self._vectorize_game_state(game_state)
            pattern_key = self._extract_pattern(game_state)

            entry = CacheEntry(
                strategy=strategy,
                game_state_hash=state_hash,
                game_state_vector=state_vector,
                pattern_key=pattern_key,
                timestamp=datetime.now(),
            )

            # Update Tier 1: Exact cache
            self.exact_cache[state_hash] = entry
            self.exact_cache.move_to_end(state_hash)

            # Evict if needed (LRU with performance weighting)
            if len(self.exact_cache) > self.max_size:
                self._evict_lru()

            # Update Tier 2: Similarity cache
            self.similarity_cache.append(entry)
            if len(self.similarity_cache) > self.max_size // 2:
                # Keep only high-performing entries
                self.similarity_cache.sort(
                    key=lambda e: e.success_rate * e.hits, reverse=True
                )
                self.similarity_cache = self.similarity_cache[: self.max_size // 2]

            # Update Tier 3: Pattern cache
            if pattern_key:
                # Only cache successful patterns
                if strategy.confidence > 0.7:
                    self.pattern_cache[pattern_key] = entry

            logger.debug(f"Cached strategy: {state_hash[:8]}")

    async def update_performance(self, game_state: Any, success: bool):
        """Update performance metrics for a cached strategy."""
        async with self.lock:
            state_hash = self._hash_game_state(game_state)
            if entry := self.exact_cache.get(state_hash):
                entry.update_stats(success)

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        hit_rate = sum(self.tier_hits.values()) / max(1, self.total_lookups)

        return {
            "total_lookups": self.total_lookups,
            "hit_rate": hit_rate * 100,
            "tier_hits": dict(self.tier_hits),
            "cache_sizes": {
                "exact": len(self.exact_cache),
                "similarity": len(self.similarity_cache),
                "pattern": len(self.pattern_cache),
            },
            "memory_usage_mb": self._estimate_memory_usage() / 1024 / 1024,
        }

    async def clear_expired(self):
        """Remove expired entries from all cache tiers."""
        async with self.lock:
            # Clear exact cache
            expired_keys = [
                k for k, v in self.exact_cache.items() if v.is_expired(self.ttl_hours)
            ]
            for key in expired_keys:
                del self.exact_cache[key]

            # Clear similarity cache
            self.similarity_cache = [
                e for e in self.similarity_cache if not e.is_expired(self.ttl_hours)
            ]

            # Clear pattern cache (longer TTL)
            expired_patterns = [
                k
                for k, v in self.pattern_cache.items()
                if v.is_expired(self.ttl_hours * 2)
            ]
            for key in expired_patterns:
                del self.pattern_cache[key]

            logger.info(f"Cleared {len(expired_keys)} expired entries")

    def _hash_game_state(self, game_state: Any) -> str:
        """Create a hash of the game state for exact matching."""
        # Convert game state to a canonical string representation
        state_dict = (
            asdict(game_state) if hasattr(game_state, "__dict__") else game_state
        )

        # Sort keys for consistency
        canonical = json.dumps(state_dict, sort_keys=True, default=str)

        # Create hash
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _vectorize_game_state(self, game_state: Any) -> np.ndarray:
        """Convert game state to a vector for similarity matching."""
        features = []

        # Basic features
        features.extend(
            [
                game_state.ante / 10.0,  # Normalize
                game_state.money / 100.0,
                len(game_state.jokers) / 5.0,
                game_state.hands_remaining / 4.0,
                game_state.discards_remaining / 4.0,
                game_state.deck_size / 52.0,
                np.log10(max(1, game_state.score_target)),
            ]
        )

        # Joker features (top 5 by some metric)
        joker_features = [0] * 10  # 2 features per joker
        for i, joker in enumerate(game_state.jokers[:5]):
            joker_features[i * 2] = hash(joker.get("name", "")) % 100 / 100.0
            joker_features[i * 2 + 1] = joker.get("level", 1) / 5.0
        features.extend(joker_features)

        # Shop features
        shop_types = {"Joker": 0, "Tarot": 0, "Planet": 0, "Spectral": 0}
        for item in game_state.shop:
            item_type = item.get("type", "")
            if item_type in shop_types:
                shop_types[item_type] += 1
        features.extend([v / 5.0 for v in shop_types.values()])

        return np.array(features, dtype=np.float32)

    def _find_similar(self, state_vector: np.ndarray) -> Optional[CacheEntry]:
        """Find similar game state in cache using cosine similarity."""
        if not self.similarity_cache or state_vector is None:
            return None

        best_similarity = 0
        best_entry = None

        for entry in self.similarity_cache:
            if entry.game_state_vector is None:
                continue

            # Cosine similarity
            similarity = np.dot(state_vector, entry.game_state_vector) / (
                np.linalg.norm(state_vector) * np.linalg.norm(entry.game_state_vector)
            )

            if similarity > self.similarity_threshold and similarity > best_similarity:
                best_similarity = similarity
                best_entry = entry

        return best_entry

    def _extract_pattern(self, game_state: Any) -> Optional[str]:
        """Extract abstract pattern from game state."""
        patterns = []

        # Ante-based pattern
        if game_state.ante <= 3:
            patterns.append("early_game")
        elif game_state.ante <= 6:
            patterns.append("mid_game")
        else:
            patterns.append("late_game")

        # Joker count pattern
        joker_count = len(game_state.jokers)
        if joker_count == 0:
            patterns.append("no_jokers")
        elif joker_count <= 2:
            patterns.append("few_jokers")
        else:
            patterns.append("many_jokers")

        # Money pattern
        if game_state.money < 10:
            patterns.append("low_money")
        elif game_state.money > 50:
            patterns.append("high_money")

        # Blind type pattern
        blind_type = game_state.current_blind.get("type", "").lower()
        if "boss" in blind_type:
            patterns.append("boss_blind")
        elif "small" in blind_type:
            patterns.append("small_blind")
        elif "big" in blind_type:
            patterns.append("big_blind")

        return "_".join(patterns) if patterns else None

    def _evict_lru(self):
        """Evict least recently used entry with performance weighting."""
        if not self.exact_cache:
            return

        # Find entry with lowest score (LRU + performance)
        min_score = float("inf")
        min_key = None

        for key, entry in self.exact_cache.items():
            # Score combines recency and performance
            recency_score = (datetime.now() - entry.timestamp).total_seconds()
            performance_penalty = (
                1 - entry.success_rate
            ) * 3600  # 1 hour penalty per failure
            score = (
                recency_score + performance_penalty - (entry.hits * 600)
            )  # 10 min bonus per hit

            if score < min_score:
                min_score = score
                min_key = key

        if min_key:
            del self.exact_cache[min_key]

    def _estimate_memory_usage(self) -> int:
        """Estimate cache memory usage in bytes."""
        # Rough estimation
        exact_size = len(self.exact_cache) * 1024  # ~1KB per entry
        similarity_size = len(self.similarity_cache) * 1536  # ~1.5KB with vectors
        pattern_size = len(self.pattern_cache) * 512  # ~0.5KB per pattern

        return exact_size + similarity_size + pattern_size
