"""Memgraph client for JimBot.

Provides async connection management and query execution with performance monitoring.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from neo4j import AsyncDriver, AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable, TransientError

logger = logging.getLogger(__name__)


@dataclass
class QueryStats:
    """Statistics for a query execution."""

    query: str
    execution_time_ms: float
    records_returned: int
    success: bool
    error: Optional[str] = None


class MemgraphClient:
    """Async client for Memgraph database operations."""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        auth: Optional[tuple] = None,
        max_connection_lifetime: int = 3600,
        max_connection_pool_size: int = 20,
        connection_timeout: float = 10.0,
        query_timeout: float = 0.1,  # 100ms default
    ):
        """Initialize Memgraph client.

        Args:
            uri: Bolt protocol URI
            auth: Optional (username, password) tuple
            max_connection_lifetime: Max lifetime of connections in seconds
            max_connection_pool_size: Maximum number of connections
            connection_timeout: Timeout for establishing connections
            query_timeout: Default query timeout in seconds
        """
        self.uri = uri
        self.auth = auth
        self.query_timeout = query_timeout
        self._driver: Optional[AsyncDriver] = None
        self._query_stats: List[QueryStats] = []

        # Connection pool configuration
        self._config = {
            "max_connection_lifetime": max_connection_lifetime,
            "max_connection_pool_size": max_connection_pool_size,
            "connection_timeout": connection_timeout,
            "keep_alive": True,
            "encrypted": False,  # Set to True for production with TLS
        }

    async def connect(self):
        """Establish connection to Memgraph."""
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                self.uri, auth=self.auth, **self._config
            )
            logger.info(f"Connected to Memgraph at {self.uri}")

    async def close(self):
        """Close connection to Memgraph."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Disconnected from Memgraph")

    @asynccontextmanager
    async def session(self, database: Optional[str] = None):
        """Create a session context manager."""
        if not self._driver:
            await self.connect()

        async with self._driver.session(database=database) as session:
            yield session

    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters
            timeout: Query timeout in seconds (overrides default)

        Returns:
            List of result records as dictionaries

        Raises:
            TimeoutError: If query exceeds timeout
            ServiceUnavailable: If Memgraph is unavailable
        """
        timeout = timeout or self.query_timeout
        parameters = parameters or {}

        start_time = time.time()
        stats = QueryStats(
            query=query[:100] + "..." if len(query) > 100 else query,
            execution_time_ms=0,
            records_returned=0,
            success=False,
        )

        try:
            async with self.session() as session:
                # Use asyncio timeout for query execution
                async with asyncio.timeout(timeout):
                    result = await session.run(query, parameters)
                    records = [dict(record) async for record in result]

                stats.records_returned = len(records)
                stats.success = True

                return records

        except asyncio.TimeoutError:
            stats.error = f"Query exceeded {timeout}s timeout"
            logger.error(f"Query timeout: {stats.error}")
            raise TimeoutError(stats.error)

        except ServiceUnavailable as e:
            stats.error = str(e)
            logger.error(f"Memgraph unavailable: {e}")
            raise

        except Exception as e:
            stats.error = str(e)
            logger.error(f"Query error: {e}")
            raise

        finally:
            stats.execution_time_ms = (time.time() - start_time) * 1000
            self._query_stats.append(stats)

            # Log slow queries
            if stats.execution_time_ms > 50:
                logger.warning(
                    f"Slow query detected: {stats.execution_time_ms:.1f}ms - {stats.query}"
                )

    async def execute_transaction(self, transaction_function, *args, **kwargs):
        """Execute a function within a transaction.

        Args:
            transaction_function: Async function that takes a transaction object
            *args, **kwargs: Arguments passed to the function

        Returns:
            Result of the transaction function
        """
        async with self.session() as session:
            return await session.execute_write(transaction_function, *args, **kwargs)

    async def check_health(self) -> Dict[str, Any]:
        """Check Memgraph health and return status."""
        try:
            # Basic connectivity check
            result = await self.execute_query(
                "RETURN 'healthy' as status, datetime() as timestamp", timeout=1.0
            )

            # Get database statistics
            stats = await self.execute_query(
                """
                MATCH (n)
                WITH count(n) as node_count
                MATCH ()-[r]->()
                WITH node_count, count(r) as relationship_count
                RETURN node_count, relationship_count
            """,
                timeout=2.0,
            )

            return {
                "status": "healthy",
                "timestamp": result[0]["timestamp"],
                "node_count": stats[0]["node_count"] if stats else 0,
                "relationship_count": stats[0]["relationship_count"] if stats else 0,
                "average_query_time_ms": self.get_average_query_time(),
            }

        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "timestamp": None}

    def get_query_stats(self, last_n: Optional[int] = None) -> List[QueryStats]:
        """Get query statistics.

        Args:
            last_n: Return only the last N queries

        Returns:
            List of query statistics
        """
        if last_n:
            return self._query_stats[-last_n:]
        return self._query_stats.copy()

    def get_average_query_time(self) -> float:
        """Get average query execution time in milliseconds."""
        if not self._query_stats:
            return 0.0

        successful_queries = [s for s in self._query_stats if s.success]
        if not successful_queries:
            return 0.0

        return sum(s.execution_time_ms for s in successful_queries) / len(
            successful_queries
        )

    async def create_indexes(self):
        """Create all required indexes for optimal performance."""
        indexes = [
            "CREATE INDEX ON :Joker(name);",
            "CREATE INDEX ON :Joker(rarity);",
            "CREATE INDEX ON :Joker(cost);",
            "CREATE INDEX ON :PlayingCard(suit, rank);",
            "CREATE INDEX ON :HandType(name);",
            "CREATE INDEX ON :Strategy(win_rate);",
            "CREATE CONSTRAINT ON (j:Joker) ASSERT j.name IS UNIQUE;",
            "CREATE CONSTRAINT ON (h:HandType) ASSERT h.name IS UNIQUE;",
        ]

        for index_query in indexes:
            try:
                await self.execute_query(index_query)
                logger.info(f"Created index: {index_query}")
            except Exception as e:
                # Index might already exist
                logger.debug(f"Index creation skipped: {e}")

    async def load_schema(self, schema_file: str):
        """Load schema from a Cypher file.

        Args:
            schema_file: Path to the schema file
        """
        with open(schema_file, "r") as f:
            schema_content = f.read()

        # Split by semicolons and execute each statement
        statements = [s.strip() for s in schema_content.split(";") if s.strip()]

        for statement in statements:
            if statement.startswith("//") or not statement:
                continue

            try:
                await self.execute_query(statement)
                logger.info(f"Executed schema statement: {statement[:50]}...")
            except Exception as e:
                logger.error(f"Failed to execute statement: {e}")
                raise


class MemgraphConnectionPool:
    """Connection pool manager for multiple Memgraph clients."""

    def __init__(self, uri: str, pool_size: int = 5):
        self.uri = uri
        self.pool_size = pool_size
        self._clients: List[MemgraphClient] = []
        self._available: asyncio.Queue = asyncio.Queue()
        self._initialized = False

    async def initialize(self):
        """Initialize the connection pool."""
        if self._initialized:
            return

        for _ in range(self.pool_size):
            client = MemgraphClient(self.uri)
            await client.connect()
            self._clients.append(client)
            await self._available.put(client)

        self._initialized = True
        logger.info(f"Initialized connection pool with {self.pool_size} clients")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a client from the pool."""
        if not self._initialized:
            await self.initialize()

        client = await self._available.get()
        try:
            yield client
        finally:
            await self._available.put(client)

    async def close_all(self):
        """Close all connections in the pool."""
        for client in self._clients:
            await client.close()
        self._clients.clear()
        self._initialized = False


# Example usage
async def example_usage():
    """Example of using the Memgraph client."""
    client = MemgraphClient()

    try:
        # Connect to Memgraph
        await client.connect()

        # Create indexes
        await client.create_indexes()

        # Execute a simple query
        result = await client.execute_query(
            "MATCH (j:Joker) WHERE j.rarity = $rarity RETURN j.name as name",
            {"rarity": "common"},
        )

        print(f"Found {len(result)} common jokers")
        for joker in result:
            print(f"  - {joker['name']}")

        # Check health
        health = await client.check_health()
        print(f"\nDatabase health: {health}")

        # Get query statistics
        stats = client.get_query_stats()
        print(f"\nAverage query time: {client.get_average_query_time():.1f}ms")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(example_usage())
