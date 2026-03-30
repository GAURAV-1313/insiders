"""Explain-and-log stage implementation."""

from __future__ import annotations

import os
import threading

from k8swhisperer.audit import append_audit_entry
from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState, new_log_entry


def _find_stellar_hook() -> str | None:
    """Locate stellar_hook.py relative to CWD or project root."""
    candidates = [
        os.path.join(os.getcwd(), "stellar", "stellar_hook.py"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "stellar", "stellar_hook.py"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)
    return None


def _submit_to_stellar(entry: dict) -> None:
    """Submit incident to Stellar blockchain. Runs in a daemon thread."""
    secret_key = os.environ.get("STELLAR_SECRET_KEY", "")
    if not secret_key:
        return

    incident_id = entry.get("incident_id", "?")[:12]
    anomaly = entry.get("anomaly", {})
    plan = entry.get("plan", {})

    print(
        f"[stellar] submitting incident {incident_id} to Stellar blockchain...",
        flush=True,
    )
    print(
        f"[stellar]   type={anomaly.get('type', '?')} "
        f"action={plan.get('action', '?')} "
        f"resource={anomaly.get('affected_resource', '?')}",
        flush=True,
    )

    hook_path = _find_stellar_hook()
    if not hook_path:
        print("[stellar] stellar_hook.py not found -- skipping", flush=True)
        return

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("stellar_hook", hook_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        tx_hash = mod.submit_incident_to_stellar(entry)

        print(f"[stellar] ON-CHAIN: incident {incident_id} stored successfully", flush=True)
        print(f"[stellar]   TX hash : {tx_hash}", flush=True)
        print(
            f"[stellar]   Explorer: https://stellar.expert/explorer/testnet/tx/{tx_hash}",
            flush=True,
        )
    except ImportError as exc:
        print(f"[stellar] stellar-sdk not installed ({exc}) -- pip install stellar-sdk", flush=True)
    except KeyError as exc:
        print(f"[stellar] missing env var: {exc} -- check .env", flush=True)
    except Exception as exc:
        print(f"[stellar] submission failed: {exc}", flush=True)


def run(state: ClusterState, runtime: Runtime) -> ClusterState:
    runtime.log("[explain] generating human-readable summary")
    state["explanation"] = runtime.llm.explain(state)
    runtime.log(f"[explain] {state['explanation']}")
    entry = new_log_entry(state)
    # Always load from disk so multi-anomaly dispatch accumulates entries correctly
    from k8swhisperer.audit import load_audit_log
    existing = load_audit_log(runtime.settings.audit_log_path)
    state["audit_log"] = append_audit_entry(
        runtime.settings.audit_log_path,
        existing,
        entry,
    )

    # Auto-submit to Stellar blockchain (non-blocking daemon thread)
    if os.environ.get("STELLAR_SECRET_KEY"):
        runtime.log("[explain] queuing Stellar blockchain submission...")
        threading.Thread(
            target=_submit_to_stellar,
            args=(entry,),
            daemon=True,
        ).start()
    else:
        runtime.log("[explain] Stellar submission skipped (STELLAR_SECRET_KEY not set)")

    return state

