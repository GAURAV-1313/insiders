# K8sWhisperer — Person 1 Guide
## Infrastructure & Cluster Management
### 24-Hour Hackathon Edition · Windows · Repo on Person 2's MacBook

---

## READ THIS FIRST — YOUR ACTUAL ROLE

The main codebase and minikube run on **Person 2's MacBook**. You do not run the agent. You do not write Python code. The kubectl adapter is already implemented and validated by Person 2.

Your job has three parts:

1. **RBAC** — create and apply three YAML files that judges will inspect
2. **Scenario YAMLs** — create two YAML files for OOMKilled and Pending scenarios
3. **Demo support** — inject anomalies on command during the live demo

That is it. Everything else is done.

---

## What is already done — do not redo this

- CrashLoopBackOff scenario YAML — already exists and validated
- kubectl adapter — already implemented and tested against real cluster
- Graph and agent logic — fully built by Person 2

---

## Your machine setup — Windows

You need two things installed on your Windows laptop:

### 1. Install kubectl

Open PowerShell as Administrator (right-click PowerShell → Run as Administrator):

```powershell
# Install Chocolatey if not already installed
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

Then install kubectl:

```powershell
choco install kubernetes-cli -y
```

Close PowerShell and open a new one (normal, not Admin). Verify:

```powershell
kubectl version --client
```

Expected: prints a version number like `Client Version: v1.28.x`

If it says `kubectl not recognized` — close all PowerShell windows and open a new one. PATH needs to refresh.

### 2. Get the kubeconfig from Person 2

Person 2 runs this on their MacBook and sends you the output:

```bash
# Person 2 runs this on their Mac
cat ~/.kube/config
```

You create this file on your Windows machine:

```powershell
# Create the .kube folder if it doesn't exist
mkdir $HOME\.kube -ErrorAction SilentlyContinue

# Open Notepad to paste the config
notepad $HOME\.kube\config
```

Paste what Person 2 sent you, save and close.

Verify your kubectl talks to Person 2's cluster:

```powershell
kubectl get nodes
```

Expected:
```
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   Xm    v1.28.x
```

If it says `connection refused` — Person 2's minikube is not running. Tell them to run `minikube start --driver=docker --cpus=4 --memory=6144` on their Mac.

---

## DOC 1 — RBAC Setup

> **Time needed: 20 minutes**
> **Why this matters: Judges inspect RBAC directly. They run one command and expect no cluster-admin. This is worth marks.**

### What RBAC is in plain English

RBAC is a permission system. The agent runs as a ServiceAccount. That ServiceAccount has a Role that says exactly what the agent can and cannot do. Judges check that the agent cannot delete namespaces or touch cluster-wide resources — only pod-level operations in the `production` namespace.

### Create the three RBAC files

Create a folder on your machine to work from:

```powershell
mkdir C:\k8swhisperer\rbac
cd C:\k8swhisperer\rbac
```

Create each file using Notepad. Open PowerShell and run:

```powershell
notepad C:\k8swhisperer\rbac\serviceaccount.yaml
```

Paste this exactly and save:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: k8swhisperer-sa
  namespace: production
```

---

```powershell
notepad C:\k8swhisperer\rbac\role.yaml
```

Paste this exactly and save:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: k8swhisperer-role
  namespace: production
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list", "watch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "patch"]
- apiGroups: [""]
  resources: ["events"]
  verbs: ["get", "list", "watch"]
```

---

```powershell
notepad C:\k8swhisperer\rbac\rolebinding.yaml
```

Paste this exactly and save:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: k8swhisperer-binding
  namespace: production
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: k8swhisperer-role
subjects:
- kind: ServiceAccount
  name: k8swhisperer-sa
  namespace: production
```

### Apply all three files

```powershell
kubectl apply -f C:\k8swhisperer\rbac\serviceaccount.yaml
kubectl apply -f C:\k8swhisperer\rbac\role.yaml
kubectl apply -f C:\k8swhisperer\rbac\rolebinding.yaml
```

Expected output (one line per file):
```
serviceaccount/k8swhisperer-sa created
role.rbac.authorization.k8s.io/k8swhisperer-role created
rolebinding.rbac.authorization.k8s.io/k8swhisperer-binding created
```

### Verify — run all four and save the output

```powershell
# MUST print: no
kubectl auth can-i delete namespace `
  --as=system:serviceaccount:production:k8swhisperer-sa
```

```powershell
# MUST print: yes
kubectl auth can-i delete pods -n production `
  --as=system:serviceaccount:production:k8swhisperer-sa
```

```powershell
# MUST print: yes
kubectl auth can-i patch deployments -n production `
  --as=system:serviceaccount:production:k8swhisperer-sa
```

```powershell
# MUST print: empty — nothing returned
kubectl get clusterrolebindings | findstr k8swhisperer
```

Screenshot all four outputs. Judges will ask you to run these live.

### RBAC done when

- `delete namespace` → `no`
- `delete pods` → `yes`
- `patch deployments` → `yes`
- `clusterrolebindings grep` → empty

### Common RBAC errors

| Error | Fix |
|---|---|
| `namespace "production" not found` | Run `kubectl create namespace production` then re-apply |
| `connection refused` | Person 2's minikube not running — tell them to start it |
| `AlreadyExists error` | Use `kubectl apply` not `kubectl create` — apply is safe to run multiple times |
| `Error from server (Forbidden)` | Your kubeconfig is wrong — get a fresh one from Person 2 |

---

## DOC 2 — Scenario Setup

> **Time needed: 30 minutes**
> **Why this matters: Without scenarios there is nothing to demo. OOMKilled and Pending must produce correct status values that the agent can detect.**

### Why Deployments not standalone Pods

The agent's fix for CrashLoopBackOff and OOMKilled deletes the pod. If it's a standalone Pod with no Deployment behind it, Kubernetes does not recreate it — the pod just disappears. The verify loop fails. All scenarios must be Deployment-backed so the pod is automatically recreated after deletion.

### Scenario 1 — CrashLoopBackOff (already done)

This scenario already exists at `/Users/gaurav/Documents/insiders/scenarios/crashloop.yaml` on Person 2's Mac. It is already validated. You do not need to do anything for this one.

### Scenario 2 — OOMKilled

Create the file:

```powershell
mkdir C:\k8swhisperer\scenarios -ErrorAction SilentlyContinue
notepad C:\k8swhisperer\scenarios\oomkill.yaml
```

Paste this exactly and save:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: analytics-worker
  namespace: production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: analytics-worker
  template:
    metadata:
      labels:
        app: analytics-worker
    spec:
      containers:
      - name: analytics-worker
        image: python:3.11-alpine
        command:
        - python
        - -c
        - |
          import time
          x = []
          while True:
              x.append(' ' * 1024 * 1024)
              time.sleep(0.1)
        resources:
          limits:
            memory: "64Mi"
            cpu: "200m"
```

Apply it:

```powershell
kubectl apply -f C:\k8swhisperer\scenarios\oomkill.yaml
```

Wait 60 seconds then check:

```powershell
kubectl get pods -n production
```

You should see `analytics-worker-xxx-xxx` with status `OOMKilled` or `CrashLoopBackOff`. The container allocates about 10MB per second and gets killed when it hits the 64Mi limit.

**What success looks like:**
```
NAME                                READY   STATUS             RESTARTS   AGE
analytics-worker-6fd79bd4bd-xk9p2   0/1     OOMKilled          2          75s
```

Or after multiple kills:
```
NAME                                READY   STATUS             RESTARTS   AGE
analytics-worker-6fd79bd4bd-xk9p2   0/1     CrashLoopBackOff   4          2m
```

Both are correct. What matters is the exit code. Check it with:

```powershell
kubectl describe pod -n production -l app=analytics-worker
```

Look for this in the output:
```
Last State: Terminated
  Reason: OOMKilled
  Exit Code: 137
```

Exit code 137 means OOMKilled. This is what the agent needs to see.

**If pod stays Running and never gets killed:**
The memory limit might be too high for the image. Try lowering it to 32Mi:
```yaml
memory: "32Mi"
```
Delete the Deployment and re-apply:
```powershell
kubectl delete -f C:\k8swhisperer\scenarios\oomkill.yaml
kubectl apply -f C:\k8swhisperer\scenarios\oomkill.yaml
```

**Send the describe output to Person 2** so they can confirm the adapter reads exit_code 137 correctly.

### Scenario 3 — Pending Pod

Create the file:

```powershell
notepad C:\k8swhisperer\scenarios\pending.yaml
```

Paste this exactly and save:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: resource-hog
  namespace: production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: resource-hog
  template:
    metadata:
      labels:
        app: resource-hog
    spec:
      containers:
      - name: resource-hog
        image: nginx
        resources:
          requests:
            memory: "999Gi"
            cpu: "999"
```

Apply it:

```powershell
kubectl apply -f C:\k8swhisperer\scenarios\pending.yaml
```

Check immediately — no need to wait:

```powershell
kubectl get pods -n production
```

**What success looks like:**
```
NAME                         READY   STATUS    RESTARTS   AGE
resource-hog-xxx-xxx         0/1     Pending   0          5s
```

This requests 999Gi of memory which no node has. The pod stays Pending indefinitely. This is correct — do not try to fix it.

**If the pod shows Running instead of Pending:**
Your minikube node somehow has 999Gi available which is impossible. Try increasing the request:
```yaml
memory: "9999Gi"
```

**Send a screenshot of `kubectl get pods -n production` to Person 2** to confirm.

### Send scenario files to Person 2

After creating both files, send them to Person 2 via WhatsApp, email, or any file sharing. They need to copy them to `/Users/gaurav/Documents/insiders/scenarios/` on their Mac.

Or if you are physically next to Person 2 — just plug in a USB or use AirDrop.

### Cleanup between tests

When you need to remove a scenario:

```powershell
# remove one specific scenario
kubectl delete -f C:\k8swhisperer\scenarios\oomkill.yaml
kubectl delete -f C:\k8swhisperer\scenarios\pending.yaml

# remove everything from production namespace
kubectl delete all --all -n production

# verify nothing left
kubectl get pods -n production
# should show: No resources found in production namespace.
```

---

## DOC 3 — kubectl Command Reference

These are all the commands you will need. Nothing else.

### Check cluster health

```powershell
# is the cluster alive
kubectl get nodes

# what's running right now
kubectl get pods -n production

# watch pods change in real time (Ctrl+C to stop)
kubectl get pods -n production -w

# see all pods across all namespaces
kubectl get pods -A
```

### Inspect a specific pod

```powershell
# replace <pod-name> with the actual name from kubectl get pods
kubectl describe pod <pod-name> -n production

# get last 50 lines of logs
kubectl logs <pod-name> -n production --tail=50

# get logs from the previous crash
kubectl logs <pod-name> -n production --previous --tail=50
```

### Apply and delete scenarios

```powershell
# apply a scenario
kubectl apply -f C:\k8swhisperer\scenarios\crashloop.yaml
kubectl apply -f C:\k8swhisperer\scenarios\oomkill.yaml
kubectl apply -f C:\k8swhisperer\scenarios\pending.yaml

# delete a specific scenario
kubectl delete -f C:\k8swhisperer\scenarios\oomkill.yaml

# delete everything in production namespace
kubectl delete all --all -n production
```

### RBAC checks — for judges

```powershell
# run these live when judges ask
kubectl auth can-i delete namespace `
  --as=system:serviceaccount:production:k8swhisperer-sa
# must print: no

kubectl auth can-i delete pods -n production `
  --as=system:serviceaccount:production:k8swhisperer-sa
# must print: yes

kubectl get clusterrolebindings | findstr k8swhisperer
# must print: empty
```

---

## DOC 4 — Validation Checklist

Run all of these before telling Person 2 your work is done.

```
RBAC checks:
[ ] kubectl get sa k8swhisperer-sa -n production → shows the service account
[ ] kubectl auth can-i delete namespace → no
[ ] kubectl auth can-i delete pods -n production → yes
[ ] kubectl auth can-i patch deployments -n production → yes
[ ] kubectl get clusterrolebindings | findstr k8swhisperer → empty
[ ] screenshot saved for judges

OOMKilled scenario:
[ ] kubectl apply -f oomkill.yaml → created
[ ] kubectl get pods -n production after 60s → shows OOMKilled or CrashLoopBackOff
[ ] kubectl describe pod → shows Exit Code: 137
[ ] scenario file sent to Person 2
[ ] kubectl delete -f oomkill.yaml → cleaned up

Pending scenario:
[ ] kubectl apply -f pending.yaml → created
[ ] kubectl get pods -n production immediately → shows Pending
[ ] scenario file sent to Person 2
[ ] kubectl delete -f pending.yaml → cleaned up
```

---

## DOC 5 — Demo Day Role

This is your most important job. The live demo is where marks are made or lost.

### Your setup before judges arrive

Open four PowerShell windows. Label them with the title bar:

**Window 1 — Cluster Monitor (keep open always)**
```powershell
kubectl get pods -n production -w
```
Leave this running. It shows pods changing in real time. Point at this screen when the agent detects an anomaly.

**Window 2 — RBAC Proof (ready to show)**
```powershell
# have this ready to run on command
kubectl auth can-i delete namespace `
  --as=system:serviceaccount:production:k8swhisperer-sa
```

**Window 3 — Scenario Injection (you manage this)**
```powershell
# staged and ready — do not run until judge says go
kubectl apply -f C:\k8swhisperer\scenarios\crashloop.yaml
```

**Window 4 — Cleanup Between Scenarios**
```powershell
kubectl delete all --all -n production
```

### Demo sequence for each scenario

**CrashLoopBackOff demo:**
```powershell
# Window 3 — inject when judge says go
kubectl apply -f C:\k8swhisperer\scenarios\crashloop.yaml

# Watch Window 1 — pod appears, restarts climb
# Watch Person 2's screen — agent detects → diagnoses → plans → executes
# After demo — Window 4
kubectl delete -f C:\k8swhisperer\scenarios\crashloop.yaml
```

**OOMKilled demo:**
```powershell
# Window 3
kubectl apply -f C:\k8swhisperer\scenarios\oomkill.yaml

# Watch Window 1 — wait about 60 seconds for OOMKilled status
# Watch Person 2's screen — agent auto-patches memory limit
# After demo — Window 4
kubectl delete -f C:\k8swhisperer\scenarios\oomkill.yaml
```

**Pending demo:**
```powershell
# Window 3
kubectl apply -f C:\k8swhisperer\scenarios\pending.yaml

# Watch Window 1 — pod shows Pending immediately
# Watch Person 2's screen — agent runs explain-only path
# After demo — Window 4
kubectl delete -f C:\k8swhisperer\scenarios\pending.yaml
```

### HITL demo — what to expect

When the agent hits a risky action (blast_radius not low, or confidence below 0.8), it sends a Slack message with Approve and Reject buttons. Person 3 or Person 2 will be watching Slack. When the judge says to approve, click the button. The agent resumes automatically. Your job during HITL is to keep Window 1 visible so the judge can see the pod state while waiting.

### If something breaks

**minikube stopped responding:**
Tell Person 2 immediately. They restart it on their Mac:
```bash
minikube stop
minikube start --driver=docker --cpus=4 --memory=6144
```
Takes about 2 minutes. Get a fresh kubeconfig from them and replace your `$HOME\.kube\config`.

**kubectl get pods returns connection refused:**
Same issue — minikube stopped. Tell Person 2.

**Scenario pod not showing the right status:**
Wait longer. OOMKilled takes 60+ seconds. CrashLoopBackOff needs 4+ restarts before it shows that label. Pending shows immediately.

**RBAC check fails during demo:**
```powershell
kubectl apply -f C:\k8swhisperer\rbac\
```
Re-apply all three files. Then rerun the verification commands.

---

## DOC 6 — Debugging Reference

| Problem | What to check | Fix |
|---|---|---|
| `kubectl: command not found` | PATH not updated | Close all PowerShell, open new one |
| `connection refused` | minikube stopped | Tell Person 2 to restart minikube |
| `namespace not found` | production namespace missing | `kubectl create namespace production` |
| OOMKilled pod stays Running | Memory limit too high | Lower to 32Mi in oomkill.yaml, delete and re-apply |
| Pending pod becomes Running | Requested resources too low | Increase to 9999Gi, delete and re-apply |
| RBAC apply fails AlreadyExists | Using create instead of apply | Use `kubectl apply` not `kubectl create` |
| kubectl describe shows ImagePullBackOff | Image not found | Check image name in YAML — must be exact |
| kubeconfig issues after minikube restart | IP changed | Get fresh kubeconfig from Person 2 |

---

## SECTION A — Your Full Task List

Work top to bottom. Check each item before moving to the next.

```
Phase 1 — RBAC (do first, 20 minutes)
[ ] kubectl installed, version prints correctly
[ ] kubeconfig from Person 2 in place
[ ] kubectl get nodes → minikube Ready
[ ] Create rbac/serviceaccount.yaml
[ ] Create rbac/role.yaml
[ ] Create rbac/rolebinding.yaml
[ ] kubectl apply all three → created
[ ] Verify: delete namespace → no
[ ] Verify: delete pods → yes
[ ] Verify: patch deployments → yes
[ ] Verify: clusterrolebindings → empty
[ ] Screenshot saved for judges

Phase 2 — OOMKilled scenario (30 minutes)
[ ] Create scenarios/oomkill.yaml
[ ] kubectl apply → created
[ ] Wait 60s → confirm OOMKilled or exit_code 137
[ ] kubectl describe → shows Exit Code: 137
[ ] Send file to Person 2
[ ] kubectl delete → cleaned up

Phase 3 — Pending scenario (15 minutes)
[ ] Create scenarios/pending.yaml
[ ] kubectl apply → created
[ ] Immediately confirm Pending status
[ ] Send file to Person 2
[ ] kubectl delete → cleaned up

Phase 4 — Demo prep (30 minutes)
[ ] Practice 4-window setup
[ ] Practice each scenario injection
[ ] Know RBAC commands by memory
[ ] Practice cleanup between scenarios

Phase 5 — Pre-demo checklist (1 hour before)
[ ] kubectl get nodes → Ready
[ ] kubectl apply -f rbac/ → unchanged
[ ] All RBAC verifications pass
[ ] All scenario files ready to inject
[ ] 4 PowerShell windows open and labeled
[ ] RBAC screenshot ready to show
```

---

## SECTION B — What You Do NOT Own

Do not touch these. If something breaks here, tell Person 2.

- Any Python files in the repo
- `src/k8swhisperer/adapters/kubectl_cluster.py`
- `src/k8swhisperer/graph.py`
- `main.py`
- `bootstrap.py`

Your files are only: YAML files in `rbac/` and `scenarios/`. That's it.

---

## SECTION C — Speed Mode

If behind schedule, strict priority order:

1. **RBAC** — 20 minutes — cannot skip, judges check this specifically
2. **OOMKilled scenario YAML** — 15 minutes — needed for auto-fix demo
3. **Pending scenario YAML** — 10 minutes — needed for explain path demo
4. **Demo window setup** — 20 minutes — practice injection on command

Total minimum work: about 65 minutes. Everything else is optional.

---

## SECTION D — Important Notes on Windows Differences

When running multi-line kubectl commands, use backtick `` ` `` not backslash `\` for line continuation in PowerShell:

```powershell
# CORRECT on Windows PowerShell
kubectl auth can-i delete namespace `
  --as=system:serviceaccount:production:k8swhisperer-sa

# WRONG — backslash is for bash/mac
kubectl auth can-i delete namespace \
  --as=system:serviceaccount:production:k8swhisperer-sa
```

File paths use backslash on Windows:
```powershell
# CORRECT
kubectl apply -f C:\k8swhisperer\rbac\role.yaml

# WRONG
kubectl apply -f C:/k8swhisperer/rbac/role.yaml
```

PowerShell grep equivalent is `findstr`:
```powershell
# CORRECT on Windows
kubectl get clusterrolebindings | findstr k8swhisperer

# WRONG on Windows
kubectl get clusterrolebindings | grep k8swhisperer
```

---

*K8sWhisperer — Person 1 Infrastructure Guide · Windows Edition · 24-Hour Hackathon*
