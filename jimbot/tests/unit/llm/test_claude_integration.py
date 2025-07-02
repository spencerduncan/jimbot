"""
Unit tests for Claude LLM integration.

Tests strategy consultation, rate limiting, and caching.
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

import pytest

from jimbot.llm.claude_advisor import ClaudeStrategyAdvisor, RateLimiter
from jimbot.llm.prompt_builder import PromptBuilder
from jimbot.llm.response_parser import ResponseParser


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter with 10 requests/hour."""
        return RateLimiter(hourly_limit=10)
    
    def test_allows_requests_under_limit(self, rate_limiter):
        """Test requests are allowed under the limit."""
        for _ in range(5):
            assert rate_limiter.can_request()
            rate_limiter.record_request()
        
        assert rate_limiter.requests_used == 5
        assert rate_limiter.requests_remaining == 5
    
    def test_blocks_requests_over_limit(self, rate_limiter):
        """Test requests are blocked when limit exceeded."""
        # Use up all requests
        for _ in range(10):
            rate_limiter.record_request()
        
        assert not rate_limiter.can_request()
        assert rate_limiter.requests_remaining == 0
    
    def test_resets_after_time_window(self, rate_limiter):
        """Test rate limit resets after time window."""
        # Use some requests
        for _ in range(5):
            rate_limiter.record_request()
        
        # Mock time passing
        with patch('time.time') as mock_time:
            mock_time.return_value = time.time() + 3700  # Just over 1 hour
            
            assert rate_limiter.can_request()
            assert rate_limiter.requests_used == 0
    
    def test_calculates_wait_time(self, rate_limiter):
        """Test calculation of wait time until next request."""
        # Use all requests
        for _ in range(10):
            rate_limiter.record_request()
        
        wait_time = rate_limiter.time_until_next_request()
        
        assert 3500 < wait_time < 3600  # Close to 1 hour


class TestClaudeStrategyAdvisor:
    """Test Claude strategy advisor."""
    
    @pytest.fixture
    def mock_claude_client(self):
        """Create a mock Claude client."""
        client = AsyncMock()
        client.chat = AsyncMock(return_value={
            "choices": [{
                "message": {
                    "content": "Focus on flush builds with your current joker setup."
                }
            }]
        })
        return client
    
    @pytest.fixture
    def advisor(self, mock_claude_client):
        """Create an advisor with mocked client."""
        return ClaudeStrategyAdvisor(
            client=mock_claude_client,
            hourly_limit=100
        )
    
    @pytest.mark.asyncio
    async def test_gets_strategic_advice(self, advisor, sample_game_state):
        """Test getting strategic advice for game state."""
        advice = await advisor.get_strategic_advice(
            sample_game_state,
            knowledge_graph_context={"top_synergies": ["flush_focus"]}
        )
        
        assert "flush" in advice.lower()
        advisor.client.chat.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_respects_rate_limits(self, advisor, sample_game_state):
        """Test rate limiting is enforced."""
        advisor.rate_limiter.hourly_limit = 2
        
        # Make requests up to limit
        await advisor.get_strategic_advice(sample_game_state)
        await advisor.get_strategic_advice(sample_game_state)
        
        # Next request should use cache
        with patch.object(advisor, 'get_cached_strategy') as mock_cache:
            mock_cache.return_value = "Cached strategy"
            advice = await advisor.get_strategic_advice(sample_game_state)
            
            assert advice == "Cached strategy"
            mock_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_caches_similar_requests(self, advisor, sample_game_state):
        """Test caching for similar game states."""
        # First request
        advice1 = await advisor.get_strategic_advice(sample_game_state)
        
        # Similar state should use cache
        similar_state = sample_game_state.copy()
        similar_state["money"] += 1  # Minor difference
        
        with patch.object(advisor.client, 'chat') as mock_chat:
            advice2 = await advisor.get_strategic_advice(similar_state)
            
            # Should not make new API call
            mock_chat.assert_not_called()
            assert advice2 == advice1
    
    @pytest.mark.asyncio
    async def test_analyzes_failed_runs(self, advisor):
        """Test analysis of failed game runs."""
        game_history = [
            {"ante": 1, "action": "buy_joker", "result": "success"},
            {"ante": 3, "action": "skip_shop", "result": "success"},
            {"ante": 5, "action": "play_weak_hand", "result": "failure"}
        ]
        
        advisor.client.chat.return_value = {
            "choices": [{
                "message": {
                    "content": "Failed due to insufficient scaling. Should have bought damage jokers in ante 3 shop."
                }
            }]
        }
        
        analysis = await advisor.analyze_failure(game_history)
        
        assert "scaling" in analysis.lower()
        assert "ante 3" in analysis.lower()
    
    @pytest.mark.asyncio 
    async def test_handles_api_errors(self, advisor, sample_game_state):
        """Test graceful handling of API errors."""
        advisor.client.chat.side_effect = Exception("API Error")
        
        advice = await advisor.get_strategic_advice(sample_game_state)
        
        assert advice is not None  # Should return fallback
        assert "error" in advice.lower() or "default" in advice.lower()
    
    @pytest.mark.asyncio
    async def test_tracks_token_usage(self, advisor, sample_game_state):
        """Test tracking of token usage for cost management."""
        advisor.client.chat.return_value = {
            "choices": [{"message": {"content": "Strategy advice"}}],
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 50,
                "total_tokens": 200
            }
        }
        
        await advisor.get_strategic_advice(sample_game_state)
        
        assert advisor.total_tokens_used == 200
        assert advisor.estimated_cost > 0


class TestPromptBuilder:
    """Test prompt construction for Claude."""
    
    @pytest.fixture
    def builder(self):
        """Create a prompt builder."""
        return PromptBuilder()
    
    def test_builds_strategy_prompt(self, builder, sample_game_state):
        """Test building a strategy consultation prompt."""
        context = {
            "synergies": ["flush_builds", "economy_scaling"],
            "win_rate": 0.65
        }
        
        prompt = builder.build_strategy_prompt(sample_game_state, context)
        
        assert "ante" in prompt
        assert "jokers" in prompt
        assert "synergies" in prompt
        assert len(prompt) < 2000  # Keep prompts concise
    
    def test_builds_failure_analysis_prompt(self, builder):
        """Test building failure analysis prompt."""
        game_history = [
            {"ante": 1, "key_decisions": ["bought_joker"]},
            {"ante": 5, "key_decisions": ["skipped_scaling"], "failed": True}
        ]
        
        prompt = builder.build_failure_prompt(game_history)
        
        assert "ante 5" in prompt
        assert "skipped_scaling" in prompt
        assert "recommendations" in prompt.lower()
    
    def test_includes_relevant_context(self, builder):
        """Test inclusion of relevant context in prompts."""
        state = {"ante": 7, "boss": "The Needle"}
        context = {
            "boss_strategy": "Requires exactly 7 cards",
            "recommended_jokers": ["Trading Card", "DNA"]
        }
        
        prompt = builder.build_strategy_prompt(state, context)
        
        assert "The Needle" in prompt
        assert "exactly 7 cards" in prompt
        assert "Trading Card" in prompt
    
    def test_formats_game_state_clearly(self, builder):
        """Test clear formatting of game state."""
        complex_state = {
            "jokers": ["Joker", "Baseball Card", "DNA"],
            "hand": ["AH", "KH", "QH", "JH", "10H", "9H", "8H", "7H"],
            "money": 45,
            "shop": {
                "jokers": ["Blueprint", "Brainstorm"],
                "vouchers": ["Blank"],
                "packs": ["Arcana", "Buffoon"]
            }
        }
        
        formatted = builder.format_game_state(complex_state)
        
        assert formatted.count("\n") > 5  # Well-structured
        assert "Jokers:" in formatted
        assert "Shop:" in formatted


class TestResponseParser:
    """Test parsing Claude responses."""
    
    @pytest.fixture
    def parser(self):
        """Create a response parser."""
        return ResponseParser()
    
    def test_extracts_action_recommendation(self, parser):
        """Test extracting recommended action from response."""
        response = """
        Based on your current setup, I recommend:
        ACTION: buy_joker Blueprint
        REASON: Will copy your Baseball Card for exponential scaling
        CONFIDENCE: 0.85
        """
        
        parsed = parser.parse_strategy_response(response)
        
        assert parsed["action"] == "buy_joker"
        assert parsed["target"] == "Blueprint"
        assert parsed["confidence"] == 0.85
        assert "exponential scaling" in parsed["reason"]
    
    def test_extracts_multiple_recommendations(self, parser):
        """Test extracting prioritized recommendations."""
        response = """
        Priority recommendations:
        1. Buy Blueprint (0.9 confidence) - Best scaling option
        2. Save for next shop (0.7 confidence) - If Blueprint not available
        3. Buy Tarot pack (0.5 confidence) - Look for hand enhancements
        """
        
        recommendations = parser.parse_recommendations(response)
        
        assert len(recommendations) == 3
        assert recommendations[0]["action"] == "Buy Blueprint"
        assert recommendations[0]["confidence"] == 0.9
        assert recommendations[2]["confidence"] == 0.5
    
    def test_handles_unstructured_responses(self, parser):
        """Test parsing free-form responses."""
        response = "Focus on building flushes with your current setup"
        
        parsed = parser.parse_strategy_response(response)
        
        assert parsed["strategy"] == "flush_focus"
        assert parsed["raw_advice"] == response
    
    def test_extracts_failure_insights(self, parser):
        """Test extracting insights from failure analysis."""
        response = """
        Analysis of failed run:
        
        CRITICAL ERROR: Insufficient damage scaling
        - Should have prioritized multiplicative jokers in ante 3-4
        - Economy management was good but over-saved
        
        KEY LEARNING: Balance economy with scaling purchases
        """
        
        insights = parser.parse_failure_analysis(response)
        
        assert insights["critical_error"] == "Insufficient damage scaling"
        assert len(insights["mistakes"]) == 2
        assert insights["key_learning"] is not None