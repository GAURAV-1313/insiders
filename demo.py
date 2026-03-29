import time
from tools.observer import collect_cluster_state, detect_anomalies_locally
from tools.execution_engine import execute_crashloop_fix

print('Checking current anomalies...')
state = collect_cluster_state()
anoms = detect_anomalies_locally(state)
print(f'Detected {len(anoms)} anomalies.')

pod = None
for a in anoms:
    if a['anomaly_type'] == 'CrashLoopBackOff':
        pod = a['pod_name']
        break

if pod:
    print(f'Testing fix for CrashLoopBackOff pod: {pod}')
    result = execute_crashloop_fix(pod)
    print(result)
else:
    print('No CrashLoop pod found!')
