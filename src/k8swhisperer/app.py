"""Application helpers for local development and demo runs."""

from __future__ import annotations

import os
import time
from typing import Dict

from k8swhisperer.bootstrap import build_runtime_from_env
from k8swhisperer.graph import LANGGRAPH_AVAILABLE, build_graph, execute_fixture_cycle
from k8swhisperer.state import ClusterState, create_initial_state


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class K8sWhispererApp:
    """Small runtime wrapper around one-cycle and continuous execution."""

    # How long to wait before re-remediating the same pod (prevents restart loops)
    COOLDOWN_SECONDS = 300  # 5 minutes

    def __init__(self) -> None:
        self.runtime = build_runtime_from_env()
        self.graph = build_graph(self.runtime) if LANGGRAPH_AVAILABLE else None
        self._remediated: Dict[str, float] = {}  # pod_name → last remediated timestamp

    def _is_on_cooldown(self, pod_name: str) -> bool:
        last = self._remediated.get(pod_name, 0)
        return (time.time() - last) < self.COOLDOWN_SECONDS

    def _mark_remediated(self, pod_name: str) -> None:
        self._remediated[pod_name] = time.time()

    def run_cycle(self) -> None:
        """Scan the cluster, classify all anomalies, and run one graph invocation per anomaly."""
        if self.graph is None:
            self.runtime.log("[app] LangGraph not installed; running fixture fallback cycle")
            state = create_initial_state()
            result = execute_fixture_cycle(state, self.runtime)
            self.runtime.log(f"[app] fixture cycle completed: {result.get('result', '')}")
            return

        # Step 1: scan and classify all pods in one pass (avoids duplicate LLM scans per anomaly)
        events = self.runtime.cluster.scan_cluster()
        if not events:
            self.runtime.log("[app] no pods found in cluster")
            return

        all_anomalies = self.runtime.llm.classify(events)
        if not all_anomalies:
            self.runtime.log("[app] no anomalies detected")
            return

        # Step 2: filter pods on remediation cooldown
        active_anomalies = [
            a for a in all_anomalies
            if not self._is_on_cooldown(a.get("affected_resource", ""))
        ]
        if not active_anomalies:
            skipped = [a.get("affected_resource", "?") for a in all_anomalies]
            self.runtime.log(
                f"[app] {len(all_anomalies)} anomaly(s) on cooldown — skipping: {skipped}"
            )
            return

        self.runtime.log(
            f"[app] {len(active_anomalies)} active anomaly(s) to process "
            f"({len(all_anomalies) - len(active_anomalies)} on cooldown)"
        )

        # Step 3: run full pipeline for each anomaly as its own incident
        for anomaly in active_anomalies:
            state: ClusterState = create_initial_state()
            state["events"] = events
            state["anomalies"] = [anomaly]
            thread_id = state["incident_id"]
            pod_name = anomaly.get("affected_resource", "")
            self.runtime.log(
                f"[app] incident {thread_id[:8]}… — processing {anomaly.get('type')} "
                f"on pod {pod_name}"
            )
            try:
                result = self.graph.invoke(
                    state,
                    config={"configurable": {"thread_id": thread_id}},
                )
                # Mark pod as remediated to enforce cooldown on next scan
                if pod_name:
                    self._mark_remediated(pod_name)
                self.runtime.log(
                    f"[app] incident {thread_id[:8]}… done: "
                    f"status={result.get('execution_status', '?')} "
                    f"result={result.get('result', '')[:80]}"
                )
            except Exception as exc:
                self.runtime.log(f"[app] incident {thread_id[:8]}… error: {exc} — continuing")

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
            except Exception as exc:
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
