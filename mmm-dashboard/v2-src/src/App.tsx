import { useMemo, useState } from 'react'
import { useLiveSnapshot } from '@/lib/useLiveSnapshot'
import { mergeLiveSnapshot } from '@/lib/mergeLive'
import { useCountdown } from '@/lib/useCountdown'
import { SnapshotProvider, useSnapshot } from '@/lib/SnapshotContext'
import { BracketCalc } from '@/components/BracketCalc'
import {
  ExternalLink, Newspaper, LineChart, CandlestickChart, CalendarDays,
  Briefcase, Radar, Calculator as CalcIcon,
} from 'lucide-react'

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
function srcTag(s: string | null | undefined): string {
  if (!s) return 'GATED'
  if (s.includes('Schwab')) return 'SCHWAB'
  if (s.includes('Finnhub')) return 'FINNHUB'
  if (s.includes('Massive')) return 'MASSIVE'
  if (s.includes('FRED')) return 'FRED'
  if (s.includes('CBOE')) return 'CBOE'
  return 'GATED'
}

/**
 * Bull/Bear meter — carried over from the old MMM newsletter
 * (top.bullbear.score_0_100). Composite of the real sentiment inputs the
 * pipeline actually has: Fear & Greed, VIX, and put/call. Each component is
 * only included when its source value is real, and the meter reports how many
 * inputs it used — so a partial read is visible as partial rather than
 * silently weighted as if complete.
 */
function bullBearScore(fgi: number | null, vix: string | null, pc: string | null) {
  const parts: number[] = []
  if (fgi != null && Number.isFinite(fgi)) parts.push(Math.max(0, Math.min(100, fgi)))
  const v = toNum(vix)
  if (Number.isFinite(v)) parts.push(Math.max(0, Math.min(100, 100 - ((v - 10) / 30) * 100)))
  const p = toNum(pc)
  if (Number.isFinite(p)) parts.push(Math.max(0, Math.min(100, 100 - ((p - 0.6) / 0.8) * 100)))
  if (!parts.length) return { score: null as number | null, label: '—', inputs: 0 }
  const score = Math.round(parts.reduce((a, b) => a + b, 0) / parts.length)
  const label = score <= 20 ? 'Extreme Bearish' : score <= 40 ? 'Bearish' : score <= 60 ? 'Neutral' : score <= 80 ? 'Bullish' : 'Extreme Bullish'
  return { score, label, inputs: parts.length }
}

// ── Primitives ──

function Panel({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cx('bg-gradient-to-b from-card to-bg-elev border border-border rounded-xl', className)}>{children}</div>
}

function PanelHeader({ label, accent, meta, dotTone, right }: { label: string; accent?: boolean; meta?: string; dotTone?: 'gain' | 'amber' | 'loss'; right?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-border flex-wrap gap-2">
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

function Gated() { return <span className="text-muted-foreground">—</span> }

function AnalysisNote({ text }: { text: string }) {
  return <div className="text-[12.5px] text-foreground/90 leading-relaxed"><span className="text-primary font-medium">Analysis  </span>{text}</div>
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

function TrendLine({ from, to, label }: { from: number; to: number; label: string }) {
  if (!Number.isFinite(from) || !Number.isFinite(to)) {
    return <span className="text-[10px] text-dim">Trend pending live/prior-session data</span>
  }
  const up = to >= from
  const pct = from !== 0 ? ((to - from) / from) * 100 : 0
  const color = up ? 'hsl(var(--gain))' : 'hsl(var(--loss))'
  const y1 = up ? 22 : 4, y2 = up ? 4 : 22
  return (
    <div className="flex items-center gap-2">
      <svg viewBox="0 0 44 26" className="w-11 h-6 flex-none">
        <line x1="3" y1={y1} x2="33" y2={y2} stroke={color} strokeWidth="2.5" strokeLinecap="round" />
        <polygon points={up ? '33,4 27,10 39,10' : '33,22 27,16 39,16'} fill={color} />
      </svg>
      <span className={cx('font-mono-data text-[11px] font-semibold', up ? 'text-gain' : 'text-loss')}>
        {up ? '+' : ''}{pct.toFixed(2)}%
      </span>
      <span className="text-[9.5px] text-dim">{label}</span>
    </div>
  )
}

function LevelLines({ entry, stop, target }: { entry: number; stop: number; target: number }) {
  const all = [entry, stop, target].filter(Number.isFinite)
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

// ── Shell ──

type View = 'brief' | 'markets' | 'futures' | 'calendar' | 'portfolio' | 'scanner'

const NAV: { id: View; label: string; Icon: typeof Newspaper }[] = [
  { id: 'brief', label: 'Morning Brief', Icon: Newspaper },
  { id: 'markets', label: 'Markets', Icon: LineChart },
  { id: 'futures', label: 'Futures', Icon: CandlestickChart },
  { id: 'scanner', label: 'Scanner', Icon: Radar },
  { id: 'calendar', label: 'Calendar', Icon: CalendarDays },
  { id: 'portfolio', label: 'Portfolio', Icon: Briefcase },
]

function Sidebar({ view, setView }: { view: View; setView: (v: View) => void }) {
  const snapshot = useSnapshot()
  return (
    <aside className="hidden lg:flex flex-col gap-1 w-[210px] flex-none">
      <div className="flex items-center gap-2.5 px-3 py-4">
        <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
          <circle cx="16" cy="16" r="14" stroke="hsl(var(--primary))" strokeWidth="1.5" />
          <path d="M 4 16 A 12 12 0 0 1 28 16" stroke="hsl(var(--primary))" strokeWidth="2.5" strokeLinecap="round" />
          <circle cx="16" cy="16" r="3" fill="hsl(var(--primary))" />
        </svg>
        <div>
          <div className="font-display text-[17px] font-bold tracking-tight leading-none">Daybreak<span className="text-primary">.</span></div>
          <div className="text-[7.5px] tracking-[0.22em] text-dim mt-0.5">MORNING MARKET MONITOR</div>
        </div>
      </div>

      <nav className="flex flex-col gap-0.5 px-1.5">
        {NAV.map(({ id, label, Icon }) => (
          <button key={id} onClick={() => setView(id)}
            className={cx('flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[12.5px] transition text-left',
              view === id
                ? 'bg-primary/10 text-primary font-medium border border-primary/20'
                : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60 border border-transparent')}>
            <Icon className="w-[15px] h-[15px] flex-none" />
            {label}
          </button>
        ))}
      </nav>

      <div className="mt-auto px-3 py-4 space-y-2">
        <div className="rounded-lg border border-border bg-black/20 px-3 py-2.5">
          <div className="text-[8.5px] uppercase tracking-wider text-dim">Snapshot</div>
          <div className="text-[10.5px] font-mono-data text-muted-foreground mt-0.5 leading-snug">{snapshot.updatedAt}</div>
        </div>
        <div className="flex items-center gap-2 px-1">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary to-accent-deep flex items-center justify-center text-background font-bold text-[10px]">SM</div>
          <span className="text-[11px] text-muted-foreground">Shadow Monkey</span>
        </div>
      </div>
    </aside>
  )
}

function TopBar({ view, setView }: { view: View; setView: (v: View) => void }) {
  const cd = useCountdown()
  const snapshot = useSnapshot()
  return (
    <div className="flex items-center justify-between gap-4 flex-wrap mb-5">
      <div>
        <h1 className="font-display text-2xl font-bold leading-none">
          {NAV.find((n) => n.id === view)?.label}
        </h1>
        <p className="text-[11px] text-dim mt-1.5">{snapshot.brief.day}</p>
      </div>

      <div className="flex items-center gap-3">
        {/* Mobile nav */}
        <select value={view} onChange={(e) => setView(e.target.value as View)}
          className="lg:hidden bg-black/40 border border-border rounded-lg px-2.5 py-1.5 text-[12px] text-foreground">
          {NAV.map((n) => <option key={n.id} value={n.id}>{n.label}</option>)}
        </select>

        <div className="hidden sm:flex items-center gap-2.5 rounded-xl border border-border bg-black/20 px-3 py-2">
          <div className="text-right">
            <div className="text-[8.5px] tracking-[0.18em] text-dim uppercase leading-none">NY Open</div>
            <div className="text-[10px] text-muted-foreground mt-0.5">{cd.etLabel}</div>
          </div>
          <div className="font-display font-bold text-lg text-primary tabular-nums leading-none">
            {cd.h}<span className="text-dim mx-0.5">:</span>{cd.m}<span className="text-dim mx-0.5">:</span>{cd.s}
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-[10px] font-semibold tracking-wider uppercase bg-gain/10 border border-gain/25 text-gain">
          <span className="pulse-dot" />{cd.status}
        </span>
      </div>
    </div>
  )
}

function Ticker() {
  const snapshot = useSnapshot()
  const items = [
    ...snapshot.news.map((n) => ({ time: n.time, tag: 'NEWS', text: n.headline, tone: 'neutral' as const })),
    ...snapshot.drivers.map((d) => ({ time: d.time, tag: 'DRIVER', text: d.event, tone: 'bull' as const })),
    ...snapshot.risks.map((r) => ({ time: r.time, tag: 'RISK', text: r.event, tone: 'bear' as const })),
  ]
  const track = [...items, ...items]
  return (
    <div className="overflow-hidden border-b border-border bg-black/30">
      <div className="flex gap-12 whitespace-nowrap py-2 w-max" style={{ animation: 'scroll-x 260s linear infinite' }}>
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

// ── Metric strip (compact, replaces the old 12-card grid) ──

function MetricStrip() {
  const snapshot = useSnapshot()
  const c = snapshot.command
  const topSector = [...snapshot.sectors.all].sort((a, b) => Math.abs(b.d1 ?? 0) - Math.abs(a.d1 ?? 0))[0]
  const topSectorReal = topSector?.real && topSector.d1 != null

  const cards: { label: string; value: React.ReactNode; sub?: string; tone?: 'gain' | 'loss' }[] = [
    { label: 'SPX', value: c.spx.value, sub: c.spx.src },
    { label: 'VIX', value: c.vix.value, sub: vixNote(c.vix.value) },
    { label: 'GAP /ES', value: snapshot.futures.es.gapProbClosePct ?? null, sub: snapshot.futures.es.gapProbClosePct != null ? 'live vs prior close' : 'needs live feed' },
    { label: 'FEAR', value: `${c.fgi.value}`, sub: c.fgi.label },
    { label: 'TOP SECTOR', value: topSector ? `${topSector.etf} ${topSectorReal ? `${(topSector.d1! >= 0 ? '+' : '')}${topSector.d1!.toFixed(2)}%` : 'est.'}` : null, sub: topSector?.sector, tone: topSectorReal ? ((topSector.d1 ?? 0) >= 0 ? 'gain' : 'loss') : undefined },
    { label: 'MOOD', value: c.newsMood.score, sub: `${c.newsMood.heatCount} items`, tone: c.newsMood.tone },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2.5 mb-5">
      {cards.map((m) => (
        <div key={m.label} className="rounded-xl border border-border bg-gradient-to-b from-card to-bg-elev px-3.5 py-3">
          <div className="text-[9px] tracking-wider text-dim uppercase leading-none">{m.label}</div>
          <div className={cx('font-mono-data font-semibold text-[17px] mt-1.5 leading-none', m.tone === 'gain' && 'text-gain', m.tone === 'loss' && 'text-loss')}>{m.value ?? <Gated />}</div>
          <div className="text-[9px] text-dim mt-1 truncate" title={m.sub}>{m.sub}</div>
        </div>
      ))}
    </div>
  )
}

// ── Views ──

function BriefView() {
  const snapshot = useSnapshot()
  const b = snapshot.brief
  const c = snapshot.command
  const bb = bullBearScore(c.fgi.value, c.vix.value, c.putCall.total)
  return (
    <div className="space-y-5">
      <MetricStrip />

      <Panel>
        <div className="px-6 py-8 md:px-10">
          <div className="max-w-3xl mx-auto">
            <h2 className="font-display text-3xl font-bold text-center leading-tight mb-1">
              <span className="gradient-text">🌅 Morning Brief</span>
            </h2>
            <p className="text-center text-dim text-[11px] uppercase tracking-[0.15em] mb-2">{b.day}</p>
            <div className="flex justify-center gap-2 mb-7 flex-wrap">
              <Chip tone={snapshot.bias.tone === 'loss' ? 'bear' : 'bull'}>{snapshot.bias.flag}</Chip>
              {bb.score != null && (
                <Chip>Bull/Bear {bb.score}/100 · {bb.label}</Chip>
              )}
            </div>

            {bb.score != null && (
              <div className="mb-7">
                <div className="h-2 rounded-full bg-secondary overflow-hidden border border-border">
                  <div className="h-full rounded-full bg-gradient-to-r from-loss via-primary to-gain transition-all" style={{ width: `${bb.score}%` }} />
                </div>
                <p className="text-[9.5px] text-dim mt-1.5 text-center">
                  Composite of {bb.inputs} live input{bb.inputs === 1 ? '' : 's'} (Fear &amp; Greed, VIX, put/call) — only sources with a real value are counted.
                </p>
              </div>
            )}

            <h3 className="font-display text-xl font-bold text-primary mb-3">1. Market Pulse</h3>
            <div className="space-y-3 mb-7">
              {snapshot.news.map((n, i) => (
                <p key={i} className="text-[14px] text-foreground/90 leading-relaxed">
                  <span className="mr-1.5">📌</span>{n.headline}{' '}
                  <span className="text-dim text-[11.5px]">[{n.source}, {n.time}]</span>
                </p>
              ))}
            </div>

            <div className="signature-line mb-7" />

            <h3 className="font-display text-xl font-bold text-primary mb-3">2. Founder Focus</h3>
            <blockquote className="border-l-2 border-primary/50 pl-4 italic text-foreground text-[15px] leading-relaxed mb-3">
              "{b.oneThing.prompt}"
            </blockquote>
            <p className="text-foreground/85 text-[14px] leading-relaxed mb-7">
              {b.oneThing.note} Protect <strong className="text-foreground font-semibold">{b.oneThing.block}</strong> for that outcome alone — no meetings, no notifications.
            </p>

            <div className="signature-line mb-7" />

            <h3 className="font-display text-xl font-bold text-primary mb-3">3. Strategic Lens — {b.lens.title}</h3>
            <p className="text-foreground/90 text-[14px] leading-relaxed mb-2">{b.lens.text}</p>
            <p className="text-foreground/75 text-[13.5px] italic leading-relaxed mb-7">{b.lens.prompt}</p>

            <div className="signature-line mb-7" />

            <h3 className="font-display text-xl font-bold text-primary mb-3">
              4. Quick Wins <span className="text-dim text-[12px] font-normal tracking-normal">(≤15 min each)</span>
            </h3>
            <ol className="space-y-2.5 text-[14px] text-foreground/90 leading-relaxed mb-7">
              {b.quickWins.map((w, i) => (
                <li key={i} className="flex gap-2.5">
                  <span className="text-primary font-semibold flex-none">{['①', '②', '③', '④', '⑤'][i] ?? `${i + 1}.`}</span>
                  <span>{w}</span>
                </li>
              ))}
            </ol>

            <div className="signature-line mb-7" />

            <h3 className="font-display text-xl font-bold text-primary mb-3 text-center">5. Mindset Moment</h3>
            <blockquote className="text-center">
              <p className="font-display text-[17px] italic text-foreground/90 leading-snug">"{b.mindset.quote}"</p>
              <p className="text-primary text-[12.5px] mt-1.5">— {b.mindset.author}</p>
              <p className="text-foreground/70 text-[13px] italic mt-3 max-w-lg mx-auto leading-relaxed">{b.mindset.note}</p>
            </blockquote>
          </div>
        </div>
      </Panel>

      <Panel>
        <PanelHeader label="Today's Read" accent dotTone="amber" />
        <div className="p-5 grid grid-cols-1 lg:grid-cols-2 gap-5">
          <AnalysisNote text={snapshot.topAnalysis} />
          <div>
            <div className="text-[9px] uppercase tracking-wider text-dim mb-2">Action items</div>
            <ActionsList rows={snapshot.topActions} />
          </div>
        </div>
      </Panel>

      <SourcesPanel />
    </div>
  )
}

function SourcesPanel() {
  const snapshot = useSnapshot()
  return (
    <Panel>
      <PanelHeader label="Sources (MLA)" meta={`${snapshot.sources.length} cited`} />
      <div className="p-4 max-h-72 overflow-y-auto space-y-2">
        {snapshot.sources.map((s, i) => (
          <p key={i} className="text-[10.5px] text-foreground/80 leading-relaxed pb-2 border-b border-border/60 last:border-0">
            {s.author} "{s.title}" <em className="text-dim not-italic">{s.site}</em>, {s.date}.{' '}
            <a href={s.url} target="_blank" rel="noreferrer" className="text-primary hover:underline inline-flex items-center gap-0.5">link <ExternalLink className="w-2.5 h-2.5" /></a>.
          </p>
        ))}
      </div>
    </Panel>
  )
}

function MarketsView() {
  const snapshot = useSnapshot()
  const all = snapshot.sectors.all
  const [drillSector, setDrillSector] = useState<string | null>(null)
  const maxAbs = Math.max(...all.map((s) => Math.abs(s.d1 ?? 0)), 0.01)
  const ranked = [...all].sort((a, b) => Math.abs(b.d1 ?? 0) - Math.abs(a.d1 ?? 0))
  const c = snapshot.command

  function spanFor(rank: number) {
    if (rank === 0) return 'col-span-2 row-span-2'
    if (rank <= 2) return 'col-span-2 row-span-1'
    return 'col-span-1 row-span-1'
  }
  function Cell({ s, rank }: { s: typeof all[number]; rank: number }) {
    const positive = (s.d1 ?? 0) >= 0
    const strength = s.real && s.d1 != null ? Math.min(1, Math.abs(s.d1) / maxAbs) : 0
    const alpha = 0.08 + strength * 0.32
    const bg = s.real
      ? `linear-gradient(135deg, hsl(var(--${positive ? 'gain' : 'loss'}) / ${alpha.toFixed(2)}), hsl(var(--${positive ? 'gain' : 'loss'}) / ${(alpha * 0.3).toFixed(2)}))`
      : 'hsl(var(--secondary))'
    const big = rank === 0
    return (
      <button onClick={() => setDrillSector(s.sector)}
        className="rounded-lg p-3 flex flex-col justify-between border border-transparent hover:border-border-bright transition h-full text-left w-full"
        style={{ background: bg }}>
        <div className="flex items-start justify-between gap-1">
          <div className={cx('font-display font-bold leading-none', big ? 'text-base' : 'text-xs')}>{s.sector}</div>
          <div className={cx('font-mono-data font-bold', big ? 'text-lg' : 'text-sm', s.real ? (positive ? 'text-gain' : 'text-loss') : 'text-dim')}>
            {s.real && s.d1 != null ? `${positive ? '+' : ''}${s.d1.toFixed(2)}%` : 'est.'}
          </div>
        </div>
        <div className="text-[9px] text-dim">{s.etf}</div>
      </button>
    )
  }

  return (
    <div className="space-y-5">
      <MetricStrip />
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <Panel className="xl:col-span-8">
          <PanelHeader label="Sector Snapshot" meta={snapshot.sectors.asof} />
          <div className="p-4">
            <div className="grid grid-cols-4 gap-2" style={{ gridAutoRows: '76px' }}>
              {ranked.map((s, i) => (<div key={s.etf} className={spanFor(i)}><Cell s={s} rank={i} /></div>))}
            </div>
            {drillSector && (
              <div className="mt-3 border border-border-bright rounded-lg p-3 bg-secondary/40 text-[11px] text-muted-foreground leading-relaxed flex items-start justify-between gap-3">
                <div>
                  <span className="text-primary font-medium">{drillSector} industry breakdown — </span>
                  not wired yet. Needs sector-constituent + industry-classification data that isn't in the snapshot pipeline — real feature, not built, no placeholder numbers in its place.
                </div>
                <button onClick={() => setDrillSector(null)} className="text-dim hover:text-foreground flex-none">✕</button>
              </div>
            )}
          </div>
        </Panel>

        <Panel className="xl:col-span-4 flex flex-col">
          <PanelHeader label="Sentiment & Breadth" />
          <div className="p-4 flex-1">
            <FGIGauge score={c.fgi.value} label={c.fgi.label} />
            <div className="signature-line my-4" />
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Put / Call</span><span className="font-mono-data text-primary">{c.putCall.total}</span></div>
                <div className="h-1.5 bg-border rounded overflow-hidden"><div className="h-full bg-primary rounded" style={{ width: `${Math.min(100, toNum(c.putCall.total) * 50)}%` }} /></div>
              </div>
              <div className="flex justify-between text-xs"><span className="text-muted-foreground">HY OAS</span><span className="font-mono-data text-primary">{c.hyOas.value} bps</span></div>
              <div className="text-[10px] text-dim -mt-2">{hyOasNote(c.hyOas.value)}</div>
              <div className="flex justify-between text-xs"><span className="text-muted-foreground">Adv / Dec</span><span className="font-mono-data text-muted-foreground text-[10px]">{c.advDec.reason}</span></div>
              <div className="flex justify-between text-xs"><span className="text-muted-foreground">New Highs / Lows</span><span className="font-mono-data text-muted-foreground text-[10px]">{c.newHighsLows.reason}</span></div>
              <div className="flex justify-between text-xs"><span className="text-muted-foreground">AAII Bull/Bear</span><span className="font-mono-data text-muted-foreground text-[10px]">{c.aaii.gated ? c.aaii.reason : `${c.aaii.bull}% / ${c.aaii.bear}%`}</span></div>
            </div>
          </div>
        </Panel>
      </div>

      <Panel>
        <PanelHeader label="Stock Spotlight — High Conviction" accent dotTone="amber" />
        <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
          {snapshot.spotlight.items.map((s) => (
            <div key={s.ticker} className="border border-border rounded-lg p-3.5">
              <div className="flex items-baseline gap-2 mb-1.5"><span className="font-display font-bold text-primary text-[15px]">{s.ticker}</span><span className="text-[10px] text-dim">{s.valuation}</span></div>
              <p className="text-[12px] text-foreground/90 leading-snug">{s.theme}</p>
              <p className="text-[10.5px] text-muted-foreground leading-snug mt-1.5">{s.levels}</p>
              <p className="text-[10.5px] text-foreground/70 leading-snug mt-1">{s.plan}</p>
            </div>
          ))}
        </div>
        <div className="px-4 pb-4"><AnalysisNote text={snapshot.spotlight.analysis} /></div>
      </Panel>

      <Panel>
        <PanelHeader label="Trade Architecture" accent dotTone="amber" />
        <div className="p-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
          {snapshot.ideas.items.map((idea, i) => {
            const s = idea.strategy.toLowerCase()
            const long = s.includes('call') || s.includes('long')
            return (
              <div key={i} className={cx('rounded-lg border border-border p-3.5 border-t-2', long ? 'border-t-gain' : 'border-t-primary')}>
                <Chip tone={long ? 'bull' : 'neutral'}>{idea.strategy}</Chip>
                <div className="font-display text-xl font-bold mt-1.5">{idea.ticker}</div>
                <div className="text-[10px] text-dim">{idea.strikes} · exp {idea.expiry}</div>
                <p className="text-[10.5px] text-primary/85 leading-relaxed my-2 border-l-2 border-primary/40 pl-2">{idea.trigger}</p>
                <LevelLines entry={toNum(idea.entry)} stop={toNum(idea.stop)} target={toNum(idea.target)} />
                <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs mt-2">
                  <div className="flex justify-between border-b border-border pb-1"><span className="text-dim uppercase text-[9px]">Trigger</span><span className="font-mono-data text-primary">{idea.entry}</span></div>
                  <div className="flex justify-between border-b border-border pb-1"><span className="text-dim uppercase text-[9px]">Escape</span><span className="font-mono-data text-loss">{idea.stop}</span></div>
                  <div className="flex justify-between"><span className="text-dim uppercase text-[9px]">Target</span><span className="font-mono-data text-gain">{idea.target}</span></div>
                  <div className="flex justify-between"><span className="text-dim uppercase text-[9px]">R/R</span><span className="font-mono-data text-primary font-semibold">{idea.rr}</span></div>
                </div>
              </div>
            )
          })}
        </div>
        <p className="text-[10px] text-dim px-4 pb-4">{snapshot.ideas.caveat}</p>
      </Panel>
    </div>
  )
}

function FuturesView() {
  const snapshot = useSnapshot()
  return (
    <div className="space-y-4">
      {(['es', 'nq'] as const).map((key) => {
        const f = snapshot.futures[key]
        const bearish = f.dir.toLowerCase().includes('bear')
        const o = toNum(f.priorOhlc.o), h = toNum(f.priorOhlc.h), l = toNum(f.priorOhlc.l), c = toNum(f.priorOhlc.c)
        const liveLast = toNum(f.live.last)
        const hasLive = Number.isFinite(liveLast)
        const piv = f.pivots
        return (
          <Panel key={key}>
            <PanelHeader label={`/${key.toUpperCase()} — ${key === 'es' ? 'E-Mini S&P 500' : 'E-Mini Nasdaq 100'}`} meta={f.contract} dotTone={bearish ? 'loss' : 'gain'}
              right={<Chip tone={bearish ? 'bear' : 'bull'}>{f.dir}</Chip>} />
            <div className="p-4 flex flex-col gap-3">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-mono-data text-3xl font-semibold leading-none">{Number.isFinite(c) ? fmtNum(c) : <Gated />}</div>
                  <div className="text-[10px] text-dim mt-1.5">prior session close</div>
                  <div className="mt-2.5">
                    <TrendLine from={hasLive ? c : o} to={hasLive ? liveLast : c} label={hasLive ? 'since close (Schwab)' : 'prior session'} />
                  </div>
                </div>
                <Candle o={o} h={h} l={l} c={c} />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-5 border-t border-border pt-3">
                <Tech rows={[
                  ['Fair Value (FMV)', f.fmv.fair ?? <Gated />],
                  ['Basis (pts)', f.fmv.basisPts ?? <Gated />],
                  ['Cash Index', f.fmv.cashIndexGated ? <Gated /> : f.fmv.cashIndex],
                  ['Gap vs close', f.gapProbClosePct ?? <Gated />],
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

              <div className="border-t border-border pt-3">
                <div className="text-[9px] tracking-wider text-dim uppercase mb-2">Pivots — Full Ladder</div>
                <div className="grid grid-cols-7 gap-1.5 text-center">
                  {(['r3', 'r2', 'r1', 'pp', 's1', 's2', 's3'] as const).map((k) => (
                    <div key={k} className={cx('rounded-lg px-1 py-2', k === 'pp' ? 'bg-primary/10 border border-primary/30' : k.startsWith('r') ? 'bg-loss/5 border border-loss/10' : 'bg-gain/5 border border-gain/10')}>
                      <div className={cx('text-[8.5px] uppercase tracking-wider', k === 'pp' ? 'text-primary font-semibold' : 'text-dim')}>{k}</div>
                      <div className={cx('font-mono-data text-[11px] font-medium mt-0.5', k === 'pp' ? 'text-primary' : k.startsWith('r') ? 'text-loss' : 'text-gain')}>{piv[k] != null ? fmtNum(piv[k]) : '—'}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="border-t border-border pt-3 flex flex-col gap-2">
                <AnalysisNote text={f.analysis} />
                <ActionsList rows={[{ ticker: `/${key.toUpperCase()}`, ...f.action }]} />
              </div>
            </div>
          </Panel>
        )
      })}
    </div>
  )
}

type ScanTab = 'futures' | 'sectors' | 'macro' | 'ideas'
function ScannerView() {
  const snapshot = useSnapshot()
  const [tab, setTab] = useState<ScanTab>('macro')
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
      { sym: 'SPX', name: 'S&P 500 Cash', val1: c.spx.value, val2: c.spx.src, tone: 'neutral' as const, signal: srcTag(c.spx.src) },
      { sym: 'NDX', name: 'Nasdaq-100 Cash', val1: c.ndx.gated ? '—' : c.ndx.value, val2: c.ndx.reason, tone: 'neutral' as const, signal: c.ndx.gated ? 'GATED' : srcTag(c.ndx.reason) },
      { sym: 'US$', name: 'Dollar Index (futures)', val1: c.usdIdx.gated ? '—' : c.usdIdx.value, val2: c.usdIdx.reason, tone: 'neutral' as const, signal: c.usdIdx.gated ? 'GATED' : srcTag(c.usdIdx.reason) },
      { sym: 'GC', name: 'Gold (futures)', val1: c.goldFut.gated ? '—' : c.goldFut.value, val2: c.goldFut.reason, tone: 'neutral' as const, signal: c.goldFut.gated ? 'GATED' : srcTag(c.goldFut.reason) },
      { sym: '10Y', name: 'US 10-Year Yield', val1: c.tenYear.gated ? '—' : `${c.tenYear.value}%`, val2: c.tenYear.gated ? c.tenYear.reason : tenYearNote(c.tenYear.value), tone: 'neutral' as const, signal: c.tenYear.gated ? 'GATED' : 'FRED' },
      { sym: 'WTI', name: 'Crude Oil (WTI)', val1: c.wti.gated ? '—' : `$${c.wti.value}`, val2: c.wti.gated ? c.wti.reason : wtiNote(c.wti.value), tone: 'neutral' as const, signal: c.wti.gated ? 'GATED' : 'FRED' },
      { sym: 'GDX', name: 'Gold Miners ETF', val1: c.gdx.gated ? '—' : c.gdx.value, val2: c.gdx.reason, tone: 'neutral' as const, signal: c.gdx.gated ? 'GATED' : srcTag(c.gdx.reason) },
      { sym: 'XAU', name: 'Gold (ETF proxy)', val1: `$${c.xau.value}`, val2: c.xau.src, tone: 'neutral' as const, signal: srcTag(c.xau.src) },
      { sym: 'BTC', name: 'Bitcoin', val1: `$${c.btc.value}`, val2: c.btc.src, tone: 'bull' as const, signal: srcTag(c.btc.src) },
      { sym: 'ETH', name: 'Ethereum', val1: c.eth.gated ? '—' : `$${c.eth.value}`, val2: c.eth.reason, tone: 'bull' as const, signal: c.eth.gated ? 'GATED' : 'MASSIVE' },
      { sym: 'HY OAS', name: 'High-Yield Credit Spread', val1: `${c.hyOas.value} bps`, val2: hyOasNote(c.hyOas.value), tone: 'neutral' as const, signal: 'FRED' },
    ]
    return snapshot.ideas.items.map((idea) => ({
      sym: idea.ticker, name: idea.strategy, val1: idea.entry, val2: `R/R ${idea.rr}`,
      tone: idea.strategy.toLowerCase().includes('call') || idea.strategy.toLowerCase().includes('long') ? 'bull' as const : 'neutral' as const, signal: idea.expiry,
    }))
  }, [tab, snapshot, c])

  return (
    <Panel>
      <PanelHeader label="Multi-Asset Scanner" accent right={
        <div className="flex gap-1">
          {(['macro', 'futures', 'sectors', 'ideas'] as ScanTab[]).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={cx('px-2.5 py-1 text-[10px] font-semibold tracking-wider uppercase rounded-lg transition-colors',
                tab === t ? 'text-primary bg-primary/10' : 'text-dim hover:text-muted-foreground')}>{t}</button>
          ))}
        </div>
      } />
      <div className="grid grid-cols-[70px_1fr_120px_90px] gap-3 px-4 py-2 text-[9px] text-dim uppercase tracking-wider border-b border-border">
        <div>Symbol</div><div>Name / Note</div><div className="text-right">Value</div><div className="text-right">Source</div>
      </div>
      <div>
        {rows.map((r, i) => (
          <div key={i} className="grid grid-cols-[70px_1fr_120px_90px] gap-3 px-4 py-2.5 items-center border-b border-border/60 last:border-0 hover:bg-secondary/40 transition text-xs">
            <div className="font-display font-bold">{r.sym}</div>
            <div>
              <div className="text-muted-foreground text-[11px]">{r.name}</div>
              {r.val2 && <div className="text-dim text-[9.5px] italic mt-0.5">{r.val2}</div>}
            </div>
            <div className={cx('text-right font-mono-data', r.tone === 'bull' && 'text-gain', r.tone === 'bear' && 'text-loss')}>{r.val1}</div>
            <div className="text-right"><Chip tone={r.tone}>{r.signal}</Chip></div>
          </div>
        ))}
      </div>
    </Panel>
  )
}

function CalendarView() {
  const snapshot = useSnapshot()
  return (
    <div className="space-y-4">
      <Panel>
        <PanelHeader label="Economic Calendar" meta="Drivers · Risks · Earnings" accent dotTone="amber" />
        <div className="p-3 space-y-1">
          {snapshot.drivers.map((d, i) => <TimelineRow key={`d${i}`} time={d.time} title={d.event} sub={d.source} tone={d.severity === 'high' ? 'bull' : 'neutral'} tag="DRIVER" />)}
          {snapshot.risks.map((r, i) => <TimelineRow key={`r${i}`} time={r.time} title={r.event} sub={r.source} tone={r.severity === 'high' ? 'bear' : 'neutral'} tag="RISK" />)}
        </div>
      </Panel>

      <Panel>
        <PanelHeader label="Earnings Watch" meta="Today" />
        <div className="p-3 space-y-1">
          {snapshot.earnings.today.map((e) => (
            <TimelineRow key={e.ticker} time={e.when.slice(0, 12)} title={`${e.ticker} — ${e.consensus}`} sub={e.rec}
              tone={e.tone === 'gain' ? 'bull' : e.tone === 'loss' ? 'bear' : 'neutral'} tag={e.rating} />
          ))}
          {snapshot.earnings.restOfWeek.length > 0 && (
            <>
              <div className="text-[9px] uppercase tracking-wider text-dim px-2.5 pt-3 pb-1">Rest of week</div>
              {snapshot.earnings.restOfWeek.map((e) => (
                <TimelineRow key={e.ticker} time={e.when.slice(0, 12)} title={`${e.ticker} — ${e.note}`} tone="neutral" tag={e.rating} />
              ))}
            </>
          )}
        </div>
        <p className="text-[10px] text-dim px-4 pb-4">{snapshot.earnings.caveat}</p>
      </Panel>

      <Panel>
        <PanelHeader label="Unusual Options Activity" meta="Flow vendor req." right={<Chip>GATED</Chip>} />
        <div className="p-4 flex flex-col gap-2">
          <p className="text-[11px] text-muted-foreground border-l-2 border-border pl-2.5 leading-relaxed">{snapshot.uoa.note}</p>
          <AnalysisNote text={snapshot.uoa.analysis} />
        </div>
      </Panel>

      <Panel>
        <PanelHeader label="Ticker Talk" meta="RSS + Social" />
        <div className="p-3 overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead><tr className="text-left text-[9px] text-dim uppercase tracking-wider border-b border-border">
              <th className="pb-2 pr-2 font-normal">Ticker</th><th className="pb-2 pr-2 font-normal">Signal</th><th className="pb-2 pr-2 font-normal">Plan</th><th className="pb-2 font-normal">Δ</th>
            </tr></thead>
            <tbody>{snapshot.buzz.items.map((b) => (
              <tr key={b.ticker} className="border-b border-border/50 last:border-0">
                <td className="py-2 pr-2 font-mono-data font-semibold text-primary">{b.ticker}</td>
                <td className="py-2 pr-2">{b.signal}</td>
                <td className="py-2 pr-2 text-muted-foreground">{b.plan}</td>
                <td className="py-2 text-gain font-mono-data">{b.trend}</td>
              </tr>
            ))}</tbody>
          </table>
          <p className="text-[10px] text-dim mt-2">{snapshot.buzz.note}</p>
        </div>
      </Panel>
    </div>
  )
}

/**
 * Schwab portfolio view. The snapshot pipeline authenticates to Schwab for
 * QUOTES only (marketdata/v1/quotes) — it has never called the accounts /
 * positions endpoints, so there are no holdings to show. Rather than mock a
 * portfolio, this states exactly what's missing and what it would take.
 */
function PortfolioView() {
  return (
    <div className="space-y-4">
      <Panel>
        <PanelHeader label="Schwab Portfolio" right={<Chip>NOT WIRED</Chip>} />
        <div className="p-6 max-w-2xl">
          <h3 className="font-display text-lg font-bold mb-2">No holdings data yet — and nothing invented in its place.</h3>
          <p className="text-[13px] text-foreground/85 leading-relaxed mb-4">
            The pipeline already authenticates to Schwab (OAuth refresh-token flow, working today for
            <span className="font-mono-data text-primary"> $SPX/$NDX/ES/NQ</span> quotes). Positions are a
            different scope and a different set of endpoints that this build has never called, so there is
            genuinely nothing to display here.
          </p>
          <div className="text-[9px] uppercase tracking-wider text-dim mb-2">What it needs</div>
          <ul className="space-y-2 text-[12.5px] text-foreground/85 leading-relaxed">
            <li className="flex gap-2"><span className="text-primary flex-none">1.</span><span>Schwab app scope covering accounts/positions — the current app token is quote-scoped.</span></li>
            <li className="flex gap-2"><span className="text-primary flex-none">2.</span><span>A server-side fetch of the accounts endpoint added to <code className="text-dim font-mono-data">generate_snapshot.mjs</code>, same pattern as the existing quote call.</span></li>
            <li className="flex gap-2"><span className="text-primary flex-none">3.</span><span>A decision on what actually lands in the committed snapshot — account balances in a public repo is a real consideration worth thinking through before wiring it.</span></li>
          </ul>
          <p className="text-[11px] text-dim mt-5 leading-relaxed">
            Point 3 is worth pausing on: this repo's snapshot.json is committed to a public GitHub repo on every run.
            Positions and balances would be public too unless the pipeline changes shape first.
          </p>
        </div>
      </Panel>
    </div>
  )
}

// ── App ──

function Shell() {
  const snapshot = useSnapshot()
  const [view, setView] = useState<View>('brief')
  const es = snapshot.futures.es

  const seed = {
    hPrev: es.priorOhlc.h, lPrev: es.priorOhlc.l, cPrev: es.priorOhlc.c,
    vix: toNum(snapshot.command.vix.value) || null,
    entry: toNum(es.live.last) || es.priorOhlc.c,
    contract: es.contract,
  }

  return (
    <div className="relative z-10 min-h-screen bg-transparent font-sans text-foreground text-[13px]">
      <Ticker />
      <div className="flex max-w-[1800px] mx-auto">
        <Sidebar view={view} setView={setView} />

        <main className="flex-1 min-w-0 px-5 py-6 lg:px-7">
          <TopBar view={view} setView={setView} />
          {view === 'brief' && <BriefView />}
          {view === 'markets' && <MarketsView />}
          {view === 'futures' && <FuturesView />}
          {view === 'scanner' && <ScannerView />}
          {view === 'calendar' && <CalendarView />}
          {view === 'portfolio' && <PortfolioView />}

          <footer className="pt-8 mt-8 border-t border-border">
            <div className="flex flex-wrap items-center justify-between gap-3 text-[10px] text-dim">
              <span>Markets are risky. Not investment advice.</span>
              <span className="font-mono-data">FRED · CBOE · Massive · Schwab · Finnhub · feargreedchart · rss2json</span>
            </div>
          </footer>
        </main>

        {/* Right rail — calculator, always available like the reference layout */}
        <aside className="hidden xl:block w-[330px] flex-none border-l border-border bg-black/15">
          <div className="sticky top-0 max-h-screen overflow-y-auto p-4">
            <div className="flex items-center gap-2 mb-4">
              <CalcIcon className="w-4 h-4 text-primary" />
              <span className="text-[10px] font-semibold tracking-[0.18em] uppercase text-primary">Bracket Calculator</span>
            </div>
            <BracketCalc seed={seed} />
          </div>
        </aside>
      </div>

      {/* Calculator for narrow screens — same component, inline at the end */}
      <div className="xl:hidden max-w-[1800px] mx-auto px-5 pb-8 lg:px-7">
        <Panel>
          <PanelHeader label="Bracket Calculator" accent dotTone="amber" />
          <div className="p-4"><BracketCalc seed={seed} /></div>
        </Panel>
      </div>
    </div>
  )
}

function App() {
  const live = useLiveSnapshot()
  const snapshot = useMemo(() => mergeLiveSnapshot(live), [live])
  return (
    <SnapshotProvider value={snapshot}>
      <div className="sun-orb" />
      <Shell />
    </SnapshotProvider>
  )
}

export default App
