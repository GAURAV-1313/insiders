import unittest
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from k8swhisperer.adapters.kubectl_cluster import KubectlClusterAdapter


class KubectlAdapterUnitTests(unittest.TestCase):
    def test_restart_pod_treats_not_found_as_safe_noop(self):
        adapter = KubectlClusterAdapter()

        adapter._run_completed = lambda args: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr='Error from server (NotFound): pods "payment-api-123" not found\n',
        )

        result = adapter.restart_pod("payment-api-123", "production")

        self.assertIn("already absent", result)


if __name__ == "__main__":
    unittest.main()
