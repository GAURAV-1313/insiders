# IncidentAudit Soroban Smart Contract

Stores K8sWhisperer incident records on the Stellar blockchain.

## Functions

- `store_incident(incident_id, anomaly_type, severity, namespace, affected_resource, action, timestamp)` -- Writes a new record, returns updated count
- `get_incident(incident_id)` -- Reads a record by ID
- `get_count()` -- Returns total incidents stored

## Build

```bash
cargo build --target wasm32-unknown-unknown --release
```

## Deploy

```bash
stellar contract deploy \
  --wasm target/wasm32-unknown-unknown/release/incident_audit.wasm \
  --source <your-key> \
  --network testnet
```

## Deployed Instance

Contract ID: `CAVBWCYJP2AXAEUJCAW3AUTBKZ2TUHZXIVGJET66PZECJQDDZ3YU7RAP`
Network: Stellar Testnet
