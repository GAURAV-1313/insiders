"""Detect stage implementation."""

from __future__ import annotations

from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState


def run(state: ClusterState, runtime: Runtime) -> ClusterState:
    runtime.log("[detect] classifying anomalies")
    state["anomalies"] = runtime.llm.classify(state.get("events", []))
    return state

