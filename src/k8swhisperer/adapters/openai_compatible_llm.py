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
        """TODO Person 3.

        Expected output: one concise evidence-backed diagnosis string.
        """

        raise NotImplementedError("Person 3: implement diagnose() in openai_compatible_llm.py")

    def plan(self, anomaly: Anomaly, diagnosis: str) -> RemediationPlan:
        """TODO Person 3.

        Expected output example:
        {
          "action": "restart_pod",
          "target_resource": "payment-api-123",
          "namespace": "production",
          "params": {},
          "confidence": 0.91,
          "blast_radius": "low",
          "reason": "Transient crash loop likely resolved by pod restart."
        }
        """

        raise NotImplementedError("Person 3: implement plan() in openai_compatible_llm.py")

    def explain(self, state: ClusterState) -> str:
        """TODO Person 3.

        Expected output: a plain-English incident summary suitable for judges and audit logs.
        """

        raise NotImplementedError("Person 3: implement explain() in openai_compatible_llm.py")

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
