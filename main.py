#!/usr/bin/env python3
"""Boti Local: Persian-friendly terminal chat UI for Termux."""
import os
import sys

# Configure the current Python streams explicitly; changing environment variables
# alone is not enough after Python has already started.
os.environ.setdefault("LANG", "C.UTF-8")
os.environ.setdefault("LC_ALL", "C.UTF-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from bot.core import LocalBot

RESET = "\033[0m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
DIM = "\033[2m"


def clear():
    print("\033[2J\033[H", end="")


def banner():
    print(f"{CYAN}╭────────────────────────────────────────────╮{RESET}")
    print(f"{CYAN}│{RESET}        🤖  B O T I  L O C A L             {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}     ربات محلی فارسی برای ترموکس            {CYAN}│{RESET}")
    print(f"{CYAN}╰────────────────────────────────────────────╯{RESET}")
    print(f"{DIM}فرمان‌ها: /help  /clear  /memory  /exit{RESET}\n")


def main():
    bot = LocalBot()
    clear()
    banner()
    print(f"{GREEN}بات ›{RESET} سلام! من آماده‌ام. پیامت را بنویس.\n")
    while True:
        try:
            text = input(f"{YELLOW}شما › {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nخدانگهدار!")
            break
        if not text:
            continue
        if text in ("/exit", "/quit", "خروج"):
            print("خدانگهدار 🌱")
            break
        if text == "/clear":
            clear(); banner(); continue
        if text == "/help":
            print("/clear پاک‌کردن صفحه | /memory نمایش حافظه | /exit خروج\n")
            continue
        if text == "/memory":
            print(bot.memory_text() + "\n")
            continue
        answer = bot.reply(text)
        print(f"{GREEN}بات ›{RESET} {answer}\n")


if __name__ == "__main__":
    main()
