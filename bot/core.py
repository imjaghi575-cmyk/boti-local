"""Secure, dependency-free Persian-friendly local assistant core."""
from __future__ import annotations

import ast
import json
import operator
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

_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def normalize(text: str) -> str:
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


def _safe_calculate(expression: str) -> int | float:
    """Evaluate bounded arithmetic AST nodes without executing arbitrary code."""
    if not expression or len(expression) > 80 or not re.fullmatch(r"[0-9+\-*/%.() ]+", expression):
        raise ValueError("unsupported expression")
    tree = ast.parse(expression, mode="eval")

    def visit(node: ast.AST) -> int | float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            if not (float("-inf") < node.value < float("inf")) or abs(node.value) > 10**12:
                raise ValueError("number too large")
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("power too large")
            result = _BINARY_OPS[type(node.op)](left, right)
            if not isinstance(result, (int, float)) or not (float("-inf") < result < float("inf")) or abs(result) > 10**15:
                raise ValueError("result too large")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            result = _UNARY_OPS[type(node.op)](visit(node.operand))
            if abs(result) > 10**15:
                raise ValueError("result too large")
            return result
        raise ValueError("unsupported expression")

    return visit(tree)


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
                if not isinstance(item, dict):
                    continue
                if item.get("fact") == "name" and isinstance(item.get("value"), str):
                    value = item["value"].strip()[:MAX_NAME_LENGTH]
                    if value:
                        valid.append({"fact": "name", "value": value, "time": str(item.get("time", ""))[:40]})
                elif isinstance(item.get("user"), str) and isinstance(item.get("bot"), str):
                    valid.append({
                        "user": item["user"][:MAX_INPUT_LENGTH],
                        "bot": item["bot"][:MAX_INPUT_LENGTH],
                        "time": str(item.get("time", ""))[:40],
                    })
            return valid[-MAX_MEMORY_ITEMS:]
        except (json.JSONDecodeError, OSError, UnicodeError, TypeError):
            return []

    def _save_memory(self) -> None:
        payload = json.dumps(self.memory[-MAX_MEMORY_ITEMS:], ensure_ascii=False, indent=2)
        fd, temp_name = tempfile.mkstemp(prefix="memory-", suffix=".tmp", dir=MEMORY_FILE.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_name, 0o600)
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
        self.memory.append({"user": text[:MAX_INPUT_LENGTH], "bot": answer[:MAX_INPUT_LENGTH], "time": datetime.now().isoformat(timespec="seconds")})
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

    def _answer_for_math(self, value: str) -> str | None:
        command_match = re.search(r"(?:حساب کن|محاسبه کن|جواب)\s*[:：]?\s*(.*)$", value)
        if not command_match:
            return None
        expression = command_match.group(1).strip()
        if not expression:
            return "این عبارت ریاضی قابل محاسبه نیست."
        try:
            result = _safe_calculate(expression)
            return f"نتیجه: {result:g}" if isinstance(result, float) else f"نتیجه: {result}"
        except (ValueError, SyntaxError, ZeroDivisionError, OverflowError, MemoryError, RecursionError):
            return "این عبارت ریاضی قابل محاسبه نیست."

    def reply(self, text: str) -> str:
        original = str(text).strip()[:MAX_INPUT_LENGTH]
        value = normalize(original)
        now = datetime.now()
        if not value:
            return "یک پیام بنویس تا پاسخ بدم."

        name_match = re.fullmatch(
            r"(?:اسم|نام) من\s*(?:(?:این است|هست|است)\s*[:：-]?\s*|[:：-]\s*)(.+)",
            value,
        )
        if name_match:
            name = name_match.group(1).strip(" .،,!؟")[:MAX_NAME_LENGTH]
            if not name or name in {"چیه", "چیست", "چی", "؟", "?"}:
                return "اسم را کامل بنویس؛ مثلاً: اسم من علی است."
            answer = f"خوشحالم که شناختیمت، {name}! این مورد را محلی ذخیره کردم."
            self.memory = [item for item in self.memory if item.get("fact") != "name"]
            self.memory.append({"fact": "name", "value": name, "time": now.isoformat(timespec="seconds")})
            self.memory = self.memory[-MAX_MEMORY_ITEMS:]
            self._save_memory()
            return answer

        math_answer = self._answer_for_math(value)
        if math_answer is not None:
            answer = math_answer
        elif any(x in value for x in ("اسم من چیه", "نام من چیه", "من کی هستم")):
            saved_name = self._saved_name()
            answer = f"اسم تو {saved_name} است." if saved_name else "هنوز اسمت را به من نگفتی."
        elif any(x in value for x in ("سلام", "درود", "hello", "hi", "خسته نباشی")):
            saved_name = self._saved_name()
            answer = f"سلام {saved_name}! 🌷 من بوتی هستم." if saved_name else "سلام! 🌷 من بوتی هستم. آماده‌ام کمکت کنم."
        elif any(x in value for x in ("اسمت چیه", "نامت چیه", "تو کی هستی", "خودت رو معرفی")):
            answer = "من بوتی هستم؛ دستیار محلی و آفلاین برای Termux. می‌توانم حافظه، محاسبه ساده، زمان، تاریخ و گفت‌وگوی پایه را مدیریت کنم."
        elif "ساعت" in value or "زمان" in value:
            answer = f"ساعت سیستم: {now.strftime('%H:%M:%S')}"
        elif "تاریخ" in value or "امروز" in value:
            answer = f"تاریخ سیستم: {now.strftime('%Y-%m-%d')}"
        elif "یادت" in value or "حافظه" in value:
            answer = self.memory_text()
        elif "کمک" in value or "چه کار" in value or "قابلیت" in value:
            answer = "قابلیت‌ها: گفت‌وگوی پایه، ذخیره نام، حافظه محلی، محاسبه امن عبارت‌های ساده، زمان و تاریخ سیستم. فرمان‌ها: /help، /memory، /stats، /forget، /clear و /exit."
        elif any(x in value for x in ("ممنون", "مرسی", "سپاس")):
            answer = "خواهش می‌کنم! 😊"
        elif "خوبی" in value or "حالت چطوره" in value:
            answer = "خوبم و آماده‌ام! تو چطوری؟"
        elif value.endswith(("؟", "?")):
            answer = "فعلاً آفلاین هستم و دانش محدودی دارم. می‌توانی از قابلیت‌های محلی، حافظه یا محاسبه ساده استفاده کنی."
        else:
            answer = "پیامت دریافت شد. می‌توانی سؤال مشخص بپرسی، نامت را معرفی کنی یا بنویسی «حساب کن: ۱۲ + ۸»."

        self._remember(original, answer)
        return answer

    def memory_text(self) -> str:
        if not self.memory:
            return "حافظه هنوز خالی است."
        lines = [f"حافظه محلی ({min(MAX_MEMORY_TEXT_ITEMS, len(self.memory))} مورد آخر):"]
        for item in self.memory[-MAX_MEMORY_TEXT_ITEMS:]:
            if item.get("fact") == "name":
                lines.append(f"- نام ذخیره‌شده: {item.get('value', '')}")
            else:
                lines.append(f"- شما: {item.get('user', '')}\n  بات: {item.get('bot', '')}")
        return "\n".join(lines)
