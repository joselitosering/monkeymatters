#!/usr/bin/env python3
"""
fetch_helpers.py — Pure-math utilities for the Shadow Monkey MMM pipeline.
No LLM touches these. No external imports beyond stdlib.
"""
from __future__ import annotations


def calc_pivots(high: float, low: float, close: float) -> dict:
    pp = (high + low + close) / 3.0
    r1 = 2 * pp - low
    s1 = 2 * pp - high
    r2 = pp + (high - low)
    s2 = pp - (high - low)
    r3 = high + 2 * (pp - low)
    s3 = low - 2 * (high - pp)
    return {
        "PP": round(pp, 2),
        "R1": round(r1, 2), "R2": round(r2, 2), "R3": round(r3, 2),
        "S1": round(s1, 2), "S2": round(s2, 2), "S3": round(s3, 2),
    }


def calc_rr(entry: float, stop: float, target: float, direction: str) -> float:
    try:
        if direction == "long":
            risk, reward = entry - stop, target - entry
        else:
            risk, reward = stop - entry, entry - target
        if risk <= 0 or reward <= 0:
            return 0.0
        return round(reward / risk, 2)
    except Exception:
        return 0.0


def calc_adr(highs: list, lows: list) -> float:
    if not highs or len(highs) != len(lows):
        return 0.0
    return round(sum(h - l for h, l in zip(highs, lows)) / len(highs), 2)


def normalize_fmp_quote(raw: dict) -> dict:
    return {
        "symbol":     raw.get("symbol", ""),
        "price":      raw.get("price"),
        "change":     raw.get("change"),
        "change_pct": raw.get("changesPercentage"),
        "volume":     raw.get("volume"),
        "avg_volume": raw.get("avgVolume"),
        "prev_close": raw.get("previousClose"),
        "open":       raw.get("open"),
        "day_high":   raw.get("dayHigh"),
        "day_low":    raw.get("dayLow"),
        "name":       raw.get("name", ""),
        "timestamp":  raw.get("timestamp"),
    }


def classify_regime(vix, spy_close, spy_200sma) -> str:
    if vix is None:
        return "MIXED"
    if spy_close is not None and spy_200sma is not None:
        above = spy_close > spy_200sma
        if vix < 18 and above:
            return "BULL"
        if vix > 25 and not above:
            return "BEAR"
    if vix < 18:
        return "BULL"
    if vix > 25:
        return "BEAR"
    return "CHOPPY"
