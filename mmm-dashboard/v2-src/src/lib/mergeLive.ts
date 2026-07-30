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

  if (j?.hyOas) merged.command.hyOas = { value: j.hyOas.value, unit: 'bps', asOf: `${j.hyOas.date} (FRED)` }
  if (j?.tenYear) merged.command.tenYear = { value: j.tenYear.value, gated: false, reason: `${j.tenYear.date} (FRED DGS10)` } as any
  if (j?.wti) merged.command.wti = { value: j.wti.value, gated: false, reason: `${j.wti.date} (FRED DCOILWTICO)` } as any
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
