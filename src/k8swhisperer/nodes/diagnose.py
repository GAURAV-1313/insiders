"""Diagnose stage implementation."""

from __future__ import annotations

from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState


def run(state: ClusterState, runtime: Runtime) -> ClusterState:
    runtime.log("[diagnose] gathering evidence")
    if not state.get("anomalies"):
        state["diagnosis"] = "No anomalies detected."
        return state

    anomaly = state["anomalies"][0]
    resource = anomaly["affected_resource"]
    namespace = anomaly.get("namespace", "default")
    logs = runtime.cluster.get_pod_logs(resource, namespace)
    description = runtime.cluster.describe_pod(resource, namespace)
    state["diagnosis"] = runtime.llm.diagnose(anomaly, logs, description, state.get("events", []))
    return state

