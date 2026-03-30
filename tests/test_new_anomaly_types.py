"""Tests for the three new anomaly types: CPUThrottling, DeploymentStalled, NodeNotReady."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from k8swhisperer.adapters.openai_compatible_llm import OpenAICompatibleLLMAdapter
from k8swhisperer.config import Settings
from k8swhisperer.nodes.safety_gate import determine_route
from k8swhisperer.runtime import Runtime
from k8swhisperer.state import Anomaly, ClusterState, RemediationPlan


def _make_runtime(**overrides):
    rt = MagicMock(spec=Runtime)
    settings = Settings(**overrides) if overrides else Settings()
    rt.settings = settings
    rt.log = MagicMock()
    return rt


# ---------------------------------------------------------------------------
# CPUThrottling
# ---------------------------------------------------------------------------

class TestCPUThrottlingClassification(unittest.TestCase):
    def test_classify_from_status_detects_cpu_throttling(self):
        adapter = OpenAICompatibleLLMAdapter.__new__(OpenAICompatibleLLMAdapter)
        events = [
            {"pod_name": "web-abc", "namespace": "production", "status": "Running",
             "restart_count": 0, "exit_code": None, "cpu_throttled_ratio": 0.7},
        ]
        result = adapter._classify_from_status(events)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "CPUThrottling")
        self.assertEqual(result[0]["severity"], "MED")

    def test_cpu_throttled_below_threshold_ignored(self):
        adapter = OpenAICompatibleLLMAdapter.__new__(OpenAICompatibleLLMAdapter)
        events = [
            {"pod_name": "web-abc", "namespace": "production", "status": "Running",
             "restart_count": 0, "exit_code": None, "cpu_throttled_ratio": 0.3},
        ]
        result = adapter._classify_from_status(events)
        self.assertEqual(len(result), 0)


class TestCPUThrottlingPlan(unittest.TestCase):
    def test_fallback_plan_returns_patch_cpu_limit(self):
        adapter = OpenAICompatibleLLMAdapter.__new__(OpenAICompatibleLLMAdapter)
        anomaly = Anomaly(type="CPUThrottling", severity="MED",
                          affected_resource="web-abc", namespace="production", confidence=0.90)
        plan = adapter._fallback_plan(anomaly)
        self.assertEqual(plan["action"], "patch_cpu_limit")
        self.assertEqual(plan["blast_radius"], "medium")
        self.assertIn("cpu_limit", plan["params"])


class TestCPUThrottlingSafetyGate(unittest.TestCase):
    def test_cpu_throttling_routes_to_hitl(self):
        """patch_cpu_limit with blast_radius=medium routes to HITL (rolling restart risk)."""
        runtime = _make_runtime()
        plan = RemediationPlan(
            action="patch_cpu_limit", confidence=0.90, blast_radius="medium",
            target_resource="web-abc", namespace="production", params={"cpu_limit": "500m"},
        )
        route = determine_route(plan, runtime)
        self.assertEqual(route, "hitl")


class TestExtractCpuLimit(unittest.TestCase):
    def test_extracts_and_increases(self):
        result = OpenAICompatibleLLMAdapter._extract_cpu_limit("current cpu limit is 250m")
        self.assertEqual(result, "375m")

    def test_default_when_no_match(self):
        result = OpenAICompatibleLLMAdapter._extract_cpu_limit("no cpu info here")
        self.assertEqual(result, "500m")


# ---------------------------------------------------------------------------
# DeploymentStalled
# ---------------------------------------------------------------------------

class TestDeploymentStalledClassification(unittest.TestCase):
    def test_classify_from_status_detects_stalled(self):
        adapter = OpenAICompatibleLLMAdapter.__new__(OpenAICompatibleLLMAdapter)
        events = [
            {"kind": "deployment", "resource_name": "stalled-deploy", "namespace": "production",
             "stalled": True, "replicas": 2, "updatedReplicas": 0},
        ]
        result = adapter._classify_from_status(events)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "DeploymentStalled")
        self.assertEqual(result[0]["severity"], "HIGH")

    def test_healthy_deployment_not_flagged(self):
        adapter = OpenAICompatibleLLMAdapter.__new__(OpenAICompatibleLLMAdapter)
        events = [
            {"kind": "deployment", "resource_name": "healthy-deploy", "namespace": "production",
             "stalled": False, "replicas": 2, "updatedReplicas": 2},
        ]
        result = adapter._classify_from_status(events)
        self.assertEqual(len(result), 0)


class TestDeploymentStalledPlan(unittest.TestCase):
    def test_fallback_plan_returns_rollback(self):
        adapter = OpenAICompatibleLLMAdapter.__new__(OpenAICompatibleLLMAdapter)
        anomaly = Anomaly(type="DeploymentStalled", severity="HIGH",
                          affected_resource="stalled-deploy", namespace="production", confidence=0.85)
        plan = adapter._fallback_plan(anomaly)
        self.assertEqual(plan["action"], "rollback_deployment")
        self.assertEqual(plan["blast_radius"], "high")


class TestDeploymentStalledSafetyGate(unittest.TestCase):
    def test_rollback_deployment_routes_to_hitl(self):
        """rollback_deployment is NOT in ALLOWED_V1_ACTIONS → HITL required."""
        runtime = _make_runtime()
        plan = RemediationPlan(
            action="rollback_deployment", confidence=0.90, blast_radius="high",
            target_resource="stalled-deploy", namespace="production", params={},
        )
        route = determine_route(plan, runtime)
        self.assertEqual(route, "hitl")


# ---------------------------------------------------------------------------
# NodeNotReady
# ---------------------------------------------------------------------------

class TestNodeNotReadyClassification(unittest.TestCase):
    def test_classify_from_status_detects_node_notready(self):
        adapter = OpenAICompatibleLLMAdapter.__new__(OpenAICompatibleLLMAdapter)
        events = [
            {"kind": "node", "resource_name": "minikube", "namespace": "",
             "node_ready": False},
        ]
        result = adapter._classify_from_status(events)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "NodeNotReady")
        self.assertEqual(result[0]["severity"], "CRITICAL")

    def test_ready_node_not_flagged(self):
        adapter = OpenAICompatibleLLMAdapter.__new__(OpenAICompatibleLLMAdapter)
        events = [
            {"kind": "node", "resource_name": "minikube", "namespace": "",
             "node_ready": True},
        ]
        result = adapter._classify_from_status(events)
        self.assertEqual(len(result), 0)


class TestNodeNotReadyPlan(unittest.TestCase):
    def test_fallback_plan_returns_log_node_metrics(self):
        adapter = OpenAICompatibleLLMAdapter.__new__(OpenAICompatibleLLMAdapter)
        anomaly = Anomaly(type="NodeNotReady", severity="CRITICAL",
                          affected_resource="minikube", namespace="", confidence=0.80)
        plan = adapter._fallback_plan(anomaly)
        self.assertEqual(plan["action"], "log_node_metrics")
        self.assertEqual(plan["blast_radius"], "high")


class TestNodeNotReadySafetyGate(unittest.TestCase):
    def test_node_notready_always_hitl_even_with_high_confidence_low_blast(self):
        """NodeNotReady must ALWAYS route to HITL regardless of confidence/blast_radius.
        This is the key safety differentiator — never auto-drain a node."""
        runtime = _make_runtime()
        # Even if someone crafted a low-blast, high-confidence plan, the anomaly type overrides
        plan = RemediationPlan(
            action="log_node_metrics", confidence=1.0, blast_radius="low",
            target_resource="minikube", namespace="", params={},
        )
        state = ClusterState(
            incident_id="test",
            anomalies=[Anomaly(type="NodeNotReady", severity="CRITICAL",
                               affected_resource="minikube", namespace="", confidence=0.99)],
        )
        route = determine_route(plan, runtime, state)
        self.assertEqual(route, "hitl")

    def test_node_notready_hitl_overrides_allowed_actions(self):
        """Even if log_node_metrics were somehow in allowed_v1_actions, NodeNotReady still goes to HITL."""
        runtime = _make_runtime()
        plan = RemediationPlan(
            action="explain_only", confidence=0.99, blast_radius="low",
            target_resource="minikube", namespace="", params={},
        )
        state = ClusterState(
            incident_id="test",
            anomalies=[Anomaly(type="NodeNotReady", severity="CRITICAL",
                               affected_resource="minikube", namespace="", confidence=0.99)],
        )
        route = determine_route(plan, runtime, state)
        self.assertEqual(route, "hitl")


# ---------------------------------------------------------------------------
# Confidence normalization for new types
# ---------------------------------------------------------------------------

class TestConfidenceNormalizationNewTypes(unittest.TestCase):
    def setUp(self):
        self.adapter = OpenAICompatibleLLMAdapter.__new__(OpenAICompatibleLLMAdapter)

    def test_cpu_throttling_floor(self):
        event = {"cpu_throttled_ratio": 0.7}
        result = self.adapter._normalize_confidence("CPUThrottling", 0.5, event)
        self.assertGreaterEqual(result, 0.90)

    def test_deployment_stalled_floor(self):
        event = {"stalled": True}
        result = self.adapter._normalize_confidence("DeploymentStalled", 0.5, event)
        self.assertGreaterEqual(result, 0.92)

    def test_node_notready_floor(self):
        event = {"node_ready": False}
        result = self.adapter._normalize_confidence("NodeNotReady", 0.5, event)
        self.assertGreaterEqual(result, 0.99)


# ---------------------------------------------------------------------------
# Fallback diagnosis for new types
# ---------------------------------------------------------------------------

class TestFallbackDiagnosisNewTypes(unittest.TestCase):
    def setUp(self):
        self.adapter = OpenAICompatibleLLMAdapter.__new__(OpenAICompatibleLLMAdapter)

    def test_cpu_throttling_diagnosis(self):
        anomaly = Anomaly(type="CPUThrottling", severity="MED",
                          affected_resource="web-abc", namespace="production", confidence=0.9)
        result = self.adapter._fallback_diagnosis(anomaly)
        self.assertIn("CPU", result)

    def test_deployment_stalled_diagnosis(self):
        anomaly = Anomaly(type="DeploymentStalled", severity="HIGH",
                          affected_resource="stalled-deploy", namespace="production", confidence=0.85)
        result = self.adapter._fallback_diagnosis(anomaly)
        self.assertIn("stalled", result)

    def test_node_notready_diagnosis(self):
        anomaly = Anomaly(type="NodeNotReady", severity="CRITICAL",
                          affected_resource="minikube", namespace="", confidence=0.99)
        result = self.adapter._fallback_diagnosis(anomaly)
        self.assertIn("NotReady", result)


if __name__ == "__main__":
    unittest.main()
