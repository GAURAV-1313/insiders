"""Development fixtures for local graph scaffolding."""

from __future__ import annotations

from typing import Any, Dict, List

from k8swhisperer.adapters.base import ClusterAdapter, LLMAdapter, NotifierAdapter
from k8swhisperer.state import Anomaly, ClusterState, RemediationPlan


class FixtureClusterAdapter(ClusterAdapter):
    def scan_cluster(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "payment-api-7c4f9",
                "namespace": "production",
                "phase": "CrashLoopBackOff",
                "restart_count": 5,
                "reason": "BackOff",
            }
        ]

    def get_pod_logs(self, resource_name: str, namespace: str, tail_lines: int = 100) -> str:
        return (
            "ERROR database connection refused at 10.0.0.9:5432\n"
            "ERROR retry budget exhausted\n"
            "FATAL startup failed\n"
        )

    def describe_pod(self, resource_name: str, namespace: str) -> str:
        return (
            f"Name: {resource_name}\n"
            f"Namespace: {namespace}\n"
            "Status: CrashLoopBackOff\n"
            "Last State: Terminated\n"
            "Exit Code: 1\n"
        )

    def restart_pod(self, resource_name: str, namespace: str) -> str:
        return f"pod/{resource_name} deleted"

    def patch_memory_limit(self, resource_name: str, namespace: str, memory_limit: str) -> str:
        return f"deployment/{resource_name} patched with memory={memory_limit}"

    def delete_pod(self, pod_name: str, namespace: str) -> str:
        return f"pod/{pod_name} deleted"

    def get_resource_state(self, resource_name: str, namespace: str) -> Dict[str, Any]:
        return {"phase": "Running", "restart_count": 0}

    def patch_cpu_limit(self, pod_name: str, namespace: str, cpu_limit: str) -> str:
        return f"deployment/{pod_name} patched with cpu={cpu_limit}"

    def scan_deployments(self, namespace: str) -> List[Dict[str, Any]]:
        return []

    def scan_nodes(self) -> List[Dict[str, Any]]:
        return []

    def get_node_status(self, node_name: str) -> Dict[str, Any]:
        return {"conditions": [], "describe": f"Node {node_name} fixture"}


class FixtureLLMAdapter(LLMAdapter):
    def classify(self, events: List[Dict[str, Any]]) -> List[Anomaly]:
        resource = events[0]["name"] if events else "unknown"
        return [
            Anomaly(
                type="CrashLoopBackOff",
                severity="HIGH",
                affected_resource=resource,
                confidence=0.91,
                namespace="production",
                evidence=["restart_count > 3", "phase CrashLoopBackOff"],
            )
        ]

    def diagnose(self, anomaly: Anomaly, logs: str, description: str, events: List[Dict[str, Any]]) -> str:
        return (
            "Pod is crash looping during startup. Logs show database connection refused and repeated "
            "retry exhaustion. Treat as transient for the first attempt and restart the pod."
        )

    def plan(self, anomaly: Anomaly, diagnosis: str) -> RemediationPlan:
        return RemediationPlan(
            action="restart_pod",
            target_resource=anomaly["affected_resource"],
            namespace=anomaly.get("namespace", "default"),
            params={},
            confidence=0.91,
            blast_radius="low",
            reason=diagnosis,
        )

    def explain(self, state: ClusterState) -> str:
        anomaly = state["anomalies"][0] if state.get("anomalies") else {}
        resource = anomaly.get("affected_resource", "unknown")
        return (
            f"Incident {state['incident_id']} affected {resource}. "
            f"Diagnosis: {state.get('diagnosis', 'n/a')} "
            f"Result: {state.get('result', 'n/a')}"
        )


class FixtureNotifierAdapter(NotifierAdapter):
    def send_hitl_request(self, state: ClusterState) -> Dict[str, Any]:
        return {
            "incident_id": state["incident_id"],
            "status": "sent",
            "message": "Approval request would be sent to Slack here.",
        }

