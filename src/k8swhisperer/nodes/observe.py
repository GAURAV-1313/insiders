"""Observe stage implementation."""

from __future__ import annotations

from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState


def run(state: ClusterState, runtime: Runtime) -> ClusterState:
    runtime.log("[observe] scanning cluster")
    state["events"] = runtime.cluster.scan_cluster()
    return state

