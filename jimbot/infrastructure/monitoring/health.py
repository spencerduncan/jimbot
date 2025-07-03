"""Health Check Module

Provides health checking for all components.
"""

from typing import Dict, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio
import time


class HealthStatus(Enum):
    """Health status levels"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a health check"""

    component: str
    status: HealthStatus
    message: str
    metrics: Dict[str, float]
    timestamp: float


class HealthChecker:
    """Manages health checks for all components"""

    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.results: Dict[str, HealthCheckResult] = {}

    def register_check(self, component: str, check_func: Callable):
        """Register a health check function"""
        self.checks[component] = check_func

    async def run_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks"""
        tasks = {}
        for component, check_func in self.checks.items():
            tasks[component] = asyncio.create_task(
                self._run_check(component, check_func)
            )

        # Wait for all checks
        for component, task in tasks.items():
            try:
                self.results[component] = await task
            except Exception as e:
                self.results[component] = HealthCheckResult(
                    component=component,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(e)}",
                    metrics={},
                    timestamp=time.time(),
                )

        return self.results

    async def _run_check(
        self, component: str, check_func: Callable
    ) -> HealthCheckResult:
        """Run a single health check"""
        result = await check_func()
        return HealthCheckResult(
            component=component,
            status=result.get("status", HealthStatus.UNHEALTHY),
            message=result.get("message", ""),
            metrics=result.get("metrics", {}),
            timestamp=time.time(),
        )
