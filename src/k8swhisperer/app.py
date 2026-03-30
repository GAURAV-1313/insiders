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
        self.runtime.log("[app] scanning cluster (pods + deployments + nodes)...")
        events = self.runtime.cluster.scan_cluster()

        # Also scan deployments and nodes for new anomaly types
        try:
            deploy_events = self.runtime.cluster.scan_deployments(self.runtime.cluster.namespace)
            for e in deploy_events:
                e.setdefault("kind", "deployment")
            events.extend(deploy_events)
        except Exception:
            pass
        try:
            node_events = self.runtime.cluster.scan_nodes()
            for e in node_events:
                e.setdefault("kind", "node")
            events.extend(node_events)
        except Exception:
            pass

        if not events:
            self.runtime.log("[app] no resources found in cluster")
            return

        pod_count = sum(1 for e in events if e.get("kind", "pod") == "pod")
        deploy_count = sum(1 for e in events if e.get("kind") == "deployment")
        node_count = sum(1 for e in events if e.get("kind") == "node")
        self.runtime.log(f"[app] scanned {pod_count} pod(s), {deploy_count} deployment(s), {node_count} node(s)")

        all_anomalies = self.runtime.llm.classify(events)
        if not all_anomalies:
            self.runtime.log("[app] cluster healthy -- no anomalies detected")
            return

        # Step 2: filter pods on remediation cooldown
        active_anomalies = [
            a for a in all_anomalies
            if not self._is_on_cooldown(a.get("affected_resource", ""))
        ]
        if not active_anomalies:
            skipped = [a.get("affected_resource", "?") for a in all_anomalies]
            self.runtime.log(
                f"[app] {len(all_anomalies)} anomaly(s) on cooldown -- skipping: {skipped}"
            )
            return

        cooldown_count = len(all_anomalies) - len(active_anomalies)
        self.runtime.log(
            f"[app] {len(active_anomalies)} anomaly(s) detected"
            + (f" ({cooldown_count} on cooldown)" if cooldown_count else "")
        )

        # Step 3: run full pipeline for each anomaly as its own incident
        for i, anomaly in enumerate(active_anomalies, 1):
            state: ClusterState = create_initial_state()
            state["events"] = events
            state["anomalies"] = [anomaly]
            thread_id = state["incident_id"]
            pod_name = anomaly.get("affected_resource", "")
            atype = anomaly.get("type", "unknown")
            severity = anomaly.get("severity", "?")
            self.runtime.log(
                f"\n[app] --- incident {i}/{len(active_anomalies)} [{thread_id[:8]}] ---"
            )
            self.runtime.log(
                f"[app] type={atype}  severity={severity}  resource={pod_name}"
            )
            try:
                result = self.graph.invoke(
                    state,
                    config={"configurable": {"thread_id": thread_id}},
                )
                # Mark pod as remediated to enforce cooldown on next scan
                if pod_name:
                    self._mark_remediated(pod_name)
                exec_status = result.get("execution_status", "?")
                plan_action = result.get("plan", {}).get("action", "?")
                self.runtime.log(
                    f"[app] result: action={plan_action}  status={exec_status}"
                )
                if exec_status == "verified":
                    self.runtime.log(f"[app] [OK] incident {thread_id[:8]} resolved successfully")
                elif exec_status == "awaiting_approval":
                    self.runtime.log(f"[app] [HITL] incident {thread_id[:8]} waiting for human approval")
                elif exec_status == "rejected":
                    self.runtime.log(f"[app] [REJECTED] incident {thread_id[:8]} was rejected by human")
                elif exec_status == "explained":
                    self.runtime.log(f"[app] [INFO] incident {thread_id[:8]} explained (no action taken)")
                else:
                    self.runtime.log(f"[app] incident {thread_id[:8]} completed: {exec_status}")
            except Exception as exc:
                self.runtime.log(f"[app] [ERROR] incident {thread_id[:8]} failed: {exc}")

    def run_forever(self) -> None:
        interval = self.runtime.settings.poll_interval_seconds
        self.runtime.log(
            f"K8sWhisperer agent running -- polling every {interval}s"
        )
        self.runtime.log(
            f"[config] safety: auto-execute when confidence>{self.runtime.settings.min_auto_confidence} "
            f"AND blast_radius=low AND action not destructive"
        )
        self.runtime.log(
            f"[config] anomaly types: CrashLoopBackOff, OOMKilled, Pending, "
            f"ImagePullBackOff, Evicted, CPUThrottling, DeploymentStalled, NodeNotReady"
        )
        iteration = 0
        while True:
            iteration += 1
            self.runtime.log(f"\n{'~' * 48}")
            self.runtime.log(f"[cycle {iteration}] scanning cluster...")
            try:
                self.run_cycle()
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                self.runtime.log(f"[cycle {iteration}] error: {exc} -- continuing")
            self.runtime.log(f"[cycle {iteration}] next scan in {interval}s")
            self.runtime.sleep(interval)


def create_app() -> K8sWhispererApp:
    return K8sWhispererApp()


def run_development_cycle() -> None:
    app = create_app()
    if _to_bool(os.getenv("K8SWHISPERER_RUN_ONCE"), default=False):
        app.run_cycle()
        return
    app.run_forever()
