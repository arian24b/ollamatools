# ollama-tool-cli

[English](README.md)

مدل‌های [Ollama](https://ollama.com) را از خط فرمان فهرست، به‌روزرسانی، پشتیبان‌گیری و بازیابی کنید. پشتیبان‌ها فایل zip ساده‌اند و می‌توانید آن‌ها را به ماشین دیگر ببرید.

## نصب

پایتون ۳٫۱۲ تا ۳٫۱۵ و Ollama در `PATH` لازم است.

```bash
uv tool install ollama-tool-cli      # یا: pipx install ollama-tool-cli
ollama-tool-cli --help
```

از روی کلون: `uv sync && uv run ollama-tool-cli --help`.

## دستورها

| دستور | کار |
|---|---|
| `list` | جدول مدل‌های نصب‌شده با اندازه و زمان آخرین تغییر |
| `update-models [MODEL] [-j N] [-b]` | آخرین نسخهٔ یک مدل یا همهٔ مدل‌ها را می‌گیرد |
| `backup [-p DIR] [-m MODEL] [-j N] [-b]` | هر مدل را در یک zip می‌نویسد (پیش‌فرض: `~/Downloads/ollama_models_backup`) |
| `restore PATH [-j N] [-b]` | از یک zip یا از همهٔ zipهای یک پوشه بازیابی می‌کند |
| `info` | نسخهٔ Ollama، سیستم‌عامل، تعداد مدل‌ها، مسیر مدل‌ها و مسیر لاگ |
| `logs [-f]` | مسیر فایل لاگ را چاپ می‌کند یا آن را دنبال می‌کند |

`-j/--jobs` تعداد کارهای موازی را تعیین می‌کند و `-b/--background` دستور را جدا از ترمینال اجرا می‌کند و خروجی را در لاگ می‌نویسد. اگر مسیر را به `restore` ندهید، می‌پرسد.

> `update-models` قبلاً `update` بود. حالا `update` خود ابزار را به‌روز می‌کند (پایین‌تر را ببینید).

## نمونه‌ها

```bash
ollama-tool-cli list
ollama-tool-cli update-models                    # همهٔ مدل‌ها
ollama-tool-cli update-models llama3.2 -j 2
ollama-tool-cli backup --path /mnt/backup --model llama3.2
ollama-tool-cli backup --jobs 4 --background
ollama-tool-cli restore /mnt/backup              # پوشه‌ای از zipها
ollama-tool-cli logs --follow
```

هر مدل پس از پایان یک خط وضعیت چاپ می‌کند. اگر کار حتی یک مدل شکست بخورد، کد خروج غیرصفر است.

## لاگ اجرای پس‌زمینه

دستورهای پس‌زمینه در فایل لاگی می‌نویسند که با رسیدن به حد اندازه می‌چرخد:

- macOS: `~/Library/Logs/ollama-tool-cli/`
- Linux: `${XDG_STATE_HOME:-~/.local/state}/ollama-tool-cli/logs/`
- Windows: `%LOCALAPPDATA%\ollama-tool-cli\Logs\`

## دستورهای مشترک

این ابزار روی [cfuicli](https://github.com/arian24b/cfui) ساخته شده و ظاهر و رفتارش با بقیهٔ ابزارهای این مجموعه یکی است.

```bash
ollama-tool-cli help [command]     # راهنما؛ -h روی هر دستور کار می‌کند
ollama-tool-cli version            # نسخه و مخزن گیت (همچنین: -v)
ollama-tool-cli update [--check]   # به‌روزرسانی خود ابزار؛ --check فقط نسخه‌ها را مقایسه می‌کند
ollama-tool-cli -q ...             # حالت آرام: بدون بنر و یادداشت (یا OLLAMA_TOOL_CLI_QUIET=1)
```

- اگر گزینهٔ اجباری جا افتاده باشد و ابزار را در ترمینال اجرا کرده باشید، مقدارش را می‌پرسد. در pipe یا CI با پیام `--flag is required. Pass --flag <value> or run interactively.` متوقف می‌شود (کد خروج ۲).
- خطاها در یک کادر قرمز روی stderr و با کد خروج غیرصفر نمایش داده می‌شوند. با Ctrl-C کد خروج ۱۳۰ است.
- رنگ فقط در ترمینال استفاده می‌شود. با `NO_COLOR=1` خاموش می‌شود.

## توسعه

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv build
```

ابزارهای مرتبط: [LinkCovery](https://github.com/arian24b/linkcovery)، [PEM](https://github.com/arian24b/pem)، [ThroneTools](https://github.com/arian24b/thronetools).

## مجوز

MIT
