import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from k8swhisperer.adapters.base import ClusterAdapter, LLMAdapter, NotifierAdapter
from k8swhisperer.config import Settings
from k8swhisperer.nodes.execute import verify_resolution
from k8swhisperer.runtime import Runtime


class SequenceClusterAdapter(ClusterAdapter):
    def __init__(self, states):
        self.states = list(states)
        self.index = 0

    def scan_cluster(self):
        return []

    def get_pod_logs(self, resource_name, namespace, tail_lines=100):
        return ""

    def describe_pod(self, resource_name, namespace):
        return ""

    def restart_pod(self, resource_name, namespace):
        return "ok"

    def patch_memory_limit(self, resource_name, namespace, memory_limit):
        return "ok"

    def get_resource_state(self, resource_name, namespace):
        state = self.states[min(self.index, len(self.states) - 1)]
        self.index += 1
        return state


class DeploymentSequenceClusterAdapter(ClusterAdapter):
    def __init__(self, pod_sequences):
        self.pod_sequences = list(pod_sequences)
        self.index = 0

    def scan_cluster(self):
        pods = self.pod_sequences[min(self.index, len(self.pod_sequences) - 1)]
        self.index += 1
        return pods

    def get_pod_logs(self, resource_name, namespace, tail_lines=100):
        return ""

    def describe_pod(self, resource_name, namespace):
        return ""

    def restart_pod(self, resource_name, namespace):
        return "ok"

    def patch_memory_limit(self, resource_name, namespace, memory_limit):
        return "ok"

    def get_resource_state(self, resource_name, namespace):
        return {}


class EmptyLLMAdapter(LLMAdapter):
    def classify(self, events):
        return []

    def diagnose(self, anomaly, logs, description, events):
        return ""

    def plan(self, anomaly, diagnosis):
        return {}

    def explain(self, state):
        return ""


class EmptyNotifierAdapter(NotifierAdapter):
    def send_hitl_request(self, state):
        return {}


class ExecuteVerificationTests(unittest.TestCase):
    def test_running_zero_restarts_counts_as_fixed(self):
        runtime = Runtime(
            cluster=SequenceClusterAdapter(
                [
                    {"phase": "ContainerCreating", "restart_count": 0},
                    {"phase": "Running", "restart_count": 0},
                ]
            ),
            llm=EmptyLLMAdapter(),
            notifier=EmptyNotifierAdapter(),
            settings=Settings().copy_with_backoff((0, 0)),
            sleep=lambda _: None,
            log=lambda _: None,
        )

        verified, latest_state = verify_resolution(runtime, "payment-api", "production", sleep=lambda _: None)
        self.assertTrue(verified)
        self.assertEqual(latest_state["phase"], "Running")

    def test_restarting_or_crashing_never_counts_as_fixed(self):
        runtime = Runtime(
            cluster=SequenceClusterAdapter(
                [
                    {"phase": "ContainerCreating", "restart_count": 0},
                    {"phase": "CrashLoopBackOff", "restart_count": 1},
                ]
            ),
            llm=EmptyLLMAdapter(),
            notifier=EmptyNotifierAdapter(),
            settings=Settings().copy_with_backoff((0, 0)),
            sleep=lambda _: None,
            log=lambda _: None,
        )

        verified, latest_state = verify_resolution(runtime, "payment-api", "production", sleep=lambda _: None)
        self.assertFalse(verified)
        self.assertEqual(latest_state["phase"], "CrashLoopBackOff")

    def test_deployment_requires_two_consecutive_healthy_observations(self):
        runtime = Runtime(
            cluster=DeploymentSequenceClusterAdapter(
                [
                    [{"pod_name": "payment-api-1", "namespace": "production", "status": "Running", "restart_count": 0}],
                    [{"pod_name": "payment-api-1", "namespace": "production", "status": "Running", "restart_count": 0}],
                ]
            ),
            llm=EmptyLLMAdapter(),
            notifier=EmptyNotifierAdapter(),
            settings=Settings().copy_with_backoff((0, 0)),
            sleep=lambda _: None,
            log=lambda _: None,
        )

        verified, latest_state = verify_resolution(
            runtime,
            "payment-api-abc",
            "production",
            deployment_name="payment-api",
            sleep=lambda _: None,
        )
        self.assertTrue(verified)
        self.assertEqual(latest_state["pods"][0]["status"], "Running")

    def test_deployment_transient_running_then_error_does_not_false_pass(self):
        runtime = Runtime(
            cluster=DeploymentSequenceClusterAdapter(
                [
                    [{"pod_name": "payment-api-1", "namespace": "production", "status": "Running", "restart_count": 0}],
                    [{"pod_name": "payment-api-1", "namespace": "production", "status": "Error", "restart_count": 1}],
                ]
            ),
            llm=EmptyLLMAdapter(),
            notifier=EmptyNotifierAdapter(),
            settings=Settings().copy_with_backoff((0, 0)),
            sleep=lambda _: None,
            log=lambda _: None,
        )

        verified, latest_state = verify_resolution(
            runtime,
            "payment-api-abc",
            "production",
            deployment_name="payment-api",
            sleep=lambda _: None,
        )
        self.assertFalse(verified)
        self.assertEqual(latest_state["pods"][0]["status"], "Error")


if __name__ == "__main__":
    unittest.main()
