"""Query builder for constructing optimized Cypher queries."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class MatchType(Enum):
    """Types of pattern matching in Cypher."""

    SIMPLE = "MATCH"
    OPTIONAL = "OPTIONAL MATCH"


class OrderDirection(Enum):
    """Sort order directions."""

    ASC = "ASC"
    DESC = "DESC"


@dataclass
class QueryBuilder:
    """Fluent interface for building Cypher queries with optimization hints."""

    _match_clauses: List[str] = field(default_factory=list)
    _where_clauses: List[str] = field(default_factory=list)
    _with_clauses: List[str] = field(default_factory=list)
    _return_clause: Optional[str] = None
    _order_by: List[Tuple[str, OrderDirection]] = field(default_factory=list)
    _limit: Optional[int] = None
    _skip: Optional[int] = None
    _create_clauses: List[str] = field(default_factory=list)
    _set_clauses: List[str] = field(default_factory=list)
    _delete_clauses: List[str] = field(default_factory=list)
    _union_queries: List["QueryBuilder"] = field(default_factory=list)
    _parameters: Dict[str, Any] = field(default_factory=dict)
    _hints: List[str] = field(default_factory=list)

    def match(
        self, pattern: str, match_type: MatchType = MatchType.SIMPLE
    ) -> "QueryBuilder":
        """Add a MATCH clause.

        Args:
            pattern: Cypher pattern to match
            match_type: Type of match (MATCH or OPTIONAL MATCH)

        Returns:
            Self for chaining
        """
        self._match_clauses.append(f"{match_type.value} {pattern}")
        return self

    def optional_match(self, pattern: str) -> "QueryBuilder":
        """Add an OPTIONAL MATCH clause."""
        return self.match(pattern, MatchType.OPTIONAL)

    def where(self, condition: str) -> "QueryBuilder":
        """Add a WHERE condition.

        Args:
            condition: Cypher condition expression

        Returns:
            Self for chaining
        """
        self._where_clauses.append(condition)
        return self

    def where_in(
        self, property_path: str, values: List[Any], param_name: str
    ) -> "QueryBuilder":
        """Add a WHERE IN condition with parameter.

        Args:
            property_path: Property path (e.g., "j.name")
            values: List of values
            param_name: Parameter name to use

        Returns:
            Self for chaining
        """
        self._parameters[param_name] = values
        self._where_clauses.append(f"{property_path} IN ${param_name}")
        return self

    def where_range(
        self,
        property_path: str,
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None,
        param_prefix: str = "range",
    ) -> "QueryBuilder":
        """Add range conditions.

        Args:
            property_path: Property path
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
            param_prefix: Prefix for parameter names

        Returns:
            Self for chaining
        """
        if min_value is not None:
            param_name = f"{param_prefix}_min"
            self._parameters[param_name] = min_value
            self._where_clauses.append(f"{property_path} >= ${param_name}")

        if max_value is not None:
            param_name = f"{param_prefix}_max"
            self._parameters[param_name] = max_value
            self._where_clauses.append(f"{property_path} <= ${param_name}")

        return self

    def with_clause(self, *expressions: str) -> "QueryBuilder":
        """Add a WITH clause for query pipelining.

        Args:
            *expressions: Expressions to include in WITH

        Returns:
            Self for chaining
        """
        self._with_clauses.append("WITH " + ", ".join(expressions))
        return self

    def return_clause(self, *expressions: str) -> "QueryBuilder":
        """Set the RETURN clause.

        Args:
            *expressions: Expressions to return

        Returns:
            Self for chaining
        """
        self._return_clause = "RETURN " + ", ".join(expressions)
        return self

    def order_by(
        self, expression: str, direction: OrderDirection = OrderDirection.ASC
    ) -> "QueryBuilder":
        """Add ORDER BY clause.

        Args:
            expression: Expression to order by
            direction: Sort direction

        Returns:
            Self for chaining
        """
        self._order_by.append((expression, direction))
        return self

    def limit(self, n: int) -> "QueryBuilder":
        """Set LIMIT clause.

        Args:
            n: Maximum number of results

        Returns:
            Self for chaining
        """
        self._limit = n
        return self

    def skip(self, n: int) -> "QueryBuilder":
        """Set SKIP clause.

        Args:
            n: Number of results to skip

        Returns:
            Self for chaining
        """
        self._skip = n
        return self

    def create(self, pattern: str) -> "QueryBuilder":
        """Add CREATE clause.

        Args:
            pattern: Pattern to create

        Returns:
            Self for chaining
        """
        self._create_clauses.append(f"CREATE {pattern}")
        return self

    def merge(self, pattern: str) -> "QueryBuilder":
        """Add MERGE clause.

        Args:
            pattern: Pattern to merge

        Returns:
            Self for chaining
        """
        self._create_clauses.append(f"MERGE {pattern}")
        return self

    def set(self, *assignments: str) -> "QueryBuilder":
        """Add SET clause.

        Args:
            *assignments: Property assignments

        Returns:
            Self for chaining
        """
        self._set_clauses.extend(assignments)
        return self

    def delete(self, *variables: str) -> "QueryBuilder":
        """Add DELETE clause.

        Args:
            *variables: Variables to delete

        Returns:
            Self for chaining
        """
        self._delete_clauses.extend(variables)
        return self

    def detach_delete(self, *variables: str) -> "QueryBuilder":
        """Add DETACH DELETE clause.

        Args:
            *variables: Variables to detach delete

        Returns:
            Self for chaining
        """
        for var in variables:
            self._delete_clauses.append(f"DETACH DELETE {var}")
        return self

    def union(self, other: "QueryBuilder", all: bool = False) -> "QueryBuilder":
        """Add UNION with another query.

        Args:
            other: Another QueryBuilder
            all: Whether to use UNION ALL

        Returns:
            Self for chaining
        """
        self._union_queries.append(other)
        return self

    def using_index(self, variable: str, label: str, property: str) -> "QueryBuilder":
        """Add index hint.

        Args:
            variable: Variable name
            label: Node label
            property: Property name

        Returns:
            Self for chaining
        """
        self._hints.append(f"USING INDEX {variable}:{label}({property})")
        return self

    def param(self, name: str, value: Any) -> "QueryBuilder":
        """Add a query parameter.

        Args:
            name: Parameter name
            value: Parameter value

        Returns:
            Self for chaining
        """
        self._parameters[name] = value
        return self

    def build(self) -> Tuple[str, Dict[str, Any]]:
        """Build the final query and parameters.

        Returns:
            Tuple of (query_string, parameters)
        """
        parts = []

        # Add hints
        parts.extend(self._hints)

        # Add MATCH clauses
        parts.extend(self._match_clauses)

        # Add WHERE clause
        if self._where_clauses:
            parts.append("WHERE " + " AND ".join(self._where_clauses))

        # Add CREATE/MERGE clauses
        parts.extend(self._create_clauses)

        # Add SET clauses
        if self._set_clauses:
            parts.append("SET " + ", ".join(self._set_clauses))

        # Add DELETE clauses
        parts.extend(self._delete_clauses)

        # Add WITH clauses
        parts.extend(self._with_clauses)

        # Add RETURN clause
        if self._return_clause:
            parts.append(self._return_clause)

            # Add ORDER BY
            if self._order_by:
                order_parts = [f"{expr} {dir.value}" for expr, dir in self._order_by]
                parts.append("ORDER BY " + ", ".join(order_parts))

            # Add SKIP/LIMIT
            if self._skip is not None:
                parts.append(f"SKIP {self._skip}")
            if self._limit is not None:
                parts.append(f"LIMIT {self._limit}")

        query = "\n".join(parts)

        # Add UNION queries
        for union_query in self._union_queries:
            union_str, union_params = union_query.build()
            query += f"\nUNION\n{union_str}"
            self._parameters.update(union_params)

        return query, self._parameters


class SynergyQueryBuilder:
    """Specialized query builder for synergy-related queries."""

    @staticmethod
    def find_synergies(
        joker_names: List[str], min_strength: float = 0.5, limit: int = 10
    ) -> Tuple[str, Dict[str, Any]]:
        """Build query to find synergies for given jokers.

        Args:
            joker_names: List of joker names
            min_strength: Minimum synergy strength
            limit: Maximum results per joker

        Returns:
            Tuple of (query, parameters)
        """
        return (
            QueryBuilder()
            .match("(j:Joker)")
            .where_in("j.name", joker_names, "joker_names")
            .match("(j)-[s:SYNERGIZES_WITH]->(other:Joker)")
            .where("s.strength >= $min_strength")
            .return_clause(
                "j.name as joker",
                "COLLECT({target: other.name, strength: s.strength, type: s.synergy_type}) as synergies",
            )
            .param("min_strength", min_strength)
            .limit(limit)
            .build()
        )

    @staticmethod
    def find_synergy_paths(
        start_joker: str, max_depth: int = 3, min_path_strength: float = 0.6
    ) -> Tuple[str, Dict[str, Any]]:
        """Build query to find synergy paths from a starting joker.

        Args:
            start_joker: Starting joker name
            max_depth: Maximum path depth
            min_path_strength: Minimum acceptable path strength

        Returns:
            Tuple of (query, parameters)
        """
        return (
            QueryBuilder()
            .match("(start:Joker {name: $start_joker})")
            .match(f"path = (start)-[:SYNERGIZES_WITH*1..{max_depth}]->(end:Joker)")
            .where("ALL(r IN relationships(path) WHERE r.strength >= $min_strength)")
            .with_clause(
                "path",
                "end",
                "REDUCE(s = 1.0, r IN relationships(path) | s * r.strength) as path_strength",
            )
            .where("path_strength >= $min_path_strength")
            .return_clause("path", "end.name as target", "path_strength")
            .order_by("path_strength", OrderDirection.DESC)
            .limit(10)
            .param("start_joker", start_joker)
            .param("min_strength", 0.5)
            .param("min_path_strength", min_path_strength)
            .build()
        )

    @staticmethod
    def calculate_joker_combinations(
        current_jokers: List[str], budget: int, min_synergy: float = 0.6
    ) -> Tuple[str, Dict[str, Any]]:
        """Build query to find optimal joker combinations within budget.

        Args:
            current_jokers: Currently owned jokers
            budget: Available money
            min_synergy: Minimum required synergy

        Returns:
            Tuple of (query, parameters)
        """
        return (
            QueryBuilder()
            .match("(owned:Joker)")
            .where_in("owned.name", current_jokers, "current_jokers")
            .match("(owned)-[s:SYNERGIZES_WITH]->(candidate:Joker)")
            .where("NOT candidate.name IN $current_jokers")
            .where("candidate.cost <= $budget")
            .where("s.strength >= $min_synergy")
            .with_clause(
                "candidate",
                "AVG(s.strength) as avg_synergy",
                "COUNT(DISTINCT owned) as synergy_count",
            )
            .where("synergy_count >= 2")  # Synergizes with at least 2 owned jokers
            .return_clause(
                "candidate.name as joker",
                "candidate.cost as cost",
                "avg_synergy",
                "synergy_count",
                "avg_synergy * synergy_count as total_value",
            )
            .order_by("total_value", OrderDirection.DESC)
            .limit(5)
            .param("current_jokers", current_jokers)
            .param("budget", budget)
            .param("min_synergy", min_synergy)
            .build()
        )


class CardQueryBuilder:
    """Specialized query builder for card-related queries."""

    @staticmethod
    def find_required_cards(joker_names: List[str]) -> Tuple[str, Dict[str, Any]]:
        """Build query to find cards required by jokers.

        Args:
            joker_names: List of joker names

        Returns:
            Tuple of (query, parameters)
        """
        return (
            QueryBuilder()
            .match("(j:Joker)")
            .where_in("j.name", joker_names, "joker_names")
            .match("(j)-[r:REQUIRES_CARD]->(c:PlayingCard)")
            .return_clause(
                "j.name as joker",
                "COLLECT({suit: c.suit, rank: c.rank, quantity: r.optimal_quantity}) as required_cards",
            )
            .build()
        )

    @staticmethod
    def analyze_deck_compatibility(
        deck_composition: Dict[str, int],
    ) -> Tuple[str, Dict[str, Any]]:
        """Build query to find jokers compatible with deck composition.

        Args:
            deck_composition: Dict of suit -> count

        Returns:
            Tuple of (query, parameters)
        """
        query = QueryBuilder()

        # Build dynamic WHERE conditions for each suit
        for suit, count in deck_composition.items():
            param_name = f"deck_{suit.lower()}"
            query.param(param_name, count)

        return (
            query.match("(j:Joker)-[r:REQUIRES_CARD]->(c:PlayingCard)")
            .with_clause("j", "c.suit as suit", "SUM(r.optimal_quantity) as needed")
            .where(
                " AND ".join(
                    [
                        f"(suit = '{suit}' AND needed <= $deck_{suit.lower()})"
                        for suit in deck_composition.keys()
                    ]
                )
            )
            .with_clause("j", "COUNT(*) as compatible_suits")
            .return_clause("j.name as joker", "j.cost as cost", "compatible_suits")
            .order_by("compatible_suits", OrderDirection.DESC)
            .build()
        )


# Example usage
if __name__ == "__main__":
    # Example 1: Simple query
    query, params = (
        QueryBuilder()
        .match("(j:Joker)")
        .where("j.rarity = $rarity")
        .return_clause("j.name", "j.cost")
        .order_by("j.cost", OrderDirection.ASC)
        .limit(5)
        .param("rarity", "common")
        .build()
    )
    print("Simple Query:")
    print(query)
    print(f"Parameters: {params}\n")

    # Example 2: Complex synergy query
    query, params = SynergyQueryBuilder.find_synergies(
        ["Blueprint", "Brainstorm", "DNA"], min_strength=0.7
    )
    print("Synergy Query:")
    print(query)
    print(f"Parameters: {params}\n")

    # Example 3: Path finding query
    query, params = SynergyQueryBuilder.find_synergy_paths(
        "Blueprint", max_depth=3, min_path_strength=0.5
    )
    print("Path Query:")
    print(query)
    print(f"Parameters: {params}")
