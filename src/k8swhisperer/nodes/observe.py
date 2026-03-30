"""Observe stage implementation.

Scans three resource types in parallel:
1. Pods — CrashLoopBackOff, OOMKilled, Pending, ImagePullBackOff, Evicted
2. Deployments — DeploymentStalled (updatedReplicas != replicas)
3. Nodes — NodeNotReady (conditions[Ready] = False)

Each event is tagged with a 'kind' field ('pod', 'deployment', 'node')
so the detect stage can apply type-specific classification rules.
"""

from __future__ import annotations

import logging

from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState

logger = logging.getLogger(__name__)


def run(state: ClusterState, runtime: Runtime) -> ClusterState:
    if state.get("events"):
        # Events pre-injected by multi-anomaly dispatch — skip re-scan to avoid duplicate work
        runtime.log(f"[observe] using {len(state['events'])} pre-scanned event(s)")
        return state
    runtime.log("[observe] scanning cluster")
    pod_events = runtime.cluster.scan_cluster()
    # Tag pod events with kind for unified classification
    for event in pod_events:
        event.setdefault("kind", "pod")

    all_events = list(pod_events)

    # Scan deployments for DeploymentStalled detection
    try:
        deploy_events = runtime.cluster.scan_deployments(runtime.cluster.namespace)
        all_events.extend(deploy_events)
    except Exception as exc:
        logger.debug("[observe] deployment scan skipped: %s", exc)

    # Scan nodes for NodeNotReady detection
    try:
        node_events = runtime.cluster.scan_nodes()
        all_events.extend(node_events)
    except Exception as exc:
        logger.debug("[observe] node scan skipped: %s", exc)

    state["events"] = all_events
    return state

