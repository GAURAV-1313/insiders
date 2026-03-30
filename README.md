# K8sWhisperer

**Autonomous Kubernetes Incident Response Agent**

> When production breaks at 3am, engineers spend 40 minutes grepping logs. K8sWhisperer does it in 90 seconds -- autonomously.

K8sWhisperer continuously monitors a Kubernetes cluster, detects anomalies, diagnoses root causes, plans remediations, and executes fixes -- while routing risky actions through a human-in-the-loop (HITL) Slack approval flow. Every decision is logged in plain English and recorded on the Stellar blockchain for tamper-proof audit.

---

## Architecture

```
                          K8sWhisperer Pipeline
 ┌─────────┐  ┌────────┐  ┌───────────┐  ┌──────┐  ┌─────────────┐
 │ OBSERVE  │→ │ DETECT │→ │ DIAGNOSE  │→ │ PLAN │→ │ SAFETY GATE │
 │ kubectl  │  │  LLM   │  │ logs+desc │  │ LLM  │  │deterministic│
 │ scan all │  │classify │  │ root cause│  │action│  │   routing   │
 └─────────┘  └────────┘  └───────────┘  └──────┘  └──────┬──────┘
                                                           │
                                          ┌────────────────┼────────────────┐
                                          │ confidence>0.8 │ OTHERWISE      │
                                          │ blast=low      │                │
                                          │ !destructive   │                │
                                          ▼                ▼                │
                                    ┌─────────┐    ┌──────────────┐        │
                                    │ EXECUTE  │    │ HITL REQUEST │        │
                                    │ kubectl  │    │ Slack msg    │        │
                                    │ action   │    │ Approve/Deny │        │
                                    └────┬────┘    └──────┬───────┘        │
                                         │                │                │
                                         │          ┌─────▼──────┐        │
                                         │          │ HITL WAIT  │        │
                                         │          │ FastAPI    │        │
                                         │          │ webhook    │        │
                                         │          └─────┬──────┘        │
                                         │                │                │
                                         ▼                ▼                │
                                    ┌──────────────────────────┐          │
                                    │    EXPLAIN & LOG         │          │
                                    │ Plain-English summary    │          │
                                    │ Persistent audit_log.json│──→ Stellar
                                    │ Slack notification       │  blockchain
                                    └──────────────────────────┘
                                              │
                                              ▼
                                         Loop → OBSERVE
```

---

## Supported Anomaly Types (8 total)

| Anomaly | Trigger Signal | Auto-Action | Severity | HITL? |
|---------|---------------|-------------|----------|-------|
| **CrashLoopBackOff** | restartCount > 3 | `restart_pod` | HIGH | No |
| **OOMKilled** | exit_code=137 | `patch_memory_limit` (+50%) | HIGH | No |
| **Pending Pod** | phase=Pending > 5min | `explain_only` | MED | No |
| **ImagePullBackOff** | waiting.reason=ImagePullBackOff | `explain_only` | MED | No |
| **Evicted Pod** | reason=Evicted | `delete_pod` | MED | No |
| **CPU Throttling** | cpu_throttled_ratio > 0.5 | `patch_cpu_limit` (+50%) | MED | No |
| **Deployment Stalled** | updatedReplicas != replicas | `rollback_deployment` | HIGH | **Yes** |
| **Node NotReady** | conditions[Ready]=False | `log_node_metrics` | CRITICAL | **Always** |

---

## Safety Gate Logic

The safety gate is **fully deterministic** -- no LLM involvement. Auto-execute ONLY when ALL conditions are met:

```
confidence > 0.8
  AND blast_radius == "low"
  AND action NOT in DESTRUCTIVE_ACTIONS
  AND action IN ALLOWED_V1_ACTIONS
  AND anomaly_type != "NodeNotReady"
```

**NodeNotReady always requires HITL** -- the agent will never auto-drain or auto-cordon a node. This is a deliberate safety design choice.

**Destructive actions** (always HITL): `delete_namespace`, `delete_deployment`, `drain_node`, `scale_workload`, `rollout_restart`, `rollout_undo`, `cordon_node`

---

## Project Structure

```
k8swhisperer/
├── src/k8swhisperer/
│   ├── nodes/                  # 7 pipeline stages
│   │   ├── observe.py          # Stage 1: kubectl scan (pods + deployments + nodes)
│   │   ├── detect.py           # Stage 2: LLM anomaly classification
│   │   ├── diagnose.py         # Stage 3: Root cause analysis
│   │   ├── plan.py             # Stage 4: Remediation proposal
│   │   ├── safety_gate.py      # Stage 5: Deterministic risk routing
│   │   ├── execute.py          # Stage 6: kubectl action + backoff verification
│   │   ├── explain_log.py      # Stage 7: Audit trail + Slack notification
│   │   └── hitl.py             # HITL approval request handler
│   ├── adapters/
│   │   ├── base.py             # Protocol contracts (ClusterAdapter, LLMAdapter, NotifierAdapter)
│   │   ├── kubectl_cluster.py  # Real kubectl integration with RBAC
│   │   ├── openai_compatible_llm.py  # Groq/OpenAI LLM with fallback
│   │   ├── slack_notifier.py   # Slack Block Kit + HITL buttons
│   │   └── fixtures.py         # Development/test fixtures
│   ├── state.py                # Shared ClusterState TypedDict
│   ├── graph.py                # LangGraph StateGraph builder
│   ├── config.py               # Safety policies and thresholds
│   ├── bootstrap.py            # Adapter selection from environment
│   ├── app.py                  # Runtime loop with multi-anomaly dispatch
│   ├── mcp_server.py           # MCP server (7 typed kubectl tools)
│   ├── webhook.py              # FastAPI HITL webhook
│   └── audit.py                # Persistent JSON audit log
├── stellar/                    # Web3 Blockchain Bonus
│   ├── contracts/incident-audit/  # Soroban smart contract (Rust)
│   ├── src/                    # React + Tailwind dashboard
│   ├── stellar_hook.py         # Python bridge to blockchain
│   └── README.md               # Web3 documentation
├── scenarios/                  # Kubernetes demo manifests (8 scenarios)
├── tests/                      # Unit + integration tests (71 tests)
├── rbac/                       # RBAC YAML (ServiceAccount + Role + RoleBinding)
├── demo_click.py               # One-click demo runner
├── run.py                      # Agent loop + webhook server
└── requirements.txt            # Python dependencies
```

---

## Quick Start

### Prerequisites
- minikube (or any local K8s cluster)
- Python 3.9+
- Groq API key (or any OpenAI-compatible API)

### Setup

```bash
# 1. Start minikube
minikube start

# 2. Create namespace and apply RBAC
kubectl create namespace production
kubectl apply -f rbac/k8s-rbac.yaml

# 3. Install Python dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys and Slack webhook URL

# 5. Run the demo
python demo_click.py
```

### Run Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

---

## Demo Scenarios

Apply any scenario to trigger the pipeline:

```bash
# CrashLoopBackOff (auto-fix: restart pod)
kubectl apply -f scenarios/crashloop.yaml

# OOMKilled (auto-fix: patch memory +50%)
kubectl apply -f scenarios/oomkill.yaml

# Pending Pod (explain only)
kubectl apply -f scenarios/pending.yaml

# ImagePullBackOff (explain only)
kubectl apply -f scenarios/imagepullbackoff.yaml

# Evicted Pod (auto-fix: delete dead pod)
kubectl apply -f scenarios/evicted.yaml

# CPU Throttling (auto-fix: patch CPU +50%)
kubectl apply -f scenarios/cpu-throttling.yaml

# Deployment Stalled (HITL: rollback)
kubectl apply -f scenarios/deployment-stalled.yaml
```

---

## RBAC

The agent runs with **minimal permissions** -- no cluster-admin:

```yaml
# rbac/k8s-rbac.yaml
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch", "delete"]
- apiGroups: [""]
  resources: ["pods/log", "events"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "patch"]
```

Pod-level operations only. Cannot delete namespaces, drain nodes, or access secrets.

---

## HITL Slack Flow

1. Safety gate detects high-risk action (or NodeNotReady)
2. Slack message sent with **Approve / Reject** buttons
3. Judge clicks Approve
4. FastAPI webhook receives callback
5. LangGraph resumes execution from checkpoint
6. Action executed and verified

---

## Web3 Blockchain Bonus (Stellar)

Every incident is optionally recorded on the **Stellar testnet** for tamper-proof audit:

- **Smart Contract**: Soroban contract storing incident records on-chain
- **Contract ID**: `CAVBWCYJP2AXAEUJCAW3AUTBKZ2TUHZXIVGJET66PZECJQDDZ3YU7RAP`
- **Frontend**: React + Tailwind dashboard to browse on-chain incidents
- **Integration**: Python hook submits incidents from `audit_log.json` to blockchain

See [stellar/README.md](stellar/README.md) for full Web3 documentation.

---

## Verification Backoff Strategy

After executing an action, the agent verifies resolution with exponential backoff:

| Poll | Wait | Check |
|------|------|-------|
| 1 | 15s | pod phase + restart count |
| 2 | 30s | deployment health (2-observation confirmation) |
| 3 | 60s | continued health check |
| 4 | 90s | final verification |

Deployment verification requires **2 consecutive healthy observations** to prevent false positives from transient states.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Orchestration | LangGraph StateGraph with MemorySaver checkpointer |
| LLM | Groq (llama-3.3-70b) or any OpenAI-compatible API |
| Cluster | kubectl with RBAC ServiceAccount |
| HITL | FastAPI webhook + Slack Block Kit buttons |
| MCP | Python MCP SDK with 7 typed kubectl tools |
| Blockchain | Stellar Soroban smart contract + React dashboard |
| Testing | unittest (71 tests covering all pipeline stages) |

---

## Scoring Rubric Alignment

| Criterion | Marks | Our Implementation |
|-----------|-------|--------------------|
| **Autonomous Remediation** | 30 | 8 anomaly types, auto-fix for CrashLoop/OOM/Evicted/CPUThrottle, verify with backoff |
| **Safety Gate & HITL** | 25 | Deterministic routing, NodeNotReady always HITL, Slack approval end-to-end, RBAC enforced |
| **Diagnosis Quality** | 20 | LLM evidence-backed diagnosis, fallback templates, plain-English for non-experts |
| **LangGraph Architecture** | 15 | 9 nodes, conditional edges, checkpointer, shared TypedDict, multi-anomaly dispatch |
| **MCP Integration** | 10 | 7 typed tools, RBAC-scoped kubectl, Slack MCP |
| **Web3 Bonus** | 25 | Deployed Soroban contract, React frontend, SDK integration, block explorer proof |
