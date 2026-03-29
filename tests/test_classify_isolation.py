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


def main() -> None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")

    adapter = OpenAICompatibleLLMAdapter(
        api_key=api_key,
        model="llama-3.1-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
    )

    for index in range(1, 4):
        result = adapter.classify(HARDCODED_EVENTS)
        print(f"run {index}: {result}")


if __name__ == "__main__":
    main()
