"""Validated local memory backup and restore helpers."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

MAX_BACKUP_BYTES = 512 * 1024
MAX_ITEMS = 150


def export_memory(memory: list[dict[str, Any]], destination: Path) -> None:
    """Write a bounded, private JSON backup atomically."""
    safe = memory[-MAX_ITEMS:]
    payload = json.dumps(safe, ensure_ascii=False, indent=2)
    if len(payload.encode("utf-8")) > MAX_BACKUP_BYTES:
        raise ValueError("backup too large")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="backup-", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, destination)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def import_memory(source: Path) -> list[dict[str, Any]]:
    """Read a bounded JSON backup and reject malformed top-level data."""
    if source.stat().st_size > MAX_BACKUP_BYTES:
        raise ValueError("backup too large")
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
        raise ValueError("invalid backup format")
    return data[-MAX_ITEMS:]
