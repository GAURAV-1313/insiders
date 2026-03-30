"""Slack HITL notifier — supports both incoming webhook and Bot Token."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib import error, request

from k8swhisperer.adapters.base import NotifierAdapter
from k8swhisperer.state import ClusterState


class SlackNotifierAdapter(NotifierAdapter):
    def __init__(
        self,
        webhook_url: str = "",
        channel: Optional[str] = None,
        public_base_url: Optional[str] = None,
        bot_token: Optional[str] = None,
    ) -> None:
        self.webhook_url = webhook_url
        self.channel = channel
        self.public_base_url = (public_base_url or "").rstrip("/")
        self.bot_token = bot_token

    def send_hitl_request(self, state: ClusterState) -> Dict[str, Any]:
        payload = self.build_payload(state)

        if not self.bot_token and not self.webhook_url:
            print("[slack] no credentials configured — HITL notification skipped", flush=True)
            return {"status": "skipped", "reason": "no credentials"}

        try:
            if self.bot_token:
                return self._send_via_bot_token(payload)
            else:
                return self._send_via_webhook(payload, state)
        except Exception as exc:
            print(f"[slack] notification failed (non-fatal): {exc}", flush=True)
            return {"status": "failed", "error": str(exc)}

    def _send_via_bot_token(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = "https://slack.com/api/chat.postMessage"
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.bot_token}",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=15) as response:
                body = response.read().decode("utf-8", errors="replace")
                result = json.loads(body)
                if not result.get("ok"):
                    raise RuntimeError(f"Slack API error: {result.get('error')}")
                return {"status": "sent", "channel": result.get("channel"), "ts": result.get("ts")}
        except error.URLError as exc:
            raise RuntimeError(f"Could not reach Slack API: {exc}") from exc

    def _send_via_webhook(self, payload: Dict[str, Any], state: ClusterState) -> Dict[str, Any]:
        req = request.Request(
            self.webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=15) as response:
                body = response.read().decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Slack webhook failed: {exc.code} {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Could not reach Slack webhook: {exc}") from exc
        return {"incident_id": state["incident_id"], "response": body}

    def build_payload(self, state: ClusterState) -> Dict[str, Any]:
        anomaly = state["anomalies"][0] if state.get("anomalies") else {}
        plan = state.get("plan", {})
        approve_url = self._decision_url(state["incident_id"], approved=True)
        reject_url = self._decision_url(state["incident_id"], approved=False)

        payload: Dict[str, Any] = {
            "text": f"K8sWhisperer approval required for incident {state['incident_id']}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*Approval required*\n"
                            f"*Incident:* `{state['incident_id']}`\n"
                            f"*Anomaly:* `{anomaly.get('type', 'unknown')}` on `{anomaly.get('affected_resource', 'unknown')}`\n"
                            f"*Diagnosis:* {state.get('diagnosis', 'n/a')}\n"
                            f"*Plan:* `{plan.get('action', 'unknown')}` with blast radius `{plan.get('blast_radius', 'unknown')}`"
                        ),
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Approve"},
                            "style": "primary",
                            "action_id": "approve_incident",
                            **({"url": approve_url} if approve_url else {}),
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Reject"},
                            "style": "danger",
                            "action_id": "reject_incident",
                            **({"url": reject_url} if reject_url else {}),
                        },
                    ],
                },
            ],
        }
        if self.channel:
            payload["channel"] = self.channel
        return payload

    def _decision_url(self, incident_id: str, approved: bool) -> str:
        if not self.public_base_url:
            return ""
        decision = "approve" if approved else "reject"
        return f"{self.public_base_url}/webhook/slack/{decision}/{incident_id}"
