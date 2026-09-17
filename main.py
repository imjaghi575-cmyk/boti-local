#!/usr/bin/env python3
"""Boti Local: safe Persian-friendly terminal UI for Termux."""
import os
import sys

os.environ.setdefault("LANG", "C.UTF-8")
os.environ.setdefault("LC_ALL", "C.UTF-8")
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

from bot.core import LocalBot, MAX_INPUT_LENGTH

RESET = "\033[0m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
DIM = "\033[2m"
USE_COLOR = bool(getattr(sys.stdout, "isatty", lambda: False)())


def paint(code: str, text: str) -> str:
    return f"{code}{text}{RESET}" if USE_COLOR else text


def clear() -> None:
    if USE_COLOR:
        print("\033[2J\033[H", end="")


def banner() -> None:
    print(paint(CYAN, "╭────────────────────────────────────────────╮"))
    print(paint(CYAN, "│") + "        🤖  B O T I  L O C A L             " + paint(CYAN, "│"))
    print(paint(CYAN, "│") + "     ربات محلی فارسی برای ترموکس            " + paint(CYAN, "│"))
    print(paint(CYAN, "╰────────────────────────────────────────────╯"))
    print(paint(DIM, "فرمان‌ها: /help  /clear  /memory  /stats  /forget  /about  /exit\n"))


def main() -> None:
    try:
        bot = LocalBot()
    except (OSError, UnicodeError):
        print("خطا در آماده‌سازی حافظه محلی. مسیر دسترسی و مجوز پوشه data را بررسی کن.")
        return

    clear()
    banner()
    print(paint(GREEN, "بات ›") + " سلام! من آماده‌ام. پیامت را بنویس.\n")
    while True:
        try:
            text = input(paint(YELLOW, "شما › ")).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nخدانگهدار!")
            break
        if not text:
            continue
        if len(text) > MAX_INPUT_LENGTH:
            print(f"پیام بیش از حد طولانی است؛ حداکثر {MAX_INPUT_LENGTH} نویسه.\n")
            continue
        command = text.casefold()
        if command in ("/exit", "/quit", "خروج"):
            print("خدانگهدار 🌱")
            break
        if command == "/clear":
            clear(); banner(); continue
        if command == "/help":
            print("/clear پاک‌کردن صفحه | /memory نمایش حافظه | /stats آمار | /forget حذف حافظه | /about درباره ربات | /exit خروج")
            print("برای محاسبه امن بنویس: حساب کن: ۱۲ + ۸\n")
            continue
        if command == "/memory":
            try:
                print(bot.memory_text() + "\n")
            except Exception:
                print("نمایش حافظه ممکن نشد.\n")
            continue
        if command == "/stats":
            print(bot.stats() + "\n")
            continue
        if command == "/forget":
            try:
                bot.clear_memory()
                print("حافظه محلی پاک شد.\n")
            except Exception:
                print("پاک‌کردن حافظه انجام نشد.\n")
            continue
        if command == "/about":
            print("بوتی یک ربات محلی و بدون وابستگی اجباری به اینترنت است. داده‌ها در data/memory.json ذخیره می‌شوند.\n")
            continue
        try:
            answer = bot.reply(text)
        except Exception:
            answer = "در پردازش پیام مشکلی پیش آمد؛ دوباره تلاش کن."
        print(paint(GREEN, "بات ›") + f" {answer}\n")


if __name__ == "__main__":
    main()
