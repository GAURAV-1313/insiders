"""Plan stage implementation."""

from __future__ import annotations

from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState, RemediationPlan


def run(state: ClusterState, runtime: Runtime) -> ClusterState:
    runtime.log("[plan] creating remediation proposal")
    if not state.get("anomalies"):
        state["plan"] = RemediationPlan(
            action="explain_only",
            target_resource="",
            params={},
            confidence=1.0,
            blast_radius="low",
            reason="No anomaly to remediate.",
            namespace="default",
        )
        return state

    anomaly = state["anomalies"][0]
    state["plan"] = runtime.llm.plan(anomaly, state.get("diagnosis", ""))
    plan = state["plan"]
    runtime.log(
        f"[plan] proposed: action={plan.get('action')} "
        f"confidence={plan.get('confidence', 0):.0%} "
        f"blast_radius={plan.get('blast_radius')}"
    )
    return state

