"""Application helpers for local development and demo runs."""

from __future__ import annotations

import os

from k8swhisperer.bootstrap import build_runtime_from_env
from k8swhisperer.graph import LANGGRAPH_AVAILABLE, build_graph, execute_fixture_cycle
from k8swhisperer.state import create_initial_state


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class K8sWhispererApp:
    """Small runtime wrapper around one-cycle and continuous execution."""

    def __init__(self) -> None:
        self.runtime = build_runtime_from_env()
        self.graph = build_graph(self.runtime) if LANGGRAPH_AVAILABLE else None

    def run_cycle(self):
        state = create_initial_state()
        if self.graph is not None:
            result = self.graph.invoke(
                state,
                config={"configurable": {"thread_id": state["incident_id"]}},
            )
        else:
            self.runtime.log("[app] LangGraph not installed; running fixture fallback cycle")
            result = execute_fixture_cycle(state, self.runtime)

        self.runtime.log(f"[app] cycle completed with result={result.get('result', '')}")
        return result

    def run_forever(self) -> None:
        self.runtime.log(
            f"K8sWhisperer running — polling every {self.runtime.settings.poll_interval_seconds}s"
        )
        iteration = 0
        while True:
            iteration += 1
            self.runtime.log(f"\n[loop] cycle {iteration}")
            try:
                self.run_cycle()
            except KeyboardInterrupt:
                raise
            except Exception as exc:  # pragma: no cover - exercised in real integration
                self.runtime.log(f"[loop] cycle error: {exc} — continuing")
            self.runtime.log(f"[loop] sleeping {self.runtime.settings.poll_interval_seconds}s...")
            self.runtime.sleep(self.runtime.settings.poll_interval_seconds)


def create_app() -> K8sWhispererApp:
    return K8sWhispererApp()


def run_development_cycle() -> None:
    app = create_app()
    if _to_bool(os.getenv("K8SWHISPERER_RUN_ONCE"), default=False):
        app.run_cycle()
        return
    app.run_forever()
