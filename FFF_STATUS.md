# SHADOW MONKEY FFF — FRIDAY FINANCIAL FORECAST — STATUS
*Weekly product. Built 2026-08-21 by converting the session-side weekly recap
to the as-built MMM architecture. Read MMM_STATUS.md first — every decision
there (hybrid split, no LLM in CI, PAT push, PT gates, sanitize) applies
here unchanged. This doc supersedes WEEKLY_PIPELINE_HANDOFF.md (all four of
its stages are now built; kept for history).*

## Product naming (Joe, 2026-08-21)
- **MMM** — Morning Market Monitor, daily, weekday pre-market.
- **FFF** — Friday Financial Forecast, weekly, **Friday 2:10 PM PT**
  (market closes 1:00 PM PT — the run grades the completed week including
  Friday's session, then forecasts the week ahead).
- Output: `shadowmonkey/fff/fff-YYYY-Www.html` + `data/weekly/YYYY-Www.json`.
  The old one-off `shadowmonkey/mmm-weekly/weekly-recap-2026-W33.*` stays as
  archive; `shadowmonkey/index.html` now lists both products.

## The four handoff stages — where each landed
1. **Structured trade-idea records** → contract below; consumed from
   `data/daily/DATE.insert.json` (`trade_ideas` array). The W33 archive shape
   (rich nested entries) is also read via an adapter, so history stays graded.
2. **Price history cache** → `scripts/fetch_prices.py`, `data/prices/*.json`.
   Ladder: cache → FMP `/stable/historical-price-eod/full` (shape verified at
   runtime, legacy `/api/v3/historical-price-full` fallback) → Schwab
   `pricehistory` (futures + `$DXY`) → same-day bar synthesized from
   `/stable/quote` after the close (lets Friday grade Friday). Every bar
   records its `src`; cached forever, fetched once.
3. **Grading orchestration** → `scripts/fff_build.py`. Calls
   `grade_trades.grade_idea()` per idea; writes `data/outcomes/DATE.json`.
   One surgical fix landed in `grade_trades.py` (2026-08-21): a stop-out now
   grades **−1.0R** (realized risk) — previously it returned −(reward/risk),
   overstating every loss (a 1:4.5 idea graded −4.5R on a routine stop).
   Nothing else in that function changed.
4. **Weekly recap** → `template/generate_fff.py`. Week is computed (never
   hardcoded), reads `template/apex_theme.css` (singular), publishes to
   `shadowmonkey/fff/`, narrative merges from the weekly insert (below) with
   honest PENDING notices otherwise. APEX theme = the locked design system
   from the pinned artifact — layout/theme changes need Joe's explicit OK.

## Stage-1 contract — trade ideas the on-demand DAILY pass must write
Inside `data/daily/YYYY-MM-DD.insert.json`, alongside the display tokens:
```json
"trade_ideas": [
  {"id": "2026-08-24-T01", "symbol": "TLT", "instrument": "etf",
   "direction": "long", "entry_type": "price", "entry": 94.0,
   "stop": 93.0, "target": 96.5,
   "setup": "Rate-Cut Repricing", "priority": 3,
   "notes": "12K+ Sep 95C flow", "entry_raw": "above 94.00"}
]
```
Rules: `entry_type` is `"price"` (entry = numeric level) or `"market"`
(fills at first bar's open; entry may be null). `stop`/`target` MUST be
numeric levels on the same price scale the symbol's bars trade at.
Optional `bar_symbol` overrides which series grades it (e.g. a GLD idea
quoted in spot-gold points sets `"bar_symbol": "GCUSD"`). Futures ideas
(`/ES`, `/NQ`) grade ONLY on real Schwab futures bars — if the Schwab
secret is stale they grade `no_data`, never silently proxied to cash
indexes (basis error). VWAP / opening-range / PM-offset entries can't be
graded on daily bars — they come back `ungradable_v1` (visible, counted,
not dropped); intraday grading is the designated v2 upgrade.

## Weekly narrative insert — what the on-demand FFF pass writes
`data/weekly/YYYY-Www.insert.json` (Shadow Monkey persona, grounded ONLY in
that week's `data/daily/*`, `data/outcomes/*`, `data/weekly/<week>.json`):
```json
{
  "WEEK_IN_REVIEW": "prose — the week's market arc, grounded in the tracker numbers",
  "DAY_CATALYSTS": {"2026-08-24": "one-line session catalyst", "...": "..."},
  "THESIS_REVIEW": [
    {"thesis": "…", "verdict": "confirmed|refuted|mixed|unresolved", "evidence": "…"}
  ],
  "LESSONS": [
    {"rule": "imperative rule for next week's monitors", "action": "adopt|watch", "evidence": "…"}
  ],
  "FORWARD_GUIDANCE": {
    "posture": "next-week stance", "watchlist": ["…"], "key_events": ["…"]
  }
}
```
Flow every Friday: 2:10 PM data pass publishes FFF with PENDING narrative →
Joe asks Shadow Monkey for the FFF narrative in a live chat → it writes the
insert + pushes → "Run workflow" (force) merges it. Adopted LESSONS should
be echoed into the following week's daily monitors by the on-demand daily
pass — that's the learning loop closing.

## Verified in sandbox before commit (2026-08-21)
- W33 backfill end-to-end: archive-shape ideas adapted, graded (cache-only
  bars), rendered `fff-2026-W33.html` (102 KB, board + all sections).
- W34 current-week path: renders with 0 ideas, PENDING everywhere, honest
  "no structured trade ideas this week" board notice.
- Loss-R fix confirmed (−4.5R artifact → −1.0R).
- NOT yet verified (needs first real CI run, same as daily's first fire):
  FMP `/stable/historical-price-eod` live shape on Joe's key, Schwab
  pricehistory scope, quote-synth Friday bar. First run: workflow_dispatch
  force=true, week=2026-08-14, READ the diff.

## Explicitly decided
- Same zero-LLM CI + on-demand narrative split as daily (don't re-litigate).
- Friday 2:10 PM PT cadence (Joe, 2026-08-21). Cron pair + PT gate.
- File naming: `fff-YYYY-Www.html` (ISO week), chosen over date-range names.
- `data/prices` committed to the repo (the repo is the database — bars are
  fetched once, forever).
