"""Joker synergy calculation algorithms for Memgraph.

This module provides algorithms to calculate and update synergy scores
between jokers based on game performance data.
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
from dataclasses import dataclass
import asyncio
from neo4j import AsyncGraphDatabase
import logging

logger = logging.getLogger(__name__)


@dataclass
class JokerSynergy:
    """Represents a synergy relationship between two jokers."""
    joker1: str
    joker2: str
    strength: float
    synergy_type: str
    win_rate: float
    confidence: float
    games_tested: int


class JokerSynergyCalculator:
    """Calculates synergy scores between jokers based on game data."""
    
    def __init__(self, driver: AsyncGraphDatabase.driver):
        self.driver = driver
        self.min_games_for_confidence = 20
        self.synergy_threshold = 0.5
        
    async def calculate_pairwise_synergy(
        self, 
        joker1: str, 
        joker2: str
    ) -> Optional[JokerSynergy]:
        """Calculate synergy between two specific jokers.
        
        Args:
            joker1: Name of first joker
            joker2: Name of second joker
            
        Returns:
            JokerSynergy object or None if insufficient data
        """
        query = """
        MATCH (g:GameSession)-[:USED_JOKER]->(j1:Joker {name: $joker1})
        MATCH (g)-[:USED_JOKER]->(j2:Joker {name: $joker2})
        WHERE j1 <> j2
        WITH g.final_score as score, 
             g.final_ante as ante,
             g.won as won
        WITH AVG(score) as avg_score,
             AVG(ante) as avg_ante,
             AVG(CASE WHEN won THEN 1.0 ELSE 0.0 END) as win_rate,
             COUNT(*) as games_count,
             STDEV(score) as score_std
        
        // Compare with individual joker performance
        MATCH (g1:GameSession)-[:USED_JOKER]->(j1:Joker {name: $joker1})
        WHERE NOT (g1)-[:USED_JOKER]->(:Joker {name: $joker2})
        WITH avg_score, avg_ante, win_rate, games_count, score_std,
             AVG(g1.final_score) as j1_solo_score
        
        MATCH (g2:GameSession)-[:USED_JOKER]->(j2:Joker {name: $joker2})
        WHERE NOT (g2)-[:USED_JOKER]->(:Joker {name: $joker1})
        WITH avg_score, avg_ante, win_rate, games_count, score_std,
             j1_solo_score,
             AVG(g2.final_score) as j2_solo_score
        
        RETURN avg_score, avg_ante, win_rate, games_count,
               j1_solo_score, j2_solo_score,
               (avg_score - (j1_solo_score + j2_solo_score) / 2) as synergy_bonus
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                joker1=joker1,
                joker2=joker2
            )
            record = await result.single()
            
            if not record or record["games_count"] < self.min_games_for_confidence:
                return None
            
            # Calculate synergy strength based on performance improvement
            synergy_bonus = record["synergy_bonus"]
            avg_solo = (record["j1_solo_score"] + record["j2_solo_score"]) / 2
            
            if avg_solo > 0:
                strength = min(1.0, max(0.0, synergy_bonus / avg_solo))
            else:
                strength = 0.0
            
            # Determine synergy type
            if synergy_bonus > avg_solo * 0.5:
                synergy_type = "multiplicative"
            elif synergy_bonus > avg_solo * 0.2:
                synergy_type = "additive"
            else:
                synergy_type = "complementary"
            
            # Calculate confidence based on sample size
            confidence = min(1.0, record["games_count"] / (self.min_games_for_confidence * 5))
            
            return JokerSynergy(
                joker1=joker1,
                joker2=joker2,
                strength=strength,
                synergy_type=synergy_type,
                win_rate=record["win_rate"],
                confidence=confidence,
                games_tested=record["games_count"]
            )
    
    async def update_all_synergies(self) -> Dict[str, int]:
        """Recalculate all joker synergies based on recent games.
        
        Returns:
            Dictionary with update statistics
        """
        stats = {
            "updated": 0,
            "created": 0,
            "removed": 0,
            "errors": 0
        }
        
        # Get all joker pairs to analyze
        query = """
        MATCH (j:Joker)
        WITH collect(j.name) as jokers
        UNWIND jokers as j1
        UNWIND jokers as j2
        WHERE j1 < j2  // Avoid duplicates and self-pairs
        RETURN j1, j2
        """
        
        async with self.driver.session() as session:
            result = await session.run(query)
            pairs = [(r["j1"], r["j2"]) async for r in result]
        
        # Calculate synergies for each pair
        for joker1, joker2 in pairs:
            try:
                synergy = await self.calculate_pairwise_synergy(joker1, joker2)
                
                if synergy and synergy.strength >= self.synergy_threshold:
                    await self._update_synergy_relationship(synergy)
                    stats["updated"] += 1
                elif synergy and synergy.strength < self.synergy_threshold:
                    await self._remove_synergy_relationship(joker1, joker2)
                    stats["removed"] += 1
                    
            except Exception as e:
                logger.error(f"Error calculating synergy for {joker1}-{joker2}: {e}")
                stats["errors"] += 1
        
        return stats
    
    async def _update_synergy_relationship(self, synergy: JokerSynergy):
        """Update or create synergy relationship in graph."""
        query = """
        MATCH (j1:Joker {name: $joker1})
        MATCH (j2:Joker {name: $joker2})
        MERGE (j1)-[s:SYNERGIZES_WITH]->(j2)
        SET s.strength = $strength,
            s.synergy_type = $synergy_type,
            s.win_rate = $win_rate,
            s.confidence = $confidence,
            s.games_tested = $games_tested,
            s.last_updated = datetime()
        """
        
        async with self.driver.session() as session:
            await session.run(
                query,
                joker1=synergy.joker1,
                joker2=synergy.joker2,
                strength=synergy.strength,
                synergy_type=synergy.synergy_type,
                win_rate=synergy.win_rate,
                confidence=synergy.confidence,
                games_tested=synergy.games_tested
            )
    
    async def _remove_synergy_relationship(self, joker1: str, joker2: str):
        """Remove weak synergy relationship."""
        query = """
        MATCH (j1:Joker {name: $joker1})-[s:SYNERGIZES_WITH]->(j2:Joker {name: $joker2})
        DELETE s
        """
        
        async with self.driver.session() as session:
            await session.run(query, joker1=joker1, joker2=joker2)
    
    async def find_synergy_clusters(self, min_cluster_size: int = 3) -> List[List[str]]:
        """Find clusters of highly synergistic jokers.
        
        Args:
            min_cluster_size: Minimum number of jokers in a cluster
            
        Returns:
            List of joker clusters (each cluster is a list of joker names)
        """
        query = """
        // Find strongly connected components of synergistic jokers
        CALL gds.graph.project(
            'synergy-graph',
            'Joker',
            {
                SYNERGIZES_WITH: {
                    properties: ['strength']
                }
            }
        )
        
        CALL gds.louvain.stream('synergy-graph', {
            relationshipWeightProperty: 'strength',
            includeIntermediateCommunities: false
        })
        YIELD nodeId, communityId
        
        WITH gds.util.asNode(nodeId) AS joker, communityId
        WITH communityId, collect(joker.name) as cluster
        WHERE size(cluster) >= $min_size
        
        CALL gds.graph.drop('synergy-graph') YIELD graphName
        
        RETURN cluster
        ORDER BY size(cluster) DESC
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, min_size=min_cluster_size)
                return [r["cluster"] async for r in result]
        except Exception as e:
            logger.warning(f"GDS not available, using fallback clustering: {e}")
            return await self._fallback_clustering(min_cluster_size)
    
    async def _fallback_clustering(self, min_cluster_size: int) -> List[List[str]]:
        """Simple clustering without GDS library."""
        query = """
        MATCH (j1:Joker)-[s:SYNERGIZES_WITH]-(j2:Joker)
        WHERE s.strength > 0.7
        WITH j1, collect(DISTINCT j2.name) as neighbors
        WHERE size(neighbors) >= $min_size - 1
        RETURN j1.name as joker, neighbors
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, min_size=min_cluster_size)
            
            # Build clusters from neighborhoods
            clusters = []
            seen_jokers = set()
            
            async for record in result:
                joker = record["joker"]
                if joker not in seen_jokers:
                    cluster = [joker] + record["neighbors"]
                    cluster = [j for j in cluster if j not in seen_jokers]
                    if len(cluster) >= min_cluster_size:
                        clusters.append(cluster)
                        seen_jokers.update(cluster)
            
            return clusters
    
    async def get_anti_synergies(self, threshold: float = -0.3) -> List[Tuple[str, str, float]]:
        """Find joker pairs that work poorly together.
        
        Args:
            threshold: Maximum synergy score to consider anti-synergistic
            
        Returns:
            List of (joker1, joker2, anti_synergy_strength) tuples
        """
        query = """
        MATCH (j1:Joker)-[s:SYNERGIZES_WITH]->(j2:Joker)
        WHERE s.strength < $threshold
        RETURN j1.name as joker1, j2.name as joker2, s.strength as strength
        ORDER BY s.strength ASC
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, threshold=threshold)
            return [
                (r["joker1"], r["joker2"], r["strength"])
                async for r in result
            ]


class SynergyMatrixBuilder:
    """Builds synergy matrices for machine learning models."""
    
    def __init__(self, driver: AsyncGraphDatabase.driver):
        self.driver = driver
    
    async def build_synergy_matrix(self) -> Tuple[np.ndarray, List[str]]:
        """Build a synergy matrix for all jokers.
        
        Returns:
            Tuple of (synergy_matrix, joker_names)
            Matrix is symmetric with diagonal = 1.0
        """
        # Get all jokers
        query = """
        MATCH (j:Joker)
        RETURN j.name as name
        ORDER BY j.name
        """
        
        async with self.driver.session() as session:
            result = await session.run(query)
            joker_names = [r["name"] async for r in result]
        
        n_jokers = len(joker_names)
        matrix = np.eye(n_jokers)  # Initialize with 1.0 on diagonal
        
        # Fill in synergy values
        query = """
        MATCH (j1:Joker)-[s:SYNERGIZES_WITH]->(j2:Joker)
        RETURN j1.name as joker1, j2.name as joker2, s.strength as strength
        """
        
        async with self.driver.session() as session:
            result = await session.run(query)
            
            joker_to_idx = {name: i for i, name in enumerate(joker_names)}
            
            async for record in result:
                i = joker_to_idx.get(record["joker1"])
                j = joker_to_idx.get(record["joker2"])
                
                if i is not None and j is not None:
                    strength = record["strength"]
                    matrix[i, j] = strength
                    matrix[j, i] = strength  # Symmetric
        
        return matrix, joker_names
    
    async def build_requirement_matrix(self) -> Tuple[np.ndarray, List[str], List[str]]:
        """Build a matrix of joker-card requirements.
        
        Returns:
            Tuple of (requirement_matrix, joker_names, card_identifiers)
        """
        # Get jokers and cards
        joker_query = "MATCH (j:Joker) RETURN j.name as name ORDER BY j.name"
        card_query = "MATCH (c:PlayingCard) RETURN c.suit + c.rank as card ORDER BY c.suit, c.rank"
        
        async with self.driver.session() as session:
            joker_result = await session.run(joker_query)
            joker_names = [r["name"] async for r in joker_result]
            
            card_result = await session.run(card_query)
            card_ids = [r["card"] async for r in card_result]
        
        # Build requirement matrix
        matrix = np.zeros((len(joker_names), len(card_ids)))
        
        query = """
        MATCH (j:Joker)-[r:REQUIRES_CARD]->(c:PlayingCard)
        RETURN j.name as joker, c.suit + c.rank as card, r.optimal_quantity as qty
        """
        
        async with self.driver.session() as session:
            result = await session.run(query)
            
            joker_to_idx = {name: i for i, name in enumerate(joker_names)}
            card_to_idx = {card: i for i, card in enumerate(card_ids)}
            
            async for record in result:
                i = joker_to_idx.get(record["joker"])
                j = card_to_idx.get(record["card"])
                
                if i is not None and j is not None:
                    matrix[i, j] = record["qty"]
        
        return matrix, joker_names, card_ids


# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Example connection (adjust URI as needed)
        driver = AsyncGraphDatabase.driver("bolt://localhost:7687")
        
        try:
            calculator = JokerSynergyCalculator(driver)
            
            # Calculate specific synergy
            synergy = await calculator.calculate_pairwise_synergy("Fibonacci", "Odd Todd")
            if synergy:
                print(f"Synergy between Fibonacci and Odd Todd:")
                print(f"  Strength: {synergy.strength:.2f}")
                print(f"  Type: {synergy.synergy_type}")
                print(f"  Win Rate: {synergy.win_rate:.2%}")
            
            # Update all synergies
            stats = await calculator.update_all_synergies()
            print(f"\nSynergy update stats: {stats}")
            
            # Find clusters
            clusters = await calculator.find_synergy_clusters()
            print(f"\nFound {len(clusters)} synergy clusters")
            for i, cluster in enumerate(clusters):
                print(f"  Cluster {i+1}: {', '.join(cluster)}")
            
            # Build matrices
            matrix_builder = SynergyMatrixBuilder(driver)
            synergy_matrix, joker_names = await matrix_builder.build_synergy_matrix()
            print(f"\nBuilt synergy matrix: {synergy_matrix.shape}")
            
        finally:
            await driver.close()
    
    asyncio.run(main())