#!/usr/bin/env python3
"""
generate_fff.py — FRIDAY FINANCIAL FORECAST renderer (weekly product).
Descends from the LOCKED weekly template (template/generate_weekly.py,
apex-v1.0) — same APEX design system (template/apex_theme.css, extracted
from the pinned "Morning Market Monitor Shadowmonkey" artifact, do not
fork), same section order, rebranded FFF and converted from a one-off
into automation per WEEKLY_PIPELINE_HANDOFF.md:
  1. week is COMPUTED (passed in by fff_build.py), never hardcoded
  2. paths: template/ (singular), publishes to shadowmonkey/fff-weekly/
  3. narrative is NOT literal prose in this file: deterministic stats are
     Python (real math, always rendered); qualitative sections merge from
     data/weekly/YYYY-Www.insert.json (written by the on-demand Shadow
     Monkey pass) and show explicit PENDING notices until then — the same
     honest-pending pattern the daily uses.
Zero LLM calls here. Ever.
"""
from __future__ import annotations
import json, html, datetime
from pathlib import Path
from collections import defaultdict
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "template"
OUT_DIR = ROOT / "shadowmonkey" / "fff-weekly"
DAILY_SITE_DIR = ROOT / "shadowmonkey" / "mmm-daily"
INDEX_PATH = ROOT / "shadowmonkey" / "index.html"
DATA_DAILY = ROOT / "data" / "daily"
DATA_OUT = ROOT / "data" / "outcomes"
DATA_WEEKLY = ROOT / "data" / "weekly"
PRICES = ROOT / "data" / "prices"
PT = ZoneInfo("America/Los_Angeles")

PENDING = "PENDING — awaiting Shadow Monkey analysis pass"
E = html.escape
GRADED = ("win", "loss", "scratch")

TRACKERS = [  # label, cache key
    ("S&P 500", "IDX_GSPC"), ("Nasdaq Comp", "IDX_IXIC"), ("Gold (spot)", "GCUSD"),
    ("Silver (spot)", "SIUSD"), ("Bitcoin", "BTCUSD"), ("Ethereum", "ETHUSD"),
    ("Brent Crude", "BZUSD"), ("USD Index ($DXY)", "IDX_DXY"),
]

CHIP = dict(win=("WIN", "var(--safe)"), loss=("LOSS", "var(--danger)"),
            scratch=("SCRATCH", "var(--sub)"), no_trigger=("NO TRIGGER", "var(--accent3)"),
            indeterminate=("INDET", "var(--warn)"), no_data=("NO DATA", "var(--muted)"),
            ungradable_v1=("N/G v1", "var(--muted)"))


def _load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def chip(result):
    lbl, c = CHIP.get(result, (str(result).upper(), "var(--sub)"))
    return (f'<span style="font-family:\'Space Mono\',monospace;font-size:9px;letter-spacing:1px;'
            f'padding:1px 6px;border:1px solid {c};color:{c};white-space:nowrap">{lbl}</span>')


def rfmt(v):
    if v is None:
        return '<span style="color:var(--muted)">&mdash;</span>'
    c = "var(--safe)" if v > 0 else ("var(--danger)" if v < 0 else "var(--sub)")
    return f'<span class="mono" style="color:{c};font-weight:700">{v:+.2f}R</span>'


def cval(x):
    return "c-safe" if x > 0 else ("c-bad" if x < 0 else "c-sub")


def pending_box(label: str) -> str:
    return (f'<div class="highlight-box" style="margin-bottom:14px;border-left-color:var(--warn);'
            f'color:var(--muted);font-style:italic">{label}: {PENDING}. Run the on-demand pass '
            f'(live Shadow Monkey chat) to write data/weekly/&lt;week&gt;.insert.json, then re-run '
            f'the FFF workflow.</div>')


# ─────────────────────────────────────────────── data assembly
def week_change(key: str, days: list[str]):
    bars = _load(PRICES / f"{key}.json") or []
    inwk = [b for b in bars if days[0] <= b["date"] <= days[-1]]
    if not inwk:
        return None
    last = inwk[-1]
    prior = [b for b in bars if b["date"] < days[0]]
    base = prior[-1]["close"] if prior else inwk[0]["open"]
    if not base:
        return None
    return last["close"], round(100 * (last["close"] / base - 1), 2), last["date"]


def build_fff(week: str, days: list[str]) -> Path:
    dow = {d: datetime.datetime.strptime(d, "%Y-%m-%d").strftime("%a") for d in days}
    outcomes = {d: (_load(DATA_OUT / f"{d}.json") or {"results": [], "day_summary": {}}) for d in days}
    dailies = {d: (_load(DATA_DAILY / f"{d}.json") or {}) for d in days}
    idea_lookup = {}
    for d in days:
        base, ins = dailies[d], _load(DATA_DAILY / f"{d}.insert.json") or {}
        for src in (ins, base):
            for it in src.get("trade_ideas", []) if isinstance(src.get("trade_ideas"), list) else []:
                if it.get("id"):
                    idea_lookup[it["id"]] = it

    results = [r for d in days for r in outcomes[d]["results"]]
    counts = defaultdict(int)
    for r in results:
        counts[r.get("result", "no_data")] += 1
    graded = [r for r in results if r.get("result") in GRADED]
    wins = [r for r in graded if r["result"] == "win"]
    losses = [r for r in graded if r["result"] == "loss"]
    total_r = round(sum(r.get("r_multiple") or 0 for r in graded), 2)
    win_rate = round(len(wins) / max(1, len(wins) + len(losses)), 3)
    exp_r = round(total_r / max(1, len(graded)), 2)

    curve, cum = [], 0.0
    for d in days:
        dr = round(sum(r.get("r_multiple") or 0 for r in outcomes[d]["results"]
                       if r.get("result") in GRADED), 2)
        cum = round(cum + dr, 2)
        curve.append((d, dr, cum))

    def bd(keyfn, min_n=1):
        agg = defaultdict(lambda: dict(n=0, wins=0, losses=0, total_r=0.0))
        for d in days:
            for r in outcomes[d]["results"]:
                idea = idea_lookup.get(r.get("id"), {})
                k = keyfn(r, idea, d)
                a = agg[k]
                a["n"] += 1
                if r.get("result") == "win":
                    a["wins"] += 1
                if r.get("result") == "loss":
                    a["losses"] += 1
                if r.get("result") in GRADED:
                    a["total_r"] = round(a["total_r"] + (r.get("r_multiple") or 0), 2)
        return {k: v for k, v in agg.items() if v["n"] >= min_n}

    by_instrument = bd(lambda r, i, d: r.get("instrument") or i.get("instrument", "?"))
    by_direction = bd(lambda r, i, d: r.get("direction") or i.get("direction", "?"))
    by_priority = bd(lambda r, i, d: f"P{r.get('priority') or i.get('priority', 1)}")
    by_setup = bd(lambda r, i, d: (r.get("setup") or i.get("setup") or "?")[:28], min_n=2)
    by_day = bd(lambda r, i, d: dow[d])

    mkt = {label: week_change(key, days) for label, key in TRACKERS}

    ins = _load(DATA_WEEKLY / f"{week}.insert.json") or {}
    gen_ts = datetime.datetime.now(PT).strftime("%Y-%m-%d %H:%M %Z")

    # ── persist the machine-readable weekly record
    DATA_WEEKLY.mkdir(parents=True, exist_ok=True)
    weekly_json = dict(
        schema_version=2, week=week, days=days,
        generated_at=datetime.datetime.now(PT).isoformat(timespec="seconds"),
        stats=dict(ideas_total=len(results), wins=len(wins), losses=len(losses),
                   win_rate=win_rate, total_r=total_r, expectancy_r=exp_r,
                   no_trigger=counts["no_trigger"], indeterminate=counts["indeterminate"],
                   no_data=counts["no_data"], ungradable_v1=counts["ungradable_v1"],
                   by_instrument=by_instrument, by_direction=by_direction,
                   by_priority=by_priority, by_setup=by_setup, by_day=by_day,
                   daily_r_curve=[dict(date=a, r=b, cum_r=c) for a, b, c in curve]),
        market_week={k: (dict(close=v[0], change_pct=v[1], asof=v[2]) if v else None)
                     for k, v in mkt.items()},
        narrative_status="merged" if ins else "pending",
        narrative=ins or None)
    (DATA_WEEKLY / f"{week}.json").write_text(json.dumps(weekly_json, indent=2), encoding="utf-8")

    # ── render
    apex_css = (TEMPLATE_DIR / "apex_theme.css").read_text(encoding="utf-8")
    html_doc = _render(week, days, dow, outcomes, idea_lookup, counts, graded, wins, losses,
                       total_r, win_rate, exp_r, curve,
                       by_instrument, by_direction, by_priority, by_setup,
                       mkt, ins, gen_ts, apex_css)

    if not html_doc.startswith("<!DOCTYPE html>") or len(html_doc) < 15000:
        raise RuntimeError("FFF output failed validation — refusing to publish.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"fff-{week}.html"
    out_path.write_text(html_doc, encoding="utf-8")
    rebuild_index()
    return out_path


# ─────────────────────────────────────────────── HTML
EXT_CSS = """
.mkt-strip{display:grid;grid-template-columns:repeat(8,1fr);gap:6px;margin-bottom:14px}
.day-strip{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:14px}
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


def _render(week, days, dow, outcomes, idea_lookup, counts, graded, wins, losses,
            total_r, win_rate, exp_r, curve, by_instrument, by_direction,
            by_priority, by_setup, mkt, ins, gen_ts, apex_css) -> str:

    day_cats = ins.get("DAY_CATALYSTS", {})
    day_tiles = "".join(
        f'<div class="day-card"><div class="st-lbl">{dow[d]} &middot; {d[-5:]}</div>'
        f'<div class="st-val {cval(r)}">{r:+.2f}R</div>'
        f'<div class="st-sub c-sub">cumulative {c:+.2f}R &middot; '
        f'{outcomes[d]["day_summary"].get("ideas_total", 0)} ideas</div>'
        f'<div class="day-cat">{E(day_cats.get(d, "catalyst notes: " + PENDING.lower()))}</div></div>'
        for d, r, c in curve)

    def mkt_tile(label, v):
        if v is None:
            return (f'<div class="sent-tile"><div class="st-lbl">{E(label)}</div>'
                    f'<div class="st-val c-sub" style="font-size:15px">N/A</div>'
                    f'<div class="st-sub" style="color:var(--muted)">NO BARS THIS RUN</div></div>')
        close, pct, _ = v
        return (f'<div class="sent-tile"><div class="st-lbl">{E(label)}</div>'
                f'<div class="st-val {cval(pct)}" style="font-size:15px">{close:,.2f}</div>'
                f'<div class="st-sub {cval(pct)}">{pct:+.2f}% WK</div></div>')

    mkt_tiles = "".join(mkt_tile(l, v) for l, v in mkt.items())

    def bd_table(title, data):
        trs = "".join(
            f'<tr><td>{E(str(k))}</td><td class="mono">{v["n"]}</td>'
            f'<td class="mono">{v["wins"]}-{v["losses"]}</td>'
            f'<td class="mono" style="color:{"var(--safe)" if v["total_r"]>0 else "var(--danger)" if v["total_r"]<0 else "var(--sub)"};font-weight:700">{v["total_r"]:+.2f}R</td></tr>'
            for k, v in sorted(data.items(), key=lambda kv: -kv[1]["total_r"]))
        if not trs:
            trs = f'<tr><td colspan="4" style="color:var(--muted);font-style:italic">no graded ideas yet</td></tr>'
        return (f'<div class="sm-card"><div class="card-hd">{title}</div>'
                f'<table class="etbl"><tr><th>Bucket</th><th>N</th><th>W-L</th><th>R</th></tr>{trs}</table></div>')

    # thesis / lessons / forecast — insert-driven, PENDING otherwise
    verd_c = dict(confirmed="var(--safe)", refuted="var(--danger)",
                  mixed="var(--warn)", unresolved="var(--muted)")
    thesis = ins.get("THESIS_REVIEW") or []
    thesis_html = "".join(
        f'<div class="spot-item"><div class="spot-hd"><span class="spot-tk">{E(t.get("thesis",""))}</span>'
        f'<span class="tag" style="border-color:{verd_c.get(t.get("verdict"),"var(--sub)")};color:{verd_c.get(t.get("verdict"),"var(--sub)")}">{E(str(t.get("verdict","")).upper())}</span></div>'
        f'<div class="spot-body">{E(t.get("evidence",""))}</div></div>' for t in thesis) or \
        f'<div class="spot-body" style="color:var(--muted);font-style:italic">{PENDING}</div>'
    lessons = ins.get("LESSONS") or []
    lessons_html = "".join(
        f'<div class="spot-item"><div class="spot-hd">'
        f'<span class="tag" style="border-color:{"var(--safe)" if l.get("action")=="adopt" else "var(--warn)"};color:{"var(--safe)" if l.get("action")=="adopt" else "var(--warn)"}">{E(str(l.get("action","watch")).upper())}</span></div>'
        f'<div class="spot-body"><strong style="color:var(--text)">{E(l.get("rule",""))}</strong><br>{E(l.get("evidence",""))}</div></div>'
        for l in lessons) or \
        f'<div class="spot-body" style="color:var(--muted);font-style:italic">{PENDING}</div>'

    best = max(graded, key=lambda r: r.get("r_multiple") or 0, default=None)
    worst = min(graded, key=lambda r: r.get("r_multiple") or 0, default=None)

    def receipt(r, fallback):
        if not r:
            return f'<div class="spot-body" style="color:var(--muted);font-style:italic">{fallback}</div>'
        idea = idea_lookup.get(r.get("id"), {})
        return (f'<div class="spot-body"><strong style="color:var(--text)">'
                f'{E(r.get("symbol","?"))} &middot; {E(r.get("setup") or idea.get("setup",""))} '
                f'({E(r.get("id",""))})</strong><br>{rfmt(r.get("r_multiple"))} &middot; '
                f'{E(r.get("exit_reason",""))}</div>')

    fg = ins.get("FORWARD_GUIDANCE") or {}
    if fg:
        fg_html = (f'<div class="sm-card" style="border-left:3px solid var(--accent);margin-bottom:14px">'
                   f'<div class="spot-body" style="font-size:12px;color:var(--text)">{E(fg.get("posture",""))}</div>'
                   f'<div class="spot-body" style="margin-top:8px">'
                   f'<span class="mono" style="color:var(--accent)">WATCHLIST //</span> {E(" · ".join(fg.get("watchlist", [])))}<br>'
                   f'<span class="mono" style="color:var(--accent)">KEY EVENTS //</span> {E(" · ".join(fg.get("key_events", [])))}</div></div>')
    else:
        fg_html = pending_box("Forecast &amp; next-week guidance")

    wir = ins.get("WEEK_IN_REVIEW")
    wir_html = (f'<div class="highlight-box" style="margin-bottom:14px">{E(wir)}</div>'
                if wir else pending_box("Week-in-review market narrative"))

    RESULT_ORDER = dict(win=0, loss=1, scratch=2, no_trigger=3, indeterminate=4,
                        no_data=5, ungradable_v1=6)
    rows = []
    for d in days:
        for r in outcomes[d]["results"]:
            idea = idea_lookup.get(r.get("id"), {})
            rm = r.get("r_multiple")
            direction = r.get("direction") or idea.get("direction", "?")
            dirc = ("var(--safe)" if direction == "long"
                    else "var(--danger)" if direction == "short" else "var(--sub)")
            note = r.get("notes")
            note = " ".join(note) if isinstance(note, list) else (note or "")
            rows.append(
                f'<tr data-day="{dow[d]}" data-result="{r.get("result")}" data-dir="{direction}" '
                f'data-sym="{E(str(r.get("symbol","?")).upper())}" data-r="{rm if rm is not None else -999}" '
                f'data-rorder="{RESULT_ORDER.get(r.get("result"), 9)}">'
                f'<td class="mono">{dow[d]} {d[-2:]}</td><td><strong>{E(r.get("symbol","?"))}</strong></td>'
                f'<td style="color:var(--sub)">{E(r.get("instrument") or idea.get("instrument","?"))}</td>'
                f'<td style="color:{dirc};font-weight:700">{E(direction.upper())}</td>'
                f'<td style="color:var(--sub)">{E((r.get("setup") or idea.get("setup",""))[:34])}</td>'
                f'<td class="mono" style="color:var(--accent3)">{E((r.get("entry_raw") or str(idea.get("entry","—")))[:18])}</td>'
                f'<td>{chip(r.get("result"))}</td><td>{rfmt(rm)}</td>'
                f'<td style="color:var(--muted);font-size:10px">{E(note[:80])}</td></tr>')
    board_rows = "".join(rows) or (
        '<tr><td colspan="9" style="color:var(--muted);font-style:italic">No structured trade ideas '
        "were published this week — the on-demand daily pass writes them into "
        "data/daily/DATE.insert.json (see FFF_STATUS.md contract).</td></tr>")

    n_results = sum(len(outcomes[d]["results"]) for d in days)
    d0 = datetime.datetime.strptime(days[0], "%Y-%m-%d")
    d1 = datetime.datetime.strptime(days[-1], "%Y-%m-%d")
    date_rng = f"{d0.strftime('%b')} {d0.day}&ndash;{d1.strftime('%b')} {d1.day}, {d1.year}"  # Windows-safe

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Friday Financial Forecast &mdash; {week} &mdash; Shadow Monkey / Monkey Matters LLC</title>
<style>{apex_css}
{EXT_CSS}</style></head><body>
<div class="wrap">

<div class="hdr">
  <div class="hdr-classification">
    <span class="tag tag-red">EYES ONLY</span>
    <span class="tag tag-green">OPERATIVE: SHADOW MONKEY</span>
    <span class="tag tag-muted">HANDLER: JOE</span>
    <span class="tag tag-blue">MONKEY MATTERS LLC</span>
  </div>
  <div class="hdr-top">
    <div class="hdr-title-block">
      <div class="hdr-brand">FRIDAY<br><span>FINANCIAL</span><br>FORECAST</div>
      <div class="hdr-subtitle">FFF &bull; {week} &bull; {date_rng} &bull; Weekly recap of the Morning Market Monitor &bull; Shadow Monkey / Monkey Matters LLC</div>
    </div>
    <div class="hdr-badges">
      <span class="sm-badge sm-badge-warn">{'&#x25CF; NARRATIVE MERGED' if ins else '&#x26A0; NARRATIVE PENDING &mdash; ON-DEMAND PASS'}</span>
      <span class="sm-badge sm-badge-live">&#x25CF; GRADED VS REAL BARS</span>
    </div>
  </div>
  <div class="hdr-meta-grid">
    <div class="hdr-meta-cell"><div class="hm-label">Cadence</div><div class="hm-val">Fridays &middot; 2:10 PM PT</div></div>
    <div class="hdr-meta-cell"><div class="hm-label">Record</div><div class="hm-val" style="color:{'var(--safe)' if total_r>0 else 'var(--danger)' if total_r<0 else 'var(--sub)'}">{len(wins)}&ndash;{len(losses)} &middot; {total_r:+.2f}R</div></div>
    <div class="hdr-meta-cell"><div class="hm-label">Ideas This Week</div><div class="hm-val">{n_results}</div></div>
    <div class="hdr-meta-cell"><div class="hm-label">Prime Directive</div><div class="hm-val" style="color:var(--accent2)">SURVIVE. COMPOUND. LEGACY.</div></div>
  </div>
</div>

<div class="sec-label">01 &mdash; WEEK SCOREBOARD</div>
<div class="sent-strip wk-sent">
  <div class="sent-tile"><div class="st-lbl">Ideas Published</div><div class="st-val c-acc3">{n_results}</div><div class="st-sub c-sub">{sum(1 for d in days if outcomes[d]['results'])} SESSION(S) WITH IDEAS</div></div>
  <div class="sent-tile"><div class="st-lbl">Graded W-L</div><div class="st-val c-warn">{len(wins)}-{len(losses)}</div><div class="st-sub c-sub">{len(graded)} GRADED &middot; {counts['no_trigger']} NO-TRIGGER</div></div>
  <div class="sent-tile"><div class="st-lbl">Win Rate</div><div class="st-val {'c-safe' if win_rate>=0.5 else 'c-bad'}">{win_rate*100:.0f}%</div><div class="st-sub c-sub">OF DECIDED TRADES</div></div>
  <div class="sent-tile"><div class="st-lbl">Total R</div><div class="st-val {cval(total_r)}">{total_r:+.2f}R</div><div class="st-sub c-sub">EXPECTANCY {exp_r:+.2f}R</div></div>
  <div class="sent-tile"><div class="st-lbl">Indeterminate</div><div class="st-val c-warn">{counts['indeterminate']}</div><div class="st-sub c-sub">AMBIGUOUS ON DAILY BARS</div></div>
  <div class="sent-tile"><div class="st-lbl">No Data / N-G</div><div class="st-val" style="color:var(--muted)">{counts['no_data'] + counts['ungradable_v1']}</div><div class="st-sub c-sub">COVERAGE &middot; V1 LIMITS</div></div>
</div>

<div class="sec-label">02 &mdash; THE WEEK IN THE MARKET</div>
{wir_html}

<div class="sec-label">03 &mdash; MACRO TRACKERS &middot; WEEKLY CLOSE</div>
<div class="mkt-strip">{mkt_tiles}</div>

<div class="sec-label">04 &mdash; SESSION LEDGER &middot; R BY DAY</div>
<div class="day-strip">{day_tiles}</div>

<div class="sec-label">05 &mdash; SCORECARDS &middot; WHERE THE R CAME FROM</div>
<div class="grid2w">
{bd_table("BY INSTRUMENT", by_instrument)}
{bd_table("BY DIRECTION", by_direction)}
{bd_table("BY PRIORITY", by_priority)}
{bd_table("BY SETUP (N&ge;2)", by_setup)}
</div>

<div class="sec-label">06 &mdash; THESIS REVIEW &amp; LESSONS</div>
<div class="grid2w">
<div class="sm-card"><div class="card-hd">&#x1F50D; THESIS REVIEW</div>{thesis_html}</div>
<div class="sm-card"><div class="card-hd">&#x1F4DA; LESSONS &mdash; RULES FOR NEXT WEEK'S MONITORS</div>{lessons_html}</div>
</div>

<div class="sec-label">07 &mdash; RECEIPTS &middot; BEST / WORST</div>
<div class="grid2w">
<div class="sm-card"><div class="card-hd" style="color:var(--safe)">&#x1F3C6; BEST CALL</div>{receipt(best, "no graded wins this week")}</div>
<div class="sm-card"><div class="card-hd" style="color:var(--danger)">&#x1F4A5; WORST CALL</div>{receipt(worst, "no graded losses this week")}</div>
</div>

<div class="sec-label">08 &mdash; FORECAST &middot; WEEK AHEAD</div>
{fg_html}

<div class="sec-label">09 &mdash; FULL BOARD &middot; EVERY IDEA, EVERY RESULT ({n_results})</div>
<div class="tbl-section">
<div class="ttbl-controls">
  <span class="ttbl-filter-lbl">Filter:</span>
  <input id="fSym" class="ttbl-filter-input" placeholder="SYMBOL&hellip;" oninput="smFilter()">
  <select id="fDay" class="ttbl-filter-select" onchange="smFilter()">
    <option value="">ALL DAYS</option><option>Mon</option><option>Tue</option><option>Wed</option><option>Thu</option><option>Fri</option>
  </select>
  <select id="fRes" class="ttbl-filter-select" onchange="smFilter()">
    <option value="">ALL RESULTS</option><option value="win">WIN</option><option value="loss">LOSS</option>
    <option value="scratch">SCRATCH</option><option value="no_trigger">NO TRIGGER</option>
    <option value="indeterminate">INDETERMINATE</option><option value="no_data">NO DATA</option>
    <option value="ungradable_v1">N/G V1</option>
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
</tr></thead><tbody>{board_rows}</tbody></table></div>

<div class="sec-label" style="margin-top:14px">10 &mdash; METHOD &middot; HONEST LIMITS</div>
<div class="highlight-box" style="border-left-color:var(--warn)">Grading is deterministic Python
(scripts/grade_trades.py) against real daily bars from the source ladder (FMP stable EOD &rarr;
Schwab pricehistory &rarr; same-day quote-synth); every outcome records its bar source. Ideas whose
entry style needs intraday bars (VWAP, opening-range, premarket offsets) grade N/G V1 rather than
being guessed. Futures ideas grade only on real Schwab futures bars &mdash; never silently proxied
to cash indexes. No LLM graded anything; narrative sections are written by the on-demand Shadow
Monkey pass and merged, never invented by the data pass.</div>

<div style="display:flex;justify-content:space-between;align-items:center;margin-top:18px;padding-top:12px;border-top:1px solid var(--border)">
  <div class="footer-logo">SHADOW MONKEY</div>
  <div class="footer-meta">FRIDAY FINANCIAL FORECAST {week} &middot; GENERATED {gen_ts}<br>
  MONKEY MATTERS LLC / JVS HOLDINGS LTD &middot; INFORMATIONAL ONLY &mdash; NOT FINANCIAL ADVICE<br>
  SURVIVE FIRST. COMPOUND SECOND. LEGACY THIRD.</div>
</div>

</div>
<script>
(function(){{
  var tbody = document.querySelector('#smBoard tbody');
  var sortState = {{col:-1, asc:true}};
  var DAYO = {{Mon:0, Tue:1, Wed:2, Thu:3, Fri:4}};
  function rowsAll(){{ return Array.from(tbody.querySelectorAll('tr')); }}
  function txt(r,c){{ var td=r.cells[c]; return td?td.textContent.trim():''; }}
  window.smFilter = function(){{
    var sym=(document.getElementById('fSym').value||'').toUpperCase().trim();
    var day=document.getElementById('fDay').value;
    var res=document.getElementById('fRes').value;
    var dir=document.getElementById('fDir').value;
    var shown=0, total=0;
    rowsAll().forEach(function(r){{
      if(!r.dataset.sym) return;
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
    var rs = rowsAll().filter(function(r){{return r.dataset.sym;}});
    rs.sort(function(a,b){{
      if(col===0) return m*((DAYO[a.dataset.day]??9)-(DAYO[b.dataset.day]??9));
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


# ─────────────────────────────────────────────── shared index (daily + FFF)
def rebuild_index() -> None:
    """One index for the whole shadowmonkey/ site: MMM daily archive + FFF
    weekly archive. fetch_mmm_data.py calls its own copy of this logic —
    keep the two in sync (or import this one)."""
    daily_files = sorted(DAILY_SITE_DIR.glob("*.html"), reverse=True)
    fff_files = sorted(OUT_DIR.glob("*.html"), reverse=True)
    daily_rows = "\n".join(
        f'<tr><td>{f.stem}</td><td><a href="mmm-daily/{f.name}">Open</a></td></tr>'
        for f in daily_files)
    fff_rows = "\n".join(
        f'<tr><td>{f.stem}</td><td><a href="fff-weekly/{f.name}">Open</a></td></tr>'
        for f in fff_files) or '<tr><td colspan="2" style="color:#666">none yet</td></tr>'
    INDEX_PATH.write_text(f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Shadow Monkey — Monkey Matters LLC</title>
<style>body{{background:#080808;color:#fff;font-family:'Space Mono',monospace;padding:24px}}
a{{color:#c8ff00}} table{{border-collapse:collapse;margin-bottom:28px}}
td{{padding:6px 14px;border-bottom:1px solid #222}} h2{{color:#c8ff00;letter-spacing:2px}}</style>
</head><body><h1>Shadow Monkey — Intelligence Archive</h1>
<h2>FFF — Friday Financial Forecast (weekly)</h2>
<table>{fff_rows}</table>
<h2>MMM — Morning Market Monitor (daily)</h2>
<table>{daily_rows}</table></body></html>""", encoding="utf-8")


if __name__ == "__main__":
    import sys as _sys
    wk = _sys.argv[1] if len(_sys.argv) > 1 else None
    if not wk:
        print("usage: generate_fff.py YYYY-Www  (fff_build.py normally drives this)")
        _sys.exit(1)
    year, wnum = wk.split("-W")
    monday = datetime.date.fromisocalendar(int(year), int(wnum), 1)
    days = [(monday + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
    print(build_fff(wk, days))
