# K8sWhisperer — Person 1 Guide (V2 Hardened)
## Infrastructure & Cluster Management
### 24-Hour Hackathon Edition · Windows · Repo on Person 2's MacBook

---

## READ THIS FIRST — YOUR ACTUAL ROLE

The main codebase and minikube run on **Person 2's MacBook**. You do not run the agent. You do not write Python code. The kubectl adapter is already implemented and validated by Person 2.

Your job has three parts:
1. **RBAC** — create and apply three YAML files that judges will inspect
2. **Scenario YAMLs** — create two YAML files for `OOMKilled` and `Pending` scenarios
3. **Demo support** — inject anomalies on command during the live demo

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

*(If it says `kubectl not recognized` — close all PowerShell windows and open a new one to refresh PATH).*

### 2. The Kubeconfig Connection (Critical Step)

> [!CAUTION]
> Copying a standard macOS `kubeconfig` to Windows will fail due to missing local certificate files. **Person 2 MUST flatten the config.**

**Person 2 runs this on their MacBook:**
```bash
# 1. Flatten the config to embed certificates directly
minikube config view --flatten > config.txt

# 2. Ensure Minikube is open to your local LAN network
# Person 2 can run this proxy in a separate terminal:
kubectl proxy --address='0.0.0.0' --port=8001 --accept-hosts='.*'
```

**What you do on Windows:**
1. Get `config.txt` from Person 2 and save it to `$HOME\.kube\config`.
   ```powershell
   mkdir $HOME\.kube -ErrorAction SilentlyContinue
   notepad $HOME\.kube\config
   ```
2. **Modify the server address**: In that file, change the `server: https://127.0.0.1:...` line to point to Person 2's Mac LAN IP and the port they used, or if using proxy: `server: http://<PERSON_2_MAC_IP>:8001`.

Verify your kubectl talks to Person 2's cluster:
```powershell
kubectl get nodes
```

---

## DOC 1 — RBAC Setup

### Create the three RBAC files
Stop using WhatsApp to transfer files. You must use the official GitHub repository so that file paths are identical on both machines.

Clone the repository, move into it, and switch to your branch:
```powershell
cd C:\
git clone https://github.com/GAURAV-1313/insiders
cd C:\insiders
git checkout -B Ash
md C:\insiders\rbac -ErrorAction SilentlyContinue
cd C:\insiders\rbac
```

Create `C:\insiders\rbac\serviceaccount.yaml`:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: k8swhisperer-sa
  namespace: production
```

Create `C:\insiders\rbac\role.yaml`:
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

Create `C:\insiders\rbac\rolebinding.yaml`:
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

**Apply them safely:**
```powershell
kubectl apply -f C:\insiders\rbac\serviceaccount.yaml
kubectl apply -f C:\insiders\rbac\role.yaml
kubectl apply -f C:\insiders\rbac\rolebinding.yaml
```

**Verify:**
```powershell
kubectl auth can-i delete namespace --as=system:serviceaccount:production:k8swhisperer-sa
# MUST Print: no

kubectl auth can-i patch deployments --as=system:serviceaccount:production:k8swhisperer-sa -n production
# MUST Print: yes
```

---

## DOC 2 — Scenario Setup (Hardened)

> [!WARNING]
> Do NOT use simple python scripts to trigger OOMKills. They are unreliable and may freeze the container instead of cleanly exiting with code 137.

### Scenario 2 — Deterministic OOMKilled

Create `C:\insiders\scenarios\oomkill.yaml`:
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
        image: polinux/stress
        args: ["--vm", "1", "--vm-bytes", "128M", "--vm-hang", "1"]
        resources:
          limits:
            memory: "64Mi"
            cpu: "200m"
```
*This uses a dedicated stress-testing image guaranteeing an immediate and clean `Exit Code: 137` every single time without delay.*

### Scenario 3 — Pending Pod

Create `C:\insiders\scenarios\pending.yaml`:
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

**File Transfer Protocol (Branch: Ash):**
Commit these files to the `Ash` branch and push them to GitHub. This ensures the agent uses proper relative file paths rather than hardcoded `/Users/gaurav/` paths, and keeps your changes isolated until integration.

```powershell
cd C:\insiders
git add rbac\ scenarios\
git commit -m "Added RBAC and Scenario files from Person 1"
git push -u origin Ash
```

Person 2 can then pull or checkout the `Ash` branch during the demo, or integrate it into their `main` branch before the presentation.

---

## DOC 3 — The Demo & Cleanup Routine

### Safe Cleanup (Crucial during live demo)
> [!CAUTION]
> Never use `kubectl delete all --all`. It is a dangerous command that may wipe out essential resources.

To reset the stage between scenarios, only delete workloads:
```powershell
# Safe cleanup command
kubectl delete deployment --all -n production
kubectl delete pod --all -n production
```

### The 4-Window Demo Setup

1. **Window 1 (Monitor):** `kubectl get pods -n production -w`
2. **Window 2 (RBAC Proof):** `kubectl auth can-i delete namespace --as=system:serviceaccount:production:k8swhisperer-sa`
3. **Window 3 (Injection):** Keep your `kubectl apply -f C:\insiders\scenarios\...` commands ready here.
4. **Window 4 (Cleanup):** Keep your safe cleanup command ready here.

### Human-In-The-Loop (HITL) Fallback
If Slack goes down or the webhook fails during the live demo:
- **Do not panic.**
- Instruct Person 2 to look at their backend terminal running the agent Python script. There should be a standard CLI fallback (e.g., waiting for terminal input `y/n` to proceed).

---

## SECTION A — Quick Cheat Sheet / Debugging

| Problem | Fix |
|---|---|
| Kubeconfig complains about missing files | Person 2 did not `flatten` the config. They must run `minikube config view --flatten` |
| Connection timeout | You are not on the same network OR Person 2's Mac firewall is blocking the connection. Have them use `kubectl proxy` |
| RBAC check fails | You accidentally deleted the namespace or standard RBAC. Re-apply the `rbac/` folder. |
| OOMKilled pod is slow | The new `polinux/stress` image guarantees instant kills. Do not modify its `args`. |
