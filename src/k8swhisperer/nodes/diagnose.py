"""Diagnose stage implementation."""

from __future__ import annotations

from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState


def run(state: ClusterState, runtime: Runtime) -> ClusterState:
    if not state.get("anomalies"):
        state["diagnosis"] = "No anomalies detected."
        return state

    anomaly = state["anomalies"][0]
    resource = anomaly["affected_resource"]
    namespace = anomaly.get("namespace", "default")
    anomaly_type = anomaly.get("type", "")

    # DeploymentStalled and NodeNotReady use deployment/node names, not pod names
    # — skip pod-level log/describe fetching for these types
    if anomaly_type in ("DeploymentStalled", "NodeNotReady"):
        runtime.log(f"[diagnose] {anomaly_type} on {resource} — using event-based diagnosis")
        logs = ""
        description = ""
    else:
        runtime.log(f"[diagnose] fetching logs and describe for {resource}")
        try:
            logs = runtime.cluster.get_pod_logs(resource, namespace)
        except Exception:
            logs = ""
        try:
            description = runtime.cluster.describe_pod(resource, namespace)
        except Exception:
            description = ""

    state["diagnosis"] = runtime.llm.diagnose(anomaly, logs, description, state.get("events", []))
    runtime.log(f"[diagnose] root cause: {state['diagnosis']}")
    return state

