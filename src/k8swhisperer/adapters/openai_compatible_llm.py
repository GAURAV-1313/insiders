"""Person 3 integration file: OpenAI-compatible LLM adapter skeleton."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List
from urllib import error, request

from openai import OpenAI

from k8swhisperer.adapters.base import LLMAdapter
from k8swhisperer.state import Anomaly, ClusterState, RemediationPlan

logger = logging.getLogger(__name__)

VALID_TYPES = {"CrashLoopBackOff", "OOMKilled", "Pending"}
VALID_SEVERITIES = {"HIGH", "MED", "LOW", "CRITICAL"}


class OpenAICompatibleLLMAdapter(LLMAdapter):
    """Skeleton adapter for Groq/OpenAI-compatible chat completion APIs.

    Person 3 should implement the four task-specific methods below.
    The shared HTTP helper is already provided so they only need to focus on:
    - prompt design
    - schema-safe parsing
    - reliable outputs for the required scenarios
    """

    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = OpenAI(api_key=api_key, base_url=self.base_url)

    def classify(self, events: List[Dict[str, Any]]) -> List[Anomaly]:
        """Classify anomalous pods from normalized cluster events."""

        events_json = json.dumps(events, indent=2, sort_keys=True)
        system_prompt = (
            "You are a Kubernetes anomaly classifier. "
            "Return only valid JSON. No markdown. No explanation. "
            "No code fences. No text before or after the JSON."
        )
        user_prompt = (
            "Classify anomalous pods from these events.\n"
            "Return a JSON array only. Each object must have exactly \n"
            "these fields and no others:\n"
            "  type: one of exactly: CrashLoopBackOff, OOMKilled, Pending\n"
            "  severity: one of exactly: HIGH, MED, LOW, CRITICAL\n"
            "  affected_resource: copy the pod_name value exactly\n"
            "  namespace: copy the namespace value exactly\n"
            "  confidence: a float between 0.0 and 1.0\n\n"
            "Rules:\n"
            "- status is CrashLoopBackOff OR restart_count > 3 \n"
            "  with exit_code not 0 \n"
            "  \u2192 type=CrashLoopBackOff, severity=HIGH\n"
            "- status is OOMKilled OR exit_code is 137 \n"
            "  \u2192 type=OOMKilled, severity=HIGH  \n"
            "- status is Pending \n"
            "  \u2192 type=Pending, severity=MED\n"
            "- if nothing is anomalous return []\n\n"
            f"Events:\n{events_json}"
        )

        raw_response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        ).choices[0].message.content or ""

        cleaned = self._strip_code_fences(raw_response.strip())
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Could not parse classify() JSON response: %s", raw_response)
            return []

        if not isinstance(payload, list):
            logger.warning("classify() returned non-list payload: %r", payload)
            return []

        valid_anomalies: List[Anomaly] = []
        for item in payload:
            anomaly = self._validate_anomaly(item)
            if anomaly:
                valid_anomalies.append(anomaly)

        return valid_anomalies

    def diagnose(self, anomaly: Anomaly, logs: str, description: str, events: List[Dict[str, Any]]) -> str:
        """Return a concise evidence-backed root cause string."""

        log_lines = logs.strip().splitlines()
        if len(log_lines) > 100:
            logs = "[Showing last 100 lines]\n" + "\n".join(log_lines[-100:])

        system_prompt = (
            "You are the root cause analysis component of a Kubernetes incident response agent. "
            "You will receive an anomaly, pod logs, kubectl describe output, and recent events. "
            "Return a single plain-English paragraph (3-5 sentences maximum). "
            "Cite specific evidence from the logs or describe output — quote relevant lines. "
            "State the most likely root cause first, then supporting evidence. "
            "If logs are empty or uninformative, say so explicitly. "
            "Do not use markdown. Do not use JSON. Return plain text only."
        )
        user_prompt = (
            f"Anomaly:\n{json.dumps(anomaly, indent=2)}\n\n"
            f"Pod logs (last 100 lines):\n{logs or '(no logs available)'}\n\n"
            f"kubectl describe output:\n{description or '(no describe output available)'}\n\n"
            f"Recent events:\n{json.dumps(events, indent=2)}\n\n"
            "Write the root cause diagnosis now."
        )

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return (response.choices[0].message.content or "").strip()

    def plan(self, anomaly: Anomaly, diagnosis: str) -> RemediationPlan:
        """Propose a RemediationPlan using the repo schema (action, params, blast_radius)."""

        system_prompt = (
            "You are the remediation planner for a Kubernetes incident response agent. "
            "Return only valid JSON. No markdown. No code fences. No explanation outside the JSON.\n\n"
            "Required fields:\n"
            "  action: one of exactly: restart_pod, patch_memory_limit, explain_only\n"
            "  target_resource: the exact pod or deployment name to act on\n"
            "  namespace: the Kubernetes namespace\n"
            "  params: a dict of action-specific parameters\n"
            "  confidence: float 0.0-1.0\n"
            "  blast_radius: one of exactly: low, medium, high\n"
            "  reason: one sentence explaining why this action addresses the root cause\n\n"
            "Action selection rules:\n"
            "  CrashLoopBackOff -> action=restart_pod, blast_radius=low, params={}\n"
            "  OOMKilled -> action=patch_memory_limit, blast_radius=low, "
            "params={\"memory_limit\": \"<current+50%>\"}\n"
            "  Pending -> action=explain_only, blast_radius=low, params={}\n\n"
            "For OOMKilled: set memory_limit to 384Mi if current limit is unknown."
        )
        user_prompt = (
            f"Anomaly:\n{json.dumps(anomaly, indent=2)}\n\n"
            f"Root cause diagnosis:\n{diagnosis}\n\n"
            "Return the remediation plan JSON now."
        )

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        raw = self._strip_code_fences((response.choices[0].message.content or "").strip())

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("plan() could not parse JSON: %s", raw)
            return self._fallback_plan(anomaly)

        return self._validate_plan(data, anomaly)

    def explain(self, state: ClusterState) -> str:
        """Return a single plain-English incident summary string."""

        anomaly = state["anomalies"][0] if state.get("anomalies") else {}
        plan = state.get("plan", {})
        approved = state.get("approved")
        result = state.get("result", "")
        diagnosis = state.get("diagnosis", "")

        if state.get("execution_status") in ("awaiting_approval", "rejected"):
            action_path = "sent for human approval (HITL)"
        elif approved is True:
            action_path = "approved by human and executed"
        elif approved is False:
            action_path = "rejected by human — no action taken"
        else:
            action_path = "auto-executed"

        system_prompt = (
            "You are the explanation writer for a Kubernetes incident response agent. "
            "Write a clear, concise incident summary a non-expert on-call engineer can understand at 3am. "
            "Format: What happened -> Why -> What was done -> Current status. "
            "3-5 sentences. Plain text only. No markdown. No JSON. No bullet points."
        )
        user_prompt = (
            f"Anomaly: {json.dumps(anomaly)}\n"
            f"Root cause: {diagnosis}\n"
            f"Plan: action={plan.get('action', 'unknown')}, "
            f"target={plan.get('target_resource', 'unknown')}, "
            f"blast_radius={plan.get('blast_radius', 'unknown')}\n"
            f"Action path: {action_path}\n"
            f"Execution result: {result or 'not yet executed'}\n\n"
            "Write the incident summary now."
        )

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        return (response.choices[0].message.content or "").strip()

    def _fallback_plan(self, anomaly: Anomaly) -> RemediationPlan:
        """Return a safe default plan when LLM output cannot be parsed."""
        anomaly_type = anomaly.get("type", "")
        if anomaly_type == "OOMKilled":
            return RemediationPlan(
                action="patch_memory_limit",
                target_resource=anomaly.get("affected_resource", "unknown"),
                namespace=anomaly.get("namespace", "default"),
                params={"memory_limit": "384Mi"},
                confidence=0.7,
                blast_radius="low",
                reason="OOMKilled — increasing memory limit by 50% as safe default.",
            )
        if anomaly_type == "Pending":
            return RemediationPlan(
                action="explain_only",
                target_resource=anomaly.get("affected_resource", "unknown"),
                namespace=anomaly.get("namespace", "default"),
                params={},
                confidence=0.8,
                blast_radius="low",
                reason="Pending pod — human review required.",
            )
        return RemediationPlan(
            action="restart_pod",
            target_resource=anomaly.get("affected_resource", "unknown"),
            namespace=anomaly.get("namespace", "default"),
            params={},
            confidence=0.7,
            blast_radius="low",
            reason="CrashLoopBackOff — restarting pod as safe default.",
        )

    def _validate_plan(self, data: dict, anomaly: Anomaly) -> RemediationPlan:
        """Parse LLM plan output and enforce repo schema."""
        valid_actions = {"restart_pod", "patch_memory_limit", "explain_only"}
        valid_blast = {"low", "medium", "high"}

        action = data.get("action", "")
        if action not in valid_actions:
            logger.warning("plan() returned invalid action %r, using fallback", action)
            return self._fallback_plan(anomaly)

        blast_radius = data.get("blast_radius", "low")
        if blast_radius not in valid_blast:
            blast_radius = "low"

        confidence = data.get("confidence", 0.7)
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            confidence = 0.7

        params = data.get("params", {})
        if not isinstance(params, dict):
            params = {}

        # Enforce OOMKilled must have memory_limit in params
        if action == "patch_memory_limit" and "memory_limit" not in params:
            params["memory_limit"] = "384Mi"

        return RemediationPlan(
            action=action,
            target_resource=data.get("target_resource", anomaly.get("affected_resource", "unknown")),
            namespace=data.get("namespace", anomaly.get("namespace", "default")),
            params=params,
            confidence=float(confidence),
            blast_radius=blast_radius,
            reason=data.get("reason", ""),
        )

    def chat_text(self, messages: List[Dict[str, str]], temperature: float = 0.0) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM request failed: {exc.code} {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Could not reach LLM endpoint: {exc}") from exc

        return raw["choices"][0]["message"]["content"]

    def _strip_code_fences(self, text: str) -> str:
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        return text.strip()

    def _validate_anomaly(self, item: Any) -> Anomaly | None:
        if not isinstance(item, dict):
            return None

        required_fields = {"type", "severity", "affected_resource", "namespace", "confidence"}
        if not required_fields.issubset(item.keys()):
            return None

        anomaly_type = item.get("type")
        severity = item.get("severity")
        affected_resource = item.get("affected_resource")
        namespace = item.get("namespace")
        confidence = item.get("confidence")

        if anomaly_type not in VALID_TYPES:
            return None
        if severity not in VALID_SEVERITIES:
            return None
        if not isinstance(affected_resource, str) or not affected_resource.strip():
            return None
        if not isinstance(namespace, str) or not namespace.strip():
            return None
        if isinstance(confidence, bool):
            return None
        if not isinstance(confidence, (int, float)):
            return None

        return Anomaly(
            type=anomaly_type,
            severity=severity,
            affected_resource=affected_resource,
            namespace=namespace,
            confidence=float(confidence),
        )
