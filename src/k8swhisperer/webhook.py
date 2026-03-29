"""FastAPI webhook seam for HITL resume."""

from __future__ import annotations

from typing import Any, Dict

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from langgraph.types import Command

    FASTAPI_AVAILABLE = True
except ImportError as exc:  # pragma: no cover - exercised only without deps
    FASTAPI_AVAILABLE = False
    FASTAPI_IMPORT_ERROR = exc


def create_webhook_app(graph: Any) -> Any:
    if not FASTAPI_AVAILABLE:  # pragma: no cover - depends on local install
        raise RuntimeError(
            "FastAPI is not installed. Install dependencies with 'pip install -r requirements.txt' "
            f"before creating the webhook app. Import error: {FASTAPI_IMPORT_ERROR}"
        )

    app = FastAPI()

    def _resume_incident(incident_id: str, approved: bool) -> Dict[str, Any]:
        graph.invoke(
            Command(resume={"approved": approved}),
            config={"configurable": {"thread_id": incident_id}},
        )
        return {"status": "ok", "incident_id": incident_id, "approved": approved}

    @app.post("/webhook/slack")
    def slack_callback(payload: Dict[str, Any]) -> Dict[str, Any]:
        incident_id = payload["incident_id"]
        approved = bool(payload.get("approved", False))
        return _resume_incident(incident_id, approved)

    @app.get("/webhook/slack/approve/{incident_id}", response_class=HTMLResponse)
    def slack_approve(incident_id: str) -> HTMLResponse:
        _resume_incident(incident_id, True)
        return HTMLResponse(
            _decision_page(
                title="Approval Recorded",
                body=(
                    f"Incident <code>{incident_id}</code> was approved. "
                    "K8sWhisperer will resume execution now."
                ),
                accent="#16a34a",
            )
        )

    @app.get("/webhook/slack/reject/{incident_id}", response_class=HTMLResponse)
    def slack_reject(incident_id: str) -> HTMLResponse:
        _resume_incident(incident_id, False)
        return HTMLResponse(
            _decision_page(
                title="Rejection Recorded",
                body=(
                    f"Incident <code>{incident_id}</code> was rejected. "
                    "K8sWhisperer will skip execution and continue logging."
                ),
                accent="#dc2626",
            )
        )

    return app


def _decision_page(title: str, body: str, accent: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #0f172a;
      color: #e2e8f0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .card {{
      max-width: 520px;
      margin: 24px;
      padding: 28px 32px;
      border-radius: 16px;
      background: #111827;
      border: 1px solid #1f2937;
      box-shadow: 0 18px 40px rgba(0, 0, 0, 0.28);
    }}
    h1 {{
      margin: 0 0 12px;
      color: {accent};
      font-size: 28px;
    }}
    p {{
      margin: 0;
      line-height: 1.6;
      color: #cbd5e1;
    }}
    code {{
      background: #1f2937;
      padding: 2px 6px;
      border-radius: 6px;
      color: #f8fafc;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{title}</h1>
    <p>{body}</p>
  </div>
</body>
</html>"""
