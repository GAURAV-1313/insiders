from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from k8swhisperer.adapters.openai_compatible_llm import OpenAICompatibleLLMAdapter


HARDCODED_EVENTS = [
    {
        "pod_name": "payment-api-747b59cf4f-kmh8j",
        "namespace": "production",
        "status": "CrashLoopBackOff",
        "restart_count": 6,
        "exit_code": 1,
    }
]


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    _load_dotenv()

    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("K8SWHISPERER_LLM_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")

    adapter = OpenAICompatibleLLMAdapter(
        api_key=api_key,
        model=os.environ.get("K8SWHISPERER_LLM_MODEL", "llama-3.3-70b-versatile"),
        base_url=os.environ.get("K8SWHISPERER_LLM_BASE_URL", "https://api.groq.com/openai/v1"),
    )

    for index in range(1, 4):
        result = adapter.classify(HARDCODED_EVENTS)
        print(f"run {index}: {result}")


if __name__ == "__main__":
    main()
