"""Audit log persistence helpers."""

from __future__ import annotations

import json
import os
from typing import Iterable, List

from k8swhisperer.state import LogEntry


def load_audit_log(path: str) -> List[LogEntry]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return list(data)


def append_audit_entry(path: str, existing_entries: Iterable[LogEntry], entry: LogEntry) -> List[LogEntry]:
    entries = list(existing_entries)
    entries.append(entry)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(entries, handle, indent=2)
    return entries

