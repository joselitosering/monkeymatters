#!/usr/bin/env python3
"""
generate_weekly.py — WEEKLY RECAP TEMPLATE v1.0 — LOCKED (2026-08-17, per Joe)
Theme: APEX design system, extracted verbatim from the pinned Cowork artifact
"Morning Market Monitor Shadowmonkey" (templates/apex_theme.css — do not fork).
Locked layout: header/classification → 01 scoreboard → 02 week-in-review →
03 macro trackers (S&P, Nasdaq, Gold, Silver, BTC, ETH, Brent, $DXY) →
04 session ledger → 05 scorecards → 06 thesis+lessons → 07 receipts →
08 forward guidance → 09 sortable full board → 10 coverage → footer.
Content/data flows may evolve; layout & theme changes require explicit unlock.
Sections: scoreboard · week-in-review market recap · day tiles · scorecards ·
thesis review · lessons · best/worst/discipline · forward guidance ·
sortable+filterable full board · coverage & method.
Stats are 100% deterministic from data/outcomes + data/daily + data/prices.
Narrative blocks come from the analysis tier (free models in production),
grounded in the same graded record.
"""
import json, html
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEEK = "2026-W33"
DAYS = ["2026-08-11", "2026-08-12", "2026-08-13", "2026-08-14"]
DOW = {"2026-08-11": "Tue", "2026-08-12": "Wed", "2026-08-13": "Thu", "2026-08-14": "Fri"}

daily = {d: json.load(open(ROOT/"data"/"daily"/f"{d}.json")) for d in DAYS}
outc  = {d: json.load(open(ROOT/"data"/"outcomes"/f"{d}.json")) for d in DAYS}
ideas = {i['id']: i for d in DAYS for i in daily[d]['trade_ideas']}
res   = {r['id']: r for d in DAYS for r in outc[d]['results']}
GRADED = ('win', 'loss', 'scratch')

# ---------------------------------------------------------------- stats
def bd(keyfn):
    agg = defaultdict(lambda: dict(n=0, triggered=0, wins=0, losses=0, total_r=0.0))
    for iid, r in res.items():
        a = agg[keyfn(ideas[iid])]; a['n'] += 1
        if r.get('triggered'): a['triggered'] += 1
        if r['result'] == 'win': a['wins'] += 1
        if r['result'] == 'loss': a['losses'] += 1
        if r['result'] in GRADED: a['total_r'] = round(a['total_r'] + (r.get('r_multiple') or 0), 2)
    for a in agg.values():
        wl = a['wins'] + a['losses']
        if wl: a['win_rate'] = round(a['wins'] / wl, 3)
    return dict(agg)

counts = defaultdict(int)
for r in res.values(): counts[r['result']] += 1
graded = [r for r in res.values() if r['result'] in GRADED]
wins = [r for r in graded if r['result'] == 'win']
losses = [r for r in graded if r['result'] == 'loss']
total_r = round(sum(r.get('r_multiple') or 0 for r in graded), 2)
curve, cum = [], 0.0
for d in DAYS:
    dr = round(sum((r.get('r_multiple') or 0) for r in outc[d]['results'] if r['result'] in GRADED), 2)
    cum = round(cum + dr, 2)
    curve.append(dict(date=d, r=dr, cum_r=cum))
best = max(graded, key=lambda r: r.get('r_multiple') or 0, default=None)
worst = min(graded, key=lambda r: r.get('r_multiple') or 0, default=None)

stats = dict(
    ideas_total=len(res), triggered=sum(1 for r in res.values() if r.get('triggered')),
    wins=len(wins), losses=len(losses),
    no_trigger=counts['no_trigger'], indeterminate=counts['indeterminate'],
    no_data=counts['no_data'] + counts.get('ungradable', 0),
    win_rate=round(len(wins) / max(1, len(wins) + len(losses)), 3), total_r=total_r,
    expectancy_r=round(total_r / max(1, len(graded)), 2),
    by_setup=bd(lambda i: i['setup'][:28]), by_direction=bd(lambda i: i['direction']),
    by_instrument=bd(lambda i: i['instrument']), by_priority=bd(lambda i: f"P{i.get('priority',1)}"),
    by_day=bd(lambda i: i['id'][:10]), daily_r_curve=curve)

# ------------------------------------------------- market week (from real bars)
def wkchg(series):
    b = json.load(open(ROOT/'data'/'prices'/f'{series}.json'))
    d0 = next(x for x in b if x['date'] == '2026-08-07')
    d1 = next(x for x in b if x['date'] == '2026-08-14')
    return d1['close'], round(100 * (d1['close']/d0['close'] - 1), 2)

MKT = {label: wkchg(s) for label, s in [
    ("S&P 500", "IDX_GSPC"), ("Nasdaq Comp", "IDX_IXIC"), ("Gold (spot)", "GCUSD"),
    ("Silver (spot)", "SIUSD"), ("Bitcoin", "BTCUSD"), ("Ethereum", "ETHUSD"),
    ("Brent Crude", "BZUSD")]}
# ── $DXY — TRUE dollar index. Primary source: Schwab leg writes data/prices/DXY.json
#    (nightly, once OAuth lands). Until then: cited analyst level, change flagged approx.
try:
    MKT["USD Index ($DXY)"] = wkchg('DXY')
    DXY_NOTE = "DXY weekly bars via Schwab cache (data/prices/DXY.json)"
except FileNotFoundError:
    MKT["USD Index ($DXY)"] = (99.84, None)   # None change -> tile renders '≈ FLAT WK'
    DXY_NOTE = ("DXY ~99.84, 'roughly flat on the week' — OneUp Trader DXY technical analysis, "
                "Aug 14 2026 (blog.oneuptrader.com). Precise weekly bars land with the Schwab $DXY leg.")

DAY_CATALYST = {
    "2026-08-11": "CPI-eve positioning — defined-risk spreads and hedges; semis weak post-earnings (COHR, GFS, LITE)",
    "2026-08-12": "CPI: MoM in line (+0.1%) but YoY re-accelerated to 3.4% — rate-hike fear bid, 10Y 4.72%; CSCO ATM straddle set AMC",
    "2026-08-13": "PPI 0.0% MoM — clean disinflation flips the tape BULL; ATH push; CSCO −8.4% pays the straddles; BIRK/DELL/AMBP BMO beats",
    "2026-08-14": "Retail Sales −0.6% + UMich 51.0 double miss — stagflation fork; WMT beat but no-trigger; index longs bleed into the close",
}

WEEK_IN_REVIEW = (
    "A whipsaw macro week that ended almost exactly where it started — S&P 500 +0.36%, Nasdaq +0.14% — "
    "but the path was violent. Tuesday was CPI-eve caution. Wednesday's CPI opened the relief valve on the monthly print "
    "(+0.1% MoM) while YoY re-accelerated to 3.4%, briefly resurrecting rate-HIKE fear with the 10Y at 4.72%. "
    "Thursday's 0.0% PPI flipped the entire tape: regime went BULL, indexes pushed toward highs, and Cisco's −8.4% "
    "earnings gap paid both straddles. Friday broke the rally's back — Retail Sales −0.6% and UMich 51.0, the week's "
    "second regime flip, this time into the stagflation fork. Hard assets told the real story: gold +0.85%, silver +2.53%, "
    "and Brent crude +5.95% on the week (the Hormuz tension bid) while the middle-market consumer names cracked. "
    "Two cross-checks worth logging: the dollar barely moved (UUP +0.14%), so the hard-asset bid was fear, not dollar "
    "debasement — and Bitcoin fell 2.95% (ETH −1.71%) in the very week the 'rate cuts = crypto bullish' narrative anchored "
    "the HIVE thesis. Crypto is not yet confirming the rate-cut trade. Three regimes in four sessions; the scoreboard "
    "below is what our ideas did inside that chop.")

NARRATIVE = dict(
    thesis_review=[
        dict(thesis="Event-volatility edge (CSCO earnings straddles)", days_active=["2026-08-11", "2026-08-12"],
             verdict="confirmed",
             evidence="Both CSCO straddles graded WIN: CSCO fell 8.4% on its Aug 13 report vs stated 3% and 8% expected-move thresholds, and finished the week −8.03%. 2-for-2 — the only setup class that went undefeated."),
        dict(thesis="Rate-cut repricing index longs (/ES, /NQ)", days_active=["2026-08-13", "2026-08-14"],
             verdict="mixed",
             evidence="Thursday confirmed: /ES OR-Break R1 long hit target (+0.79R, SPX 7,763→7,798) on the PPI disinflation flip. Friday refuted intraday: both index longs closed red (−0.56R, −0.32R) as the stagflation fork resolved bearish into the close — exactly the risk Friday's own advisory flagged."),
        dict(thesis="Gold as inflation/stagflation hedge", days_active=["2026-08-12", "2026-08-13", "2026-08-14"],
             verdict="mixed",
             evidence="Split decision that vindicates entry discipline. Thursday's long from 4,430 gapped in at 4,468 and stopped at 4,400 (−1R) on the intraday fade. Friday's re-entry above the pre-market high caught the rebound and closed the week positive. Gold finished +0.85%, silver +2.53% — the thesis was right; only the gapped fill lost money."),
        dict(thesis="TLT rate-cut macro long — 'trade of the week'", days_active=["2026-08-13", "2026-08-14"],
             verdict="unresolved",
             evidence="Ungradable this run: TLT price history is not on the current FMP plan. The Alpha Vantage key now in .env closes this gap — next automated run grades TLT with intraday bars."),
    ],
    lessons_candidates=[
        dict(rule="Keep taking event straddles that state an explicit expected-move threshold; skip ones that don't.",
             evidence="2/2 wins (CSCO Aug 11 + Aug 12); straddles without stated thresholds were ungradable — unmeasurable means unaccountable.",
             supporting_ids=["2026-08-11-T21", "2026-08-12-T06"], action="watch"),
        dict(rule="Stand down when the open gaps beyond the entry/stop/target geometry — don't chase re-anchored entries.",
             evidence="Two /NQ setups were invalidated by gap-opens and three more had entries re-anchored so far from plan that R:R degraded to near zero. The GLD stop-out was the same disease: planned 4,430, filled 4,468, stopped 4,400.",
             supporting_ids=["2026-08-11-T07", "2026-08-12-T13", "2026-08-13-T08", "2026-08-13-T09"], action="adopt"),
        dict(rule="On macro-miss days (Retail Sales/UMich type), index longs held to the close bled: enforce the PP-hold confirmation the advisory itself demanded before sizing intraday index longs.",
             evidence="Friday's two index longs both closed negative (−0.88R combined) on the double-miss day; the day's own advisory said 'below PP = sidelines'.",
             supporting_ids=["2026-08-14-T01", "2026-08-14-T06"], action="watch"),
    ],
    forward_guidance=dict(
        posture_next_week="Coverage first, conviction second: the Alpha Vantage key is loaded — first automated run re-grades this week at intraday fidelity and unlocks TLT, sector ETFs, and the small caps. Trade-wise: respect the two-flip week — regime is unstable, so defined-risk event structures (the week's only undefeated class) over naked directional conviction. Treat gap-opens as a stand-down signal, not a chase signal.",
        watchlist=["CSCO post-earnings drift", "/ES PP reclaim vs stagflation follow-through", "Gold 4,400 floor retest (thesis alive, entries disciplined)", "TLT once intraday coverage lands", "HIVE/BTC correlation (VWAP entries gradable next run)"],
        key_events_next_week=["FOMC minutes Wed", "HD housing read-through", "Weekly claims Thu", "Flash PMIs Fri"]))

weekly = dict(schema_version=1, week=WEEK,
              date_range=dict(start=DAYS[0], end=DAYS[-1]),
              generated_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds'),
              days_included=DAYS, stats=stats,
              highlights=dict(
                  best_call=dict(id=best['id'], symbol=best['symbol'], setup=ideas[best['id']]['setup'],
                                 r_multiple=best.get('r_multiple'),
                                 story="CSCO event straddle: 8.4% post-earnings move vs 3% stated threshold.") if best else None,
                  worst_call=dict(id=worst['id'], symbol=worst['symbol'], setup=ideas[worst['id']]['setup'],
                                  r_multiple=worst.get('r_multiple'),
                                  story="Gold hedge long gapped in at 4,468 vs 4,430 plan; stopped 4,400 on the intraday fade.") if worst else None,
                  biggest_no_trigger_regret=dict(id="2026-08-14-T03", symbol="WMT", setup="Gap-and-Go BMO Beat",
                                                 r_multiple=0.0,
                                                 story="WMT never crossed PM-High+1% — the entry rule correctly kept us out of a flat tape.")),
              coverage=dict(graded=len(graded), no_trigger=counts['no_trigger'],
                            indeterminate=counts['indeterminate'],
                            no_data=counts['no_data'] + counts.get('ungradable', 0),
                            notes="Daily-bar grading v1. no_data = symbol not on current FMP plan (TLT, QQQ, sector ETFs, small/mid caps) — Alpha Vantage key now staged to close this. indeterminate = needs intraday bars (VWAP/OR entries, same-bar stop+target) or the level/data-mismatch guard."),
              market_week=dict(week_in_review=WEEK_IN_REVIEW,
                               kpis={k: dict(close=v[0], change_pct=v[1]) for k, v in MKT.items()},
                               dxy_source=DXY_NOTE,
                               day_catalysts=DAY_CATALYST),
              **NARRATIVE)

(ROOT/"data"/"weekly").mkdir(parents=True, exist_ok=True)
json.dump(weekly, open(ROOT/"data"/"weekly"/f"{WEEK}.json", "w"), indent=2)

# ---------------------------------------------------------------- HTML (APEX brand)
# Theme source: pinned Cowork artifact "Morning Market Monitor Shadowmonkey" —
# full APEX design system CSS embedded verbatim from templates/apex_theme.css.
E = html.escape
APEX_CSS = open(ROOT/"templates"/"apex_theme.css").read()

CHIP = dict(win=('WIN', 'var(--safe)'), loss=('LOSS', 'var(--danger)'),
            scratch=('SCRATCH', 'var(--sub)'), no_trigger=('NO TRIGGER', 'var(--accent3)'),
            indeterminate=('INDET', 'var(--warn)'), no_data=('NO DATA', 'var(--muted)'),
            ungradable=('N/G', 'var(--muted)'))

def chip(result):
    lbl, c = CHIP.get(result, (result.upper(), 'var(--sub)'))
    return (f'<span style="font-family:\'Space Mono\',monospace;font-size:9px;letter-spacing:1px;'
            f'padding:1px 6px;border:1px solid {c};color:{c};white-space:nowrap">{lbl}</span>')

def rfmt(r):
    v = r.get('r_multiple')
    if v is None: return '<span style="color:var(--muted)">&mdash;</span>'
    c = 'var(--safe)' if v > 0 else ('var(--danger)' if v < 0 else 'var(--sub)')
    return f'<span class="mono" style="color:{c};font-weight:700">{v:+.2f}R</span>'

def cval(x):  # tile color class by sign
    return 'c-safe' if x > 0 else ('c-bad' if x < 0 else 'c-sub')

RESULT_ORDER = dict(win=0, loss=1, scratch=2, no_trigger=3, indeterminate=4, no_data=5, ungradable=5)
rows = []
for d in DAYS:
    for i in daily[d]['trade_ideas']:
        r = res[i['id']]
        rm = r.get('r_multiple')
        dirc = 'var(--safe)' if i['direction'] == 'long' else 'var(--danger)' if i['direction'] == 'short' else 'var(--sub)'
        rows.append(
            f'<tr data-day="{DOW[d]}" data-result="{r["result"]}" data-dir="{i["direction"]}" '
            f'data-sym="{E(i["symbol"].upper())}" data-r="{rm if rm is not None else -999}" '
            f'data-rorder="{RESULT_ORDER.get(r["result"], 9)}">'
            f'<td class="mono">{DOW[d]} {d[-2:]}</td><td><strong>{E(i["symbol"])}</strong></td>'
            f'<td style="color:var(--sub)">{E(i["instrument"])}</td>'
            f'<td style="color:{dirc};font-weight:700">{i["direction"].upper()}</td>'
            f'<td style="color:var(--sub)">{E(i["setup"][:34])}</td>'
            f'<td class="mono" style="color:var(--accent3)">{E((i.get("entry") or {}).get("raw") or str((i.get("entry") or {}).get("value") or "—"))[:18]}</td>'
            f'<td>{chip(r["result"])}</td><td>{rfmt(r)}</td>'
            f'<td style="color:var(--muted);font-size:10px">{E((r.get("notes") or "")[:80])}</td></tr>')

day_tiles = "".join(
    f'<div class="day-card"><div class="st-lbl">{DOW[c["date"]]} &middot; {c["date"][-5:]}</div>'
    f'<div class="st-val {cval(c["r"])}">{c["r"]:+.2f}R</div>'
    f'<div class="st-sub c-sub">cumulative {c["cum_r"]:+.2f}R</div>'
    f'<div class="day-cat">{E(DAY_CATALYST[c["date"]])}</div></div>' for c in curve)

def _mkt_tile(k, v):
    if v[1] is None:
        return (f'<div class="sent-tile"><div class="st-lbl">{E(k)}</div>'
                f'<div class="st-val c-sub" style="font-size:15px">{v[0]:,.2f}</div>'
                f'<div class="st-sub" style="color:var(--muted)">&asymp; FLAT WK &middot; SCHWAB PENDING</div></div>')
    return (f'<div class="sent-tile"><div class="st-lbl">{E(k)}</div>'
            f'<div class="st-val {cval(v[1])}" style="font-size:15px">{v[0]:,.2f}</div>'
            f'<div class="st-sub {cval(v[1])}">{v[1]:+.2f}% WK</div></div>')
mkt_tiles = "".join(_mkt_tile(k, v) for k, v in MKT.items())

def bd_table(title, data, min_n=1):
    items = [(k, v) for k, v in data.items() if v['n'] >= min_n]
    trs = "".join(
        f'<tr><td>{E(str(k))}</td><td class="mono">{v["n"]}</td><td class="mono">{v["wins"]}-{v["losses"]}</td>'
        f'<td class="mono">{"" if v.get("win_rate") is None else format(v["win_rate"]*100, ".0f")+"%"}</td>'
        f'<td class="mono" style="color:{"var(--safe)" if v["total_r"]>0 else "var(--danger)" if v["total_r"]<0 else "var(--sub)"};font-weight:700">{v["total_r"]:+.2f}R</td></tr>'
        for k, v in sorted(items, key=lambda kv: -kv[1]['total_r']))
    return (f'<div class="sm-card"><div class="card-hd">{title}</div>'
            f'<table class="etbl"><tr><th>Bucket</th><th>N</th><th>W-L</th><th>Win%</th><th>R</th></tr>{trs}</table></div>')

verd_c = dict(confirmed='var(--safe)', refuted='var(--danger)', mixed='var(--warn)', unresolved='var(--muted)')
thesis_html = "".join(
    f'<div class="spot-item"><div class="spot-hd"><span class="spot-tk">{E(t["thesis"])}</span>'
    f'<span class="tag" style="border-color:{verd_c[t["verdict"]]};color:{verd_c[t["verdict"]]}">{t["verdict"].upper()}</span></div>'
    f'<div class="spot-body">{E(t["evidence"])}</div></div>' for t in NARRATIVE['thesis_review'])

lessons_html = "".join(
    f'<div class="spot-item"><div class="spot-hd">'
    f'<span class="tag" style="border-color:{"var(--safe)" if l["action"]=="adopt" else "var(--warn)"};color:{"var(--safe)" if l["action"]=="adopt" else "var(--warn)"}">{l["action"].upper()}</span>'
    f'<span class="mono" style="font-size:9px;color:var(--muted)">{len(l["supporting_ids"])} SUPPORTING IDEAS</span></div>'
    f'<div class="spot-body"><strong style="color:var(--text)">{E(l["rule"])}</strong><br>{E(l["evidence"])}</div></div>'
    for l in NARRATIVE['lessons_candidates'])

cov = weekly['coverage']
series_str = ", ".join(sorted(p.stem.replace('IDX_', '^') for p in (ROOT/'data'/'prices').glob('*.json')))
fg = NARRATIVE['forward_guidance']
gen_ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

EXT_CSS = """
/* ── WEEKLY RECAP EXTENSIONS (APEX tokens) ─────────────────── */
.mkt-strip{display:grid;grid-template-columns:repeat(8,1fr);gap:6px;margin-bottom:14px}
.day-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:14px}
.day-card{background:var(--surface);border:1px solid var(--border);padding:10px 12px}
.day-cat{font-family:'Space Mono',monospace;font-size:9px;color:var(--muted);margin-top:7px;line-height:1.6;border-top:1px solid var(--border);padding-top:6px}
.grid2w{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px}
.grid3w{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px}
.spot-item{margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid var(--border)}
.spot-item:last-child{border-bottom:none;margin-bottom:0;padding-bottom:0}
.spot-hd{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:4px}
.spot-tk{font-weight:700;color:var(--text);font-size:12px}
.spot-body{font-size:11px;color:var(--sub);line-height:1.6}
.sec-label::after{content:"";flex:1;height:1px;background:var(--border)}
.wk-sent{grid-template-columns:repeat(6,1fr)}
@media(max-width:900px){.mkt-strip{grid-template-columns:repeat(4,1fr)}}
@media(max-width:640px){.day-strip,.grid2w,.grid3w{grid-template-columns:1fr}.mkt-strip,.wk-sent{grid-template-columns:repeat(2,1fr)}}
"""

html_doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Weekly Recap &mdash; {WEEK} &mdash; Shadow Monkey / Monkey Matters LLC</title>
<style>{APEX_CSS}
{EXT_CSS}</style></head><body>
<div class="wrap">

<!-- ══ HEADER ══════════════════════════════════════════════ -->
<div class="hdr">
  <div class="hdr-classification">
    <span class="tag tag-red">EYES ONLY</span>
    <span class="tag tag-green">OPERATIVE: SHADOW MONKEY</span>
    <span class="tag tag-muted">HANDLER: JOE</span>
    <span class="tag tag-blue">MONKEY MATTERS LLC</span>
  </div>
  <div class="hdr-top">
    <div class="hdr-title-block">
      <div class="hdr-brand">WEEKLY<br><span>RECAP</span><br>{WEEK}</div>
      <div class="hdr-subtitle">Trade Idea Accountability Report &bull; Week of Aug 11&ndash;14, 2026 &bull; Shadow Monkey / Monkey Matters LLC</div>
    </div>
    <div class="hdr-badges">
      <span class="sm-badge sm-badge-warn">&#x26A0; DAILY-BAR GRADING V1 &middot; PARTIAL COVERAGE</span>
      <span class="sm-badge sm-badge-live">&#x25CF; GRADED VS REAL BARS</span>
    </div>
  </div>
  <div class="hdr-meta-grid">
    <div class="hdr-meta-cell"><div class="hm-label">Session Range</div><div class="hm-val">Tue&ndash;Fri &middot; 4 sessions</div></div>
    <div class="hdr-meta-cell"><div class="hm-label">Record</div><div class="hm-val" style="color:{'var(--safe)' if total_r>0 else 'var(--danger)'}">{stats['wins']}&ndash;{stats['losses']} &middot; {total_r:+.2f}R</div></div>
    <div class="hdr-meta-cell"><div class="hm-label">Ideas Published</div><div class="hm-val">{stats['ideas_total']}</div></div>
    <div class="hdr-meta-cell"><div class="hm-label">Prime Directive</div><div class="hm-val" style="color:var(--accent2)">SURVIVE. COMPOUND. LEGACY.</div></div>
  </div>
</div>

<!-- ══ 01 SCOREBOARD ═══════════════════════════════════════ -->
<div class="sec-label">01 &mdash; WEEK SCOREBOARD</div>
<div class="sent-strip wk-sent">
  <div class="sent-tile"><div class="st-lbl">Ideas Published</div><div class="st-val c-acc3">{stats['ideas_total']}</div><div class="st-sub c-sub">4 SESSIONS</div></div>
  <div class="sent-tile"><div class="st-lbl">Graded W-L</div><div class="st-val c-warn">{stats['wins']}-{stats['losses']}</div><div class="st-sub c-sub">{len(graded)} GRADED &middot; {counts['no_trigger']} NO-TRIGGER</div></div>
  <div class="sent-tile"><div class="st-lbl">Win Rate</div><div class="st-val {'c-safe' if stats['win_rate']>=0.5 else 'c-bad'}">{stats['win_rate']*100:.0f}%</div><div class="st-sub c-sub">OF DECIDED TRADES</div></div>
  <div class="sent-tile"><div class="st-lbl">Total R</div><div class="st-val {cval(total_r)}">{total_r:+.2f}R</div><div class="st-sub c-sub">EXPECTANCY {stats['expectancy_r']:+.2f}R</div></div>
  <div class="sent-tile"><div class="st-lbl">Needs Intraday</div><div class="st-val c-warn">{counts['indeterminate']}</div><div class="st-sub c-sub">INDETERMINATE</div></div>
  <div class="sent-tile"><div class="st-lbl">No Data</div><div class="st-val" style="color:var(--muted)">{cov['no_data']}</div><div class="st-sub c-sub">SCHWAB LEG CLOSES THIS</div></div>
</div>

<!-- ══ 02 WEEK IN REVIEW ═══════════════════════════════════ -->
<div class="sec-label">02 &mdash; THE WEEK IN THE MARKET &middot; THREE REGIMES IN FOUR SESSIONS</div>
<div class="highlight-box" style="margin-bottom:14px">{E(WEEK_IN_REVIEW)}</div>

<!-- ══ 03 MACRO TRACKERS ═══════════════════════════════════ -->
<div class="sec-label">03 &mdash; MACRO TRACKERS &middot; WEEKLY CLOSE</div>
<div class="mkt-strip">{mkt_tiles}</div>

<!-- ══ 04 SESSION LEDGER ═══════════════════════════════════ -->
<div class="sec-label">04 &mdash; SESSION LEDGER &middot; R BY DAY</div>
<div class="day-strip">{day_tiles}</div>

<!-- ══ 05 SCORECARDS ═══════════════════════════════════════ -->
<div class="sec-label">05 &mdash; SCORECARDS &middot; WHERE THE R CAME FROM</div>
<div class="grid2w">
{bd_table("BY INSTRUMENT", stats['by_instrument'])}
{bd_table("BY DIRECTION", stats['by_direction'])}
{bd_table("BY PRIORITY", stats['by_priority'])}
{bd_table("BY SETUP (N&ge;2)", stats['by_setup'], min_n=2)}
</div>

<!-- ══ 06 THESIS REVIEW ════════════════════════════════════ -->
<div class="sec-label">06 &mdash; THESIS REVIEW &middot; NARRATIVES VS RECEIPTS</div>
<div class="grid2w">
<div class="sm-card"><div class="card-hd">&#x1F50D; THESIS REVIEW</div>{thesis_html}</div>
<div class="sm-card"><div class="card-hd">&#x1F4DA; LESSONS &mdash; CANDIDATE RULES FOR NEXT WEEK</div>{lessons_html}
<div class="spot-item"><div class="spot-body" style="color:var(--muted)">Promotion rule: candidates need &ge;5 supporting ideas to go active. ADOPT items enter probation now; WATCH items accumulate evidence. Active lessons are injected into every morning monitor's analysis prompt.</div></div></div>
</div>

<!-- ══ 07 RECEIPTS ═════════════════════════════════════════ -->
<div class="sec-label">07 &mdash; RECEIPTS &middot; BEST / WORST / DISCIPLINE</div>
<div class="grid3w">
<div class="sm-card"><div class="card-hd" style="color:var(--safe)">&#x1F3C6; BEST CALL</div><div class="spot-body">
<strong style="color:var(--safe)">CSCO event straddle ({E(best['id']) if best else ''})</strong><br>
CSCO moved 8.4% on earnings against a 3% stated expected-move threshold, finishing the week &minus;8.03%. Both straddles cashed at {rfmt(best) if best else ''} &mdash; the only undefeated setup class of the week.</div></div>
<div class="sm-card"><div class="card-hd" style="color:var(--danger)">&#x1F4A5; WORST CALL</div><div class="spot-body">
<strong style="color:var(--danger)">GLD hedge long ({E(worst['id']) if worst else ''})</strong><br>
Planned entry 4,430 &mdash; gold gapped in at 4,468, faded 4,509&rarr;4,400 intraday, stopped for {rfmt(worst) if worst else ''}. The sting: gold still closed the week +0.85%. Right thesis, undisciplined fill.</div></div>
<div class="sm-card"><div class="card-hd" style="color:var(--accent3)">&#x1F9CA; DISCIPLINE SAVE</div><div class="spot-body">
<strong style="color:var(--accent3)">WMT gap-and-go (2026-08-14-T03)</strong><br>
WMT never crossed PM-High+1% on Friday &mdash; the entry rule kept us flat in a tape that closed below its open. No-trigger is a result, not a miss: the rule did its job.</div></div>
</div>

<!-- ══ 08 FORWARD GUIDANCE ═════════════════════════════════ -->
<div class="sec-label">08 &mdash; FORWARD GUIDANCE &middot; WEEK OF AUG 17</div>
<div class="sm-card" style="border-left:3px solid var(--accent);margin-bottom:14px">
<div class="spot-body" style="font-size:12px;color:var(--text)">{E(fg['posture_next_week'])}</div>
<div class="spot-body" style="margin-top:8px"><span class="mono" style="color:var(--accent)">WATCHLIST //</span> {E(' · '.join(fg['watchlist']))}<br>
<span class="mono" style="color:var(--accent)">KEY EVENTS //</span> {E(' · '.join(fg['key_events_next_week']))}</div></div>

<!-- ══ 09 FULL BOARD ═══════════════════════════════════════ -->
<div class="sec-label">09 &mdash; FULL BOARD &middot; EVERY IDEA, EVERY RESULT ({stats['ideas_total']})</div>
<div class="tbl-section">
<div class="ttbl-controls">
  <span class="ttbl-filter-lbl">Filter:</span>
  <input id="fSym" class="ttbl-filter-input" placeholder="SYMBOL&hellip;" oninput="smFilter()">
  <select id="fDay" class="ttbl-filter-select" onchange="smFilter()">
    <option value="">ALL DAYS</option><option>Tue</option><option>Wed</option><option>Thu</option><option>Fri</option>
  </select>
  <select id="fRes" class="ttbl-filter-select" onchange="smFilter()">
    <option value="">ALL RESULTS</option><option value="win">WIN</option><option value="loss">LOSS</option>
    <option value="scratch">SCRATCH</option><option value="no_trigger">NO TRIGGER</option>
    <option value="indeterminate">INDETERMINATE</option><option value="no_data">NO DATA</option>
  </select>
  <select id="fDir" class="ttbl-filter-select" onchange="smFilter()">
    <option value="">ALL DIRECTIONS</option><option value="long">LONG</option><option value="short">SHORT</option><option value="neutral">NEUTRAL</option>
  </select>
  <button class="ttbl-reset" onclick="smReset()">RESET</button>
  <span id="smCount" class="ttbl-count"></span>
</div>
<table class="ttbl" id="smBoard"><thead><tr>
  <th class="sortable" onclick="smSort(0)">Day</th>
  <th class="sortable" onclick="smSort(1)">Symbol</th>
  <th class="sortable" onclick="smSort(2)">Type</th>
  <th class="sortable" onclick="smSort(3)">Dir</th>
  <th class="sortable" onclick="smSort(4)">Setup</th>
  <th>Entry</th>
  <th class="sortable" onclick="smSort(6)">Result</th>
  <th class="sortable" onclick="smSort(7)">R</th>
  <th>Grading Note</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table></div>

<!-- ══ 10 COVERAGE ═════════════════════════════════════════ -->
<div class="sec-label" style="margin-top:14px">10 &mdash; COVERAGE &amp; METHOD &middot; HONEST LIMITS</div>
<div class="highlight-box" style="border-left-color:var(--warn)">{E(cov['notes'])} Grading is deterministic Python against real daily bars ({series_str}); /ES graded via S&amp;P 500 index (basis &minus;23.5), /NQ via Nasdaq Composite (&divide;1.12625), spot-quoted GLD via gold continuous. $DXY tile: {E(DXY_NOTE)} No LLM graded anything. Monday Aug 10 was not in the source folder; this recap covers Tue&ndash;Fri.</div>

<!-- ══ FOOTER ══════════════════════════════════════════════ -->
<div style="display:flex;justify-content:space-between;align-items:center;margin-top:18px;padding-top:12px;border-top:1px solid var(--border)">
  <div class="footer-logo">SHADOW MONKEY</div>
  <div class="footer-meta">WEEKLY RECAP {WEEK} &middot; GENERATED {gen_ts}<br>
  MONKEY MATTERS LLC / JVS HOLDINGS LTD &middot; INFORMATIONAL ONLY &mdash; NOT FINANCIAL ADVICE<br>
  SURVIVE FIRST. COMPOUND SECOND. LEGACY THIRD.</div>
</div>

</div>
<script>
(function(){{
  var tbody = document.querySelector('#smBoard tbody');
  var sortState = {{col:-1, asc:true}};
  var DAYO = {{Tue:1, Wed:2, Thu:3, Fri:4}};
  function rowsAll(){{ return Array.from(tbody.querySelectorAll('tr')); }}
  function txt(r,c){{ var td=r.cells[c]; return td?td.textContent.trim():''; }}
  window.smFilter = function(){{
    var sym=(document.getElementById('fSym').value||'').toUpperCase().trim();
    var day=document.getElementById('fDay').value;
    var res=document.getElementById('fRes').value;
    var dir=document.getElementById('fDir').value;
    var shown=0, total=0;
    rowsAll().forEach(function(r){{
      total++;
      var ok=true;
      if(sym && r.dataset.sym.indexOf(sym)===-1) ok=false;
      if(ok && day && r.dataset.day!==day) ok=false;
      if(ok && res && r.dataset.result!==res) ok=false;
      if(ok && dir && r.dataset.dir!==dir) ok=false;
      r.style.display = ok?'':'none';
      if(ok) shown++;
    }});
    document.getElementById('smCount').textContent = shown+' / '+total+' IDEAS';
  }};
  window.smReset = function(){{
    ['fSym','fDay','fRes','fDir'].forEach(function(id){{document.getElementById(id).value='';}});
    smFilter();
  }};
  window.smSort = function(col){{
    var asc = (sortState.col===col)? !sortState.asc : true;
    sortState = {{col:col, asc:asc}};
    document.querySelectorAll('#smBoard th').forEach(function(th){{th.classList.remove('sort-asc','sort-desc');}});
    var ths=document.querySelectorAll('#smBoard th');
    if(ths[col]) ths[col].classList.add(asc?'sort-asc':'sort-desc');
    var m = asc?1:-1;
    var rs = rowsAll();
    rs.sort(function(a,b){{
      if(col===0) return m*((DAYO[a.dataset.day]||9)-(DAYO[b.dataset.day]||9));
      if(col===6) return m*((+a.dataset.rorder)-(+b.dataset.rorder));
      if(col===7) return m*((+a.dataset.r)-(+b.dataset.r));
      return m*txt(a,col).toLowerCase().localeCompare(txt(b,col).toLowerCase());
    }});
    rs.forEach(function(r){{tbody.appendChild(r);}});
  }};
  smFilter();
}})();
</script>
</body></html>"""

site = ROOT/"site"/"weekly"; site.mkdir(parents=True, exist_ok=True)
open(site/f"{WEEK}.html", "w").write(html_doc)
print("wrote", site/f"{WEEK}.html", "(APEX theme)")
print("board rows:", len(rows))
