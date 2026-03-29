import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from k8swhisperer.adapters.fixtures import FixtureClusterAdapter, FixtureLLMAdapter, FixtureNotifierAdapter
from k8swhisperer.config import Settings
from k8swhisperer.nodes.safety_gate import determine_route
from k8swhisperer.runtime import Runtime
from k8swhisperer.state import RemediationPlan


class SafetyGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = Runtime(
            cluster=FixtureClusterAdapter(),
            llm=FixtureLLMAdapter(),
            notifier=FixtureNotifierAdapter(),
            settings=Settings(),
            sleep=lambda _: None,
            log=lambda _: None,
        )

    def test_low_risk_high_confidence_non_destructive_routes_to_execute(self) -> None:
        plan = RemediationPlan(
            action="restart_pod",
            target_resource="payment-api",
            params={},
            confidence=0.91,
            blast_radius="low",
            namespace="production",
        )
        self.assertEqual(determine_route(plan, self.runtime), "execute")

    def test_medium_risk_routes_to_hitl(self) -> None:
        plan = RemediationPlan(
            action="restart_pod",
            target_resource="payment-api",
            params={},
            confidence=0.91,
            blast_radius="medium",
            namespace="production",
        )
        self.assertEqual(determine_route(plan, self.runtime), "hitl")

    def test_low_confidence_routes_to_hitl(self) -> None:
        plan = RemediationPlan(
            action="restart_pod",
            target_resource="payment-api",
            params={},
            confidence=0.8,
            blast_radius="low",
            namespace="production",
        )
        self.assertEqual(determine_route(plan, self.runtime), "hitl")

    def test_destructive_action_routes_to_hitl(self) -> None:
        plan = RemediationPlan(
            action="delete_deployment",
            target_resource="payment-api",
            params={},
            confidence=0.99,
            blast_radius="low",
            namespace="production",
        )
        self.assertEqual(determine_route(plan, self.runtime), "hitl")


if __name__ == "__main__":
    unittest.main()
