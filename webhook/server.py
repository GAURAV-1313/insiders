"""
FastAPI webhook server — receives Slack Approve/Reject button callbacks
and resumes the paused LangGraph agent.

Start with:
    uvicorn webhook.server:app --host 0.0.0.0 --port 8000 --reload

With ngrok:
    ngrok http --domain=YOUR-STATIC-DOMAIN.ngrok-free.app 8000

Endpoints:
  GET  /health                 — liveness check
  GET  /hitl/approve/{id}      — approve action (Slack button redirect)
  GET  /hitl/reject/{id}       — reject action  (Slack button redirect)
  POST /hitl/callback          — Slack interactive component callback (alternative)
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="K8sWhisperer HITL Webhook")

# ---------------------------------------------------------------------------
# Pending approval registry
# Maps incident_id → asyncio.Event so the agent node can await it
# ---------------------------------------------------------------------------
_pending: dict[str, dict] = {}
# Structure per entry:
# {
#   "event": asyncio.Event,
#   "decision": None | "approved" | "rejected",
#   "decided_at": None | ISO timestamp,
#   "anomaly": dict,
#   "plan": dict,
# }


def register_pending(incident_id: str, anomaly: dict, plan: dict) -> asyncio.Event:
    """
    Called by the hitl_node BEFORE sending the Slack message.
    Returns an asyncio.Event the agent node should await.
    """
    event = asyncio.Event()
    _pending[incident_id] = {
        "event": event,
        "decision": None,
        "decided_at": None,
        "anomaly": anomaly,
        "plan": plan,
    }
    print(f"[Webhook] Registered pending approval for incident {incident_id}")
    return event


def get_decision(incident_id: str) -> str | None:
    """
    After the event is set, call this to get 'approved' or 'rejected'.
    Returns None if the incident_id is not found.
    """
    entry = _pending.get(incident_id)
    if entry is None:
        return None
    return entry.get("decision")


def cleanup(incident_id: str):
    """Remove from registry once handled."""
    _pending.pop(incident_id, None)


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "pending_approvals": len(_pending)}


@app.get("/hitl/approve/{incident_id}", response_class=HTMLResponse)
async def approve(incident_id: str):
    """
    Called when engineer clicks the Approve button in Slack.
    Slack buttons open this URL in the browser — we serve a simple HTML page.
    """
    entry = _pending.get(incident_id)
    if entry is None:
        return HTMLResponse(
            content=_html_page("Not Found", f"Incident <code>{incident_id}</code> not found or already handled.", "orange"),
            status_code=404,
        )

    if entry["decision"] is not None:
        return HTMLResponse(
            content=_html_page(
                "Already Decided",
                f"Incident <code>{incident_id}</code> was already <b>{entry['decision']}</b> at {entry['decided_at']}.",
                "grey",
            )
        )

    entry["decision"] = "approved"
    entry["decided_at"] = datetime.now(timezone.utc).isoformat()
    entry["event"].set()

    print(f"[Webhook] Incident {incident_id} APPROVED")

    action = entry["plan"].get("action_type", "unknown action")
    target = entry["plan"].get("target_resource", "unknown resource")

    return HTMLResponse(
        content=_html_page(
            "Action Approved",
            f"You approved: <b>{action}</b> on <code>{target}</code>.<br><br>The agent will now execute this action.",
            "green",
        )
    )


@app.get("/hitl/reject/{incident_id}", response_class=HTMLResponse)
async def reject(incident_id: str):
    """
    Called when engineer clicks the Reject button in Slack.
    """
    entry = _pending.get(incident_id)
    if entry is None:
        return HTMLResponse(
            content=_html_page("Not Found", f"Incident <code>{incident_id}</code> not found or already handled.", "orange"),
            status_code=404,
        )

    if entry["decision"] is not None:
        return HTMLResponse(
            content=_html_page(
                "Already Decided",
                f"Incident <code>{incident_id}</code> was already <b>{entry['decision']}</b> at {entry['decided_at']}.",
                "grey",
            )
        )

    entry["decision"] = "rejected"
    entry["decided_at"] = datetime.now(timezone.utc).isoformat()
    entry["event"].set()

    print(f"[Webhook] Incident {incident_id} REJECTED")

    action = entry["plan"].get("action_type", "unknown action")

    return HTMLResponse(
        content=_html_page(
            "Action Rejected",
            f"You rejected: <b>{action}</b>.<br><br>The agent will log this and skip execution.",
            "red",
        )
    )


@app.post("/hitl/callback")
async def slack_interactive_callback(request: Request):
    """
    Alternative: Slack interactive component POST callback.
    Slack sends application/x-www-form-urlencoded with a 'payload' field.
    Use this if you configure Slack's Interactivity Request URL instead of button URLs.
    """
    try:
        form = await request.form()
        payload = json.loads(form.get("payload", "{}"))

        actions = payload.get("actions", [])
        if not actions:
            return JSONResponse({"ok": True})

        action = actions[0]
        action_id = action.get("action_id", "")
        incident_id = action.get("value", "")

        if action_id == "hitl_approve":
            entry = _pending.get(incident_id)
            if entry and entry["decision"] is None:
                entry["decision"] = "approved"
                entry["decided_at"] = datetime.now(timezone.utc).isoformat()
                entry["event"].set()
                print(f"[Webhook] Incident {incident_id} APPROVED via callback")

        elif action_id == "hitl_reject":
            entry = _pending.get(incident_id)
            if entry and entry["decision"] is None:
                entry["decision"] = "rejected"
                entry["decided_at"] = datetime.now(timezone.utc).isoformat()
                entry["event"].set()
                print(f"[Webhook] Incident {incident_id} REJECTED via callback")

        # Slack expects HTTP 200 with empty body to dismiss the "loading" spinner
        return JSONResponse({"ok": True})

    except Exception as e:
        print(f"[Webhook] Callback error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.get("/pending")
async def list_pending():
    """Debug endpoint — see what's waiting for approval."""
    return {
        incident_id: {
            "decision": entry["decision"],
            "decided_at": entry["decided_at"],
            "anomaly_type": entry["anomaly"].get("type"),
            "affected_resource": entry["anomaly"].get("affected_resource"),
        }
        for incident_id, entry in _pending.items()
    }


# ---------------------------------------------------------------------------
# HTML helper — simple response page shown after button click
# ---------------------------------------------------------------------------

def _html_page(title: str, body: str, color: str) -> str:
    color_map = {
        "green": "#22c55e",
        "red": "#ef4444",
        "orange": "#f97316",
        "grey": "#6b7280",
    }
    hex_color = color_map.get(color, "#6b7280")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>K8sWhisperer — {title}</title>
  <style>
    body {{ font-family: -apple-system, sans-serif; display: flex; align-items: center;
            justify-content: center; height: 100vh; margin: 0; background: #0f172a; color: #f8fafc; }}
    .card {{ background: #1e293b; padding: 2rem 3rem; border-radius: 12px;
             border-left: 4px solid {hex_color}; max-width: 480px; text-align: center; }}
    h1 {{ color: {hex_color}; margin-bottom: 1rem; }}
    code {{ background: #334155; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{title}</h1>
    <p>{body}</p>
    <p style="color:#94a3b8; font-size:0.85em; margin-top:1.5rem;">You can close this tab.</p>
  </div>
</body>
</html>"""
