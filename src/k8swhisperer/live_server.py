"""Combined live server for webhook callbacks and background agent execution.

Run with:
    PYTHONPATH=src uvicorn k8swhisperer.live_server:app --host 0.0.0.0 --port 8000

This keeps the FastAPI webhook and the LangGraph workflow in the same process,
which is required when using the in-memory MemorySaver checkpointer.
"""

from __future__ import annotations

import threading

from fastapi import FastAPI

from k8swhisperer.app import create_app
from k8swhisperer.webhook import create_webhook_app

_whisperer = create_app()
app: FastAPI = create_webhook_app(_whisperer.graph)

_loop_thread: threading.Thread | None = None
_loop_lock = threading.Lock()


def _run_agent_loop() -> None:
    _whisperer.run_forever()


@app.on_event("startup")
def _start_agent_loop() -> None:
    global _loop_thread
    with _loop_lock:
        if _loop_thread is not None and _loop_thread.is_alive():
            return
        _loop_thread = threading.Thread(
            target=_run_agent_loop,
            name="k8swhisperer-agent-loop",
            daemon=True,
        )
        _loop_thread.start()
