"""Standalone live adapter isolation test.

Run with:
kubectl create namespace production --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f scenarios/crashloop.yaml
.venv/bin/python tests/test_kubectl_adapter_live.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from k8swhisperer.adapters.kubectl_cluster import KubectlClusterAdapter


SCENARIO = ROOT / "scenarios" / "crashloop.yaml"
NAMESPACE = "production"
CRASH_STATUSES = {"CrashLoopBackOff", "Error", "OOMKilled"}


def run_command(args):
    result = subprocess.run(args, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(args)}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result.stdout.strip() or result.stderr.strip()


def main() -> None:
    if not SCENARIO.exists():
        raise FileNotFoundError(f"Scenario file not found: {SCENARIO}")

    print("Applying crashloop scenario...")
    print(run_command(["kubectl", "apply", "-f", str(SCENARIO)]))
    print("Waiting 60 seconds for the pod to start crash cycling...")
    time.sleep(60)

    adapter = KubectlClusterAdapter()

    print("\nscan_cluster()")
    pods = adapter.scan_cluster()
    print(json.dumps(pods, indent=2))

    found = any(pod.get("status") in CRASH_STATUSES for pod in pods)
    if not found:
        raise RuntimeError("No crashing pods detected")

    for pod in pods:
        print(
            "pod="
            f"{pod.get('pod_name')} "
            f"status={pod.get('status')} "
            f"restart_count={pod.get('restart_count')} "
            f"exit_code={pod.get('exit_code')}"
        )

    crashloop_pods = [pod for pod in pods if pod.get("status") in CRASH_STATUSES]

    pod_name = crashloop_pods[0]["pod_name"]

    print("\nget_pod_logs()")
    logs = adapter.get_pod_logs(pod_name, NAMESPACE)
    print(logs or "<no logs returned>")

    print("\ndescribe_pod()")
    description = adapter.describe_pod(pod_name, NAMESPACE)
    print(description)

    print("\nrestart_pod()")
    restart_result = adapter.restart_pod(pod_name, NAMESPACE)
    print(restart_result)

    print("Waiting 10 seconds for the deployment to recreate the pod...")
    time.sleep(10)

    refreshed_pods = adapter.scan_cluster()
    recreated = next((pod for pod in refreshed_pods if pod.get("pod_name", "").startswith("payment-api-")), None)
    if recreated is None:
        raise RuntimeError("Expected the deployment to recreate a payment-api pod after restart.")

    print("\npatch_memory_limit()")
    patch_result = adapter.patch_memory_limit(recreated["pod_name"], NAMESPACE, "128Mi")
    print(patch_result)

    print("\nLive kubectl adapter isolation test completed successfully.")


if __name__ == "__main__":
    main()
