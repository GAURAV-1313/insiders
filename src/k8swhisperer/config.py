"""Runtime configuration defaults for the orchestration layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Tuple


DESTRUCTIVE_ACTIONS = frozenset(
    {
        "delete_namespace",
        "delete_deployment",
        "drain_node",
        "scale_workload",
        "rollout_restart",
        "rollout_undo",
        "cordon_node",
    }
)

ALLOWED_V1_ACTIONS = frozenset({"restart_pod", "patch_memory_limit", "explain_only"})


@dataclass(frozen=True)
class Settings:
    poll_interval_seconds: int = 30
    verify_backoff_seconds: Tuple[int, ...] = field(default_factory=lambda: (15, 30, 60, 90))
    min_auto_confidence: float = 0.8
    destructive_actions: frozenset[str] = DESTRUCTIVE_ACTIONS
    allowed_v1_actions: frozenset[str] = ALLOWED_V1_ACTIONS
    audit_log_path: str = "audit_log.json"

    def copy_with_backoff(self, values: Iterable[int]) -> "Settings":
        return Settings(
            poll_interval_seconds=self.poll_interval_seconds,
            verify_backoff_seconds=tuple(values),
            min_auto_confidence=self.min_auto_confidence,
            destructive_actions=self.destructive_actions,
            allowed_v1_actions=self.allowed_v1_actions,
            audit_log_path=self.audit_log_path,
        )

