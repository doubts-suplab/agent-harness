"""MemoryPort reference adapters (spec §7) — always scoped by tenant.

Two references: an in-memory store and a durable JSON-file store. Both isolate by ``(tenant_id,
user_id, key)`` so one tenant can never read another's memory. The harness core does not touch memory;
these are for agents/consumers that need scoped, governed storage behind the port.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


def _scope(tenant_id: str, user_id: str, key: str) -> str:
    if not tenant_id or not user_id:
        raise ValueError("memory access MUST be scoped by non-empty tenant_id and user_id (spec §7)")
    return "\x00".join((tenant_id, user_id, key))


class InMemoryMemory:
    """Process-local, tenant-scoped key/value memory."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._lock = threading.Lock()

    def read(self, tenant_id: str, user_id: str, key: str) -> Any | None:
        return self._store.get(_scope(tenant_id, user_id, key))

    def write(self, tenant_id: str, user_id: str, key: str, value: Any) -> None:
        with self._lock:
            self._store[_scope(tenant_id, user_id, key)] = value


class FileMemory:
    """Durable, tenant-scoped memory backed by a single JSON file (read fresh each call)."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def read(self, tenant_id: str, user_id: str, key: str) -> Any | None:
        return self._load().get(_scope(tenant_id, user_id, key))

    def write(self, tenant_id: str, user_id: str, key: str, value: Any) -> None:
        with self._lock:
            data = self._load()
            data[_scope(tenant_id, user_id, key)] = value
            tmp = self._path.with_suffix(self._path.suffix + ".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._path)  # atomic swap

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))
