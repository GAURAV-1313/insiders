"""
Slack notification module.

Two functions:
  post_hitl_approval_request  — sends a Block Kit message with Approve/Reject buttons
  post_incident_summary       — sends a plain summary after resolution
"""

import os
import json
import requests

try:
    from config import SLACK_WEBHOOK_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
except ImportError:
    SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
    SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID", "#k8s-alerts")


# Severity → emoji mapping for visual triage
SEVERITY_EMOJI = {
    "CRITICAL": "🚨",
    "HIGH": "🔴",
    "MEDIUM": "🟡",
    "LOW": "🟢",
}

BLAST_RADIUS_EMOJI = {
    "low": "🟢 Low",
    "medium": "🟡 Medium",
    "high": "🔴 High",
}


def post_hitl_approval_request(
    incident_id: str,
    anomaly: dict,
    diagnosis: str,
    plan: dict,
    webhook_base_url: str,
) -> bool:
    """
    Send a Slack Block Kit message asking for human approval.

    The message includes:
    - What broke (anomaly type + affected pod)
    - Why it broke (root cause)
    - What the agent wants to do (action + blast radius)
    - Approve / Reject buttons that POST to the webhook server

    Returns True if Slack accepted the message, False otherwise.
    """
    severity = anomaly.get("severity", "UNKNOWN")
    emoji = SEVERITY_EMOJI.get(severity, "⚪")
    blast = BLAST_RADIUS_EMOJI.get(plan.get("blast_radius", "high"), "🔴 High")

    # Truncate diagnosis for display — keep it readable in Slack
    diagnosis_short = diagnosis[:400] + "..." if len(diagnosis) > 400 else diagnosis

    blocks = [
        # Header
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} K8sWhisperer — Human Approval Required",
            },
        },
        {"type": "divider"},
        # Incident overview
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Incident ID:*\n`{incident_id}`"},
                {"type": "mrkdwn", "text": f"*Anomaly Type:*\n`{anomaly.get('type', 'Unknown')}`"},
                {"type": "mrkdwn", "text": f"*Affected Pod:*\n`{anomaly.get('affected_resource', 'Unknown')}`"},
                {"type": "mrkdwn", "text": f"*Namespace:*\n`{anomaly.get('namespace', 'Unknown')}`"},
                {"type": "mrkdwn", "text": f"*Severity:*\n{emoji} {severity}"},
                {"type": "mrkdwn", "text": f"*Blast Radius:*\n{blast}"},
            ],
        },
        {"type": "divider"},
        # Root cause
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Root Cause:*\n{diagnosis_short}",
            },
        },
        {"type": "divider"},
        # Proposed action
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Proposed Action:*\n"
                    f"`{plan.get('action_type', 'unknown')}` on `{plan.get('target_resource', 'unknown')}`\n"
                    f"*Parameters:* `{json.dumps(plan.get('parameters', {}))}`\n"
                    f"*Agent confidence:* {int(plan.get('confidence', 0) * 100)}%\n"
                    f"*Reasoning:* {plan.get('reasoning', 'No reasoning provided.')}"
                ),
            },
        },
        {"type": "divider"},
        # Approve / Reject buttons
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ Approve"},
                    "style": "primary",
                    "value": incident_id,
                    "action_id": "hitl_approve",
                    "url": f"{webhook_base_url}/hitl/approve/{incident_id}",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ Reject"},
                    "style": "danger",
                    "value": incident_id,
                    "action_id": "hitl_reject",
                    "url": f"{webhook_base_url}/hitl/reject/{incident_id}",
                },
            ],
        },
        # Footer
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "⏳ Waiting for your decision. The agent is paused until you respond.",
                }
            ],
        },
    ]

    return _send_blocks(blocks)


def post_incident_summary(
    incident_id: str,
    anomaly: dict,
    slack_summary: str,
    auto_executed: bool,
    success: bool,
) -> bool:
    """
    Post a plain resolution summary after an incident is handled.
    """
    severity = anomaly.get("severity", "UNKNOWN")
    emoji = SEVERITY_EMOJI.get(severity, "⚪")
    status_emoji = "✅" if success else "❌"
    path = "Auto-executed" if auto_executed else "Human approved"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{status_emoji} K8sWhisperer — Incident {incident_id} Resolved",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Anomaly:*\n`{anomaly.get('type', 'Unknown')}`"},
                {"type": "mrkdwn", "text": f"*Pod:*\n`{anomaly.get('affected_resource', 'Unknown')}`"},
                {"type": "mrkdwn", "text": f"*Severity:*\n{emoji} {severity}"},
                {"type": "mrkdwn", "text": f"*Action path:*\n{path}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": slack_summary},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Full details in `audit_log.json` — incident ID `{incident_id}`"}
            ],
        },
    ]

    return _send_blocks(blocks)


def _send_blocks(blocks: list) -> bool:
    """
    Internal helper — POST blocks to the Slack Incoming Webhook URL.
    Returns True on HTTP 200, False otherwise.
    """
    if not SLACK_WEBHOOK_URL:
        print("[Slack] WARNING: SLACK_WEBHOOK_URL not set — message not sent.")
        print("[Slack] Blocks that would have been sent:")
        print(json.dumps(blocks, indent=2))
        return False

    payload = {"blocks": blocks}
    try:
        resp = requests.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            timeout=10,
        )
        if resp.status_code == 200:
            print(f"[Slack] Message sent successfully.")
            return True
        else:
            print(f"[Slack] ERROR: HTTP {resp.status_code} — {resp.text}")
            return False
    except requests.RequestException as e:
        print(f"[Slack] ERROR: Could not reach Slack — {e}")
        return False
