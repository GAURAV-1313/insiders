"""Runtime construction helpers for switching between fixtures and real adapters."""

from __future__ import annotations

import os
import time
from pathlib import Path

from k8swhisperer.adapters.fixtures import FixtureClusterAdapter, FixtureLLMAdapter, FixtureNotifierAdapter
from k8swhisperer.adapters.kubectl_cluster import KubectlClusterAdapter
from k8swhisperer.adapters.openai_compatible_llm import OpenAICompatibleLLMAdapter
from k8swhisperer.adapters.slack_notifier import SlackNotifierAdapter
from k8swhisperer.config import Settings
from k8swhisperer.runtime import Runtime
from k8swhisperer.state import Anomaly


def _to_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _log(message: str) -> None:
    print(message)


class _ClusterSchemaFixtureLLMAdapter(FixtureLLMAdapter):
    """Fixture LLM that understands the real cluster adapter pod shape."""

    def classify(self, events):
        resource = events[0]["pod_name"] if events else "unknown"
        return [
            Anomaly(
                type="CrashLoopBackOff",
                severity="HIGH",
                affected_resource=resource,
                confidence=0.91,
                namespace="production",
                evidence=["restart_count > 3", "status CrashLoopBackOff"],
            )
        ]


def _load_dotenv() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def build_runtime_from_env() -> Runtime:
    """Build either fixture or real adapters based on environment configuration."""

    _load_dotenv()
    use_fixtures = _to_bool(os.getenv("K8SWHISPERER_USE_FIXTURES"), default=True)
    use_real_adapters = _to_bool(os.getenv("K8SWHISPERER_USE_REAL_ADAPTERS"), default=False)
    poll_interval = int(os.getenv("K8SWHISPERER_POLL_INTERVAL_SECONDS", "30"))
    settings = Settings(poll_interval_seconds=poll_interval)

    if use_real_adapters:
        kubectl_bin = os.getenv("K8SWHISPERER_KUBECTL_BIN", "kubectl")
        return Runtime(
            cluster=KubectlClusterAdapter(kubectl_bin=kubectl_bin),
            llm=_ClusterSchemaFixtureLLMAdapter(),
            notifier=FixtureNotifierAdapter(),
            settings=settings,
            sleep=time.sleep,
            log=_log,
        )

    if use_fixtures:
        return Runtime(
            cluster=FixtureClusterAdapter(),
            llm=FixtureLLMAdapter(),
            notifier=FixtureNotifierAdapter(),
            settings=settings.copy_with_backoff((0, 0)),
            sleep=lambda _: None,
            log=_log,
        )

    kubectl_bin = os.getenv("K8SWHISPERER_KUBECTL_BIN", "kubectl")
    # Groq fallback: if K8SWHISPERER_LLM_* vars are not set, use GROQ_API_KEY
    llm_api_key = (
        os.getenv("K8SWHISPERER_LLM_API_KEY")
        or os.getenv("GROQ_API_KEY", "")
    )
    llm_model = (
        os.getenv("K8SWHISPERER_LLM_MODEL")
        or "llama-3.3-70b-versatile"
    )
    llm_base_url = (
        os.getenv("K8SWHISPERER_LLM_BASE_URL")
        or "https://api.groq.com/openai/v1"
    )
    slack_webhook_url = os.getenv("K8SWHISPERER_SLACK_WEBHOOK_URL", "")
    slack_channel = os.getenv("K8SWHISPERER_SLACK_CHANNEL")

    return Runtime(
        cluster=KubectlClusterAdapter(kubectl_bin=kubectl_bin),
        llm=OpenAICompatibleLLMAdapter(
            api_key=llm_api_key,
            model=llm_model,
            base_url=llm_base_url,
        ),
        notifier=SlackNotifierAdapter(
            webhook_url=slack_webhook_url,
            channel=slack_channel,
        ),
        settings=settings,
        sleep=time.sleep,
        log=_log,
    )
