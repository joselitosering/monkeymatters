import { useMemo, useState } from 'react'
import { useLiveSnapshot } from '@/lib/useLiveSnapshot'
import { mergeLiveSnapshot } from '@/lib/mergeLive'
import { useCountdown } from '@/lib/useCountdown'
import { SnapshotProvider, useSnapshot } from '@/lib/SnapshotContext'
import { ExternalLink } from 'lucide-react'

function cx(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}
function toNum(v: unknown): number {
  if (typeof v === 'number') return v
  if (typeof v === 'string') return parseFloat(v.replace(/,/g, ''))
  return NaN
}
function fmtNum(v: unknown): string {
  const n = toNum(v)
  return Number.isFinite(n) ? n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'
}

// Standard, well-established market-convention thresholds — not fabricated
// data, just widely-used reference ranges applied to the real fetched value.
function vixNote(v: string | null): string {
  const n = toNum(v)
  if (!Number.isFinite(n)) return '—'
  if (n < 15) return 'Complacent — low hedging demand'
  if (n < 20) return 'Normal range'
  if (n < 30) return 'Elevated — hedging demand rising'
  return 'Fear/panic zone — historically overshoots'
}
function tenYearNote(v: string | null): string {
  const n = toNum(v)
  if (!Number.isFinite(n)) return '—'
  if (n < 3.5) return 'Low-rate regime — growth/tech tailwind'
  if (n < 4.5) return 'Neutral-to-restrictive'
  return 'Restrictive — headwind for long-duration equities'
}
function wtiNote(v: string | null): string {
  const n = toNum(v)
  if (!Number.isFinite(n)) return '—'
  if (n < 70) return 'Soft demand / oversupply regime'
  if (n < 85) return 'Normal range'
  return 'Elevated — inflation/CPI pressure risk'
}
function hyOasNote(v: string | null): string {
  const n = toNum(v)
  if (!Number.isFinite(n)) return '—'
  if (n < 300) return 'Healthy credit conditions'
  if (n < 500) return 'Caution — spreads widening'
  return 'Credit stress — risk-off signal'
}

// ── Shared primitives ──

function Panel({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cx('bg-gradient-to-b from-card to-bg-elev border border-border rounded', className)}>{children}</div>
}

function PanelHeader({ label, accent, meta, dotTone, right }: { label: string; accent?: boolean; meta?: string; dotTone?: 'gain' | 'amber' | 'loss'; right?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-border bg-black/20 flex-wrap gap-2">
      <div className="flex items-center gap-2.5">
        {dotTone && <span className={cx('pulse-dot', dotTone === 'amber' && 'amber', dotTone === 'loss' && 'loss')} />}
        <span className={cx('text-[10px] font-semibold tracking-[0.18em] uppercase', accent ? 'text-primary' : 'text-muted-foreground')}>{label}</span>
        {meta && <span className="text-[10px] text-dim font-mono-data">{meta}</span>}
      </div>
      {right}
    </div>
  )
}

function Chip({ tone, children }: { tone?: 'bull' | 'bear' | 'neutral'; children: React.ReactNode }) {
  return (
    <span className={cx('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border whitespace-nowrap',
      tone === 'bull' && 'text-gain border-gain/25 bg-gain/10',
      tone === 'bear' && 'text-loss border-loss/25 bg-loss/10',
      (!tone || tone === 'neutral') && 'text-muted-foreground border-border bg-secondary')}>
      {children}
    </span>
  )
}

function Gated() { return <span className="text-dim">—</span> }

function AnalysisNote({ text }: { text: string }) {
  return <div className="text-[11px] text-muted-foreground leading-relaxed"><span className="text-primary/80 font-medium">Analysis  </span>{text}</div>
}
function ActionsList({ rows }: { rows: { ticker: string; levels: string; strategy: string }[] }) {
  return (
    <div className="space-y-1.5">
      {rows.map((r, i) => (
        <div key={i} className="text-[11px] leading-relaxed">
          <span className="font-mono-data font-semibold text-primary">{r.ticker}</span>
          <span className="text-muted-foreground"> · {r.levels} — {r.strategy}</span>
        </div>
      ))}
    </div>
  )
}
function Tech({ rows }: { rows: [string, React.ReactNode][] }) {
  return (
    <table className="w-full text-[11px]">
      <tbody>{rows.map(([label, val], i) => (
        <tr key={i} className="border-b border-border/60 last:border-0">
          <td className="py-1 text-dim">{label}</td>
          <td className="py-1 text-right font-mono-data font-medium">{val}</td>
        </tr>
      ))}</tbody>
    </table>
  )
}

// One real candlestick per prior session bar — honest for a single OHLC bar;
// no fabricated intraday path, since we don't know the actual tick sequence.
function Candle({ o, h, l, c }: { o: number; h: number; l: number; c: number }) {
  if (![o, h, l, c].every(Number.isFinite)) {
    return <svg viewBox="0 0 60 64" className="w-14 h-16"><text x="30" y="34" textAnchor="middle" fill="hsl(var(--dim))" fontSize="9" fontFamily="JetBrains Mono">—</text></svg>
  }
  const up = c >= o
  const min = Math.min(l, o, c), max = Math.max(h, o, c)
  const range = (max - min) || 1
  const H = 56
  const y = (v: number) => H - ((v - min) / range) * H
  const bodyTop = y(Math.max(o, c)), bodyBot = y(Math.min(o, c))
  const color = up ? 'hsl(var(--gain))' : 'hsl(var(--loss))'
  return (
    <svg viewBox="0 0 60 64" className="w-14 h-16">
      <line x1="30" y1={y(h)} x2="30" y2={y(l)} stroke={color} strokeWidth="2" />
      <rect x="18" y={bodyTop} width="24" height={Math.max(2, bodyBot - bodyTop)} fill={color} rx="1" />
    </svg>
  )
}

// Real entry/stop/target as horizontal reference lines — no fabricated price
// path, since we don't have a live tick series backing these trade ideas.
function LevelLines({ entry, stop, target, label2 }: { entry: number; stop: number; target: number; label2?: number }) {
  const all = [entry, stop, target, ...(label2 != null ? [label2] : [])].filter(Number.isFinite)
  if (!all.length) return null
  const min = Math.min(...all) * 0.997, max = Math.max(...all) * 1.003
  const range = (max - min) || 1
  const W = 300, H = 70
  const y = (v: number) => H - ((v - min) / range) * H
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-16">
      {Number.isFinite(target) && <line x1="0" y1={y(target)} x2={W} y2={y(target)} stroke="hsl(var(--gain))" strokeWidth="1" strokeDasharray="3,3" opacity="0.8" />}
      {Number.isFinite(entry) && <line x1="0" y1={y(entry)} x2={W} y2={y(entry)} stroke="hsl(var(--primary))" strokeWidth="1" strokeDasharray="4,3" opacity="0.9" />}
      {Number.isFinite(stop) && <line x1="0" y1={y(stop)} x2={W} y2={y(stop)} stroke="hsl(var(--loss))" strokeWidth="1" strokeDasharray="3,3" opacity="0.8" />}
    </svg>
  )
}

// Fear & Greed arc gauge with a needle, driven by the real live score.
function FGIGauge({ score, label }: { score: number; label: string }) {
  const clamped = Math.max(0, Math.min(100, score))
  const angle = -90 + (clamped / 100) * 180
  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 120" className="w-[180px]">
        <defs>
          <linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="hsl(var(--loss))" /><stop offset="45%" stopColor="hsl(var(--accent-deep))" />
            <stop offset="70%" stopColor="hsl(var(--primary))" /><stop offset="100%" stopColor="hsl(var(--gain))" />
          </linearGradient>
        </defs>
        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="hsl(var(--border))" strokeWidth="12" strokeLinecap="round" />
        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="url(#gaugeGrad)" strokeWidth="12" strokeLinecap="round" opacity="0.9" />
        <g transform={`translate(100,100) rotate(${angle})`}>
          <line x1="0" y1="0" x2="0" y2="-64" stroke="hsl(var(--primary))" strokeWidth="2" strokeLinecap="round" />
          <circle cx="0" cy="0" r="5" fill="hsl(var(--primary))" /><circle cx="0" cy="0" r="2.5" fill="hsl(var(--background))" />
        </g>
        <text x="20" y="114" textAnchor="middle" fill="hsl(var(--dim))" fontSize="8" fontFamily="JetBrains Mono">FEAR</text>
        <text x="180" y="114" textAnchor="middle" fill="hsl(var(--dim))" fontSize="8" fontFamily="JetBrains Mono">GREED</text>
      </svg>
      <div className="font-display text-3xl font-bold text-primary -mt-2 leading-none">{Math.round(clamped)}</div>
      <div className="text-[10px] tracking-[0.2em] text-primary/80 uppercase mt-0.5">{label}</div>
    </div>
  )
}

function PivotBars({ pivots, live }: { pivots: { r2: number | null; r1: number | null; pp: number | null; s1: number | null; s2: number | null }; live?: number | null }) {
  const rows: { k: string; v: number | null; tone: 'bear' | 'amber' | 'bull' }[] = [
    { k: 'R2', v: pivots.r2, tone: 'bear' }, { k: 'R1', v: pivots.r1, tone: 'bear' },
    { k: 'PIV', v: pivots.pp, tone: 'amber' },
    { k: 'S1', v: pivots.s1, tone: 'bull' }, { k: 'S2', v: pivots.s2, tone: 'bull' },
  ]
  if (rows.every((r) => r.v == null)) {
    return <p className="text-[10.5px] text-dim border-l-2 border-border pl-2 leading-relaxed">Pivots populate once the futures snapshot has real prior-session OHLC.</p>
  }
  return (
    <div className="space-y-1">
      {live != null && <div className="flex justify-between text-[10px] text-dim uppercase tracking-wider mb-1"><span>Prior Close</span><span className="font-mono-data text-foreground">{fmtNum(live)}</span></div>}
      {rows.map((r) => (
        <div key={r.k} className="flex items-center gap-2 text-xs">
          <span className={cx('font-mono-data w-8 text-[10px]', r.tone === 'amber' ? 'text-primary font-semibold' : 'text-dim')}>{r.k}</span>
          <div className="flex-1 h-1 bg-secondary rounded relative overflow-hidden">
            <div className={cx('absolute inset-y-0 rounded', r.tone === 'bear' && 'right-0 bg-loss/50 w-1/3', r.tone === 'bull' && 'left-0 bg-gain/50 w-1/3', r.tone === 'amber' && 'left-1/2 -translate-x-1/2 w-1 bg-primary')} />
          </div>
          <span className={cx('font-mono-data w-14 text-right text-[11px]', r.tone === 'bear' && 'text-loss', r.tone === 'bull' && 'text-gain', r.tone === 'amber' && 'text-primary font-semibold')}>{r.v != null ? fmtNum(r.v) : <Gated />}</span>
        </div>
      ))}
    </div>
  )
}

function TimelineRow({ time, title, sub, tone, tag }: { time: string; title: string; sub?: string; tone: 'bull' | 'bear' | 'amber' | 'neutral'; tag?: string }) {
  const borderCls = tone === 'bull' ? 'border-gain' : tone === 'bear' ? 'border-loss' : tone === 'amber' ? 'border-primary' : 'border-border-bright'
  return (
    <div className={cx('flex items-center gap-3 px-2.5 py-2 rounded border-l-2', borderCls)}>
      <span className="font-mono-data text-[10px] text-primary w-14 flex-none">{time}</span>
      <div className="flex-1 min-w-0">
        <div className="text-[11.5px] text-foreground leading-snug">{title}</div>
        {sub && <div className="text-[10px] text-dim leading-snug">{sub}</div>}
      </div>
      {tag && <Chip tone={tone === 'amber' || tone === 'neutral' ? 'neutral' : tone}>{tag}</Chip>}
    </div>
  )
}

// ── Ticker — real scrolling marquee: live news + curated drivers/risks ──

function Ticker() {
  const snapshot = useSnapshot()
  const items = [
    ...snapshot.news.map((n) => ({ time: n.time, tag: 'NEWS', text: n.headline, tone: 'neutral' as const })),
    ...snapshot.drivers.map((d) => ({ time: d.time, tag: 'DRIVER', text: d.event, tone: 'bull' as const })),
    ...snapshot.risks.map((r) => ({ time: r.time, tag: 'RISK', text: r.event, tone: 'bear' as const })),
  ]
  const track = [...items, ...items] // duplicate for seamless loop
  return (
    <div className="overflow-hidden border-y border-border bg-black/30 relative">
      <div className="flex gap-12 whitespace-nowrap py-2.5 w-max" style={{ animation: 'scroll-x 260s linear infinite' }}>
        {track.map((it, i) => (
          <div key={i} className="inline-flex items-center gap-2.5 text-xs">
            <span className="font-mono-data text-primary text-[10px]">{it.time}</span>
            <Chip tone={it.tone}>{it.tag}</Chip>
            <span className="text-muted-foreground">{it.text}</span>
            <span className="text-dim">•</span>
          </div>
        ))}
      </div>
      <style>{`@keyframes scroll-x { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }`}</style>
    </div>
  )
}

function TopAlerts() {
  const snapshot = useSnapshot()
  const c = snapshot.command

  // Derived, not fabricated — computed straight off real sector/spotlight data.
  const topSector = [...snapshot.sectors.all].sort((a, b) => Math.abs(b.d1 ?? 0) - Math.abs(a.d1 ?? 0))[0]
  const topSectorReal = topSector?.real && topSector.d1 != null
  const topStock = snapshot.spotlight.items[0]

  const cards: { label: string; value: React.ReactNode; sub?: string; tone?: 'gain' | 'loss' }[] = [
    { label: 'VIX', value: c.vix.value, sub: c.vix.src },
    { label: 'SPX', value: c.spx.value, sub: c.spx.src },
    { label: 'NDX', value: c.ndx.gated ? null : c.ndx.value, sub: c.ndx.reason },
    { label: 'DXY', value: c.dxy.gated ? null : c.dxy.value, sub: c.dxy.reason },
    { label: 'GDX', value: c.gdx.gated ? null : c.gdx.value, sub: c.gdx.reason },
    { label: 'BTC', value: `$${c.btc.value}`, sub: c.btc.src },
    { label: 'WTI', value: c.wti.gated ? null : `$${c.wti.value}`, sub: c.wti.gated ? c.wti.reason : c.wti.reason },
    { label: 'GAP (ES)', value: snapshot.futures.es.gapProbClosePct ?? null, sub: 'Needs live/intraday feed — Massive Basic is prior-session only' },
    { label: 'TOP SECTOR', value: topSector ? `${topSector.etf} ${topSectorReal ? `${(topSector.d1! >= 0 ? '+' : '')}${topSector.d1!.toFixed(2)}%` : 'est.'}` : null, sub: topSector?.sector, tone: topSectorReal ? ((topSector.d1 ?? 0) >= 0 ? 'gain' : 'loss') : undefined },
    { label: 'TOP STOCK', value: topStock?.ticker ?? null, sub: topStock ? `Spotlight — ${topStock.catalyst}` : undefined },
    { label: 'MOOD', value: c.newsMood.score, sub: `${c.newsMood.heatCount} items / ${c.newsMood.windowMin}m`, tone: c.newsMood.tone },
    { label: 'FEAR', value: `${c.fgi.value}`, sub: c.fgi.label },
  ]

  return (
    <Panel>
      <PanelHeader label="Top Alerts" accent dotTone="amber" />
      <div className="p-4">
        <div className="flex flex-wrap gap-1.5 mb-3">{snapshot.tags.map((t) => <Chip key={t}>{t}</Chip>)}</div>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mb-3">
          {cards.map((m) => (
            <div key={m.label} className="border border-border rounded px-2.5 py-1.5">
              <div className="text-[9px] tracking-wider text-dim uppercase leading-none">{m.label}</div>
              <div className={cx('font-mono-data font-semibold text-[13px] mt-1', m.tone === 'gain' && 'text-gain', m.tone === 'loss' && 'text-loss')}>{m.value ?? <Gated />}</div>
              <div className="text-[8.5px] text-dim mt-0.5 truncate" title={m.sub}>{m.sub}</div>
            </div>
          ))}
        </div>
        <div className="border-t border-border pt-3 grid grid-cols-1 lg:grid-cols-2 gap-4">
          <AnalysisNote text={snapshot.topAnalysis} />
          <ActionsList rows={snapshot.topActions} />
        </div>
      </div>
    </Panel>
  )
}

function DadJoke() {
  const snapshot = useSnapshot()
  return (
    <div className="bg-black/20 border-b border-border px-6 py-1.5 flex items-center gap-2.5 text-[11px]">
      <span className="text-primary">😄</span>
      <span className="text-muted-foreground italic">{snapshot.joke.text}</span>
      <span className="text-dim font-mono-data ml-auto">#{snapshot.joke.id}</span>
    </div>
  )
}

function Header() {
  const cd = useCountdown()
  return (
    <header className="border-b border-border bg-bg-elev/80 backdrop-blur sticky top-0 z-50">
      <div className="px-6 py-3 flex items-center justify-between gap-6 flex-wrap">
        <div className="flex items-center gap-3">
          <svg width="30" height="30" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="14" stroke="hsl(var(--primary))" strokeWidth="1.5" />
            <path d="M 4 16 A 12 12 0 0 1 28 16" stroke="hsl(var(--primary))" strokeWidth="2.5" strokeLinecap="round" />
            <circle cx="16" cy="16" r="3" fill="hsl(var(--primary))" />
          </svg>
          <div>
            <div className="font-display text-lg font-bold tracking-tight leading-none">Daybreak<span className="text-primary">.</span></div>
            <div className="text-[8px] tracking-[0.25em] text-dim mt-0.5">MORNING MARKET MONITOR</div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-[9px] tracking-[0.2em] text-dim uppercase">NY Session</div>
            <div className="text-xs text-muted-foreground">{cd.etLabel}</div>
          </div>
          <div className="flex items-center gap-1.5">
            {[['H', cd.h], ['M', cd.m], ['S', cd.s]].map(([lbl, val], i) => (
              <div key={lbl} className="flex items-center gap-1.5">
                {i > 0 && <span className="text-primary font-display text-xl">:</span>}
                <div className="bg-gradient-to-b from-primary/10 to-primary/[0.02] border border-primary/25 rounded min-w-[48px] px-1 py-1.5 text-center">
                  <div className="font-display font-bold text-2xl leading-none text-primary tabular-nums">{val}</div>
                  <div className="text-[7px] tracking-[0.2em] text-dim uppercase mt-0.5">{lbl === 'H' ? 'Hours' : lbl === 'M' ? 'Min' : 'Sec'}</div>
                </div>
              </div>
            ))}
          </div>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold tracking-wider uppercase bg-gain/10 border border-gain/25 text-gain">
            <span className="pulse-dot" />{cd.status}
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent-deep flex items-center justify-center text-background font-bold text-xs">SM</div>
        </div>
      </div>
    </header>
  )
}

// ── Sections ──

function FuturesStrip() {
  const snapshot = useSnapshot()
  return (
    <section>
      <div className="flex items-center gap-3 mb-3">
        <span className="text-[10px] font-semibold tracking-[0.18em] uppercase text-primary">Futures — Values &amp; Technical Analysis</span>
        <span className="pulse-dot amber" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {(['es', 'nq'] as const).map((key) => {
          const f = snapshot.futures[key]
          const bearish = f.dir.toLowerCase().includes('bear')
          const o = toNum(f.priorOhlc.o), h = toNum(f.priorOhlc.h), l = toNum(f.priorOhlc.l), c = toNum(f.priorOhlc.c)
          const piv = f.pivots
          return (
            <Panel key={key} className="flex flex-col">
              <PanelHeader label={`/${key.toUpperCase()} — ${key === 'es' ? 'E-Mini S&P 500' : 'E-Mini Nasdaq 100'}`} meta={f.contract} dotTone={bearish ? 'loss' : 'gain'} />
              <div className="p-4 flex flex-col gap-3">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-mono-data text-2xl font-semibold leading-none">{Number.isFinite(c) ? fmtNum(c) : <Gated />}</div>
                    <div className="text-[10px] text-dim mt-1">prior session close</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Candle o={o} h={h} l={l} c={c} />
                    <Chip tone={bearish ? 'bear' : 'bull'}>{f.dir}</Chip>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-x-4 border-t border-border pt-2.5">
                  <Tech rows={[
                    ['Fair Value (FMV)', f.fmv.fair ?? <Gated />],
                    ['Basis (pts)', f.fmv.basisPts ?? <Gated />],
                    ['Cash Index', f.fmv.cashIndexGated ? <Gated /> : f.fmv.cashIndex],
                    ['Gap Prob %', f.gapProbClosePct ?? <Gated />],
                    ['Live Last', f.live.last ?? <Gated />],
                    ['Live As Of', f.live.asOf ?? <Gated />],
                  ]} />
                  <Tech rows={[
                    [`Open (${f.priorOhlc.sessionDate})`, Number.isFinite(o) ? fmtNum(o) : <Gated />],
                    ['High', Number.isFinite(h) ? fmtNum(h) : <Gated />],
                    ['Low', Number.isFinite(l) ? fmtNum(l) : <Gated />],
                    ['Close', Number.isFinite(c) ? fmtNum(c) : <Gated />],
                    ['VAH / POC / VAL', f.valueArea?.vah != null ? fmtNum(f.valueArea.vah) : <Gated />],
                    ['Fib 38 / 50 / 62', f.fibs.f38 != null ? `${fmtNum(f.fibs.f38)} / ${fmtNum(f.fibs.f50)} / ${fmtNum(f.fibs.f62)}` : <Gated />],
                  ]} />
                </div>

                <div className="border-t border-border pt-2.5">
                  <div className="text-[9px] tracking-wider text-dim uppercase mb-1.5">Pivots — Full Ladder</div>
                  <div className="grid grid-cols-7 gap-1 text-center">
                    {(['r3', 'r2', 'r1', 'pp', 's1', 's2', 's3'] as const).map((k) => (
                      <div key={k} className={cx('rounded px-1 py-1.5', k === 'pp' ? 'bg-primary/10 border border-primary/30' : k.startsWith('r') ? 'bg-loss/5' : 'bg-gain/5')}>
                        <div className={cx('text-[8.5px] uppercase tracking-wider', k === 'pp' ? 'text-primary font-semibold' : 'text-dim')}>{k}</div>
                        <div className={cx('font-mono-data text-[11px] font-medium', k === 'pp' ? 'text-primary' : k.startsWith('r') ? 'text-loss' : 'text-gain')}>{piv[k] != null ? fmtNum(piv[k]) : '—'}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="border-t border-border pt-2.5 flex flex-col gap-2">
                  <AnalysisNote text={f.analysis} />
                  <ActionsList rows={[{ ticker: `/${key.toUpperCase()}`, ...f.action }]} />
                </div>
              </div>
            </Panel>
          )
        })}
      </div>
    </section>
  )
}

function BriefAndLevels() {
  const snapshot = useSnapshot()
  const b = snapshot.brief
  const es = snapshot.futures.es
  return (
    <section className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      <Panel className="lg:col-span-7 flex flex-col">
        <PanelHeader label="The Morning Brief" accent dotTone="amber" meta={b.day} />
        <div className="p-5 flex-1">
          <h2 className="font-display text-2xl font-bold leading-tight mb-3"><span className="gradient-text">{b.oneThing.prompt}</span></h2>
          <p className="text-muted-foreground text-[13px] leading-relaxed mb-2">{b.oneThing.note}</p>
          <p className="text-foreground/85 text-[13px] leading-relaxed">{b.lens.text}</p>
          <p className="text-[11.5px] italic text-muted-foreground mt-2">{b.lens.prompt}</p>
          <div className="signature-line my-4" />
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div><div className="text-[9px] tracking-wider text-dim uppercase mb-1">Focus Block</div><Chip>{b.oneThing.block}</Chip></div>
            <div><div className="text-[9px] tracking-wider text-dim uppercase mb-1">Lens</div><Chip>{b.lens.title}</Chip></div>
            <div><div className="text-[9px] tracking-wider text-dim uppercase mb-1">Bias</div><Chip tone={snapshot.bias.tone === 'loss' ? 'bear' : 'bull'}>{snapshot.bias.flag}</Chip></div>
          </div>
          <div className="text-center">
            <span className="font-display text-[12.5px] italic text-foreground/85">"{b.mindset.quote}"</span>
            <span className="text-[11px] text-dim ml-2">— {b.mindset.author}</span>
            <p className="text-[10.5px] text-dim italic mt-1">{b.mindset.note}</p>
          </div>
        </div>
      </Panel>
      <Panel className="lg:col-span-5 flex flex-col">
        <PanelHeader label="Key Levels · /ES" meta={es.pivots.pp ? `Pivot ${es.pivots.pp}` : undefined} />
        <div className="p-4 space-y-3 flex-1">
          <PivotBars pivots={es.pivots} live={es.priorOhlc.c} />
          <div className="border-t border-border pt-2.5">
            <div className="text-[9px] tracking-wider text-dim uppercase mb-1.5">Quick Wins Today</div>
            <ol className="space-y-1.5 text-[11px] text-foreground/85 list-decimal list-inside leading-relaxed">
              {b.quickWins.map((w, i) => <li key={i}>{w}</li>)}
            </ol>
          </div>
        </div>
      </Panel>
    </section>
  )
}

function TradeArchitecture() {
  const snapshot = useSnapshot()
  return (
    <section>
      <div className="flex items-end justify-between mb-3 flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-semibold tracking-[0.18em] uppercase text-primary">Trade Architecture</span>
          <span className="pulse-dot amber" />
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {snapshot.ideas.items.map((idea, i) => {
          const s = idea.strategy.toLowerCase()
          const long = s.includes('call') || s.includes('long')
          const entry = toNum(idea.entry), stop = toNum(idea.stop), target = toNum(idea.target)
          return (
            <Panel key={i} className={cx('p-4 border-t-2', long ? 'border-t-gain' : 'border-t-primary')}>
              <div className="flex items-start justify-between mb-2">
                <div>
                  <Chip tone={long ? 'bull' : 'neutral'}>{idea.strategy}</Chip>
                  <div className="font-display text-xl font-bold mt-1.5">{idea.ticker}</div>
                  <div className="text-[10px] text-dim">{idea.strikes} · exp {idea.expiry}</div>
                </div>
              </div>
              <p className="text-[10.5px] text-primary/85 leading-relaxed mb-2 border-l-2 border-primary/40 pl-2">{idea.trigger}</p>
              <LevelLines entry={entry} stop={stop} target={target} />
              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs mt-2 mb-1">
                <div className="flex justify-between border-b border-border pb-1"><span className="text-dim uppercase text-[9px]">Trigger</span><span className="font-mono-data text-primary">{idea.entry}</span></div>
                <div className="flex justify-between border-b border-border pb-1"><span className="text-dim uppercase text-[9px]">Escape</span><span className="font-mono-data text-loss">{idea.stop}</span></div>
                <div className="flex justify-between"><span className="text-dim uppercase text-[9px]">Target</span><span className="font-mono-data text-gain">{idea.target}</span></div>
                <div className="flex justify-between"><span className="text-dim uppercase text-[9px]">R/R</span><span className="font-mono-data text-primary font-semibold">{idea.rr}</span></div>
              </div>
            </Panel>
          )
        })}
      </div>
      <p className="text-[10px] text-dim mt-2">{snapshot.ideas.caveat}</p>
    </section>
  )
}

function Spotlight() {
  const snapshot = useSnapshot()
  return (
    <Panel>
      <PanelHeader label="Stock Spotlight — High Conviction" accent dotTone="amber" />
      <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
        {snapshot.spotlight.items.map((s) => (
          <div key={s.ticker} className="border border-border rounded p-3">
            <div className="flex items-baseline gap-2 mb-1"><span className="font-display font-bold text-primary">{s.ticker}</span><span className="text-[10px] text-dim">{s.valuation}</span></div>
            <p className="text-[11.5px] text-foreground/85 leading-snug">{s.theme}</p>
            <p className="text-[10.5px] text-dim leading-snug mt-1">{s.levels}</p>
            <p className="text-[10.5px] text-foreground/70 leading-snug mt-1">{s.plan}</p>
          </div>
        ))}
      </div>
      <div className="px-4 pb-4"><AnalysisNote text={snapshot.spotlight.analysis} /></div>
    </Panel>
  )
}

function HeatmapAndSentiment() {
  const snapshot = useSnapshot()
  const all = snapshot.sectors.all
  const [drillSector, setDrillSector] = useState<string | null>(null)
  const maxAbs = Math.max(...all.map((s) => Math.abs(s.d1 ?? 0)), 0.01)
  // Rank by |move| so the strongest movers get the biggest cells — a real
  // (if simplified) size-by-magnitude treemap, not just a uniform grid.
  const ranked = [...all].sort((a, b) => Math.abs(b.d1 ?? 0) - Math.abs(a.d1 ?? 0))
  function spanFor(rank: number) {
    if (rank === 0) return 'col-span-2 row-span-2'
    if (rank <= 2) return 'col-span-2 row-span-1'
    return 'col-span-1 row-span-1'
  }
  function Cell({ s, rank }: { s: typeof all[number]; rank: number }) {
    const positive = (s.d1 ?? 0) >= 0
    const strength = s.real && s.d1 != null ? Math.min(1, Math.abs(s.d1) / maxAbs) : 0
    const alpha = 0.08 + strength * 0.32 // stronger move = stronger fill
    const bg = s.real
      ? `linear-gradient(135deg, hsl(var(--${positive ? 'gain' : 'loss'}) / ${alpha.toFixed(2)}), hsl(var(--${positive ? 'gain' : 'loss'}) / ${(alpha * 0.3).toFixed(2)}))`
      : 'hsl(var(--secondary))'
    const big = rank === 0
    return (
      <button
        onClick={() => setDrillSector(s.sector)}
        className="rounded p-3 flex flex-col justify-between border border-transparent hover:border-border-bright transition h-full text-left w-full"
        style={{ background: bg }}
      >
        <div className="flex items-start justify-between">
          <div className={cx('font-display font-bold leading-none', big ? 'text-base' : 'text-xs')}>{s.sector}</div>
          <div className={cx('font-mono-data font-bold', big ? 'text-lg' : 'text-sm', s.real ? (positive ? 'text-gain' : 'text-loss') : 'text-dim')}>
            {s.real && s.d1 != null ? `${positive ? '+' : ''}${s.d1.toFixed(2)}%` : 'est.'}
          </div>
        </div>
        <div className="text-[9px] text-dim">{s.etf}</div>
      </button>
    )
  }
  const c = snapshot.command
  return (
    <section className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      <Panel className="lg:col-span-8">
        <PanelHeader label="Sector Snapshot" meta={snapshot.sectors.asof} />
        <div className="p-4">
          <div className="grid grid-cols-4 gap-2" style={{ gridAutoRows: '76px' }}>
            {ranked.map((s, i) => (<div key={s.etf} className={spanFor(i)}><Cell s={s} rank={i} /></div>))}
          </div>
          {drillSector && (
            <div className="mt-3 border border-border-bright rounded p-3 bg-secondary/40 text-[11px] text-muted-foreground leading-relaxed flex items-start justify-between gap-3">
              <div>
                <span className="text-primary font-medium">{drillSector} industry breakdown — </span>
                not available yet. Drilling into industry- and stock-level heatmaps needs sector constituent + industry-classification data that isn't wired into <code className="text-dim">generate_snapshot.mjs</code> yet — real feature, not built, no placeholder numbers shown in its place.
              </div>
              <button onClick={() => setDrillSector(null)} className="text-dim hover:text-foreground flex-none">✕</button>
            </div>
          )}
          <p className="text-[10px] text-dim mt-3">All 11 S&amp;P sectors, sized and shaded by move strength — biggest mover gets the biggest cell. "est." cells (if any) stay neutral. Click a cell for industry detail.</p>
        </div>
      </Panel>
      <Panel className="lg:col-span-4 flex flex-col">
        <PanelHeader label="Sentiment & Breadth" />
        <div className="p-4 flex-1">
          <FGIGauge score={c.fgi.value} label={c.fgi.label} />
          <div className="signature-line my-4" />
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Put / Call Ratio</span><span className="font-mono-data text-primary">{c.putCall.total}</span></div>
              <div className="h-1.5 bg-border rounded overflow-hidden"><div className="h-full bg-primary rounded" style={{ width: `${Math.min(100, toNum(c.putCall.total) * 50)}%` }} /></div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Adv / Dec Line</span><span className="font-mono-data text-dim">{c.advDec.reason}</span></div>
              <div className="h-1.5 bg-border rounded" />
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">New Highs / Lows</span><span className="font-mono-data text-dim">{c.newHighsLows.reason}</span></div>
              <div className="h-1.5 bg-border rounded" />
            </div>
          </div>
          <div className="signature-line my-4" />
          <div>
            <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">AAII Bull / Bear</span><span className="font-mono-data text-primary">{c.aaii.bull}% / {c.aaii.bear}%</span></div>
            <div className="text-[10px] text-dim">{c.aaii.weekOf}</div>
          </div>
        </div>
      </Panel>
    </section>
  )
}

type ScanTab = 'futures' | 'sectors' | 'macro' | 'ideas'
function Scanner() {
  const snapshot = useSnapshot()
  const [tab, setTab] = useState<ScanTab>('futures')
  const c = snapshot.command

  const rows = useMemo(() => {
    if (tab === 'futures') return (['es', 'nq'] as const).map((k) => {
      const f = snapshot.futures[k]
      const bearish = f.dir.toLowerCase().includes('bear')
      return { sym: `/${k.toUpperCase()}`, name: f.contract, val1: f.priorOhlc.c ? fmtNum(f.priorOhlc.c) : '—', val2: 'Prior Close', tone: bearish ? 'bear' as const : 'bull' as const, signal: f.dir }
    })
    if (tab === 'sectors') return snapshot.sectors.all.map((s) => ({
      sym: s.etf, name: s.sector, val1: s.real && s.d1 != null ? `${s.d1 >= 0 ? '+' : ''}${s.d1.toFixed(2)}%` : 'est.', val2: '1D %',
      tone: s.real ? ((s.d1 ?? 0) >= 0 ? 'bull' as const : 'bear' as const) : 'neutral' as const, signal: s.real ? 'REAL' : 'EST.',
    }))
    if (tab === 'macro') return [
      { sym: 'VIX', name: 'CBOE Volatility', val1: c.vix.value, val2: vixNote(c.vix.value), tone: 'neutral' as const, signal: 'FRED' },
      { sym: 'SPX', name: 'S&P 500 Cash', val1: c.spx.value, val2: c.spx.src, tone: 'neutral' as const, signal: 'MANUAL' },
      { sym: 'NDX', name: 'Nasdaq-100 Cash', val1: c.ndx.gated ? '—' : c.ndx.value, val2: c.ndx.reason, tone: 'neutral' as const, signal: 'GATED' },
      { sym: 'DXY', name: 'US Dollar Index', val1: c.dxy.gated ? '—' : c.dxy.value, val2: c.dxy.reason, tone: 'neutral' as const, signal: 'GATED' },
      { sym: '10Y', name: 'US 10-Year Yield', val1: c.tenYear.gated ? '—' : `${c.tenYear.value}%`, val2: c.tenYear.gated ? c.tenYear.reason : tenYearNote(c.tenYear.value), tone: 'neutral' as const, signal: c.tenYear.gated ? 'GATED' : 'FRED' },
      { sym: 'WTI', name: 'Crude Oil (WTI)', val1: c.wti.gated ? '—' : `$${c.wti.value}`, val2: c.wti.gated ? c.wti.reason : wtiNote(c.wti.value), tone: 'neutral' as const, signal: c.wti.gated ? 'GATED' : 'FRED' },
      { sym: 'GDX', name: 'Gold Miners ETF', val1: c.gdx.gated ? '—' : c.gdx.value, val2: c.gdx.reason, tone: 'neutral' as const, signal: 'GATED' },
      { sym: 'XAU', name: 'Gold Spot', val1: `$${c.xau.value}`, val2: c.xau.src, tone: 'neutral' as const, signal: 'MANUAL' },
      { sym: 'BTC', name: 'Bitcoin', val1: `$${c.btc.value}`, val2: c.btc.src, tone: 'bull' as const, signal: 'MANUAL' },
      { sym: 'HY OAS', name: 'High-Yield Credit Spread', val1: `${c.hyOas.value} bps`, val2: hyOasNote(c.hyOas.value), tone: 'neutral' as const, signal: 'FRED' },
    ]
    return snapshot.ideas.items.map((idea) => ({
      sym: idea.ticker, name: idea.strategy, val1: idea.entry, val2: `R/R ${idea.rr}`,
      tone: idea.strategy.toLowerCase().includes('call') || idea.strategy.toLowerCase().includes('long') ? 'bull' as const : 'neutral' as const, signal: idea.expiry,
    }))
  }, [tab, snapshot])

  return (
    <Panel>
      <PanelHeader label="Multi-Asset Scanner" accent right={
        <div className="flex gap-1">
          {(['futures', 'sectors', 'macro', 'ideas'] as ScanTab[]).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={cx('px-2.5 py-1 text-[10px] font-semibold tracking-wider uppercase rounded transition-colors',
                tab === t ? 'text-primary bg-primary/10' : 'text-dim hover:text-muted-foreground')}>{t}</button>
          ))}
        </div>
      } />
      <div className="grid grid-cols-[80px_1fr_120px_90px] gap-3 px-4 py-2 text-[9px] text-dim uppercase tracking-wider border-b border-border">
        <div>Symbol</div><div>Name / Note</div><div className="text-right">Value</div><div className="text-right">Signal</div>
      </div>
      <div>
        {rows.map((r, i) => (
          <div key={i} className="grid grid-cols-[80px_1fr_120px_90px] gap-3 px-4 py-2.5 items-center border-b border-border/60 last:border-0 hover:bg-secondary/50 transition text-xs">
            <div className="font-display font-bold">{r.sym}</div>
            <div>
              <div className="text-dim text-[11px]">{r.name}</div>
              {r.val2 && <div className="text-dim/70 text-[9.5px] italic mt-0.5">{r.val2}</div>}
            </div>
            <div className={cx('text-right font-mono-data', r.tone === 'bull' && 'text-gain', r.tone === 'bear' && 'text-loss')}>{r.val1}</div>
            <div className="text-right"><Chip tone={r.tone}>{r.signal}</Chip></div>
          </div>
        ))}
      </div>
    </Panel>
  )
}

function CalendarAndFlow() {
  const snapshot = useSnapshot()
  return (
    <section className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      <Panel className="lg:col-span-7">
        <PanelHeader label="Economic Calendar" meta="Drivers · Risks · Earnings" />
        <div className="p-3 space-y-1">
          {snapshot.drivers.map((d, i) => <TimelineRow key={`d${i}`} time={d.time} title={d.event} sub={d.source} tone={d.severity === 'high' ? 'bull' : 'neutral'} tag="DRIVER" />)}
          {snapshot.risks.map((r, i) => <TimelineRow key={`r${i}`} time={r.time} title={r.event} sub={r.source} tone={r.severity === 'high' ? 'bear' : 'neutral'} tag="RISK" />)}
          {snapshot.earnings.today.map((e) => <TimelineRow key={e.ticker} time={e.when.slice(0, 12)} title={`${e.ticker} — ${e.consensus}`} sub={e.rec} tone={e.tone === 'gain' ? 'bull' : e.tone === 'loss' ? 'bear' : 'neutral'} tag={e.rating} />)}
          {snapshot.earnings.restOfWeek.map((e) => <TimelineRow key={e.ticker} time={e.when.slice(0, 12)} title={`${e.ticker} — ${e.note}`} tone="neutral" tag={e.rating} />)}
        </div>
        <p className="text-[10px] text-dim px-3 pb-3">{snapshot.earnings.caveat}</p>
      </Panel>
      <Panel className="lg:col-span-5 flex flex-col">
        <PanelHeader label="Unusual Options Activity" meta="Flow vendor req." right={<Chip>GATED</Chip>} />
        <div className="p-4 flex-1 flex flex-col gap-2">
          <p className="text-[10.5px] text-dim border-l-2 border-border pl-2 leading-relaxed">{snapshot.uoa.note}</p>
          <AnalysisNote text={snapshot.uoa.analysis} />
          <ActionsList rows={snapshot.uoa.actions} />
        </div>
      </Panel>
    </section>
  )
}

function BuzzAndSources() {
  const snapshot = useSnapshot()
  return (
    <section className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      <Panel className="lg:col-span-7">
        <PanelHeader label="Ticker Talk" meta="RSS + Social" />
        <div className="p-3 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead><tr className="text-left text-[9px] text-dim uppercase tracking-wider border-b border-border">
              <th className="pb-1.5 pr-2 font-normal">Ticker</th><th className="pb-1.5 pr-2 font-normal">Signal</th><th className="pb-1.5 pr-2 font-normal">Plan</th><th className="pb-1.5 font-normal">Δ</th>
            </tr></thead>
            <tbody>{snapshot.buzz.items.map((b) => (
              <tr key={b.ticker} className="border-b border-border/50 last:border-0">
                <td className="py-1.5 pr-2 font-mono-data font-semibold text-primary">{b.ticker}</td>
                <td className="py-1.5 pr-2">{b.signal}</td>
                <td className="py-1.5 pr-2 text-muted-foreground">{b.plan}</td>
                <td className="py-1.5 text-gain font-mono-data">{b.trend}</td>
              </tr>
            ))}</tbody>
          </table>
          <p className="text-[10px] text-dim mt-2">{snapshot.buzz.note}</p>
        </div>
      </Panel>
      <Panel className="lg:col-span-5">
        <PanelHeader label="Sources (MLA)" />
        <div className="p-3 max-h-64 overflow-y-auto space-y-2">
          {snapshot.sources.map((s, i) => (
            <p key={i} className="text-[10.5px] text-foreground/80 leading-relaxed pb-2 border-b border-border/60 last:border-0">
              {s.author} "{s.title}" <em className="text-dim not-italic">{s.site}</em>, {s.date}.{' '}
              <a href={s.url} target="_blank" rel="noreferrer" className="text-primary hover:underline inline-flex items-center gap-0.5">link <ExternalLink className="w-2.5 h-2.5" /></a>.
            </p>
          ))}
        </div>
      </Panel>
    </section>
  )
}

function Footer() {
  const snapshot = useSnapshot()
  return (
    <footer className="pt-6 pb-4 border-t border-border">
      <div className="flex flex-wrap items-center justify-between gap-3 text-[10px] text-dim">
        <div className="flex items-center gap-2">
          <span className="font-display font-bold text-muted-foreground">Daybreak<span className="text-primary">.</span></span>
          <span>·</span><span>Morning Market Monitor</span>
          <span>·</span><span className="font-mono-data">Snapshot: {snapshot.updatedAt}</span>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <span>Markets are risky. Not investment advice.</span><span>·</span>
          <span className="font-mono-data">Data: FRED · CBOE · AAII · Massive · feargreedchart · rss2json</span>
        </div>
      </div>
    </footer>
  )
}

// ── App ──

function App() {
  const live = useLiveSnapshot()
  const snapshot = useMemo(() => mergeLiveSnapshot(live), [live])

  return (
    <SnapshotProvider value={snapshot}>
      <div className="sun-orb" />
      <div className="relative z-10 min-h-screen bg-transparent font-sans text-foreground text-[13px]">
        <DadJoke />
        <Header />
        <Ticker />
        <main className="max-w-[1600px] mx-auto px-6 py-6 space-y-6">
          <TopAlerts />
          <FuturesStrip />
          <Spotlight />
          <BuzzAndSources />
          <BriefAndLevels />
          <TradeArchitecture />
          <HeatmapAndSentiment />
          <Scanner />
          <CalendarAndFlow />
          <Footer />
        </main>
      </div>
    </SnapshotProvider>
  )
}

export default App
