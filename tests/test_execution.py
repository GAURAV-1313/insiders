import json
from tools.execution_engine import execute_crashloop_fix, execute_oom_fix, explain_pending
from tools.kubectl_tools import get_all_pods

def test_crashloop():
    print("Testing execute_crashloop_fix...")
    pods = get_all_pods('production').get('pods', [])
    target = None
    for p in pods:
        if p.get('reason') == 'CrashLoopBackOff':
            target = p['name']
            break
            
    if not target:
        print("No CrashLoop pod found — deploy scenario first")
        return
        
    result = execute_crashloop_fix(target)
    print("CrashLoop Fix Result:")
    print(json.dumps(result, indent=2))
    if result.get('success'):
        print("test_crashloop: PASS")
    else:
        print("test_crashloop: FAIL")

def test_pending():
    print("Testing explain_pending...")
    pods = get_all_pods('production').get('pods', [])
    target = None
    for p in pods:
        if p.get('phase') == 'Pending':
            target = p['name']
            break
            
    if not target:
        print("No Pending pod found — deploy scenario first")
        return
        
    result = explain_pending(target)
    print(f"Pending Reason: {result}")
    if result and "Insufficient" in result:
        print("test_pending: PASS")
    else:
        print("test_pending: FAIL")

if __name__ == '__main__':
    test_crashloop()
    print("-" * 40)
    test_pending()
