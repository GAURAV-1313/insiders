import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from k8swhisperer.adapters.openai_compatible_llm import OpenAICompatibleLLMAdapter


class ClassifyNormalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = OpenAICompatibleLLMAdapter(
            api_key="test",
            model="test",
            base_url="https://api.groq.com/openai/v1",
        )

    def test_crashloop_error_with_three_restarts_gets_auto_fix_confidence(self) -> None:
        events = [
            {
                "pod_name": "payment-api-123",
                "namespace": "production",
                "status": "Error",
                "restart_count": 3,
                "exit_code": 1,
            }
        ]
        item = {
            "type": "CrashLoopBackOff",
            "severity": "HIGH",
            "affected_resource": "payment-api-123",
            "namespace": "production",
            "confidence": 0.8,
        }

        anomaly = self.adapter._validate_anomaly(item, events)

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly["confidence"], 0.91)

    def test_oomkilled_exit_code_gets_high_confidence(self) -> None:
        events = [
            {
                "pod_name": "oom-app-123",
                "namespace": "production",
                "status": "OOMKilled",
                "restart_count": 2,
                "exit_code": 137,
            }
        ]
        item = {
            "type": "OOMKilled",
            "severity": "HIGH",
            "affected_resource": "oom-app-123",
            "namespace": "production",
            "confidence": 0.8,
        }

        anomaly = self.adapter._validate_anomaly(item, events)

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly["confidence"], 0.95)


if __name__ == "__main__":
    unittest.main()
