#!/usr/bin/env node
/**
 * MMM Dashboard — server-side snapshot generator
 *
 * Runs once per weekday (via GitHub Actions cron), pulls everything that can't
 * live in the browser — Massive (futures/sectors), FRED (VIX/HY OAS), CBOE
 * (Put/Call), AAII (Bull-Bear) — computes derived values (pivots, fibs,
 * 1D/5D%), and bakes plain strings into the dashboard's static TEXT snapshot
 * object. The client-side script (feargreedchart, rss2json, Twelve Data,
 * Finnhub) is untouched and keeps refreshing live in the browser on top of
 * whatever this script bakes in.
 *
 * Why server-side and not client fetch():
 *  - FRED sends no Access-Control-Allow-Origin — browser fetch() fails outright.
 *  - Massive Basic (free) is end-of-day/8h-delayed regardless of when it's
 *    called, so there's no freshness lost by calling it once here vs. on
 *    every page view — and calling it once instead of N times keeps well
 *    under the 5-req/min free-tier ceiling.
 *  - CBOE and AAII are HTML pages, not JSON APIs — need parsing, and most
 *    sites don't set CORS headers for that kind of cross-origin scrape.
 *
 * Usage:
 *   MASSIVE_API_KEY=... FRED_API_KEY=... node generate_snapshot.mjs <path-to-dashboard.html>
 *
 * Exits non-zero only on a hard failure to read/write the file. Individual
 * data-source failures are logged and leave that field's existing value
 * untouched — this script must never write "undefined" or a guessed number
 * into the dashboard.
 */

import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

// ── CONFIG ──
// Update these each quarterly futures rollover (Mar/Jun/Sep/Dec -> H/M/U/Z).
// Massive's ticker format is {SYMBOL}{MONTH_CODE}{SINGLE-DIGIT YEAR}, e.g. "GCJ5" = Gold, Apr 2025.
const FUTURES = {
  ES: 'ESU6', // September 2026
  NQ: 'NQU6', // September 2026
};

// Schwab's futures symbol format is completely different from Massive's above
// — thinkorswim convention: "/" + root + month-code + TWO-digit year (e.g.
// /ESU26 = E-mini S&P 500, September 2026). Confirmed via Schwab's own
// Futures FAQ page and schwab-py's docs (which flag the "/" as needing
// URL-encoding, handled automatically by encodeURIComponent below). Update
// BOTH this and FUTURES above at each quarterly rollover — they drift
// independently since the formats don't share a source string.
const SCHWAB_FUTURES = {
  ES: '/ESU26', // September 2026
  NQ: '/NQU26', // September 2026
};

// Gold and Dollar Index FUTURES (not the UUP/GLD ETF proxies used previously)
// — same Massive Futures endpoint and ticker format as ES/NQ above. GC (gold)
// is confirmed supported: the original FUTURES comment above used "GCJ5" as
// its own example of Massive's ticker format. DX (ICE Dollar Index futures)
// is NOT independently confirmed the same way — it's the standard root
// symbol for Dollar Index futures on most platforms, but this hasn't been
// verified against Massive's specific symbol directory. If Massive rejects
// it, this field will simply come back gated (see fetchMassiveFuturesSession's
// null-on-failure handling) rather than silently show a wrong number — check
// the Action run's logs after the first live run to confirm either way.
const COMMODITY_FUTURES = {
  GOLD: 'GCU6', // September 2026
  DXY: 'DXU6',  // September 2026 — unverified against Massive, see comment above
};

// SPDR sector ETFs — Massive Stocks Basic covers all of these.
const SECTOR_ETFS = {
  XLK: 'Technology', XLF: 'Financials', XLE: 'Energy', XLV: 'Health Care',
  XLI: 'Industrials', XLY: 'Consumer Discretionary', XLP: 'Consumer Staples',
  XLU: 'Utilities', XLB: 'Materials', XLRE: 'Real Estate', XLC: 'Communication Services',
};

const MASSIVE_KEY = process.env.MASSIVE_API_KEY || '';
const FRED_KEY = process.env.FRED_API_KEY || '';
const SCHWAB_CLIENT_ID = process.env.SCHWAB_CLIENT_ID || '';
const SCHWAB_CLIENT_SECRET = process.env.SCHWAB_CLIENT_SECRET || '';
const SCHWAB_REFRESH_TOKEN = process.env.SCHWAB_REFRESH_TOKEN || '';
// 'full' (default) runs every section — Massive/FRED/CBOE/Schwab. 'light'
// runs ONLY the Schwab section, loading the existing snapshot.json as a base
// and carrying forward everything else unchanged. This exists because most
// of what this script fetches (sectors, FRED series, CBOE) is end-of-day or
// daily data that genuinely can't change intraday — refetching it every 5
// minutes during the pre-market window would be pure waste, and for CBOE
// specifically, more requests means more exposure to its bot detection for
// zero benefit. See .github/workflows/mmm-dashboard.yml for how mode is
// chosen based on which cron entry fired.
const SNAPSHOT_MODE = process.env.SNAPSHOT_MODE === 'light' ? 'light' : 'full';
const DASHBOARD_PATH = process.argv[2];

if (!DASHBOARD_PATH) {
  console.error('Usage: node generate_snapshot.mjs <path-to-dashboard.html>');
  process.exit(1);
}

// ── Small helpers ──

function fmt(n, decimals = 2) {
  if (n == null || Number.isNaN(n)) return null;
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

/** Steps back one calendar day at a time, skipping Sat/Sun. Does not know about market holidays. */
function previousTradingDay(date) {
  const d = new Date(date);
  do {
    d.setUTCDate(d.getUTCDate() - 1);
  } while (d.getUTCDay() === 0 || d.getUTCDay() === 6); // 0=Sun, 6=Sat
  return d;
}

function ymd(date) {
  return date.toISOString().slice(0, 10);
}

/** Standard floor-trader pivots from a session's OHLC. */
function computePivots(o, h, l, c) {
  const pp = (h + l + c) / 3;
  return {
    pp,
    r1: 2 * pp - l,
    s1: 2 * pp - h,
    r2: pp + (h - l),
    s2: pp - (h - l),
    r3: h + 2 * (pp - l),
    s3: l - 2 * (h - pp),
  };
}

/** Fibonacci retracement levels of the prior session's range. */
function computeFibs(h, l) {
  const range = h - l;
  return {
    f38: h - 0.382 * range,
    f50: h - 0.5 * range,
    f62: h - 0.618 * range,
  };
}

// ── Data fetchers — each returns null on any failure and logs why ──

async function fetchMassiveFuturesSession(ticker) {
  const url = `https://api.massive.com/futures/v1/aggs/${ticker}?resolution=1session&limit=1&apiKey=${MASSIVE_KEY}`;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      const bodyText = await res.text().catch(() => '(no body)');
      console.error(`[Massive Futures] ${ticker}: HTTP ${res.status} ${res.statusText} — ${bodyText.slice(0, 200) || '(empty body)'}`);
      return null;
    }
    const data = await res.json();
    if (data.status !== 'OK' || !data.results || !data.results.length) {
      console.error(`[Massive Futures] ${ticker}: no results (status=${data.status}, message=${data.message || data.error || 'n/a'})`);
      return null;
    }
    const bar = data.results[0];
    return { open: bar.open, high: bar.high, low: bar.low, close: bar.close, sessionDate: bar.session_end_date };
  } catch (e) {
    console.error(`[Massive Futures] ${ticker} fetch failed:`, e.message);
    return null;
  }
}

/** Fetches ALL US stocks' EOD OHLC for one date in a single call. Returns Map<ticker, {c}> or null. */
async function fetchMassiveGroupedDaily(dateStr) {
  const url = `https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks/${dateStr}?apiKey=${MASSIVE_KEY}`;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      // Non-2xx (e.g. 401/429) may not have a JSON body at all — read as text
      // first so we always log something useful instead of a JSON-parse crash.
      const bodyText = await res.text().catch(() => '(no body)');
      console.error(`[Massive Stocks] ${dateStr}: HTTP ${res.status} ${res.statusText} — ${bodyText.slice(0, 200) || '(empty body)'}`);
      return null;
    }
    const data = await res.json();
    if (data.status !== 'OK' || !data.results) {
      console.error(`[Massive Stocks] ${dateStr}: no results (status=${data.status}, message=${data.message || data.error || 'n/a'})`);
      return null;
    }
    const map = new Map();
    for (const row of data.results) map.set(row.T, row.c);
    return map;
  } catch (e) {
    console.error(`[Massive Stocks] ${dateStr} fetch failed:`, e.message);
    return null;
  }
}

/**
 * Previous-day OHLC bar for any Massive ticker — stocks, indices ("I:" prefix,
 * e.g. I:SPX, I:NDX — confirmed via massive.com/blog/indices-data-has-arrived),
 * or crypto ("X:" prefix, e.g. X:BTCUSD — confirmed via Massive's own MACD/EMA/
 * RSI endpoint docs). Same shape and auth as the futures/stocks fetchers above.
 */
async function fetchMassivePrevClose(ticker) {
  const url = `https://api.massive.com/v2/aggs/ticker/${encodeURIComponent(ticker)}/prev?apiKey=${MASSIVE_KEY}`;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      const bodyText = await res.text().catch(() => '(no body)');
      console.error(`[Massive PrevClose] ${ticker}: HTTP ${res.status} ${res.statusText} — ${bodyText.slice(0, 200) || '(empty body)'}`);
      return null;
    }
    const data = await res.json();
    if (data.status !== 'OK' || !data.results || !data.results.length) {
      console.error(`[Massive PrevClose] ${ticker}: no results (status=${data.status}, message=${data.message || data.error || 'n/a'})`);
      return null;
    }
    const bar = data.results[0];
    return { open: bar.o, high: bar.h, low: bar.l, close: bar.c };
  } catch (e) {
    console.error(`[Massive PrevClose] ${ticker} fetch failed:`, e.message);
    return null;
  }
}

async function fetchFredSeries(seriesId) {
  const url = `https://api.stlouisfed.org/fred/series/observations?series_id=${seriesId}&api_key=${FRED_KEY}&limit=1&sort_order=desc&file_type=json`;
  try {
    const res = await fetch(url);
    const data = await res.json();
    const obs = data.observations && data.observations[0];
    if (!obs || obs.value === '.') {
      console.error(`[FRED] ${seriesId}: no valid observation`);
      return null;
    }
    return { value: obs.value, date: obs.date };
  } catch (e) {
    console.error(`[FRED] ${seriesId} fetch failed:`, e.message);
    return null;
  }
}

/**
 * Parses Cboe's public daily options market statistics page for the Total
 * and Equity Put/Call ratios. UNVERIFIED against live markup — Cboe's page
 * structure was not directly inspected before writing this parser (only the
 * page's existence and general content were confirmed). This is a best-effort
 * regex against likely phrasing; if Cboe's HTML doesn't match, this returns
 * null and logs loudly rather than guess. Check the logged warning after the
 * first real run and adjust the pattern against the actual page source.
 */
async function fetchCboePutCall() {
  const url = 'https://www.cboe.com/markets/us/options/market-statistics/daily/';
  try {
    const res = await fetch(url);
    const html = await res.text();
    // Best-effort patterns — Cboe's page may render via JS, in which case a
    // plain fetch() won't see the populated table at all. Flagged as a known risk.
    const totalMatch = html.match(/total\s*put\/call\s*ratio[^0-9]{0,40}([01]\.\d{2})/i);
    const equityMatch = html.match(/equity\s*put\/call\s*ratio[^0-9]{0,40}([01]\.\d{2})/i);
    if (!totalMatch && !equityMatch) {
      console.error('[CBOE] Could not find Put/Call figures in page HTML — page likely renders via JS, or markup differs from the assumed pattern. Needs manual inspection of the live page source.');
      return null;
    }
    return {
      total: totalMatch ? totalMatch[1] : null,
      equity: equityMatch ? equityMatch[1] : null,
    };
  } catch (e) {
    console.error('[CBOE] fetch failed:', e.message);
    return null;
  }
}

/**
 * Exchanges the long-lived (~7 day) SCHWAB_REFRESH_TOKEN secret for a fresh
 * 30-minute access token. Manual browser re-auth is required roughly weekly
 * when the refresh token itself expires — confirmed directly with Schwab
 * (TraderAPI@Schwab.com): there is no programmatic way to renew a refresh
 * token past 7 days. See mmm-dashboard/schwab-setup/get_refresh_token.mjs.
 */
async function fetchSchwabAccessToken() {
  const basicAuth = Buffer.from(`${SCHWAB_CLIENT_ID}:${SCHWAB_CLIENT_SECRET}`).toString('base64');
  const body = new URLSearchParams({ grant_type: 'refresh_token', refresh_token: SCHWAB_REFRESH_TOKEN });
  try {
    const res = await fetch('https://api.schwabapi.com/v1/oauth/token', {
      method: 'POST',
      headers: { Authorization: `Basic ${basicAuth}`, 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    });
    const bodyText = await res.text();
    if (!res.ok) {
      console.error(`[Schwab OAuth] HTTP ${res.status} ${res.statusText} — ${bodyText.slice(0, 300)}. Refresh token likely expired (~7 day lifetime) — re-run schwab-setup/get_refresh_token.mjs and update the SCHWAB_REFRESH_TOKEN secret.`);
      return null;
    }
    const data = JSON.parse(bodyText);
    if (!data.access_token) {
      console.error('[Schwab OAuth] No access_token in response:', bodyText.slice(0, 300));
      return null;
    }
    return data.access_token;
  } catch (e) {
    console.error('[Schwab OAuth] Token refresh failed:', e.message);
    return null;
  }
}

/**
 * Real-time-as-of-this-run quotes for one or more Schwab-format symbols
 * (index tickers use a "$" prefix, e.g. $SPX, $NDX — confirmed directly from
 * Schwab's own developer support correspondence). Returns Map<symbol,
 * {last, netChange}> or null. Parses defensively against two possible
 * response nesting shapes (top-level vs nested under "quote") and logs the
 * raw shape on a miss rather than guessing wrong a second time.
 */
async function fetchSchwabQuotes(accessToken, symbols) {
  const url = `https://api.schwabapi.com/marketdata/v1/quotes?symbols=${encodeURIComponent(symbols.join(','))}`;
  try {
    const res = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` } });
    const bodyText = await res.text();
    if (!res.ok) {
      console.error(`[Schwab Quotes] HTTP ${res.status} ${res.statusText} — ${bodyText.slice(0, 300)}`);
      return null;
    }
    const data = JSON.parse(bodyText);
    const map = new Map();
    for (const sym of symbols) {
      const entry = data[sym];
      if (!entry) { console.error(`[Schwab Quotes] No entry for ${sym} in response — symbol may be wrong or market closed.`); continue; }
      const q = entry.quote || entry; // defend against either nesting shape
      const last = q.lastPrice ?? q.mark ?? q.closePrice;
      if (last == null) {
        console.error(`[Schwab Quotes] ${sym}: couldn't find lastPrice/mark/closePrice. Raw entry: ${JSON.stringify(entry).slice(0, 300)}`);
        continue;
      }
      map.set(sym, { last, netChange: q.netChange ?? null });
    }
    return map.size ? map : null;
  } catch (e) {
    console.error('[Schwab Quotes] fetch failed:', e.message);
    return null;
  }
}

// ── Main ──

async function main() {
  const values = {}; // dataId -> string, only populated on success
  // Mirrors `values` but keeps numeric/structured shapes instead of the
  // display strings — this is what gets written to snapshot.json for the
  // React build (mmm-dashboard/v2) to fetch at runtime. Same source calls,
  // same null-on-failure discipline, just a second, machine-readable output
  // alongside the existing HTML string-injection. Never fabricate a value
  // here that isn't also backed by a successful fetch above.
  //
  // Same directory as the dashboard HTML, so both the classic dashboard and
  // any co-located React build (e.g. mmm-dashboard/v2/) can find it via a
  // same-directory relative fetch regardless of the Pages base path. Computed
  // here (not just at write time) because light mode needs to READ this file
  // as its starting point, not just write it.
  const jsonPath = join(dirname(DASHBOARD_PATH), 'snapshot.json');

  let raw;
  if (SNAPSHOT_MODE === 'light') {
    try {
      raw = JSON.parse(readFileSync(jsonPath, 'utf8'));
      console.log(`[Light mode] Loaded existing ${jsonPath} as base — only the Schwab section runs; everything else carries forward unchanged.`);
    } catch (e) {
      console.error(`[Light mode] Could not read existing ${jsonPath} (first run of the day?) — starting from an empty snapshot instead:`, e.message);
      raw = { generatedAt: new Date().toISOString(), futures: {}, sectors: null };
    }
  } else {
    raw = { generatedAt: new Date().toISOString(), futures: {}, sectors: null };
  }
  raw.generatedAt = new Date().toISOString(); // always reflects THIS run, even in light mode
  const today = new Date();

  // 1. Futures — Massive Basic (8h-delayed, but prior session is always fully settled)
  if (SNAPSHOT_MODE === 'full' && MASSIVE_KEY) {
    for (const [sym, ticker] of Object.entries(FUTURES)) {
      const prefix = sym.toLowerCase(); // 'es' | 'nq'
      const bar = await fetchMassiveFuturesSession(ticker);
      if (bar) {
        values[`fut.${prefix}.prior.ohlc.o`] = fmt(bar.open);
        values[`fut.${prefix}.prior.ohlc.h`] = fmt(bar.high);
        values[`fut.${prefix}.prior.ohlc.l`] = fmt(bar.low);
        values[`fut.${prefix}.prior.ohlc.c`] = fmt(bar.close);
        values[`fut.${prefix}.prior.session_date`] = bar.sessionDate;
        const piv = computePivots(bar.open, bar.high, bar.low, bar.close);
        const fib = computeFibs(bar.high, bar.low);
        values[`fut.${prefix}.pivots.pp`] = fmt(piv.pp);
        values[`fut.${prefix}.pivots.r1`] = fmt(piv.r1);
        values[`fut.${prefix}.pivots.r2`] = fmt(piv.r2);
        values[`fut.${prefix}.pivots.r3`] = fmt(piv.r3);
        values[`fut.${prefix}.pivots.s1`] = fmt(piv.s1);
        values[`fut.${prefix}.pivots.s2`] = fmt(piv.s2);
        values[`fut.${prefix}.pivots.s3`] = fmt(piv.s3);
        values[`fut.${prefix}.fibs.f38`] = fmt(fib.f38);
        values[`fut.${prefix}.fibs.f50`] = fmt(fib.f50);
        values[`fut.${prefix}.fibs.f62`] = fmt(fib.f62);
        raw.futures[prefix] = {
          contract: ticker,
          priorOhlc: { o: bar.open, h: bar.high, l: bar.low, c: bar.close, sessionDate: bar.sessionDate },
          pivots: piv,
          fibs: fib,
        };
      }
      await new Promise((r) => setTimeout(r, 1500)); // stagger — stay under 5 req/min
    }
  } else {
    console.error(SNAPSHOT_MODE === 'light' ? '[Massive] Light mode — skipping futures (carried forward from existing snapshot).' : '[Massive] MASSIVE_API_KEY not set — skipping futures.');
  }

  // 1b. Gold futures (GC) and Dollar Index futures (DX) — real futures
  // prices, not the UUP/GLD ETF proxies section 6 used to supply. Same
  // fetcher/ticker-format as ES/NQ above; only the prior-session close is
  // kept (TopAlerts just needs one number, not a full pivot ladder).
  if (SNAPSHOT_MODE === 'full' && MASSIVE_KEY) {
    for (const [sym, ticker] of Object.entries(COMMODITY_FUTURES)) {
      const bar = await fetchMassiveFuturesSession(ticker);
      if (bar) {
        if (sym === 'GOLD') raw.goldFutures = { value: fmt(bar.close), sessionDate: bar.sessionDate, source: `Massive Futures (${ticker})` };
        if (sym === 'DXY') raw.dollarIndexFutures = { value: fmt(bar.close), sessionDate: bar.sessionDate, source: `Massive Futures (${ticker})` };
      }
      await new Promise((r) => setTimeout(r, 1500)); // stagger — stay under 5 req/min
    }
  }

  // 2. Sectors — 3 grouped-daily calls (T, T-1, T-5) cover ALL tickers at once
  let sectorRowsLeaders = [];
  let sectorRowsLaggards = [];
  if (SNAPSHOT_MODE === 'full' && MASSIVE_KEY) {
    const dT = previousTradingDay(today); // most recent completed session
    const dT1 = previousTradingDay(dT);
    let d5 = dT;
    for (let i = 0; i < 5; i++) d5 = previousTradingDay(d5);

    // Sequential with a wait after each call — matches the futures loop's
    // pattern. The previous version used Promise.all with staggered START
    // times (0/1500/3000ms), which still lets all three requests be in
    // flight close together under network latency; fully sequential is the
    // safer bet against a 5-req/min limit, even though it's ~1.5s slower.
    const mapT = await fetchMassiveGroupedDaily(ymd(dT));
    await new Promise((r) => setTimeout(r, 1500));
    const mapT1 = await fetchMassiveGroupedDaily(ymd(dT1));
    await new Promise((r) => setTimeout(r, 1500));
    const mapT5 = await fetchMassiveGroupedDaily(ymd(d5));

    if (mapT && mapT1 && mapT5) {
      const rows = Object.entries(SECTOR_ETFS).map(([etf, sector]) => {
        const cNow = mapT.get(etf), cPrev = mapT1.get(etf), cFive = mapT5.get(etf);
        if (cNow == null || cPrev == null) return null;
        const d1 = ((cNow - cPrev) / cPrev) * 100;
        const d5pct = cFive != null ? ((cNow - cFive) / cFive) * 100 : null;
        return { etf, sector, close: cNow, d1, d5: d5pct };
      }).filter(Boolean);

      rows.sort((a, b) => b.d1 - a.d1);
      const leaders = rows.slice(0, 6);
      const laggards = rows.slice(-6).reverse();

      const rowHtml = (r) => {
        const cls1 = r.d1 >= 0 ? 'sev-low' : 'sev-high';
        return `<tr><td>${r.etf}</td><td>${r.sector}</td><td>$${fmt(r.close)}</td><td class="${cls1}">${r.d1 >= 0 ? '+' : ''}${fmt(r.d1)}%</td><td>${r.d5 != null ? (r.d5 >= 0 ? '+' : '') + fmt(r.d5) + '%' : '—'}</td></tr>`;
      };
      sectorRowsLeaders = leaders.map(rowHtml);
      sectorRowsLaggards = laggards.map(rowHtml);

      values['sectors.asof'] = `${ymd(dT)} close (Massive Stocks Basic, end-of-day)`;
      values['sectors.leaders'] = sectorRowsLeaders.join('');
      values['sectors.laggards'] = sectorRowsLaggards.join('');
      raw.sectors = { asOf: ymd(dT), rows }; // full sorted rows — React derives leaders/laggards itself
    } else {
      console.error('[Massive Stocks] One or more grouped-daily calls failed — leaving sectors on existing snapshot.');
    }
  }

  // 3. FRED — VIX close + HY OAS (works fine server-side; CORS only blocks browsers)
  if (SNAPSHOT_MODE === 'full' && FRED_KEY) {
    const vix = await fetchFredSeries('VIXCLS');
    if (vix) {
      values['top.vix.close'] = `${vix.value} (FRED, ${vix.date})`;
      raw.vix = { value: vix.value, date: vix.date, source: 'FRED VIXCLS' };
    }
    await new Promise((r) => setTimeout(r, 500));
    const hyOas = await fetchFredSeries('BAMLH0A0HYM2');
    if (hyOas) {
      values['sent.credit.hy_oas.value'] = `${hyOas.value} bps`;
      values['sent.credit.hy_oas.dod'] = `as of ${hyOas.date} (FRED)`;
      raw.hyOas = { value: hyOas.value, date: hyOas.date, source: 'FRED BAMLH0A0HYM2' };
    }
    await new Promise((r) => setTimeout(r, 500));
    const tenYear = await fetchFredSeries('DGS10');
    if (tenYear) raw.tenYear = { value: tenYear.value, date: tenYear.date, source: 'FRED DGS10' };
    await new Promise((r) => setTimeout(r, 500));
    const wti = await fetchFredSeries('DCOILWTICO');
    if (wti) raw.wti = { value: wti.value, date: wti.date, source: 'FRED DCOILWTICO' };
  } else {
    console.error(SNAPSHOT_MODE === 'light' ? '[FRED] Light mode — skipping (carried forward from existing snapshot).' : '[FRED] FRED_API_KEY not set — skipping VIX/HY OAS.');
  }

  // 4. CBOE Put/Call (free public page, no key — best-effort parse, see
  // function docstring). Full mode only — see SNAPSHOT_MODE comment above
  // for why: more requests to a scraped page = more bot-detection exposure
  // for data that only changes a few times a day at most.
  if (SNAPSHOT_MODE === 'full') {
    const pc = await fetchCboePutCall();
    if (pc) {
      if (pc.total) values['top.pc.total.value'] = pc.total;
      if (pc.equity) values['top.pc.equity.value'] = pc.equity;
      raw.putCall = { total: pc.total, equity: pc.equity, source: 'CBOE' };
    }
  }

  // 5. (Removed) AAII Bull-Bear spread — the scraper never reliably worked:
  // /sentimentsurvey turned out to be an evergreen "about the survey" page
  // with no weekly data, and the corrected target (/investorupdate) hit bot
  // detection on every direct-fetch test. Rather than ship something fragile
  // that silently goes stale, this stays gated in the React UI (see data.ts).

  // 6. Indices (SPX/NDX), Crypto (BTC/ETH), and ETF equivalents (GDX, UUP for
  // dollar, GLD for gold) — same Massive key, no scraping, no new provider.
  // UUP/GLD/GDX are plain ETFs, same category as the sector ETFs above; SPX/
  // NDX use Massive's "I:" index ticker prefix; BTC/ETH use the "X:" crypto
  // prefix. No confirmed direct DXY/gold-index ticker on the free tier, so
  // UUP/GLD stand in as the ETF equivalents rather than guess at an index
  // symbol that might not exist. Replaces the previously-manual SPX/BTC/XAU
  // values.
  if (SNAPSHOT_MODE === 'full' && MASSIVE_KEY) {
    const PREV_CLOSE_TICKERS = { spx: 'I:SPX', ndx: 'I:NDX', gdx: 'GDX', dxy: 'UUP', gold: 'GLD', btc: 'X:BTCUSD', eth: 'X:ETHUSD' };
    for (const [key, ticker] of Object.entries(PREV_CLOSE_TICKERS)) {
      const bar = await fetchMassivePrevClose(ticker);
      if (bar) {
        raw[key] = { value: fmt(bar.close), open: fmt(bar.open), high: fmt(bar.high), low: fmt(bar.low), source: `Massive (${ticker})` };
        if (key === 'spx') values['top.spx.last'] = fmt(bar.close);
        if (key === 'btc') values['top.btc.last'] = `$${fmt(bar.close)}`;
        if (key === 'gold') values['top.xau.last'] = `$${fmt(bar.close)}`;
      }
      await new Promise((r) => setTimeout(r, 1500)); // stagger — stay under 5 req/min
    }
  } else {
    console.error(SNAPSHOT_MODE === 'light' ? '[Massive] Light mode — skipping SPX/NDX/GDX/UUP/GLD/BTC/ETH prev-close (carried forward from existing snapshot; Schwab section below still refreshes SPX/NDX).' : '[Massive] MASSIVE_API_KEY not set — skipping SPX/NDX/GDX/UUP/GLD/BTC/ETH prev-close.');
  }

  // 7. Schwab real-time SPX/NDX/ES/NQ — overrides the Massive end-of-day
  // values set above when available, and for ES/NQ specifically, fills the
  // Live Last/As-Of/Gap% fields that have been gated since the start of this
  // build (Massive Basic has no live/intraday feed). Real-time as of THIS
  // run only (once/weekday at cron time), not continuously live for the rest
  // of the day — but that's exactly the 6am pre-market window this was built
  // for. Requires all three SCHWAB_* secrets; silently skips (leaving
  // Massive's values / gated state in place) if any are missing or the
  // refresh token has expired past its ~7-day life.
  if (SCHWAB_CLIENT_ID && SCHWAB_CLIENT_SECRET && SCHWAB_REFRESH_TOKEN) {
    const accessToken = await fetchSchwabAccessToken();
    if (accessToken) {
      const symbols = ['$SPX', '$NDX', ...Object.values(SCHWAB_FUTURES)];
      const quotes = await fetchSchwabQuotes(accessToken, symbols);
      if (quotes) {
        const spx = quotes.get('$SPX');
        const ndx = quotes.get('$NDX');
        if (spx) {
          raw.spx = { value: fmt(spx.last), open: null, high: null, low: null, source: 'Schwab, real-time (as of run)' };
          values['top.spx.last'] = fmt(spx.last);
        }
        if (ndx) {
          raw.ndx = { value: fmt(ndx.last), open: null, high: null, low: null, source: 'Schwab, real-time (as of run)' };
        }

        // ES/NQ: live price + a straightforward computed gap% against the
        // prior close section 1 already captured (live vs. prior settle,
        // NOT a modeled "probability" — the field name gapProbClosePct
        // predates this and is kept as-is for compatibility with existing
        // UI wiring rather than renamed mid-project).
        for (const [sym, ticker] of Object.entries(SCHWAB_FUTURES)) {
          const prefix = sym.toLowerCase();
          const q = quotes.get(ticker);
          if (!q) continue;
          const nowIso = new Date().toISOString();
          if (!raw.futures[prefix]) raw.futures[prefix] = {};
          raw.futures[prefix].live = { last: q.last, asOf: nowIso };
          const priorClose = raw.futures[prefix].priorOhlc?.c;
          if (priorClose != null) {
            raw.futures[prefix].gapProbClosePct = +(((q.last - priorClose) / priorClose) * 100).toFixed(2);
            raw.futures[prefix].gapPoints = +(q.last - priorClose).toFixed(2);
          }
          values[`fut.${prefix}.live.last`] = fmt(q.last);
          values[`fut.${prefix}.live.as_of`] = nowIso;
        }
      }
    }
  } else {
    console.error('[Schwab] One or more of SCHWAB_CLIENT_ID/SCHWAB_CLIENT_SECRET/SCHWAB_REFRESH_TOKEN not set — SPX/NDX/ES/NQ live stay on Massive end-of-day / gated.');
  }

  // ── Write results into the dashboard's TEXT snapshot object ──
  let html = readFileSync(DASHBOARD_PATH, 'utf8');
  let written = 0, skipped = 0;

  // Keys that live in the HTML object as `"key": [ ... multi-line array ... ].join(''),`
  // rather than a plain quoted string — need a different match/replace shape.
  const ARRAY_LITERAL_KEYS = new Set(['sectors.leaders', 'sectors.laggards']);

  for (const [key, val] of Object.entries(values)) {
    if (val == null) { skipped++; continue; }
    const escaped = String(val).replace(/\\/g, '\\\\').replace(/"/g, '\\"');

    if (ARRAY_LITERAL_KEYS.has(key)) {
      const arrayPattern = new RegExp(`"${key.replace(/\./g, '\\.')}"\\s*:\\s*\\[[\\s\\S]*?\\]\\.join\\((['"])\\1\\)`);
      if (arrayPattern.test(html)) {
        // Use a replacer FUNCTION, not a template string — a template string is
        // re-scanned by String.replace() for $1/$2/etc. patterns, and this regex
        // has a capturing group, so any literal "$" + digit in the escaped value
        // (e.g. a dollar price like "$150.96") would get corrupted into "'50.96".
        html = html.replace(arrayPattern, () => `"${key}": "${escaped}"`);
        written++;
      } else {
        console.error(`[Write] Array-literal key not found, skipped: ${key}`);
        skipped++;
      }
      continue;
    }

    const pattern = new RegExp(`("${key.replace(/\./g, '\\.')}"\\s*:\\s*)"[^"]*"`);
    if (pattern.test(html)) {
      // Same fix — replacer function instead of a "$1..." template string.
      html = html.replace(pattern, (fullMatch, prefix) => `${prefix}"${escaped}"`);
      written++;
    } else {
      console.error(`[Write] Key not found in TEXT object, skipped: ${key}`);
      skipped++;
    }
  }

  writeFileSync(DASHBOARD_PATH, html, 'utf8');

  // ── Also write the machine-readable snapshot for the React build (v2) ──
  // jsonPath was already computed at the top of main() (light mode needs it
  // for reading); reused here for writing, same path either way.
  writeFileSync(jsonPath, JSON.stringify(raw, null, 2), 'utf8');
  console.log(`Wrote ${jsonPath}`);

  console.log(`Done (${SNAPSHOT_MODE} mode). ${written} field(s) written, ${skipped} skipped (missing source data or key not found).`);
}

main().catch((e) => {
  console.error('FATAL:', e);
  process.exit(1);
});
