"""Deterministic safety gate logic."""

from __future__ import annotations

from typing import Literal

from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState, RemediationPlan


Route = Literal["execute", "hitl"]


def determine_route(plan: RemediationPlan, runtime: Runtime) -> Route:
    action = plan.get("action", "")
    confidence = float(plan.get("confidence", 0))
    blast_radius = plan.get("blast_radius", "high")

    if action in runtime.settings.destructive_actions:
        return "hitl"
    if action not in runtime.settings.allowed_v1_actions:
        return "hitl"
    if confidence <= runtime.settings.min_auto_confidence:
        return "hitl"
    if blast_radius != "low":
        return "hitl"
    return "execute"


def run(state: ClusterState, runtime: Runtime) -> ClusterState:
    runtime.log("[safety_gate] evaluating remediation risk")
    route = determine_route(state.get("plan", RemediationPlan()), runtime)
    if route == "hitl":
        state["execution_status"] = "awaiting_approval"
    return state

