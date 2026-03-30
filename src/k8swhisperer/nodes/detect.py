"""Detect stage implementation."""

from __future__ import annotations

from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState


def run(state: ClusterState, runtime: Runtime) -> ClusterState:
    if state.get("anomalies"):
        # Anomalies pre-classified by multi-anomaly dispatch — skip LLM re-classify
        runtime.log(f"[detect] using pre-classified anomaly: {state['anomalies'][0].get('type')} on {state['anomalies'][0].get('affected_resource')}")
        return state
    runtime.log("[detect] classifying anomalies")
    state["anomalies"] = runtime.llm.classify(state.get("events", []))
    return state

