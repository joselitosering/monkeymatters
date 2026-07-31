import { useMemo, useState } from 'react'
import {
  CONTRACTS, calculate, computePivots, MODE_COPY,
  type Sym, type Side, type Term, type StopMethod, type TargetMode,
} from '@/lib/calculator'

function cx(...c: (string | false | undefined)[]) { return c.filter(Boolean).join(' ') }
const f2 = (n: number, d = 2) => Number.isFinite(n) ? n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }) : '—'
const money = (n: number, d = 0) => (n < 0 ? '-' : '') + '$' + f2(Math.abs(n), d)

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-[9.5px] uppercase tracking-wider text-dim mb-1">{label}</span>
      {children}
    </label>
  )
}

const inputCls = 'w-full bg-black/40 border border-border rounded-lg px-2.5 py-1.5 text-[12.5px] font-mono-data text-foreground focus:outline-none focus:border-primary/60 transition'

/**
 * Bracket / position-size calculator. Auto-seeds prior H/L/C and VIX from the
 * live snapshot when available (passed in via props) so it isn't a blank form
 * every morning — but every field stays editable, and nothing is invented:
 * if the snapshot has no value the field simply starts empty.
 */
export function BracketCalc({ seed }: {
  seed: { hPrev?: number | null; lPrev?: number | null; cPrev?: number | null; vix?: number | null; entry?: number | null; contract?: string }
}) {
  const [sym, setSym] = useState<Sym>('ES')
  const [side, setSide] = useState<Side>('long')
  const [entry, setEntry] = useState<string>(seed.entry != null ? String(seed.entry) : '')
  const [atr, setAtr] = useState('')
  const [stopMethod, setStopMethod] = useState<StopMethod>('atr')
  const [stopParam, setStopParam] = useState('0.6')
  const [bufferTicks, setBufferTicks] = useState('4')
  const [structKey, setStructKey] = useState('PP')
  const [autoStops, setAutoStops] = useState(true)
  const [targetMode, setTargetMode] = useState<TargetMode>('r')
  const [vix, setVix] = useState<string>(seed.vix != null ? String(seed.vix) : '')
  const [trin, setTrin] = useState('1.0')
  const [tick, setTick] = useState('0')
  const [term, setTerm] = useState<Term>('contango')
  const [dailyLoss, setDailyLoss] = useState('2500')
  const [riskFrac, setRiskFrac] = useState('30')
  const [maxStd, setMaxStd] = useState('10')
  const [hPrev, setHPrev] = useState<string>(seed.hPrev != null ? String(seed.hPrev) : '')
  const [lPrev, setLPrev] = useState<string>(seed.lPrev != null ? String(seed.lPrev) : '')
  const [cPrev, setCPrev] = useState<string>(seed.cPrev != null ? String(seed.cPrev) : '')

  const pivots = useMemo(() => {
    const H = parseFloat(hPrev), L = parseFloat(lPrev), C = parseFloat(cPrev)
    if (![H, L, C].every(Number.isFinite)) return null
    return computePivots(H, L, C)
  }, [hPrev, lPrev, cPrev])

  const levels: Record<string, number | null> = useMemo(() => ({
    PP: pivots?.P ?? null, R1: pivots?.R1 ?? null, R2: pivots?.R2 ?? null, R3: pivots?.R3 ?? null,
    S1: pivots?.S1 ?? null, S2: pivots?.S2 ?? null, S3: pivots?.S3 ?? null,
  }), [pivots])

  const res = useMemo(() => calculate({
    sym, side,
    entry: parseFloat(entry) || 0,
    atr: parseFloat(atr) || 0,
    stopMethod,
    stopParam: parseFloat(stopParam) || 0.6,
    bufferTicks: parseFloat(bufferTicks) || 0,
    structLevelPx: levels[structKey] ?? null,
    autoModeStops: autoStops,
    targetMode,
    levels,
    vix: parseFloat(vix) || 0,
    trin: parseFloat(trin) || 1,
    tick: parseFloat(tick) || 0,
    term,
    dailyLoss: parseFloat(dailyLoss) || 0,
    riskFracPct: parseFloat(riskFrac) || 0,
    maxStd: parseFloat(maxStd) || 999,
  }), [sym, side, entry, atr, stopMethod, stopParam, bufferTicks, structKey, autoStops, targetMode, levels, vix, trin, tick, term, dailyLoss, riskFrac, maxStd])

  const modeTone = res.mode === 'Trending' ? 'text-gain border-gain/30 bg-gain/10'
    : res.mode === 'Balance' ? 'text-primary border-primary/30 bg-primary/10'
    : 'text-loss border-loss/30 bg-loss/10'

  return (
    <div className="space-y-3.5">
      {/* Regime + risk header */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className={cx('px-2 py-0.5 rounded-full text-[10px] font-semibold border', modeTone)}>Mode: {res.mode}</span>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono-data border border-border bg-secondary text-muted-foreground">{res.multiplier.toFixed(2)}×</span>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono-data border border-primary/25 bg-primary/10 text-primary">{money(res.riskTrade)}/trade</span>
      </div>
      <p className="text-[10.5px] text-muted-foreground leading-snug">{MODE_COPY[res.mode].note}</p>

      {/* Contract + side */}
      <div className="grid grid-cols-2 gap-2">
        <Field label="Contract">
          <select value={sym} onChange={(e) => setSym(e.target.value as Sym)} className={inputCls}>
            {(Object.keys(CONTRACTS) as Sym[]).map((s) => <option key={s} value={s}>{CONTRACTS[s].label}</option>)}
          </select>
        </Field>
        <Field label="Direction">
          <div className="grid grid-cols-2 gap-1">
            {(['long', 'short'] as Side[]).map((s) => (
              <button key={s} onClick={() => setSide(s)}
                className={cx('py-1.5 rounded-lg text-[11px] font-semibold uppercase tracking-wide border transition',
                  side === s
                    ? (s === 'long' ? 'bg-gain/15 border-gain/40 text-gain' : 'bg-loss/15 border-loss/40 text-loss')
                    : 'border-border text-dim hover:text-muted-foreground')}>
                {s}
              </button>
            ))}
          </div>
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Field label="Entry"><input value={entry} onChange={(e) => setEntry(e.target.value)} placeholder="—" inputMode="decimal" className={inputCls} /></Field>
        <Field label="ATR (pts)"><input value={atr} onChange={(e) => setAtr(e.target.value)} placeholder="—" inputMode="decimal" className={inputCls} /></Field>
      </div>

      {/* Stop config */}
      <div className="border-t border-border pt-3 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[9.5px] uppercase tracking-wider text-dim">Stop</span>
          <button onClick={() => setAutoStops((v) => !v)}
            className={cx('px-2 py-0.5 rounded-full text-[9.5px] font-semibold border transition',
              autoStops ? 'bg-primary/15 border-primary/40 text-primary' : 'border-border text-dim')}>
            Auto by regime {autoStops ? 'ON' : 'OFF'}
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Method">
            <select value={stopMethod} onChange={(e) => setStopMethod(e.target.value as StopMethod)} className={inputCls}>
              <option value="atr">ATR multiple</option>
              <option value="fixed">Fixed points</option>
              <option value="structure">Structure level</option>
            </select>
          </Field>
          {stopMethod === 'structure' ? (
            <Field label="Level">
              <select value={structKey} onChange={(e) => setStructKey(e.target.value)} className={inputCls}>
                {Object.keys(levels).map((k) => <option key={k} value={k}>{k}{levels[k] == null ? ' (—)' : ''}</option>)}
              </select>
            </Field>
          ) : (
            <Field label={stopMethod === 'atr' ? 'ATR ×' : 'Points'}>
              <input value={stopParam} onChange={(e) => setStopParam(e.target.value)} disabled={autoStops && stopMethod === 'atr'}
                inputMode="decimal" className={cx(inputCls, autoStops && stopMethod === 'atr' && 'opacity-50')} />
            </Field>
          )}
        </div>
        {stopMethod === 'structure' && (
          <Field label="Buffer (ticks)"><input value={bufferTicks} onChange={(e) => setBufferTicks(e.target.value)} inputMode="decimal" className={inputCls} /></Field>
        )}
      </div>

      {/* Prior session H/L/C -> pivots */}
      <div className="border-t border-border pt-3 space-y-2">
        <span className="text-[9.5px] uppercase tracking-wider text-dim">Prior session H / L / C</span>
        <div className="grid grid-cols-3 gap-2">
          <input value={hPrev} onChange={(e) => setHPrev(e.target.value)} placeholder="High" inputMode="decimal" className={inputCls} />
          <input value={lPrev} onChange={(e) => setLPrev(e.target.value)} placeholder="Low" inputMode="decimal" className={inputCls} />
          <input value={cPrev} onChange={(e) => setCPrev(e.target.value)} placeholder="Close" inputMode="decimal" className={inputCls} />
        </div>
        {pivots ? (
          <div className="flex flex-wrap gap-1">
            {([['R3', pivots.R3], ['R2', pivots.R2], ['R1', pivots.R1], ['PP', pivots.P], ['S1', pivots.S1], ['S2', pivots.S2], ['S3', pivots.S3]] as [string, number][]).map(([n, v]) => (
              <span key={n} className={cx('px-1.5 py-0.5 rounded text-[9.5px] font-mono-data border',
                n === 'PP' ? 'border-primary/30 bg-primary/10 text-primary' : n.startsWith('R') ? 'border-loss/20 bg-loss/5 text-loss' : 'border-gain/20 bg-gain/5 text-gain')}>
                {n} {f2(v)}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-[10px] text-dim">Enter prior H/L/C to compute the pivot ladder.</p>
        )}
      </div>

      {/* Internals */}
      <div className="border-t border-border pt-3 space-y-2">
        <span className="text-[9.5px] uppercase tracking-wider text-dim">Internals</span>
        <div className="grid grid-cols-3 gap-2">
          <Field label="VIX"><input value={vix} onChange={(e) => setVix(e.target.value)} placeholder="—" inputMode="decimal" className={inputCls} /></Field>
          <Field label="TRIN"><input value={trin} onChange={(e) => setTrin(e.target.value)} inputMode="decimal" className={inputCls} /></Field>
          <Field label="TICK"><input value={tick} onChange={(e) => setTick(e.target.value)} inputMode="decimal" className={inputCls} /></Field>
        </div>
        <Field label="Term structure">
          <select value={term} onChange={(e) => setTerm(e.target.value as Term)} className={inputCls}>
            <option value="contango">Contango</option><option value="flat">Flat</option><option value="backwardation">Backwardation</option>
          </select>
        </Field>
      </div>

      {/* Account */}
      <div className="border-t border-border pt-3 space-y-2">
        <span className="text-[9.5px] uppercase tracking-wider text-dim">Account &amp; risk</span>
        <div className="grid grid-cols-3 gap-2">
          <Field label="Daily loss $"><input value={dailyLoss} onChange={(e) => setDailyLoss(e.target.value)} inputMode="decimal" className={inputCls} /></Field>
          <Field label="Risk %"><input value={riskFrac} onChange={(e) => setRiskFrac(e.target.value)} inputMode="decimal" className={inputCls} /></Field>
          <Field label="Max std"><input value={maxStd} onChange={(e) => setMaxStd(e.target.value)} inputMode="decimal" className={inputCls} /></Field>
        </div>
        <Field label="Targets">
          <select value={targetMode} onChange={(e) => setTargetMode(e.target.value as TargetMode)} className={inputCls}>
            <option value="r">1R / 2R</option><option value="structure">Nearest structure levels</option>
          </select>
        </Field>
      </div>

      {/* Output */}
      <div className="border-t border-border pt-3">
        {!res.ok ? (
          <div className="rounded-lg border border-primary/25 bg-primary/5 px-3 py-2.5 text-[11px] text-primary">{res.error}</div>
        ) : (
          <div className="space-y-2.5">
            <div className="rounded-lg bg-black/30 border border-border-bright p-3">
              <div className="text-[9.5px] uppercase tracking-wider text-dim mb-1.5">Position size</div>
              <div className="font-display text-2xl font-bold text-primary leading-none">
                {res.stdCount} <span className="text-[13px] text-muted-foreground font-sans font-normal">std</span>
                <span className="text-dim mx-1.5 text-base">/</span>
                {res.microCount} <span className="text-[13px] text-muted-foreground font-sans font-normal">micro</span>
              </div>
              <div className="text-[10px] text-dim mt-1.5">
                {f2(res.stopPts)} pt stop ({Math.round(res.distStopTicks)} ticks) · {money(res.riskPerCon, 2)}/contract
              </div>
            </div>

            <div className="grid grid-cols-4 gap-1.5 text-center">
              {([
                ['Stop', res.stopPx, 'text-loss'],
                ['Entry', res.entry, 'text-foreground'],
                ['T1', res.t1, 'text-gain'],
                ['T2', res.t2, 'text-gain'],
              ] as [string, number, string][]).map(([l, v, cls]) => (
                <div key={l} className="rounded-lg border border-border py-1.5">
                  <div className="text-[8.5px] uppercase tracking-wider text-dim">{l}</div>
                  <div className={cx('font-mono-data text-[12px] font-semibold mt-0.5', cls)}>{f2(v)}</div>
                </div>
              ))}
            </div>
            {targetMode === 'structure' && (
              <p className="text-[9.5px] text-dim text-center">T1 → {res.t1Label} · T2 → {res.t2Label}</p>
            )}

            <table className="w-full text-[11px]">
              <tbody>
                {([
                  ['Risk at stop', money(res.riskStopAcct, 2), 'text-loss'],
                  ['P/L at T1', money(res.pnlT1Acct, 2), 'text-gain'],
                  ['P/L at T2', money(res.pnlT2Acct, 2), 'text-gain'],
                  ['Per point', money(res.perPointAcct, 2), 'text-muted-foreground'],
                  ['Per tick', money(res.perTickAcct, 2), 'text-muted-foreground'],
                ] as [string, string, string][]).map(([l, v, cls]) => (
                  <tr key={l} className="border-b border-border/50 last:border-0">
                    <td className="py-1 text-dim">{l}</td>
                    <td className={cx('py-1 text-right font-mono-data font-medium', cls)}>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <p className="text-[10px] text-muted-foreground leading-relaxed border-l-2 border-primary/40 pl-2">
              {MODE_COPY[res.mode].strategy}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
