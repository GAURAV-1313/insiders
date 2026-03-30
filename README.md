# K8sWhisperer

**Autonomous Kubernetes Incident Response Agent**

K8sWhisperer is a LangGraph-based agent that watches a live Kubernetes cluster, detects common production anomalies, diagnoses the likely root cause, plans a remediation, routes that plan through a deterministic safety gate, executes safe low-blast-radius actions automatically, and records every incident in a persistent audit log.

For higher-risk or persistent cases, K8sWhisperer supports Slack-based human-in-the-loop approval before resuming execution.

## What This Repo Actually Supports

### Demo-verified core scenarios
- `Pending` -> explain-only, no unsafe mutation
- `OOMKilled` -> automatic memory-limit patch + verification
- `CrashLoopBackOff` -> restart-first path with verification and HITL escalation support

### Additional implemented anomaly types
- `ImagePullBackOff`
- `Evicted`
- `CPUThrottling`
- `DeploymentStalled`
- `NodeNotReady`

These expanded anomaly types are implemented in the current adapter, safety gate, execute node, and tests. The strongest live evaluation path today is still the first two or three core scenarios.

## Architecture

```text
observe -> detect -> diagnose -> plan -> safety_gate -> execute/HITL -> explain_and_log
```

### Pipeline stages
1. `observe`
   - scans pods in the `production` namespace
   - also scans deployments and nodes for extended anomaly types
2. `detect`
   - classifies anomalies using an OpenAI-compatible LLM
   - falls back to deterministic classification when the provider fails or is rate-limited
3. `diagnose`
   - uses logs, `kubectl describe`, and events to generate a root-cause summary
4. `plan`
   - creates a typed remediation plan
5. `safety_gate`
   - deterministic, no LLM involvement
   - auto-executes only when confidence is high, blast radius is low, and action is allowed
6. `execute`
   - runs the actual kubectl-backed action
   - verifies success with exponential backoff
7. `explain_and_log`
   - generates a plain-English summary
   - appends the incident to `audit_log.json`

### HITL path
- Slack notification via bot token or webhook
- callback handling via FastAPI webhook
- LangGraph resume from checkpoint
- repeated polling pauses while a human decision is pending

## Current Safety Model

The safety gate is deterministic. Auto-remediation requires:

- confidence `> 0.8`
- `blast_radius == "low"`
- action in `allowed_v1_actions`
- action not in `destructive_actions`

`NodeNotReady` is explicitly forced to HITL even if a plan is otherwise low blast radius.

## Repository Layout

```text
.
├── src/k8swhisperer/
│   ├── adapters/
│   │   ├── base.py
│   │   ├── fixtures.py
│   │   ├── kubectl_cluster.py
│   │   ├── openai_compatible_llm.py
│   │   └── slack_notifier.py
│   ├── nodes/
│   │   ├── observe.py
│   │   ├── detect.py
│   │   ├── diagnose.py
│   │   ├── plan.py
│   │   ├── safety_gate.py
│   │   ├── execute.py
│   │   ├── hitl.py
│   │   └── explain_log.py
│   ├── app.py
│   ├── audit.py
│   ├── bootstrap.py
│   ├── config.py
│   ├── graph.py
│   ├── live_server.py
│   ├── mcp_server.py
│   ├── runtime.py
│   ├── state.py
│   └── webhook.py
├── scenarios/
├── rbac/
├── tests/
├── stellar/
├── main.py
├── run.py
├── demo_click.py
└── audit_log.json
```

## Entry Points

### 1. One-shot / loop runner
Use the standard development runner:

```bash
python main.py
```

With:

```env
K8SWHISPERER_RUN_ONCE=true
```

it performs a single cycle and exits. Otherwise it runs continuously.

### 2. FastAPI live server for Slack/ngrok
Use this when testing Slack callbacks or running the HITL flow:

```bash
PYTHONPATH=src uvicorn k8swhisperer.live_server:app --host 0.0.0.0 --port 8000
```

### 3. Local dashboard / one-click demo
For the threaded local dashboard flow:

```bash
python demo_click.py
```

This launches `run.py`, which serves a dashboard on:

```text
http://localhost:9000/dashboard
```

## Quick Start

### Prerequisites
- Python 3.9+
- `kubectl`
- access to a Kubernetes cluster such as minikube
- an OpenAI-compatible API key or Groq key
- optional Slack app for HITL

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create the namespace and apply RBAC:

```bash
kubectl create namespace production
kubectl apply -f rbac/k8s-rbac.yaml
```

Configure environment:

```bash
cp .env.example .env
```

Minimum useful env values:

```env
K8SWHISPERER_USE_FIXTURES=false
K8SWHISPERER_USE_REAL_ADAPTERS=false
K8SWHISPERER_RUN_ONCE=false

K8SWHISPERER_KUBECTL_BIN=kubectl
K8SWHISPERER_POLL_INTERVAL_SECONDS=30

GROQ_API_KEY=...
K8SWHISPERER_GROQ_MODEL=llama-3.3-70b-versatile
K8SWHISPERER_GROQ_BASE_URL=https://api.groq.com/openai/v1
```

For Slack bot-token mode:

```env
K8SWHISPERER_SLACK_BOT_TOKEN=...
K8SWHISPERER_SLACK_CHANNEL=#your-channel
K8SWHISPERER_PUBLIC_BASE_URL=https://your-ngrok-url.ngrok-free.app
```

## Demo Scenarios

### Core evaluation scenarios

```bash
# Pending -> explain_only
kubectl apply -f scenarios/pending.yaml

# OOMKilled -> patch_memory_limit
kubectl apply -f scenarios/oomkill.yaml

# CrashLoopBackOff -> restart_pod, verify, HITL/escalation path
kubectl apply -f scenarios/crashloop.yaml
```

### Extended scenarios

```bash
kubectl apply -f scenarios/imagepullbackoff.yaml
kubectl apply -f scenarios/evicted.yaml
kubectl apply -f scenarios/cpu-throttling.yaml
kubectl apply -f scenarios/deployment-stalled.yaml
kubectl apply -f scenarios/node-notready.yaml
```

## Recommended Evaluation Flow

For the most reliable live evaluation demo:

1. `Pending`
   - shows safe explain-only behavior
2. `OOMKilled`
   - shows true autonomous remediation
   - demonstrates before/after memory change
3. optional `CrashLoopBackOff`
   - shows restart-first logic and HITL architecture

## What To Show For OOM Auto-Fix

Before remediation:

```bash
kubectl get deployment oom-app -n production -o jsonpath='{.spec.template.spec.containers[0].resources.limits.memory}'; echo
```

Expected initial limit:

```text
50Mi
```

After the agent runs:

```bash
kubectl get deployment oom-app -n production -o jsonpath='{.spec.template.spec.containers[0].resources.limits.memory}'; echo
kubectl get pods -n production -l app=oom-app -o wide
```

Expected result:
- memory limit increased, typically to `75Mi`
- replacement pod `Running`
- restart count `0`

## Audit Log

Every processed incident is appended to:

```text
audit_log.json
```

Each entry includes:
- `incident_id`
- `timestamp`
- `anomaly`
- `diagnosis`
- `plan`
- `approved`
- `result`
- `explanation`

Useful live check:

```bash
tail -f audit_log.json
```

## Tests

Current test suite:

```bash
source .venv/bin/activate
python -m unittest discover -s tests
```

Last verified result:

```text
Ran 71 tests in 0.078s
OK
```

## RBAC

The demo RBAC is namespace-scoped and avoids cluster-admin. Current permissions include:

- pods: `get`, `list`, `watch`, `delete`
- pod logs: `get`, `list`, `watch`
- events: `get`, `list`, `watch`
- deployments: `get`, `list`, `watch`, `patch`

See:

- [rbac/k8s-rbac.yaml](/Users/gaurav/Documents/insiders/rbac/k8s-rbac.yaml)

## MCP Server

The repo also exposes kubectl capabilities as MCP tools:

```bash
python src/k8swhisperer/mcp_server.py
```

Exposed tools include:
- `scan_cluster`
- `get_pod_logs`
- `describe_pod`
- `restart_pod`
- `patch_memory_limit`
- `delete_evicted_pod`
- `patch_cpu_limit`
- `scan_deployments`
- `scan_nodes`
- `get_audit_log`

## Web3 Bonus

The `stellar/` directory contains the optional Web3 bonus path:
- Soroban smart contract
- React dashboard
- hook that can publish incident summaries from `audit_log.json`

This is best treated as a bonus extension, not a required dependency for the core demo.

## Known Caveats

- On some macOS setups, `urllib3` prints a LibreSSL/OpenSSL warning. This has been non-blocking in local testing.
- If your LLM provider hits rate limits, the repo falls back to deterministic classify/diagnose/plan/explain behavior for the supported scenarios.
- Slack HITL is implemented, but the cleanest evaluation demo remains `Pending` + `OOMKilled`.

## Evaluation Pitch

K8sWhisperer is an autonomous Kubernetes incident-response agent built for real cluster behavior, not mocked screenshots. It continuously observes the cluster, classifies failures, diagnoses root cause from logs and describe output, plans a remediation, routes actions through a deterministic safety gate, and then either auto-executes or escalates to human approval. The strongest live proof is the OOMKilled scenario: the workload starts with a `50Mi` memory limit, the agent detects the OOM condition, patches the deployment to a higher limit, and verifies that the replacement pod becomes healthy. Every step is captured in a plain-English audit log, and the repo also includes a Slack HITL path, MCP tooling, and an optional Stellar-based Web3 audit extension.
