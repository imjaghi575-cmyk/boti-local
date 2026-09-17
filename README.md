# 🤖 Boti Local

ربات محلی فارسی با رابط اختصاصی ترمینال، مناسب اجرای مستقیم در Termux.

## امکانات نسخه اول

- رابط رنگی و اختصاصی در ترمینال
- پاسخ‌های پایه فارسی
- حافظه محلی در `data/memory.json`
- بدون نیاز به کتابخانه خارجی یا سرویس آنلاین
- تنظیم صریح UTF-8 برای خروجی فارسی

## اجرا در Termux

```bash
pkg update -y
pkg install python git -y
git clone https://github.com/imjaghi575-cmyk/boti-local.git
cd boti-local
python main.py
```

## فرمان‌ها

- `/help` راهنما
- `/memory` نمایش حافظه
- `/clear` پاک‌کردن صفحه
- `/exit` خروج

> نکته: برای نمایش بهتر فارسی، در تنظیمات Termux از فونت دارای پشتیبانی فارسی استفاده کنید و در صورت نیاز `pkg install ncurses-utils` را اجرا کنید. شکل‌دهی راست‌به‌چپ به پشتیبانی ترمینال و فونت نیز وابسته است.
