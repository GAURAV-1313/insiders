# C:\k8swhisperer\tools\INTERFACE.py
# 
# LIVING DOCUMENTATION FOR PERSON 2 (LANGGRAPH DEVELOPER)
# This file shows you exactly how to import and call the MCP tools I built.
# DO NOT RUN THIS FILE directly. It is just reference documentation.

"""
#################################################################
# OBSERVATION / MONITORING
#################################################################

from tools.observer import collect_cluster_state, detect_anomalies_locally

# 1. Get current snapshot of the cluster in the 'production' namespace
state = collect_cluster_state(namespace='production')
# RETURNS a dict:
# {
#   'events': [list of pod dicts],
#   'anomalies': [], 
#   'timestamp': '2025-01-01T12:00:00Z',
#   'namespace': 'production'
# }

# 2. Run local detection against the state snapshot
anomalies = detect_anomalies_locally(state)
# RETURNS a list of anomaly dicts:
# [
#   {
#     'pod_name': 'crash-app-xyz',
#     'anomaly_type': 'CrashLoopBackOff', 
#     'severity': 'HIGH',
#     'restart_count': 5,
#     'reason': 'CrashLoopBackOff'
#   }
# ]


#################################################################
# DIAGNOSIS (Gathering Context for LLM)
#################################################################

from tools.kubectl_tools import get_pod_logs, describe_pod

# 1. Get logs for a pod. For CrashLoop, previous=True is mandatory to see what crashed.
logs = get_pod_logs(pod_name='crash-app-xyz', previous=True, tail=50)
# RETURNS: raw text string of the last 50 lines of logs

# 2. Get full kubernetes describe output (helpful if pod won't even start)
desc = describe_pod(pod_name='pending-app-abc')
# RETURNS: raw text string of the describe output


#################################################################
# EXECUTION (Fixing the Problems)
#################################################################

from tools.execution_engine import execute_crashloop_fix, execute_oom_fix, explain_pending

# 1. Auto-fix a pod stuck in CrashLoopBackOff (Deletes it, waits for new one, verifies it runs)
result = execute_crashloop_fix(pod_name='crash-app-xyz')
# RETURNS a dict:
# {
#   'action': 'restart_pod',
#   'target_pod': 'crash-app-xyz',
#   'namespace': 'production',
#   'success': True,
#   'new_pod_name': 'crash-app-newhash',
#   'final_status': 'Running',
#   'message': 'Pod fixed. New pod crash-app-newhash is Running.'
# }

# 2. Auto-fix an OOMKilled issue (Patches the Deployment with more memory, verifies it runs)
result = execute_oom_fix(deployment_name='oom-app', new_memory='256Mi')
# RETURNS a dict:
# {
#   'action': 'patch_memory',
#   'target_deployment': 'oom-app',
#   'new_memory': '256Mi',
#   'namespace': 'production',
#   'success': True,
#   'message': 'Deployment patched. New pod oom-app-newhash is Running.'
# }

# 3. Diagnose a Pending pod (Extracts FailedScheduling events to pass to the LLM)
reason = explain_pending(pod_name='pending-app-abc')
# RETURNS a string summarizing the scheduling error:
# "FailedScheduling: 0/1 nodes are available: 1 Insufficient memory."
"""
