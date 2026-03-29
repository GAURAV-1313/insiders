# K8sWhisperer — Stellar Blockchain Audit Dashboard

## Project Title
K8sWhisperer Immutable Incident Audit on Stellar

## Project Description
K8sWhisperer is an AI-powered Kubernetes incident response agent that automatically detects anomalies (CrashLoopBackOff, OOMKilled, Pending), diagnoses root causes using an LLM, and executes remediation actions. This Web3 extension records every incident decision permanently on the Stellar blockchain via a Soroban smart contract, creating a tamper-proof audit trail that any engineer can verify.

## Project Vision
Kubernetes clusters fail silently. When an on-call engineer asks "what happened and what was done?", audit logs stored on a mutable server can be altered or lost. By anchoring each incident record to Stellar's blockchain, we make the entire incident lifecycle — detection, diagnosis, action, result — permanently verifiable and trust-minimised. No single team member can retroactively modify what the agent did.

## Key Features
- **Soroban Smart Contract** — `store_incident()` and `get_incident()` functions store structured incident records (anomaly type, severity, namespace, pod name, action taken, timestamp) on-chain
- **React + Tailwind Dashboard** — Real-time incident browser that reads from the deployed contract via Stellar-SDK
- **Store Incidents UI** — Form to submit new incidents directly to the blockchain from the browser
- **Python Integration Hook** — `stellar_hook.py` reads `audit_log.json` (produced by K8sWhisperer) and submits each incident to the contract automatically
- **Block Explorer Links** — Every incident card links directly to stellar.expert for independent verification

## Deployed Smartcontract Details

**Contract ID:**
```
CAVBWCYJP2AXAEUJCAW3AUTBKZ2TUHZXIVGJET66PZECJQDDZ3YU7RAP
```

**Network:** Stellar Testnet

**Block Explorer:**
https://stellar.expert/explorer/testnet/contract/CAVBWCYJP2AXAEUJCAW3AUTBKZ2TUHZXIVGJET66PZECJQDDZ3YU7RAP

**Deployment transaction:**
https://stellar.expert/explorer/testnet/tx/345322b2c046894942126b4665f408259dc6476af1e3c5bf9d1269ffcf82e05b

**First incident stored on-chain:**
https://stellar.expert/explorer/testnet/tx/51a62be7ebc0577b22ad705ffd084a5d473793a6c44cc13d04c61eaebb3ba85c

**Second incident stored on-chain:**
https://stellar.expert/explorer/testnet/tx/d63ed94d0a069572f7afcb2a6588ad5a2ebd70fb64ef58f046c9ec6361f8ea89

> Screenshot of block explorer showing deployed contract: see `docs/blockexplorer.png`

## UI Screenshots
> See `docs/ui-dashboard.png` and `docs/ui-store.png`

## Project Setup Guide

### Prerequisites
- Node.js 18+
- Rust + wasm32-unknown-unknown target (`rustup target add wasm32-unknown-unknown`)
- Stellar CLI (`stellar --version`)

### 1. Install frontend dependencies
```bash
cd stellar/
npm install
```

### 2. Configure environment
```bash
cp .env.example .env
# .env already contains the deployed contract ID and public key
```

### 3. Start the frontend
```bash
npm start
# Opens at http://localhost:3000
```

### 4. (Optional) Rebuild the smart contract
```bash
cd contracts/incident-audit/
cargo +stable-x86_64-pc-windows-gnu build --target wasm32-unknown-unknown --release
```

### 5. (Optional) Deploy your own contract instance
```bash
stellar keys generate mykey --network testnet
# Fund via: https://friendbot.stellar.org?addr=<your-public-key>
stellar contract deploy \
  --wasm contracts/incident-audit/target/wasm32-unknown-unknown/release/incident_audit.wasm \
  --source mykey \
  --network testnet
```

### 6. Run the Python integration hook
```bash
# After K8sWhisperer writes to audit_log.json:
cd stellar/
pip install stellar-sdk
export STELLAR_SECRET_KEY=S...
export STELLAR_CONTRACT_ID=CAVBWCYJP2AXAEUJCAW3AUTBKZ2TUHZXIVGJET66PZECJQDDZ3YU7RAP
export STELLAR_PUBLIC_KEY=GB4MX4A5LJTCV2FCW3WNY4CF6WTLOGXSXVZMQVLN7WF5HFQBMC7XR235
python stellar_hook.py
```

## Future Scope
- Integrate `stellar_hook.py` directly into K8sWhisperer's `audit.py` so every incident auto-publishes on-chain without manual steps
- Add Stellar Passkey / social login so engineers can verify incidents without managing secret keys
- Build a multi-cluster view aggregating incidents from multiple K8s deployments into one blockchain dashboard
- Use Stellar's native multi-sig for HITL approval — require 2-of-3 team signatures before high blast-radius remediations execute
