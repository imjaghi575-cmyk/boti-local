"""Secure, dependency-free core for the Persian-friendly local assistant."""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path(__file__).resolve().parent.parent / "data" / "memory.json"
MAX_INPUT_LENGTH = 2000
MAX_MEMORY_ITEMS = 100
MAX_NAME_LENGTH = 80
MAX_MEMORY_TEXT_ITEMS = 10


def normalize(text: str) -> str:
    """Normalize common Persian/Arabic variants and invisible characters."""
    if not isinstance(text, str):
        return ""
    replacements = str.maketrans({
        "ي": "ی", "ى": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه",
        "ؤ": "و", "إ": "ا", "أ": "ا", "ٱ": "ا",
        "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
        "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
    })
    text = text.translate(replacements)
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", " ", text)
    return re.sub(r"\s+", " ", text.strip().casefold())


class LocalBot:
    def __init__(self) -> None:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.memory = self._load_memory()

    def _load_memory(self) -> list[dict]:
        if not MEMORY_FILE.exists():
            return []
        try:
            data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            valid = []
            for item in data[-MAX_MEMORY_ITEMS:]:
                if isinstance(item, dict) and ("user" in item or "fact" in item):
                    valid.append(item)
            return valid[-MAX_MEMORY_ITEMS:]
        except (json.JSONDecodeError, OSError, UnicodeError):
            return []

    def _save_memory(self) -> None:
        """Write memory atomically to reduce corruption after interruption."""
        payload = json.dumps(self.memory[-MAX_MEMORY_ITEMS:], ensure_ascii=False, indent=2)
        fd, temp_name = tempfile.mkstemp(prefix="memory-", suffix=".tmp", dir=MEMORY_FILE.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temp_name, 0o600)
            except OSError:
                pass
            os.replace(temp_name, MEMORY_FILE)
        except (OSError, UnicodeError):
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                os.unlink(temp_name)
            except OSError:
                pass

    def _remember(self, text: str, answer: str) -> None:
        self.memory.append({
            "user": text[:MAX_INPUT_LENGTH],
            "bot": answer[:MAX_INPUT_LENGTH],
            "time": datetime.now().isoformat(timespec="seconds"),
        })
        self.memory = self.memory[-MAX_MEMORY_ITEMS:]
        self._save_memory()

    def clear_memory(self) -> None:
        self.memory.clear()
        self._save_memory()

    def stats(self) -> str:
        return f"تعداد موارد حافظه: {len(self.memory)} از {MAX_MEMORY_ITEMS}"

    def _saved_name(self) -> str | None:
        for item in reversed(self.memory):
            if item.get("fact") == "name" and item.get("value"):
                return str(item["value"])
        return None

    def reply(self, text: str) -> str:
        original = str(text).strip()[:MAX_INPUT_LENGTH]
        value = normalize(original)
        now = datetime.now()
        if not value:
            return "یک پیام بنویس تا پاسخ بدم."

        name_match = re.search(r"(?:اسم|نام) من\s*(?:این است|هست|است)?\s*[:：-]?\s*(.+)", value)
        if name_match:
            name = name_match.group(1).strip(" .،,!؟")[:MAX_NAME_LENGTH]
            answer = f"خوشحالم که شناختیمت، {name}! این مورد را محلی ذخیره کردم."
            self.memory = [item for item in self.memory if item.get("fact") != "name"]
            self.memory.append({"fact": "name", "value": name, "time": now.isoformat(timespec="seconds")})
            self.memory = self.memory[-MAX_MEMORY_ITEMS:]
            self._save_memory()
            return answer

        if any(x in value for x in ("اسم من چیه", "نام من چیه", "من کی هستم")):
            saved_name = self._saved_name()
            answer = f"اسم تو {saved_name} است." if saved_name else "هنوز اسمت را به من نگفتی."
        elif any(x in value for x in ("سلام", "درود", "hello", "hi", "خسته نباشی")):
            saved_name = self._saved_name()
            answer = f"سلام {saved_name}! 🌷 من بوتی هستم." if saved_name else "سلام! 🌷 من بوتی هستم. آماده‌ام کمکت کنم."
        elif any(x in value for x in ("اسمت چیه", "نامت چیه", "تو کی هستی", "خودت رو معرفی")):
            answer = "من بوتی هستم؛ یک دستیار محلی، آفلاین و قابل توسعه برای Termux."
        elif "ساعت" in value or "زمان" in value:
            answer = f"ساعت سیستم: {now.strftime('%H:%M:%S')}"
        elif "تاریخ" in value or "امروز" in value:
            answer = f"تاریخ سیستم: {now.strftime('%Y-%m-%d')}"
        elif "یادت" in value or "حافظه" in value:
            answer = self.memory_text()
        elif "کمک" in value or "چه کار" in value or "قابلیت" in value:
            answer = "می‌تونم گفت‌وگوی پایه انجام بدم، نامت را به خاطر بسپارم، زمان و تاریخ سیستم را بگم و اطلاعات گفتگو را محلی نگه دارم."
        elif any(x in value for x in ("ممنون", "مرسی", "سپاس")):
            answer = "خواهش می‌کنم! 😊"
        elif "خوبی" in value or "حالت چطوره" in value:
            answer = "خوبم و آماده‌ام! تو چطوری؟"
        elif value.endswith(("؟", "?")):
            answer = "فعلاً آفلاین هستم و دانش محدودی دارم؛ اما می‌تونم با قابلیت‌های محلی و بدون اینترنت توسعه پیدا کنم."
        else:
            answer = "پیامت دریافت شد. برای شروع می‌تونی سلام کنی، اسمت را بگی، درباره حافظه یا قابلیت‌ها سؤال کنی."

        self._remember(original, answer)
        return answer

    def memory_text(self) -> str:
        if not self.memory:
            return "حافظه هنوز خالی است."
        lines = [f"حافظه محلی ({MAX_MEMORY_TEXT_ITEMS} مورد آخر):"]
        for item in self.memory[-MAX_MEMORY_TEXT_ITEMS:]:
            if item.get("fact") == "name":
                lines.append(f"- نام ذخیره‌شده: {item.get('value', '')}")
            else:
                lines.append(f"- شما: {item.get('user', '')}\n  بات: {item.get('bot', '')}")
        return "\n".join(lines)
