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

    logger.info(f'[EXECUTE] Step 1: Deleting pod {pod_name}')
    deleted = delete_pod(pod_name, namespace)
    if not deleted:
        result['message'] = f'Failed to delete pod {pod_name}'
        return result

    logger.info('[EXECUTE] Step 2: Waiting 5s for new pod to start...')
    time.sleep(5)

    deployment_prefix = '-'.join(pod_name.split('-')[:-2])
    logger.info(f'[EXECUTE] Step 3: Looking for new pod with prefix: {deployment_prefix}')

    new_pod = None
    for attempt in range(10):
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

    for elapsed in range(0, 120, 10):
        status = get_pod_status(new_pod, namespace)
        logger.info(f'[{elapsed}s] Status: {status}')
        if status == 'Running':
            result['success'] = True
            result['final_status'] = 'Running'
            result['message'] = f'Pod fixed. New pod {new_pod} is Running.'
            return result
        elif status in ['CrashLoopBackOff', 'Failed']:
            result['final_status'] = status
            result['message'] = f'Fix failed. New pod {new_pod} entered {status}.'
            return result
        time.sleep(10)

    result['final_status'] = get_pod_status(new_pod, namespace)
    result['message'] = f'Timeout waiting for pod {new_pod} to be Running. Status: {result["final_status"]}'
    return result

def execute_oom_fix(deployment_name, namespace='production', new_memory='256Mi'):
    """
    Auto-fix for OOMKilled.
    Strategy: patch deployment memory limit -> wait for rollout -> verify Running.
    """
    logger.info(f'[EXECUTE] Starting OOM fix: patching {deployment_name} memory to {new_memory}')
    result = {
        'action': 'patch_memory',
        'target_deployment': deployment_name,
        'new_memory': new_memory,
        'namespace': namespace,
        'success': False,
        'message': ''
    }

    success = patch_memory(deployment_name, new_memory, namespace)
    if not success:
        result['message'] = f'Failed to patch deployment {deployment_name}'
        return result

    logger.info('[EXECUTE] Step 2: Waiting 15s for rollout to begin...')
    time.sleep(15)

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
        result['message'] = 'New pod did not start within 120 seconds'
        return result

    logger.info(f'[EXECUTE] Found new pod: {new_pod}')
    for elapsed in range(0, 120, 10):
        status = get_pod_status(new_pod, namespace)
        logger.info(f'[{elapsed}s] Status: {status}')
        if status == 'Running':
            result['success'] = True
            result['message'] = f'Deployment patched. New pod {new_pod} is Running.'
            return result
        time.sleep(10)

    result['message'] = f'Timeout waiting for pod {new_pod} to be Running'
    return result

def explain_pending(pod_name, namespace='production'):
    """
    Extracts reason for Pending state from pod describe events.
    """
    desc = describe_pod(pod_name, namespace)
    lines = desc.split('\n')
    
    in_events = False
    events_lines = []
    for line in lines:
        if line.startswith('Events:'):
            in_events = True
            continue
        if in_events:
            if line.strip() == '' and events_lines:
                # end of events or empty line
                pass
            events_lines.append(line)
            
    reasons = []
    keywords = ['FailedScheduling', 'Insufficient', 'Unschedulable', "didn't match"]
    for event in events_lines:
        if any(keyword in event for keyword in keywords):
            reasons.append(event.strip())
            
    if not reasons:
        return 'Pod is Pending. Run kubectl describe for details.'
        
    return ' | '.join(reasons)
