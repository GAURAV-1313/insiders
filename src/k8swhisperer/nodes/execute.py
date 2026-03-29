"""Execute stage implementation with verification."""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState, RemediationPlan


def verify_resolution(
    runtime: Runtime,
    pod_name: str,
    namespace: str,
    deployment_name: str | None = None,
    sleep: Callable[[int], None] | None = None,
) -> Tuple[bool, Dict[str, object]]:
    """Verify that a resource recovered after an action."""

    sleeper = sleep or runtime.sleep
    latest_state: Dict[str, object] = {}
    if deployment_name:
        return _verify_deployment_healthy(
            runtime=runtime,
            deployment_name=deployment_name,
            namespace=namespace,
            sleep=sleeper,
        )

    for backoff in runtime.settings.verify_backoff_seconds:
        runtime.log(f"[execute] waiting {backoff}s before verification")
        sleeper(backoff)
        latest_state = runtime.cluster.get_resource_state(pod_name, namespace)
        phase = str(latest_state.get("phase", "unknown"))
        restart_count = int(latest_state.get("restart_count", 0))
        runtime.log(
            f"[execute] observed phase={phase} restart_count={restart_count}"
        )
        if phase == "Running" and restart_count == 0:
            return True, latest_state
    return False, latest_state


def _verify_deployment_healthy(
    runtime: Runtime,
    deployment_name: str,
    namespace: str,
    sleep: Callable[[int], None],
) -> Tuple[bool, Dict[str, object]]:
    latest_state: Dict[str, object] = {"deployment_name": deployment_name, "pods": []}
    healthy_streak = 0
    for backoff in runtime.settings.verify_backoff_seconds:
        runtime.log(f"[execute] waiting {backoff}s before verification")
        sleep(backoff)
        pods = runtime.cluster.scan_cluster()
        matching = [
            pod
            for pod in pods
            if pod.get("namespace") == namespace
            and str(pod.get("pod_name", "")).startswith(deployment_name)
        ]
        runtime.log(
            f"[execute] observed {len(matching)} pods for deployment prefix={deployment_name}"
        )
        latest_state = {
            "deployment_name": deployment_name,
            "pods": matching,
        }
        healthy = [
            pod
            for pod in matching
            if pod.get("status") == "Running" and int(pod.get("restart_count", 0)) == 0
        ]
        if healthy:
            healthy_streak += 1
            if healthy_streak >= 2:
                return True, {"deployment_name": deployment_name, "pods": healthy}
            runtime.log(
                f"[execute] healthy deployment candidate found for {deployment_name}; confirming on next poll"
            )
            continue
        healthy_streak = 0
    return False, latest_state


def _deployment_name_from_pod_name(pod_name: str) -> str:
    parts = pod_name.split("-")
    if len(parts) <= 2:
        return pod_name
    return "-".join(parts[:-2])


def run(state: ClusterState, runtime: Runtime) -> ClusterState:
    runtime.log("[execute] performing approved action")
    plan = state.get("plan", RemediationPlan())
    action = plan.get("action", "explain_only")
    namespace = plan.get("namespace", "default")
    resource = plan.get("target_resource", "")

    if action == "explain_only":
        state["result"] = "No action executed. Explanation only."
        state["execution_status"] = "explained"
        return state

    if action == "restart_pod":
        command_result = runtime.cluster.restart_pod(resource, namespace)
        deployment_name = _deployment_name_from_pod_name(resource)
    elif action == "patch_memory_limit":
        memory_limit = str(plan.get("params", {}).get("memory_limit", "384Mi"))
        command_result = runtime.cluster.patch_memory_limit(resource, namespace, memory_limit)
        deployment_name = _deployment_name_from_pod_name(resource)
    else:
        state["result"] = f"Blocked unsupported action: {action}"
        state["execution_status"] = "verification_failed"
        return state

    verified, observed_state = verify_resolution(
        runtime,
        resource,
        namespace,
        deployment_name=deployment_name,
    )
    if verified:
        state["result"] = f"{command_result}; verification passed with state={observed_state}"
        state["execution_status"] = "verified"
    else:
        state["result"] = f"{command_result}; verification failed with state={observed_state}"
        state["execution_status"] = "verification_failed"
    return state
