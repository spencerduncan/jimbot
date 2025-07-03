"""
Unit tests for Memgraph query operations.

Tests graph queries, schema operations, and performance.
"""

import pytest

from jimbot.memgraph.queries import (
    JokerSynergyQuery,
    GameStateStore,
    StrategyAnalyzer,
    GraphOptimizer,
)


class TestJokerSynergyQuery:
    """Test joker synergy calculations."""

    @pytest.fixture
    def query_engine(self, mock_memgraph_client):
        """Create a query engine with mocked client."""
        return JokerSynergyQuery(mock_memgraph_client)

    def test_finds_direct_synergies(self, query_engine):
        """Test finding direct joker synergies."""
        # Mock return data
        query_engine.client.execute_query.return_value = [
            {
                "joker": "Baseball Card",
                "synergy": 0.8,
                "reason": "Both scale with cards",
            },
            {"joker": "Scary Face", "synergy": 0.6, "reason": "Face card synergy"},
        ]

        synergies = query_engine.find_synergies("Joker")

        assert len(synergies) == 2
        assert synergies[0]["synergy"] == 0.8
        query_engine.client.execute_query.assert_called_once()

    def test_calculates_team_synergy_score(self, query_engine):
        """Test calculating overall synergy for joker team."""
        jokers = ["Joker", "Baseball Card", "Scary Face"]

        # Mock individual synergy queries
        query_engine.client.execute_query.side_effect = [
            [{"total_synergy": 1.4}],  # Joker pairs
            [{"total_synergy": 0.8}],  # Baseball Card pairs
            [{"total_synergy": 0.6}],  # Scary Face pairs
        ]

        score = query_engine.calculate_team_synergy(jokers)

        assert score == 2.8
        assert query_engine.client.execute_query.call_count == 3

    def test_finds_synergy_paths(self, query_engine):
        """Test finding multi-hop synergy paths."""
        query_engine.client.execute_query.return_value = [
            {
                "path": ["Joker", "Baseball Card", "DNA"],
                "total_strength": 1.2,
                "path_length": 2,
            }
        ]

        paths = query_engine.find_synergy_paths("Joker", max_depth=3)

        assert len(paths) == 1
        assert paths[0]["path_length"] == 2
        assert "DNA" in paths[0]["path"]

    def test_recommends_jokers_for_strategy(self, query_engine):
        """Test joker recommendations based on strategy."""
        current_jokers = ["Joker"]
        strategy = "flush_build"

        query_engine.client.execute_query.return_value = [
            {"name": "Smeared Joker", "score": 0.9, "reason": "Enables flush builds"},
            {"name": "Four Fingers", "score": 0.85, "reason": "Makes flushes easier"},
        ]

        recommendations = query_engine.recommend_jokers(current_jokers, strategy)

        assert len(recommendations) == 2
        assert recommendations[0]["name"] == "Smeared Joker"
        assert recommendations[0]["score"] == 0.9


class TestGameStateStore:
    """Test game state storage and retrieval."""

    @pytest.fixture
    def state_store(self, mock_memgraph_client):
        """Create a game state store."""
        return GameStateStore(mock_memgraph_client)

    def test_stores_complete_game_state(self, state_store, sample_game_state):
        """Test storing a full game state."""
        result = state_store.store_state(sample_game_state)

        assert result["success"]
        assert result["state_id"] is not None

        # Verify all components were stored
        calls = state_store.client.execute_query.call_args_list
        assert any("CREATE (:GameState" in str(call) for call in calls)

    def test_retrieves_game_state_by_id(self, state_store):
        """Test retrieving stored game state."""
        state_id = "test-state-123"

        # Mock the retrieval
        state_store.client.execute_query.return_value = [
            {"state": {"ante": 5, "money": 50, "jokers": ["Joker", "Baseball Card"]}}
        ]

        retrieved = state_store.get_state(state_id)

        assert retrieved["ante"] == 5
        assert len(retrieved["jokers"]) == 2

    def test_finds_similar_game_states(self, state_store, sample_game_state):
        """Test finding similar historical states."""
        state_store.client.execute_query.return_value = [
            {"state_id": "similar-1", "similarity": 0.92},
            {"state_id": "similar-2", "similarity": 0.88},
        ]

        similar = state_store.find_similar_states(sample_game_state, limit=5)

        assert len(similar) == 2
        assert similar[0]["similarity"] == 0.92

    def test_tracks_state_transitions(self, state_store):
        """Test linking game states in sequence."""
        prev_state_id = "state-1"
        new_state_id = "state-2"
        action = {"type": "play_hand", "cards": ["AH", "KH", "QH", "JH", "10H"]}

        result = state_store.link_states(prev_state_id, new_state_id, action)

        assert result["success"]
        state_store.client.execute_query.assert_called()


class TestStrategyAnalyzer:
    """Test strategy analysis and pattern detection."""

    @pytest.fixture
    def analyzer(self, mock_memgraph_client):
        """Create a strategy analyzer."""
        return StrategyAnalyzer(mock_memgraph_client)

    def test_identifies_winning_patterns(self, analyzer):
        """Test finding patterns in successful runs."""
        analyzer.client.execute_query.return_value = [
            {"pattern": "early_economy_focus", "success_rate": 0.75, "occurrences": 45},
            {"pattern": "joker_scaling", "success_rate": 0.68, "occurrences": 32},
        ]

        patterns = analyzer.find_winning_patterns(min_ante=8)

        assert len(patterns) == 2
        assert patterns[0]["success_rate"] == 0.75
        assert patterns[0]["pattern"] == "early_economy_focus"

    def test_analyzes_decision_outcomes(self, analyzer):
        """Test analyzing specific decision outcomes."""
        decision_type = "joker_purchase"

        analyzer.client.execute_query.return_value = [
            {
                "choice": "Blueprint",
                "avg_ante_improvement": 1.2,
                "success_rate": 0.65,
                "sample_size": 25,
            }
        ]

        analysis = analyzer.analyze_decisions(decision_type)

        assert len(analysis) == 1
        assert analysis[0]["choice"] == "Blueprint"
        assert analysis[0]["avg_ante_improvement"] == 1.2

    def test_detects_failure_patterns(self, analyzer):
        """Test identifying common failure patterns."""
        analyzer.client.execute_query.return_value = [
            {
                "pattern": "insufficient_scaling",
                "failure_rate": 0.82,
                "avg_ante_failed": 6,
            },
            {
                "pattern": "poor_economy_management",
                "failure_rate": 0.71,
                "avg_ante_failed": 4,
            },
        ]

        failures = analyzer.find_failure_patterns()

        assert len(failures) == 2
        assert failures[0]["failure_rate"] == 0.82


class TestGraphOptimizer:
    """Test graph optimization and maintenance."""

    @pytest.fixture
    def optimizer(self, mock_memgraph_client):
        """Create a graph optimizer."""
        return GraphOptimizer(mock_memgraph_client)

    def test_creates_indexes(self, optimizer):
        """Test index creation for performance."""
        optimizer.create_indexes()

        # Verify index creation queries
        calls = optimizer.client.execute_query.call_args_list
        index_queries = [call for call in calls if "CREATE INDEX" in str(call)]

        assert len(index_queries) >= 3  # At least joker, state, synergy indexes

    def test_analyzes_query_performance(self, optimizer):
        """Test query performance analysis."""
        optimizer.client.execute_query.return_value = [
            {"query_pattern": "synergy_search", "avg_time_ms": 45, "call_count": 1200},
            {"query_pattern": "state_retrieval", "avg_time_ms": 12, "call_count": 3400},
        ]

        slow_queries = optimizer.find_slow_queries(threshold_ms=20)

        assert len(slow_queries) == 1
        assert slow_queries[0]["query_pattern"] == "synergy_search"

    def test_suggests_optimizations(self, optimizer):
        """Test optimization suggestions."""
        query = "MATCH (j:Joker)-[s:SYNERGIZES_WITH*1..3]-(j2:Joker) RETURN j, s, j2"

        suggestions = optimizer.suggest_optimizations(query)

        assert len(suggestions) > 0
        assert any("index" in s.lower() for s in suggestions)

    @pytest.mark.parametrize(
        "node_count,expected_action",
        [(10000, "none"), (100000, "cleanup_suggested"), (1000000, "cleanup_required")],
    )
    def test_monitors_graph_size(self, optimizer, node_count, expected_action):
        """Test graph size monitoring and cleanup suggestions."""
        optimizer.client.execute_query.return_value = [{"node_count": node_count}]

        status = optimizer.check_graph_health()

        assert status["action"] == expected_action
        assert status["node_count"] == node_count
