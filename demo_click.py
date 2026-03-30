"""One-click demo runner for K8sWhisperer.

What this script does:
1. Applies RBAC + all scenario manifests.
2. Starts run.py (agent loop + webhook server).
3. Streams backend logs in real time.
4. Notifies clearly when HITL approval is triggered.
5. Prints explanation summaries from audit_log.json as soon as they are written.

Usage:
    python demo_click.py
    python demo_click.py --reset-audit
    python demo_click.py --skip-apply
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
AUDIT_LOG = ROOT / "audit_log.json"
RBAC_PATH = ROOT / "rbac" / "k8s-rbac.yaml"
SCENARIOS_DIR = ROOT / "scenarios"


def _print(msg: str) -> None:
    print(msg, flush=True)


def _read_env_var(name: str) -> str:
    """Read from process env first, then from local .env file."""
    if os.getenv(name):
        return os.getenv(name, "")

    env_path = ROOT / ".env"
    if not env_path.exists():
        return ""
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip()
    return ""


def _run_cmd(args: Iterable[str]) -> None:
    cmd = list(args)
    _print(f"[demo] $ {' '.join(cmd)}")
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.stdout.strip():
        _print(proc.stdout.strip())
    if proc.returncode != 0:
        if proc.stderr.strip():
            _print(proc.stderr.strip())
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}")


def _apply_demo_manifests() -> None:
    if RBAC_PATH.exists():
        _run_cmd(["kubectl", "apply", "-f", str(RBAC_PATH)])
    else:
        _print(f"[demo] RBAC file not found: {RBAC_PATH}")
    _run_cmd(["kubectl", "apply", "-f", str(SCENARIOS_DIR)])
    _run_cmd(["kubectl", "get", "pods", "-n", "production"])


def _load_audit_entries() -> list[dict]:
    if not AUDIT_LOG.exists():
        return []
    try:
        return json.loads(AUDIT_LOG.read_text(encoding="utf-8"))
    except Exception:
        return []


def _watch_explanations(stop_event: threading.Event) -> None:
    """Watch audit_log.json and print new explanations immediately."""
    seen_ids = {entry.get("incident_id", "") for entry in _load_audit_entries()}
    while not stop_event.is_set():
        entries = _load_audit_entries()
        for entry in entries:
            incident_id = entry.get("incident_id", "")
            if not incident_id or incident_id in seen_ids:
                continue
            seen_ids.add(incident_id)
            anomaly = entry.get("anomaly", {})
            plan = entry.get("plan", {})
            exec_status = entry.get("execution_status", "")
            atype = anomaly.get("type", "unknown")
            severity = anomaly.get("severity", "?")
            resource = anomaly.get("affected_resource", "unknown")

            if exec_status == "verified":
                tag = "[RESOLVED]"
            elif exec_status == "awaiting_approval":
                tag = "[AWAITING APPROVAL]"
            elif exec_status == "rejected":
                tag = "[REJECTED]"
            elif exec_status == "explained":
                tag = "[EXPLAINED]"
            else:
                tag = f"[{exec_status.upper()}]"

            _print(f"\n{'=' * 56}")
            _print(f"  INCIDENT {tag}")
            _print(f"  ID:       {incident_id[:12]}...")
            _print(f"  Type:     {atype} ({severity})")
            _print(f"  Resource: {resource}")
            _print(f"  Action:   {plan.get('action', '?')} (blast={plan.get('blast_radius', '?')})")
            _print(f"  Status:   {exec_status}")
            explanation = entry.get("explanation", "")
            if explanation:
                _print(f"  Summary:  {explanation[:200]}")
            _print(f"{'=' * 56}\n")
        time.sleep(2)


def _start_backend() -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    return subprocess.Popen(
        [sys.executable, "run.py"],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all demo scenarios in one click.")
    parser.add_argument(
        "--reset-audit",
        action="store_true",
        help="Reset audit_log.json before starting demo.",
    )
    parser.add_argument(
        "--skip-apply",
        action="store_true",
        help="Do not apply RBAC/scenario manifests.",
    )
    args = parser.parse_args()

    _print("=" * 64)
    _print("  K8sWhisperer -- Autonomous Kubernetes Incident Response")
    _print("  DevOps x AI/ML Hackathon Demo")
    _print("=" * 64)
    _print("")

    public_base_url = _read_env_var("K8SWHISPERER_PUBLIC_BASE_URL")
    if public_base_url:
        _print(f"[config] Slack callback URL: {public_base_url}")
    else:
        _print("[config] No external callback URL set (use browser dashboard for approvals)")

    if args.reset_audit:
        AUDIT_LOG.write_text("[]\n", encoding="utf-8")
        _print("[config] Audit log reset")

    if not args.skip_apply:
        _print("\n[setup] Applying RBAC + scenario manifests to cluster...")
        _apply_demo_manifests()

    stop_event = threading.Event()
    watcher = threading.Thread(target=_watch_explanations, args=(stop_event,), daemon=True)
    watcher.start()

    backend = _start_backend()
    _print("")
    _print("-" * 64)
    _print("  DASHBOARD:  http://localhost:9000/dashboard")
    _print("  APPROVE:    http://localhost:9000/approve/<incident_id>")
    _print("  REJECT:     http://localhost:9000/reject/<incident_id>")
    _print("-" * 64)
    _print("")
    _print("[agent] Monitoring cluster... (Ctrl+C to stop)\n")

    try:
        assert backend.stdout is not None
        for raw_line in backend.stdout:
            line = raw_line.rstrip("\n")
            print(line, flush=True)

            if "[hitl] requesting human approval" in line:
                _print("\a")
                _print("*" * 56)
                _print("  HUMAN APPROVAL REQUIRED")
                _print("  Approve via dashboard: http://localhost:9000/dashboard")
                if public_base_url:
                    _print(f"  Or via Slack buttons")
                _print("*" * 56)
            elif "[webhook] decision received:" in line:
                _print(f"[HITL] Decision received: {line.split('decision received:')[-1].strip()}")
            elif "resume completed" in line and "[webhook] incident" in line:
                _print(f"[HITL] Pipeline resumed after approval")

            if backend.poll() is not None:
                break
    except KeyboardInterrupt:
        _print("\n[demo] stopping demo...")
    finally:
        stop_event.set()
        if backend.poll() is None:
            backend.terminate()
            try:
                backend.wait(timeout=8)
            except subprocess.TimeoutExpired:
                backend.kill()
        _print("[demo] stopped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
