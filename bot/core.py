import json
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path(__file__).resolve().parent.parent / "data" / "memory.json"


class LocalBot:
    def __init__(self):
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.memory = self._load_memory()

    def _load_memory(self):
        if not MEMORY_FILE.exists():
            return []
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save_memory(self):
        MEMORY_FILE.write_text(
            json.dumps(self.memory[-100:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def reply(self, text: str) -> str:
        normalized = text.casefold()
        if any(word in normalized for word in ("سلام", "درود", "hello", "hi")):
            answer = "سلام! خوش اومدی 🌷"
        elif "اسمت" in text or "نامت" in text:
            answer = "من بوتی هستم؛ یک ربات محلی و قابل توسعه."
        elif "ساعت" in text:
            answer = f"زمان محلی سیستم: {datetime.now().strftime('%H:%M:%S')}"
        elif "کمک" in text or "چه کار" in text:
            answer = "فعلاً گفت‌وگوی پایه، حافظه محلی و رابط ترمینالی دارم."
        else:
            answer = "پیامت رو دریافت کردم. در نسخه‌های بعدی هوشمندتر می‌شم."
        self.memory.append({"user": text, "bot": answer, "time": datetime.now().isoformat(timespec="seconds")})
        self._save_memory()
        return answer

    def memory_text(self) -> str:
        if not self.memory:
            return "حافظه هنوز خالی است."
        lines = ["حافظه محلی:"]
        for item in self.memory[-10:]:
            lines.append(f"- شما: {item['user']}\n  بات: {item['bot']}")
        return "\n".join(lines)
