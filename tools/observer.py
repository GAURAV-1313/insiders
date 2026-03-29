import time
import logging
from datetime import datetime, timezone
from tools.kubectl_tools import get_all_pods

logger = logging.getLogger('observer')

def collect_cluster_state(namespace='production'):
    """
    Returns a dict with events, anomalies, timestamp, and namespace.
    """
    state = {
        'events': [],
        'anomalies': [],
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'namespace': namespace
    }
    
    pods_data = get_all_pods(namespace)
    if 'pods' in pods_data:
        state['events'] = pods_data['pods']
    
    return state

def detect_anomalies_locally(cluster_state):
    """
    Loops through pods and returns a list of detected anomalies based on local rules.
    """
    anomalies = []
    
    for pod in cluster_state.get('events', []):
        reason = pod.get('reason', '')
        phase = pod.get('phase', '')
        restart_count = int(pod.get('restart_count', 0))
        pod_name = pod.get('name', 'unknown')
        
        # Detection rules
        if reason == 'CrashLoopBackOff' or restart_count > 3:
            anomalies.append({
                'pod_name': pod_name,
                'anomaly_type': 'CrashLoopBackOff',
                'severity': 'HIGH',
                'restart_count': restart_count,
                'reason': reason
            })
        elif reason == 'OOMKilled':
            anomalies.append({
                'pod_name': pod_name,
                'anomaly_type': 'OOMKilled',
                'severity': 'HIGH',
                'restart_count': restart_count,
                'reason': reason
            })
        elif phase == 'Pending':
            anomalies.append({
                'pod_name': pod_name,
                'anomaly_type': 'PendingPod',
                'severity': 'MEDIUM',
                'restart_count': restart_count,
                'reason': reason
            })
        elif reason == 'ImagePullBackOff':
            anomalies.append({
                'pod_name': pod_name,
                'anomaly_type': 'ImagePullBackOff',
                'severity': 'MEDIUM',
                'restart_count': restart_count,
                'reason': reason
            })
            
    return anomalies

def run_observation_loop(namespace='production', interval=30, max_cycles=None):
    """
    Infinite loop (or max_cycles) to monitor cluster state and log anomalies.
    """
    logger.info(f"Starting observation loop for namespace '{namespace}' (interval={interval}s)")
    cycles = 0
    
    while True:
        if max_cycles is not None and cycles >= max_cycles:
            logger.info("Reached max_cycles. Shutting down observer.")
            break
            
        logger.info(f"--- Cycle {cycles + 1} ---")
        state = collect_cluster_state(namespace)
        anomalies = detect_anomalies_locally(state)
        
        if not anomalies:
            logger.info("No anomalies detected.")
        else:
            for anomaly in anomalies:
                logger.warning(f"ANOMALY DETECTED: {anomaly['anomaly_type']} on {anomaly['pod_name']} "
                               f"(Severity: {anomaly['severity']}, Restarts: {anomaly['restart_count']})")
                
        cycles += 1
        if max_cycles is None or cycles < max_cycles:
            time.sleep(interval)
            
if __name__ == '__main__':
    # Test script for Observer
    state = collect_cluster_state()
    anoms = detect_anomalies_locally(state)
    print(f"Pods found: {len(state.get('events', []))}")
    import json
    print(f"Anomalies: {json.dumps(anoms, indent=2)}")
