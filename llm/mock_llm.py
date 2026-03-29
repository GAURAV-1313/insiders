"""
Mock LLM responses for development without using the real API.
Person 1/2 can use these while the graph is being built — no API key needed.

Usage in nodes:
    from llm.mock_llm import mock_detect, mock_diagnose, mock_plan, mock_explain
"""

import time


def mock_detect(events: list[dict], pod_states: list[dict]) -> list[dict]:
    """Returns a fake CrashLoopBackOff anomaly."""
    time.sleep(0.1)  # simulate network latency
    return [
        {
            "type": "CrashLoopBackOff",
            "severity": "HIGH",
            "affected_resource": "api-deployment-7d9f8b-xk2p1",
            "namespace": "default",
            "confidence": 0.95,
            "trigger_signal": "restartCount=7, reason=Error, last exit code 1",
        }
    ]


def mock_diagnose(anomaly: dict, logs: str, describe_output: str, events: list[dict]) -> str:
    time.sleep(0.1)
    return (
        "The pod is crash-looping due to a missing environment variable 'DATABASE_URL'. "
        "Logs show 'KeyError: DATABASE_URL' at startup (line 42 of app.py). "
        "The pod reaches exit code 1 within 2 seconds of starting, which matches the pattern. "
        "The ConfigMap 'api-config' referenced in the deployment spec does not contain this key."
    )


def mock_plan(anomaly: dict, diagnosis: str) -> dict:
    time.sleep(0.1)
    return {
        "action_type": "restart_pod",
        "target_resource": anomaly.get("affected_resource", "unknown-pod"),
        "namespace": anomaly.get("namespace", "default"),
        "parameters": {},
        "confidence": 0.85,
        "blast_radius": "low",
        "reasoning": "Restarting the pod will pick up the corrected ConfigMap if it has been patched.",
    }


def mock_plan_oom(anomaly: dict, diagnosis: str) -> dict:
    time.sleep(0.1)
    return {
        "action_type": "patch_memory_limit",
        "target_resource": anomaly.get("affected_resource", "unknown-pod"),
        "namespace": anomaly.get("namespace", "default"),
        "parameters": {"new_memory_limit": "512Mi", "current_limit": "256Mi"},
        "confidence": 0.88,
        "blast_radius": "medium",
        "reasoning": "Increasing memory limit by 50% gives headroom above the OOM kill threshold.",
    }


def mock_explain(anomaly: dict, diagnosis: str, plan: dict, auto_executed: bool, execution_result: str) -> dict:
    time.sleep(0.1)
    return {
        "slack_summary": (
            f"Pod {anomaly.get('affected_resource', 'unknown')} was crash-looping due to a misconfigured environment variable. "
            "The agent restarted the pod. The pod is now Running."
        ),
        "audit_summary": (
            f"INCIDENT: {anomaly.get('type')} on {anomaly.get('affected_resource')} "
            f"(namespace: {anomaly.get('namespace')}). "
            f"Root cause: {diagnosis[:120]}... "
            f"Action: {plan.get('action_type')} on {plan.get('target_resource')}. "
            f"Result: {execution_result[:80]}. "
            f"{'Auto-executed' if auto_executed else 'HITL approved'}."
        ),
    }
