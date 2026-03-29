"""Shared state contracts for the orchestration graph."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, TypedDict
from uuid import uuid4


Severity = Literal["LOW", "MED", "HIGH", "CRITICAL"]
BlastRadius = Literal["low", "medium", "high"]
ActionName = Literal["restart_pod", "patch_memory_limit", "explain_only"]
ExecutionStatus = Literal[
    "pending",
    "awaiting_approval",
    "approved",
    "rejected",
    "verified",
    "verification_failed",
    "explained",
]


class Anomaly(TypedDict, total=False):
    type: str
    severity: Severity
    affected_resource: str
    confidence: float
    namespace: str
    reason: str
    evidence: List[str]


class RemediationPlan(TypedDict, total=False):
    action: ActionName
    target_resource: str
    params: Dict[str, Any]
    confidence: float
    blast_radius: BlastRadius
    reason: str
    namespace: str


class LogEntry(TypedDict, total=False):
    incident_id: str
    timestamp: str
    anomaly: Anomaly
    diagnosis: str
    plan: RemediationPlan
    approved: bool
    result: str
    explanation: str


class ClusterState(TypedDict, total=False):
    incident_id: str
    events: List[Dict[str, Any]]
    anomalies: List[Anomaly]
    diagnosis: str
    plan: RemediationPlan
    approved: bool
    approval_requested: bool
    result: str
    audit_log: List[LogEntry]
    explanation: str
    execution_status: ExecutionStatus


def create_initial_state() -> ClusterState:
    """Create an empty graph state for a new incident cycle."""

    return ClusterState(
        incident_id=str(uuid4()),
        events=[],
        anomalies=[],
        diagnosis="",
        plan=RemediationPlan(),
        approved=False,
        approval_requested=False,
        result="",
        audit_log=[],
        explanation="",
        execution_status="pending",
    )


def new_log_entry(state: ClusterState) -> LogEntry:
    """Build a structured audit entry from the current state."""

    anomaly = state["anomalies"][0] if state.get("anomalies") else Anomaly()
    return LogEntry(
        incident_id=state["incident_id"],
        timestamp=datetime.now(timezone.utc).isoformat(),
        anomaly=anomaly,
        diagnosis=state.get("diagnosis", ""),
        plan=state.get("plan", RemediationPlan()),
        approved=state.get("approved", False),
        result=state.get("result", ""),
        explanation=state.get("explanation", ""),
    )
