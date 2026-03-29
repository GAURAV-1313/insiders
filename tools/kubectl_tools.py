import subprocess
import json
import logging
import time

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
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30  # fail if takes more than 30 seconds
        )
        if result.returncode != 0:
            logger.error(f'kubectl error: {result.stderr}')
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        logger.error('kubectl command timed out')
        return '', 'TIMEOUT', 1

def get_all_pods(namespace='production'):
    """Returns list of pod dicts. Key fields: name, status, restartCount, reason."""
    stdout, stderr, rc = run_kubectl(['get', 'pods', '-n', namespace, '-o', 'json'])
    if rc != 0:
        return {'error': stderr, 'pods': []}
    
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return {'error': f'Failed to parse JSON: {stdout}', 'pods': []}

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

def get_new_pod_name(deployment_name, namespace='production', timeout=30):
    """After deleting a pod, get the name of the new replacement pod."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = get_all_pods(namespace)
        for pod in result.get('pods', []):
            if deployment_name in pod['name'] and pod['phase'] not in ['Terminating']:
                return pod['name']
        time.sleep(3)
    return None

if __name__ == '__main__':
    # Simple self-test
    stdout, stderr, rc = run_kubectl(['version', '--client'])
    print(f"run_kubectl test: return_code={rc}")
    pods = get_all_pods()
    print(f"get_all_pods test: found {len(pods.get('pods', []))} pods")
