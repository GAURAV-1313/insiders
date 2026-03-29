import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from k8swhisperer.adapters.base import ClusterAdapter, LLMAdapter, NotifierAdapter
from k8swhisperer.config import Settings
from k8swhisperer.nodes.hitl import request_approval
from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState, create_initial_state


class EmptyClusterAdapter(ClusterAdapter):
    def scan_cluster(self):
        return []

    def get_pod_logs(self, resource_name, namespace, tail_lines=100):
        return ""

    def describe_pod(self, resource_name, namespace):
        return ""

    def restart_pod(self, resource_name, namespace):
        return ""

    def patch_memory_limit(self, resource_name, namespace, memory_limit):
        return ""

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


class CountingNotifier(NotifierAdapter):
    def __init__(self):
        self.calls = 0

    def send_hitl_request(self, state):
        self.calls += 1
        return {"incident_id": state["incident_id"]}


class HitlTests(unittest.TestCase):
    def test_request_approval_only_sends_once(self):
        notifier = CountingNotifier()
        runtime = Runtime(
            cluster=EmptyClusterAdapter(),
            llm=EmptyLLMAdapter(),
            notifier=notifier,
            settings=Settings(),
            sleep=lambda _: None,
            log=lambda _: None,
        )
        state: ClusterState = create_initial_state()
        state = request_approval(state, runtime)
        state = request_approval(state, runtime)

        self.assertEqual(notifier.calls, 1)
        self.assertTrue(state["approval_requested"])
        self.assertEqual(state["execution_status"], "awaiting_approval")


if __name__ == "__main__":
    unittest.main()
