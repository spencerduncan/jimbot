"""
Unit tests for Memgraph query builder with focus on SQL injection prevention.

Tests parameterized queries, input validation, and security measures.
"""

import pytest

from jimbot.memgraph.query_builder import CardQueryBuilder, QueryBuilder


class TestQueryBuilderSecurity:
    """Test QueryBuilder security measures and SQL injection prevention."""

    def test_basic_query_builder_parameterization(self):
        """Test that QueryBuilder properly parameterizes values."""
        query = (
            QueryBuilder()
            .match("(j:Joker)")
            .where("j.name = $name")
            .param("name", "Blueprint")
            .build()
        )
        
        query_str, params = query
        assert "$name" in query_str
        assert params["name"] == "Blueprint"
        # Ensure no direct string interpolation
        assert "Blueprint" not in query_str

    def test_where_in_prevents_injection(self):
        """Test that where_in method prevents SQL injection."""
        malicious_values = [
            "valid_joker",
            "evil'); MATCH (n) DETACH DELETE n; //",
            "another' OR 1=1 --"
        ]
        
        query = (
            QueryBuilder()
            .match("(j:Joker)")
            .where_in("j.name", malicious_values, "names")
            .build()
        )
        
        query_str, params = query
        assert "$names" in query_str
        assert params["names"] == malicious_values
        # Ensure malicious strings are not in the query
        assert "DELETE" not in query_str
        assert "OR 1=1" not in query_str


class TestCardQueryBuilderSecurity:
    """Test CardQueryBuilder security against SQL injection attacks."""

    def test_analyze_deck_compatibility_prevents_injection(self):
        """Test that analyze_deck_compatibility prevents SQL injection through suit names."""
        # Attempt SQL injection through suit parameter
        malicious_deck = {
            "Hearts' OR 1=1 UNION MATCH (n) DETACH DELETE n //": 10,
            "Diamonds": 5
        }
        
        # Should raise ValueError for invalid suit
        with pytest.raises(ValueError, match="Invalid suit"):
            CardQueryBuilder.analyze_deck_compatibility(malicious_deck)

    def test_analyze_deck_compatibility_valid_suits(self):
        """Test that valid suits are processed correctly with parameterization."""
        valid_deck = {
            "Hearts": 13,
            "Diamonds": 10,
            "Clubs": 8,
            "Spades": 12
        }
        
        query_str, params = CardQueryBuilder.analyze_deck_compatibility(valid_deck)
        
        # Check that all suits are parameterized
        assert "$suit_0" in query_str
        assert "$suit_1" in query_str
        assert "$suit_2" in query_str
        assert "$suit_3" in query_str
        
        # Check that counts are parameterized
        assert "$deck_0" in query_str
        assert "$deck_1" in query_str
        assert "$deck_2" in query_str
        assert "$deck_3" in query_str
        
        # Verify parameters contain the correct values
        assert params["suit_0"] == "Hearts"
        assert params["deck_0"] == 13
        assert params["suit_1"] == "Diamonds"
        assert params["deck_1"] == 10
        assert params["suit_2"] == "Clubs"
        assert params["deck_2"] == 8
        assert params["suit_3"] == "Spades"
        assert params["deck_3"] == 12
        
        # Ensure no direct string interpolation of suit names
        assert "'Hearts'" not in query_str
        assert "'Diamonds'" not in query_str
        assert "'Clubs'" not in query_str
        assert "'Spades'" not in query_str

    def test_sql_injection_attempts_comprehensive(self):
        """Test various SQL injection payloads are blocked."""
        injection_payloads = [
            # Classic SQL injection attempts
            {"Hearts' OR '1'='1": 10},
            {"Hearts'; DROP TABLE jokers; --": 10},
            {"Hearts' UNION SELECT * FROM users --": 10},
            
            # Cypher-specific injection attempts
            {"Hearts' WITH 1 as x MATCH (n) DETACH DELETE n //": 10},
            {"Hearts' RETURN 1 UNION MATCH (j:Joker) SET j.cost = 0 //": 10},
            {"Hearts'] WITH true as dummy MATCH (n) DETACH DELETE n //": 10},
            
            # Unicode and encoding attacks
            {"Hearts\u0027 OR 1=1 --": 10},
            {"Hearts%27 OR 1=1 --": 10},
            
            # Multi-line injection attempts
            {"Hearts'\nMATCH (n) DELETE n\n//": 10},
            
            # Comment-based injections
            {"Hearts' /* comment */ OR 1=1 --": 10},
            {"Hearts' -- comment\nOR 1=1": 10}
        ]
        
        for malicious_deck in injection_payloads:
            with pytest.raises(ValueError, match="Invalid suit"):
                CardQueryBuilder.analyze_deck_compatibility(malicious_deck)

    def test_mixed_valid_invalid_suits(self):
        """Test that mixing valid and invalid suits still raises error."""
        mixed_deck = {
            "Hearts": 10,  # Valid
            "Diamonds": 5,  # Valid
            "InvalidSuit': DELETE n //": 8  # Invalid/malicious
        }
        
        with pytest.raises(ValueError, match="Invalid suit"):
            CardQueryBuilder.analyze_deck_compatibility(mixed_deck)

    def test_case_sensitive_suit_validation(self):
        """Test that suit validation is case-sensitive."""
        # Lowercase should be invalid
        invalid_case_deck = {
            "hearts": 10,
            "diamonds": 5
        }
        
        with pytest.raises(ValueError, match="Invalid suit"):
            CardQueryBuilder.analyze_deck_compatibility(invalid_case_deck)

    def test_empty_deck_composition(self):
        """Test handling of empty deck composition."""
        empty_deck = {}
        
        query_str, params = CardQueryBuilder.analyze_deck_compatibility(empty_deck)
        
        # Should produce valid query even with no suits
        assert "MATCH" in query_str
        assert len(params) == 0

    def test_whitespace_in_suit_names(self):
        """Test that suits with whitespace are rejected."""
        whitespace_deck = {
            " Hearts": 10,  # Leading space
            "Hearts ": 5,   # Trailing space
            "Hearts Diamonds": 8  # Space in middle
        }
        
        with pytest.raises(ValueError, match="Invalid suit"):
            CardQueryBuilder.analyze_deck_compatibility(whitespace_deck)

    def test_special_characters_in_suit_names(self):
        """Test that suits with special characters are rejected."""
        special_char_decks = [
            {"Hearts$": 10},
            {"Hearts@": 10},
            {"Hearts#": 10},
            {"Hearts&": 10},
            {"Hearts*": 10},
            {"Hearts(": 10},
            {"Hearts)": 10},
            {"Hearts{": 10},
            {"Hearts}": 10},
            {"Hearts[": 10},
            {"Hearts]": 10},
            {"Hearts;": 10},
            {"Hearts:": 10},
            {"Hearts<": 10},
            {"Hearts>": 10},
            {"Hearts?": 10},
            {"Hearts/": 10},
            {"Hearts\\": 10},
            {"Hearts|": 10},
            {"Hearts`": 10},
            {"Hearts~": 10},
            {"Hearts!": 10},
            {"Hearts%": 10},
            {"Hearts^": 10},
            {"Hearts=": 10},
            {"Hearts+": 10},
            {"Hearts-": 10},
            {"Hearts.": 10},
            {"Hearts,": 10}
        ]
        
        for special_deck in special_char_decks:
            with pytest.raises(ValueError, match="Invalid suit"):
                CardQueryBuilder.analyze_deck_compatibility(special_deck)

    def test_parameter_isolation(self):
        """Test that parameters are properly isolated and don't interfere."""
        deck1 = {"Hearts": 10, "Diamonds": 5}
        deck2 = {"Clubs": 8, "Spades": 12}
        
        query1_str, params1 = CardQueryBuilder.analyze_deck_compatibility(deck1)
        query2_str, params2 = CardQueryBuilder.analyze_deck_compatibility(deck2)
        
        # Ensure parameters don't overlap
        assert set(params1.keys()).isdisjoint(set(params2.keys()))
        
        # Each query should have its own parameters
        assert len(params1) == 4  # 2 suits + 2 counts
        assert len(params2) == 4  # 2 suits + 2 counts

    def test_query_structure_with_security_fix(self):
        """Test the query structure after security fix implementation."""
        deck = {"Hearts": 10, "Spades": 5}
        
        query_str, params = CardQueryBuilder.analyze_deck_compatibility(deck)
        
        # Verify query structure
        assert "MATCH (j:Joker)-[r:REQUIRES_CARD]->(c:PlayingCard)" in query_str
        assert "WITH j, c.suit as suit, SUM(r.optimal_quantity) as needed" in query_str
        assert "WHERE" in query_str
        assert "OR" in query_str  # Should use OR logic for compatibility
        assert "WITH j, COUNT(*) as compatible_suits" in query_str
        assert "RETURN j.name as joker, j.cost as cost, compatible_suits" in query_str
        assert "ORDER BY compatible_suits DESC" in query_str
        
        # Verify parameterization in WHERE clause
        assert "(suit = $suit_0 AND needed <= $deck_0)" in query_str
        assert "(suit = $suit_1 AND needed <= $deck_1)" in query_str

    def test_find_required_cards_security(self):
        """Test that find_required_cards also uses safe parameterization."""
        joker_names = [
            "Blueprint",
            "Malicious'; DELETE n; //",
            "Another' OR 1=1 --"
        ]
        
        query_str, params = CardQueryBuilder.find_required_cards(joker_names)
        
        # Check parameterization
        assert "$joker_names" in query_str
        assert params["joker_names"] == joker_names
        
        # Ensure no injection strings in query
        assert "DELETE" not in query_str
        assert "OR 1=1" not in query_str


class TestQueryBuilderRegressionTests:
    """Regression tests to ensure functionality still works after security fix."""

    def test_deck_compatibility_returns_valid_cypher(self):
        """Test that the query builder still produces valid Cypher syntax."""
        deck = {"Hearts": 13, "Diamonds": 13}
        
        query_str, params = CardQueryBuilder.analyze_deck_compatibility(deck)
        
        # Basic Cypher syntax validation
        assert query_str.count("MATCH") >= 1
        assert query_str.count("WITH") >= 2
        assert query_str.count("WHERE") >= 1
        assert query_str.count("RETURN") == 1
        assert query_str.count("ORDER BY") == 1

    def test_single_suit_deck(self):
        """Test handling of single-suit deck."""
        single_suit_deck = {"Hearts": 13}
        
        query_str, params = CardQueryBuilder.analyze_deck_compatibility(single_suit_deck)
        
        # Should have one condition in WHERE clause
        assert "(suit = $suit_0 AND needed <= $deck_0)" in query_str
        assert len(params) == 2  # One suit + one count

    def test_all_four_suits(self):
        """Test handling of all four suits."""
        full_deck = {
            "Hearts": 13,
            "Diamonds": 13,
            "Clubs": 13,
            "Spades": 13
        }
        
        query_str, params = CardQueryBuilder.analyze_deck_compatibility(full_deck)
        
        # Should have four conditions connected by OR
        assert query_str.count(" OR ") == 3  # Three OR operators for four conditions
        assert len(params) == 8  # Four suits + four counts