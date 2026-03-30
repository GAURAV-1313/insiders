"""LangGraph builder and fallback-friendly workflow helpers.

Builds a 9-node StateGraph with conditional edges:

  observe -> detect -> diagnose -> plan -> safety_gate
                                              │
                        ┌─────────────────────┼──────────────────────┐
                        ▼ (auto-execute)      ▼ (HITL required)     │
                     execute            hitl_request -> hitl_wait    │
                        │                     │                      │
                        │              ┌──────┴──────┐               │
                        │              ▼ (approved)  ▼ (rejected)    │
                        │           execute    explain_and_log       │
                        │              │                             │
                        ▼              ▼                             │
                   explain_and_log ← ──┘                             │
                        │                                            │
                       END                                           │
                                                                     │
  If execute verification fails and not yet HITL-approved:           │
     execute -> hitl_request (re-escalation) ────────────────────────┘
"""

from __future__ import annotations

from typing import Any, Callable

from k8swhisperer.nodes import detect, diagnose, execute, explain_log, hitl, observe, plan, safety_gate
from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState, ExecutionStatus, RemediationPlan

try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import interrupt

    LANGGRAPH_AVAILABLE = True
except ImportError as exc:  # pragma: no cover - exercised only without deps
    LANGGRAPH_AVAILABLE = False
    LANGGRAPH_IMPORT_ERROR = exc


def route_after_safety(state: ClusterState) -> str:
    if state.get("execution_status") == "awaiting_approval":
        return "hitl_request"
    return "execute"


def route_after_hitl(state: ClusterState) -> str:
    return "execute" if state.get("approved", False) else "explain_and_log"


def route_after_execute(state: ClusterState) -> str:
    return "hitl" if state.get("execution_status") == "verification_failed" and not state.get("approved", False) else "explain_and_log"


class WorkflowNodes:
    """Runtime-bound node collection used by the graph."""

    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime

    def observe(self, state: ClusterState) -> ClusterState:
        return observe.run(state, self.runtime)

    def detect(self, state: ClusterState) -> ClusterState:
        return detect.run(state, self.runtime)

    def diagnose(self, state: ClusterState) -> ClusterState:
        return diagnose.run(state, self.runtime)

    def plan(self, state: ClusterState) -> ClusterState:
        return plan.run(state, self.runtime)

    def safety_gate(self, state: ClusterState) -> ClusterState:
        return safety_gate.run(state, self.runtime)

    def execute(self, state: ClusterState) -> ClusterState:
        return execute.run(state, self.runtime)

    def hitl_request(self, state: ClusterState) -> ClusterState:
        return hitl.request_approval(state, self.runtime)

    def hitl_wait(self, state: ClusterState) -> ClusterState:
        approval = interrupt(hitl.build_hitl_payload(state))
        state["approved"] = bool(approval.get("approved", False))
        state["execution_status"] = "approved" if state["approved"] else "rejected"
        return state

    def explain_and_log(self, state: ClusterState) -> ClusterState:
        return explain_log.run(state, self.runtime)


def build_graph(runtime: Runtime) -> Any:
    """Build the orchestration graph."""

    if not LANGGRAPH_AVAILABLE:  # pragma: no cover - depends on local install
        raise RuntimeError(
            "LangGraph is not installed. Install dependencies with 'pip install -r requirements.txt' "
            f"before building the graph. Import error: {LANGGRAPH_IMPORT_ERROR}"
        )

    nodes = WorkflowNodes(runtime)
    builder: StateGraph = StateGraph(ClusterState)
    builder.add_node("observe", nodes.observe)
    builder.add_node("detect", nodes.detect)
    builder.add_node("diagnose", nodes.diagnose)
    builder.add_node("plan", nodes.plan)
    builder.add_node("safety_gate", nodes.safety_gate)
    builder.add_node("execute", nodes.execute)
    builder.add_node("hitl_request", nodes.hitl_request)
    builder.add_node("hitl_wait", nodes.hitl_wait)
    builder.add_node("explain_and_log", nodes.explain_and_log)

    builder.add_edge(START, "observe")
    builder.add_edge("observe", "detect")
    builder.add_edge("detect", "diagnose")
    builder.add_edge("diagnose", "plan")
    builder.add_edge("plan", "safety_gate")
    builder.add_conditional_edges(
        "safety_gate",
        route_after_safety,
        {"execute": "execute", "hitl_request": "hitl_request"},
    )
    builder.add_edge("hitl_request", "hitl_wait")
    builder.add_conditional_edges(
        "hitl_wait",
        route_after_hitl,
        {"execute": "execute", "explain_and_log": "explain_and_log"},
    )
    builder.add_conditional_edges(
        "execute",
        route_after_execute,
        {"hitl": "hitl_request", "explain_and_log": "explain_and_log"},
    )
    builder.add_edge("explain_and_log", END)
    return builder.compile(checkpointer=MemorySaver())


def execute_fixture_cycle(state: ClusterState, runtime: Runtime) -> ClusterState:
    """Fallback execution path used when LangGraph is unavailable locally."""

    nodes = WorkflowNodes(runtime)
    state = nodes.observe(state)
    state = nodes.detect(state)
    state = nodes.diagnose(state)
    state = nodes.plan(state)
    state = nodes.safety_gate(state)
    next_step = route_after_safety(state)
    if next_step == "hitl_request":
        state = nodes.hitl_request(state)
        state["approved"] = False
        state["execution_status"] = "rejected"
    else:
        state = nodes.execute(state)
        if route_after_execute(state) == "hitl":
            state = nodes.hitl_request(state)
            state["approved"] = False
            state["execution_status"] = "rejected"
    state = nodes.explain_and_log(state)
    return state
