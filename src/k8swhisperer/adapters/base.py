"""Protocol contracts for Person 1 and Person 3 integrations."""

from __future__ import annotations

from typing import Any, Dict, List, Protocol

from k8swhisperer.state import Anomaly, ClusterState, RemediationPlan


class ClusterAdapter(Protocol):
    def scan_cluster(self) -> List[Dict[str, Any]]:
        ...

    def get_pod_logs(self, resource_name: str, namespace: str, tail_lines: int = 100) -> str:
        ...

    def describe_pod(self, resource_name: str, namespace: str) -> str:
        ...

    def restart_pod(self, resource_name: str, namespace: str) -> str:
        ...

    def patch_memory_limit(self, resource_name: str, namespace: str, memory_limit: str) -> str:
        ...

    def delete_pod(self, pod_name: str, namespace: str) -> str:
        ...

    def get_resource_state(self, resource_name: str, namespace: str) -> Dict[str, Any]:
        ...

    def patch_cpu_limit(self, pod_name: str, namespace: str, cpu_limit: str) -> str:
        ...

    def scan_deployments(self, namespace: str) -> List[Dict[str, Any]]:
        ...

    def scan_nodes(self) -> List[Dict[str, Any]]:
        ...

    def get_node_status(self, node_name: str) -> Dict[str, Any]:
        ...


class LLMAdapter(Protocol):
    def classify(self, events: List[Dict[str, Any]]) -> List[Anomaly]:
        ...

    def diagnose(self, anomaly: Anomaly, logs: str, description: str, events: List[Dict[str, Any]]) -> str:
        ...

    def plan(self, anomaly: Anomaly, diagnosis: str) -> RemediationPlan:
        ...

    def explain(self, state: ClusterState) -> str:
        ...


class NotifierAdapter(Protocol):
    def send_hitl_request(self, state: ClusterState) -> Dict[str, Any]:
        ...

