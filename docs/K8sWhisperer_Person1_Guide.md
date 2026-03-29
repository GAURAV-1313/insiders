# K8sWhisperer — Person 1: Infrastructure & Kubernetes Layer
## Complete Beginner-Friendly Execution System
### 24-Hour Hackathon Edition · Windows + Codex/Antigravity

> ⚠️ **READ THIS FIRST:** You are on Windows. Every command runs in PowerShell or Command Prompt UNLESS stated otherwise. Minikube runs on your Windows machine. Python runs on your Windows machine. This guide holds your hand at every step.

> 🤖 **HOW TO USE WITH CODEX/ANTIGRAVITY:** Copy the prompt in each section exactly into Codex/Antigravity. It will generate the code. You paste and run it. You do NOT need to write code from scratch.

---

## Table of Contents

- [DOC 1 — Environment Setup](#doc-1--environment-setup)
- [DOC 2 — Kubernetes Essentials](#doc-2--kubernetes-essentials)
- [DOC 3 — kubectl Command Playbook](#doc-3--kubectl-command-playbook)
- [DOC 4 — MCP Tool Layer — Python Subprocess](#doc-4--mcp-tool-layer--python-subprocess)
- [DOC 5 — RBAC Security — Keep It Safe](#doc-5--rbac-security--keep-it-safe)
- [DOC 6 — Execution Engine — Fix Pods Automatically](#doc-6--execution-engine--fix-pods-automatically)
- [DOC 7 — Failure Handling & Edge Cases](#doc-7--failure-handling--edge-cases)
- [DOC 8 — Demo Scenario Setup](#doc-8--demo-scenario-setup)
- [DOC 9 — Testing & Validation Checklist](#doc-9--testing--validation-checklist)
- [DOC 10 — Debugging Playbook](#doc-10--debugging-playbook)
- [SECTION A — Master Execution Checklist](#section-a--master-execution-checklist)
- [SECTION B — Validation System](#section-b--validation-system)
- [SECTION C — Debug Prompts for Codex](#section-c--debug-prompts-for-codex)
- [SECTION D — Speed Mode Plan](#section-d--speed-mode-plan)
- [SECTION E — 24-Hour Time Plan](#section-e--24-hour-time-plan)

---

## DOC 1 — Environment Setup — Install Everything on Windows

> 🎯 **GOAL:** By the end of this doc, your laptop can run Kubernetes locally. Takes ~1 hour. Do this BEFORE the hackathon.

### What Is This? (Plain English)

Kubernetes is a system that runs containers (packaged apps). Minikube lets you run Kubernetes on your own laptop. kubectl is the command-line tool to talk to Kubernetes. Python subprocess is how we'll make Python code run kubectl commands. Think of it like: Python is the brain, kubectl is the hands, minikube is the pretend server.

---

### Step 1 — Install Chocolatey (Windows Package Manager)

Open PowerShell **AS ADMINISTRATOR** (right-click PowerShell → Run as Administrator):

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force;
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072;
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

**Expected output:** You will see 'Chocolatey installed' at the end.

**If it fails:** Check your internet connection. Try running PowerShell as Admin again.

---

### Step 2 — Install Docker Desktop

Minikube needs Docker to run containers. Download from: https://www.docker.com/products/docker-desktop/

- Download the .exe installer and run it
- Accept all defaults during installation
- RESTART your computer after installing
- Open Docker Desktop and wait for it to say 'Docker Desktop is running'

**Expected:** Green icon in system tray, Docker Desktop window shows 'Engine running'.

**If it fails:** Make sure Hyper-V is enabled. Go to Control Panel → Programs → Turn Windows features on or off → check Hyper-V.

---

### Step 3 — Install minikube and kubectl

In PowerShell **AS ADMINISTRATOR**:

```powershell
choco install minikube -y
choco install kubernetes-cli -y
```

Then **close and reopen PowerShell (as normal user this time)**. Run:

```powershell
minikube version
kubectl version --client
```

**Expected:** You see version numbers printed. Something like 'minikube version: v1.32.0'

**If 'not recognized' error:** Close ALL PowerShell windows and open a new one. The PATH needs to refresh.

---

### Step 4 — Install Python

Open PowerShell **AS ADMINISTRATOR**:

```powershell
choco install python --version=3.11.0 -y
```

After install, close and reopen PowerShell:

```powershell
python --version
# Should print: Python 3.11.0
```

**IMPORTANT:** When you installed Python, you MUST have checked 'Add Python to PATH'. If python command not found, re-install Python from python.org and check that box.

---

### Step 5 — Start Minikube (The Big Test)

This starts your local Kubernetes cluster. Run in PowerShell (normal, not Admin):

```powershell
minikube start --driver=docker --memory=4096 --cpus=2
```

This takes 3-5 minutes the first time. Wait for it to finish.

**Expected final output:** 'Done! kubectl is now configured to use minikube cluster'

**Then run these to verify:**

```powershell
kubectl get nodes
# Expected output:
# NAME      STATUS   ROLES           AGE   VERSION
# minikube  Ready    control-plane   1m    v1.28.x

kubectl get pods -A
# Expected: several system pods all showing Running or Completed
```

> ✅ **SUCCESS CHECK:** If `kubectl get nodes` shows 'minikube Ready' — your environment is working. This is the single most important thing to verify.

---

### Step 6 — Install Python Packages

```powershell
pip install kubernetes
pip install pyyaml
```

**Expected:** 'Successfully installed kubernetes-xx.x.x'

**If pip not found:** Try `python -m pip install kubernetes pyyaml`

---

### Step 7 — Create Your Project Folder

```powershell
cd C:\
mkdir k8swhisperer
cd k8swhisperer
mkdir tools
mkdir scenarios
mkdir rbac
mkdir tests
```

All your files go here. This is your working directory for the hackathon.

---

### Failure Cases & Fixes

| Problem | Fix |
|---|---|
| minikube start fails with 'docker not running' | Open Docker Desktop first, wait for green icon, then run minikube start again |
| 'kubectl' is not recognized | Close PowerShell, open new one. If still fails: `choco install kubernetes-cli -y` again |
| minikube start says 'Exiting due to PROVIDER_DOCKER_NOT_RUNNING' | Docker Desktop is not started. Launch it and wait 1 minute before retrying |
| 'choco' is not recognized | You did not open PowerShell as Admin when installing Chocolatey. Redo Step 1 as Admin. |
| Low memory warning | Close other apps. The `--memory=4096` gives minikube 4GB RAM. Fine for hackathon. |

---

## DOC 2 — Kubernetes Essentials — Only What You Need to Know

> This is not a full Kubernetes course. This is ONLY the 5 concepts you need to build your part. Read this once. The rest you will learn by doing.

---

### Concept 1 — What is a Pod?

A Pod is one running application. Think of it as a single process running in a box. When your agent sees a 'CrashLoopBackOff', that means a Pod keeps crashing and Kubernetes keeps restarting it. Your job: detect it crashed, restart it, check if it's fixed.

| Pod State | What It Means | What We Do |
|---|---|---|
| Running | App is working fine | Nothing |
| CrashLoopBackOff | App keeps crashing, K8s keeps restarting | Fetch logs → auto restart |
| OOMKilled | App used too much memory and was killed | Patch memory limits → restart |
| Pending | Pod can't start (no space, wrong image, etc) | Describe pod → explain why |
| ImagePullBackOff | Can't download the app's Docker image | Alert human |

---

### Concept 2 — What is a Namespace?

A Namespace is a folder inside Kubernetes. All pods live in a namespace. By default everything goes into 'default'. We will create a 'production' namespace for our demo. When you run kubectl, always add `-n production` to look inside that folder.

```bash
kubectl get pods              # looks in 'default' namespace
kubectl get pods -n production # looks in 'production' namespace
kubectl get pods -A           # looks in ALL namespaces
```

---

### Concept 3 — What is a Deployment?

A Deployment says 'I want 3 copies of this app running'. If one crashes, K8s starts a new one. We will create Deployments for our demo scenarios (crash, OOM, pending). When we 'patch' a Deployment, we change its configuration (like giving it more memory).

---

### Concept 4 — What is RBAC?

RBAC = Role-Based Access Control. It controls WHAT our agent is ALLOWED to do. We will create a limited ServiceAccount so our agent can only restart pods — it cannot delete namespaces or do anything dangerous. This is a competition requirement (judges will check for no cluster-admin).

---

### Concept 5 — The Three Commands You Must Know Cold

| Command | What It Does |
|---|---|
| `kubectl get pods -n production` | List all pods in production namespace — shows status, restarts, age |
| `kubectl describe pod <name> -n production` | Deep info about one pod — events, errors, resource usage |
| `kubectl logs <name> -n production --tail=50` | Last 50 lines of the pod's output — shows WHY it crashed |

---

### What You Will Build (Your Responsibility Only)

- minikube running locally
- Python functions that run kubectl commands
- Scenarios: deploy broken pods for testing
- RBAC: a ServiceAccount with limited permissions
- Execution engine: restart pod, patch memory, verify it worked

> **YOU DO NOT build:** LangGraph logic, LLM prompts, Slack messages. Those are Person 2 and Person 3's jobs. Your tools just need to work correctly when called.

---

## DOC 3 — kubectl Command Playbook — Every Command You Need

> These are REAL working commands. Copy them exactly. Each one is mapped to an anomaly type. Run them manually first to see what they output.

---

### Section A — Observation Commands (Read Cluster State)

**Get All Pods With Status:**
```bash
kubectl get pods -n production -o wide
# Expected output columns:
# NAME                    READY   STATUS             RESTARTS   AGE
# crash-app-xyz           0/1     CrashLoopBackOff   5          2m
# oom-app-abc             0/1     OOMKilled           1          1m
# pending-app-def         0/1     Pending             0          6m
```

**Get Pod Details as JSON (for Python parsing):**
```bash
kubectl get pods -n production -o json
# This outputs machine-readable JSON — your Python code will parse this
# Key fields to look for:
# .items[].status.phase --> 'Running', 'Pending', 'Failed'
# .items[].status.containerStatuses[0].state.waiting.reason --> 'CrashLoopBackOff'
# .items[].status.containerStatuses[0].restartCount --> number
# .items[].status.containerStatuses[0].lastState.terminated.reason --> 'OOMKilled'
```

**Describe a Specific Pod (Deep Info):**
```bash
kubectl describe pod crash-app-xyz -n production
# Look for these sections in output:
# Events:  --> shows why it crashed
# Limits:  --> shows memory/CPU limits
# State:   --> current state details
```

**Get Logs from a Crashed Pod:**
```bash
# Current logs (if pod is running):
kubectl logs crash-app-xyz -n production --tail=50

# Previous logs (from BEFORE the last crash):
kubectl logs crash-app-xyz -n production --previous --tail=50

# Note: --previous is KEY for CrashLoopBackOff — current logs are empty!
```

**Get Events (Cluster-wide Problems):**
```bash
kubectl get events -n production --sort-by=.metadata.creationTimestamp
# Shows recent events sorted by time
# Look for: OOMKilling, BackOff, FailedScheduling
```

---

### Section B — Remediation Commands (Fix Things)

**Restart a Pod (Delete it — K8s creates a new one):**
```bash
kubectl delete pod crash-app-xyz -n production
# K8s automatically creates a replacement pod
# Expected: 'pod crash-app-xyz deleted'
# Then verify with: kubectl get pods -n production
```

**Patch Memory Limits (for OOMKilled):**
```bash
# This patches the Deployment (not just the pod)
# It increases memory limit to 256Mi (was probably 128Mi)
kubectl patch deployment oom-app -n production --type=json \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "256Mi"}]'

# Expected: 'deployment.apps/oom-app patched'

# Simpler alternative using strategic merge patch:
kubectl patch deployment oom-app -n production \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"oom-container","resources":{"limits":{"memory":"256Mi"}}}]}}}}'
```

**Describe Pod to Understand Pending:**
```bash
kubectl describe pod pending-app-def -n production
# In the Events section, look for:
# 'FailedScheduling: 0/1 nodes are available: 1 Insufficient memory.'
# 'FailedScheduling: 0/1 nodes are available: 1 Insufficient cpu.'
# These tell you WHY the pod is pending
```

---

### Section C — Verification Commands (Did It Work?)

```bash
# Check if pod is now Running:
kubectl get pod <pod-name> -n production

# Check restart count dropped to 0:
kubectl get pod <pod-name> -n production -o jsonpath='{.status.containerStatuses[0].restartCount}'

# Check pod status field:
kubectl get pod <pod-name> -n production -o jsonpath='{.status.phase}'

# Watch pod in real-time (Ctrl+C to stop):
kubectl get pods -n production -w
```

---

### Section D — Setup Commands (One-Time)

```bash
# Create production namespace:
kubectl create namespace production

# Apply RBAC (run after creating the YAML from DOC 5):
kubectl apply -f rbac/k8s-rbac.yaml

# Apply a scenario (run from DOC 8):
kubectl apply -f scenarios/crashloop.yaml -n production
kubectl apply -f scenarios/oomkill.yaml -n production
kubectl apply -f scenarios/pending.yaml -n production
```

---

### Quick Reference Table — What to Run for Each Anomaly

| Anomaly | Detect Command | Diagnose Command | Fix Command |
|---|---|---|---|
| CrashLoopBackOff | `kubectl get pods -n production -o json` | `kubectl logs <pod> --previous --tail=50` | `kubectl delete pod <pod> -n production` |
| OOMKilled | `kubectl get pods -n production -o json` | `kubectl describe pod <pod> -n production` | `kubectl patch deployment <dep> -n production` (see above) |
| Pending | `kubectl get pods -n production -o json` | `kubectl describe pod <pod> -n production` (check Events) | Cannot auto-fix — explain to human |

---

## DOC 4 — MCP Tool Layer — Python Code That Runs kubectl

> MCP = Model Context Protocol. It's a way to expose tools (functions) so the LangGraph agent can call them. You build the functions. Person 2 calls them from the graph.

### What You Are Building

A Python file with functions. Each function runs one kubectl command and returns structured data. The agent calls these functions like tools. Think of it as: you build the remote control buttons; Person 2 decides when to press them.

---

### Codex Prompt for This File

```
CODEX PROMPT: Create a Python file called tools/kubectl_tools.py. It must:
1. Import subprocess, json, logging
2. Have a function run_kubectl(args_list) that runs a subprocess command and returns (stdout, stderr, returncode)
3. Have get_all_pods(namespace='production') that calls kubectl get pods -n <namespace> -o json and returns parsed JSON
4. Have get_pod_logs(pod_name, namespace='production', previous=False, tail=50) that returns log string
5. Have describe_pod(pod_name, namespace='production') that returns describe output as string
6. Have delete_pod(pod_name, namespace='production') that deletes the pod and returns success bool
7. Have patch_memory(deployment_name, new_memory='256Mi', namespace='production') that patches memory limit
8. Have get_events(namespace='production') that returns events as string
9. ALL functions must use a serviceaccount context if available, log all calls, and handle errors gracefully
```

---

### Complete Code — tools/kubectl_tools.py

```python
# tools/kubectl_tools.py
# Person 1 builds this. Person 2 imports and calls these functions.

import subprocess
import json
import logging
import shlex

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('kubectl_tools')

def run_kubectl(args_list):
    """
    Core function: runs any kubectl command.
    args_list: list of strings e.g. ['get', 'pods', '-n', 'production']
    Returns: (stdout_str, stderr_str, return_code)
    """
    cmd = ['kubectl'] + args_list
    logger.info(f'Running: {" ".join(cmd)}')
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30  # fail if takes more than 30 seconds
    )
    if result.returncode != 0:
        logger.error(f'kubectl error: {result.stderr}')
    return result.stdout, result.stderr, result.returncode

def get_all_pods(namespace='production'):
    """Returns list of pod dicts. Key fields: name, status, restartCount, reason."""
    stdout, stderr, rc = run_kubectl(['get', 'pods', '-n', namespace, '-o', 'json'])
    if rc != 0:
        return {'error': stderr, 'pods': []}
    data = json.loads(stdout)
    pods = []
    for item in data.get('items', []):
        name = item['metadata']['name']
        phase = item['status'].get('phase', 'Unknown')
        restart_count = 0
        reason = ''
        container_statuses = item['status'].get('containerStatuses', [])
        if container_statuses:
            cs = container_statuses[0]
            restart_count = cs.get('restartCount', 0)
            waiting = cs.get('state', {}).get('waiting', {})
            terminated = cs.get('lastState', {}).get('terminated', {})
            reason = waiting.get('reason', terminated.get('reason', ''))
        pods.append({
            'name': name,
            'phase': phase,
            'restart_count': restart_count,
            'reason': reason,
            'namespace': namespace
        })
    return {'pods': pods}

def get_pod_logs(pod_name, namespace='production', previous=False, tail=50):
    """Returns last N lines of pod logs as string."""
    args = ['logs', pod_name, '-n', namespace, f'--tail={tail}']
    if previous:
        args.append('--previous')
    stdout, stderr, rc = run_kubectl(args)
    if rc != 0:
        return f'ERROR getting logs: {stderr}'
    return stdout

def describe_pod(pod_name, namespace='production'):
    """Returns kubectl describe output as string."""
    stdout, stderr, rc = run_kubectl(['describe', 'pod', pod_name, '-n', namespace])
    if rc != 0:
        return f'ERROR: {stderr}'
    return stdout

def delete_pod(pod_name, namespace='production'):
    """Deletes pod (K8s will restart it). Returns True if successful."""
    stdout, stderr, rc = run_kubectl(['delete', 'pod', pod_name, '-n', namespace])
    if rc == 0:
        logger.info(f'Pod {pod_name} deleted successfully')
        return True
    logger.error(f'Failed to delete pod {pod_name}: {stderr}')
    return False

def patch_memory(deployment_name, new_memory='256Mi', namespace='production', container_index=0):
    """Patches deployment memory limit. Returns True if successful."""
    patch_json = json.dumps([{
        "op": "replace",
        "path": f"/spec/template/spec/containers/{container_index}/resources/limits/memory",
        "value": new_memory
    }])
    stdout, stderr, rc = run_kubectl([
        'patch', 'deployment', deployment_name,
        '-n', namespace,
        '--type=json',
        f'-p={patch_json}'
    ])
    return rc == 0

def get_events(namespace='production'):
    """Returns events sorted by time as string."""
    stdout, stderr, rc = run_kubectl([
        'get', 'events', '-n', namespace,
        '--sort-by=.metadata.creationTimestamp'
    ])
    if rc != 0:
        return f'ERROR: {stderr}'
    return stdout

def get_pod_status(pod_name, namespace='production'):
    """Returns just the status string for a single pod."""
    stdout, stderr, rc = run_kubectl([
        'get', 'pod', pod_name, '-n', namespace,
        '-o', 'jsonpath={.status.phase}'
    ])
    return stdout.strip() if rc == 0 else 'Unknown'
```

---

### How to Test This File Manually

```powershell
# First deploy a scenario (from DOC 8), then test:
cd C:\k8swhisperer
python -c "from tools.kubectl_tools import get_all_pods; import json; print(json.dumps(get_all_pods(), indent=2))"
# Expected: JSON with list of pods

# Test logs:
python -c "from tools.kubectl_tools import get_pod_logs; print(get_pod_logs('crash-app-xyz'))"
```

---

### The Verify Loop Function (Critical for Competition)

After fixing a pod, you must verify it's actually fixed. The judge will check this. Add this to `tools/kubectl_tools.py`:

```python
import time

def verify_pod_running(pod_name, namespace='production', max_wait_seconds=120, poll_interval=10):
    """
    Polls pod status until Running or timeout.
    Returns: ('success', final_status) or ('timeout', last_status)
    """
    logger.info(f'Waiting for pod {pod_name} to reach Running state...')
    elapsed = 0
    while elapsed < max_wait_seconds:
        status = get_pod_status(pod_name, namespace)
        logger.info(f'  [{elapsed}s] Pod status: {status}')
        if status == 'Running':
            return ('success', status)
        if status in ['Failed', 'Unknown']:
            return ('failed', status)
        time.sleep(poll_interval)
        elapsed += poll_interval
    return ('timeout', get_pod_status(pod_name, namespace))
```

> ⚠️ **WARNING:** After deleting a pod, a NEW pod starts with a DIFFERENT name. The old name is gone. You must watch `kubectl get pods` and get the new pod's name before calling `verify_pod_running`.

---

### How to Get the New Pod Name After Restart

```python
def get_new_pod_name(deployment_name, namespace='production', timeout=30):
    """After deleting a pod, get the name of the new replacement pod."""
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = get_all_pods(namespace)
        for pod in result.get('pods', []):
            if deployment_name in pod['name'] and pod['phase'] not in ['Terminating']:
                return pod['name']
        time.sleep(3)
    return None
```

---

## DOC 5 — RBAC Security — Keep the Agent Safe

> **JUDGES WILL CHECK THIS.** If your agent has cluster-admin permissions, you lose points. This doc shows you how to create a limited ServiceAccount that can only do what the agent needs.

### What is RBAC? (Simple Explanation)

RBAC is a permission system. Without it, your agent could accidentally delete your entire cluster. With it, the agent can ONLY do specific things like list pods and delete individual pods — nothing else. Think of it like: cluster-admin is a master key. Our ServiceAccount is a key that only opens certain rooms.

### The Three Things to Create

- **ServiceAccount** — an identity for your agent (like a user account)
- **Role** — what actions are allowed (list/delete pods only)
- **RoleBinding** — connects the ServiceAccount to the Role

---

### Step 1 — Create the YAML File

Create file: `C:\k8swhisperer\rbac\k8s-rbac.yaml`

Copy this EXACTLY:

```yaml
# rbac/k8s-rbac.yaml
# DO NOT change this unless you know what you are doing
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
  # Can READ pods, events, deployments
  - apiGroups: [""]
    resources: ["pods", "pods/log", "events"]
    verbs: ["get", "list", "watch"]
  # Can DELETE pods (restart = delete + K8s recreates)
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["delete"]
  # Can READ deployments
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch"]
  # Can PATCH deployments (for OOMKilled memory fix)
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["patch"]
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

---

### Step 2 — Apply the RBAC

```powershell
# First make sure production namespace exists:
kubectl create namespace production

# Apply the RBAC:
kubectl apply -f C:\k8swhisperer\rbac\k8s-rbac.yaml

# Expected output:
# serviceaccount/k8s-whisperer-agent created
# role.rbac.authorization.k8s.io/k8s-whisperer-role created
# rolebinding.rbac.authorization.k8s.io/k8s-whisperer-binding created
```

---

### Step 3 — Verify It Worked

```powershell
kubectl get serviceaccount k8s-whisperer-agent -n production
kubectl get role k8s-whisperer-role -n production
kubectl get rolebinding k8s-whisperer-binding -n production
# All three should say NAME + AGE — not 'not found'
```

---

### Step 4 — CRITICAL: Verify NO Cluster Admin

Judges will run this check. Make sure it returns 'no':

```powershell
kubectl auth can-i delete namespace --as=system:serviceaccount:production:k8s-whisperer-agent
# MUST output: no

kubectl auth can-i delete pods -n production --as=system:serviceaccount:production:k8s-whisperer-agent
# MUST output: yes

kubectl auth can-i get pods -n production --as=system:serviceaccount:production:k8s-whisperer-agent
# MUST output: yes
```

> ✅ **PASSING STATE:** delete namespace = 'no', delete pods in production = 'yes', get pods in production = 'yes'. Show this output to judges.

---

## DOC 6 — Execution Engine — Auto-Fix Pods with Verify Loop

> This is the most important code you write. It takes an anomaly type and executes the fix — then verifies it worked. This is what judges watch during the demo.

### Codex Prompt for This File

```
CODEX PROMPT: Create tools/execution_engine.py. It must:
1. Import from tools.kubectl_tools
2. Have execute_crashloop_fix(pod_name, namespace='production') that:
   deletes the pod, waits for new pod to start, verifies it's Running,
   returns dict with success, new_pod_name, status, message
3. Have execute_oom_fix(deployment_name, namespace='production') that:
   patches memory to 256Mi, waits for rollout, returns similar dict
4. Have explain_pending(pod_name, namespace='production') that:
   describes the pod, extracts the FailedScheduling reason, returns the reason string
5. ALL functions must log each step and include a verify loop with polling
```

---

### Complete Code — tools/execution_engine.py

```python
# tools/execution_engine.py

import time
import logging
from tools.kubectl_tools import (
    delete_pod, patch_memory, describe_pod,
    get_all_pods, get_pod_status, get_pod_logs
)

logger = logging.getLogger('execution_engine')

def execute_crashloop_fix(pod_name, namespace='production'):
    """
    Auto-fix for CrashLoopBackOff.
    Strategy: delete pod -> K8s creates new one -> verify Running.
    """
    logger.info(f'[EXECUTE] Starting CrashLoop fix for pod: {pod_name}')
    result = {
        'action': 'restart_pod',
        'target_pod': pod_name,
        'namespace': namespace,
        'success': False,
        'new_pod_name': None,
        'final_status': None,
        'message': ''
    }

    # Step 1: Delete the crashed pod
    logger.info(f'[EXECUTE] Step 1: Deleting pod {pod_name}')
    deleted = delete_pod(pod_name, namespace)
    if not deleted:
        result['message'] = f'Failed to delete pod {pod_name}'
        return result

    # Step 2: Wait a moment then find the new pod
    logger.info('[EXECUTE] Step 2: Waiting 5s for new pod to start...')
    time.sleep(5)

    # Step 3: Find the new pod (same deployment, different name suffix)
    # Extract deployment name (pod names are: deploymentname-randomhash-hash)
    deployment_prefix = '-'.join(pod_name.split('-')[:-2])
    logger.info(f'[EXECUTE] Step 3: Looking for new pod with prefix: {deployment_prefix}')

    new_pod = None
    for attempt in range(10):  # try for ~50 seconds
        pods_data = get_all_pods(namespace)
        for pod in pods_data.get('pods', []):
            if pod['name'] != pod_name and deployment_prefix in pod['name']:
                new_pod = pod['name']
                break
        if new_pod:
            break
        time.sleep(5)

    if not new_pod:
        result['message'] = 'New pod did not start within 50 seconds'
        return result

    result['new_pod_name'] = new_pod
    logger.info(f'[EXECUTE] Found new pod: {new_pod}')

    # Step 4: Poll until Running or timeout
    logger.info('[EXECUTE] Step 4: Polling for Running status (up to 120s)...')
    for elapsed in range(0, 120, 10):
        status = get_pod_status(new_pod, namespace)
        logger.info(f'[EXECUTE] [{elapsed}s] Status: {status}')
        if status == 'Running':
            result['success'] = True
            result['final_status'] = 'Running'
            result['message'] = f'Pod fixed. New pod {new_pod} is Running.'
            logger.info('[EXECUTE] SUCCESS: Pod is Running!')
            return result
        if status == 'CrashLoopBackOff':
            result['message'] = f'Pod is still crashing. May need deeper fix.'
            result['final_status'] = status
            return result
        time.sleep(10)

    result['message'] = 'Timeout: pod did not reach Running in 120 seconds'
    result['final_status'] = get_pod_status(new_pod, namespace)
    return result


def execute_oom_fix(deployment_name, namespace='production', new_memory='256Mi'):
    """
    Fix for OOMKilled: patch deployment memory limit upward.
    NOTE: This is HITL in competition — only call if human approved.
    """
    logger.info(f'[EXECUTE] Starting OOM fix for deployment: {deployment_name}')
    result = {
        'action': 'patch_memory',
        'target_deployment': deployment_name,
        'new_memory': new_memory,
        'namespace': namespace,
        'success': False,
        'message': ''
    }

    # Step 1: Patch the deployment
    patched = patch_memory(deployment_name, new_memory, namespace)
    if not patched:
        result['message'] = 'Patch command failed'
        return result

    logger.info(f'[EXECUTE] Patched memory to {new_memory}. Waiting for rollout...')
    time.sleep(15)  # wait for rollout to start

    # Step 2: Find the new pod after rollout
    new_pod = None
    for attempt in range(12):
        pods_data = get_all_pods(namespace)
        for pod in pods_data.get('pods', []):
            if deployment_name in pod['name']:
                new_pod = pod['name']
                break
        if new_pod:
            break
        time.sleep(10)

    if not new_pod:
        result['message'] = 'Could not find pod after patch'
        return result

    # Step 3: Verify running
    for elapsed in range(0, 120, 10):
        status = get_pod_status(new_pod, namespace)
        logger.info(f'[EXECUTE] OOM pod status [{elapsed}s]: {status}')
        if status == 'Running':
            result['success'] = True
            result['message'] = f'Memory patched to {new_memory}. Pod {new_pod} Running.'
            return result
        time.sleep(10)

    result['message'] = 'Timeout waiting for pod after memory patch'
    return result


def explain_pending(pod_name, namespace='production'):
    """
    For Pending pods: explain WHY it is pending.
    Extracts the FailedScheduling reason.
    """
    desc = describe_pod(pod_name, namespace)
    lines = desc.split('\n')
    reason_lines = []
    in_events = False
    for line in lines:
        if 'Events:' in line:
            in_events = True
        if in_events and ('FailedScheduling' in line or 'Insufficient' in line or 'Unschedulable' in line):
            reason_lines.append(line.strip())
    if reason_lines:
        return ' | '.join(reason_lines)
    return 'Pod is Pending. Reason unknown — check describe output manually.'
```

---

### How to Test the Execution Engine

```powershell
# First deploy the crash scenario (from DOC 8):
kubectl apply -f C:\k8swhisperer\scenarios\crashloop.yaml -n production

# Wait 1 minute for it to enter CrashLoopBackOff, then test:
python -c "
from tools.execution_engine import execute_crashloop_fix
import json

# Get the pod name first:
import subprocess
result = subprocess.run(['kubectl','get','pods','-n','production','--no-headers','-o','custom-columns=NAME:.metadata.name'],
    capture_output=True, text=True)
pod_name = result.stdout.strip().split('\n')[0]
print(f'Testing fix on: {pod_name}')

fix_result = execute_crashloop_fix(pod_name)
print(json.dumps(fix_result, indent=2))
"
```

---

## DOC 7 — Failure Handling & Edge Cases

> The competition has 'Hidden Traps' that will break naive implementations. This doc covers each one and how to handle it.

---

### Trap 1 — Pod Restarts During Rolling Update (False Positive)

**Problem:** A pod restarts because of a deployment update (normal). Your agent should NOT treat this as a CrashLoop.

```python
# Add to kubectl_tools.py:
def is_rollout_in_progress(deployment_name, namespace='production'):
    stdout, _, rc = run_kubectl([
        'rollout', 'status', 'deployment', deployment_name,
        '-n', namespace, '--timeout=1s'
    ])
    return 'successfully rolled out' not in stdout

# In your anomaly detection:
# If restartCount > 3 AND NOT is_rollout_in_progress(deployment) --> real crashloop
# If restartCount > 3 AND is_rollout_in_progress(deployment) --> ignore, normal update
```

---

### Trap 2 — The New Pod Has a Different Name After Restart

When you delete a pod, K8s creates a new one with a different random suffix. Example: `crash-app-xyz-abc123` becomes `crash-app-xyz-def456`. Your verify loop MUST find the new pod by deployment prefix, not old pod name.

This is already handled in the execution engine code above. The `deployment_prefix` variable extracts just the first two parts of the name.

---

### Trap 3 — Container-Level vs Pod-Level Status

`pod.status.phase` might say 'Running' while the container inside is still starting. A properly running pod needs both `phase=Running` AND `containerStatuses[0].ready=True`.

```python
# Better verify function:
def is_pod_truly_ready(pod_name, namespace='production'):
    stdout, _, rc = run_kubectl([
        'get', 'pod', pod_name, '-n', namespace,
        '-o', 'jsonpath={.status.phase}/{.status.containerStatuses[0].ready}'
    ])
    return stdout.strip() == 'Running/true'
```

---

### Trap 4 — get logs returns empty for CrashLoopBackOff

When a pod is in CrashLoopBackOff, the current logs may be empty because the container is not running. You MUST use the `--previous` flag to get logs from the LAST run.

```python
# Always try previous logs first for CrashLoopBackOff:
def get_crash_logs(pod_name, namespace='production'):
    # Try previous first
    logs = get_pod_logs(pod_name, namespace, previous=True, tail=50)
    if 'ERROR getting logs' not in logs and len(logs) > 10:
        return logs
    # Fall back to current logs
    return get_pod_logs(pod_name, namespace, previous=False, tail=50)
```

---

### Trap 5 — Subprocess Timeout

kubectl commands can hang. Always set `timeout=30` in `subprocess.run`. If it hangs, the tool returns an error, not a hang.

---

### Trap 6 — Production Namespace Does Not Exist

If someone resets minikube and you run tests, the namespace might be missing.

```python
# Add to kubectl_tools.py:
def ensure_namespace(namespace='production'):
    stdout, stderr, rc = run_kubectl(['get', 'namespace', namespace])
    if rc != 0:  # namespace doesn't exist
        run_kubectl(['create', 'namespace', namespace])
        logger.info(f'Created namespace: {namespace}')

# Call at start of every test
```

---

### Trap 7 — OOMKilled Container Name May Not Match

The `patch_memory` function uses `container_index=0`. If the deployment has multiple containers, this patches the first one. For the demo, all our scenarios use single-container deployments, so this is fine.

---

### Trap 8 — Minikube Out of Resources

If you run too many scenarios, minikube runs out of CPU/memory.

```powershell
# Clean up between tests:
kubectl delete all --all -n production

# If minikube feels slow:
minikube stop
minikube start --memory=4096 --cpus=2
```

---

## DOC 8 — Demo Scenario Setup — Deploy Broken Pods for Testing

> These YAML files create intentionally broken pods in your cluster for demo. Copy each one into a file, apply it with kubectl apply, and watch the anomaly appear.

---

### Scenario 1 — CrashLoopBackOff

This deploys a pod that exits immediately with code 1. Kubernetes keeps restarting it. After about 1 minute, it enters CrashLoopBackOff.

Create file: `C:\k8swhisperer\scenarios\crashloop.yaml`

```yaml
# scenarios/crashloop.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crash-app
  namespace: production
  labels:
    app: crash-app
    scenario: crashloop
spec:
  replicas: 1
  selector:
    matchLabels:
      app: crash-app
  template:
    metadata:
      labels:
        app: crash-app
    spec:
      containers:
        - name: crash-container
          image: busybox:latest
          command: ["/bin/sh", "-c"]
          args:
            - |
              echo 'App starting...'
              echo 'ERROR: Database connection refused at db:5432'
              echo 'FATAL: Cannot start without database'
              exit 1   # This causes the crash
          resources:
            limits:
              memory: "64Mi"
              cpu: "100m"
```

```powershell
kubectl apply -f C:\k8swhisperer\scenarios\crashloop.yaml
kubectl get pods -n production -w  # Watch it (Ctrl+C to stop)

# Expected progression:
# crash-app-xxx   0/1   ContainerCreating   0   5s
# crash-app-xxx   0/1   Error               0   8s
# crash-app-xxx   0/1   CrashLoopBackOff    1   20s
# crash-app-xxx   0/1   CrashLoopBackOff    3   90s
```

---

### Scenario 2 — OOMKilled

This deploys a pod with a tiny memory limit. The app tries to allocate memory, exceeds the limit, and gets killed with OOMKilled.

Create file: `C:\k8swhisperer\scenarios\oomkill.yaml`

```yaml
# scenarios/oomkill.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oom-app
  namespace: production
  labels:
    app: oom-app
    scenario: oomkill
spec:
  replicas: 1
  selector:
    matchLabels:
      app: oom-app
  template:
    metadata:
      labels:
        app: oom-app
    spec:
      containers:
        - name: oom-container
          image: python:3.9-slim
          command: ["/bin/sh", "-c"]
          args:
            - |
              python3 -c "
              print('Allocating memory...')
              data = []
              for i in range(100000):
                  data.append('x' * 10000)   # Fills memory fast
              print('Done')"
          resources:
            limits:
              memory: "20Mi"   # Very small — will be OOMKilled
              cpu: "100m"
            requests:
              memory: "10Mi"
```

```powershell
kubectl apply -f C:\k8swhisperer\scenarios\oomkill.yaml

# Check after 30 seconds:
kubectl describe pod -n production -l app=oom-app
# Look for: Last State: Terminated   Reason: OOMKilled
```

---

### Scenario 3 — Pending Pod

This deploys a pod that requests more memory than the node has. It will stay Pending forever.

Create file: `C:\k8swhisperer\scenarios\pending.yaml`

```yaml
# scenarios/pending.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pending-app
  namespace: production
  labels:
    app: pending-app
    scenario: pending
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pending-app
  template:
    metadata:
      labels:
        app: pending-app
    spec:
      containers:
        - name: pending-container
          image: nginx:latest
          resources:
            requests:
              memory: "100Gi"   # More than any node has = always Pending
              cpu: "100m"
            limits:
              memory: "100Gi"
```

```powershell
kubectl apply -f C:\k8swhisperer\scenarios\pending.yaml

# Check immediately:
kubectl get pods -n production
# pending-app-xxx   0/1   Pending   0   10s

kubectl describe pod -n production -l app=pending-app
# Events section will show:
# FailedScheduling: 0/1 nodes are available: 1 Insufficient memory.
```

---

### Scenario Management Commands

```powershell
# Deploy ALL scenarios at once:
kubectl apply -f C:\k8swhisperer\scenarios\ -n production

# Delete ALL scenarios (clean slate):
kubectl delete deployment crash-app oom-app pending-app -n production

# Quick status check all scenarios:
kubectl get pods -n production -o wide

# Reset everything and start fresh:
kubectl delete all --all -n production
kubectl apply -f C:\k8swhisperer\rbac\k8s-rbac.yaml
```

---

## DOC 9 — Testing & Validation Checklist

> Run through this checklist before the demo. Every item must pass. If one fails, the section next to it tells you which DOC to look at.

---

### Phase 1 — Environment Check (DOC 1)

| Test | Command | Pass if |
|---|---|---|
| Docker running | `docker ps` | No error message |
| Minikube started | `minikube status` | Shows 'Running' for host, kubelet, apiserver |
| kubectl connected | `kubectl get nodes` | Shows 'minikube Ready' |
| Python working | `python --version` | Shows Python 3.x |
| Packages installed | `python -c "import kubernetes; print('ok')"` | Prints 'ok' |

---

### Phase 2 — Kubernetes Check (DOC 2, 5)

| Test | Command | Pass if |
|---|---|---|
| Production namespace | `kubectl get ns production` | Shows production namespace |
| RBAC applied | `kubectl get sa k8s-whisperer-agent -n production` | Shows service account |
| No cluster-admin | `kubectl auth can-i delete namespace --as=system:serviceaccount:production:k8s-whisperer-agent` | Outputs 'no' |
| Can delete pods | `kubectl auth can-i delete pods -n production --as=system:serviceaccount:production:k8s-whisperer-agent` | Outputs 'yes' |

---

### Phase 3 — MCP Tools Check (DOC 4)

| Test | Command/Code | Pass if |
|---|---|---|
| get_all_pods works | `python -c "from tools.kubectl_tools import get_all_pods; print(get_all_pods())"` | Returns dict with 'pods' key |
| delete_pod works | Deploy crashloop, then `python -c "from tools.kubectl_tools import delete_pod; print(delete_pod('pod-name'))"` | Returns True |
| get logs works | `python -c "from tools.kubectl_tools import get_pod_logs; print(get_pod_logs('pod-name'))"` | Returns string (not ERROR) |
| patch_memory works | `python -c "from tools.kubectl_tools import patch_memory; print(patch_memory('oom-app'))"` | Returns True |

---

### Phase 4 — Scenario Check (DOC 8)

| Scenario | Deploy Command | Pass if (after 90s) |
|---|---|---|
| CrashLoopBackOff | `kubectl apply -f scenarios/crashloop.yaml` | `kubectl get pods` shows CrashLoopBackOff with restarts > 3 |
| OOMKilled | `kubectl apply -f scenarios/oomkill.yaml` | `kubectl describe` shows OOMKilled in lastState |
| Pending | `kubectl apply -f scenarios/pending.yaml` | `kubectl get pods` shows Pending status |

---

### Phase 5 — Execution Engine Check (DOC 6)

| Test | Expected Result |
|---|---|
| execute_crashloop_fix on CrashLoopBackOff pod | Returns dict with success=True, new_pod_name filled, final_status='Running' |
| explain_pending on Pending pod | Returns string mentioning 'Insufficient memory' or similar reason |
| execute_oom_fix on oom-app deployment | Returns dict with success=True (after patching memory) |

---

### Phase 6 — Verify Loop Check

This is critical for the competition. Manually verify:

- After fixing CrashLoop: pod eventually shows Running (may take 60s)
- Execution engine did NOT just return immediately — it polled
- Log output shows timestamps like '[30s] Status: ContainerCreating' then '[60s] Status: Running'

---

## DOC 10 — Debugging Playbook — Fix Everything That Goes Wrong

---

### Problem: minikube start fails

| Error Message | Fix |
|---|---|
| 'Exiting due to PROVIDER_DOCKER_NOT_RUNNING' | Open Docker Desktop app, wait for green icon in system tray (1 min), then retry |
| 'Unable to pick a default driver' | Run: `minikube start --driver=docker` |
| 'Error: Cannot connect to the Docker daemon' | Restart Docker Desktop. If still fails: restart computer |
| Stuck at 'Verifying Kubernetes components...' | Wait 5 minutes. If no progress: `minikube delete && minikube start --driver=docker` |

---

### Problem: kubectl commands fail

| Error | Fix |
|---|---|
| 'The connection to the server was refused' | minikube is not running. Run: `minikube start --driver=docker` |
| 'Error from server (NotFound): pods not found' | Wrong namespace. Add `-n production` to your command |
| 'kubectl' is not recognized | Close PowerShell, open new one. Or: `choco install kubernetes-cli -y` in Admin PowerShell |
| 'unable to retrieve pod logs: container is not running' | Pod already crashed. Use `--previous` flag: `kubectl logs pod-name --previous` |

---

### Problem: Python subprocess errors

| Error | Fix |
|---|---|
| ModuleNotFoundError: No module named 'tools' | Run Python from the `C:\k8swhisperer` directory. `cd C:\k8swhisperer` first |
| subprocess.TimeoutExpired | kubectl command hung. Check minikube is running. Retry. |
| json.JSONDecodeError | kubectl returned an error instead of JSON. Check stderr in the run_kubectl return value |
| '[Errno 2] No such file or directory: kubectl' | kubectl not in PATH. Run kubectl from full path or reinstall: `choco install kubernetes-cli -y` |

---

### Problem: RBAC permission denied

| Error | Fix |
|---|---|
| 'Error from server (Forbidden): pods is forbidden' | RBAC not applied. Run: `kubectl apply -f rbac/k8s-rbac.yaml` |
| 'cannot get resource pods in API group' | Your code is not using the serviceaccount. Check run_kubectl uses correct context |
| RBAC applied but still denied | Check: `kubectl describe role k8s-whisperer-role -n production` to see allowed verbs |

---

### Problem: Scenarios not showing correct errors

| Issue | Fix |
|---|---|
| CrashLoop pod shows ContainerCreating for >5 min | Image pull taking long. Check internet. Run: `kubectl describe pod <name> -n production`, look at Events |
| OOM pod shows Running (not killed) | Memory limit too high. Edit oomkill.yaml and set memory limit to '20Mi' not higher |
| Pending pod shows ContainerCreating | Minikube has enough memory after all. Increase memory request in YAML to '100Gi' |

---

### Nuclear Option — Full Reset

If nothing works and you have time, this resets everything:

```powershell
minikube delete
minikube start --driver=docker --memory=4096 --cpus=2
kubectl create namespace production
kubectl apply -f C:\k8swhisperer\rbac\k8s-rbac.yaml
# Then re-deploy your scenarios
```

---

## SECTION A — Master Execution Checklist — Phase 1 to 7

> This is your to-do list for the 24 hours. Each task is atomic (one action). Check them off as you complete them. If stuck, jump to the matching DOC.

---

### PHASE 1 — Before Hackathon Starts (Pre-work)

**Target: These must be done BEFORE hour 0.** Do them today.

1. Install Chocolatey (DOC 1, Step 1) — opens PowerShell as Admin, one command
2. Install Docker Desktop (DOC 1, Step 2) — download, run installer, restart PC
3. Install minikube + kubectl (DOC 1, Step 3) — choco install command
4. Install Python 3.11 (DOC 1, Step 4) — choco install command
5. Run: `minikube start --driver=docker --memory=4096 --cpus=2` — verify it shows 'Done!'
6. Run: `kubectl get nodes` — verify shows 'Ready'
7. Create project folder structure (DOC 1, Step 7)
8. Install pip packages: `pip install kubernetes pyyaml`

---

### PHASE 2 — Hours 0–2: Environment & Namespace (DOC 1, 2, 5)

9. `minikube start` — confirm still working
10. `kubectl create namespace production`
11. Create `rbac/k8s-rbac.yaml` (DOC 5 — copy the YAML exactly)
12. `kubectl apply -f rbac/k8s-rbac.yaml`
13. Run RBAC verification commands from DOC 5 — confirm no cluster-admin
14. Run all Phase 1 checks from DOC 9 Testing Checklist

---

### PHASE 3 — Hours 2–5: MCP Tools (DOC 4)

15. Create `C:\k8swhisperer\tools\__init__.py` (empty file — makes it a Python package)
16. Create `tools/kubectl_tools.py` (DOC 4 — copy full code)
17. Test: `python -c "from tools.kubectl_tools import get_all_pods; print(get_all_pods())"`
18. If test fails: read error, check DOC 10 debugging section
19. Add `verify_pod_running` function (DOC 4, Verify Loop section)
20. Add `get_new_pod_name` function (DOC 4, last section)
21. Run Phase 3 checks from DOC 9 Testing Checklist

---

### PHASE 4 — Hours 5–9: Scenarios + Execution Engine (DOC 6, 8)

22. Create `scenarios/crashloop.yaml` (DOC 8 — copy YAML)
23. Create `scenarios/oomkill.yaml` (DOC 8 — copy YAML)
24. Create `scenarios/pending.yaml` (DOC 8 — copy YAML)
25. `kubectl apply -f scenarios/crashloop.yaml` — wait 90s, verify CrashLoopBackOff
26. Create `tools/execution_engine.py` (DOC 6 — copy full code)
27. Test `execute_crashloop_fix` manually — verify returns `success=True`
28. Test `explain_pending` manually
29. Test `execute_oom_fix` manually (first apply oomkill scenario)

---

### PHASE 5 — Hours 9–13: Integration with Person 2 (Handoff)

30. Share `tools/kubectl_tools.py` and `tools/execution_engine.py` with Person 2
31. Show Person 2 how to call each function
32. Make sure the dict formats match what Person 2 expects
33. The ClusterState schema needs: events list, anomalies list — confirm format with Person 2
34. Test that your tools run correctly when called from Person 2's LangGraph code

---

### PHASE 6 — Hours 13–20: Demo Rehearsal

35. Clean slate: `kubectl delete all --all -n production`
36. Re-apply RBAC: `kubectl apply -f rbac/k8s-rbac.yaml`
37. Run full demo flow 3 times: deploy crash scenario → agent detects → agent fixes → verify
38. Time the full cycle (should be < 3 minutes for CrashLoop fix)
39. Fix any issues found during rehearsal
40. Run all DOC 9 checks again

---

### PHASE 7 — Hours 20–24: Freeze & Stress Test

41. **NO NEW FEATURES after hour 20. Only bug fixes.**
42. Run all 3 scenarios 3x each — no failures allowed
43. Have full reset procedure memorized (DOC 10, Nuclear Option)
44. Know how to restart minikube if it crashes during demo
45. RBAC check output saved/ready to show judges

---

## SECTION B — Validation System — Quick Pass/Fail Checks

Run these in order. If any fails, go to the DOC number shown.

---

### Minikube Validation

| Check | Command | Pass? | If Fail |
|---|---|---|---|
| Minikube running | `minikube status` | Host: Running, kubelet: Running | DOC 1 Step 5 |
| K8s API reachable | `kubectl cluster-info` | Shows cluster URLs | `minikube start --driver=docker` |
| Node ready | `kubectl get nodes` | STATUS = Ready | `minikube delete && minikube start` |
| System pods running | `kubectl get pods -n kube-system` | Most show Running | Wait 2 more minutes |

---

### kubectl Validation

| Check | Command | Pass? | If Fail |
|---|---|---|---|
| kubectl installed | `kubectl version --client` | Shows Client Version | `choco install kubernetes-cli -y` |
| Namespace exists | `kubectl get ns production` | Shows production | `kubectl create namespace production` |
| Can list pods | `kubectl get pods -n production` | No error (empty list ok) | Check namespace exists |
| Can get events | `kubectl get events -n production` | No error | Same as above |

---

### MCP Tools Validation

| Check | Command | Pass? | If Fail |
|---|---|---|---|
| Import works | `python -c "import tools.kubectl_tools"` | No error | Run from `C:\k8swhisperer`, add `__init__.py` |
| get_all_pods returns list | `python -c "from tools.kubectl_tools import get_all_pods; r=get_all_pods(); print(type(r['pods']))"` | Prints `<class 'list'>` | DOC 4 |
| delete_pod works | Deploy scenario, then test | Returns True | DOC 4, DOC 10 |
| logs work | Deploy crashloop, test get_pod_logs | Returns non-empty string | Use `previous=True` |

---

### Execution Engine Validation

| Check | What to Test | Pass? | If Fail |
|---|---|---|---|
| CrashLoop fix | Deploy crashloop, wait 90s, run execute_crashloop_fix | success=True, final_status=Running | DOC 6, check pod prefix logic |
| OOM fix | Deploy oomkill, run execute_oom_fix | success=True | DOC 6 |
| Pending explain | Deploy pending, run explain_pending | Returns reason string | DOC 6, check describe output format |
| Verify loop logs | Check Python output during fix | Shows [0s], [10s], [20s] status updates | DOC 4 verify loop code |

---

### RBAC Validation (Show This to Judges)

```powershell
echo '=== RBAC SAFETY CHECK ==='

kubectl auth can-i delete namespace --as=system:serviceaccount:production:k8s-whisperer-agent
# MUST print: no

kubectl auth can-i delete pods -n production --as=system:serviceaccount:production:k8s-whisperer-agent
# MUST print: yes

kubectl auth can-i get pods -n production --as=system:serviceaccount:production:k8s-whisperer-agent
# MUST print: yes

kubectl auth can-i patch deployments -n production --as=system:serviceaccount:production:k8s-whisperer-agent
# MUST print: yes
```

---

## SECTION C — Debug Prompts — Copy Into Codex/Antigravity When Stuck

> When something breaks and you don't know why, copy the prompt below into Codex/Antigravity. It will diagnose and fix it.

---

### Prompt 1 — kubectl Not Working

```
CODEX DEBUG PROMPT: My kubectl command is not working. I am on Windows.
The error is: [PASTE ERROR HERE].
I have minikube installed and Docker Desktop running.
Please tell me step by step what to check and how to fix this.
Start with the most common causes.
Give me exact commands to run in PowerShell.
```

---

### Prompt 2 — Python Subprocess Failing

```
CODEX DEBUG PROMPT: My Python subprocess command to run kubectl is failing.
Here is my code: [PASTE CODE].
Here is the error I get: [PASTE ERROR].
I am on Windows.
The kubectl command works when I run it directly in PowerShell.
Fix my Python code so subprocess.run can find and run kubectl correctly on Windows.
```

---

### Prompt 3 — Minikube Issues

```
CODEX DEBUG PROMPT: My minikube cluster has an issue.
Here is the error/symptom: [DESCRIBE PROBLEM].
I am on Windows with Docker Desktop as the driver.
Give me a step-by-step troubleshooting guide.
If minikube needs to be reset, tell me exactly how to do it without losing my YAML files.
```

---

### Prompt 4 — RBAC Permission Error

```
CODEX DEBUG PROMPT: I am getting a Kubernetes RBAC permission error.
The error is: [PASTE ERROR].
My RBAC YAML is: [PASTE YAML].
I need the agent to have permission to [describe what you need].
Show me exactly what to add to my Role's rules section.
I must NOT give cluster-admin permissions.
```

---

### Prompt 5 — Verify Loop Not Working

```
CODEX DEBUG PROMPT: My pod verify loop is not working. After deleting a pod, I cannot find the new pod's name.
The deployment name is [NAME]. Pod names follow the pattern: deploymentname-replicaset-hash.
Write a Python function that: waits 5 seconds after deletion, then polls kubectl get pods in the
production namespace every 5 seconds for up to 60 seconds, looking for a new pod whose name starts
with the deployment name prefix. Return the new pod name when found.
```

---

### Prompt 6 — Scenario YAML Not Triggering Anomaly

```
CODEX DEBUG PROMPT: My Kubernetes scenario YAML is not creating the anomaly I expect.
I deployed this YAML: [PASTE YAML].
I expected the pod to show [CrashLoopBackOff / OOMKilled / Pending].
Instead it shows [WHAT YOU SEE].
kubectl describe output shows: [PASTE DESCRIBE OUTPUT].
Fix my YAML so it reliably triggers the correct anomaly.
```

---

## SECTION D — Speed Mode Plan — Minimum for Demo Success

> If you are behind schedule, do ONLY these things. This is the minimum viable implementation for the demo. Everything else is bonus.

---

### Minimum 1 — CrashLoopBackOff Auto-Fix (MUST HAVE)

**Time needed:** 2 hours from scratch

**Files needed:**
- `tools/kubectl_tools.py` (just `run_kubectl` + `delete_pod` + `get_pod_status`)
- `tools/execution_engine.py` (just `execute_crashloop_fix`)

**Scenario YAML:** `scenarios/crashloop.yaml`

- This scenario scores the most points (Autonomous Remediation = 30 marks)
- Judges WILL inject this anomaly live
- Your verify loop MUST poll — one-shot check is not enough

---

### Minimum 2 — OOMKilled (HITL Placeholder)

**Time needed:** 1 hour

For the demo, OOMKilled goes through HITL (human approval). So YOUR job is just to provide `execute_oom_fix`. Person 3 adds the Slack button. For speed mode, make `execute_oom_fix` work even without HITL — just run it directly when called.

- Scenario YAML: `scenarios/oomkill.yaml`
- Function: `execute_oom_fix` in `execution_engine.py`
- Verify it patches memory and pod comes back Running

---

### Minimum 3 — Pending Pod Explanation (No Auto-Fix Needed)

**Time needed:** 30 minutes

Pending pods are explained, not auto-fixed. Your `explain_pending` function just needs to return the FailedScheduling reason string. That string gets passed to the LLM for a nice explanation.

- Scenario YAML: `scenarios/pending.yaml`
- Function: `explain_pending` in `execution_engine.py`
- Returns: string like 'Insufficient memory: node has 3.9Gi but pod requests 100Gi'

---

### RBAC — Cannot Skip

Even in speed mode, RBAC must be done. It's a 15-minute task (copy the YAML, apply it). Judges inspect for this specifically. See DOC 5.

---

### Things You CAN Skip If Behind Schedule

- Prometheus integration — not required for passing
- Multi-namespace support — not required
- Handling more than 3 anomaly types — CrashLoop + OOM + Pending is enough
- Concurrency handling — not required for base score
- Web3/Blockchain bonus — skip entirely if behind schedule

---

## SECTION E — 24-Hour Time Plan — Exact Timeline

> This is your schedule. Stick to it. If you are > 30 minutes behind, skip optional tasks and do the minimum from SECTION D first.

| Hours | Task | Your Deliverable | Risk if Late |
|---|---|---|---|
| 00:00–02:00 | SETUP: minikube + kubectl + namespace + RBAC | minikube running, RBAC applied, verification passes | Everything else blocked |
| 02:00–05:00 | MCP TOOLS: kubectl_tools.py | All 8 functions working, test output confirmed | Execution engine blocked |
| 05:00–07:00 | SCENARIOS: 3 YAML files deployed and verified | CrashLoop, OOM, Pending all showing in kubectl | Demo scenarios unavailable |
| 07:00–09:00 | EXECUTION ENGINE: execution_engine.py | All 3 fix functions working end-to-end | Demo has no auto-fix |
| 09:00–10:00 | INTEGRATION: hand off to Person 2 | Person 2 can call your tools from LangGraph | Full agent cannot run |
| 10:00–13:00 | BUFFER + DEBUGGING: fix whatever is broken | All DOC 9 checks pass | Demo instability |
| 13:00–15:00 | JOINT TESTING: run full agent pipeline | Full cycle works: detect → fix → verify | Demo failure |
| 15:00–17:00 | DEMO REHEARSAL x3 | Full demo under 5 minutes, no manual kubectl | Rough demo presentation |
| 17:00–20:00 | STRESS TEST: run all 3 scenarios 3x each | Zero failures across all runs | Flaky demo |
| 20:00–22:00 | FREEZE + FINAL CHECKS | All validations pass, reset procedure ready | Late-breaking bugs |
| 22:00–24:00 | PRESENTATION PREP | Know demo script, RBAC check ready to show judges | Weak Q&A responses |

---

### Hourly Rules

- Every 2 hours: run `kubectl get pods -n production` to make sure cluster is healthy
- Every 4 hours: run the DOC 9 Phase 1 environment check
- At hour 20: **STOP adding features. Only fix bugs.**
- Know the Nuclear Option (DOC 10) in case minikube crashes

---

### Signs You Are on Track vs Behind

| Hour | On Track | Behind — Do This |
|---|---|---|
| Hour 2 | minikube running, RBAC applied | Skip optional RBAC verifications, just apply it |
| Hour 5 | kubectl_tools.py all functions tested | Skip patch_memory test, do it in hour 7 |
| Hour 9 | All 3 execution engine functions work | Skip OOM fix, focus on crashloop only (most points) |
| Hour 13 | Full pipeline running with Person 2 | Deliver kubectl_tools.py only, let Person 2 integrate |
| Hour 20 | 3 clean demo runs completed | Do 1 clean run. Document anything manual for judges. |

---

### Final Checklist — 1 Hour Before Demo

46. `minikube start` → `kubectl get nodes` shows Ready
47. `kubectl apply -f rbac/k8s-rbac.yaml` → confirmed applied
48. All 3 scenarios deployed and showing expected errors
49. RBAC check printed and ready: no cluster-admin, yes pod operations
50. Full demo cycle runs clean: deploy anomaly → agent detects → fixes → verify
51. Nuclear reset procedure memorized in case of crash

---

*K8sWhisperer — Person 1 Infrastructure Guide · 24-Hour Hackathon Edition · Complete Execution System*
