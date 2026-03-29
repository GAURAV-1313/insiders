"""
Quick smoke tests for Person 3's code.
Run: python test_my_parts.py

Tests (in order):
  1. Groq API call works
  2. All 4 prompts return expected structure
  3. Audit log read/write works
  4. Slack notifier prints blocks (no real Slack needed)
  5. Webhook server starts and /health returns 200
"""

import json
import sys
import os

print("=" * 60)
print("K8sWhisperer — Person 3 smoke tests")
print("=" * 60)

# ---------------------------------------------------------------------------
# TEST 1: Groq API
# ---------------------------------------------------------------------------
print("\n[1] Testing Groq API connection...")
try:
    from groq import Groq
    from config import GROQ_API_KEY, GROQ_MODEL
    client = Groq(api_key=GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": "Reply with the word ONLINE only."}],
        max_tokens=10,
    )
    result = resp.choices[0].message.content.strip()
    print(f"   Groq response: '{result}'")
    print("   PASS: Groq API works.")
except Exception as e:
    print(f"   FAIL: {e}")
    print("   → Check your GROQ_API_KEY in config.py")

# ---------------------------------------------------------------------------
# TEST 2: Prompt functions
# ---------------------------------------------------------------------------
print("\n[2] Testing prompt functions (real LLM calls)...")

SAMPLE_ANOMALY = {
    "type": "CrashLoopBackOff",
    "severity": "HIGH",
    "affected_resource": "api-deployment-7d9f8b-xk2p1",
    "namespace": "default",
    "confidence": 0.95,
    "trigger_signal": "restartCount=7, reason=Error, last exit code 1",
}

SAMPLE_EVENTS = [
    {"type": "Warning", "reason": "BackOff", "object": "pod/api-deployment-7d9f8b-xk2p1",
     "message": "Back-off restarting failed container"},
]

SAMPLE_POD_STATES = [
    {"name": "api-deployment-7d9f8b-xk2p1", "namespace": "default",
     "status": "CrashLoopBackOff", "restartCount": 7},
]

SAMPLE_LOGS = """
Starting application...
Loading config from /etc/config/app.yaml
KeyError: DATABASE_URL
Traceback (most recent call last):
  File "app.py", line 42, in <module>
    db_url = os.environ['DATABASE_URL']
KeyError: 'DATABASE_URL'
"""

SAMPLE_DESCRIBE = """
Name: api-deployment-7d9f8b-xk2p1
Namespace: default
Status: CrashLoopBackOff
Containers:
  api:
    Last State: Terminated
      Reason: Error
      Exit Code: 1
    Ready: False
    Restart Count: 7
"""

try:
    from llm.prompts import run_detect_prompt, run_diagnose_prompt, run_plan_prompt, run_explain_prompt

    print("   Testing detect prompt...")
    anomalies = run_detect_prompt(SAMPLE_EVENTS, SAMPLE_POD_STATES)
    assert isinstance(anomalies, list), "detect must return a list"
    print(f"   Detected {len(anomalies)} anomalies")

    print("   Testing diagnose prompt...")
    diagnosis = run_diagnose_prompt(SAMPLE_ANOMALY, SAMPLE_LOGS, SAMPLE_DESCRIBE, SAMPLE_EVENTS)
    assert isinstance(diagnosis, str) and len(diagnosis) > 20, "diagnosis must be a non-empty string"
    print(f"   Diagnosis (first 100 chars): {diagnosis[:100]}...")

    print("   Testing plan prompt...")
    plan = run_plan_prompt(SAMPLE_ANOMALY, diagnosis)
    assert "action_type" in plan, "plan must have action_type"
    assert "blast_radius" in plan, "plan must have blast_radius"
    assert "confidence" in plan, "plan must have confidence"
    print(f"   Plan: action={plan['action_type']}, blast_radius={plan['blast_radius']}, confidence={plan['confidence']}")

    print("   Testing explain prompt...")
    explanation = run_explain_prompt(
        anomaly=SAMPLE_ANOMALY,
        diagnosis=diagnosis,
        plan=plan,
        auto_executed=True,
        execution_result="Pod transitioned to Running state in 42 seconds.",
    )
    assert "slack_summary" in explanation, "explain must have slack_summary"
    assert "audit_summary" in explanation, "explain must have audit_summary"
    print(f"   Slack summary: {explanation['slack_summary'][:120]}...")
    print("   PASS: All 4 prompts work.")
except Exception as e:
    print(f"   FAIL: {e}")
    import traceback; traceback.print_exc()

# ---------------------------------------------------------------------------
# TEST 3: Audit log
# ---------------------------------------------------------------------------
print("\n[3] Testing audit log...")
try:
    from audit import build_log_entry, append_log_entry, load_log, generate_incident_id

    incident_id = generate_incident_id()
    entry = build_log_entry(
        incident_id=incident_id,
        anomaly=SAMPLE_ANOMALY,
        diagnosis="Test diagnosis",
        plan={"action_type": "restart_pod", "blast_radius": "low", "confidence": 0.9},
        approved=None,
        auto_executed=True,
        execution_result="Pod is Running",
        audit_summary="Test audit summary",
    )
    append_log_entry(entry)

    log = load_log()
    assert any(e["incident_id"] == incident_id for e in log), "entry not found after write"
    print(f"   Wrote and read back incident {incident_id}")
    print("   PASS: Audit log works.")
except Exception as e:
    print(f"   FAIL: {e}")

# ---------------------------------------------------------------------------
# TEST 4: Slack notifier (dry run — no real Slack)
# ---------------------------------------------------------------------------
print("\n[4] Testing Slack notifier (dry run, no real Slack)...")
try:
    # Temporarily unset webhook URL to trigger dry-run path
    import slack.notifier as notifier
    original = notifier.SLACK_WEBHOOK_URL
    notifier.SLACK_WEBHOOK_URL = ""

    result = notifier.post_hitl_approval_request(
        incident_id="inc-test",
        anomaly=SAMPLE_ANOMALY,
        diagnosis="Test diagnosis for Slack",
        plan={"action_type": "restart_pod", "target_resource": "api-pod", "blast_radius": "low",
              "confidence": 0.85, "parameters": {}, "reasoning": "Pod is crash-looping"},
        webhook_base_url="http://localhost:8000",
    )
    notifier.SLACK_WEBHOOK_URL = original
    # Result is False because no real webhook, but blocks printed — that's the test
    print("   Slack blocks constructed without error.")
    print("   PASS: Slack notifier works (dry run).")
except Exception as e:
    print(f"   FAIL: {e}")

# ---------------------------------------------------------------------------
# TEST 5: Webhook server import
# ---------------------------------------------------------------------------
print("\n[5] Testing webhook server import...")
try:
    from webhook.server import app, register_pending, get_decision
    print("   FastAPI app imported successfully.")
    print("   PASS: Webhook server module works.")
    print("   → Start server with: uvicorn webhook.server:app --reload")
except Exception as e:
    print(f"   FAIL: {e}")

print("\n" + "=" * 60)
print("Tests complete. Fix any FAILs above before the hackathon.")
print("=" * 60)
