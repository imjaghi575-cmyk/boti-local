"""Core logic for the offline Persian-friendly Boti Local assistant."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path(__file__).resolve().parent.parent / "data" / "memory.json"


def normalize(text: str) -> str:
    """Normalize common Arabic/Persian character variants for matching."""
    return (
        text.strip().casefold()
        .replace("ي", "ی")
        .replace("ى", "ی")
        .replace("ك", "ک")
        .replace("ۀ", "ه")
        .replace("ة", "ه")
        .replace("‌", " ")
    )


class LocalBot:
    def __init__(self) -> None:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.memory = self._load_memory()

    def _load_memory(self) -> list[dict]:
        if not MEMORY_FILE.exists():
            return []
        try:
            data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save_memory(self) -> None:
        try:
            MEMORY_FILE.write_text(
                json.dumps(self.memory[-100:], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _remember(self, text: str, answer: str) -> None:
        self.memory.append({
            "user": text,
            "bot": answer,
            "time": datetime.now().isoformat(timespec="seconds"),
        })
        self._save_memory()

    def reply(self, text: str) -> str:
        original = text.strip()
        value = normalize(original)
        now = datetime.now()

        if not value:
            return "یک پیام بنویس تا پاسخ بدم."

        # Simple local memory: the user can teach the bot a name or fact.
        name_match = re.search(r"(?:اسم|نام) من\s*(?:این است|هست|است)?\s*[:：-]?\s*(.+)", value)
        if name_match:
            name = name_match.group(1).strip(" .،,!؟")
            answer = f"خوشحالم که شناختیمت، {name}! این مورد را محلی ذخیره کردم."
            self.memory.append({"fact": "name", "value": name, "time": now.isoformat(timespec="seconds")})
            self._save_memory()
            return answer

        if any(x in value for x in ("سلام", "درود", "hello", "hi", "خسته نباشی")):
            answer = "سلام! 🌷 من بوتی هستم. آماده‌ام کمکت کنم."
        elif any(x in value for x in ("اسمت چیه", "نامت چیه", "تو کی هستی", "خودت رو معرفی")):
            answer = "من بوتی هستم؛ یک دستیار محلی، آفلاین و قابل توسعه برای Termux."
        elif "ساعت" in value or "زمان" in value:
            answer = f"ساعت سیستم: {now.strftime('%H:%M:%S')}"
        elif "تاریخ" in value or "امروز" in value:
            answer = f"تاریخ سیستم: {now.strftime('%Y-%m-%d')}"
        elif "یادت" in value or "حافظه" in value:
            answer = self.memory_text()
        elif "کمک" in value or "چه کار" in value or "قابلیت" in value:
            answer = "می‌تونم گفت‌وگوی پایه انجام بدم، زمان و تاریخ سیستم رو بگم و اطلاعات گفتگو رو محلی نگه دارم."
        elif any(x in value for x in ("ممنون", "مرسی", "سپاس")):
            answer = "خواهش می‌کنم! 😊"
        elif "خوبی" in value or "حالت چطوره" in value:
            answer = "خوبم و آماده‌ام! تو چطوری؟"
        elif value.endswith(("؟", "?")):
            answer = "فعلاً آفلاین هستم و دانش محدودی دارم؛ اما می‌تونیم قابلیت‌های بیشتری به من اضافه کنیم."
        else:
            answer = "پیامت دریافت شد. برای راهنمایی، درباره قابلیت‌ها یا حافظه از من سؤال کن."

        self._remember(original, answer)
        return answer

    def memory_text(self) -> str:
        if not self.memory:
            return "حافظه هنوز خالی است."
        lines = ["حافظه محلی (۱۰ مورد آخر):"]
        for item in self.memory[-10:]:
            if "fact" in item:
                lines.append(f"- یادداشت: {item.get('value', '')}")
            else:
                lines.append(f"- شما: {item.get('user', '')}\n  بات: {item.get('bot', '')}")
        return "\n".join(lines)
