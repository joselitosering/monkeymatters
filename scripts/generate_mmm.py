#!/usr/bin/env python3
"""
generate_mmm.py — Shadow Monkey Morning Market Monitor generator.

Runs inside GitHub Actions (see .github/workflows/mmm-daily.yml).
Design principle: this script does NOT try to hand-template the APEX
report itself. The live template (templates/mmm_template.html) uses
positional, non-uniquely-named {{TOKENS}} (e.g. {{STAT_COL1}} repeats
~25x per futures table) — a blind Python find/replace would silently
scramble label/value pairs. Instead: Claude (with web_search) reads the
FULL template in one call and returns the FULL filled document. Python's
job is orchestration + hard guardrails, never content invention:
  - compute date/day-of-week deterministically (eliminates the
    "Monday, August 18" bug found 2026-08-18 — hand-typed, wrong weekday)
  - self-gate on the correct 6:25 AM PT window regardless of DST
  - refuse to publish if any {{TOKEN}} survives, or the doc looks truncated
  - run sanitize.py before anything is committed
"""
from __future__ import annotations
import os, re, sys, subprocess, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = ROOT / "templates" / "mmm_template.html"
OUT_DIR = ROOT / "docs" / "mmm-daily"
INDEX_PATH = ROOT / "docs" / "index.html"
PT = ZoneInfo("America/Los_Angeles")

MODEL = "claude-sonnet-5"
MAX_TOKENS = 16000
TARGET_HOUR, TARGET_MIN, WINDOW_MIN = 6, 25, 20  # 6:25 AM PT +/- 20 min


def gate(force: bool) -> datetime.datetime:
    """Exit 0 (no-op, not a failure) unless it's actually a weekday within
    the 6:25 AM PT window, or the run was manually forced."""
    now = datetime.datetime.now(PT)
    if force:
        print(f"FORCE_RUN set — skipping time/weekday gate. Now: {now.isoformat()}")
        return now
    if now.weekday() >= 5:
        print(f"Weekend ({now.strftime('%A')}) — no-op.")
        sys.exit(0)
    target = now.replace(hour=TARGET_HOUR, minute=TARGET_MIN, second=0, microsecond=0)
    delta_min = abs((now - target).total_seconds()) / 60
    if delta_min > WINDOW_MIN:
        print(f"Outside 6:25 AM PT window (now {now.strftime('%H:%M %Z')}, "
              f"{delta_min:.0f} min off target) — this is the DST-mirror cron "
              f"firing at the wrong offset. No-op.")
        sys.exit(0)
    print(f"In window: {now.isoformat()} ({delta_min:.0f} min from target)")
    return now


def build_prompt(now: datetime.datetime, template_html: str) -> tuple[str, str]:
    date_long = now.strftime("%A, %B ") + str(now.day) + now.strftime(", %Y")
    date_short = now.strftime("%b ") + str(now.day)
    day_of_week = now.strftime("%A")
    prev = now - datetime.timedelta(days=3 if now.weekday() == 0 else 1)
    prev_date_short = prev.strftime("%b ") + str(prev.day)

    system = f"""You are Shadow Monkey — hyper-intelligent financial strategist and \
wealth architect for Joe (Handler), Entity: Monkey Matters LLC / JVS Holdings LTD. \
No hallucination: every number must trace to something you actually found via \
web_search this call. If a figure is genuinely unavailable, write "N/A" rather \
than invent it — never publish a fabricated level. No filler, no hedging language \
in the analysis fields; write like a seasoned trading-desk operative.

TASK: Fill the Morning Market Monitor HTML template below with TODAY's real data \
and analysis, using web_search as needed (indices/futures levels, VIX, gold, \
BTC/ETH, econ calendar, earnings, pre-market movers, sector performance, \
geopolitical/macro catalysts). Ground every trade idea and level in what you \
actually found or in standard, clearly-labeled technical calculation (pivots, \
prior settlement, etc.) — never a guess presented as fact.

HARD FACTS — use these exactly, do not recompute or vary them:
  DAY_OF_WEEK = "{day_of_week}"
  DATE_LONG = "{date_long}"
  DATE_SHORT = "{date_short}"
  PREV_DATE_SHORT = "{prev_date_short}"

TEMPLATE STRUCTURE NOTES:
  - {{{{TOKEN}}}} placeholders repeat with IDENTICAL names across sections \
(e.g. {{{{CA_ANALYSIS}}}}, {{{{STAT_COL1}}}}/{{{{STAT_COL2}}}}) — each occurrence \
must be filled with content correct FOR ITS OWN POSITION, not copy-pasted from \
another section.
  - Comment blocks like "<!-- INJECT: S06 ECON CALENDAR — repeat <tr> per event: \
... -->" show the exact <tr> markup to replicate; delete the comment markers and \
emit one real <tr> per real item (use as many rows as you have real data for, \
not a fixed count) using that exact markup pattern.
  - The trade-ideas <tbody> (id="apexTradeTable") wants up to 20 rows in column \
order #, Symbol, Type, Direction, Setup, Entry, Stop, Target, R:R, Notes, \
Priority — only include ideas you can actually ground in today's data; do not \
pad to 20 with filler.
  - {{{{STAT_COL1}}}}/{{{{STAT_COL2}}}} pairs under each futures table are \
label/value pairs — reuse the exact row labels already established in this \
template family (Prev High, Prev Low, Settlement, Pre-Mkt Est., Gap / ADR, then \
under "Pivot Levels": PP, R3, R2, R1, S1, S2, S3, then under "Volume Profile": \
VAH, POC, VAL, Prev VWAP) unless the surrounding sub-header in the template asks \
for something else — match the sub-header groupings you see below.

OUTPUT RULES:
  - Respond with ONLY the complete filled HTML document. First character must \
be "<". No commentary, no markdown code fences, no preamble or sign-off.
  - Zero unresolved "{{{{" tokens may remain anywhere in the output.
  - Keep every CSS class, structural div, and script block from the template \
byte-identical except where a token is being replaced with real content — do \
not redesign, do not drop the trade-table sort/filter script at the bottom.

TEMPLATE TO FILL:
{template_html}
"""
    user = (f"Generate today's Morning Market Monitor — {day_of_week}, {date_long}. "
            "Research live and fill the template completely per the system instructions.")
    return system, user


def call_claude(system: str, user: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": user}],
    )
    text_blocks = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    if not text_blocks:
        raise RuntimeError(f"No text block in response. stop_reason={resp.stop_reason}")
    html = text_blocks[-1].strip()
    # Defensive strip in case markdown fences slipped through despite instructions.
    html = re.sub(r"^```(?:html)?\s*", "", html)
    html = re.sub(r"\s*```$", "", html)
    return html.strip()


def validate(html: str) -> None:
    if not html.startswith("<!DOCTYPE html>") and not html.startswith("<!doctype html>"):
        raise RuntimeError("Output does not start with <!DOCTYPE html> — refusing to publish.")
    if "{{" in html:
        leftover = sorted(set(re.findall(r"\{\{[A-Z0-9_*]+\}\}", html)))[:20]
        raise RuntimeError(f"Unresolved tokens remain, refusing to publish: {leftover}")
    if "</html>" not in html.lower():
        raise RuntimeError("Output looks truncated (no closing </html>) — refusing to publish.")
    if len(html) < 20000:
        raise RuntimeError(f"Output suspiciously short ({len(html)} chars) — refusing to publish.")


def rebuild_index() -> None:
    files = sorted(OUT_DIR.glob("*.html"), reverse=True)
    rows = "\n".join(
        f'<tr><td>{f.stem}</td><td><a href="mmm-daily/{f.name}">Open</a></td></tr>'
        for f in files
    )
    INDEX_PATH.write_text(f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Shadow Monkey — Monkey Matters LLC</title>
<style>body{{background:#080808;color:#fff;font-family:'Space Mono',monospace;padding:24px}}
a{{color:#c8ff00}} table{{border-collapse:collapse}} td{{padding:6px 14px;border-bottom:1px solid #222}}</style>
</head><body><h1>Shadow Monkey — Morning Market Monitor Archive</h1>
<table>{rows}</table></body></html>""", encoding="utf-8")


def main() -> None:
    force = os.environ.get("FORCE_RUN", "").lower() in ("true", "1")
    now = gate(force)

    if not TEMPLATE_PATH.exists():
        print(f"FATAL: {TEMPLATE_PATH} not found — template was never committed to the repo.",
              file=sys.stderr)
        sys.exit(1)
    template_html = TEMPLATE_PATH.read_text(encoding="utf-8")

    out_path = OUT_DIR / f"{now.strftime('%Y-%m-%d')}.html"
    if out_path.exists() and not force:
        print(f"{out_path} already exists — no-op (won't overwrite a real edition silently).")
        sys.exit(0)

    system, user = build_prompt(now, template_html)
    html = call_claude(system, user)
    validate(html)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    rebuild_index()

    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "sanitize.py"), str(ROOT)],
                             capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        print("SANITIZE FAILED — not committing.", file=sys.stderr)
        sys.exit(1)

    print(f"OK: wrote {out_path} ({len(html)} chars)")


if __name__ == "__main__":
    main()
