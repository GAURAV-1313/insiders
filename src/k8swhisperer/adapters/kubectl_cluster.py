"""Person 1 integration file: real kubectl-backed cluster adapter."""

from __future__ import annotations

import json
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from k8swhisperer.adapters.base import ClusterAdapter


class KubectlClusterAdapter(ClusterAdapter):
    """Wrap kubectl commands in the protocol expected by the graph.

    Person 1 should use this file as the primary integration point.
    The methods are real and usable, but the workload-resolution logic may
    need to be refined once the team finalizes the exact demo manifests.
    """

    def __init__(self, kubectl_bin: str = "kubectl", namespace: str = "production") -> None:
        self.kubectl_bin = kubectl_bin
        self.namespace = namespace

    def scan_cluster(self) -> List[Dict[str, Any]]:
        data = self._run_json(["get", "pods", "-n", self.namespace, "-o", "json"], timeout=15)
        items = data.get("items", [])
        return [self._normalize_pod(item) for item in items]

    def get_pod_logs(self, pod_name: str, namespace: str, tail_lines: int = 60) -> str:
        current_output = self._run_logs_command(["logs", pod_name, "-n", namespace])
        previous_output = self._run_logs_command(["logs", pod_name, "-n", namespace, "--previous"])
        return self._summarize_logs(
            current_output,
            previous_output,
            tail_lines=tail_lines,
        )

    def describe_pod(self, pod_name: str, namespace: str) -> str:
        return self._run_text(["describe", "pod", pod_name, "-n", namespace])

    def restart_pod(self, pod_name: str, namespace: str) -> str:
        result = self._run_completed(["delete", "pod", pod_name, "-n", namespace])
        output = (result.stdout or result.stderr).strip()
        if result.returncode == 0:
            return output or f"pod/{pod_name} deleted"

        # Slack/HITL resumes may act on a stale pod name after a replacement already exists.
        # Treat that as a safe no-op and let deployment-level verification decide the outcome.
        if "NotFound" in output or "not found" in output.lower():
            return f"pod/{pod_name} already absent; relying on deployment reconciliation"

        raise RuntimeError(
            f"kubectl command failed: delete pod {pod_name} -n {namespace}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    def patch_memory_limit(self, pod_name: str, namespace: str, memory_limit: str) -> str:
        deployment_name = self._resolve_owner_deployment(pod_name, namespace)
        output = self._run_text(
            [
                "set",
                "resources",
                f"deployment/{deployment_name}",
                "-n",
                namespace,
                f"--limits=memory={memory_limit}",
            ]
        )
        return output.strip() or f"deployment/{deployment_name} patched with memory={memory_limit}"

    def delete_pod(self, pod_name: str, namespace: str) -> str:
        """Delete a terminated/evicted pod to clean it up. Safe — pod is already not running."""
        result = self._run_completed(["delete", "pod", pod_name, "-n", namespace])
        output = (result.stdout or result.stderr).strip()
        if result.returncode == 0 or "NotFound" in output or "not found" in output.lower():
            return output or f"pod/{pod_name} deleted"
        raise RuntimeError(f"kubectl delete pod failed: {output}")

    def get_resource_state(self, resource_name: str, namespace: str) -> Dict[str, Any]:
        data = self._run_json(["get", "pod", resource_name, "-n", namespace, "-o", "json"])
        status = data.get("status", {})
        container_statuses = status.get("containerStatuses", []) or []
        restart_count = 0
        if container_statuses:
            restart_count = int(container_statuses[0].get("restartCount", 0))
        return {
            "phase": status.get("phase", "Unknown"),
            "restart_count": restart_count,
            "reason": status.get("reason", "") or self._extract_waiting_reason(container_statuses),
        }

    def _resolve_owner_deployment(self, pod_name: str, namespace: str) -> str:
        pod = self._run_json(["get", "pod", pod_name, "-n", namespace, "-o", "json"])
        owners = pod.get("metadata", {}).get("ownerReferences", []) or []
        if not owners:
            raise RuntimeError(
                f"Could not resolve a workload owner for pod '{pod_name}'. "
                "Use a Deployment-backed pod for the OOMKilled scenario."
            )

        owner = owners[0]
        kind = owner.get("kind", "")
        name = owner.get("name", "")

        if kind == "ReplicaSet":
            replica_set = self._run_json(["get", "replicaset", name, "-n", namespace, "-o", "json"])
            rs_owners = replica_set.get("metadata", {}).get("ownerReferences", []) or []
            if rs_owners and rs_owners[0].get("kind") == "Deployment":
                return str(rs_owners[0].get("name", name))

        raise RuntimeError(
            f"Unsupported owner kind '{kind}' for memory patching on pod '{pod_name}'. "
            "This isolation test expects a Deployment-backed pod."
        )

    def _normalize_pod(self, item: Dict[str, Any]) -> Dict[str, Any]:
        metadata = item.get("metadata", {})
        status = item.get("status", {})
        container_statuses = status.get("containerStatuses", []) or []

        restart_count = 0
        exit_code: Optional[int] = None
        if container_statuses:
            container = container_statuses[0]
            restart_count = int(container.get("restartCount", 0))
            exit_code = self._extract_exit_code(container)

        return {
            "pod_name": metadata.get("name", ""),
            "namespace": metadata.get("namespace", "default"),
            "status": self._extract_status(status, container_statuses),
            "restart_count": restart_count,
            "exit_code": exit_code,
        }

    def _extract_waiting_reason(self, container_statuses: List[Dict[str, Any]]) -> str:
        if not container_statuses:
            return ""
        waiting = container_statuses[0].get("state", {}).get("waiting", {}) or {}
        return waiting.get("reason", "")

    def _extract_status(self, status: Dict[str, Any], container_statuses: List[Dict[str, Any]]) -> str:
        # Evicted pods: phase=Failed, reason=Evicted at pod level (no container state)
        if status.get("reason") == "Evicted":
            return "Evicted"
        if container_statuses:
            container = container_statuses[0]
            waiting_reason = container.get("state", {}).get("waiting", {}) or {}
            if waiting_reason.get("reason"):
                return str(waiting_reason["reason"])
            terminated_reason = container.get("state", {}).get("terminated", {}) or {}
            if terminated_reason.get("reason"):
                return str(terminated_reason["reason"])
            last_terminated = container.get("lastState", {}).get("terminated", {}) or {}
            if last_terminated.get("reason"):
                return str(last_terminated["reason"])
        return str(status.get("phase", "Unknown"))

    def _extract_exit_code(self, container_status: Dict[str, Any]) -> Optional[int]:
        current_terminated = container_status.get("state", {}).get("terminated", {}) or {}
        if "exitCode" in current_terminated:
            return int(current_terminated["exitCode"])
        last_terminated = container_status.get("lastState", {}).get("terminated", {}) or {}
        if "exitCode" in last_terminated:
            return int(last_terminated["exitCode"])
        return None

    def _summarize_logs(self, *log_outputs: str, tail_lines: int = 60) -> str:
        all_lines: List[str] = []
        for output in log_outputs:
            if isinstance(output, str) and output.strip():
                all_lines.extend(
                    line for line in output.splitlines() if line.strip()
                )

        error_lines = [
            line
            for line in all_lines
            if any(word in line.upper() for word in ["ERROR", "FATAL", "WARN", "EXCEPTION", "TRACEBACK"])
        ]
        tail = all_lines[-tail_lines:] if len(all_lines) > tail_lines else all_lines

        combined = error_lines + [line for line in tail if line not in error_lines]
        return "\n".join(combined)

    def _run_logs_command(self, args: List[str]) -> str:
        result = self._run_completed(args, timeout=20)
        return result.stdout if result.returncode == 0 else ""

    def _run_json(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        output = self._run_text(args, timeout=timeout)
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {}

    def _run_completed(self, args: List[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                [self.kubectl_bin, *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"kubectl command timed out after {timeout}s: {self.kubectl_bin} {' '.join(args)}"
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"kubectl binary not found: '{self.kubectl_bin}'. "
                "Ensure kubectl is installed and in PATH, or set K8SWHISPERER_KUBECTL_BIN."
            )

    def _run_text(self, args: List[str], allow_nonzero: bool = False, timeout: int = 30) -> str:
        result = self._run_completed(args, timeout=timeout)
        if result.returncode != 0 and not allow_nonzero:
            stderr = result.stderr or ""
            if "forbidden" in stderr.lower() or "cannot" in stderr.lower():
                raise RuntimeError(
                    f"kubectl RBAC denied: {' '.join(args)}\n{stderr.strip()}"
                )
            raise RuntimeError(
                f"kubectl command failed: {' '.join(args)}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {stderr}"
            )
        return result.stdout if result.stdout else result.stderr
