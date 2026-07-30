import { useEffect, useState } from 'react'

// Mirrors mmm_dashboard.html's client-side "LIVE API WIRING" block exactly —
// same endpoints, same no-fabrication discipline. Anything that fails to
// fetch just stays null/undefined here; the caller falls back to the static
// baseline snapshot rather than inventing a number.

export interface LiveFutures {
  contract: string
  priorOhlc: { o: number; h: number; l: number; c: number; sessionDate: string }
  pivots: { pp: number; r1: number; r2: number; r3: number; s1: number; s2: number; s3: number }
  fibs: { f38: number; f50: number; f62: number }
}

export interface LiveSectorRow { etf: string; sector: string; close: number; d1: number; d5: number | null }

export interface LiveSnapshotJson {
  generatedAt?: string
  futures?: { es?: LiveFutures; nq?: LiveFutures }
  sectors?: { asOf: string; rows: LiveSectorRow[] } | null
  vix?: { value: string; date: string; source: string }
  hyOas?: { value: string; date: string; source: string }
  tenYear?: { value: string; date: string; source: string }
  wti?: { value: string; date: string; source: string }
  putCall?: { total: string | null; equity: string | null; source: string }
  aaii?: { bull: number; bear: number; spread: number; source: string }
  spx?: { value: string; open: string; high: string; low: string; source: string }
  ndx?: { value: string; open: string; high: string; low: string; source: string }
  gdx?: { value: string; open: string; high: string; low: string; source: string }
  dxy?: { value: string; open: string; high: string; low: string; source: string }
  gold?: { value: string; open: string; high: string; low: string; source: string }
  btc?: { value: string; open: string; high: string; low: string; source: string }
  eth?: { value: string; open: string; high: string; low: string; source: string }
}

export interface LiveNewsItem { time: string; headline: string; source: string }

export interface LiveData {
  json: LiveSnapshotJson | null
  jsonError: string | null
  fgi: { score: number; label: string } | null
  vixLive: number | null // feargreedchart's live VIX confirmation, separate from FRED's json.vix
  news: LiveNewsItem[] | null
  newsError: string | null
}

const CRYPTO_KEYWORDS = /\b(bitcoin|btc|ethereum|eth|crypto|cryptocurrency|blockchain|altcoin|stablecoin|defi|nft|coinbase|binance|dogecoin|solana|xrp|ripple)\b/i
const NEWS_FEEDS = [
  'https://feeds.reuters.com/reuters/businessNews',
  'https://www.benzinga.com/market-moving-exclusives/feed',
  // Added for premarket review — overnight action specifically, not just
  // general market-moving news. Confirmed against Benzinga's own public feed
  // directory (benzinga.com/feeds/list), not guessed.
  'https://www.benzinga.com/pre-market-outlook/feed',
  'https://www.benzinga.com/markets/asia/feed',
]

function fgiLabel(score: number): string {
  return score <= 20 ? 'Extreme Fear' : score <= 40 ? 'Fear' : score <= 60 ? 'Neutral' : score <= 80 ? 'Greed' : 'Extreme Greed'
}

function ptTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('en-US', { timeZone: 'America/Los_Angeles', hour: 'numeric', minute: '2-digit' })
  } catch {
    return '—'
  }
}

export function useLiveSnapshot(): LiveData {
  const [state, setState] = useState<LiveData>({
    json: null, jsonError: null, fgi: null, vixLive: null, news: null, newsError: null,
  })

  useEffect(() => {
    let cancelled = false

    // 1. Server-computed snapshot (futures/sectors/VIX/HY OAS/Put-Call/AAII) —
    // written by generate_snapshot.mjs into the same directory as this build.
    fetch('./snapshot.json')
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then((data: LiveSnapshotJson) => { if (!cancelled) setState((s) => ({ ...s, json: data })) })
      .catch((e) => { if (!cancelled) setState((s) => ({ ...s, jsonError: String(e?.message || e) })) })

    // 2. Fear & Greed + live VIX confirmation — feargreedchart.com, no key, CORS-enabled.
    fetch('https://feargreedchart.com/api/?action=all')
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return
        const score = data?.score?.score
        const vix = data?.market?.VIX?.price
        setState((s) => ({
          ...s,
          fgi: typeof score === 'number' ? { score, label: fgiLabel(score) } : s.fgi,
          vixLive: vix != null ? parseFloat(vix) : s.vixLive,
        }))
      })
      .catch(() => { /* leave fgi/vixLive null — baseline fallback handles it */ })

    // 3. News headlines — rss2json, no key, CORS-enabled. Four feeds now
    // (general market-moving + dedicated premarket outlook + Asia overnight
    // session), same crypto keyword filter applied to every source. Limit
    // bumped from 8 to 14 since 4 feeds need more room than 2 did, and
    // sorted newest-first so overnight/premarket items surface even though
    // they're spread across more sources.
    Promise.all(
      NEWS_FEEDS.map((feedUrl) =>
        fetch('https://api.rss2json.com/v1/api.json?rss_url=' + encodeURIComponent(feedUrl))
          .then((r) => r.json())
          .then((data) => {
            if (!data || data.status !== 'ok') return [] as any[]
            const src = data.feed?.title || '—'
            return (data.items || []).map((it: any) => ({ ...it, _source: src }))
          })
          .catch(() => [] as any[])
      )
    )
      .then((results) => {
        if (cancelled) return
        const all = results.flat().filter((it) => !CRYPTO_KEYWORDS.test(it.title || ''))
        if (!all.length) return
        all.sort((a, b) => new Date(b.pubDate).getTime() - new Date(a.pubDate).getTime())
        const items: LiveNewsItem[] = all.slice(0, 14).map((it) => ({
          time: ptTime(it.pubDate),
          headline: it.title,
          source: it._source,
        }))
        setState((s) => ({ ...s, news: items }))
      })
      .catch((e) => { if (!cancelled) setState((s) => ({ ...s, newsError: String(e?.message || e) })) })

    return () => { cancelled = true }
  }, [])

  return state
}
