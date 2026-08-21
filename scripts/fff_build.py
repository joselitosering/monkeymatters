#!/usr/bin/env python3
"""
fff_build.py — FRIDAY FINANCIAL FORECAST (FFF), data-pass orchestrator.
Stages 3+4 of WEEKLY_PIPELINE_HANDOFF.md, wired to Stage 1 (structured
trade-idea records, see FFF_STATUS.md contract) and Stage 2 (fetch_prices).

Same hybrid doctrine as the daily MMM (MMM_STATUS.md — read it first):
  - THIS script: zero LLM calls. Computes the target week, collects the
    week's published trade ideas, ensures price bars, grades every idea
    with scripts/grade_trades.grade_idea() (unchanged, pure math), writes
    data/outcomes/YYYY-MM-DD.json, computes all stats, renders the FFF
    page with real numbers — narrative sections show honest PENDING
    markers unless data/weekly/YYYY-Www.insert.json exists.
  - ON-DEMAND pass (live Shadow Monkey chat, Max-plan usage, no API key):
    reads the week's dailies + outcomes, writes the narrative insert
    (week-in-review, thesis review, lessons, forecast, next-week ideas),
    then this workflow re-runs (manual "Run workflow") and merges it.

Fires Friday 2:10 PM PT (market closed 1:00 PM PT; Friday's own session
grades same-day via fetch_prices' quote-synth bar if EOD history lags).
"""
from __future__ import annotations
import os, sys, json, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "template"))

from grade_trades import grade_idea            # unchanged, pure — see handoff
from fetch_prices import ensure_bars, key_for, TRACKER_SYMBOLS

PT = ZoneInfo("America/Los_Angeles")
DATA_DAILY = ROOT / "data" / "daily"
DATA_OUT = ROOT / "data" / "outcomes"
TARGET_HOUR, TARGET_MIN, WINDOW_MIN = 14, 10, 25   # Fri 2:10 PM PT ± window


# ─────────────────────────────────────────────── gate & week computation
def gate(force: bool) -> datetime.datetime:
    now = datetime.datetime.now(PT)
    if force:
        print(f"FORCE_RUN set — skipping gate. Now: {now.isoformat()}")
        return now
    if now.weekday() != 4:
        print(f"Not Friday ({now.strftime('%A')}) — no-op. "
              f"(DST-mirror cron fires twice; the PT gate picks the right one.)")
        sys.exit(0)
    target = now.replace(hour=TARGET_HOUR, minute=TARGET_MIN, second=0, microsecond=0)
    delta_min = abs((now - target).total_seconds()) / 60
    if delta_min > WINDOW_MIN:
        print(f"Outside Friday 2:10 PM PT window (now {now.strftime('%H:%M %Z')}) — no-op.")
        sys.exit(0)
    print(f"In window: {now.isoformat()}")
    return now


def target_week(now: datetime.datetime) -> tuple[str, list[str]]:
    """The Mon–Fri week being recapped. On Friday that's the current week;
    on any other (forced) day, the most recently completed Mon–Fri."""
    d = now.date()
    if d.weekday() != 4:                       # forced off-Friday run
        d = d - datetime.timedelta(days=(d.weekday() - 4) % 7)
    monday = d - datetime.timedelta(days=4)
    days = [(monday + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
    iso = monday.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}", days


# ─────────────────────────────────────────────── idea collection + adapter
def _load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def collect_ideas(days: list[str]) -> dict[str, list[dict]]:
    """Per-day list of RAW idea dicts. Contract shape lives in the daily
    .insert.json (Stage 1); the W33 archive kept them in the base daily
    file — both are read so history stays graded."""
    out = {}
    for d in days:
        ideas = []
        base = _load_json(DATA_DAILY / f"{d}.json") or {}
        ins = _load_json(DATA_DAILY / f"{d}.insert.json") or {}
        for src in (ins, base):
            if isinstance(src.get("trade_ideas"), list):
                ideas = src["trade_ideas"]
                break
        out[d] = ideas
    return out


def normalize_idea(raw: dict, date: str, n: int) -> tuple[dict | None, dict]:
    """-> (flat idea for grade_idea() or None, display record).
    Flat contract passes through; the W33 rich shape converts where its
    entry resolves to a price; everything else is ungradable_v1 — visible,
    never silently dropped."""
    disp = {
        "id": raw.get("id") or f"{date}-T{n:02d}",
        "symbol": raw.get("symbol", "?"),
        "instrument": raw.get("instrument", "?"),
        "direction": raw.get("direction", "neutral"),
        "setup": raw.get("setup", ""),
        "priority": raw.get("priority", 1),
        "notes": (raw.get("notes") or "")[:120],
        "entry_raw": "",
    }
    e = raw.get("entry")
    if isinstance(e, (int, float)) or e is None:          # flat contract
        etype = raw.get("entry_type", "price" if e is not None else "market")
        disp["entry_raw"] = raw.get("entry_raw") or (f"{e}" if e is not None else "market")
        if not isinstance(raw.get("stop"), (int, float)) or not isinstance(raw.get("target"), (int, float)):
            return None, {**disp, "why": "missing numeric stop/target"}
        flat = {"id": disp["id"], "instrument": disp["symbol"], "direction": disp["direction"],
                "entry_type": etype, "entry": e, "stop": raw["stop"], "target": raw["target"]}
        return flat, disp
    if isinstance(e, dict):                                # W33 archive shape
        disp["entry_raw"] = e.get("raw") or str(e.get("value") or "")
        stop, targ = raw.get("stop") or {}, raw.get("target") or {}
        if e.get("type") == "price" and stop.get("type") == "price" and targ.get("type") == "price":
            flat = {"id": disp["id"], "instrument": disp["symbol"], "direction": disp["direction"],
                    "entry_type": "price", "entry": e.get("value"),
                    "stop": stop.get("value"), "target": targ.get("value")}
            return flat, disp
        return None, {**disp, "why": f"entry type '{e.get('type')}' needs intraday grading (v2)"}
    return None, {**disp, "why": "unrecognized idea shape"}


def bar_symbol_for(disp: dict, raw: dict) -> str | None:
    """Which price series grades this idea. Contract may override with
    'bar_symbol'. /ES //NQ require real Schwab futures bars — no silent
    cash-index proxying of futures point levels (basis error)."""
    if raw.get("bar_symbol"):
        return raw["bar_symbol"]
    sym = disp["symbol"].strip()
    if sym.startswith("/"):
        return sym                                          # Schwab futures route
    # W33 quirk: GLD ideas quoted in spot-gold points
    v = raw.get("entry") if isinstance(raw.get("entry"), (int, float)) else \
        (raw.get("entry") or {}).get("value") if isinstance(raw.get("entry"), dict) else None
    if sym.upper() == "GLD" and v and v > 2000:
        return "GCUSD"
    return sym.upper()


# ─────────────────────────────────────────────── grading orchestration
def grade_week(days: list[str], ideas_by_day: dict) -> None:
    frm, to = days[0], days[-1]
    symbols = [s for d in days for s in
               {bar_symbol_for(*_norm_pair(r, d, i)) for i, r in enumerate(ideas_by_day[d], 1)}
               if s]
    bars_by_key = ensure_bars(TRACKER_SYMBOLS + symbols, frm, to)

    for d in days:
        raws = ideas_by_day[d]
        results = []
        for i, raw in enumerate(raws, 1):
            flat, disp = normalize_idea(raw, d, i)
            if flat is None:
                results.append({**disp, "result": "ungradable_v1", "triggered": False,
                                "r_multiple": None, "exit_reason": "n/a",
                                "notes": [disp.pop("why", "")]})
                continue
            key = key_for(bar_symbol_for(disp, raw))
            bars = [b for b in bars_by_key.get(key, []) if d <= b["date"] <= to]
            graded = grade_idea(flat, bars)
            graded["symbol"] = disp["symbol"]               # grade_idea echoes instrument
            results.append({**disp, **graded,
                            "evidence": {"bars_key": key, "bars_used": len(bars),
                                         "bars_src": sorted({b.get("src", "cache") for b in bars})}})
        wins = sum(1 for r in results if r["result"] == "win")
        losses = sum(1 for r in results if r["result"] == "loss")
        summary = dict(
            ideas_total=len(results), wins=wins, losses=losses,
            no_trigger=sum(1 for r in results if r["result"] == "no_trigger"),
            indeterminate=sum(1 for r in results if r["result"] == "indeterminate"),
            no_data=sum(1 for r in results if r["result"] == "no_data"),
            ungradable=sum(1 for r in results if r["result"] == "ungradable_v1"),
            win_rate=round(wins / max(1, wins + losses), 3),
            total_r=round(sum(r.get("r_multiple") or 0 for r in results
                              if r["result"] in ("win", "loss")), 2))
        DATA_OUT.mkdir(parents=True, exist_ok=True)
        (DATA_OUT / f"{d}.json").write_text(json.dumps(dict(
            schema_version=2, date=d,
            graded_at=datetime.datetime.now(PT).isoformat(timespec="seconds"),
            grader="fff_build@v1 + grade_trades.grade_idea (daily bars)",
            results=results, day_summary=summary), indent=2), encoding="utf-8")
        print(f"graded {d}: {summary}")


def _norm_pair(raw, d, i):
    flat, disp = normalize_idea(raw, d, i)
    return disp, raw


# ─────────────────────────────────────────────── main
def main() -> None:
    force = os.environ.get("FORCE_RUN", "").lower() in ("true", "1")
    now = gate(force)
    week_override = os.environ.get("FFF_WEEK", "")         # e.g. "2026-08-14" -> that week
    if week_override:
        now = datetime.datetime.strptime(week_override, "%Y-%m-%d").replace(tzinfo=PT)
        print(f"FFF_WEEK override -> recapping week of {week_override}")
    week, days = target_week(now)
    have_days = [d for d in days if (DATA_DAILY / f"{d}.json").exists()
                 or (DATA_DAILY / f"{d}.insert.json").exists()]
    print(f"Target {week}: {days} | daily records present: {have_days}")
    if not have_days:
        print("No daily records for this week at all — nothing to recap. No-op.")
        sys.exit(0)

    ideas = collect_ideas(days)
    n_ideas = sum(len(v) for v in ideas.values())
    print(f"Trade ideas found: {n_ideas} across {sum(1 for v in ideas.values() if v)} day(s)")
    grade_week(days, ideas)

    from generate_fff import build_fff                     # template/generate_fff.py
    out = build_fff(week, days)
    print(f"OK: FFF rendered -> {out}")


if __name__ == "__main__":
    main()
