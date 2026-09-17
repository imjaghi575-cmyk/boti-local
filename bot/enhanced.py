"""Enhanced offline behavior layer for Boti Local."""
from __future__ import annotations

import json
from datetime import datetime

from .core import MAX_INPUT_LENGTH, LocalBot, normalize
from .diagnostics import health_report


class EnhancedBot(LocalBot):
    """A stronger offline bot with larger memory and intent-aware responses."""

    MAX_MEMORY_ITEMS = 1000
    MAX_CONTEXT_ITEMS = 32

    def _remember(self, text: str, answer: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        self.memory = (self.memory + [{
            "user": text[:MAX_INPUT_LENGTH],
            "bot": answer[:MAX_INPUT_LENGTH],
            "time": now,
        }])[-self.MAX_MEMORY_ITEMS:]
        self.context = (self.context + [{"user": text[:500], "bot": answer[:1000]}])[-self.MAX_CONTEXT_ITEMS:]
        self._save_memory()

    def _help(self) -> str:
        return (
            super()._help()
            + " /health، /brain، /context نیز فعال است. حافظه گسترده و پاسخ‌های هوشمند آفلاین فعال‌اند."
        )

    def _command(self, value: str) -> str | None:
        if value in {"/health", "/سلامت", "بررسی سلامت"}:
            from .core import MEMORY_FILE
            return health_report(MEMORY_FILE)
        if value in {"/brain", "/مغز", "قابلیت های هوش"}:
            return (
                "مغز آفلاین بوتی: تشخیص نیت، پاسخ‌های فارسی، حافظه بلندتر، "
                "زمینه مکالمه، محاسبه امن، مدیریت یادداشت و گزارش سلامت."
            )
        if value in {"/context", "/زمینه"}:
            if not self.context:
                return "زمینه مکالمه خالی است."
            return "آخرین زمینه‌ها:\n" + "\n".join(
                f"- {item['user']} → {item['bot']}" for item in self.context[-10:]
            )
        return super()._command(value)

    def reply(self, text: str) -> str:
        value = normalize(str(text))
        if "یادته" in value and self.context:
            latest = self.context[-1]
            return f"بله، آخرین موضوعی که یادم مانده: {latest['user']}"
        if any(term in value for term in ("چطور کار میکنی", "چگونه کار میکنی", "هوشت", "مغزت")):
            answer = (
                "من به‌صورت آفلاین کار می‌کنم؛ نیت‌های رایج فارسی را تشخیص می‌دهم، "
                "حافظه محلی و زمینه مکالمه را نگه می‌دارم و محاسبه را امن انجام می‌دهم."
            )
            self._remember(str(text).strip(), answer)
            return answer
        return super().reply(text)

    def export_memory(self) -> str:
        """Return a UTF-8 JSON export without exposing filesystem paths."""
        return json.dumps(self.memory, ensure_ascii=False, indent=2)
