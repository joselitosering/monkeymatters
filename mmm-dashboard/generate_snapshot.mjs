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

// SPDR sector ETFs — Massive Stocks Basic covers all of these.
const SECTOR_ETFS = {
  XLK: 'Technology', XLF: 'Financials', XLE: 'Energy', XLV: 'Health Care',
  XLI: 'Industrials', XLY: 'Consumer Discretionary', XLP: 'Consumer Staples',
  XLU: 'Utilities', XLB: 'Materials', XLRE: 'Real Estate', XLC: 'Communication Services',
};

const MASSIVE_KEY = process.env.MASSIVE_API_KEY || '';
const FRED_KEY = process.env.FRED_API_KEY || '';
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
 * Parses AAII's free weekly sentiment survey page/article for Bullish/
 * Neutral/Bearish percentages. Pattern matched against real AAII article
 * text sampled 2026-07-29 (format: "Bullish: NN.N%, up/down N.N points").
 * Same caveat as CBOE: if AAII changes their template wording, this needs
 * re-tuning — logs clearly on a miss rather than fabricating a number.
 */
async function fetchAaiiSentiment() {
  const url = 'https://www.aaii.com/sentimentsurvey';
  try {
    const res = await fetch(url);
    const html = await res.text();
    const bullMatch = html.match(/Bullish:?\s*(\d{1,2}\.\d)%/i);
    const neutMatch = html.match(/Neutral:?\s*(\d{1,2}\.\d)%/i);
    const bearMatch = html.match(/Bearish:?\s*(\d{1,2}\.\d)%/i);
    if (!bullMatch || !bearMatch) {
      console.error('[AAII] Could not find Bullish/Bearish figures on the page — template may have changed, or this ran before Thursday\'s weekly update. Needs manual check.');
      return null;
    }
    const bull = parseFloat(bullMatch[1]);
    const bear = parseFloat(bearMatch[1]);
    const neutral = neutMatch ? parseFloat(neutMatch[1]) : null;
    return { bull, bear, neutral, spread: +(bull - bear).toFixed(1) };
  } catch (e) {
    console.error('[AAII] fetch failed:', e.message);
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
  const raw = { generatedAt: new Date().toISOString(), futures: {}, sectors: null };
  const today = new Date();

  // 1. Futures — Massive Basic (8h-delayed, but prior session is always fully settled)
  if (MASSIVE_KEY) {
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
    console.error('[Massive] MASSIVE_API_KEY not set — skipping futures.');
  }

  // 2. Sectors — 3 grouped-daily calls (T, T-1, T-5) cover ALL tickers at once
  let sectorRowsLeaders = [];
  let sectorRowsLaggards = [];
  if (MASSIVE_KEY) {
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
  if (FRED_KEY) {
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
    console.error('[FRED] FRED_API_KEY not set — skipping VIX/HY OAS.');
  }

  // 4. CBOE Put/Call (free public page, no key — best-effort parse, see function docstring)
  const pc = await fetchCboePutCall();
  if (pc) {
    if (pc.total) values['top.pc.total.value'] = pc.total;
    if (pc.equity) values['top.pc.equity.value'] = pc.equity;
    raw.putCall = { total: pc.total, equity: pc.equity, source: 'CBOE' };
  }

  // 5. AAII Bull-Bear spread (free public page, no key — best-effort parse, see function docstring)
  const aaii = await fetchAaiiSentiment();
  if (aaii) {
    values['sent.aaii.spread'] = `${aaii.spread > 0 ? '+' : ''}${aaii.spread} pts (Bull ${aaii.bull}% / Bear ${aaii.bear}%)`;
    values['sent.aaii.week_of'] = `Published this week (AAII)`;
    raw.aaii = { bull: aaii.bull, bear: aaii.bear, spread: aaii.spread, source: 'AAII' };
  }

  // 6. Indices (SPX/NDX), Crypto (BTC/ETH), and ETF equivalents (GDX, UUP for
  // dollar, GLD for gold) — same Massive key, no scraping, no new provider.
  // UUP/GLD/GDX are plain ETFs, same category as the sector ETFs above; SPX/
  // NDX use Massive's "I:" index ticker prefix; BTC/ETH use the "X:" crypto
  // prefix. No confirmed direct DXY/gold-index ticker on the free tier, so
  // UUP/GLD stand in as the ETF equivalents rather than guess at an index
  // symbol that might not exist. Replaces the previously-manual SPX/BTC/XAU
  // values.
  if (MASSIVE_KEY) {
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
    console.error('[Massive] MASSIVE_API_KEY not set — skipping SPX/NDX/GDX/UUP/GLD/BTC/ETH prev-close.');
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
  // Same directory as the dashboard HTML, so both the classic dashboard and
  // any co-located React build (e.g. mmm-dashboard/v2/) can find it via a
  // same-directory relative fetch regardless of the Pages base path.
  const jsonPath = join(dirname(DASHBOARD_PATH), 'snapshot.json');
  writeFileSync(jsonPath, JSON.stringify(raw, null, 2), 'utf8');
  console.log(`Wrote ${jsonPath}`);

  console.log(`Done. ${written} field(s) written, ${skipped} skipped (missing source data or key not found).`);
}

main().catch((e) => {
  console.error('FATAL:', e);
  process.exit(1);
});
