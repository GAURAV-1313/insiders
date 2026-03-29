"""Development entrypoint for a single K8sWhisperer cycle."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from k8swhisperer.app import run_development_cycle


if __name__ == "__main__":
    run_development_cycle()
