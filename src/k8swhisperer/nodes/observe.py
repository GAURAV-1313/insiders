"""Observe stage implementation."""

from __future__ import annotations

from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState


def run(state: ClusterState, runtime: Runtime) -> ClusterState:
    if state.get("events"):
        # Events pre-injected by multi-anomaly dispatch — skip re-scan to avoid duplicate work
        runtime.log(f"[observe] using {len(state['events'])} pre-scanned event(s)")
        return state
    runtime.log("[observe] scanning cluster")
    state["events"] = runtime.cluster.scan_cluster()
    return state

