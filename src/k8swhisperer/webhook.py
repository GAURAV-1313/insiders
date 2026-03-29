"""FastAPI webhook seam for HITL resume."""

from __future__ import annotations

from typing import Any, Dict

try:
    from fastapi import FastAPI
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

    @app.post("/webhook/slack")
    def slack_callback(payload: Dict[str, Any]) -> Dict[str, Any]:
        incident_id = payload["incident_id"]
        approved = bool(payload.get("approved", False))
        graph.invoke(
            Command(resume={"approved": approved}),
            config={"configurable": {"thread_id": incident_id}},
        )
        return {"status": "ok", "incident_id": incident_id, "approved": approved}

    return app
