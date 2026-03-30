"""HITL node helpers."""

from __future__ import annotations

from typing import Any, Dict

from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState


def build_hitl_payload(state: ClusterState) -> Dict[str, Any]:
    return {
        "incident_id": state["incident_id"],
        "diagnosis": state.get("diagnosis", ""),
        "plan": state.get("plan", {}),
    }


def _hitl_reason(state: ClusterState) -> str:
    """Build a human-readable reason why HITL was triggered."""
    anomaly = state["anomalies"][0] if state.get("anomalies") else {}
    plan = state.get("plan", {})
    anomaly_type = anomaly.get("type", "unknown")
    action = plan.get("action", "unknown")
    confidence = plan.get("confidence", 0)
    blast_radius = plan.get("blast_radius", "unknown")

    reasons = []
    if anomaly_type == "NodeNotReady":
        reasons.append("NodeNotReady always requires human approval (never auto-drain)")
    if blast_radius != "low":
        reasons.append(f"blast_radius={blast_radius} (must be 'low' for auto-execute)")
    if confidence <= 0.8:
        reasons.append(f"confidence={confidence:.0%} (must be >80% for auto-execute)")
    if action in ("rollback_deployment", "log_node_metrics"):
        reasons.append(f"action={action} is not in allowed auto-execute actions")

    if not reasons:
        reasons.append("action requires human verification")

    return "; ".join(reasons)


def request_approval(state: ClusterState, runtime: Runtime) -> ClusterState:
    if not state.get("approval_requested", False):
        anomaly = state["anomalies"][0] if state.get("anomalies") else {}
        plan = state.get("plan", {})
        reason = _hitl_reason(state)

        runtime.log(
            f"[hitl] requesting human approval for {anomaly.get('type', '?')} "
            f"on {anomaly.get('affected_resource', '?')}"
        )
        runtime.log(f"[hitl] reason: {reason}")
        runtime.log(
            f"[hitl] proposed action: {plan.get('action', '?')} | "
            f"confidence: {plan.get('confidence', 0):.0%} | "
            f"blast_radius: {plan.get('blast_radius', '?')}"
        )
        runtime.log("[hitl] sending Slack notification...")

        runtime.notifier.send_hitl_request(state)
        state["approval_requested"] = True
    state["execution_status"] = "awaiting_approval"
    return state
