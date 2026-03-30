"""Deterministic safety gate logic.

Routes remediation plans to auto-execute or HITL based on four rules:
1. NodeNotReady anomalies ALWAYS require HITL (never auto-drain a node)
2. Destructive actions (delete_namespace, drain_node, etc.) require HITL
3. Actions not in ALLOWED_V1_ACTIONS require HITL
4. Auto-execute ONLY when: confidence > 0.8 AND blast_radius == 'low'
"""

from __future__ import annotations

from typing import Literal

from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState, RemediationPlan


Route = Literal["execute", "hitl"]


def determine_route(plan: RemediationPlan, runtime: Runtime, state: ClusterState | None = None) -> Route:
    """Deterministic risk-based routing — no LLM involvement.

    Returns 'execute' only when ALL of these are true:
    - The anomaly is NOT NodeNotReady (node ops always need human eyes)
    - The action is not in DESTRUCTIVE_ACTIONS
    - The action is in ALLOWED_V1_ACTIONS
    - Confidence > 0.8 (min_auto_confidence threshold)
    - Blast radius is 'low'
    """
    # CRITICAL: NodeNotReady ALWAYS requires HITL — never auto-remediate a node
    if state and state.get("anomalies"):
        anomaly_type = state["anomalies"][0].get("type", "")
        if anomaly_type == "NodeNotReady":
            return "hitl"

    action = plan.get("action", "")
    confidence = float(plan.get("confidence", 0))
    blast_radius = plan.get("blast_radius", "high")

    # Destructive actions (drain_node, delete_namespace, etc.) always need approval
    if action in runtime.settings.destructive_actions:
        return "hitl"
    # Unknown/new actions not yet vetted for automation
    if action not in runtime.settings.allowed_v1_actions:
        return "hitl"
    # Low-confidence plans should be reviewed by a human
    if confidence <= runtime.settings.min_auto_confidence:
        return "hitl"
    # Medium/high blast radius actions affect multiple resources
    if blast_radius != "low":
        return "hitl"
    return "execute"


def run(state: ClusterState, runtime: Runtime) -> ClusterState:
    plan = state.get("plan", RemediationPlan())
    route = determine_route(plan, runtime, state)
    if route == "hitl":
        state["execution_status"] = "awaiting_approval"
        runtime.log(
            f"[safety_gate] HITL required -- routing to human approval "
            f"(action={plan.get('action')} blast={plan.get('blast_radius')} "
            f"confidence={plan.get('confidence', 0):.0%})"
        )
    else:
        runtime.log(
            f"[safety_gate] auto-execute approved "
            f"(action={plan.get('action')} blast={plan.get('blast_radius')} "
            f"confidence={plan.get('confidence', 0):.0%})"
        )
    return state

