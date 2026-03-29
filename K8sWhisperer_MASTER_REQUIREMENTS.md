# K8sWhisperer — MASTER REQUIREMENTS DOCUMENT
## PS1 · DevOps × AI/ML Track · Team Delivery Specification
### 24-Hour Hackathon Delivery Plan · 100 Marks + 25 Web3 Bonus

> **Purpose of this document:** Single source of truth for the team’s operative build specification for PS1. This document preserves the depth and structure of the original master requirements format, but it is rewritten to match the current repo contracts, agreed routing decisions, demo strategy, and actual implementation plan. It is intended for human teammates and coding agents.

---

## SECTION 1: PROBLEM IDENTITY

| Field | Value |
|---|---|
| Problem Statement | PS1 — K8sWhisperer |
| Track | DevOps × AI/ML |
| Subtitle | Kubernetes Incident Response Agent |
| Delivery Basis | 24-hour team delivery plan |
| Team Size | 2–4 members |
| Difficulty | Extreme — Full structured pipeline required |
| Max Marks | 100 (+ 25 Web3 bonus) |

**Core v1 implementation stack:** LangGraph · kubectl-backed cluster adapter · FastAPI · Slack HITL messaging · hosted LLM (Groq/OpenAI-compatible) · minikube

**Stretch / optional stack:** LangChain specialization · Prometheus metrics · MCP-style tool abstraction layers · multi-namespace production hardening · Web3 bonus

**One-line goal:** Build an autonomous Kubernetes incident-response agent that continuously monitors cluster state, detects anomalies, diagnoses root causes, plans remediation actions, executes safe fixes automatically, routes risky or failed cases through human approval, and logs every decision in plain English.

**Important framing constraint:** This document is an engineering delivery spec, not a verbatim copy of the official challenge PDF. Where the original problem statement is broad or internally ambiguous, this document defines the exact implementation choices the team will build.

---

## SECTION 2: MANDATORY PIPELINE — 7 STAGES (ALL REQUIRED)

**CONSTRAINT:** All 7 stages must exist as structured pipeline components. A single LLM prompt replacing the full pipeline is NOT allowed. Hardcoded one-shot flows or hidden state outside the shared graph state are not valid architecture.

### Stage 01 — Observe (Cluster Scan)

- **Tool:** kubectl-backed cluster adapter
- **Target architecture:** Poll all namespaces every 30 seconds
- **Current delivery profile:** Same pipeline shape, but demo scenarios run in the `production` namespace and current adapter scans `production` for reliability
- **Data collected:** Pod status, restart counts, exit codes, logs on demand, describe output on demand
- **Output:** Normalized `ClusterState.events`
- **Constraint:** Final demo must operate against a real minikube cluster. Fixture data is allowed only for isolated development and unit tests, not for the live response path

### Stage 02 — Detect (Anomaly Classification)

- **Input:** Raw event stream from `ClusterState.events`
- **Tool:** LLM classifier
- **Output:** Typed `Anomaly` objects with fields:
  - `type`
  - `severity`
  - `affected_resource`
  - `namespace`
  - `confidence`
- **Constraint:** The classifier must return structured typed output. It cannot replace later pipeline stages

### Stage 03 — Diagnose (Root Cause Analysis)

- **Input:** Selected anomaly + real evidence
- **Data fetched:** `kubectl logs`, `kubectl describe`, recent cluster events already present in state
- **Output:** Root-cause string with supporting evidence
- **Constraint:** Diagnosis must be synthesized from actual kubectl output. Explanations should cite status reasons, restart patterns, exit codes, or log content where available

### Stage 04 — Plan (Remediation Proposal)

- **Node type:** Planner node
- **Output:** `RemediationPlan` object with fields:
  - `action`
  - `target_resource`
  - `params`
  - `confidence`
  - `blast_radius`
  - optional `reason`
  - optional `namespace`
- **Constraint:** Planner output must use repo-compatible field names exactly. `params["memory_limit"]` is the canonical memory patch key

### Stage 05 — Safety Gate (Risk-Based Routing)

**This is a deterministic LangGraph routing step. Rules are exact and must not be delegated to the LLM.**

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

**Official blast_radius classifications used by the team:**
| Action | blast_radius | Route |
|---|---|---|
| Restart pod (delete pod) | LOW | Auto-execute allowed |
| Patch memory limit for single Deployment | LOW | Auto-execute allowed if confidence > 0.8 |
| Explain-only / no-op recommendation | LOW | Auto-execute allowed |
| Scaling operations | NOT LOW | HITL required |
| Rollout operations | NOT LOW | HITL required |
| Node operations | NOT LOW | HITL required |
| Any destructive action | NOT LOW | HITL required |

**CONSTRAINT:** No destructive auto-executions are allowed. The safety gate is deterministic even when the LLM is wrong or uncertain.

### Stage 06 — Execute (Surgical kubectl Action)

- **Tool:** kubectl-backed cluster adapter
- **Supported v1 actions:** `restart_pod`, `patch_memory_limit`, `explain_only`
- **Post-action verification:** Poll with backoff, not a single check
- **Verification model:** For pod recreation scenarios, verify at Deployment/workload level rather than deleted pod name
- **Output:** Sets `result` and `execution_status` in `ClusterState`
- **Constraint:** Verification failure is a valid outcome. The graph must escalate or route safely, not crash

### Stage 07 — Explain & Log (Audit Trail)

- **LLM task:** Write human-readable incident summary
- **Slack:** Send approval request for HITL cases and surface summaries where appropriate
- **Persistence:** Append `LogEntry` to persistent `audit_log.json`
- **Constraint:** Explanations must be understandable to a non-expert
- **Current graph behavior:** On HITL, the graph may pause before explanation until the approval callback resumes the run. This is expected behavior, not a failure

---

## SECTION 3: LANGGRAPH STATE SCHEMA

**CONSTRAINT:** All nodes read from and write to a shared `ClusterState` TypedDict. Node-local hidden business state is not allowed. LangGraph pause/resume depends on explicit state.

```python
class ClusterState(TypedDict):
    incident_id:        str
    events:             list[dict]
    anomalies:          list[Anomaly]
    diagnosis:          str
    plan:               RemediationPlan
    approved:           bool
    approval_requested: bool
    result:             str
    audit_log:          list[LogEntry]
    explanation:        str
    execution_status:   str
```

**Required sub-types (repo-aligned canonical names):**
```python
class Anomaly(TypedDict):
    type:               str
    severity:           str
    affected_resource:  str
    confidence:         float
    namespace:          str
    reason:             str            # optional
    evidence:           list[str]      # optional

class RemediationPlan(TypedDict):
    action:             str            # restart_pod | patch_memory_limit | explain_only
    target_resource:    str
    params:             dict
    confidence:         float
    blast_radius:       str            # low | medium | high
    reason:             str            # optional
    namespace:          str            # optional

class LogEntry(TypedDict):
    incident_id:        str
    timestamp:          str
    anomaly:            Anomaly
    diagnosis:          str
    plan:               RemediationPlan
    approved:           bool
    result:             str
    explanation:        str
```

**Canonical naming constraints:**
- Use `action`, NOT `action_type`
- Use `params`, NOT `parameters`
- Use `affected_resource`, NOT `pod_name` in anomaly output
- Use `target_resource`, NOT `target`
- Use `memory_limit`, NOT `new_limit`

---

## SECTION 4: ANOMALY CLASSIFICATION MATRIX

**CONSTRAINT:** The team will finish the 3 mandatory scenarios first. Optional anomaly types are stretch work only after the core pipeline is stable.

| Anomaly Type | Trigger Signal | Current Planned Action | Severity | Min Required? |
|---|---|---|---|---|
| CrashLoopBackOff | `status == CrashLoopBackOff` OR `restart_count > 3` with non-zero exit | Diagnose → restart pod attempt → verify → HITL if persistent | HIGH | ✅ YES |
| OOMKilled | `status == OOMKilled` OR `exit_code == 137` | Diagnose → patch memory + verify → auto if safety gate passes | HIGH | ✅ YES |
| Pending Pod | `status == Pending` | Diagnose → explain-only recommendation | MED | ✅ YES |
| ImagePullBackOff | waiting reason indicates image pull failure | Explain-only / alert human | MED | Stretch |
| CPU Throttling | Prometheus metric signal | Patch CPU or recommend | MED | Stretch |
| Evicted Pod | status or reason indicates eviction | Cleanup / explain | LOW | Stretch |
| Deployment Stalled | rollout never converges | HITL only | HIGH | Stretch |
| Node NotReady | node readiness false | HITL only — never auto-drain | CRITICAL | Stretch |

**CrashLoopBackOff interpretation used by this team:**
- The first action is a low-risk restart attempt
- In the current demo scenario, the crash is persistent by design
- Therefore the restart is expected to fail verification and escalate to HITL

**OOMKilled interpretation used by this team:**
- OOMKilled is auto-eligible under the safety gate
- If the plan is high-confidence and low blast-radius, it auto-executes
- If confidence drops or risk increases, it routes to HITL

**Pending interpretation used by this team:**
- Pending is explanation/recommendation only in v1
- No unsafe scheduling or scaling action is auto-executed

---

## SECTION 5: REQUIRED DELIVERABLES (TEAM DELIVERY SPEC)

### Deliverable 1 — Live Agent Demo

- Working demo against a real minikube cluster
- Must cover at least 3 anomaly scenarios:
  - CrashLoopBackOff → restart attempt → verify failure → HITL escalation
  - OOMKilled → auto-fix happy path if safety gate passes
  - Pending Pod → explanation path
- Judges may inject a live anomaly during demo
- Team must let the agent respond autonomously during the active response window
- Recorded demo is backup only, not primary presentation mode

### Deliverable 2 — HITL Slack Flow

- Slack message with Approve / Reject interactive buttons
- FastAPI webhook receives callback and resumes the paused LangGraph execution
- Full flow should work live, including actual approval
- **Webhook payload contract:**
```json
{
  "incident_id": "string",
  "approved": true
}
```

### Deliverable 3 — Audit Trail

- Persistent JSON audit log file
- Must log every incident decision, action taken, result, and explanation
- Final demo should show at least 3 complete incident records
- Explanation field must be plain English and non-expert readable

### Deliverable 4 — RBAC YAML

- File set must define:
  - ServiceAccount
  - Role
  - RoleBinding
- Scope: namespace-scoped pod and deployment operations for demo safety
- Judges will inspect for cluster-admin absence
- Demo requirement:
```yaml
# Minimum expected permissions:
# - get/list/watch on pods, pods/log, events
# - delete on pods
# - get/list/watch/patch on deployments
# MUST NOT include cluster-admin
```

### Deliverable 5 — Architecture Presentation

- Duration: 5 minutes
- Must cover:
  1. Problem statement
  2. LangGraph node graph
  3. Cluster adapter/tool design
  4. Safety gate logic
  5. Live demo behavior

### Deliverable 6 — GitHub Submission

- Source code repository
- README with setup instructions
- Architecture diagram

---

## SECTION 6: SCORING RUBRIC — TEAM PRIORITY INTERPRETATION

### PS1-Specific Rubric (100 marks)

| Criterion | Marks | What Judges Look For |
|---|---|---|
| Autonomous Remediation | 30 | Correct auto-fix behavior for low-risk scenarios such as OOMKilled and safe restart attempts. Strong verify loop. |
| Safety Gate & HITL | 25 | Correct routing, no destructive auto-execution, Slack approval flow works end-to-end. |
| Diagnosis Quality | 20 | Evidence-backed diagnosis from real kubectl output. Plain-English explanation quality. |
| LangGraph Architecture | 15 | Clean node graph, conditional routing, checkpointer usage, shared TypedDict state. |
| Tool / Integration Layer | 10 | Real kubectl integration, webhook integration, scoped RBAC, reliable runtime behavior. |
| **TOTAL** | **100** | |

### Overall Hackathon Rubric (normalisation + tie-breaking)

| Criterion | Marks | What Judges Look For |
|---|---|---|
| Technical Execution | 40 | Full structured pipeline, no critical demo failure, real cluster behavior |
| Problem-Solving Depth | 20 | Safety decisions, failure handling, realistic engineering tradeoffs |
| Code & System Design | 15 | Clear modular code, shared state, maintainable architecture |
| Explainability & Communication | 15 | Good explanations, clear demo narrative, understandable output |
| Innovation & Impact | 10 | Thoughtful extensions after core system is stable |
| **TOTAL** | **100** | |

### Scoring Bands

| Band | Score | Description |
|---|---|---|
| Failing | Below 40 | Missing stages or broken end-to-end behavior |
| Passing | 40–65 | Mandatory pipeline present but shallow or unreliable |
| Good | 65–80 | Mandatory scenarios stable, evidence-backed explanations, working HITL |
| Strong | 80–90 | Mandatory scenarios plus meaningful optional extension(s) |
| Exceptional | 90+ | Outstanding robustness, polish, and useful extensions |

**Team scoring strategy:** Prioritize rubric-heavy categories first:
- autonomous remediation
- safety gate / HITL
- diagnosis quality

Optional extensions are pursued only after the 3 mandatory scenarios are stable end to end.

---

## SECTION 7: HIDDEN TRAPS — WHAT WILL BREAK NAIVE IMPLEMENTATIONS

### Trap 1 — Race Conditions

**Problem:** Two anomalies appear close together or concurrently.
**Requirement:** Shared state must not be corrupted.
**Constraint:** Concurrency is not mandatory for passing, but matters for 80+ robustness.

### Trap 2 — False Positives

**Problem:** Planned rollout restarts vs real crash loops.
**Requirement:** Classifier should eventually distinguish rollout noise from actual failure.
**Current note:** This is a higher-score robustness feature, not the first delivery target.

### Trap 3 — RBAC Footgun

**Problem:** Overbroad permissions allow dangerous hallucinated actions.
**Requirement:** Namespace-scoped permissions only for demo path.
**Verification:** Judges may inspect `kubectl auth can-i ...` output.

### Trap 4 — Verify Loop

**Problem:** New pods do not become healthy instantly.
**Requirement:** Verify must poll with backoff.
**Implementation note:** Recreated pods must be tracked at Deployment/workload level, not by old deleted pod name.

### Trap 5 — Slack Webhook Latency

**Problem:** Human approval may take minutes.
**Requirement:** Graph must pause cleanly and resume on callback.
**Forbidden:** Spin-waiting, busy loops, or fake approval timeouts.

### Trap 6 — Log Noise

**Problem:** `kubectl logs` can be large or empty depending on crash timing.
**Requirement:** Summarize relevant logs before sending to the LLM.
**Implementation note:** CrashLoop scenarios may provide minimal logs and stronger evidence via `describe`.

---

## SECTION 8: OFFICIAL FAQ ANSWERS — TEAM INTERPRETATION

### Q1 — Real system vs mock?

**Answer:** Final demo must run on a real minikube cluster. Mocks are permitted only for isolated development and unit testing.

### Q2 — Can the LLM replace the pipeline?

**Answer:** No. The LLM is used inside stages like detect, diagnose, plan, and explain, but the pipeline remains structured and explicit.

### Q3 — What counts as a working pipeline?

**Answer:** A valid pipeline must:
- execute all mandatory stages
- pass data through shared state
- produce a final result and explanation or an approval wait state

### Q4 — Safety Gate ambiguity

**Answer:** Auto-execute only if all three conditions pass:
- `confidence > 0.8`
- `blast_radius == "low"`
- action is not destructive

All other cases route to HITL.

### Q5 — Demo autonomy requirement

**Answer:** The system must react autonomously to live anomalies in the demo path. Manual kubectl intervention during active response should be avoided.

### Q6 — Concurrency requirement

**Answer:** Not mandatory for passing. Treated as an advanced robustness feature.

### Q7 — Prometheus required?

**Answer:** No for v1. Prometheus-driven detection is a stretch/bonus feature.

### Q8 — OOMKilled routing conflict between rubric and examples

**Answer:** Team interpretation is:
- OOMKilled is **auto if safe**
- HITL is required only if safety gate conditions fail

This preserves scoring potential while keeping the safety gate deterministic.

### Q9 — CrashLoopBackOff demo behavior

**Answer:** Team implementation uses a persistent crash scenario for v1 demo stability:
- detect crash loop
- attempt restart
- verify fails
- escalate to HITL

This is intentional and acceptable as the current demo path.

---

## SECTION 9: TECH STACK — CORE V1 VS STRETCH

### Core v1 Implementation Stack

| Component | Purpose | Notes |
|---|---|---|
| LangGraph StateGraph | Orchestration | Shared state, conditional routing, checkpointer |
| kubectl-backed cluster adapter | Cluster operations | Real subprocess-based adapter for kubectl |
| FastAPI | HITL webhook | Receives approval callback and resumes graph |
| Slack messaging | HITL notifications | Approve / Reject flow |
| Hosted LLM | Detect / Diagnose / Plan / Explain | Groq/OpenAI-compatible path |
| minikube | Local Kubernetes cluster | Real demo environment |

### Stretch / Optional Integrations

| Component | Benefit |
|---|---|
| LangChain specialization | Richer diagnosis sub-agent behavior |
| Prometheus | CPU throttling, memory pressure, predictive metrics |
| MCP-style abstractions | Cleaner external tool boundary |
| Multi-namespace support | Closer to target architecture |
| Auto-generated GitHub PR | Permanent remediation follow-up |

**Constraint:** Prometheus, LangChain specialization, and broader MCP abstractions must not be presented as mandatory for passing v1.

---

## SECTION 10: DEMO SCENARIOS — REQUIRED YAML FILES

Three scenario YAML files are required for the team’s planned demo.

### Scenario 1 — CrashLoopBackOff (`crashloop.yaml`)

**Expected behavior:** Deployment-backed pod exits with code 1 repeatedly and enters CrashLoopBackOff after repeated restart attempts.

**Agent path:**
- detect crash loop
- diagnose using describe/logs
- plan `restart_pod`
- auto-execute if safety gate passes
- verify against recreated Deployment pod
- if still crashing, escalate to HITL

**Current team interpretation:** This is the verify-failure-to-HITL scenario.

### Scenario 2 — OOMKilled (`oomkill.yaml`)

**Expected behavior:** Deployment-backed pod exceeds memory limit and is killed with OOM behavior / exit code 137.

**Agent path:**
- detect OOMKilled
- diagnose memory-pressure style failure
- plan `patch_memory_limit`
- auto-execute if safety gate passes
- patch memory using `params["memory_limit"]`
- verify recreated pod is healthy

**Current team interpretation:** This is the clean auto-fix happy-path scenario.

### Scenario 3 — Pending Pod (`pending.yaml`)

**Expected behavior:** Deployment-backed pod remains Pending because its requested resources cannot be scheduled.

**Agent path:**
- detect Pending
- diagnose failed scheduling / capacity mismatch
- plan `explain_only`
- route through explanation path without unsafe action

**Current team interpretation:** This is the explain-only scenario.

---

## SECTION 11: TOOLING / ADAPTER REQUIREMENTS

kubectl operations are exposed through a typed adapter/tool layer. This does not require a separate MCP server in the current repo, but the interface must remain typed and explicit.

### Required Adapter Methods

| Method | Arguments | Returns | Purpose |
|---|---|---|---|
| `scan_cluster` | none | `list[dict]` | Normalized pod snapshots |
| `get_pod_logs` | `resource_name, namespace, tail_lines` | `str` | Log summary for diagnosis |
| `describe_pod` | `resource_name, namespace` | `str` | Raw describe output |
| `restart_pod` | `resource_name, namespace` | `str` | Delete pod so controller recreates it |
| `patch_memory_limit` | `resource_name, namespace, memory_limit` | `str` | Patch owning Deployment memory limit |
| `get_resource_state` | `resource_name, namespace` | `dict` | Direct pod state lookup when applicable |

### Slack / HITL Integration Requirements

| Feature | Requirement |
|---|---|
| Message format | Approve / Reject interactive message |
| Webhook path | FastAPI `POST /webhook/slack` |
| Resume payload | `incident_id`, `approved` |
| Graph behavior | Resume paused execution using `incident_id` as thread id |

---

## SECTION 12: RBAC SPECIFICATION

### Required YAML Structure

```yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: k8swhisperer-sa
  namespace: production
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: production
  name: k8swhisperer-role
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
  name: k8swhisperer-binding
  namespace: production
subjects:
  - kind: ServiceAccount
    name: k8swhisperer-sa
    namespace: production
roleRef:
  kind: Role
  name: k8swhisperer-role
  apiGroup: rbac.authorization.k8s.io
```

### Scope Interpretation

- Demo delivery is namespace-scoped to `production` for least privilege
- All-namespaces remains the intended architectural target
- Broader scope is an architectural extension, not the demo baseline

### Judge Verification Commands (target output)

```bash
# MUST output: no
kubectl auth can-i delete namespace \
  --as=system:serviceaccount:production:k8swhisperer-sa

# MUST output: yes
kubectl auth can-i delete pods -n production \
  --as=system:serviceaccount:production:k8swhisperer-sa

# MUST output: yes
kubectl auth can-i patch deployments -n production \
  --as=system:serviceaccount:production:k8swhisperer-sa
```

---

## SECTION 13: AUDIT LOG SPECIFICATION

### Required Format

```json
{
  "audit_log": [
    {
      "incident_id": "uuid-string",
      "timestamp": "2026-XX-XXTXX:XX:XXZ",
      "anomaly": {
        "type": "CrashLoopBackOff",
        "severity": "HIGH",
        "affected_resource": "payment-api-abc123",
        "namespace": "production",
        "confidence": 0.91
      },
      "diagnosis": "Pod is repeatedly crashing during startup. Describe output shows CrashLoopBackOff and a non-zero exit code.",
      "plan": {
        "action": "restart_pod",
        "target_resource": "payment-api-abc123",
        "params": {},
        "confidence": 0.91,
        "blast_radius": "low"
      },
      "approved": false,
      "result": "verification failed after restart attempt",
      "explanation": "The payment-api pod kept crashing after a restart attempt, so the agent escalated the incident for human review."
    }
  ]
}
```

### Constraints

- File must persist on disk across cycles
- Final demo should show at least 3 complete incident records
- Each record must populate the agreed repo-compatible fields
- Explanation must be plain English and understandable to a non-expert

---

## SECTION 14: LANGGRAPH ARCHITECTURE REQUIREMENTS

### Node Definitions

```python
# Required nodes in the current graph design:
graph.add_node("observe",         observe)         # Stage 01
graph.add_node("detect",          detect)          # Stage 02
graph.add_node("diagnose",        diagnose)        # Stage 03
graph.add_node("plan",            plan)            # Stage 04
graph.add_node("safety_gate",     safety_gate)     # Stage 05
graph.add_node("execute",         execute)         # Stage 06
graph.add_node("hitl_request",    hitl_request)    # Stage 05 request path
graph.add_node("hitl_wait",       hitl_wait)       # Stage 05 pause/resume path
graph.add_node("explain_and_log", explain_and_log) # Stage 07
```

### Required Conditional Routing

```python
def route_after_safety(state):
    if state["execution_status"] == "awaiting_approval":
        return "hitl_request"
    return "execute"

def route_after_execute(state):
    if state["execution_status"] == "verification_failed" and not state["approved"]:
        return "hitl"
    return "explain_and_log"
```

### Required Checkpointer

```python
from langgraph.checkpoint.memory import MemorySaver
app = graph.compile(checkpointer=MemorySaver())
```

### HITL Resume Pattern

```python
@app.post("/webhook/slack")
def slack_callback(payload: dict):
    incident_id = payload["incident_id"]
    approved = bool(payload.get("approved", False))
    graph.invoke(
        Command(resume={"approved": approved}),
        config={"configurable": {"thread_id": incident_id}},
    )
```

---

## SECTION 15: WHAT IS EXPLICITLY FORBIDDEN

| Forbidden Action | Consequence |
|---|---|
| Using mocks for the live demo path instead of real minikube | Invalid demo |
| Replacing the full pipeline with one big LLM prompt | Technical execution penalty |
| Using cluster-admin or broad destructive permissions | Security failure / major deduction |
| Auto-executing any action with `blast_radius != low` | Safety gate violation |
| Auto-draining nodes | Critical constraint violation |
| Manual kubectl intervention during active response window | Demo credibility failure |
| Spin-waiting for HITL | Architecture failure |
| Changing canonical field names mid-implementation | Integration breakage |
| Using `new_limit` instead of `memory_limit` | Silent execute failure risk |

---

## SECTION 16: 24-HOUR BUILD TIMELINE (TEAM DELIVERY)

| Hours | Task | Key Output |
|---|---|---|
| 00–02h | Contracts & scaffold | repo setup, shared state contract, adapter seams, graph skeleton |
| 02–05h | Observe + Detect | real cluster scan shape, classify path, stable detect node |
| 05–09h | Diagnose + Plan | evidence gathering, diagnosis output, repo-compatible remediation plans |
| 09–13h | Safety Gate + Execute | deterministic routing, verify loop, deployment-aware verification |
| 13–17h | HITL + Slack | webhook, notifier, pause/resume, approval flow |
| 17–20h | Demo scenarios | crashloop, oomkill, pending stabilized against minikube |
| 20–22h | Stress test | scenario reruns, flaky edge fixes, code freeze |
| 22–24h | Presentation prep | architecture diagram, script, README, final demo rehearsal |

---

## SECTION 17: BONUS OPPORTUNITIES (PS1-SPECIFIC)

Each bonus is pursued only after mandatory scenarios are stable.

| Bonus | Value | Requirement |
|---|---|---|
| Prometheus metrics | Stretch | CPU throttling / predictive signals |
| Multi-namespace support | Stretch | Move from demo `production` scope toward target architecture |
| Predictive alerting | Stretch | Detect before failure, not only after |
| Auto-generated GitHub PR | Stretch | Permanent follow-up fix proposal |

---

## SECTION 18: WEB3 BONUS — 25 MARKS

**Team policy:** Web3 is not part of the critical path for v1 delivery. It is considered only after the 3 mandatory scenarios, HITL, audit log, and README are stable.

### Scoring

| Criterion | Marks |
|---|---|
| Valid repo structure | 10 |
| Meaningful pipeline-connected use | 10 |
| Demo / explanation quality | 5 |
| **TOTAL** | **25** |

### Meaningful Integration Constraint

- Blockchain interaction must connect to actual pipeline output
- Logging random data or unrelated hashes does not count

### Team Preference

- If attempted, Web3 should be an add-on to policy or audit behavior
- It must never block the core minikube + LangGraph + HITL demo

---

## SECTION 19: COMPLETE CONSTRAINT CHECKLIST FOR TEAM DELIVERY

### Pipeline Constraints

- [ ] All 7 stages implemented as distinct structured components
- [ ] Observe polls on an interval
- [ ] Live path uses real minikube cluster
- [ ] Detect outputs typed anomalies with confidence float
- [ ] Diagnose uses real logs and describe output
- [ ] Plan outputs repo-compatible `RemediationPlan`
- [ ] Safety gate uses exact deterministic logic
- [ ] Execute verifies with backoff
- [ ] Explanation is plain English
- [ ] Audit log persists to disk

### Data Flow Constraints

- [ ] All nodes use shared `ClusterState`
- [ ] No hidden business state outside graph state
- [ ] Canonical field names are consistent across adapters and LLM outputs

### RBAC Constraints

- [ ] ServiceAccount + Role + RoleBinding exist
- [ ] delete namespace returns `no`
- [ ] delete pods in production returns `yes`
- [ ] patch deployments in production returns `yes`
- [ ] no cluster-admin permissions

### Safety Gate Constraints

- [ ] Restart pod is low blast radius
- [ ] Memory patch is low blast radius for current demo scope
- [ ] scaling / rollout / node ops are not low blast radius
- [ ] no destructive action auto-executes

### HITL Constraints

- [ ] Slack approval message exists
- [ ] FastAPI webhook receives callback
- [ ] Graph pauses cleanly
- [ ] Graph resumes from `incident_id`
- [ ] callback payload includes `incident_id` and `approved`

### Demo Constraints

- [ ] 3 scenarios available: CrashLoopBackOff, OOMKilled, Pending
- [ ] CrashLoop shows restart attempt then HITL escalation on persistent failure
- [ ] OOMKilled shows auto-fix happy path if safe
- [ ] Pending shows explain-only path
- [ ] agent reacts autonomously in active response window
- [ ] demo runs against real minikube

### Audit Log Constraints

- [ ] persistent JSON file
- [ ] at least 3 complete incident records by final demo
- [ ] each record includes diagnosis, plan, result, explanation
- [ ] explanation readable by non-expert

### Submission Constraints

- [ ] GitHub repo ready
- [ ] README with setup instructions
- [ ] architecture diagram included
- [ ] no contract-name drift between docs and code

---

## SECTION 20: QUICK REFERENCE — MARKS AT STAKE

| What | Marks / Risk at Stake |
|---|---|
| Missing pipeline stages | Major technical execution loss |
| Wrong safety gate logic | Up to 25 marks at risk |
| No working HITL / Slack resume | Up to 25 marks at risk |
| No RBAC or unsafe RBAC | Up to 10 marks at risk + demo risk |
| Weak autonomous remediation | Up to 30 marks at risk |
| No verify loop | Major autonomous remediation penalty |
| No persistent audit log | Diagnosis / explainability penalty |
| Generic explanations with no evidence | Diagnosis quality penalty |
| Manual intervention during active response | Demo credibility failure |
| Schema mismatch across teammate work | Integration failure risk |

---

*Document rewritten from the teammate master requirements draft to match the team’s current repo contracts and agreed delivery plan.*
*Intended audience: team members, coding agents, and integration owners.*
