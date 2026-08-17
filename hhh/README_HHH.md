# HHH — Hedge Hog Holdings // APEX Portfolio Intel

Self-contained portfolio dashboard (APEX theme) + Schwab Trader API fetcher.
All secrets live in the repo-root `.env` (`SCHWAB_CLIENT_ID`, `SCHWAB_CLIENT_SECRET`,
optional `SCHWAB_CALLBACK_URL`, `SCHWAB_TOKEN_PATH`). Token defaults to
`.secrets/schwab_token.json` (gitignored).

## Weekly ritual (refresh token dies every ~7 days)
    py schwab_auth.py

## Map accounts (one time)
    py schwab_hhh_fetch.py --list-accounts
Fill the hashes into `hhh_config.json` accounts{}.

## Generate the dashboard
    py schwab_hhh_fetch.py --template HHH_APEX_Template.html --out HHH_Latest.html

## Data files (all gitignored — personal)
- `hhh_config.json` — account hash mapping, caps, bucket labels
- `manual_accounts.json` — credit cards, bank cash, non-Schwab sleeves (Coinbase leg lands here)
- `ratings.json` / `analysis.json` — analyst overlay (ratings, strategies, account analysis)
- `HHH_Latest.html` — generated output

## Sourcing legs
1. Schwab (6 sleeves) — LIVE via Trader API
2. Coinbase incl. staked ETH @ 2% — coming next
3. Credit cards ×4 + bank cash — manual monthly in `manual_accounts.json`
