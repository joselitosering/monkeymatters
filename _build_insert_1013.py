# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path

REPO = Path(r"D:\Apps\DevOps\Github\monkeymatters")
TEMPLATE_PATH = REPO / "template" / "mmm_template.html"
PREV_INSERT_PATH = REPO / "data" / "daily" / "2026-10-12.insert.json"
OUT_PATH = REPO / "data" / "daily" / "2026-10-13.insert.json"

template = TEMPLATE_PATH.read_text(encoding="utf-8")
prev = json.loads(PREV_INSERT_PATH.read_text(encoding="utf-8"))
prev_sections = prev["INJECTED_SECTIONS"]

# ---- Step 1: confirm the template has not drifted from the markers that
# produced the known-good 2026-10-12 render. Each marker must match exactly once.
problems = []
for k in prev_sections.keys():
    c = template.count(k)
    if c != 1:
        problems.append((c, k[:90]))
if problems:
    print("TEMPLATE MARKER MISMATCH \u2014 ABORTING. Details:")
    for c, k in problems:
        print(f"  count={c}  key_start={k!r}")
    sys.exit(1)
print(f"OK: all {len(prev_sections)} prior markers match the current template exactly once.")

keys = list(prev_sections.keys())

def find_key(must_have, must_not_have=None):
    cands = [k for k in keys if must_have in k and (must_not_have is None or must_not_have not in k)]
    if len(cands) != 1:
        raise SystemExit(f"find_key failed for {must_have!r}/{must_not_have!r}: {len(cands)} matches")
    return cands[0]

K_ES          = find_key("\U0001F4C8 /ES \u2014 E-Mini")
K_NQ          = find_key("\U0001F4C8 /NQ \u2014 E-Mini")

generic_ca_candidates = [k for k in keys if k.startswith('<div class="ca">') ]
econ_ca = [k for k in generic_ca_candidates if "Spec. Move" in k]
earn_ca = [k for k in generic_ca_candidates if "Spec. Move" not in k]
assert len(econ_ca) == 1, len(econ_ca)
assert len(earn_ca) == 1, len(earn_ca)
K_ECON_CA = econ_ca[0]
K_EARN_CA = earn_ca[0]

K_S06_ECON    = find_key("INJECT: S06 ECON CALENDAR")
K_S06_EARN    = find_key("INJECT: S06 EARNINGS WATCH")
K_SECTORS     = find_key("INJECT: SECTORS")
K_S07_GAIN    = find_key("INJECT: S07 GAINERS")
K_S07_DECL    = find_key("INJECT: S07 DECLINERS")
K_ALERTS      = find_key("INJECT: ALERTS")
K_EVENTS      = find_key("INJECT: EVENTS")
K_ACTIONABLES = find_key("INJECT: ACTIONABLES")
K_REGIME      = find_key("INJECT: REGIME DETAILS")
K_BBM         = find_key("INJECT: BBM SIGNAL ROWS")
K_SPOTLIGHT   = find_key("INJECT: SPOTLIGHT")
K_OPTIONS     = find_key("INJECT: OPTIONS IDEAS")
K_MONEYFLOW   = find_key("INJECT: MONEY FLOW")
K_UNUSUAL     = find_key("INJECT: UNUSUAL OPTIONS")
K_TRADEROWS   = find_key("INJECT UP TO 20 TRADE ROWS")

assert len(keys) == 19, len(keys)
print("All 19 marker keys resolved.")

# ============================================================
# Flat top-level tokens
# ============================================================
flat = {
  "DATE_LONG": "Tuesday, October 13, 2026",
  "DATE_SHORT": "Oct 13",
  "DAY_OF_WEEK": "Tuesday",
  "SESSION_LABEL": "NY Session",
  "PREV_DATE_SHORT": "Oct 12",

  "REGIME_LABEL": "MIXED",
  "REGIME_SIGNAL": "MIXED \u2014 BANK EARNINGS OPEN, CHIP ROUT SPREADS FROM ASIA",
  "REGIME_SEV": "sv-caution",
  "PRIMARY_CATALYST": "BANK EARNINGS BMO + CHIP SELLOFF \u2014 HOUTHI/HORMUZ ESCALATION LIVE",

  "VIX_VAL": "15.3",
  "VIX_LABEL": "LOW, CALM \u2014 +0.6%",
  "VIX_SEV": "sv-neut",

  "FNG_VAL": "46",
  "FNG_LABEL": "NEUTRAL (Mon, unch.)",
  "FNG_SEV": "sv-neut",

  "PUTCALL_VAL": "N/A",
  "PUTCALL_LABEL": "NOT SOURCED TODAY",
  "PUTCALL_SEV": "sv-neut",

  "BREADTH_VAL": "N/A",
  "BREADTH_LABEL": "NOT SOURCED \u2014 ASIA CHIP ROUT (KOSPI -5.5%)",
  "BREADTH_SEV": "sv-caution",

  "AAII_VAL": "40.3/39.0",
  "AAII_LABEL": "BULL/BEAR \u2014 WK OF OCT 7, UNCHANGED",
  "AAII_SEV": "sv-caution",

  "SENTIMENT_VAL": "MIXED",
  "SENTIMENT_LABEL": "INDEX CALM, CHIPS/BANKS UNDER PRESSURE",
  "SENTIMENT_SEV": "sv-caution",

  "ADVISORY_VERDICT": "BANKS OPEN THE BOOKS, CHIPS TAKE THE HIT.",
  "ADVISORY_BODY": (
    "Bank-earnings season opened this morning and it\u2019s a real split decision. "
    "JPMorgan logged a rare quarterly miss \u2014 net income still rose 6% y/y to $15.3B and EPS "
    "+10% y/y to $5.57, but an investment-banking slowdown and a securities loss spooked the "
    "tape, and shares were down roughly 3.4% premarket. Goldman Sachs went the other way \u2014 "
    "EPS $17.01, 18.7% annualized ROE, its second-best revenue quarter ever \u2014 and Citigroup "
    "logged its best bond-trading quarter in a decade and beat profit estimates, though both are "
    "fighting a reported \u2018yield-driven bank selloff\u2019 backdrop, so a beat isn\u2019t guaranteed to "
    "print green. Wells Fargo\u2019s profit rose on loan growth but revenue missed, shares -1%. "
    "UnitedHealth beat clean (EPS $4.69 vs. $4.15 est.) and is +2.6% premarket; Johnson &amp; Johnson "
    "beat adjusted EPS ($2.59 vs. $2.52 est.) and raised full-year guidance, yet still slipped "
    "-0.9% \u2014 a reminder that a good quarter doesn\u2019t always move the stock. The bigger story is "
    "semiconductors: memory and chip names are getting dumped on fresh fears that China\u2019s CXMT "
    "could challenge Samsung/SK Hynix/Micron, and it tore through Asia overnight \u2014 Korea\u2019s Kospi "
    "closed -5.5% (Samsung -7.4%, SK Hynix -10.1%) \u2014 dragging Micron -3.2% and Marvell -2.6% into "
    "the U.S. premarket. Geopolitically, the Houthi-Saudi conflict is still very live (threat "
    "alerts hit Riyadh and Khamis Mushait Monday, and a tanker was struck in the Strait of Hormuz) "
    "and Iran has offered to mediate, yet oil is actually down about 2% (Brent $104.62, WTI $91.78) "
    "on hopes the Russia-Ukraine energy truce holds. CPI lands tomorrow. The Dow\u2019s calm exterior "
    "is real, but today\u2019s stress is sector-specific \u2014 chips and parts of financials \u2014 not "
    "systemic, at least not yet."
  ),
  "SIGNAL_BULL": "GS/C/UNH/JNJ ALL BEAT ON EPS",
  "SIGNAL_WATCH": "CPI TOMORROW (WED)",
  "SIGNAL_CAUTION": "CHIP/MEMORY ROUT SPREADING FROM ASIA (KOSPI -5.5%)",
  "SIGNAL_AVOID": "CHASING /ES OR /NQ \u2014 SCHWAB FEED DOWN 2ND SESSION",

  "OPERATIVE_VERDICT_TEXT": (
    "MIXED REGIME, SECTOR-SPECIFIC STRESS. Headline index action is calm \u2014 Dow closed near "
    "51,850 Monday \u2014 but the real fight today is underneath: a China-competition scare is "
    "gutting memory/chip names on both sides of the Pacific, and bank earnings are a legitimate "
    "split (GS/C/UNH/JNJ beats, JPM a rare miss, WFC light on revenue). None of this reads "
    "systemic yet. Don\u2019t size /ES or /NQ blind \u2014 Schwab feed is down a second straight session "
    "\u2014 and treat chip-sector beta as the thing to actually risk-manage into tomorrow\u2019s CPI, not "
    "the index."
  ),

  "BBM_BULL_PCT": "46",
  "BBM_BEAR_PCT": "54",
  "BBM_HEADLINE": "BANK EARNINGS BEAT ON BALANCE, BUT CHIP-SECTOR CONTAGION AND LIVE GEOPOLITICAL RISK TIP IT CAUTIOUS",

  "CA_ROTATION": (
    "Monday\u2019s tape (as of 11am ET, Benzinga, 15-min delayed quotes) was broadly risk-on under "
    "the hood \u2014 9 of 11 S&amp;P sectors green \u2014 led by Energy (+1.03%) and Communication Services "
    "(+0.87%), with cyclical Financials (+0.50%) also firm. The two laggards were Consumer "
    "Discretionary (-0.28%) and, more notably, Technology (-1.16%) \u2014 the chip/memory selloff was "
    "already visible in Monday\u2019s intraday tape before it blew out further in Asia overnight and "
    "hit U.S. chip names again in today\u2019s premarket. That\u2019s \u2018broad participation, tech-specific "
    "stress,\u2019 not a risk-off tape \u2014 but not one to chase into tech beta either."
  ),

  "ES_PREMARKET": "N/A",
  "ES_CHANGE": "-10.00 (-0.13%)",
  "ES_COLOR": "c-bad",
  "NQ_PREMARKET": "N/A",
  "NQ_CHANGE": "-182.25 (-0.59%)",
  "NQ_COLOR": "c-bad",
  "GOLD_PRICE": "$4,199.90",
  "GOLD_CHANGE": "+9.30 (+0.22%)",
  "GOLD_COLOR": "c-safe",
  "BTC_PRICE": "$83,345.24",
  "BTC_CHANGE": "+1,590.76 (+1.95%)",
  "BTC_COLOR": "c-safe",
  "SPX_CLOSE": "7,807.24",
  "SPX_CHANGE": "-4.30 (-0.06%)",
  "SPX_COLOR": "c-bad",
  "ETH_PRICE": "$2,508.94",
  "ETH_CHANGE": "+64.80 (+2.65%)",
  "ETH_COLOR": "c-safe",

  "ES_GAP": "N/A \u2014 Schwab feed down (2nd session)",
  "ES_GAP_COLOR": "warn",
  "NQ_GAP": "N/A \u2014 Schwab feed down (2nd session)",
  "NQ_GAP_COLOR": "warn",
}

# ============================================================
# INJECTED_SECTIONS values
# ============================================================
sections = {}

sections[K_ES] = """<div class="card-hd">\U0001F4C8 /ES \u2014 E-Mini S&amp;P 500 \u00b7 {{PREV_DATE_SHORT}} Settlement</div>
<table class="ftbl">
<tr><td>Gap vs Settle (open \u2212 prior settle)</td><td class="{{ES_GAP_COLOR}}">{{ES_GAP}}</td></tr>
<tr><td>SPX cash (FMP, Mon close)</td><td class="acc">7,807.24 (-0.06%)</td></tr><tr><td>Fri close (SPX cash)</td><td class="acc">7,811.54</td></tr><tr><td>S&amp;P 500 E-mini premkt (Reuters, ~6:54am ET)</td><td class="bad">-10.00 pts (-0.13%)</td></tr><tr class="ftbl-sub"><td colspan="2">\u2014 Pivot / Volume Profile \u2014</td></tr><tr><td>Status</td><td class="bad">UNAVAILABLE \u2014 Schwab refresh token stale (HTTP 400), 2nd straight session</td></tr><tr><td>Action</td><td class="warn">No re-mint attempted \u2014 needs Joe\u2019s live OAuth; flagged below</td></tr>
</table>
<p class="tfoot-note">Source: Schwab price history \u2014 daily bars (H/L/settle, classic pivots, 5-day ADR, ATR-20 N, Donchian 20/55) + 1-min RTH bars (70% value area, POC, VWAP). Verify settlement at CME.com.</p>
<div class="ca">
<div class="ca-row"><div class="ca-lbl">Analysis</div><div class="ca-val">Second straight session without real Schwab futures data \u2014 the refresh token is still stale (HTTP 400), and schwab_futures came back {} again in today\u2019s JSON. Working off cash-index and sourced futures-adjacent snapshots instead: SPX cash closed Monday at 7,807.24, essentially flat (-0.06%) versus Friday\u2019s 7,811.54, still sitting within a hair of last week\u2019s record band. This morning\u2019s S&amp;P 500 E-mini snapshot (Reuters, ~6:54am ET) was down about 10 points (-0.13%) as bank-earnings support fights chip-sector weakness. No real pivots/VAH/POC/VAL today \u2014 don\u2019t trust any precise intraday level you see elsewhere until the feed is back.</div></div>
<div class="ca-row"><div class="ca-lbl">Spec. Move</div><div class="ca-val">Tomorrow\u2019s CPI is the real swing factor for the week, but today the wildcard is how the tape digests a split bank-earnings morning (GS, Citi, UnitedHealth and J&amp;J all beat; JPMorgan a rare miss) layered on a chip-sector selloff spreading out of Asia \u2014 either could push /ES harder than the calm VIX (15.3) suggests.</div></div>
<div class="ca-row"><div class="ca-lbl">Trade Idea</div><div class="ca-val">No sized /ES idea today \u2014 second straight session without real settlement, VAH/POC/VAL, or 1-min RTH bars to grade against. Watching the SPX cash reaction to today\u2019s earnings batch and tomorrow\u2019s CPI instead of forcing a futures entry blind.</div></div>
<div class="ca-row"><div class="ca-lbl">Strategy</div><div class="ca-val">Stand aside on /ES until the Schwab token is re-minted \u2014 that needs Joe\u2019s live OAuth, not something this pipeline can self-heal. Trading the cash/ETF proxy instead: respect last week\u2019s record-high band on SPX cash as resistance, and don\u2019t add fresh risk ahead of tomorrow\u2019s CPI.</div></div>
<div class="ca-row"><div class="ca-lbl">Levels</div><div class="ca-val"><div class="ca-lvls"><span class="lv lv-e">L Entry: N/A</span><span class="lv lv-s">L Stop: N/A</span><span class="lv lv-t">L Target: N/A</span><span class="lv lv-e">S Entry: N/A</span><span class="lv lv-s">S Stop: N/A</span><span class="lv lv-t">S Target: N/A</span><span class="lv lv-n">PP: N/A</span><span class="lv lv-n">VWAP: N/A</span></div></div></div>
</div>"""

sections[K_NQ] = """<div class="card-hd">\U0001F4C8 /NQ \u2014 E-Mini Nasdaq-100 \u00b7 {{PREV_DATE_SHORT}} Settlement</div>
<table class="ftbl">
<tr><td>Gap vs Settle (open \u2212 prior settle)</td><td class="{{NQ_GAP_COLOR}}">{{NQ_GAP}}</td></tr>
<tr><td>Nasdaq Composite (Mon close)</td><td class="bad">27,245.90 (-0.44%)</td></tr><tr><td>Nasdaq-100 E-mini premkt (Reuters, ~6:54am ET)</td><td class="bad">-182.25 pts (-0.59%)</td></tr><tr><td>Desk context</td><td class="warn">Chip/memory names (NVDA, AMD, MRVL, MU) leading futures lower</td></tr><tr class="ftbl-sub"><td colspan="2">\u2014 Pivot / Volume Profile \u2014</td></tr><tr><td>Status</td><td class="bad">UNAVAILABLE \u2014 Schwab refresh token stale (HTTP 400), 2nd straight session</td></tr><tr><td>Action</td><td class="warn">No re-mint attempted \u2014 needs Joe\u2019s live OAuth; flagged below</td></tr>
</table>
<p class="tfoot-note">Source: Schwab price history \u2014 daily bars (H/L/settle, classic pivots, 5-day ADR, ATR-20 N, Donchian 20/55) + 1-min RTH bars (70% value area, POC, VWAP). Verify settlement at CME.com.</p>
<div class="ca">
<div class="ca-row"><div class="ca-lbl">Analysis</div><div class="ca-val">Same Schwab outage hits /NQ for a second straight session \u2014 schwab_futures empty again in today\u2019s JSON. Nasdaq Composite closed Monday at 27,245.90, down 0.44% (fell over 100 points intraday) even with the Dow near a record. This morning\u2019s Nasdaq-100 E-mini snapshot (Reuters, ~6:54am ET) is down about 182 points (-0.59%), the worst of the three major futures \u2014 almost entirely a chip/memory story: Nvidia -1%, AMD -1.5%, Marvell -2.6%, Micron -3.2% premarket here, after Korea\u2019s Kospi closed -5.5% (Samsung -7.4%, SK Hynix -10.1%) overnight on fears China\u2019s CXMT could challenge the memory oligopoly. No real pivots/VAH/POC/VAL today.</div></div>
<div class="ca-row"><div class="ca-lbl">Spec. Move</div><div class="ca-val">Any confirmation that CXMT is genuinely competitive at scale (vs. a sentiment scare) would extend this selloff into the U.S. session; a \u2018fear overdone\u2019 rebuttal from a chip CEO or analyst note could just as easily spark a relief bounce given how far Asia already moved.</div></div>
<div class="ca-row"><div class="ca-lbl">Trade Idea</div><div class="ca-val">No sized /NQ idea today for the same data reason as /ES. Watching SOX-adjacent names (Micron, Marvell, AMD) for stabilization as the tell that the chip rout is done extending, rather than forcing a futures entry blind.</div></div>
<div class="ca-row"><div class="ca-lbl">Strategy</div><div class="ca-val">Stand aside on /NQ until Schwab is restored. If trading chip/memory names directly, size for the fact that Asia already moved 2\u20133x harder than what\u2019s priced into the U.S. premarket \u2014 the move isn\u2019t exhausted just because it already happened overnight.</div></div>
<div class="ca-row"><div class="ca-lbl">Levels</div><div class="ca-val"><div class="ca-lvls"><span class="lv lv-e">L Entry: N/A</span><span class="lv lv-s">L Stop: N/A</span><span class="lv lv-t">L Target: N/A</span><span class="lv lv-e">S Entry: N/A</span><span class="lv lv-s">S Stop: N/A</span><span class="lv lv-t">S Target: N/A</span><span class="lv lv-n">PP: N/A</span><span class="lv lv-n">VWAP: N/A</span></div></div></div>
</div>"""

sections[K_ECON_CA] = """<div class="ca">
<div class="ca-row"><div class="ca-lbl">Analysis</div><div class="ca-val">No scheduled U.S. econ release today \u2014 the calendar\u2019s real event was six bank/healthcare/pharma earnings reports, not a data print. September CPI lands tomorrow (Wednesday), with PPI and retail sales expected to follow later this week; Fed Governor Waller has attributed the recent run-up in Treasury yields to stronger growth and large-scale AI investment rather than inflation fears alone, which makes tomorrow\u2019s print a real test of that read.</div></div>
<div class="ca-row"><div class="ca-lbl">Spec. Move</div><div class="ca-val">A hot CPI print would undercut Waller\u2019s \u2018it\u2019s growth, not inflation\u2019 framing and could hit the same duration-sensitive names (the TLT/XLU-adjacent trade, on record call volume last week) that are already crowded on rate-cut conviction.</div></div>
<div class="ca-row"><div class="ca-lbl">Trade Idea</div><div class="ca-val">No econ-data trade today \u2014 nothing scheduled to trade around. Save the ammo for tomorrow\u2019s CPI.</div></div>
<div class="ca-row"><div class="ca-lbl">Levels</div><div class="ca-val"><div class="ca-lvls"><span class="lv lv-e">L Entry: N/A</span><span class="lv lv-s">L Stop: N/A</span><span class="lv lv-t">L Target: N/A</span><span class="lv lv-e">S Entry: N/A</span><span class="lv lv-s">S Stop: N/A</span><span class="lv lv-t">S Target: N/A</span><span class="lv lv-n">PP: N/A</span><span class="lv lv-n">VWAP: N/A</span></div></div></div>
</div>"""

sections[K_EARN_CA] = """<div class="ca">
<div class="ca-row"><div class="ca-lbl">Analysis</div><div class="ca-val">All six names on yesterday\u2019s forward-look table reported this morning, and it\u2019s a real split: Goldman, Citi, UnitedHealth and Johnson &amp; Johnson all beat, while JPMorgan logged a rare miss (investment-banking slowdown, a securities loss) despite net income still growing 6% y/y, and Wells Fargo\u2019s profit rose on loan growth even as revenue came in light. The pattern worth flagging: J&amp;J beat and raised guidance but still slipped -0.9% premarket, while Goldman and Citi\u2019s beats are running into a separately reported \u2018yield-driven bank selloff\u2019 backdrop \u2014 a good number isn\u2019t guaranteed to print green this morning.</div></div>
<div class="ca-row"><div class="ca-lbl">Trade Idea</div><div class="ca-val">No new earnings trade sized today \u2014 the moves already happened premarket. Into the open: watch whether JPMorgan\u2019s ~-3.4% reaction holds or fades once the market digests that NII still grew 13% y/y; an overreaction fade is the cleanest earnings-adjacent idea here, and it isn\u2019t sized in the master trade table today given the lack of real-time options/chain data.</div></div>
<div class="ca-row"><div class="ca-lbl">Levels</div><div class="ca-val"><div class="ca-lvls"><span class="lv lv-e">L Entry: N/A</span><span class="lv lv-s">L Stop: N/A</span><span class="lv lv-t">L Target: N/A</span><span class="lv lv-e">S Entry: N/A</span><span class="lv lv-s">S Stop: N/A</span><span class="lv lv-t">S Target: N/A</span><span class="lv lv-n">PP: N/A</span><span class="lv lv-n">VWAP: N/A</span></div></div></div>
</div>"""

sections[K_S06_ECON] = (
    '<tr><td>ALL DAY</td><td><strong>Bank/healthcare earnings BMO</strong> '
    '<span class="chk">\u2713 JPM/GS/WFC/C/JNJ/UNH reported</span></td><td>\u2014</td>'
    '<td class="c-warn">Mixed \u2014 see Earnings Watch</td></tr>'
    '<tr><td>\u2014</td><td><strong>No U.S. econ data today</strong></td>'
    '<td>CPI Wed / PPI + Retail Sales later this wk</td><td class="c-sub">\u2014</td></tr>'
)

sections[K_S06_EARN] = (
    '<tr><td>JPM</td><td><span class="timing reported">REPORTED</span></td>'
    '<td class="c-bad" style="font-weight:700">EPS $5.57 (rare miss)</td>'
    '<td style="font-size:10px;color:var(--sub)">Net income $15.3B +6% y/y; NII +13% y/y; shares ~-3.4% premkt \u2014 IB slowdown + securities loss</td></tr>'
    '<tr><td>GS</td><td><span class="timing reported">REPORTED</span></td>'
    '<td class="c-acc" style="font-weight:700">EPS $17.01 (beat)</td>'
    '<td style="font-size:10px;color:var(--sub)">18.7% annualized ROE; 2nd-best revenue quarter ever</td></tr>'
    '<tr><td>WFC</td><td><span class="timing reported">REPORTED</span></td>'
    '<td class="c-warn" style="font-weight:700">Profit up, revenue light</td>'
    '<td style="font-size:10px;color:var(--sub)">Profit rose on loan growth/NII; revenue missed; shares -1%</td></tr>'
    '<tr><td>C</td><td><span class="timing reported">REPORTED</span></td>'
    '<td class="c-acc" style="font-weight:700">Beat profit estimates</td>'
    '<td style="font-size:10px;color:var(--sub)">Best bond-trading quarter in a decade (exact EPS/rev not independently sourced today)</td></tr>'
    '<tr><td>JNJ</td><td><span class="timing reported">REPORTED</span></td>'
    '<td class="c-acc" style="font-weight:700">Adj. EPS $2.59 (beat $2.52 est.)</td>'
    '<td style="font-size:10px;color:var(--sub)">Revenue $25.4B +5.9% y/y; raised FY26 guidance; shares -0.9% premkt anyway</td></tr>'
    '<tr><td>UNH</td><td><span class="timing reported">REPORTED</span></td>'
    '<td class="c-acc" style="font-weight:700">EPS $4.69 (beat $4.15 est.)</td>'
    '<td style="font-size:10px;color:var(--sub)">Revenue $112.69B vs $111.40B est.; shares +2.6% premkt</td></tr>'
)

sections[K_SECTORS] = (
    '<div class="sector-row"><span class="sec-etf">XLE</span><span class="sec-name">Energy</span>'
    '<div class="sec-bar-wrap"><div class="sec-bar" style="width:89%;background:var(--safe)"></div></div>'
    '<span class="sec-val c-safe">+1.03%</span></div>'
    '<div class="sector-row"><span class="sec-etf">XLC</span><span class="sec-name">Communication Services</span>'
    '<div class="sec-bar-wrap"><div class="sec-bar" style="width:75%;background:var(--safe)"></div></div>'
    '<span class="sec-val c-safe">+0.87%</span></div>'
    '<div class="sector-row"><span class="sec-etf">XLF</span><span class="sec-name">Financials</span>'
    '<div class="sec-bar-wrap"><div class="sec-bar" style="width:43%;background:var(--safe)"></div></div>'
    '<span class="sec-val c-safe">+0.50%</span></div>'
    '<div class="sector-row"><span class="sec-etf">XLP</span><span class="sec-name">Consumer Staples</span>'
    '<div class="sec-bar-wrap"><div class="sec-bar" style="width:40%;background:var(--safe)"></div></div>'
    '<span class="sec-val c-safe">+0.46%</span></div>'
    '<div class="sector-row"><span class="sec-etf">XLRE</span><span class="sec-name">Real Estate</span>'
    '<div class="sec-bar-wrap"><div class="sec-bar" style="width:37%;background:var(--safe)"></div></div>'
    '<span class="sec-val c-safe">+0.43%</span></div>'
    '<div class="sector-row"><span class="sec-etf">XLY</span><span class="sec-name">Consumer Discretionary</span>'
    '<div class="sec-bar-wrap"><div class="sec-bar" style="width:24%;background:var(--danger)"></div></div>'
    '<span class="sec-val c-bad">-0.28%</span></div>'
    '<div class="sector-row"><span class="sec-etf">XLK</span><span class="sec-name">Technology</span>'
    '<div class="sec-bar-wrap"><div class="sec-bar" style="width:100%;background:var(--danger)"></div></div>'
    '<span class="sec-val c-bad">-1.16%</span></div>'
)

sections[K_S07_GAIN] = (
    '<tr><td>UNH</td><td><span class="pm-cat pm-earn">EARNINGS</span> <span class="pm-cat pm-beat">BEAT</span></td>'
    '<td class="c-safe" style="font-weight:700;text-align:right;font-family:\'Space Mono\',monospace">+2.6%</td>'
    '<td style="font-size:10px;color:var(--sub)">Q3 EPS $4.69 vs $4.15 est., rev $112.69B vs $111.40B est. \u2014 CNBC/Benzinga</td></tr>'
)

sections[K_S07_DECL] = (
    '<tr><td>JPM</td><td><span class="pm-cat pm-earn">EARNINGS</span> <span class="pm-cat pm-miss">RARE MISS</span></td>'
    '<td class="c-bad" style="font-weight:700;text-align:right;font-family:\'Space Mono\',monospace">~-3.4%</td>'
    '<td style="font-size:10px;color:var(--sub)">IB slowdown + securities loss, despite EPS +10% y/y, NII +13% y/y \u2014 TheStreet</td></tr>'
    '<tr><td>MU</td><td><span class="pm-cat pm-geo">SECTOR</span> <span class="pm-cat pm-miss">CHIP ROUT</span></td>'
    '<td class="c-bad" style="font-weight:700;text-align:right;font-family:\'Space Mono\',monospace">-3.2%</td>'
    '<td style="font-size:10px;color:var(--sub)">China CXMT competition fears; Kospi -5.5%, Samsung -7.4% overnight \u2014 BNN Bloomberg</td></tr>'
    '<tr><td>MRVL</td><td><span class="pm-cat pm-geo">SECTOR</span> <span class="pm-cat pm-miss">CHIP ROUT</span></td>'
    '<td class="c-bad" style="font-weight:700;text-align:right;font-family:\'Space Mono\',monospace">-2.6%</td>'
    '<td style="font-size:10px;color:var(--sub)">Same memory/AI-chip competition scare \u2014 BNN Bloomberg</td></tr>'
    '<tr><td>WFC</td><td><span class="pm-cat pm-earn">EARNINGS</span> <span class="pm-cat pm-miss">REV LIGHT</span></td>'
    '<td class="c-bad" style="font-weight:700;text-align:right;font-family:\'Space Mono\',monospace">-1.0%</td>'
    '<td style="font-size:10px;color:var(--sub)">Profit up on loan growth/NII, but revenue missed \u2014 BNN Bloomberg</td></tr>'
    '<tr><td>JNJ</td><td><span class="pm-cat pm-earn">EARNINGS</span> <span class="pm-cat pm-miss">BEAT, SLIPPED</span></td>'
    '<td class="c-bad" style="font-weight:700;text-align:right;font-family:\'Space Mono\',monospace">-0.9%</td>'
    '<td style="font-size:10px;color:var(--sub)">Beat adj. EPS and raised FY26 guidance, stock fell anyway \u2014 Barron\u2019s</td></tr>'
)

sections[K_ALERTS] = (
    '<div class="alert-row"><div class="alert-dot adot-r"></div><div class="alert-txt">'
    '<strong>Chip/memory sector rout spreading from Asia.</strong> Kospi closed -5.5% (Samsung -7.4%, '
    'SK Hynix -10.1%) on fears China\u2019s CXMT could challenge the memory oligopoly; Micron -3.2%, '
    'Marvell -2.6% premarket here.</div></div>'
    '<div class="alert-row"><div class="alert-dot adot-y"></div><div class="alert-txt">'
    '<strong>Bank earnings mixed as season opens.</strong> JPMorgan: rare miss (IB slowdown, securities '
    'loss) despite EPS +10% y/y, shares ~-3.4% premkt. Goldman: EPS $17.01, 2nd-best revenue quarter '
    'ever. Citi: best bond-trading quarter in a decade. Wells Fargo: profit up, revenue light, -1%.</div></div>'
    '<div class="alert-row"><div class="alert-dot adot-y"></div><div class="alert-txt">'
    '<strong>Houthi-Saudi escalation + Hormuz tanker strike.</strong> Threat alerts hit Riyadh and Khamis '
    'Mushait Monday; a products tanker was struck by an unknown projectile in the Strait of Hormuz near '
    'Oman. Iran has offered to mediate; oil is still down ~2% on truce hopes.</div></div>'
    '<div class="alert-row"><div class="alert-dot adot-y"></div><div class="alert-txt">'
    '<strong>Schwab data feed still down \u2014 2nd straight session.</strong> Refresh token remains stale '
    '(HTTP 400); no real /ES or /NQ futures ticks today either.</div></div>'
)

sections[K_EVENTS] = (
    '<div class="alert-row"><div class="alert-dot adot-g"></div><div class="alert-txt">'
    '<strong>Bank/healthcare earnings BMO.</strong> JPM, GS, WFC, C, JNJ and UNH all reported this '
    'morning \u2014 see Catalyst Alert and Earnings Watch for results.</div></div>'
    '<div class="alert-row"><div class="alert-dot adot-y"></div><div class="alert-txt">'
    '<strong>CPI lands tomorrow (Wed).</strong> September CPI is the week\u2019s real catalyst; PPI and '
    'retail sales are expected to follow later this week.</div></div>'
    '<div class="alert-row"><div class="alert-dot adot-y"></div><div class="alert-txt">'
    '<strong>Chip-sector contagion from Asia.</strong> Kospi -5.5%, Nikkei -1.8%, Taiex and TSMC each '
    '-2% overnight on CXMT competition fears.</div></div>'
)

sections[K_ACTIONABLES] = (
    '<div class="alert-row"><div class="alert-dot adot-r"></div><div class="alert-txt">'
    '<strong>Don\u2019t size /ES or /NQ off any \u2018pivot\u2019 today.</strong> Schwab feed is down a 2nd '
    'straight session; sourced futures-adjacent context only (S&amp;P 500 E-mini -10pts/-0.13%, '
    'Nasdaq-100 E-mini -182.25pts/-0.59%, per Reuters ~6:54am ET).</div></div>'
    '<div class="alert-row"><div class="alert-dot adot-y"></div><div class="alert-txt">'
    '<strong>Chip/memory names are today\u2019s real risk-off trade, not the index.</strong> Micron -3.2%, '
    'Marvell -2.6%, Nvidia/AMD -1% to -1.5% premarket; Asia already took the bigger hit overnight.</div></div>'
    '<div class="alert-row"><div class="alert-dot adot-y"></div><div class="alert-txt">'
    '<strong>Earnings reactions are inverted today \u2014 fade the headline, not the number.</strong> '
    'GS/C/UNH/JNJ all beat and some still slipped; JPM missed but the ~-3.4% stock move overstates a '
    'business that still grew NII 13% y/y.</div></div>'
)

sections[K_REGIME] = (
    '<div class="reg-div"></div><div class="reg-item">Bank earnings season opens \u2014 JPM rare miss; '
    'GS, C, UNH, JNJ all beat (JNJ raised FY26 guidance)</div>'
    '<div class="reg-div"></div><div class="reg-item">Chip/memory sector selloff \u2014 Kospi -5.5% overnight, '
    'Micron -3.2% / Marvell -2.6% premkt</div>'
    '<div class="reg-div"></div><div class="reg-item">CPI due tomorrow (Wed); PPI + retail sales expected '
    'to follow later this week</div>'
    '<div class="reg-div"></div><div class="reg-item">Oil down ~2% (Brent $104.62, WTI $91.78) despite live '
    'Houthi-Saudi/Hormuz tanker risk</div>'
)

sections[K_BBM] = (
    '<div class="bbm-signal-row"><span class="bbm-sn">Price Trend (Dow near record, SPX/NDX flat-to-soft)</span>'
    '<span class="bbm-sv-neut">NEUT</span></div>'
    '<div class="bbm-signal-row"><span class="bbm-sn">Bank Earnings (GS/C/UNH/JNJ beat, JPM rare miss, WFC light rev)</span>'
    '<span class="bbm-sv-neut">NEUT</span></div>'
    '<div class="bbm-signal-row"><span class="bbm-sn">Chip/Memory Breakdown (Kospi -5.5%, Samsung -7.4%, Micron -3.2%)</span>'
    '<span class="bbm-sv-bear">BEAR</span></div>'
    '<div class="bbm-signal-row"><span class="bbm-sn">AAII (39.0% bear vs 40.3% bull, unch. wk, still above-avg pessimism)</span>'
    '<span class="bbm-sv-neut">CAUTION</span></div>'
    '<div class="bbm-signal-row"><span class="bbm-sn">Geopolitical (Houthi/Saudi escalation, Hormuz tanker strike)</span>'
    '<span class="bbm-sv-bear">CAUTION</span></div>'
    '<div class="bbm-signal-row"><span class="bbm-sn">VIX (15.3, calm, sub-16)</span>'
    '<span class="bbm-sv-bull">BULL</span></div>'
    '<div class="bbm-signal-row"><span class="bbm-sn">Oil (Brent/WTI -2% despite live Mideast risk \u2014 truce hopes)</span>'
    '<span class="bbm-sv-neut">NEUT</span></div>'
)

sections[K_SPOTLIGHT] = (
    '<div class="spot-item"><div class="spot-hd"><span class="spot-tk">JPM / Banks</span></div>'
    '<div class="spot-body">Earnings season\u2019s open was a legitimate split: JPMorgan\u2019s rare miss '
    '(~-3.4% premkt) despite EPS +10% y/y masks a genuine investment-banking/trading-mix issue, not a '
    'credit problem \u2014 NII still grew 13% y/y. Goldman (EPS $17.01, 2nd-best revenue quarter ever) and '
    'Citi (best bond-trading quarter in a decade) both beat; whether that holds through the open is the '
    'real tell for financials today.</div></div>'
    '<div class="spot-item"><div class="spot-hd"><span class="spot-tk">Chip / Memory</span></div>'
    '<div class="spot-body">Korea\u2019s Kospi closed -5.5% overnight (Samsung -7.4%, SK Hynix -10.1%) on '
    'fears China\u2019s CXMT could break into the memory oligopoly \u2014 Micron -3.2% and Marvell -2.6% are '
    'carrying that into the U.S. premarket. This reads as a competition-fear repricing, not a demand '
    'problem; watch for an analyst or CEO rebuttal as the catalyst for a reversal.</div></div>'
    '<div class="spot-item"><div class="spot-hd"><span class="spot-tk">UNH / JNJ</span></div>'
    '<div class="spot-body">UnitedHealth (+2.6% premkt) and Johnson &amp; Johnson (beat + raised guidance, '
    'yet -0.9%) are the clearest \u2018quality of the beat matters more than the headline\u2019 pair today \u2014 '
    'UNH\u2019s beat was unambiguous, JNJ\u2019s was muddied by a one-time talc-related charge that dragged '
    'reported EPS to $0.09 even as adjusted EPS cleared estimates.</div></div>'
)

sections[K_OPTIONS] = (
    '<div class="opt-item"><div class="opt-hd"><span class="opt-tk">Bank-earnings vol</span></div>'
    '<div class="opt-body">No sized options idea into today\u2019s bank-earnings reactions \u2014 current '
    'IV/skew wasn\u2019t independently sourced today. Note only: IV on JPM/GS/WFC/C typically richens into '
    'the print and crushes right after; chasing a post-print move with options needs a real edge, not '
    'just the calendar.</div></div>'
    '<div class="opt-item"><div class="opt-hd"><span class="opt-tk">TLT / XLU crowded calls</span></div>'
    '<div class="opt-body">Still the trade to watch into tomorrow\u2019s CPI \u2014 record call volume hit both '
    'last week (sourced then, not re-verified live today) on rate-cut conviction. A hot print would force '
    'the fastest unwind of that bet.</div></div>'
)

sections[K_MONEYFLOW] = (
    '<div class="mf-item"><div class="mf-name">Dark Pool / Block Prints</div>'
    '<div class="mf-val c-warn">NOT SOURCED TODAY</div></div>'
)

sections[K_UNUSUAL] = (
    '<div class="uo-item"><div class="uo-hd"><span class="uo-tk">TLT</span>'
    '<span class="uo-exp">Weekly call volume</span></div>'
    '<div class="uo-body c-warn">~15M contracts last week (record) \u2014 crowded long-duration bet via '
    'calls; last week\u2019s desk sourcing, not a live chain read today.</div></div>'
    '<div class="uo-item"><div class="uo-hd"><span class="uo-tk">XLU</span>'
    '<span class="uo-exp">Weekly call volume</span></div>'
    '<div class="uo-body c-warn">~2.2M contracts (record) \u2014 same rate-cut-conviction trade via '
    'utilities; unwind risk into tomorrow\u2019s CPI.</div></div>'
)

sections[K_TRADEROWS] = (
    K_TRADEROWS +
    '<tr><td>1</td><td><strong>BTC</strong></td><td><span class="t-type ts">STOCK</span></td>'
    '<td class="t-long">LONG</td><td>Bounce off 50-day avg after Monday\u2019s dip</td>'
    '<td class="mono">83,345</td><td class="mono c-bad">81,900.00</td><td class="mono c-safe">86,500.00</td>'
    '<td class="t-rr">1:2.2</td>'
    '<td>50d avg $81,022 / 200d avg $72,045 per FMP; stop under today\u2019s $81,198 day low, target retests '
    'the Oct 4 local high ($86,507 area).</td><td class="t-pri">\u2605\u2605</td></tr>'
    '<tr><td>2</td><td><strong>ETH</strong></td><td><span class="t-type ts">STOCK</span></td>'
    '<td class="t-long">LONG</td><td>Mean-reversion toward 50-day avg</td>'
    '<td class="mono">2,509</td><td class="mono c-bad">2,419.00</td><td class="mono c-safe">2,580.00</td>'
    '<td class="t-rr">1:0.8</td>'
    '<td>Trading ~1.8% below its $2,555.78 50d avg per FMP after today\u2019s +2.65% bounce; stop under '
    'today\u2019s $2,419.05 day low. Sub-1 R:R \u2014 tactical, not high-conviction.</td><td class="t-pri">\u2605</td></tr>'
    '<tr><td colspan="11" style="color:var(--muted);font-size:9px;padding-top:10px">/ES and /NQ futures '
    'setups omitted today (2nd straight session) \u2014 Schwab refresh token is stale (HTTP 400), no real '
    'settlement/pivot/VAH/POC/VAL to grade against. No sized bank/chip-earnings trade today given no live '
    'options/chain data. See Section 05 Pipeline Note.</td></tr>'
)

flat["INJECTED_SECTIONS"] = sections

OUT_PATH.write_text(json.dumps(flat, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")

# ============================================================
# Simulate the render exactly as fetch_mmm_data.py's render() does:
# INJECTED_SECTIONS first (against pristine template), then flat token pass.
# ============================================================
rendered = template
for k, v in sections.items():
    c = rendered.count(k)
    if c != 1:
        print(f"MARKER MATCH FAILURE: count={c} for key starting {k[:80]!r}")
        sys.exit(1)
    rendered = rendered.replace(k, v)

for k, v in flat.items():
    if k == "INJECTED_SECTIONS":
        continue
    rendered = rendered.replace("{{" + k + "}}", v)

Path("_sim_rendered_1013.html").write_text(rendered, encoding="utf-8")

import re
stray = re.findall(r"\{\{[A-Z0-9_]+\}\}", rendered)
pending = "PENDING" in rendered
print("Stray tokens:", sorted(set(stray)))
print("Contains PENDING:", pending)
if stray or pending:
    sys.exit(1)
print("SIMULATION OK: no stray tokens, no PENDING markers.")
