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


def request_approval(state: ClusterState, runtime: Runtime) -> ClusterState:
    if not state.get("approval_requested", False):
        runtime.log("[hitl] requesting human approval")
        runtime.notifier.send_hitl_request(state)
        state["approval_requested"] = True
    state["execution_status"] = "awaiting_approval"
    return state
