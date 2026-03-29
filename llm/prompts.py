"""
All four LLM prompt functions used by the agent nodes.

Each function takes structured inputs and returns structured outputs.
The rest of the agent calls these — they never talk to the LLM directly.

Functions:
  run_detect_prompt    → list[dict]  (Anomaly objects)
  run_diagnose_prompt  → str         (root cause string)
  run_plan_prompt      → dict        (RemediationPlan)
  run_explain_prompt   → str         (plain-English summary)
"""

import json
from llm.client import call_llm, call_llm_json


# ---------------------------------------------------------------------------
# 01 · DETECT — classify raw kubectl events into typed Anomaly objects
# ---------------------------------------------------------------------------

DETECT_SYSTEM = """You are the anomaly detection component of a Kubernetes incident response agent.

Your job is to read a stream of raw kubectl events and pod states, then classify every anomaly you find.

Output a JSON object with a single key "anomalies" containing a list. Each anomaly must have exactly these fields:
- "type": one of ["CrashLoopBackOff", "OOMKilled", "PendingPod", "ImagePullBackOff", "CPUThrottling", "EvictedPod", "DeploymentStalled", "NodeNotReady"]
- "severity": one of ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
- "affected_resource": the full pod/node name as a string
- "namespace": the Kubernetes namespace as a string
- "confidence": a float between 0.0 and 1.0 — how certain you are this is a real anomaly
- "trigger_signal": one sentence explaining the raw signal that triggered this classification

Rules:
- Only report anomalies that are clearly present in the data — do not hallucinate.
- A pod restarting during a rolling update is EXPECTED behaviour — set confidence < 0.4 for it.
- A pod restarting repeatedly (restartCount > 3) with no deployment activity is a real CrashLoopBackOff.
- If restartCount increased but a new deployment is in progress, classify as rolling update, not CrashLoop.
- Return an empty list if no anomalies are present.
- Do not include duplicate entries for the same pod and same anomaly type.

Example output:
{
  "anomalies": [
    {
      "type": "CrashLoopBackOff",
      "severity": "HIGH",
      "affected_resource": "api-deployment-7d9f8b-xk2p1",
      "namespace": "production",
      "confidence": 0.95,
      "trigger_signal": "restartCount=7, reason=Error, last exit code 1"
    }
  ]
}"""


def run_detect_prompt(events: list[dict], pod_states: list[dict]) -> list[dict]:
    """
    Classify kubectl events into Anomaly objects.
    Returns a list of anomaly dicts (may be empty if cluster is healthy).
    """
    user_message = f"""Analyse these Kubernetes events and pod states:

EVENTS:
{json.dumps(events, indent=2)}

POD STATES:
{json.dumps(pod_states, indent=2)}

Return the anomalies JSON object now."""

    result = call_llm_json(DETECT_SYSTEM, user_message)
    return result.get("anomalies", [])


# ---------------------------------------------------------------------------
# 02 · DIAGNOSE — synthesise root cause from logs + describe output
# ---------------------------------------------------------------------------

DIAGNOSE_SYSTEM = """You are the root cause analysis component of a Kubernetes incident response agent.

You will receive:
- The anomaly that was detected (type, severity, affected resource)
- kubectl logs output from the failing pod (may be truncated to last 100 lines)
- kubectl describe output for the pod
- Recent Kubernetes events for the pod

Your job is to produce a precise, actionable root cause string.

Requirements for a good root cause string:
- One paragraph, 3-5 sentences maximum.
- Cite specific evidence from the logs or describe output. Quote relevant log lines.
- State the most likely root cause first, then the supporting evidence.
- If there are multiple possible causes, rank them by likelihood.
- Do not say vague things like "the pod is crashing because of an error". Be specific.
- If the logs are empty or uninformative, say so explicitly — do not invent causes.

Good example:
"The pod is crashing due to an OOM kill. The describe output shows lastState.terminated.reason=OOMKilled with exit code 137. The current memory limit is 256Mi, but the logs show the application loaded a 300MB model file at startup (line: 'Loading model weights: 312MB'). The container hits the limit before the model finishes loading and is killed by the kernel."

Bad example:
"The pod is having issues. There might be a problem with memory or configuration."

Output a JSON object with two keys:
- "root_cause": the detailed root cause string
- "confidence": float 0.0-1.0 representing how confident you are in this diagnosis"""


def run_diagnose_prompt(anomaly: dict, logs: str, describe_output: str, events: list[dict]) -> str:
    """
    Synthesise a root cause string from logs and describe output.
    Returns a plain string — the root cause explanation.
    """
    # Truncate logs to avoid hitting context limits — last 100 lines is enough
    log_lines = logs.strip().split("\n")
    if len(log_lines) > 100:
        log_lines = log_lines[-100:]
        logs_truncated = f"[Showing last 100 of {len(logs.strip().split(chr(10)))} lines]\n" + "\n".join(log_lines)
    else:
        logs_truncated = logs

    user_message = f"""Diagnose this Kubernetes anomaly:

ANOMALY:
{json.dumps(anomaly, indent=2)}

KUBECTL LOGS (last 100 lines):
{logs_truncated}

KUBECTL DESCRIBE:
{describe_output}

RECENT EVENTS:
{json.dumps(events, indent=2)}

Produce the root cause JSON now."""

    result = call_llm_json(DIAGNOSE_SYSTEM, user_message)
    return result.get("root_cause", "Root cause diagnosis failed — no output from LLM.")


# ---------------------------------------------------------------------------
# 03 · PLAN — propose a RemediationPlan
# ---------------------------------------------------------------------------

PLAN_SYSTEM = """You are the remediation planner for a Kubernetes incident response agent.

You will receive a detected anomaly and a root cause diagnosis. Your job is to propose the safest, most effective remediation action.

Output a JSON object with exactly these fields:
- "action_type": the specific action to take — use one of:
    "restart_pod", "patch_memory_limit", "patch_cpu_limit", "delete_evicted_pod",
    "describe_node", "force_rollout", "rollback_deployment", "alert_human_only"
- "target_resource": the exact pod/deployment/node name to act on
- "namespace": the Kubernetes namespace
- "parameters": a dict of action-specific parameters (e.g. {"new_memory_limit": "512Mi"})
- "confidence": float 0.0-1.0 — confidence this action will fix the issue
- "blast_radius": one of ["low", "medium", "high"] — potential for collateral damage
- "reasoning": one sentence explaining WHY this action addresses the root cause

Blast radius rules — be honest:
- "low": affects only the specific pod, no data loss possible (restart, delete evicted pod)
- "medium": changes resource limits or affects a deployment (patch limits, force rollout)
- "high": could affect multiple services or cause downtime (rollback, anything on nodes)

Action selection rules:
- CrashLoopBackOff → restart_pod (blast_radius: low)
- OOMKilled → patch_memory_limit then restart_pod (blast_radius: medium). Set new_memory_limit to current limit + 50%
- PendingPod → describe_node (blast_radius: low) — never auto-schedule pods to new nodes
- ImagePullBackOff → alert_human_only (blast_radius: low) — human must fix the image tag
- EvictedPod → delete_evicted_pod (blast_radius: low)
- DeploymentStalled → alert_human_only with action_type rollback_deployment (blast_radius: high) — always HITL
- NodeNotReady → alert_human_only (blast_radius: high) — NEVER auto-drain a node

Example output:
{
  "action_type": "patch_memory_limit",
  "target_resource": "api-deployment",
  "namespace": "production",
  "parameters": {"new_memory_limit": "384Mi", "current_limit": "256Mi"},
  "confidence": 0.88,
  "blast_radius": "medium",
  "reasoning": "Pod was OOMKilled with 256Mi limit; increasing by 50% to 384Mi gives headroom for model loading."
}"""


def run_plan_prompt(anomaly: dict, diagnosis: str) -> dict:
    """
    Propose a RemediationPlan for the given anomaly + diagnosis.
    Returns a dict matching the RemediationPlan schema.
    """
    user_message = f"""Propose a remediation plan for this incident:

ANOMALY:
{json.dumps(anomaly, indent=2)}

ROOT CAUSE:
{diagnosis}

Return the remediation plan JSON now."""

    return call_llm_json(PLAN_SYSTEM, user_message)


# ---------------------------------------------------------------------------
# 04 · EXPLAIN — write a human-readable audit trail entry
# ---------------------------------------------------------------------------

EXPLAIN_SYSTEM = """You are the explanation writer for a Kubernetes incident response agent.

After an incident has been handled, you write a clear, concise summary for the audit log and for Slack.

You will receive:
- The anomaly that was detected
- The root cause diagnosis
- The remediation plan that was proposed
- Whether the action was auto-executed or sent for human approval
- The execution result (kubectl output and post-action pod state)

Write a summary that a non-expert on-call engineer can understand at 3am.

Output a JSON object with two keys:
- "slack_summary": a short summary for posting to Slack (3-5 sentences, plain text, no jargon)
  Format: What happened → Why → What was done → Current status
- "audit_summary": a detailed summary for the audit log (can be longer, technical terms OK)
  Must include: anomaly type, affected resource, root cause evidence, action taken, outcome

The slack_summary should be readable without Kubernetes knowledge.
The audit_summary should be complete enough to reconstruct the incident from scratch.

Example slack_summary:
"The API server pod (api-deployment-7d9f8b-xk2p1) crashed 7 times in 10 minutes due to running out of memory while loading its model. The memory limit was increased from 256MB to 384MB and the pod was restarted. The pod is now Running and has been stable for 30 seconds."

Example audit_summary:
"INCIDENT: CrashLoopBackOff on api-deployment-7d9f8b-xk2p1 (namespace: production). Root cause: OOMKill — container exceeded 256Mi memory limit during model weight loading (log evidence: 'Loading model weights: 312MB'). Action: patched memory limit to 384Mi via kubectl patch, then restarted pod. Execution result: pod transitioned to Running state within 45 seconds. Auto-executed (confidence=0.88, blast_radius=medium → required HITL approval, approved by on-call engineer)." """


def run_explain_prompt(
    anomaly: dict,
    diagnosis: str,
    plan: dict,
    auto_executed: bool,
    execution_result: str,
) -> dict:
    """
    Write human-readable summaries for Slack and the audit log.
    Returns {"slack_summary": str, "audit_summary": str}
    """
    action_path = "AUTO-EXECUTED (no human approval needed)" if auto_executed else "SENT FOR HUMAN APPROVAL (HITL)"

    user_message = f"""Write the incident summary:

ANOMALY:
{json.dumps(anomaly, indent=2)}

ROOT CAUSE:
{diagnosis}

REMEDIATION PLAN:
{json.dumps(plan, indent=2)}

ACTION PATH: {action_path}

EXECUTION RESULT:
{execution_result}

Return the slack_summary and audit_summary JSON now."""

    result = call_llm_json(EXPLAIN_SYSTEM, user_message)
    return {
        "slack_summary": result.get("slack_summary", "Incident handled — see audit log for details."),
        "audit_summary": result.get("audit_summary", "Audit summary unavailable."),
    }
