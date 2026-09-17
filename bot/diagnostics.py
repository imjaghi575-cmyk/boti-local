"""Runtime diagnostics for Boti Local."""
from __future__ import annotations

import os
import platform
from pathlib import Path


def health_report(memory_file: Path) -> str:
    """Return a safe, non-sensitive local health report."""
    checks: list[str] = []
    parent = memory_file.parent
    checks.append("حافظه: آماده" if parent.exists() and os.access(parent, os.W_OK) else "حافظه: نیازمند بررسی مجوز")
    if memory_file.exists():
        checks.append(f"فایل حافظه: موجود ({memory_file.stat().st_size} بایت)")
    else:
        checks.append("فایل حافظه: هنوز ساخته نشده")
    checks.append(f"سیستم: {platform.system()} | Python: {platform.python_version()}")
    checks.append("حریم خصوصی: ذخیره‌سازی محلی فعال")
    return "گزارش سلامت بوتی:\n- " + "\n- ".join(checks)
