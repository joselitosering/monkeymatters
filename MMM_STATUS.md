# SHADOW MONKEY MMM — STATUS
*Handoff doc. Written mid-session 2026-08-18 so a fresh session (or this
one, much later) doesn't have to rediscover anything below the hard way.*

## Architecture, as-built (not as originally spec'd)

Two independent halves, deliberately decoupled:

1. **Daily data — fully automated, GitHub Actions cron, zero LLM calls.**
   `fetch_mmm_data.py` pulls real numbers, renders the template, commits,
   pushes. Runs entirely on GitHub's servers — no dependency on this PC,
   Desktop Commander, or Claude being invoked at all.
2. **Analysis / trade ideas / lessons — on demand, live chat.** Ask
   Shadow Monkey in a session with Desktop Commander connected; it reads
   that day's `data/daily/YYYY-MM-DD.json`, writes the qualitative
   content, merges it in, pushes. Uses Max-plan chat usage, not API
   billing (Joe's explicit constraint — do not reintroduce an
   ANTHROPIC_API_KEY path without re-confirming this).

This replaced the original design (a single Claude *scheduled task* doing
everything) after finding it structurally broken: Cowork scheduled tasks
run remotely with no local-machine access, but the original plan needed
Desktop Commander to push to git — those two requirements can't coexist.
**If a "Daily MMM" / "Weekly Recap" Cowork scheduled task still shows up
under Scheduled in the sidebar, it's a dead remnant of that abandoned
design — delete it, don't try to fix it.**

## Confirmed live and working (2026-08-18)

- Daily fetch/render/sanitize/commit/push validated end-to-end on GitHub's
  actual infrastructure: 15s total job duration.
- Data sources, all confirmed by live call, not assumed from docs:
  - **FMP**: `https://financialmodelingprep.com/stable/quote?symbol=X` —
    the ONE real endpoint. The FMP MCP tool's endpoint names
    (`index-quote`, `cryptocurrency-quote-short`, etc.) are an internal
    MCP abstraction, NOT real URL paths — hitting them directly 404s.
    Covers VIX (`^VIX`), SPX (`^GSPC`), Gold (`GCUSD`), BTC (`BTCUSD`),
    ETH (`ETHUSD`).
  - **Schwab** (optional, upgrades ES/NQ from cash-index proxy to real
    futures): `marketdata/v1/quotes?symbols=/ES,/NQ` on the Market Data
    scope. `/ES` auto-resolves to the correct front-month contract, no
    manual roll logic needed. Separate scope from Accounts (which HHH's
    own notes already flagged as blocked) — Market Data works fine.
- `shadowmonkey/` is the sole public folder (Pages publishes only this,
  via `path: shadowmonkey` in `pages-deploy.yml`). Contains `index.html`,
  `mmm-daily/`, `mmm-weekly/`. Everything else in the repo (`hhh/`,
  `turtleshell/`, `scripts/`, `data/`, `template/`) is NOT published.

## Gotchas found, fixed, worth knowing before touching this again

- **`.env` is UTF-8-sig, not UTF-16** despite an earlier note in
  HHH_STATUS.md suggesting otherwise — confirmed empirically.
- **`sanitize.py` was flagging its own source file** — its `FORBIDDEN`
  regex list contains the pattern strings themselves as literal text
  (the ticker-cost-basis forbidden-pattern literal matched itself). Excluded its own path from the
  scan. Zero actual leak, ever.
- **Commit messages using `date -u` vs. Python's Pacific-time logic**
  drift a day apart every evening after ~5-6pm PT (past midnight UTC).
  Fixed in `mmm-daily.yml` to use `TZ='America/Los_Angeles' date`. Apply
  the same fix to any new workflow that stamps a date in a commit message
  — including whatever gets built for weekly.
- **Schwab OAuth "password rejected" was actually a `SCHWAB_CALLBACK_URL`
  mismatch** (script defaulted to `:8182`, registered app had no port).
  Fixed via `.env` override. Not a credentials problem if it recurs —
  check the registered callback URL first.
- Pushes from Actions MUST use `SHADOW_MONKEY_PAT` (a real PAT), not the
  default `GITHUB_TOKEN` — GitHub's loop-prevention means default-token
  pushes don't trigger `pages-deploy.yml`.

## Secrets / config reference (names only, never values)

GitHub repo secrets: `SHADOW_MONKEY_PAT`, `FMP_API_KEY`, optionally
`SCHWAB_CLIENT_ID` / `SCHWAB_CLIENT_SECRET` / `SCHWAB_REFRESH_TOKEN`
(the last one dies ~7 days, needs `schwab_auth.py` re-run + secret update
on that cadence — no way to make this self-heal in CI).
Local `.env` mirrors the FMP/Schwab values for `fetch_mmm_data.py`'s
local-test fallback path (checks real env vars first, `.env` second).

## Explicitly decided, don't re-litigate

- No separate Anthropic API billing for automation (Max plan covers
  on-demand chat use instead).
- Google Drive queue sync (`mmm_sync.py` etc.) — deleted, confirmed
  remnant, not coming back.
- Detaching the on-demand analysis step from this machine — considered,
  not pursued (current on-demand-from-chat flow is sufficient for now).
- `docs/` (`v_4_*.html` files) — explicitly NOT part of the public
  `shadowmonkey/` folder. Joe said he'll address later; don't move them.
- Dashboard for monitoring/triggering — GitHub's native Actions tab
  already serves this (run history, status, duration, on-demand "Run
  workflow" button). Not building a custom one unless that changes.

## In progress / next

- **Weekly pipeline — scoped, not yet built.** Turns out to be a bigger
  lift than daily was: needs structured trade-idea logging, a price-
  history cache, and a grading orchestration layer *before* the recap
  itself can run on real data. Full dependency chain, exact files, exact
  fixes needed: **see `WEEKLY_PIPELINE_HANDOFF.md`** — start there, not
  from scratch. Process lessons from building daily (what worked, what
  didn't): `SESSION_LOG_2026-08-18.md`.
- On-demand insert merge is still manual (I read the JSON, write content,
  push via Desktop Commander) — no helper script exists yet. Fine as a
  process; flag if it becomes worth automating.


## 2026-09-02 — Futures Intelligence tables are now pipeline-filled

- `fetch_schwab_profile()` pulls Schwab price history per contract: daily bars
  (prev H/L/settle, classic pivots, 5-day ADR, ATR-20 N, 2N/0.5N, Donchian
  20/55 with live-price status) and 1-minute bars for the last completed RTH
  session (09:30-16:00 ET) -> 70% value area VAH/POC/VAL, VWAP, volume.
- `build_futures_stats_rows()` renders the /ES and /NQ tables. These take
  PRECEDENCE over the analysis insert: /ES STATS and /NQ STATS keys in an
  insert are no-ops once the pipeline has filled them. Analysis belongs in the
  CA_* blocks, not in hand-typed tables. FMP cash-index proxies are no longer
  used for these tables.
- Profile data is persisted under `schwab_futures.<ES|NQ>.profile` in the
  daily data JSON for audit.
- Volume-profile method: each 1-min bar's volume spread across the price bins
  its range touches (ES 1-pt bins, NQ 5-pt); value area expanded from POC by
  the larger neighbouring pair (CBOT Market Profile method).
