"""Standalone webhook server for HITL Slack callbacks."""
import os
import sys
sys.path.insert(0, "src")

os.environ.setdefault("K8SWHISPERER_USE_REAL_ADAPTERS", "true")
# Secrets must be set in .env or exported before running — never hardcode here
# Required: GROQ_API_KEY, K8SWHISPERER_SLACK_WEBHOOK_URL, K8SWHISPERER_PUBLIC_BASE_URL

from k8swhisperer.bootstrap import build_runtime_from_env
from k8swhisperer.app import build_graph
from k8swhisperer.webhook import create_webhook_app

runtime = build_runtime_from_env()
graph = build_graph(runtime)
app = create_webhook_app(graph)
