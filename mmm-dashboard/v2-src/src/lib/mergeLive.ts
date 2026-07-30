import { snapshot as baseline } from './data'
import type { LiveData } from './useLiveSnapshot'

// Builds the object every page component reads, by layering live values over
// the curated baseline — never the reverse. If a live source hasn't loaded
// yet or failed, that field silently stays on the baseline (which itself is
// honestly gated with "—" wherever there's no real number) instead of ever
// showing a blank or a guess.
export function mergeLiveSnapshot(live: LiveData): typeof baseline {
  const j = live.json

  const merged = structuredClone(baseline)

  // Fear & Greed (feargreedchart.com) — live score overrides the baseline read.
  if (live.fgi) {
    merged.command.fgi = { value: Math.round(live.fgi.score), label: live.fgi.label, note: 'live — feargreedchart.com' }
  }

  // VIX — prefer FRED (server-computed, in snapshot.json) since it's the
  // "official" close; fall back to feargreedchart's live intraday read.
  if (j?.vix) {
    merged.command.vix = { value: j.vix.value, src: `FRED VIXCLS, ${j.vix.date}` }
  } else if (live.vixLive != null) {
    merged.command.vix = { value: live.vixLive.toFixed(2), src: 'feargreedchart.com, live' }
  }

  // FRED's BAMLH0A0HYM2 series returns a PERCENTAGE (e.g. "2.87" = 2.87%),
  // not basis points — multiply by 100 for the correct bps figure instead of
  // mislabeling the raw percentage as "287 bps" would otherwise become "2.87 bps".
  if (j?.hyOas) {
    const pct = parseFloat(j.hyOas.value)
    merged.command.hyOas = { value: Number.isFinite(pct) ? (pct * 100).toFixed(0) : j.hyOas.value, unit: 'bps', asOf: `${j.hyOas.date} (FRED)` }
  }
  if (j?.tenYear) merged.command.tenYear = { value: j.tenYear.value, gated: false, reason: `${j.tenYear.date} (FRED DGS10)` } as any
  if (j?.wti) merged.command.wti = { value: j.wti.value, gated: false, reason: `${j.wti.date} (FRED DCOILWTICO)` } as any

  // SPX/BTC replace the manually-curated baseline values once real Massive
  // data lands; NDX/GDX/ETH un-gate from "no feed wired" the same way
  // tenYear/wti do above — no scraping, same Massive key/pipeline as futures.
  if (j?.spx) merged.command.spx = { value: j.spx.value, src: j.spx.source }
  if (j?.btc) merged.command.btc = { value: j.btc.value, src: j.btc.source }
  if (j?.ndx) merged.command.ndx = { value: j.ndx.value, gated: false, reason: j.ndx.source } as any
  if (j?.gdx) merged.command.gdx = { value: j.gdx.value, gated: false, reason: j.gdx.source } as any
  if (j?.eth) merged.command.eth = { value: j.eth.value, gated: false, reason: j.eth.source } as any

  // DXY/Gold: no confirmed direct index ticker on Massive's free tier, so
  // these carry UUP/GLD ETF values instead (see generate_snapshot.mjs) — DXY
  // un-gates the same way NDX/GDX do; gold replaces the manually-curated XAU
  // baseline the same way SPX/BTC do above.
  if (j?.dxy) merged.command.dxy = { value: j.dxy.value, gated: false, reason: j.dxy.source } as any
  if (j?.gold) merged.command.xau = { value: j.gold.value, src: j.gold.source }

  if (j?.putCall?.total || j?.putCall?.equity) {
    merged.command.putCall = {
      total: j.putCall.total ?? merged.command.putCall.total,
      equity: j.putCall.equity ?? merged.command.putCall.equity,
      src: 'CBOE, live',
    }
  }
  if (j?.aaii) {
    merged.command.aaii = {
      spread: `${j.aaii.spread > 0 ? '+' : ''}${j.aaii.spread}`,
      bull: j.aaii.bull, bear: j.aaii.bear,
      weekOf: 'Published this week (AAII)',
    }
  }

  // Futures — prior-session OHLC/pivots/fibs from Massive, computed server-side.
  for (const key of ['es', 'nq'] as const) {
    const f = j?.futures?.[key]
    if (!f) continue
    const dest = merged.futures[key]
    dest.priorOhlc = { o: f.priorOhlc.o, h: f.priorOhlc.h, l: f.priorOhlc.l, c: f.priorOhlc.c, sessionDate: f.priorOhlc.sessionDate }
    dest.pivots = f.pivots
    dest.fibs = f.fibs
  }

  // Sectors — overlay real 1D% for any ETF the server actually computed,
  // across the whole 11-sector market list; anything not present in the
  // live rows stays "est."
  if (j?.sectors?.rows?.length) {
    const byEtf = new Map(j.sectors.rows.map((r) => [r.etf, r]))
    merged.sectors.all = merged.sectors.all.map((s) => {
      const live = byEtf.get(s.etf)
      return live ? { ...s, d1: live.d1, real: true, note: undefined } : s
    })
    merged.sectors.asof = `${j.sectors.asOf} close (Massive Stocks Basic, end-of-day)`
  }

  // News — rss2json headlines replace the baked-in headline list once loaded.
  if (live.news?.length) {
    merged.news = live.news
  }

  return merged
}
