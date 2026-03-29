# K8sWhisperer — MASTER REQUIREMENTS DOCUMENT
## PS1 · DevOps × AI/ML Track · Antigravity Agent Analysis Constraints
### 36-Hour Hackathon · 100 Marks + 25 Web3 Bonus

> **Purpose of this document:** Single source of truth for every rule, constraint, scoring criterion, official FAQ answer, hidden trap, and deliverable requirement for PS1. Designed for Antigravity agent ingestion — every constraint is explicit and machine-readable.

---

## SECTION 1: PROBLEM IDENTITY

| Field | Value |
|---|---|
| Problem Statement | PS1 — K8sWhisperer |
| Track | DevOps × AI/ML |
| Subtitle | Kubernetes Autopilot Agent |
| Duration | 36 hours continuous |
| Team Size | 2–4 members |
| Difficulty | Extreme — Full pipeline required |
| Max Marks | 100 (+ 25 Web3 bonus) |

**Core Stack (mandatory):** LangGraph · LangChain · MCP Server · kubectl · Prometheus · Slack

**One-line goal:** Build an autonomous Kubernetes incident response agent that continuously monitors a cluster, detects anomalies, diagnoses root causes, plans remediation actions, and executes fixes — while routing risky actions through a human-in-the-loop approval flow. Every decision must be logged in plain English.

---

## SECTION 2: MANDATORY PIPELINE — 7 STAGES (ALL REQUIRED)

**CONSTRAINT:** All 7 stages must exist as structured pipeline components. A single LLM prompt replacing the pipeline is NOT allowed. Partial or hardcoded pipelines are penalised under Technical Execution.

### Stage 01 — Observe (Cluster Scan)

- **Tool:** kubectl MCP
- **Frequency:** Poll all namespaces every 30 seconds
- **Data collected:** events, pod phases, resource metrics, node states
- **Output:** Normalised `ClusterState` object
- **Constraint:** Must be a real minikube cluster. Mocking kubectl outputs is NOT allowed.

### Stage 02 — Detect (Anomaly Classification)

- **Input:** Raw event stream from ClusterState
- **Tool:** LLM classifier
- **Output:** Typed `Anomaly` objects with fields: `type`, `severity`, `affected_resource`, `confidence` (float 0–1)
- **Constraint:** LLM cannot replace the pipeline logic. Classifier must produce structured typed output.

### Stage 03 — Diagnose (Root Cause Analysis)

- **Agent type:** Specialist sub-agent
- **Data fetched:** `kubectl logs`, `kubectl describe`, recent events for affected pod
- **Output:** Root cause string with supporting evidence
- **Constraint:** LLM synthesises diagnosis from actual kubectl output. Evidence must be cited.

### Stage 04 — Plan (Remediation Proposal)

- **Node type:** Planner node
- **Output:** `RemediationPlan` object with fields:
  - `action_type`
  - `target_resource`
  - `parameters`
  - `confidence` (float 0–1)
  - `blast_radius` — ENUM: `low` / `medium` / `high`

### Stage 05 — Safety Gate (Risk-Based Routing)

**This is a conditional LangGraph edge. Rules are EXACT — no deviation allowed.**

**AUTO-EXECUTE condition (ALL three must be true simultaneously):**
```
confidence > 0.8
AND blast_radius == "low"
AND action NOT IN DESTRUCTIVE_ACTIONS
```

**HITL condition (ANY one triggers human approval):**
```
confidence <= 0.8
OR blast_radius != "low"
OR action IN DESTRUCTIVE_ACTIONS
```

**Official blast_radius classifications (from FAQ Q5):**
| Action | blast_radius | Route |
|---|---|---|
| Restart pod (delete pod) | LOW | Auto-execute allowed |
| Scaling operations | NOT LOW | HITL required |
| Rollout operations | NOT LOW | HITL required |
| Node operations | NOT LOW | HITL required |
| Any destructive action | NOT LOW | HITL required |

**CONSTRAINT:** No destructive auto-executions are allowed under any circumstance. Judges will verify this.

### Stage 06 — Execute (Surgical kubectl Action)

- **Tool:** kubectl MCP
- **Post-action wait:** 30 seconds before re-checking
- **Verify step:** Re-fetch pod state to confirm resolution
- **Output:** Sets `result` field in ClusterState
- **CONSTRAINT:** The verify step MUST poll with backoff — not just check once. Judges specifically test this.

### Stage 07 — Explain & Log (Audit Trail)

- **LLM task:** Write human-readable action summary
- **Slack:** Post structured message
- **Persistence:** Append `LogEntry` to persistent `audit_log` JSON file
- **Loop:** Return to Stage 01 (Observe)
- **CONSTRAINT:** Plain English explanation understandable to a non-expert is required.

---

## SECTION 3: LANGGRAPH STATE SCHEMA

**CONSTRAINT:** All agent nodes must read from and write to a shared `ClusterState` TypedDict. Nodes must NOT maintain local state — all data flows through the graph state.

```python
class ClusterState(TypedDict):
    events:     list[dict]         # Raw kubectl events from current observe cycle
    anomalies:  list[Anomaly]      # Detected anomalies: type, severity, resource, confidence
    diagnosis:  str                # LLM-generated root cause string with supporting evidence
    plan:       RemediationPlan    # Proposed action, target, params, confidence, blast_radius
    approved:   bool               # Human approval decision from HITL webhook callback
    result:     str                # kubectl execution output and post-action pod state
    audit_log:  list[LogEntry]     # Persistent history of all incidents, decisions, and actions
```

**Required sub-types:**
```python
class Anomaly(TypedDict):
    type:               str    # e.g. 'CrashLoopBackOff', 'OOMKilled', 'Pending'
    severity:           str    # 'HIGH', 'MED', 'LOW', 'CRITICAL'
    affected_resource:  str    # pod name / node name
    confidence:         float  # 0.0 – 1.0

class RemediationPlan(TypedDict):
    action_type:    str    # e.g. 'restart_pod', 'patch_memory', 'explain_only'
    target_resource: str
    parameters:     dict
    confidence:     float  # 0.0 – 1.0
    blast_radius:   str    # 'low' | 'medium' | 'high'

class LogEntry(TypedDict):
    timestamp:      str
    anomaly_type:   str
    diagnosis:      str
    action_taken:   str
    result:         str
    explanation:    str    # Plain English
```

---

## SECTION 4: ANOMALY CLASSIFICATION MATRIX

**CONSTRAINT:** Teams that implement ONLY CrashLoopBackOff will score in the bottom quartile. The first three are the minimum required for a passing demo.

| Anomaly Type | Trigger Signal | Auto-Action | Severity | Min Required? |
|---|---|---|---|---|
| CrashLoopBackOff | `restartCount > 3` | Fetch logs → diagnose → auto restart pod | HIGH | ✅ YES |
| OOMKilled | `lastState.terminated.reason = OOMKilled` | Read limits → patch +50% memory → restart | HIGH | ✅ YES |
| Pending Pod | `pod.status.phase = Pending > 5 min` | Describe → check node capacity → recommend | MED | ✅ YES |
| ImagePullBackOff | `state.waiting.reason = ImagePullBackOff` | Extract image → alert human | MED | No (bonus) |
| CPU Throttling | Prometheus: `cpu_throttled > 0.5` | Patch CPU limit upward → verify throttle drops | MED | No (bonus) |
| Evicted Pod | `pod.status.reason = Evicted` | Check node pressure → delete evicted pod | LOW | No (bonus) |
| Deployment Stalled | `updatedReplicas != replicas > 10 min` | Check events → HITL: rollback or force rollout | HIGH | No (bonus) |
| Node NotReady | `conditions[Ready] = False` | Log metrics → HITL ONLY — **never auto-drain** | CRITICAL | No (bonus) |

**CRITICAL CONSTRAINT for Node NotReady:** HITL ONLY. Auto-drain is absolutely forbidden.

**Demo minimum (from FAQ Q6):** Agent must respond autonomously to injected live anomalies. No manual kubectl commands allowed during demo window.

---

## SECTION 5: REQUIRED DELIVERABLES (ALL MANDATORY)

### Deliverable 1 — Live Agent Demo

- Working demo against a **real minikube cluster** (mocking is disqualified)
- Must cover at least **3 anomaly scenarios:**
  - CrashLoopBackOff → **auto-fix**
  - OOMKilled → **HITL flow**
  - Pending Pod → **explain**
- Judges will **inject a live anomaly** during demo
- Team must let agent respond **autonomously — no manual kubectl during demo**
- Live demo is required; recorded demo is backup only (used only if technical failure occurs)

### Deliverable 2 — HITL Slack Flow

- Slack message with **Approve / Reject** interactive buttons (Block Kit)
- **FastAPI webhook** that receives Slack callback and **resumes the LangGraph graph**
- Full flow demonstrated live **with a judge clicking Approve**
- CONSTRAINT: LangGraph must **pause the graph cleanly** and resume on callback — not spin-wait or timeout prematurely

### Deliverable 3 — Audit Trail

- **Persistent JSON** audit log file
- Must log every agent decision, action taken, and plain-English explanation
- Must include **at least 3 complete incident records**
- Contents per record: timestamp, anomaly type, diagnosis, action taken, result, explanation

### Deliverable 4 — RBAC YAML

- File must define: **ServiceAccount + Role + RoleBinding**
- Scope: **pod-level operations only**
- Judges will inspect for **cluster-admin absence**
- CONSTRAINT: If MCP tool has cluster-admin, a hallucinated action can delete namespaces — this is a disqualifying footgun

```yaml
# Minimum required permissions:
# - get/list/watch on pods, pods/log, events
# - delete on pods (restart = delete + K8s recreates)
# - get/list/watch/patch on deployments
# MUST NOT include: cluster-admin or any cluster-wide permissions
```

### Deliverable 5 — Architecture Presentation

- Duration: **5 minutes**
- Must cover:
  1. Problem statement
  2. LangGraph node graph
  3. MCP tool design
  4. Safety gate logic
  5. Live demo
- Q&A to follow

### Deliverable 6 — GitHub Submission (before judging begins)

- Source code GitHub link
- README with setup instructions
- Architecture diagram

---

## SECTION 6: SCORING RUBRIC — FULL BREAKDOWN

### PS1-Specific Rubric (100 marks)

| Criterion | Marks | What Judges Look For |
|---|---|---|
| Autonomous Remediation | 30 | Agent correctly auto-fixes CrashLoopBackOff, OOMKilled, Evicted pods. Speed and accuracy of verify step. |
| Safety Gate & HITL | 25 | Correct routing of high-risk actions to HITL. Slack approval flow works end-to-end. RBAC enforced. No destructive auto-executions. |
| Diagnosis Quality | 20 | Root cause explanation accurate and actionable. Evidence cited from actual kubectl output. Plain-English log understandable to non-expert. |
| LangGraph Architecture | 15 | Clean node definitions, proper conditional edges, working checkpointer, TypedDict schema. Code quality and graph structure reviewed. |
| MCP Integration | 10 | Proper MCP server with typed tool definitions. kubectl and Slack MCP tools functional. RBAC ServiceAccount correctly scoped. |
| **TOTAL** | **100** | |

### Overall Hackathon Rubric (normalisation + tie-breaking)

| Criterion | Marks | What Judges Look For |
|---|---|---|
| Technical Execution | 40 | Core pipeline functional end-to-end. Mandatory stages complete. Handles test inputs. No critical demo failures. |
| Problem-Solving Depth | 20 | Real engineering decisions. Edge case handling. Failure mode handling. System constraints addressed. |
| Code & System Design | 15 | Readable, modular, maintainable code. Coherent architecture. State management, error handling, logging present. |
| Explainability & Communication | 15 | System explains its own decisions clearly. Clear presentation. Demo is structured. Judge questions answered with depth. |
| Innovation & Impact | 10 | Goes beyond what was asked. Novel dimension in UX, algorithm, integration, or framing. |
| **TOTAL** | **100** | |

### Scoring Bands

| Band | Score | Description |
|---|---|---|
| Failing | Below 40 | Only 1–2 mandatory stages. No end-to-end flow. System crashes on demo inputs. |
| Passing | 40–65 | Mandatory pipeline complete but shallow. Works on easiest test input. Generic explanations. |
| Good | 65–80 | Solid mandatory pipeline. Works on 2+ inputs. Some optional extensions. Evidence-backed explanations. |
| Strong | 80–90 | Full mandatory pipeline + 2+ meaningful optional extensions. Excellent explanations. Robust system. Clean demo. |
| Exceptional | 90+ | Exceptional technical depth. Novel approach. Meaningful Web3 integration. Production-grade thinking. |

---

## SECTION 7: HIDDEN TRAPS — WHAT WILL BREAK NAIVE IMPLEMENTATIONS

### Trap 1 — Race Conditions

**Problem:** Two anomalies fire simultaneously on the same pod.
**Requirement:** Agent must handle concurrent state updates without corrupting `ClusterState`.
**Constraint:** Concurrency is not mandatory for passing but expected for scores 80+.

### Trap 2 — False Positives

**Problem:** A pod restarts during a rolling update (expected/planned) vs. a real CrashLoop (unplanned).
**Requirement:** LLM must distinguish planned from unplanned restarts.
**Implementation hint:** Check `is_rollout_in_progress` before classifying as CrashLoop anomaly.

### Trap 3 — RBAC Footgun

**Problem:** MCP tool with cluster-admin can allow hallucinated actions to delete namespaces.
**Requirement:** Scoping to pod-level delete only is non-trivial. Must be implemented correctly.
**Verification:** Judges will run `kubectl auth can-i delete namespace --as=system:serviceaccount:production:k8s-whisperer-agent` — must output `no`.

### Trap 4 — Verify Loop

**Problem:** After restarting a pod, it may take 60+ seconds to become Running.
**Requirement:** Verify step MUST poll with backoff — not just check once.
**Expected log pattern:** `[0s] Status: ContainerCreating` → `[30s] Status: ContainerCreating` → `[60s] Status: Running`

### Trap 5 — Slack Webhook Latency

**Problem:** HITL approval can take minutes.
**Requirement:** LangGraph must pause the graph cleanly and resume on callback.
**Forbidden:** Spin-wait or premature timeout.
**Implementation:** FastAPI webhook server receives Slack callback → resumes LangGraph graph via interrupt/resume mechanism.

### Trap 6 — Log Noise

**Problem:** `kubectl logs` returns megabytes. Passing the full log to the LLM hits context limits.
**Requirement:** Chunking and summarisation strategy is required.
**Recommendation:** Tail last N lines (e.g., `--tail=50`), extract error-relevant sections before passing to LLM.

---

## SECTION 8: OFFICIAL FAQ ANSWERS (AUTHORITATIVE CONSTRAINTS)

### Q1 — Real system vs mock?

**Answer:** PS1 must run on a real Kubernetes cluster (minikube). Mocking kubectl outputs is NOT allowed.
**Reference:** "Working demo against a real minikube cluster"

### Q2 — LLM usage allowed scope?

**Answer:** LLMs are allowed but cannot replace the pipeline logic entirely. Core stages (detect, diagnose, plan, etc.) must still exist as structured pipeline components, not a single prompt.
**Reference:** Mandatory multi-stage pipeline — 7 stages

### Q3 — What counts as a "working pipeline"?

**Answer:** A valid pipeline must:
- Execute all mandatory stages
- Pass data stage → stage
- Produce final output + explanation

Partial/hardcoded pipelines = penalised under Technical Execution.

### Q4 — Can we fully use fallback (manual coordinates)?

**Answer:** This applies to PS2 only. For PS1: no fallback on kubectl — real cluster is required.

### Q5 — Safety Gate ambiguity

**Answer:** Auto-execute ONLY if ALL THREE conditions met:
- `confidence > 0.8`
- `blast_radius = low`
- Action is NOT destructive

All other cases → HITL required.

Specific classifications:
- Restart pod → LOW blast_radius → CAN auto-execute
- Scaling / rollout / node operations → NOT LOW → HITL required

### Q6 — Evaluation strictness

**Answer:**
- Judges WILL test mandatory scenarios
- Judges WILL inject live anomalies during demo
- System MUST respond autonomously
- No manual kubectl commands during demo window

### Q7 — Concurrency requirement

**Answer:** Not mandatory for passing. Expected for high scores (80+). Listed under "Hidden Traps" (advanced robustness).

### Q8 — Prometheus required?

**Answer:** Optional (bonus marks only). Not required for passing demo.

---

## SECTION 9: TECH STACK — RECOMMENDED & REQUIRED

### Required Components

| Component | Purpose | Notes |
|---|---|---|
| LangGraph StateGraph | Orchestration | Conditional edges, MemorySaver checkpointer, HITL interrupt |
| LangChain | Tool wrappers | ReAct sub-agent for diagnosis, structured output parsing |
| kubectl MCP Server | Cluster operations | Python MCP SDK — expose kubectl as typed tools with RBAC ServiceAccount |
| Slack MCP | HITL notifications | Block Kit messages with Approve/Reject interactive buttons |
| FastAPI | HITL webhook | Receives Slack callback and resumes LangGraph graph |
| minikube | Local K8s cluster | Single-node, fast to spin up and reset |

### Recommended LLM

- GPT-4o or Claude Sonnet for classifier, planner, and explainer nodes
- Any LLM API is permitted and not penalised (OpenAI, Anthropic, Mistral, open-source)

### Optional (Bonus Marks)

| Component | Bonus |
|---|---|
| Prometheus MCP | Metric-driven detection (CPU throttling, memory pressure) |
| Multi-namespace support | Up to 5 bonus marks |
| Predictive alerting | Alert before pod crashes |
| Auto-generated GitHub PR | For permanent config fixes |

---

## SECTION 10: DEMO SCENARIOS — REQUIRED YAML FILES

Three scenario YAML files must be created and deployed for testing.

### Scenario 1 — CrashLoopBackOff (crashloop.yaml)

**Expected behaviour:** Pod exits with code 1, enters CrashLoopBackOff after ~4 restarts.
**Agent must:** Auto-detect → diagnose → auto-fix (delete pod) → verify new pod Running.
**Key constraint:** RESTARTS > 3 before detection triggers.

```yaml
# Minimum spec:
# - Deployment name: crash-app
# - Namespace: production
# - Image: busybox:latest
# - Command: exits with code 1 after printing error message
# - Memory limit: 64Mi, CPU limit: 100m
```

### Scenario 2 — OOMKilled (oomkill.yaml)

**Expected behaviour:** Pod exceeds memory limit, gets killed with OOMKilled.
**Agent must:** Detect → diagnose → send to HITL → upon Slack approval → patch memory +50% → restart → verify.
**Key constraint:** This is the HITL demo scenario. Judge will click Approve.

```yaml
# Minimum spec:
# - Deployment name: oom-app
# - Namespace: production
# - Image: python:3.9-slim
# - Memory limit: 20Mi (intentionally tiny)
# - Memory request: 10Mi
```

### Scenario 3 — Pending Pod (pending.yaml)

**Expected behaviour:** Pod stays Pending forever due to impossible resource request.
**Agent must:** Detect → describe → extract FailedScheduling reason → explain in plain English.
**Key constraint:** No auto-fix. Explanation only. Reason must be extracted from actual kubectl describe output.

```yaml
# Minimum spec:
# - Deployment name: pending-app
# - Namespace: production
# - Image: nginx:latest
# - Memory request: 100Gi (more than any node has)
```

---

## SECTION 11: MCP SERVER REQUIREMENTS

The kubectl MCP server must be built with the Python MCP SDK.

### Required Tool Definitions (typed)

| Tool | Arguments | Returns | RBAC Required |
|---|---|---|---|
| `get_pods` | `namespace: str` | `list[dict]` (pod objects) | get, list, watch on pods |
| `get_pod_logs` | `pod_name: str, namespace: str, previous: bool, tail: int` | `str` | get on pods/log |
| `describe_pod` | `pod_name: str, namespace: str` | `str` | get on pods |
| `delete_pod` | `pod_name: str, namespace: str` | `bool` | delete on pods |
| `patch_deployment_memory` | `deployment: str, namespace: str, new_memory: str` | `bool` | patch on deployments |
| `get_events` | `namespace: str` | `str` | get, list, watch on events |

### Slack MCP Requirements

| Feature | Requirement |
|---|---|
| Message format | Block Kit |
| Buttons | Approve and Reject interactive buttons |
| Content | Must include: anomaly type, diagnosis summary, proposed action, blast_radius, confidence |
| Webhook | FastAPI endpoint to receive Slack button callback |
| Graph resume | Webhook must call LangGraph interrupt/resume to continue graph execution |

---

## SECTION 12: RBAC SPECIFICATION

### Required YAML Structure

```yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: k8s-whisperer-agent
  namespace: production
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: production
  name: k8s-whisperer-role
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log", "events"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["delete"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: k8s-whisperer-binding
  namespace: production
subjects:
  - kind: ServiceAccount
    name: k8s-whisperer-agent
    namespace: production
roleRef:
  kind: Role
  name: k8s-whisperer-role
  apiGroup: rbac.authorization.k8s.io
```

### Judge Verification Commands (must all pass)

```bash
# MUST output: no
kubectl auth can-i delete namespace \
  --as=system:serviceaccount:production:k8s-whisperer-agent

# MUST output: yes
kubectl auth can-i delete pods -n production \
  --as=system:serviceaccount:production:k8s-whisperer-agent

# MUST output: yes
kubectl auth can-i get pods -n production \
  --as=system:serviceaccount:production:k8s-whisperer-agent

# MUST output: yes
kubectl auth can-i patch deployments -n production \
  --as=system:serviceaccount:production:k8s-whisperer-agent
```

---

## SECTION 13: AUDIT LOG SPECIFICATION

### Required Format

```json
{
  "audit_log": [
    {
      "timestamp": "2026-XX-XXTXX:XX:XXZ",
      "anomaly_type": "CrashLoopBackOff",
      "affected_resource": "crash-app-7d4b9c-xkr2p",
      "namespace": "production",
      "diagnosis": "Pod exiting with code 1. Logs show: ERROR: Database connection refused at db:5432. Root cause: missing database dependency.",
      "plan": {
        "action_type": "restart_pod",
        "target_resource": "crash-app-7d4b9c-xkr2p",
        "confidence": 0.92,
        "blast_radius": "low"
      },
      "approved": true,
      "auto_approved": true,
      "action_taken": "kubectl delete pod crash-app-7d4b9c-xkr2p -n production",
      "result": "Pod crash-app-new-pod-xxx is Running after 67 seconds.",
      "explanation": "The crash-app pod was repeatedly crashing due to a missing database connection. The agent deleted the pod and Kubernetes automatically created a replacement. The new pod is now running successfully."
    }
  ]
}
```

### Constraints

- File must be **persistent** (survives agent restart)
- Must contain **at least 3 complete incident records** for demo
- Each record must have all fields populated
- Explanation field must be **plain English, understandable to a non-expert**

---

## SECTION 14: LANGGRAPH ARCHITECTURE REQUIREMENTS

### Node Definitions

```python
# Required nodes (LangGraph StateGraph):
graph.add_node("observe",   observe_node)     # Stage 01
graph.add_node("detect",    detect_node)      # Stage 02
graph.add_node("diagnose",  diagnose_node)    # Stage 03
graph.add_node("plan",      plan_node)        # Stage 04
graph.add_node("safety",    safety_router)    # Stage 05 — conditional edge
graph.add_node("hitl",      hitl_node)        # Stage 05 HITL path
graph.add_node("execute",   execute_node)     # Stage 06
graph.add_node("explain",   explain_node)     # Stage 07
```

### Required Conditional Edge (Safety Gate)

```python
def safety_router(state: ClusterState) -> str:
    plan = state["plan"]
    if (plan.confidence > 0.8
            and plan.blast_radius == "low"
            and plan.action_type not in DESTRUCTIVE_ACTIONS):
        return "execute"   # auto-execute path
    else:
        return "hitl"      # human approval path

graph.add_conditional_edges("safety", safety_router, {
    "execute": "execute",
    "hitl":    "hitl"
})
```

### Required Checkpointer

```python
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer, interrupt_before=["hitl"])
```

### HITL Resume Pattern (required)

```python
# FastAPI webhook receives Slack callback:
@app.post("/slack/callback")
async def slack_callback(payload: dict):
    approved = payload["actions"][0]["value"] == "approve"
    thread_id = payload["callback_id"]
    # Resume the paused graph:
    app.invoke(
        {"approved": approved},
        config={"configurable": {"thread_id": thread_id}}
    )
```

---

## SECTION 15: WHAT IS EXPLICITLY FORBIDDEN

| Forbidden Action | Consequence |
|---|---|
| Mocking kubectl output instead of real minikube | Invalid demo — disqualified |
| Using a single LLM prompt to replace the 7-stage pipeline | Penalised under Technical Execution |
| Agent with cluster-admin RBAC permissions | Security failure — points deducted |
| Auto-executing any action with blast_radius != low | Safety Gate violation |
| Auto-draining a Node NotReady (must be HITL) | Critical constraint violation |
| Manual kubectl commands during demo window | Demo invalidated |
| Spin-waiting for HITL instead of proper graph pause/resume | Architecture failure |
| Plagiarism / direct reuse of existing K8s operator code without significant modification | Disqualification |
| Dishonest disclosure of fallback methods | 0 marks for affected criterion |
| Storing only random hash in Web3 without pipeline integration | 0 marks for Web3 bonus |

---

## SECTION 16: 24-HOUR BUILD TIMELINE (OFFICIAL)

| Hours | Task | Key Output |
|---|---|---|
| 00–02h | Setup & scaffold | minikube up · kubectl MCP skeleton · LangGraph StateGraph with 8 empty nodes · deps |
| 02–05h | Observe + Detect | observe_node polling loop · kubectl MCP read-only tools · detect_node LLM classifier |
| 05–09h | Diagnose + Plan | diagnose_node sub-agent (logs + describe) · plan_node with RemediationPlan schema |
| 09–13h | Safety Gate + Execute | safety_router conditional edge · kubectl action tools · execute_node with 30s verify · RBAC YAML |
| 13–17h | HITL + Slack | hitl_node with FastAPI webhook · Slack Block Kit message · Approve/Reject buttons · audit trail |
| 17–20h | Demo scenarios | crashloop.yaml · oomkill.yaml · pending.yaml · Prometheus MCP · rehearse demo flow |
| 20–22h | Stress test | Run all 3 scenarios 3× · fix flaky edges · retry logic · verify HITL end-to-end · freeze code |
| 22–24h | Presentation prep | Architecture slide · 5-minute script · fallback recorded demo · practice judge Q&A |

---

## SECTION 17: BONUS OPPORTUNITIES (PS1-SPECIFIC)

Each bonus worth up to 5 marks:

| Bonus | Marks | Requirement |
|---|---|---|
| Prometheus MCP | Up to 5 | Metric-driven detection: CPU throttling (`cpu_throttled > 0.5`) and memory pressure |
| Multi-namespace support | Up to 5 | Agent monitors and acts across multiple namespaces |
| Predictive alerting | Up to 5 | Alert before pod crashes (trend detection on restart_count, memory usage) |
| Auto-generated GitHub PR | Up to 5 | Permanent config fix (e.g., memory limit increase) submitted as PR |

---

## SECTION 18: WEB3 BONUS — 25 MARKS

**Submission link:** https://www.risein.com/programs/hackathon-project-submission-stellar?referral=JEtvo

### Scoring

| Criterion | Marks |
|---|---|
| Valid repo structure (Frontend + Smart Contract + Integration) | 10 |
| Meaningful use — adds real value to the pipeline | 10 |
| Quality of demo and explanation | 5 |
| **TOTAL** | **25** |

### What Counts as Meaningful Integration (from FAQ Q16)

- Blockchain MUST interact with pipeline output (e.g., store incident records immutably, log HITL decisions on-chain)
- Storing only a hash or random data with no connection to the pipeline → **0 marks**

### Required Repository Structure

```
YourProject/
├── contracts/hello-world/
│   ├── .gitignore
│   ├── Cargo.lock
│   ├── Cargo.toml
│   └── README.md
├── public/
├── src/
│   ├── components/
│   ├── App.css
│   ├── App.js
│   ├── index.css
│   └── index.js
├── .gitignore
├── README.md
├── package.json
└── tailwind.config.js
```

### Required README Sections

1. Project Title
2. Project Description
3. Project Vision
4. Key Features
5. Deployed Smart Contract Details (Contract ID + block explorer screenshot)
6. UI Screenshots
7. Demo link (optional)
8. Demo video (optional)
9. Project Setup Guide
10. Future Scope

**Note:** README must not look AI-generated.

### Integration Requirement

- Must use **Stellar-SDK** to call deployed smart contract functions from the frontend
- Deploying a contract without frontend integration → does NOT qualify

### Reference Repos

- https://github.com/bhupendra-chouhan/Stellar-Journey-to-Mastery
- https://github.com/bhupendra-chouhan/CratePass-Soroban

### Frontend

- Example uses React + Tailwind CSS
- Other frameworks allowed if repo is clean and integration exists
- Dummy contract without integration = invalid (from FAQ Q18)

---

## SECTION 19: COMPLETE CONSTRAINT CHECKLIST FOR AGENT ANALYSIS

The following is a flat, unambiguous list of every hard constraint. Each must be satisfied.

### Pipeline Constraints

- [ ] All 7 stages implemented as distinct structured components
- [ ] Stage 01: polls every 30 seconds
- [ ] Stage 01: uses real minikube cluster (no mocks)
- [ ] Stage 02: outputs typed Anomaly objects with confidence float
- [ ] Stage 03: fetches actual kubectl logs and kubectl describe
- [ ] Stage 04: outputs RemediationPlan with blast_radius field
- [ ] Stage 05: conditional edge with exact auto-execute logic (`confidence > 0.8 AND blast_radius == "low" AND not destructive`)
- [ ] Stage 06: waits 30 seconds post-action before re-checking
- [ ] Stage 06: verify step POLLS — does not check once
- [ ] Stage 07: plain English explanation for every incident
- [ ] Stage 07: persistent JSON audit log

### Data Flow Constraints

- [ ] All nodes use shared ClusterState TypedDict
- [ ] No node maintains local state
- [ ] All required fields present in ClusterState

### RBAC Constraints

- [ ] ServiceAccount + Role + RoleBinding YAML file exists
- [ ] `kubectl auth can-i delete namespace --as=...` returns `no`
- [ ] `kubectl auth can-i delete pods -n production --as=...` returns `yes`
- [ ] `kubectl auth can-i get pods -n production --as=...` returns `yes`
- [ ] No cluster-admin permissions anywhere

### Safety Gate Constraints

- [ ] Restart pod is classified as blast_radius = low
- [ ] Scaling/rollout/node ops classified as NOT low
- [ ] No destructive action auto-executes
- [ ] Node NotReady NEVER auto-drains — HITL only

### HITL Constraints

- [ ] Slack Block Kit message with Approve/Reject buttons
- [ ] FastAPI webhook receives Slack callback
- [ ] LangGraph graph pauses cleanly (no spin-wait)
- [ ] LangGraph graph resumes on callback
- [ ] Judge physically clicks Approve during live demo

### Demo Constraints

- [ ] 3 scenarios deployed: CrashLoop, OOMKill, Pending
- [ ] CrashLoop demonstrates auto-fix end-to-end
- [ ] OOMKill demonstrates HITL flow end-to-end
- [ ] Pending demonstrates explanation output
- [ ] Agent responds to live-injected anomaly autonomously
- [ ] Zero manual kubectl commands during demo window
- [ ] Demo is live (not recorded — recorded is backup only)

### Audit Log Constraints

- [ ] JSON format, persistent on disk
- [ ] At least 3 complete incident records
- [ ] Each record has: timestamp, anomaly_type, diagnosis, action_taken, result, explanation
- [ ] Explanation is plain English (non-expert readable)

### Submission Constraints

- [ ] GitHub repo submitted before judging begins
- [ ] README with setup instructions
- [ ] Architecture diagram included
- [ ] Source code is original — no direct copy of existing K8s operators

---

## SECTION 20: QUICK REFERENCE — MARKS AT STAKE

| What | Marks Lost if Missing |
|---|---|
| Any of the 7 pipeline stages missing | Major deduction under Technical Execution (40 marks) |
| Safety Gate wrong logic | Up to 25 marks at risk |
| No HITL / Slack flow | Up to 25 marks at risk |
| No RBAC / cluster-admin present | Up to 10 marks at risk + disqualification risk |
| Only CrashLoopBackOff implemented | Bottom quartile score |
| No verify loop (check once only) | Deduction under Autonomous Remediation (30 marks) |
| No persistent audit log | Deduction under Diagnosis Quality (20 marks) |
| Manual kubectl during demo | Demo invalidated |
| Mocked kubectl outputs | Invalid demo |
| Generic LLM explanations (no evidence) | Poor Diagnosis Quality score |
| Spin-waiting for HITL | Architecture failure |

---

*Document generated from: hackathon_ps_compendium_v2.pdf + FAQs.pdf*
*Covers: PS1 K8sWhisperer — all requirements, constraints, scoring, FAQs, and hidden traps*
*Intended audience: Antigravity agent analysis + human team reference*
