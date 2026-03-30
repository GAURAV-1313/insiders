"""K8sWhisperer MCP server — exposes kubectl tools to Claude Desktop / any MCP client.

Run:
    python src/k8swhisperer/mcp_server.py          # stdio transport (Claude Desktop)
    mcp dev src/k8swhisperer/mcp_server.py         # interactive dev mode with inspector
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from mcp.server.fastmcp import FastMCP

from k8swhisperer.bootstrap import build_runtime_from_env

mcp = FastMCP(
    "k8swhisperer",
    instructions=(
        "You are connected to a live Kubernetes cluster via K8sWhisperer. "
        "Use scan_cluster to find broken pods, get_pod_logs and describe_pod to diagnose them, "
        "then restart_pod, patch_memory_limit, or delete_evicted_pod to fix them. "
        "Always scan first, then diagnose, then act. "
        "Use get_audit_log to review previous incidents and their outcomes."
    ),
)

_runtime = None


def _get_runtime():
    global _runtime
    if _runtime is None:
        _runtime = build_runtime_from_env()
    return _runtime


@mcp.tool()
def scan_cluster() -> list[dict]:
    """Scan the production Kubernetes namespace for anomalous pods.

    Returns a list of pod objects, each containing:
    - pod_name: full pod name including replica hash
    - namespace: always 'production' for this cluster
    - status: e.g. CrashLoopBackOff, OOMKilled, ImagePullBackOff, Evicted, Running, Pending
    - restart_count: number of container restarts
    - exit_code: last container exit code (None if still running)
    """
    return _get_runtime().cluster.scan_cluster()


@mcp.tool()
def get_pod_logs(pod_name: str, namespace: str = "production") -> str:
    """Fetch recent logs from a pod, filtered for errors and warnings.

    Use after scan_cluster identifies a CrashLoopBackOff or OOMKilled pod.
    Returns up to 60 lines, prioritising ERROR/FATAL/WARN/EXCEPTION lines.

    Args:
        pod_name: exact pod name from scan_cluster
        namespace: Kubernetes namespace (default: production)
    """
    return _get_runtime().cluster.get_pod_logs(pod_name, namespace)


@mcp.tool()
def describe_pod(pod_name: str, namespace: str = "production") -> str:
    """Run kubectl describe on a pod and return full output.

    Shows events, resource limits, container states, restart history, and owner references.
    Useful for diagnosing ImagePullBackOff, Pending, and OOMKilled pods.

    Args:
        pod_name: exact pod name from scan_cluster
        namespace: Kubernetes namespace (default: production)
    """
    return _get_runtime().cluster.describe_pod(pod_name, namespace)


@mcp.tool()
def restart_pod(pod_name: str, namespace: str = "production") -> str:
    """Delete a pod so its parent Deployment controller recreates it.

    Use for CrashLoopBackOff pods. The Deployment ensures a fresh replica starts.
    Safe: blast_radius=low. Do NOT use for Pending or ImagePullBackOff pods.

    Args:
        pod_name: exact pod name from scan_cluster
        namespace: Kubernetes namespace (default: production)
    """
    return _get_runtime().cluster.restart_pod(pod_name, namespace)


@mcp.tool()
def patch_memory_limit(pod_name: str, new_memory_limit: str, namespace: str = "production") -> str:
    """Increase the memory limit of the Deployment owning this pod.

    Use for OOMKilled pods. Resolves the parent Deployment via ownerReferences and patches it.
    Safe: blast_radius=low. Recommended: increase by 50% (e.g. 256Mi → 384Mi).

    Args:
        pod_name: exact pod name from scan_cluster (must be owned by a Deployment)
        new_memory_limit: new memory limit string, e.g. '384Mi', '512Mi', '1Gi'
        namespace: Kubernetes namespace (default: production)
    """
    return _get_runtime().cluster.patch_memory_limit(pod_name, namespace, new_memory_limit)


@mcp.tool()
def delete_evicted_pod(pod_name: str, namespace: str = "production") -> str:
    """Delete an evicted pod to clean it up.

    Safe: evicted pods are already stopped by the kubelet. This just removes the dead object
    from the API so it no longer appears in get pods output.

    Args:
        pod_name: exact pod name of the evicted pod
        namespace: Kubernetes namespace (default: production)
    """
    return _get_runtime().cluster.delete_pod(pod_name, namespace)


@mcp.tool()
def patch_cpu_limit(pod_name: str, new_cpu_limit: str, namespace: str = "production") -> str:
    """Increase the CPU limit of the Deployment owning this pod.

    Use for CPU-throttled pods. Resolves the parent Deployment via ownerReferences and patches it.
    Safe: blast_radius=low. Recommended: increase by 50% (e.g. 250m -> 375m).

    Args:
        pod_name: exact pod name from scan_cluster (must be owned by a Deployment)
        new_cpu_limit: new CPU limit string, e.g. '375m', '500m', '1'
        namespace: Kubernetes namespace (default: production)
    """
    return _get_runtime().cluster.patch_cpu_limit(pod_name, namespace, new_cpu_limit)


@mcp.tool()
def scan_deployments(namespace: str = "production") -> list[dict]:
    """Scan deployments for stalled rollouts.

    Returns deployment objects with replicas, updatedReplicas, and a stalled flag.
    A stalled deployment has updatedReplicas != replicas (rollout not progressing).

    Args:
        namespace: Kubernetes namespace (default: production)
    """
    return _get_runtime().cluster.scan_deployments(namespace)


@mcp.tool()
def scan_nodes() -> list[dict]:
    """Scan cluster nodes for NotReady conditions.

    Returns node objects with resource_name and node_ready flag.
    A NotReady node has conditions[Ready]=False.
    """
    return _get_runtime().cluster.scan_nodes()


@mcp.tool()
def get_audit_log() -> list[dict]:
    """Return all K8sWhisperer incident records from the persistent audit log.

    Each entry contains: incident_id, timestamp, anomaly (type/severity/pod),
    diagnosis, plan (action/blast_radius), approved (True/False/None),
    result, and explanation.

    Use this to review what the autonomous agent has already handled.
    """
    from k8swhisperer.audit import load_audit_log
    settings = _get_runtime().settings
    return load_audit_log(settings.audit_log_path)


if __name__ == "__main__":
    mcp.run()
