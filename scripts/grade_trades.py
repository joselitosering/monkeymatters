#!/usr/bin/env python3
"""
grade_trades.py — Deterministic trade idea grading from OHLCV bar data.
Pure math. No LLM. See comments for entry_type and result enum definitions.
"""
from __future__ import annotations


def _outcome(bars, entry_idx, stop, target, direction):
    for i, bar in enumerate(bars[entry_idx + 1:], start=entry_idx + 1):
        h, l = bar.get("high", 0.0), bar.get("low", 0.0)
        hit_stop   = (l <= stop)   if direction == "long" else (h >= stop)
        hit_target = (h >= target) if direction == "long" else (l <= target)
        if hit_stop and hit_target:
            return dict(result="indeterminate", exit_reason="indeterminate",
                        r_multiple=None, exit_bar=i)
        entry_px = bars[entry_idx].get("open", bars[entry_idx].get("close", 0))
        if hit_target:
            risk = abs(entry_px - stop)
            r = round(abs(target - entry_px) / risk, 2) if risk > 0 else None
            return dict(result="win", exit_reason="target", r_multiple=r, exit_bar=i)
        if hit_stop:
            # FIX 2026-08-21 (FFF wiring): a stopped trade realizes exactly
            # -1R (loss = the risk you defined), NOT -(reward/risk) — the
            # old line returned the planned R:R as a negative, overstating
            # every loss (e.g. a 1:4.5 idea graded -4.5R on a routine stop).
            return dict(result="loss", exit_reason="stop", r_multiple=-1.0, exit_bar=i)
    return dict(result="indeterminate", exit_reason="indeterminate",
                r_multiple=None, exit_bar=None)


def grade_idea(idea: dict, bars: list) -> dict:
    iid       = idea.get("id", "unknown")
    sym       = idea.get("instrument", "")
    direction = idea.get("direction", "long")
    etype     = idea.get("entry_type", "price")
    entry     = idea.get("entry")
    stop      = idea.get("stop")
    target    = idea.get("target")

    base = dict(id=iid, symbol=sym)

    if not bars:
        return {**base, "result":"no_data","triggered":False,
                "r_multiple":None,"exit_reason":"n/a","exit_bar":None,"notes":["no bar data"]}
    if stop is None or target is None:
        return {**base, "result":"indeterminate","triggered":False,
                "r_multiple":None,"exit_reason":"indeterminate","exit_bar":None,
                "notes":["missing stop or target"]}

    if etype == "market":
        out = _outcome(bars, 0, stop, target, direction)
        return {**base, "triggered":True, **out, "notes":["market: open fill"]}

    if entry is None:
        return {**base, "result":"indeterminate","triggered":False,
                "r_multiple":None,"exit_reason":"indeterminate","exit_bar":None,
                "notes":["entry level missing"]}

    entry_idx = None
    for i, bar in enumerate(bars):
        h, l = bar.get("high", 0.0), bar.get("low", 0.0)
        if l <= entry <= h:
            entry_idx = i
            break

    if entry_idx is None:
        return {**base, "result":"no_trigger","triggered":False,
                "r_multiple":None,"exit_reason":"n/a","exit_bar":None,"notes":[]}

    bar = bars[entry_idx]
    h_e, l_e = bar.get("high", 0.0), bar.get("low", 0.0)
    stop_in   = (l_e <= stop)   if direction == "long" else (h_e >= stop)
    target_in = (h_e >= target) if direction == "long" else (l_e <= target)
    if stop_in and target_in:
        return {**base, "result":"indeterminate","triggered":True,
                "r_multiple":None,"exit_reason":"indeterminate","exit_bar":entry_idx,
                "notes":["stop+target within entry bar"]}

    out = _outcome(bars, entry_idx, stop, target, direction)
    return {**base, "triggered":True, **out, "notes":[]}
