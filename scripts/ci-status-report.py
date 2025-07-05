#!/usr/bin/env python3
"""
CI Status Reporter

Generates detailed CI health reports and metrics for the JimBot project.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class CIStatusReporter:
    def __init__(self):
        self.workflows = [
            "Main CI/CD Pipeline",
            "Code Quality",
            "Lua CI",
            "Rust Basic CI",
            "GPU Tests",
        ]

    def get_workflow_runs(self, workflow: str, limit: int = 20) -> List[Dict]:
        """Get recent runs for a specific workflow."""
        try:
            cmd = [
                "gh",
                "run",
                "list",
                f"--workflow={workflow}",
                f"--limit={limit}",
                "--json=conclusion,createdAt,workflowName,status,url",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError:
            return []

    def calculate_success_rate(self, runs: List[Dict], hours: int = 24) -> Dict:
        """Calculate success rate for runs within the specified time window."""
        cutoff = datetime.now() - timedelta(hours=hours)

        recent_runs = [
            run
            for run in runs
            if datetime.fromisoformat(run["createdAt"].replace("Z", "+00:00")) > cutoff
        ]

        if not recent_runs:
            return {"total": 0, "successful": 0, "rate": 100}

        successful = len([r for r in recent_runs if r["conclusion"] == "success"])
        total = len(recent_runs)
        rate = (successful / total * 100) if total > 0 else 100

        return {"total": total, "successful": successful, "rate": round(rate, 1)}

    def get_health_status(self, rate: float) -> str:
        """Determine health status based on success rate."""
        if rate >= 80:
            return "healthy"
        elif rate >= 50:
            return "degraded"
        else:
            return "unhealthy"

    def generate_report(self) -> Dict:
        """Generate comprehensive CI status report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "workflows": {},
            "overall": {"total": 0, "successful": 0, "rate": 0},
        }

        total_runs = 0
        total_successful = 0

        for workflow in self.workflows:
            runs = self.get_workflow_runs(workflow)
            stats = self.calculate_success_rate(runs)

            report["workflows"][workflow] = {
                "stats": stats,
                "status": self.get_health_status(stats["rate"]),
                "recent_failures": [
                    {"url": r["url"], "created": r["createdAt"]}
                    for r in runs[:5]
                    if r["conclusion"] == "failure"
                ],
            }

            total_runs += stats["total"]
            total_successful += stats["successful"]

        if total_runs > 0:
            overall_rate = total_successful / total_runs * 100
        else:
            overall_rate = 100

        report["overall"] = {
            "total": total_runs,
            "successful": total_successful,
            "rate": round(overall_rate, 1),
            "status": self.get_health_status(overall_rate),
        }

        return report

    def print_report(self, report: Dict):
        """Print formatted CI status report."""
        print("=" * 60)
        print("CI HEALTH REPORT")
        print("=" * 60)
        print(f"Generated: {report['timestamp']}")
        print(f"Overall Status: {report['overall']['status'].upper()}")
        print(
            f"Success Rate: {report['overall']['rate']}% ({report['overall']['successful']}/{report['overall']['total']} runs)"
        )
        print()

        print("WORKFLOW DETAILS:")
        print("-" * 40)

        for workflow, data in report["workflows"].items():
            stats = data["stats"]
            status = data["status"]

            status_icon = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌"}.get(
                status, "❓"
            )

            print(f"{status_icon} {workflow}")
            print(f"   Rate: {stats['rate']}% ({stats['successful']}/{stats['total']})")

            if data["recent_failures"]:
                print(f"   Recent failures: {len(data['recent_failures'])}")

        print()

        if report["overall"]["rate"] < 70:
            print("⚠️  WARNING: CI health is below acceptable threshold!")
            print(
                "   Consider investigating recent failures and infrastructure issues."
            )

    def create_badge_data(self, report: Dict) -> Dict:
        """Create badge data for shields.io endpoint."""
        rate = report["overall"]["rate"]
        status = report["overall"]["status"]

        color_map = {"healthy": "green", "degraded": "yellow", "unhealthy": "red"}

        return {
            "schemaVersion": 1,
            "label": "CI Health",
            "message": f"{rate}% ({status})",
            "color": color_map.get(status, "gray"),
        }


def main():
    """Main entry point."""
    reporter = CIStatusReporter()

    print("Generating CI status report...")
    report = reporter.generate_report()

    # Print human-readable report
    reporter.print_report(report)

    # Save badge data
    badge_data = reporter.create_badge_data(report)

    try:
        import os

        os.makedirs(".github/badges", exist_ok=True)

        with open(".github/badges/ci-health.json", "w") as f:
            json.dump(badge_data, f, indent=2)

        print(f"\n✅ Badge data saved to .github/badges/ci-health.json")

    except Exception as e:
        print(f"❌ Failed to save badge data: {e}")

    # Save full report
    try:
        with open("ci-health-report.json", "w") as f:
            json.dump(report, f, indent=2)

        print(f"✅ Full report saved to ci-health-report.json")

    except Exception as e:
        print(f"❌ Failed to save report: {e}")


if __name__ == "__main__":
    main()
