"""
K8sWhisperer → Stellar integration hook.

After every incident is logged to audit_log.json, this module
submits the incident record to the deployed Soroban IncidentAudit contract
on Stellar Testnet, creating an immutable on-chain audit trail.

Usage:
    python stellar_hook.py                    # submit latest incident from audit_log.json
    python stellar_hook.py --incident-id <id> # submit specific incident

Environment variables required:
    STELLAR_SECRET_KEY   — Stellar keypair secret (S...)
    STELLAR_CONTRACT_ID  — Deployed IncidentAudit contract ID (C...)
    STELLAR_PUBLIC_KEY   — Corresponding public key (G...)
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

TESTNET_RPC = "https://soroban-testnet.stellar.org"
TESTNET_PASSPHRASE = "Test SDF Network ; September 2015"
HORIZON_URL = "https://horizon-testnet.stellar.org"
EXPLORER_BASE = "https://stellar.expert/explorer/testnet"


def _load_stellar():
    """Import stellar-sdk lazily so main K8sWhisperer still works without it."""
    try:
        import stellar_sdk  # noqa: F401
        return stellar_sdk
    except ImportError:
        raise RuntimeError(
            "stellar-sdk not installed. Run: pip install stellar-sdk"
        )


def read_latest_incident(audit_log_path: str = "audit_log.json") -> dict | None:
    """Read the most recent incident from audit_log.json."""
    path = Path(audit_log_path)
    if not path.exists():
        return None
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not entries:
        return None
    return entries[-1] if isinstance(entries, list) else entries


def submit_incident_to_stellar(incident: dict) -> str:
    """
    Submit an incident record to the Soroban IncidentAudit contract.
    Returns the transaction hash on success.
    """
    sdk = _load_stellar()

    secret_key = os.environ["STELLAR_SECRET_KEY"]
    contract_id = os.environ["STELLAR_CONTRACT_ID"]

    keypair = sdk.Keypair.from_secret(secret_key)
    soroban_server = sdk.SorobanServer(TESTNET_RPC)

    source_account = soroban_server.load_account(keypair.public_key)

    anomaly = incident.get("anomaly", {})
    plan = incident.get("plan", {})

    incident_id = incident.get("incident_id", f"inc-{int(time.time())}")
    anomaly_type = anomaly.get("type", "Unknown")
    severity = anomaly.get("severity", "LOW")
    namespace = anomaly.get("namespace", "default")
    affected_resource = anomaly.get("affected_resource", "unknown")
    action = plan.get("action", "explain_only")
    timestamp = int(time.time())

    tx = (
        sdk.TransactionBuilder(
            source_account=source_account,
            network_passphrase=TESTNET_PASSPHRASE,
            base_fee=100,
        )
        .append_invoke_contract_function_op(
            contract_id=contract_id,
            function_name="store_incident",
            parameters=[
                sdk.scval.from_string(incident_id),
                sdk.scval.from_string(anomaly_type),
                sdk.scval.from_string(severity),
                sdk.scval.from_string(namespace),
                sdk.scval.from_string(affected_resource),
                sdk.scval.from_string(action),
                sdk.scval.from_uint64(timestamp),
            ],
        )
        .set_timeout(30)
        .build()
    )

    # prepare_transaction simulates + injects the Soroban footprint (stellar-sdk ≥ 11)
    tx = soroban_server.prepare_transaction(tx)
    tx.sign(keypair)

    response = soroban_server.send_transaction(tx)
    tx_hash = response.hash

    # Poll until confirmed (stellar-sdk ≥ 11 uses soroban_rpc.GetTransactionStatus)
    from stellar_sdk.soroban_rpc import GetTransactionStatus
    for _ in range(20):
        time.sleep(3)
        status = soroban_server.get_transaction(tx_hash)
        if status.status == GetTransactionStatus.SUCCESS:
            print(f"[stellar] Incident stored on-chain!")
            print(f"[stellar] TX hash  : {tx_hash}")
            print(f"[stellar] Explorer : {EXPLORER_BASE}/tx/{tx_hash}")
            return tx_hash
        if status.status == GetTransactionStatus.FAILED:
            raise RuntimeError(f"Transaction failed: {status}")

    raise TimeoutError(f"Transaction {tx_hash} did not confirm in time")


def main():
    parser = argparse.ArgumentParser(description="Submit K8sWhisperer incident to Stellar")
    parser.add_argument("--audit-log", default="audit_log.json")
    parser.add_argument("--incident-id", default=None)
    args = parser.parse_args()

    incident = read_latest_incident(args.audit_log)
    if not incident:
        print("[stellar] No incidents found in audit log.")
        return

    if args.incident_id:
        entries = json.loads(Path(args.audit_log).read_text())
        matches = [e for e in entries if e.get("incident_id") == args.incident_id]
        if not matches:
            print(f"[stellar] Incident {args.incident_id} not found.")
            return
        incident = matches[-1]

    print(f"[stellar] Submitting incident {incident.get('incident_id')} to Stellar testnet...")
    tx_hash = submit_incident_to_stellar(incident)
    print(f"[stellar] Done. {tx_hash}")


if __name__ == "__main__":
    main()
