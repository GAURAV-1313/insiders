import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from k8swhisperer.adapters.base import ClusterAdapter, LLMAdapter, NotifierAdapter
from k8swhisperer.adapters.slack_notifier import SlackNotifierAdapter
from k8swhisperer.config import Settings
from k8swhisperer.nodes.hitl import request_approval
from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState, create_initial_state
from k8swhisperer.webhook import create_webhook_app

from starlette.testclient import TestClient


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

    def test_slack_payload_uses_public_callback_urls(self):
        state: ClusterState = create_initial_state()
        state["anomalies"] = [
            {
                "type": "CrashLoopBackOff",
                "severity": "HIGH",
                "affected_resource": "payment-api-abc",
                "namespace": "production",
                "confidence": 0.95,
            }
        ]
        state["diagnosis"] = "Pod keeps exiting with code 1."
        state["plan"] = {
            "action": "restart_pod",
            "target_resource": "payment-api-abc",
            "params": {},
            "confidence": 0.91,
            "blast_radius": "low",
            "namespace": "production",
        }

        notifier = SlackNotifierAdapter(
            webhook_url="https://hooks.slack.test/services/example",
            public_base_url="https://example.ngrok-free.dev",
        )
        payload = notifier.build_payload(state)
        elements = payload["blocks"][1]["elements"]

        self.assertEqual(
            elements[0]["url"],
            f"https://example.ngrok-free.dev/webhook/slack/approve/{state['incident_id']}",
        )
        self.assertEqual(
            elements[1]["url"],
            f"https://example.ngrok-free.dev/webhook/slack/reject/{state['incident_id']}",
        )

    def test_webhook_get_routes_resume_graph(self):
        class DummyGraph:
            def __init__(self):
                self.calls = []

            def invoke(self, command, config):
                self.calls.append((command, config))
                return {"ok": True}

        graph = DummyGraph()
        app = create_webhook_app(graph)
        client = TestClient(app)

        approve_response = client.get("/webhook/slack/approve/inc-123")
        reject_response = client.get("/webhook/slack/reject/inc-456")

        self.assertEqual(approve_response.status_code, 200)
        self.assertIn("approved", approve_response.text.lower())
        self.assertEqual(reject_response.status_code, 200)
        self.assertIn("rejected", reject_response.text.lower())
        self.assertEqual(len(graph.calls), 2)
        self.assertEqual(graph.calls[0][1]["configurable"]["thread_id"], "inc-123")
        self.assertEqual(graph.calls[1][1]["configurable"]["thread_id"], "inc-456")


if __name__ == "__main__":
    unittest.main()
