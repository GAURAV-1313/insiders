"""Explain-and-log stage implementation."""

from __future__ import annotations

import os
import threading

from k8swhisperer.audit import append_audit_entry
from k8swhisperer.runtime import Runtime
from k8swhisperer.state import ClusterState, new_log_entry


def _submit_to_stellar(entry: dict, audit_log_path: str) -> None:
    """Fire-and-forget: submit incident to Stellar blockchain if keys are configured."""
    secret_key = os.environ.get("STELLAR_SECRET_KEY", "")
    contract_id = os.environ.get(
        "STELLAR_CONTRACT_ID",
        "CAVBWCYJP2AXAEUJCAW3AUTBKZ2TUHZXIVGJET66PZECJQDDZ3YU7RAP",
    )
    if not secret_key:
        return
    try:
        import sys
        stellar_hook_path = os.path.join(
            os.path.dirname(audit_log_path), "stellar", "stellar_hook.py"
        )
        if not os.path.exists(stellar_hook_path):
            # Try relative to CWD
            stellar_hook_path = os.path.join(os.getcwd(), "stellar", "stellar_hook.py")
        if not os.path.exists(stellar_hook_path):
            return
        import importlib.util
        spec = importlib.util.spec_from_file_location("stellar_hook", stellar_hook_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        os.environ.setdefault("STELLAR_CONTRACT_ID", contract_id)
        tx_hash = mod.submit_incident_to_stellar(entry)
        print(f"[stellar] incident {entry.get('incident_id', '')[:8]} on-chain: {tx_hash}")
    except Exception as exc:
        print(f"[stellar] submission skipped: {exc}")


def run(state: ClusterState, runtime: Runtime) -> ClusterState:
    runtime.log("[explain] generating human-readable summary")
    state["explanation"] = runtime.llm.explain(state)
    runtime.log(f"[explain] {state['explanation'][:150]}...")
    entry = new_log_entry(state)
    # Always load from disk so multi-anomaly dispatch accumulates entries correctly
    from k8swhisperer.audit import load_audit_log
    existing = load_audit_log(runtime.settings.audit_log_path)
    state["audit_log"] = append_audit_entry(
        runtime.settings.audit_log_path,
        existing,
        entry,
    )
    # Auto-submit to Stellar blockchain (non-blocking, if STELLAR_SECRET_KEY is set)
    threading.Thread(
        target=_submit_to_stellar,
        args=(entry, runtime.settings.audit_log_path),
        daemon=True,
    ).start()
    return state

