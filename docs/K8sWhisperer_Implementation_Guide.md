# K8sWhisperer · Implementation Guide (V2 - LangGraph Edition)
## Person 1: Step-by-Step Build Prompts

**This document:** Tells you WHAT to build, in WHAT ORDER, and EXACTLY what to paste into Codex/Antigravity at each step.

**IMPORTANT ARCHITECTURE NOTE:** This guide has been updated. Person 2 has built a LangGraph orchestration backend in the `GAURAV-1313/insiders` repository. You do **not** need to build polling loops, execution engines, or observers. Your only Python job is to fulfill the `ClusterAdapter` interface!

---

## STEP 1 — Environment Setup & Repository Cloning
**Hours 0–2 · Before anything else, your machine must work**

### What you are doing
Installing minikube and cloning the official `insiders` repository to your C: drive. You must work on the `Ash` branch so Person 2 can pull your hardware-specific changes later.

### Exact Build Steps

| # | Action | Exact Command / Code | Expect / If Fail |
|---|---|---|---|
| 1 | Open PowerShell as Admin | Right-click PowerShell → Run as Administrator | Title bar says Administrator |
| 2 | Install minikube+kubectl | (Assuming chocolatey is installed) `choco install minikube kubernetes-cli -y` | Both show version numbers |
| 3 | Start minikube | `minikube start --driver=docker --memory=4096 --cpus=2` | 'Done! kubectl is now configured' |
| 4 | Verify cluster | `kubectl get nodes` | minikube Ready |
| 5 | Clone Repo | `cd C:\ && git clone https://github.com/GAURAV-1313/insiders.git C:\insiders` | Cloned successfully |
| 6 | Create your Branch | `cd C:\insiders && git checkout -b Ash` | Switched to a new branch 'Ash' |

### ✅ Step 1 Done When...
- `kubectl get nodes` shows: minikube Ready
- You are on the `Ash` branch inside `C:\insiders`

---

## STEP 2 — Namespace + RBAC Setup
**Hours 1–2 · Create the production namespace and lock down permissions**

### Exact Build Steps

| # | Action | Exact Command / Code | Expect / If Fail |
|---|---|---|---|
| 1 | Create namespace | `kubectl create namespace production` | 'namespace/production created' |
| 2 | Apply RBAC | `kubectl apply -f C:\insiders\tests\fixtures\rbac.yaml` (or generated RBAC) | Resources created |
| 3 | Verify no cluster-admin | `kubectl auth can-i delete namespace --as=system:serviceaccount:production:k8s-whisperer-agent` | Prints: no |
| 4 | Verify can delete pods | `kubectl auth can-i delete pods -n production --as=system:serviceaccount:production:k8s-whisperer-agent` | Prints: yes |

---

## STEP 3 — Implement the KubectlClusterAdapter
**Hours 2–4 · The Python functions that talk to Kubernetes**

### What you are doing
Person 2's LangGraph backend relies on a `ClusterAdapter` to talk to Kubernetes. You are going to implement `src/k8swhisperer/adapters/kubectl_cluster.py` in the `insiders` repo so it maps to the underlying `kubectl` CLI commands.

**FILE PATH:** `C:\insiders\src\k8swhisperer\adapters\kubectl_cluster.py`

*(Note: The `insiders` repository might already have a reference implementation. If so, your job is simply to review it, ensure it runs on Windows, and ensure the paths/commands match your local `minikube`.)*

### Build Prompts for `kubectl_cluster.py`

#### 1. `scan_cluster`
```text
🤖 CODEX / ANTIGRAVITY PROMPT — Implement scan_cluster

In C:\insiders\src\k8swhisperer\adapters\kubectl_cluster.py, implement `scan_cluster`.
It must:
- Run `self._run_json(["get", "pods", "-n", "production", "-o", "json"])`
- Extract items and normalize them using `self._normalize_pod`.
- Return a list of Dicts.
```

#### 2. `get_pod_logs`
```text
🤖 CODEX / ANTIGRAVITY PROMPT — Implement get_pod_logs

In C:\insiders\src\k8swhisperer\adapters\kubectl_cluster.py, implement `get_pod_logs`.
It must:
- Run `logs` with and without the `--previous` flag.
- Combine and summarize the output using `self._summarize_logs`.
```

#### 3. `patch_memory_limit`
```text
🤖 CODEX / ANTIGRAVITY PROMPT — Implement patch_memory_limit

In C:\insiders\src\k8swhisperer\adapters\kubectl_cluster.py, implement `patch_memory_limit`.
It must:
- Resolve the deployment owner of the pod.
- Run `kubectl set resources deployment/<name> -n <ns> --limits=memory=<new_limit>`
- Return the command output.
```

---

## STEP 4 — Deploy the 3 Demo Scenarios
**Hours 4–5 · Create broken pods for testing**

Ensure `C:\k8swhisperer\scenarios` or `C:\insiders\scenarios` contains the following manifests and apply them.

### Scenario 1 — CrashLoopBackOff

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crash-app
  namespace: production
  labels:
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
      - name: crash-app
        image: busybox:latest
        command: ["/bin/sh", "-c", "echo 'App starting...'; echo 'ERROR: Database connection refused'; exit 1"]
        resources:
          limits:
            memory: "64Mi"
```

### Scenario 2 — OOMKilled

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oom-app
  namespace: production
  labels:
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
      - name: oom-app
        image: polinux/stress
        args: ["--vm", "1", "--vm-bytes", "250M", "--vm-hang", "1"]
        resources:
          requests:
            memory: "50Mi"
          limits:
            memory: "100Mi"
```

### Scenario 3 — Pending Pod

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pending-app
  namespace: production
  labels:
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
      - name: pending-app
        image: nginx:latest
        resources:
          requests:
            memory: "100Gi"
```

**Deploy and verify:**
```powershell
kubectl apply -f crashloop.yaml
kubectl apply -f oomkill.yaml
kubectl apply -f pending.yaml

# Check pods
kubectl get pods -n production
```

---

## STEP 5 — Run Integration Tests
**Hours 5–6 · Verify the Adapter Works locally**

Since you are in the `insiders` repo, LangGraph relies heavily on standard unit tests.

### Exact Build Steps

| # | Action | Exact Command / Code | Expect / If Fail |
|---|---|---|---|
| 1 | Set PYTHONPATH | `$env:PYTHONPATH="C:\insiders\src"` | No output |
| 2 | Run Adapter Tests | `python -m unittest discover -s C:\insiders\tests -p "test_adapters.py" -v` | All tests pass (OK) |

---

## STEP 6 — Demo Day Checklist
**2 Hours Before Judges · Run in this exact order**

### Pre-Demo Sequence

| # | Action | Exact Command / Code | Expect / If Fail |
|---|---|---|---|
| 1 | Commits Pushed | `git add . && git commit -m "adapter ready" && git push origin Ash` | Pushed to Ash branch |
| 2 | Restart minikube fresh | `minikube stop && minikube start --driver=docker` | 'Done! kubectl is configured'|
| 3 | Apply RBAC | `kubectl apply -f rbac.yaml` | applied |
| 4 | Deploy Scenarios | Apply all three scenarios in production namespace | pods created |
| 5 | Network Port Forward | (If requested by Person 2) setup `kubectl proxy --address='0.0.0.0' --port=8080` | Proxy running |
| 6 | Ready | Wait for Person 2 on macOS to trigger the agent using your cluster! | Agent fixes pods magically |

---

## Quick Reference — Which Prompt to Use When

| Situation | Step | Codex Prompt Title |
|---|---|---|
| Something fails during install | Step 1 | Environment Setup Failure |
| Need RBAC YAML written | Step 2 | RBAC YAML Generation |
| Need to implement scan_cluster | Step 3 | Implement scan_cluster |
| Need to implement memory patch | Step 3 | Implement patch_memory_limit |
| minikube crashed in demo | Step 6 | Emergency: minikube crashed |
