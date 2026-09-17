#!/usr/bin/env python3
"""Boti Local: safe Persian-friendly terminal UI for Termux."""
from __future__ import annotations

import os
import sys

from bot.core import MAX_INPUT_LENGTH, LocalBot

os.environ.setdefault("LANG", "C.UTF-8")
os.environ.setdefault("LC_ALL", "C.UTF-8")
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

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
    print(paint(DIM, "فرمان‌ها: /help /clear /memory /stats /forget /forget-name /time /date /calc /repeat /remember /recall /about /exit\n"))


def print_answer(answer: str) -> None:
    print(paint(GREEN, "بات ›") + f" {answer}\n")


def main() -> None:
    try:
        bot = LocalBot()
    except (OSError, UnicodeError):
        print("خطا در آماده‌سازی حافظه محلی. مسیر دسترسی و مجوز پوشه data را بررسی کن.")
        return

    clear()
    banner()
    print_answer("سلام! من آماده‌ام. پیامت را بنویس.")
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
        if command in {"/exit", "/quit", "خروج"}:
            print("خدانگهدار 🌱")
            break
        if command in {"/clear-screen", "/صفحه"}:
            clear()
            banner()
            continue
        if command == "/about":
            print_answer("بوتی یک ربات محلی فارسی و بدون وابستگی اجباری به اینترنت است؛ داده‌ها در data/memory.json ذخیره می‌شوند.")
            continue

        # Route all bot commands through one core to keep terminal behavior consistent.
        try:
            answer = bot.reply(text)
        except (OSError, UnicodeError, ValueError, TypeError, RecursionError):
            answer = "در پردازش پیام مشکلی پیش آمد؛ دوباره تلاش کن."
        print_answer(answer)


if __name__ == "__main__":
    main()
