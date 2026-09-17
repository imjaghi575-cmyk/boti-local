"""Enhanced offline behavior layer for Boti Local."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime

from .core import MAX_INPUT_LENGTH, MEMORY_FILE, LocalBot, normalize
from .diagnostics import health_report


class EnhancedBot(LocalBot):
    """Stronger offline bot with expanded memory and intent-aware responses."""

    MAX_MEMORY_ITEMS = 1000
    MAX_CONTEXT_ITEMS = 32

    def __init__(self) -> None:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.memory = self._load_extended_memory()
        self.context: list[dict[str, str]] = []

    def _load_extended_memory(self) -> list[dict]:
        if not MEMORY_FILE.exists():
            return []
        try:
            data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            valid = []
            for item in data[-self.MAX_MEMORY_ITEMS:]:
                if not isinstance(item, dict):
                    continue
                if isinstance(item.get("user"), str) and isinstance(item.get("bot"), str):
                    valid.append({"user": item["user"][:MAX_INPUT_LENGTH], "bot": item["bot"][:MAX_INPUT_LENGTH], "time": str(item.get("time", ""))[:40]})
                elif item.get("fact") == "name" and isinstance(item.get("value"), str):
                    valid.append({"fact": "name", "value": item["value"][:80], "time": str(item.get("time", ""))[:40]})
                elif item.get("fact") in {"note", "preference"} and isinstance(item.get("value"), str):
                    valid.append({"fact": item["fact"], "key": str(item.get("key", ""))[:60], "value": item["value"][:300], "time": str(item.get("time", ""))[:40]})
            return valid[-self.MAX_MEMORY_ITEMS:]
        except (OSError, UnicodeError, TypeError, json.JSONDecodeError):
            return []

    def _save_memory(self) -> None:
        payload = json.dumps(self.memory[-self.MAX_MEMORY_ITEMS:], ensure_ascii=False, indent=2)
        fd, temp_name = tempfile.mkstemp(prefix="memory-", suffix=".tmp", dir=MEMORY_FILE.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_name, 0o600)
            os.replace(temp_name, MEMORY_FILE)
        except OSError:
            try:
                os.unlink(temp_name)
            except OSError:
                pass

    def _remember(self, text: str, answer: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        self.memory = (self.memory + [{"user": text[:MAX_INPUT_LENGTH], "bot": answer[:MAX_INPUT_LENGTH], "time": now}])[-self.MAX_MEMORY_ITEMS:]
        self.context = (self.context + [{"user": text[:500], "bot": answer[:1000]}])[-self.MAX_CONTEXT_ITEMS:]
        self._save_memory()

    def _help(self) -> str:
        return super()._help() + " /health، /brain، /context نیز فعال است. حافظه گسترده و پاسخ‌های هوشمند آفلاین فعال‌اند."

    def _command(self, value: str) -> str | None:
        if value in {"/health", "/سلامت", "بررسی سلامت"}:
            return health_report(MEMORY_FILE)
        if value in {"/brain", "/مغز", "قابلیت های هوش"}:
            return "مغز آفلاین بوتی: تشخیص نیت، پاسخ فارسی، حافظه گسترده، زمینه مکالمه، محاسبه امن و گزارش سلامت."
        if value in {"/context", "/زمینه"}:
            if not self.context:
                return "زمینه مکالمه خالی است."
            return "آخرین زمینه‌ها:\n" + "\n".join(f"- {item['user']} → {item['bot']}" for item in self.context[-10:])
        return super()._command(value)

    def reply(self, text: str) -> str:
        value = normalize(str(text))
        if "یادته" in value and self.context:
            return f"بله، آخرین موضوعی که یادم مانده: {self.context[-1]['user']}"
        if any(term in value for term in ("چطور کار میکنی", "چگونه کار میکنی", "هوشت", "مغزت")):
            answer = "من آفلاین کار می‌کنم؛ نیت‌های رایج فارسی، حافظه محلی، زمینه مکالمه و محاسبه امن را پشتیبانی می‌کنم."
            self._remember(str(text).strip(), answer)
            return answer
        return super().reply(text)

    def export_memory(self) -> str:
        return json.dumps(self.memory, ensure_ascii=False, indent=2)
