"""Explain-and-log stage implementation."""

from __future__ import annotations

from k8swhisperer.audit import append_audit_entry
from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState, new_log_entry


def run(state: ClusterState, runtime: Runtime) -> ClusterState:
    runtime.log("[explain_and_log] generating human-readable summary")
    state["explanation"] = runtime.llm.explain(state)
    entry = new_log_entry(state)
    state["audit_log"] = append_audit_entry(
        runtime.settings.audit_log_path,
        state.get("audit_log", []),
        entry,
    )
    return state

