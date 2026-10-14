# -*- coding: utf-8 -*-
import json, re
from pathlib import Path

ROOT = Path(r"D:\Apps\DevOps\Github\monkeymatters")
TPL_PATH = ROOT / "template" / "mmm_template.html"
OUT_PATH = ROOT / "data" / "daily" / "2026-10-12.insert.json"

tpl = TPL_PATH.read_text(encoding="utf-8")
print("template length:", len(tpl))

# ---------------------------------------------------------------
# Locate the 4 ambiguous analysis blocks (ES, NQ, ECON, EARNINGS)
# ---------------------------------------------------------------
ca_positions = []
pos = 0
while True:
    i = tpl.find('<div class="ca">', pos)
    if i == -1:
        break
    ca_positions.append(i)
    pos = i + 1
print("plain <div class=\"ca\"> occurrences:", ca_positions)
assert len(ca_positions) == 4, f"expected 4, got {len(ca_positions)}"
es_ca_pos, nq_ca_pos, econ_ca_pos, earn_ca_pos = ca_positions

VWAP_MARK = 'VWAP: {{VWAP}}</span>'
TAIL = '</div></div></div>\n</div>'

def extract_block(start_idx, label):
    vwap_idx = tpl.index(VWAP_MARK, start_idx)
    after = vwap_idx + len(VWAP_MARK)
    end = after + len(TAIL)
    got = tpl[after:end]
    assert got == TAIL, f"TAIL mismatch for {label}: {got!r}"
    return tpl[start_idx:end]

es_simple_anchor = 'E-Mini S&amp;P 500 \u00b7 {{PREV_DATE_SHORT}} Settlement</div>'
nq_simple_anchor = 'E-Mini Nasdaq-100 \u00b7 {{PREV_DATE_SHORT}} Settlement</div>'
es_anchor_idx = tpl.index(es_simple_anchor)
nq_anchor_idx = tpl.index(nq_simple_anchor)
es_start = tpl.rindex('<div class="card-hd">', 0, es_anchor_idx)
nq_start = tpl.rindex('<div class="card-hd">', 0, nq_anchor_idx)

es_block = extract_block(es_start, "ES")
nq_block = extract_block(nq_start, "NQ")
econ_block = extract_block(econ_ca_pos, "ECON")
earn_block = extract_block(earn_ca_pos, "EARNINGS")

for name, b in [("ES", es_block), ("NQ", nq_block), ("ECON", econ_block), ("EARN", earn_block)]:
    print(f"--- {name} block len={len(b)} ---")
    print(b[:90].replace(chr(10), "\\n"))
    print("...")
    print(b[-60:].replace(chr(10), "\\n"))
    cnt = tpl.count(b)
    print(f"{name} block count_in_template =", cnt)
    assert cnt == 1, f"{name} marker not unique: count={cnt}"

print("ALL 4 MARKERS VERIFIED UNIQUE (count==1 each).")

# ---------------------------------------------------------------
# Helpers to fill a block's tokens / comments
# ---------------------------------------------------------------
def fill_tokens(block, mapping, label):
    out = block
    for k, v in mapping.items():
        tok = "{{%s}}" % k
        cnt = out.count(tok)
        if cnt != 1:
            raise SystemExit(f"{label}: token {tok} count={cnt} (expected 1)")
        out = out.replace(tok, v)
    return out

def replace_comment(block, comment_lead, replacement, label):
    start = block.index(comment_lead)
    end = block.index("-->", start) + 3
    cnt = block.count(block[start:end])
    if cnt != 1:
        raise SystemExit(f"{label}: comment not unique")
    return block[:start] + replacement + block[end:]

# ---------------------------------------------------------------
# BTC / ETH real daily closes (FMP cryptocurrency-historical-price-eod-light,
# fetched this session) - used to compute SMA20 / swing levels in code,
# never hand-typed price targets.
# ---------------------------------------------------------------
btc_hist = [
    ("2026-10-11", 83678.29), ("2026-10-10", 82910.80), ("2026-10-09", 82544.71),
    ("2026-10-08", 81692.79), ("2026-10-07", 83275.06), ("2026-10-06", 85539.77),
    ("2026-10-05", 85748.96), ("2026-10-04", 86507.11), ("2026-10-03", 84742.22),
    ("2026-10-02", 84504.88), ("2026-10-01", 84848.73), ("2026-09-30", 83556.14),
    ("2026-09-29", 83638.42), ("2026-09-28", 83456.74), ("2026-09-27", 84462.14),
    ("2026-09-26", 84416.65), ("2026-09-25", 84093.13), ("2026-09-24", 84385.46),
    ("2026-09-23", 84378.31), ("2026-09-22", 86198.05),
]
eth_hist = [
    ("2026-10-11", 2534.22), ("2026-10-10", 2503.86), ("2026-10-09", 2485.23),
    ("2026-10-08", 2472.89), ("2026-10-07", 2572.80), ("2026-10-06", 2697.28),
    ("2026-10-05", 2709.60), ("2026-10-04", 2726.66), ("2026-10-03", 2686.83),
    ("2026-10-02", 2668.13), ("2026-10-01", 2705.50), ("2026-09-30", 2683.93),
    ("2026-09-29", 2677.06), ("2026-09-28", 2687.41), ("2026-09-27", 2688.23),
    ("2026-09-26", 2695.53), ("2026-09-25", 2691.40), ("2026-09-24", 2687.28),
    ("2026-09-23", 2683.88), ("2026-09-22", 2753.38),
]
btc_vals = [v for _, v in btc_hist]
eth_vals = [v for _, v in eth_hist]
btc_sma20 = round(sum(btc_vals) / len(btc_vals), 2)
eth_sma20 = round(sum(eth_vals) / len(eth_vals), 2)
btc_swing_low = round(min(btc_vals), 2)
eth_swing_low = round(min(eth_vals), 2)
btc_swing_high = round(max(btc_vals), 2)
eth_swing_high = round(max(eth_vals), 2)
print("BTC sma20=", btc_sma20, "swing_low=", btc_swing_low, "swing_high=", btc_swing_high)
print("ETH sma20=", eth_sma20, "swing_low=", eth_swing_low, "swing_high=", eth_swing_high)

btc_entry = 82000.0
btc_stop = round(btc_swing_low - 500, 2)
btc_target = btc_sma20
btc_rr = round((btc_target - btc_entry) / (btc_entry - btc_stop), 1)

eth_entry = 2500.0
eth_stop = round(eth_swing_low - 30, 2)
eth_target = eth_sma20
eth_rr = round((eth_target - eth_entry) / (eth_entry - eth_stop), 1)

ccc_entry = 7.69
ccc_stop = 7.00
ccc_target = 8.50
ccc_rr = round((ccc_target - ccc_entry) / (ccc_entry - ccc_stop), 1)
print("BTC idea:", btc_entry, btc_stop, btc_target, btc_rr)
print("ETH idea:", eth_entry, eth_stop, eth_target, eth_rr)
print("CCC idea:", ccc_entry, ccc_stop, ccc_target, ccc_rr)

# ---------------------------------------------------------------
# /ES and /NQ block content
# ---------------------------------------------------------------
NA = "N/A"

es_stats_rows = (
    '<tr><td>SPX cash (FMP, live)</td><td class="acc">7,815.51 (+0.05%)</td></tr>'
    '<tr><td>Fri settle (SPX cash)</td><td class="acc">7,811.54</td></tr>'
    '<tr><td>52-wk high (SPX cash)</td><td class="acc">7,844.52</td></tr>'
    '<tr><td>Yahoo /ES premkt snapshot</td><td class="good">7,861.25 (+1.50 / +0.02%)</td></tr>'
    '<tr class="ftbl-sub"><td colspan="2">— Pivot / Volume Profile —</td></tr>'
    '<tr><td>Status</td><td class="bad">UNAVAILABLE — Schwab refresh token stale (HTTP 400)</td></tr>'
    '<tr><td>Action</td><td class="warn">No re-mint attempted — needs Joe’s live OAuth; flagged below</td></tr>'
)
es_analysis = (
    "No real Schwab futures print today — the refresh token is stale (HTTP 400 on this "
    "morning’s OAuth call, confirmed in the data-pass log; schwab_futures came back {} in "
    "data/daily/2026-10-12.json). Working off cash-index and sourced snapshots instead: SPX cash "
    "(FMP) is at 7,815.51, essentially flat (+0.05%) just above Friday’s 7,811.54 settle and "
    "within 0.4% of the 7,844.52 52-week high. Yahoo Finance’s live blog had /ES around "
    "7,861.25 (+0.02%) in early trade. Per the weekend desk read, ES reclaimed its daily 20/50-MA "
    "cluster last week and is consolidating in the upper half of its ascending channel off the "
    "April 2025 lows, with ~7,736 flagged as the support to lose. No real pivots/VAH/POC/VAL today — "
    "don’t trust any precise intraday level you see elsewhere until the feed is back."
)
es_spec = (
    "Bond markets are closed for Columbus Day and there’s no U.S. econ data today, so the "
    "swing factor is geopolitical: a confirmed/escalated U.S.-Saudi response to the Houthi strike "
    "on Riyadh’s airport is the biggest risk-premium driver for /ES into the close. A holding "
    "Russia-Ukraine energy-infrastructure truce is the offsetting bull case for a push at 7,844.52."
)
es_trade = (
    "No sized /ES idea today — the data to grade one (real settlement, VAH/POC/VAL, 1-min RTH "
    "bars) isn’t flowing. Watching the SPX cash reaction at 7,844.52 / 7,736 into tomorrow’s "
    "bank-earnings open instead of forcing a futures entry blind."
)
es_strategy = (
    "Stand aside on /ES until the Schwab token is re-minted — that needs Joe’s live OAuth, "
    "not something this pipeline can self-heal. Trading the cash/ETF proxy instead: respect 7,736 "
    "as the line in the sand, 7,844.52 as the level that matters on a breakout attempt."
)

es_filled = replace_comment(
    es_block,
    "<!-- INJECT: /ES STATS",
    es_stats_rows,
    "ES-STATS",
)
es_filled = fill_tokens(es_filled, {
    "CA_ANALYSIS": es_analysis,
    "CA_SPEC_MOVE": es_spec,
    "CA_TRADE_IDEA": es_trade,
    "CA_STRATEGY": es_strategy,
    "ENTRY": NA, "STOP": NA, "TARGET": NA,
    "S_ENTRY": NA, "S_STOP": NA, "S_TARGET": NA,
    "PIVOT": NA, "VWAP": NA,
}, "ES")
print("ES filled len:", len(es_filled))

# ---------------------------------------------------------------
# /NQ block content
# ---------------------------------------------------------------
nq_stats_rows = (
    '<tr><td>Yahoo /NQ premkt snapshot</td><td class="bad">31,036.00 (-72.75 / -0.23%)</td></tr>'
    '<tr><td>NDX cash quote</td><td class="warn">Not sourced — gated on current FMP tier</td></tr>'
    '<tr><td>Desk context (wk ahead)</td><td class="acc">NDX record close ~30,660 area last wk*</td></tr>'
    '<tr class="ftbl-sub"><td colspan="2">— Pivot / Volume Profile —</td></tr>'
    '<tr><td>Status</td><td class="bad">UNAVAILABLE — Schwab refresh token stale (HTTP 400)</td></tr>'
    '<tr><td>Action</td><td class="warn">No re-mint attempted — needs Joe’s live OAuth; flagged below</td></tr>'
)
nq_analysis = (
    "Same Schwab outage hits /NQ — schwab_futures is empty in today’s JSON (refresh token "
    "stale, HTTP 400). No independent NDX cash quote was available on today’s FMP tier either, "
    "so the only real NQ-adjacent print is Yahoo Finance’s live-blog /NQ snapshot: ~31,036.00, "
    "down 72.75 (-0.23%) in early trade — mixed versus /ES’s flat-to-firm tape. *Desk context: "
    "weekend sourcing put Nasdaq-100 near a ~30,660 record-area close last week, with the SOX "
    "semiconductor index down 4.3% on the week still weighing on tech leadership. No real "
    "pivots/VAH/POC/VAL today."
)
nq_spec = (
    "Another weak SOX print or soft AI-capex commentary ahead of tomorrow’s bank earnings "
    "could extend the Nasdaq’s 30-straight-session streak of more new 52-week lows than highs. "
    "A ‘good news is bad news’ yield spike off strong bank numbers would hit duration-"
    "sensitive tech hardest."
)
nq_trade = (
    "No sized /NQ idea today for the same data reason as /ES — won’t force a futures trade "
    "without real tick data."
)
nq_strategy = (
    "Stand aside on /NQ until Schwab is restored. If trading NDX-linked equities/ETFs, watch for "
    "SOX stabilization as the tell that tech leadership — and breadth — is actually turning, "
    "not just price."
)

nq_filled = replace_comment(
    nq_block,
    "<!-- INJECT: /NQ STATS",
    nq_stats_rows,
    "NQ-STATS",
)
nq_filled = fill_tokens(nq_filled, {
    "CA_ANALYSIS": nq_analysis,
    "CA_SPEC_MOVE": nq_spec,
    "CA_TRADE_IDEA": nq_trade,
    "CA_STRATEGY": nq_strategy,
    "ENTRY": NA, "STOP": NA, "TARGET": NA,
    "S_ENTRY": NA, "S_STOP": NA, "S_TARGET": NA,
    "PIVOT": NA, "VWAP": NA,
}, "NQ")
print("NQ filled len:", len(nq_filled))

# ---------------------------------------------------------------
# Econ Calendar .ca block (Analysis, Spec Move, Trade Idea, Levels)
# ---------------------------------------------------------------
econ_analysis = (
    "Today is thin by design: Columbus Day closes the U.S. bond market (SIFMA recommendation) "
    "while equities trade full hours, and there’s no scheduled U.S. econ release. The real "
    "calendar risk is mid-week — September CPI Wednesday, then PPI and retail sales Thursday — "
    "with the 10-year yield already at 5.24% (up from 5.22% Wednesday-prior) and 5.40% flagged "
    "as resistance for the week."
)
econ_spec = (
    "Thin bond liquidity today raises the odds of an exaggerated futures/rates reaction to any "
    "geopolitical headline (Houthi/Saudi escalation, oil) that active two-way bond flow would "
    "otherwise dampen."
)
econ_trade = "No econ-data trade today — nothing scheduled to trade around. Save the ammo for Wednesday’s CPI."

econ_filled = fill_tokens(econ_block, {
    "CA_ANALYSIS": econ_analysis,
    "CA_SPEC_MOVE": econ_spec,
    "CA_TRADE_IDEA": econ_trade,
    "ENTRY": NA, "STOP": NA, "TARGET": NA,
    "S_ENTRY": NA, "S_STOP": NA, "S_TARGET": NA,
    "PIVOT": NA, "VWAP": NA,
}, "ECON")
print("ECON filled len:", len(econ_filled))

# ---------------------------------------------------------------
# Earnings Watch .ca block (Analysis, Trade Idea, Levels)
# ---------------------------------------------------------------
earn_analysis = (
    "Nothing reports today. Tomorrow (Tue 10/13, all BMO) is the real test: JPMorgan, Goldman "
    "Sachs, Wells Fargo and Citi open bank-earnings season, with Johnson &amp; Johnson and "
    "UnitedHealth also out. Sell-side commentary cited ~30% aggregate EPS growth for the quarter, "
    "though described as highly concentrated — a soft bank print would hit the ‘earnings "
    "can keep funding these valuations’ thesis directly."
)
earn_trade = (
    "No earnings trade today. Into tomorrow’s open: banks are a sentiment tell for the whole "
    "tape, not just financials — a credit-quality miss or weak NII guide from JPM/WFC would "
    "compound the Nasdaq’s already-weak breadth."
)

earn_filled = fill_tokens(earn_block, {
    "CA_ANALYSIS": earn_analysis,
    "CA_TRADE_IDEA": earn_trade,
    "ENTRY": NA, "STOP": NA, "TARGET": NA,
    "S_ENTRY": NA, "S_STOP": NA, "S_TARGET": NA,
    "PIVOT": NA, "VWAP": NA,
}, "EARN")
print("EARN filled len:", len(earn_filled))

# ---------------------------------------------------------------
# S06 ECON CALENDAR rows (table, outside the .ca div)
# ---------------------------------------------------------------
econ_cal_marker_lead = "<!-- INJECT: S06 ECON CALENDAR"
econ_cal_rows = (
    '<tr><td>ALL DAY</td><td><strong>Columbus Day</strong> <span class="chk">✓ bond mkt closed (SIFMA)</span></td>'
    '<td>—</td><td class="c-warn">Equities trade normal hours</td></tr>'
    '<tr><td>—</td><td><strong>No U.S. econ data today</strong></td>'
    '<td>CPI Wed / PPI + Retail Sales Thu</td><td class="c-sub">—</td></tr>'
)

# ---------------------------------------------------------------
# S06 EARNINGS WATCH rows
# ---------------------------------------------------------------
earn_watch_marker_lead = "<!-- INJECT: S06 EARNINGS WATCH"
earn_rows_data = [
    ("JPM", "EPS Est. $5.93", "Rev est. $51.23B — bank-earnings season opener"),
    ("GS", "EPS Est. $12.86", "Rev est. $16.83B"),
    ("WFC", "EPS Est. $1.85", "Rev est. $22.31B"),
    ("C", "EPS Est. $2.65", "Rev est. $23.72B"),
    ("JNJ", "EPS Est. $2.52", "Rev est. $25.38B"),
    ("UNH", "EPS Est. $4.14", "Rev est. $111.31B"),
]
earn_rows = "".join(
    f'<tr><td>{t}</td><td><span class="timing bmo">BMO</span></td>'
    f'<td class="c-acc" style="font-weight:700">{move}</td>'
    f'<td style="font-size:10px;color:var(--sub)">{note}</td></tr>'
    for t, move, note in earn_rows_data
)

# ---------------------------------------------------------------
# SECTORS rows (Fri 10/9, real FMP sector-performance-snapshot)
# ---------------------------------------------------------------
sector_marker_lead = "<!-- INJECT: SECTORS"
sector_data = [
    ("XLU", "Utilities", 2.78), ("XLV", "Healthcare", 2.10),
    ("XLY", "Consumer Cyclical", 1.26), ("XLRE", "Real Estate", 0.95),
    ("XLB", "Basic Materials", 0.93), ("XLI", "Industrials", -0.88),
    ("XLK", "Technology", -0.63),
]
max_abs = max(abs(v) for _, _, v in sector_data)
sector_rows = ""
for etf, name, val in sector_data:
    pct_width = round(abs(val) / max_abs * 100)
    color_bar = "var(--safe)" if val >= 0 else "var(--danger)"
    color_cls = "c-safe" if val >= 0 else "c-bad"
    sign = "+" if val >= 0 else ""
    sector_rows += (
        f'<div class="sector-row"><span class="sec-etf">{etf}</span>'
        f'<span class="sec-name">{name}</span>'
        f'<div class="sec-bar-wrap"><div class="sec-bar" style="width:{pct_width}%;background:{color_bar}"></div></div>'
        f'<span class="sec-val {color_cls}">{sign}{val:.2f}%</span></div>'
    )
print("sector_rows built, len=", len(sector_rows))

# ---------------------------------------------------------------
# S07 GAINERS / DECLINERS (TheStreet-sourced, real tickers/moves)
# ---------------------------------------------------------------
gainers_marker_lead = "<!-- INJECT: S07 GAINERS"
gainers_data = [
    ("CCC", "M&amp;A", "TALKS", "+9.5%", "GTCR/Elliott buyout talks reported — TheStreet"),
    ("CRM", "UPGRADE", "BOFA BUY", "+4.3%", "BofA upgrade, $285 PT — TheStreet"),
    ("SBUX", "DENIAL", "NO DEAL", "+1.3%", "Denied Chipotle buyout rumor — TheStreet"),
]
gainers_rows = "".join(
    f'<tr><td>{t}</td><td><span class="pm-cat pm-earn">{c1}</span> '
    f'<span class="pm-cat pm-beat">{c2}</span></td>'
    f'<td class="c-safe" style="font-weight:700;text-align:right;font-family:\'Space Mono\',monospace">{pct}</td>'
    f'<td style="font-size:10px;color:var(--sub)">{note}</td></tr>'
    for t, c1, c2, pct, note in gainers_data
)

decliners_marker_lead = "<!-- INJECT: S07 DECLINERS"
decliners_data = [
    ("ADBE", "DOWNGRADE", "WF UW", "-4.0%", "Wells Fargo cut to Underweight, $225 PT — TheStreet"),
    ("ALB", "GUIDANCE", "WEAK", "-4.3%", "Weak lithium pricing outlook — TheStreet"),
    ("CMG", "RUMOR", "FALLOUT", "-2.8%", "Fell on SBUX buyout-rumor denial — TheStreet"),
    ("IONQ", "M&amp;A", "DILUTIVE", "-3.0%", "Buying Elisity for up to $1.3B in stock — TheStreet"),
]
decliners_rows = "".join(
    f'<tr><td>{t}</td><td><span class="pm-cat pm-earn">{c1}</span> '
    f'<span class="pm-cat pm-miss">{c2}</span></td>'
    f'<td class="c-bad" style="font-weight:700;text-align:right;font-family:\'Space Mono\',monospace">{pct}</td>'
    f'<td style="font-size:10px;color:var(--sub)">{note}</td></tr>'
    for t, c1, c2, pct, note in decliners_data
)
print("gainers/decliners rows built")

# ---------------------------------------------------------------
# S03 ALERTS / EVENTS / ACTIONABLES
# ---------------------------------------------------------------
def alert_row(dot, title, body):
    return (f'<div class="alert-row"><div class="alert-dot {dot}"></div>'
            f'<div class="alert-txt"><strong>{title}</strong> {body}</div></div>')

alerts_marker_lead = "<!-- INJECT: ALERTS"
alerts_rows = (
    alert_row("adot-r", "Houthi strike on Riyadh airport.",
              "13 killed in the weekend attack; Trump signaled the U.S. may join Saudi Arabia’s "
              "campaign against the Houthis. Two tankers were also attacked — Mideast crude-export "
              "risk is live.")
    + alert_row("adot-y", "Russia-Ukraine energy truce reported.",
                "Trump says both sides agreed to stop targeting energy infrastructure; Zelenskiy is "
                "awaiting details and Russia hasn’t commented. Oil headlines are whipsawing "
                "between this and the Houthi risk.")
    + alert_row("adot-y", "Schwab data feed down.",
                "Refresh token is stale (HTTP 400) — no real /ES or /NQ futures ticks today. "
                "Needs a live OAuth re-mint from Joe; not something this pipeline can self-heal.")
)

events_marker_lead = "<!-- INJECT: EVENTS"
events_rows = (
    alert_row("adot-g", "Bond market closed.",
              "Columbus Day — SIFMA-recommended full close for USD fixed income. Equities trade "
              "regular hours, no early close.")
    + alert_row("adot-y", "No U.S. econ data today.",
                "CPI due Wednesday, PPI + retail sales Thursday. Today’s calendar is empty by design.")
    + alert_row("adot-g", "Bank earnings tomorrow.",
                "JPM, GS, WFC, C, JNJ and UNH all report BMO Tuesday — the quarter’s first real test.")
)

actionables_marker_lead = "<!-- INJECT: ACTIONABLES"
actionables_rows = (
    alert_row("adot-r", "Don’t size /ES or /NQ off any ‘pivot’ you see today.",
              "Schwab feed is down; any precise intraday level circulating isn’t coming from this "
              "pipeline’s real data.")
    + alert_row("adot-y", "Watch 7,736 / 7,844.52 on SPX cash.",
                "Support / all-time-high band from the weekend desk read — sourced technical "
                "context, not a futures pivot.")
    + alert_row("adot-y", "Respect the TLT/XLU crowded trade.",
                "Record call volume in both — a hot CPI Wednesday could force a fast long-duration "
                "unwind.")
)
print("alerts/events/actionables built")

# ---------------------------------------------------------------
# REGIME DETAILS
# ---------------------------------------------------------------
regime_marker_lead = "<!-- INJECT: REGIME DETAILS"
regime_items = [
    "Earnings season opens Tue — JPM/GS/C/WFC/JNJ/UNH (all BMO)",
    "10Y yield 5.24%, near the 5.40% resistance flagged for the week",
    "Bond mkt closed today (Columbus Day, SIFMA rec.)",
    "Nasdaq internals: 209 new lows vs. 41 highs Fri — 30th straight session of more lows than highs",
]
regime_rows = "".join(
    f'<div class="reg-div"></div><div class="reg-item">{item}</div>' for item in regime_items
)

# ---------------------------------------------------------------
# BBM SIGNAL ROWS
# ---------------------------------------------------------------
bbm_marker_lead = "<!-- INJECT: BBM SIGNAL ROWS"
bbm_signals = [
    ("Price Trend (SPX/NDX near ATH)", "bull", "BULL"),
    ("Nasdaq Breadth (30-session new-low streak)", "bear", "BEAR"),
    ("AAII (39.0% bear vs 40.3% bull, 35wk above-avg pessimism)", "neut", "NEUT"),
    ("VIX (15.4, +4% but sub-16)", "neut", "NEUT"),
    ("Geopolitical (Houthi/Saudi escalation risk)", "bear", "CAUTION"),
    ("Rates (10Y 5.24%, near cycle highs)", "neut", "CAUTION"),
]
bbm_rows = "".join(
    f'<div class="bbm-signal-row"><span class="bbm-sn">{name}</span>'
    f'<span class="bbm-sv-{cls}">{label}</span></div>'
    for name, cls, label in bbm_signals
)
print("regime/bbm rows built")

# ---------------------------------------------------------------
# SPOTLIGHT (up to 3)
# ---------------------------------------------------------------
spotlight_marker_lead = "<!-- INJECT: SPOTLIGHT"
spotlight_items = [
    ("CCC", "+9.5% Fri (real, FMP) on reports of advanced buyout talks with GTCR and Elliott "
            "Investment Management (TheStreet). Binary catalyst — a signed deal or a denial "
            "both move it hard from here; headline risk, not a technical setup."),
    ("ADBE / CRM", "Wells Fargo cut Adobe to Underweight ($225 PT) the same day BofA upgraded "
                   "Salesforce to Buy ($285 PT) — per TheStreet. The Street is picking winners "
                   "and losers inside software, not dumping the group wholesale."),
    ("BTC / ETH", f"BTC is at $82,400, down 1.5% and ~4.8% off its Oct 4 local high of "
                  f"${btc_swing_high:,.0f}; ETH at $2,525 is tracking a similar pullback from its "
                  f"Sep 21-area high. Both remain well above their mid-September lows — reads "
                  f"as a garden-variety pullback inside an uptrend, not a trend break."),
]
spotlight_rows = "".join(
    f'<div class="spot-item"><div class="spot-hd"><span class="spot-tk">{tk}</span></div>'
    f'<div class="spot-body">{body}</div></div>'
    for tk, body in spotlight_items
)

# ---------------------------------------------------------------
# OPTIONS IDEAS (up to 4)
# ---------------------------------------------------------------
options_marker_lead = "<!-- INJECT: OPTIONS IDEAS"
options_items = [
    ("TLT / XLU crowded calls",
     "Record call volume hit TLT (~15M contracts) and XLU (~2.2M) last week — the Street is "
     "betting heavily on lower long-term yields via rate-sensitive proxies. That’s crowded: "
     "the 10-year already sits at 5.24% with 5.40% flagged as resistance, and a hot CPI print "
     "Wednesday could force a fast unwind. Read it as a sentiment gauge, not a signal to join."),
    ("Earnings-season vol",
     "No sized options idea into tomorrow’s bank earnings — current IV/skew wasn’t "
     "sourced today. Note only: IV on JPM/GS/WFC/C typically richens into the print and crushes "
     "after; a long-premium bet needs a real directional edge, not just the calendar."),
]
options_rows = "".join(
    f'<div class="opt-item"><div class="opt-hd"><span class="opt-tk">{t}</span></div>'
    f'<div class="opt-body">{b}</div></div>'
    for t, b in options_items
)
print("spotlight/options rows built")

# ---------------------------------------------------------------
# MONEY FLOW / UNUSUAL OPTIONS
# ---------------------------------------------------------------
moneyflow_marker_lead = "<!-- INJECT: MONEY FLOW"
moneyflow_rows = (
    '<div class="mf-item"><div class="mf-name">Dark Pool / Block Prints</div>'
    '<div class="mf-val c-warn">NOT SOURCED TODAY</div></div>'
)

unusual_opt_marker_lead = "<!-- INJECT: UNUSUAL OPTIONS"
unusual_opt_rows = (
    '<div class="uo-item"><div class="uo-hd"><span class="uo-tk">TLT</span>'
    '<span class="uo-exp">Weekly call volume</span></div>'
    '<div class="uo-body c-warn">~15M contracts last week (record) — crowded long-duration '
    'bet via calls; weekend-desk sourced, not a live chain read today.</div></div>'
    '<div class="uo-item"><div class="uo-hd"><span class="uo-tk">XLU</span>'
    '<span class="uo-exp">Weekly call volume</span></div>'
    '<div class="uo-body c-warn">~2.2M contracts (record) — same rate-cut-conviction trade via '
    'utilities; unwind risk if yields extend toward 5.40%.</div></div>'
)
print("moneyflow/unusual options rows built")

# ---------------------------------------------------------------
# MASTER TRADE TABLE (3 rows only - honestly supportable today)
# ---------------------------------------------------------------
trade_marker = "<!-- INJECT UP TO 20 TRADE ROWS. Column order: #, Symbol, Type, Direction, Setup, Entry, Stop, Target, R:R, Notes, Priority -->"
trades = [
    (1, "BTC", "ts", "t-long", "Mean-reversion to 20d SMA",
     f"{btc_entry:,.0f}", f"{btc_stop:,.2f}", f"{btc_target:,.2f}", f"1:{btc_rr}",
     "Pullback within uptrend; SMA20/swing-low computed from FMP daily closes.", "★★"),
    (2, "ETH", "ts", "t-long", "Mean-reversion to 20d SMA",
     f"{eth_entry:,.0f}", f"{eth_stop:,.2f}", f"{eth_target:,.2f}", f"1:{eth_rr}",
     "Same setup as BTC, tracking the Sep 21 high pullback.", "★★"),
    (3, "CCC", "ts", "t-long", "M&amp;A speculation (event-driven)",
     f"{ccc_entry:,.2f}", f"{ccc_stop:,.2f}", f"{ccc_target:,.2f}", f"1:{ccc_rr}",
     "Binary — GTCR/Elliott buyout talks (TheStreet). Size small; full-loss risk if talks "
     "collapse.", "★"),
]
trade_rows = "".join(
    f'<tr><td>{n}</td><td><strong>{sym}</strong></td><td><span class="t-type {tcls}">STOCK</span></td>'
    f'<td class="{dcls}">LONG</td><td>{setup}</td><td class="mono">{entry}</td>'
    f'<td class="mono c-bad">{stop}</td><td class="mono c-safe">{target}</td>'
    f'<td class="t-rr">{rr}</td><td>{notes}</td><td class="t-pri">{pri}</td></tr>'
    for n, sym, tcls, dcls, setup, entry, stop, target, rr, notes, pri in trades
)
trade_rows_full = (
    trade_rows
    + '<tr><td colspan="11" style="color:var(--muted);font-size:9px;padding-top:10px">'
      '/ES and /NQ futures setups omitted today — Schwab refresh token is stale (HTTP 400), '
      'no real settlement/pivot/VAH/POC/VAL to grade against. See Section 05 Pipeline Note.</td></tr>'
)
print("trade rows built, n=", len(trades))

# ---------------------------------------------------------------
# Build INJECTED_SECTIONS dict: exact pristine marker -> replacement
# ---------------------------------------------------------------
def extract_comment(lead):
    start = tpl.index(lead)
    end = tpl.index("-->", start) + 3
    marker = tpl[start:end]
    if tpl.count(marker) != 1:
        raise SystemExit(f"comment marker not unique: {lead}")
    return marker

INJECTED_SECTIONS = {}
INJECTED_SECTIONS[es_block] = es_filled
INJECTED_SECTIONS[nq_block] = nq_filled
INJECTED_SECTIONS[econ_block] = econ_filled
INJECTED_SECTIONS[earn_block] = earn_filled

comment_pairs = [
    (econ_cal_marker_lead, econ_cal_rows),
    (earn_watch_marker_lead, earn_rows),
    (sector_marker_lead, sector_rows),
    (gainers_marker_lead, gainers_rows),
    (decliners_marker_lead, decliners_rows),
    (alerts_marker_lead, alerts_rows),
    (events_marker_lead, events_rows),
    (actionables_marker_lead, actionables_rows),
    (regime_marker_lead, regime_rows),
    (bbm_marker_lead, bbm_rows),
    (spotlight_marker_lead, spotlight_rows),
    (options_marker_lead, options_rows),
    (moneyflow_marker_lead, moneyflow_rows),
    (unusual_opt_marker_lead, unusual_opt_rows),
]
for lead, repl in comment_pairs:
    marker = extract_comment(lead)
    INJECTED_SECTIONS[marker] = repl

if tpl.count(trade_marker) != 1:
    raise SystemExit("trade marker not unique")
INJECTED_SECTIONS[trade_marker] = trade_marker + trade_rows_full

print("INJECTED_SECTIONS keys:", len(INJECTED_SECTIONS))
for k in INJECTED_SECTIONS:
    assert tpl.count(k) == 1, f"marker not unique: {k[:60]!r}"
print("ALL INJECTED_SECTIONS MARKERS VERIFIED UNIQUE.")

# ---------------------------------------------------------------
# Top-level bare keys
# ---------------------------------------------------------------
TOP = {
    "DATE_LONG": "Monday, October 12, 2026",
    "DATE_SHORT": "Oct 12",
    "DAY_OF_WEEK": "Monday",
    "SESSION_LABEL": "NY Session",
    "PREV_DATE_SHORT": "Oct 9",
    "REGIME_LABEL": "MIXED",
    "REGIME_SIGNAL": "MIXED — INDEX STRENGTH, WEAK INTERNALS",
    "REGIME_SEV": "sv-caution",
    "PRIMARY_CATALYST": "HOUTHI ESCALATION RISK — OIL/MIDEAST",

    "VIX_VAL": "15.4", "VIX_LABEL": "LOW, RISING +4%", "VIX_SEV": "sv-neut",
    "FNG_VAL": "45", "FNG_LABEL": "NEUTRAL (Fri)", "FNG_SEV": "sv-neut",
    "PUTCALL_VAL": "N/A", "PUTCALL_LABEL": "NOT SOURCED TODAY", "PUTCALL_SEV": "sv-neut",
    "BREADTH_VAL": "1.2:1 ADV", "BREADTH_LABEL": "NYSE WK; NASDAQ WEAK", "BREADTH_SEV": "sv-caution",
    "AAII_VAL": "40.3/39.0", "AAII_LABEL": "BULL/BEAR — BEARS >AVG 35WK", "AAII_SEV": "sv-caution",
    "SENTIMENT_VAL": "MIXED", "SENTIMENT_LABEL": "PRICE BULL, BREADTH BEAR", "SENTIMENT_SEV": "sv-caution",

    "ADVISORY_VERDICT": "CHOP AT THE HIGHS — DON’T CHASE.",
    "ADVISORY_BODY": (
        "SPX and Nasdaq are consolidating within a point of last week’s record highs, but the "
        "move is getting thinner underneath: the Nasdaq has logged more new 52-week lows than new "
        "highs for 30 straight sessions, and AAII bears (39.0%) still edge out bulls (40.3%) after "
        "35 straight weeks of above-average pessimism. Overnight, a Houthi strike on Riyadh’s "
        "airport (13 dead) raises the odds of a U.S.-Saudi response against Yemen, while oil "
        "headlines whipsaw against a reported Russia-Ukraine energy-infrastructure truce. Bond "
        "markets are closed for Columbus Day, thinning liquidity into tomorrow’s bank-earnings "
        "open (JPM/GS/C/WFC/JNJ/UNH). Respect the uptrend, but size for chop, not conviction, "
        "until earnings and Wednesday’s CPI pick a direction."
    ),
    "SIGNAL_BULL": "SPX/NDX NEAR ATH",
    "SIGNAL_WATCH": "BANK EARNINGS TUE",
    "SIGNAL_CAUTION": "NASDAQ 30-SESSION BREADTH STREAK",
    "SIGNAL_AVOID": "CHASING GAPS — SCHWAB FEED DOWN",
    "OPERATIVE_VERDICT_TEXT": (
        "MIXED REGIME. The tape wants to go higher, the plumbing says be careful. Stand down on "
        "fresh futures risk until the Schwab data feed is restored (see Section 05 Pipeline Note); "
        "trade equities/crypto off real levels only, and let tomorrow’s bank earnings and "
        "Wednesday’s CPI set the week’s real direction."
    ),
    "BBM_BULL_PCT": "52", "BBM_BEAR_PCT": "48",
    "BBM_HEADLINE": "PRICE TREND BULLISH, INTERNALS LEANING BEARISH — CALL IT A COIN FLIP WITH AN UPWARD DRIFT",

    "CA_ROTATION": (
        "Friday’s tape rotated defensive: Utilities (+2.78%) and Healthcare (+2.10%) led, "
        "Consumer Cyclical (+1.26%) and Real Estate (+0.95%) followed — classic late-cycle / "
        "rate-hedge leadership. Technology (-0.63%) and Industrials (-0.88%) lagged. That’s a "
        "‘rising index, cautious rotation’ tape, not a clean risk-on breadth thrust."
    ),
}
print("TOP keys:", len(TOP))

# ---------------------------------------------------------------
# S04 KPI bar (real data from data/daily/2026-10-12.json + Yahoo premkt)
# ---------------------------------------------------------------
TOP.update({
    "ES_PREMARKET": "7,861.25", "ES_CHANGE": "+1.50 (+0.02%)", "ES_COLOR": "c-safe",
    "NQ_PREMARKET": "31,036.00", "NQ_CHANGE": "-72.75 (-0.23%)", "NQ_COLOR": "c-bad",
    "GOLD_PRICE": "$4,195.40", "GOLD_CHANGE": "-20.90 (-0.50%)", "GOLD_COLOR": "c-bad",
    "BTC_PRICE": "$82,399.99", "BTC_CHANGE": "-1,273.02 (-1.52%)", "BTC_COLOR": "c-bad",
    "SPX_CLOSE": "7,811.54", "SPX_CHANGE": "+46.18 (+0.59%)", "SPX_COLOR": "c-safe",
    "ETH_PRICE": "$2,524.97", "ETH_CHANGE": "-9.33 (-0.37%)", "ETH_COLOR": "c-bad",
    "ES_GAP": "N/A — Schwab feed down", "ES_GAP_COLOR": "warn",
    "NQ_GAP": "N/A — Schwab feed down", "NQ_GAP_COLOR": "warn",
})
print("TOP keys total:", len(TOP))

# ---------------------------------------------------------------
# Write insert.json
# ---------------------------------------------------------------
insert_payload = dict(TOP)
insert_payload["INJECTED_SECTIONS"] = INJECTED_SECTIONS
OUT_PATH.write_text(json.dumps(insert_payload, indent=2, ensure_ascii=False), encoding="utf-8")
print("WROTE", OUT_PATH, OUT_PATH.stat().st_size, "bytes")
