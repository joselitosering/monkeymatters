# WEEKLY PIPELINE — HANDOFF FOR NEXT SESSION
*Start here for weekly. For daily's architecture/secrets/gotchas, read
MMM_STATUS.md first — this doc assumes that context and doesn't repeat it.*

## The one thing to understand before touching any code

**This is not "copy the daily pattern."** Daily needed no grading system;
weekly structurally does — it reports on how published trade ideas
actually performed, which requires knowing what happened to them.

## Dependency chain, build in this order

```
1. Structured trade-idea records  (shared gap with daily -- do this first)
        |
        v
2. Price history cache  (data/prices/*.json -- doesn't exist yet)
        |
        v
3. Grading orchestration  (wire grade_trades.py to #1 + #2)
        |
        v
4. Weekly recap itself  (generate_weekly.py, once #3 produces real data)
```

Do not start at #4. `generate_weekly.py` looks like the finish line but
it's downstream of everything else — there's nothing real for it to
render until #1-#3 exist.

## Stage 1 — Structured trade-idea records

**The actual root gap.** Right now, published trade ideas exist only
inside rendered HTML from the on-demand analysis pass — no clean parallel
JSON with explicit numeric `entry`/`stop`/`target`/`direction`/
`entry_type`. Nothing can grade against prose.

Fix: when the on-demand pass writes `data/daily/YYYY-MM-DD.insert.json`,
it should also include a `trade_ideas` array with that exact shape --
`grade_trades.py`'s `grade_idea()` function (already written, already
correct, read it before changing it) expects:
```
{id, instrument, direction, entry_type: "price"|"market", entry, stop, target}
```
This benefits daily too (better data hygiene for the archive), not just
weekly -- frame it that way if scoping feels weekly-only.

## Stage 2 — Price history cache

`data/prices/*.json` doesn't exist. Needed: daily OHLC bars, at minimum
for whatever `generate_weekly.py`'s `MKT` dict already names (S&P,
Nasdaq, Gold, Silver, BTC, ETH, Brent, $DXY -- see the file, don't
retype the list here) plus any instrument that shows up in a given
week's trade ideas. FMP's `/stable/quote` (confirmed working this
session, see MMM_STATUS.md) gives current price only, not history --
will need a *different* FMP endpoint (historical EOD, likely
`historical-price-eod`-family) or Alpha Vantage (key already sits in
`.env`, unused so far). Verify the real endpoint shape empirically before
building around it -- assumed endpoint names were wrong twice already
today (see SESSION_LOG_2026-08-18.md).

## Stage 3 — Grading orchestration

Net-new script. Reads a day's trade ideas (from Stage 1's output) +
relevant price bars (from Stage 2's cache), calls `grade_idea()` per
idea, writes `data/outcomes/YYYY-MM-DD.json`. `grade_trades.py` itself
needs no changes -- it's a clean pure function, already correct, just
never wired to anything.

## Stage 4 — The weekly recap

`template/generate_weekly.py` (NOTE: singular `template/`, the file's own
docstring may still say `templates/` -- that's stale, fix it) has real,
solid stats/rendering logic worth keeping. Three concrete things to fix
before it runs as automation rather than a one-off:

1. **Hardcoded week**: `WEEK = "2026-W33"`, `DAYS = [...]` are literals.
   Needs to compute the actual target week instead (Mon-Fri or
   Tue-Fri of whatever week just closed).
2. **Two stale paths**: reads `templates/apex_theme.css` -> should be
   `template/apex_theme.css`. Writes to `site/weekly/{WEEK}.html` -> should
   be `shadowmonkey/mmm-weekly/{WEEK}.html` (matching the canonical
   `YYYY-Www` or date-range naming convention -- decide which before
   building, don't default silently).
3. **Narrative sections are literal prose**, not generated. `WEEK_IN_REVIEW`,
   `NARRATIVE['thesis_review']`, `lessons_candidates`, `forward_guidance`
   are all hand-written Python string/dict literals for one specific past
   week. For ongoing automation these need the same split daily uses:
   deterministic stats stay in Python (already true here -- `stats`,
   `MKT`, `curve` etc. are all real math), narrative content becomes
   on-demand (same `.insert.json`-style mechanism, or ask Joe whether
   weekly's narrative should be a heavier or lighter lift than daily's).

## What NOT to do

Don't try to build all four stages in one pass. Daily took this many
turns to get right building *less* (no grading system at all) -- treat
each stage as its own "confirm spec, build the smallest testable piece,
run it for real, then move on" cycle, same discipline that worked all
session (see SESSION_LOG_2026-08-18.md for the specific pattern).
