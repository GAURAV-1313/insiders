"""
Audit log manager.

Every incident — detected, diagnosed, planned, executed — gets a LogEntry
appended to audit_log.json. This file is the permanent record.

Usage:
    from audit import append_log_entry, load_log

    entry = build_log_entry(
        incident_id="inc-001",
        anomaly=anomaly_dict,
        diagnosis="root cause string",
        plan=plan_dict,
        approved=True,
        auto_executed=True,
        execution_result="pod is now Running",
        audit_summary="Full audit summary from explain prompt",
    )
    append_log_entry(entry)
"""

import json
import os
import uuid
from datetime import datetime, timezone

AUDIT_LOG_PATH = os.path.join(os.path.dirname(__file__), "audit_log.json")


def _load_raw() -> list:
    if not os.path.exists(AUDIT_LOG_PATH):
        return []
    with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []


def load_log() -> list[dict]:
    """Return all log entries (newest-first for display)."""
    return list(reversed(_load_raw()))


def build_log_entry(
    incident_id: str,
    anomaly: dict,
    diagnosis: str,
    plan: dict,
    approved: bool | None,
    auto_executed: bool,
    execution_result: str,
    audit_summary: str,
) -> dict:
    """
    Construct a complete LogEntry dict.
    'approved' is None if auto-executed (no human in loop).
    """
    return {
        "incident_id": incident_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "anomaly": anomaly,
        "diagnosis": diagnosis,
        "plan": plan,
        "decision": {
            "auto_executed": auto_executed,
            "human_approved": approved,
        },
        "execution_result": execution_result,
        "audit_summary": audit_summary,
    }


def append_log_entry(entry: dict) -> None:
    """Append a LogEntry to audit_log.json (thread-safe for single-process use)."""
    log = _load_raw()
    log.append(entry)
    with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"[Audit] Logged incident {entry.get('incident_id')} at {entry.get('timestamp')}")


def generate_incident_id() -> str:
    """Short unique ID for an incident, e.g. 'inc-a3f2'."""
    return "inc-" + uuid.uuid4().hex[:6]
