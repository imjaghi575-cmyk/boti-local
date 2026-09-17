"""Secure, dependency-free Persian-friendly local assistant core."""
from __future__ import annotations

import ast
import json
import math
import operator
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path(__file__).resolve().parent.parent / "data" / "memory.json"
MAX_INPUT_LENGTH = 2000
MAX_MEMORY_ITEMS = 150
MAX_NAME_LENGTH = 80
MAX_MEMORY_TEXT_ITEMS = 12
MAX_EXPRESSION_LENGTH = 80
MAX_AST_NODES = 40
MAX_AST_DEPTH = 12

_BINARY_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_DIGIT_TRANSLATION = str.maketrans("يىكۀةؤإأٱ۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "ییکههوااا01234567890123456789")
_GREETING_WORDS = ("سلام", "درود", "hello", "hi", "صبح بخیر", "شب بخیر", "خسته نباشی")
_THANKS_WORDS = ("ممنون", "مرسی", "سپاس", "متشکرم", "دمت گرم")
_GOODBYE_WORDS = ("خداحافظ", "خدانگهدار", "فعلا", "فعلاً", "بای", "بدرود")


def normalize(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.translate(_DIGIT_TRANSLATION)
    text = re.sub(r"[\u200b\u200d\ufeff]", "", text).replace("\u200c", " ")
    return re.sub(r"\s+", " ", text.strip().casefold())


def _finite(value: int | float, limit: float) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value)) and abs(value) <= limit


def _safe_calculate(expression: str) -> int | float:
    if not expression or len(expression) > MAX_EXPRESSION_LENGTH or not re.fullmatch(r"[0-9+\-*/%.() ]+", expression):
        raise ValueError("unsupported expression")
    tree = ast.parse(expression, mode="eval")
    if len(list(ast.walk(tree))) > MAX_AST_NODES:
        raise ValueError("expression too complex")

    def visit(node: ast.AST, depth: int = 0) -> int | float:
        if depth > MAX_AST_DEPTH:
            raise ValueError("expression too deep")
        if isinstance(node, ast.Expression):
            return visit(node.body, depth + 1)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            if not _finite(node.value, 10**12):
                raise ValueError("number too large")
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            result = _UNARY_OPS[type(node.op)](visit(node.operand, depth + 1))
        elif isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
            left, right = visit(node.left, depth + 1), visit(node.right, depth + 1)
            if isinstance(node.op, ast.Pow) and (abs(right) > 10 or abs(left) > 10**6):
                raise ValueError("power too large")
            result = _BINARY_OPS[type(node.op)](left, right)
        else:
            raise ValueError("unsupported expression")
        if not _finite(result, 10**15):
            raise ValueError("result too large")
        return result
    return visit(tree)


class LocalBot:
    """Offline Persian assistant with bounded memory, context and safe tools."""

    def __init__(self) -> None:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.memory = self._load_memory()
        self.context: list[dict[str, str]] = []

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
                    name = item["value"].strip()
                    if name and len(name) <= MAX_NAME_LENGTH:
                        valid.append({"fact": "name", "value": name, "time": str(item.get("time", ""))[:40]})
                elif item.get("fact") in {"note", "preference"} and isinstance(item.get("value"), str):
                    valid.append({"fact": item["fact"], "key": str(item.get("key", ""))[:60], "value": item["value"][:300], "time": str(item.get("time", ""))[:40]})
                elif isinstance(item.get("user"), str) and isinstance(item.get("bot"), str):
                    valid.append({"user": item["user"][:MAX_INPUT_LENGTH], "bot": item["bot"][:MAX_INPUT_LENGTH], "time": str(item.get("time", ""))[:40]})
            return valid[-MAX_MEMORY_ITEMS:]
        except (json.JSONDecodeError, OSError, UnicodeError, TypeError):
            return []

    def _save_memory(self) -> None:
        payload = json.dumps(self.memory[-MAX_MEMORY_ITEMS:], ensure_ascii=False, indent=2)
        fd, temp_name = tempfile.mkstemp(prefix="memory-", suffix=".tmp", dir=MEMORY_FILE.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload); handle.flush(); os.fsync(handle.fileno())
            os.chmod(temp_name, 0o600); os.replace(temp_name, MEMORY_FILE)
        except (OSError, UnicodeError):
            try: os.close(fd)
            except OSError: pass
            try: os.unlink(temp_name)
            except OSError: pass

    def _remember(self, text: str, answer: str) -> None:
        self.memory = (self.memory + [{"user": text[:MAX_INPUT_LENGTH], "bot": answer[:MAX_INPUT_LENGTH], "time": datetime.now().isoformat(timespec="seconds")}])[-MAX_MEMORY_ITEMS:]
        self.context = (self.context + [{"user": text[:300], "bot": answer[:500]}])[-8:]
        self._save_memory()

    def clear_memory(self) -> None:
        self.memory = []; self.context = []; self._save_memory()

    def forget_name(self) -> None:
        self.memory = [item for item in self.memory if item.get("fact") != "name"]; self._save_memory()

    def stats(self) -> str:
        return f"تعداد موارد حافظه: {len(self.memory)} از {MAX_MEMORY_ITEMS} | زمینه مکالمه: {len(self.context)} مورد"

    def _saved_name(self) -> str | None:
        for item in reversed(self.memory):
            if item.get("fact") == "name" and item.get("value"):
                return str(item["value"])
        return None

    def _find_fact(self, fact: str, key: str) -> str | None:
        for item in reversed(self.memory):
            if item.get("fact") == fact and item.get("key") == key:
                return str(item.get("value", ""))
        return None

    def _save_fact(self, fact: str, key: str, value: str) -> str:
        self.memory = [item for item in self.memory if not (item.get("fact") == fact and item.get("key") == key)]
        self.memory.append({"fact": fact, "key": key[:60], "value": value[:300], "time": datetime.now().isoformat(timespec="seconds")})
        self.memory = self.memory[-MAX_MEMORY_ITEMS:]; self._save_memory()
        return "ذخیره شد؛ از این به بعد یادم می‌ماند."

    def _answer_for_math(self, value: str) -> str | None:
        match = re.search(r"(?:حساب کن|محاسبه کن|جواب|حساب)\s*[:：]?\s*(.*)$", value)
        if not match: return None
        try:
            result = _safe_calculate(match.group(1).strip())
            return f"نتیجه: {result:g}" if isinstance(result, float) else f"نتیجه: {result}"
        except (ValueError, SyntaxError, ZeroDivisionError, OverflowError, MemoryError, RecursionError):
            return "این عبارت ریاضی قابل محاسبه نیست."

    def _help(self) -> str:
        return ("دستورات: /help، /memory، /stats، /clear، /forget-name، /time، /date، "
                "/calc عبارت، /repeat متن، /remember کلید=مقدار، /recall کلید، /forget کلید. "
                "گفت‌وگوی فارسی، نام، یادداشت، ترجیحات، زمینه مکالمه و محاسبه امن فعال است.")

    def _command(self, value: str) -> str | None:
        if value in {"/help", "کمک", "راهنما"}: return self._help()
        if value in {"/memory", "/حافظه"}: return self.memory_text()
        if value in {"/stats", "/آمار", "آمار حافظه"}: return self.stats()
        if value in {"/clear", "/پاک کردن حافظه"}: self.clear_memory(); return "حافظه محلی و زمینه مکالمه پاک شد."
        if value in {"/forget-name", "/فراموشی نام"}: self.forget_name(); return "نام ذخیره‌شده حذف شد."
        if value in {"/time", "/ساعت"}: return f"ساعت سیستم: {datetime.now():%H:%M:%S}"
        if value in {"/date", "/تاریخ"}: return f"تاریخ سیستم: {datetime.now():%Y-%m-%d}"
        if value.startswith("/repeat "): return value[8:].strip()[:MAX_INPUT_LENGTH] or "متنی برای تکرار وارد کن."
        if value.startswith("/calc "): return self._answer_for_math("حساب: " + value[6:])
        if value.startswith("/remember "):
            pair = value[10:].strip()
            if "=" not in pair: return "قالب درست: /remember کلید=مقدار"
            key, item = (part.strip() for part in pair.split("=", 1))
            return self._save_fact("note", key, item) if key and item else "کلید و مقدار را کامل وارد کن."
        if value.startswith("/recall "):
            key = value[8:].strip(); found = self._find_fact("note", key)
            return f"{key}: {found}" if found else "چیزی با این کلید پیدا نشد."
        if value.startswith("/forget "):
            key = value[8:].strip(); before = len(self.memory)
            self.memory = [item for item in self.memory if not (item.get("fact") == "note" and item.get("key") == key)]
            self._save_memory(); return "یادداشت حذف شد." if len(self.memory) < before else "یادداشتی با این کلید پیدا نشد."
        return None

    def reply(self, text: str) -> str:
        original = str(text).strip()[:MAX_INPUT_LENGTH]; value = normalize(original); now = datetime.now()
        if not value: return "یک پیام بنویس تا پاسخ بدم."
        command_answer = self._command(value)
        if command_answer is not None:
            if not value.startswith(("/clear", "/forget", "/forget-name")): self._remember(original, command_answer)
            return command_answer
        name_match = (re.fullmatch(r"(?:اسم|نام) من\s+(.+?)\s+(?:هست|است)$", value) or re.fullmatch(r"(?:اسم|نام) من\s+(?:این است)\s+(.+)$", value) or re.fullmatch(r"(?:اسم|نام) من\s*[:：-]\s*(.+)$", value))
        if name_match:
            name = name_match.group(1).strip(" .،,!؟")
            if not name or len(name) > MAX_NAME_LENGTH or name in {"چیه", "چیست", "چی", "؟", "?"}: return "اسم را کامل بنوی؛ مثلاً: اسم من علی است."
            answer = f"خوشحالم که شناختیمت، {name}! این مورد را محلی ذخیره کردم."
            self.memory = [item for item in self.memory if item.get("fact") != "name"]
            self.memory.append({"fact": "name", "value": name, "time": now.isoformat(timespec="seconds")}); self._save_memory(); return answer
        match = re.search(r"(?:یادداشت کن|یادم باشه|یادت باشه)\s+(.+?)\s*[:：=]\s*(.+)$", value)
        if match: return self._save_fact("note", match.group(1).strip(), match.group(2).strip())
        answer = self._answer_for_math(value)
        if answer is None:
            if any(x in value for x in ("اسم من چیه", "اسم من چیست", "نام من چیه", "نام من چیست", "من کی هستم")):
                saved = self._saved_name(); answer = f"اسم تو {saved} است." if saved else "هنوز اسمت را به من نگفتی."
            elif any(x in value for x in _GREETING_WORDS):
                saved = self._saved_name(); answer = f"سلام {saved}! 🌷" if saved else "سلام! 🌷 من بوتی هستم؛ آماده‌ام کمکت کنم."
            elif any(x in value for x in ("اسمت چیه", "نامت چیه", "تو کی هستی", "خودت رو معرفی")): answer = "من بوتی هستم؛ دستیار محلی و آفلاین فارسی."
            elif "ساعت" in value or "زمان" in value: answer = f"ساعت سیستم: {now:%H:%M:%S}"
            elif "تاریخ" in value or "امروز" in value: answer = f"تاریخ سیستم: {now:%Y-%m-%d}"
            elif "یادت" in value or "حافظه" in value: answer = self.memory_text()
            elif "کمک" in value or "قابلیت" in value or "چه کار" in value: answer = self._help()
            elif any(x in value for x in _THANKS_WORDS): answer = "خواهش می‌کنم! 😊"
            elif any(x in value for x in _GOODBYE_WORDS): answer = "خدانگهدار! 🌱"
            elif "خوبی" in value or "حالت چطوره" in value: answer = "خوبم و آماده‌ام! تو چطوری؟"
            elif "یادته" in value and self.context: answer = f"آخرین موضوع مکالمه‌مان: {self.context[-1]['user']}"
            elif value.endswith(("؟", "?")): answer = "فعلاً آفلاین هستم؛ می‌توانی از /remember برای ذخیره اطلاعات و از /help برای دستورات استفاده کنی."
            else: answer = "پیامت دریافت شد. می‌توانی سؤال مشخص بپرسی یا از /help استفاده کنی."
        self._remember(original, answer); return answer

    def memory_text(self) -> str:
        if not self.memory: return "حافظه هنوز خالی است."
        lines = [f"حافظه محلی ({min(MAX_MEMORY_TEXT_ITEMS, len(self.memory))} مورد آخر):"]
        for item in self.memory[-MAX_MEMORY_TEXT_ITEMS:]:
            if item.get("fact") == "name": lines.append(f"- نام: {item.get('value', '')}")
            elif item.get("fact") in {"note", "preference"}: lines.append(f"- {item.get('key', '')}: {item.get('value', '')}")
            else: lines.append(f"- شما: {item.get('user', '')}\n  بات: {item.get('bot', '')}")
        return "\n".join(lines)
