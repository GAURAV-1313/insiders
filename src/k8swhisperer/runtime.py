"""Injected runtime dependencies for the orchestration layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from k8swhisperer.adapters.base import ClusterAdapter, LLMAdapter, NotifierAdapter
from k8swhisperer.config import Settings


@dataclass
class Runtime:
    cluster: ClusterAdapter
    llm: LLMAdapter
    notifier: NotifierAdapter
    settings: Settings
    sleep: Callable[[int], None]
    log: Callable[[str], None]

