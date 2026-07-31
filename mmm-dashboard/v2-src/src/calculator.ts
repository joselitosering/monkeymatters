// Bracket / position-size calculator — logic ported 1:1 from
// apex_futures_day_plan_bracket_calculator_baseline_locked.html (Joe's locked
// baseline). Every constant, threshold, and formula below is copied from that
// file rather than re-derived, so results match the standalone tool exactly.
// Kept as pure functions (no DOM) so it can be unit-checked and reused.

export type Sym = 'ES' | 'MES' | 'NQ' | 'MNQ' | 'MBT'
export type Term = 'contango' | 'flat' | 'backwardation'
export type Side = 'long' | 'short'
export type StopMethod = 'atr' | 'fixed' | 'structure'
export type TargetMode = 'r' | 'structure'
export type Mode = 'Trending' | 'Balance' | 'Scalp'

export const CONTRACTS: Record<Sym, { tick: number; tickVal: number; pointVal: number; microsPerStd: number; label: string }> = {
  ES:  { tick: 0.25, tickVal: 12.5, pointVal: 50, microsPerStd: 10, label: '/ES' },
  MES: { tick: 0.25, tickVal: 1.25, pointVal: 5,  microsPerStd: 10, label: '/MES' },
  NQ:  { tick: 0.25, tickVal: 5.00, pointVal: 20, microsPerStd: 10, label: '/NQ' },
  MNQ: { tick: 0.25, tickVal: 0.50, pointVal: 2,  microsPerStd: 10, label: '/MNQ' },
  MBT: { tick: 5,    tickVal: 0.50, pointVal: 1,  microsPerStd: 1,  label: '/MBT' },
}

export const STRESS_FLOORS_TICKS: Record<Sym, number> = { ES: 8, MES: 8, NQ: 12, MNQ: 12, MBT: 20 }

export const MICRO_SYMS: Sym[] = ['MES', 'MNQ', 'MBT']

export function roundToTick(px: number, tick: number): number {
  return Math.round(px / tick) * tick
}

/** VIX + term structure -> regime. Thresholds from the locked baseline. */
export function currentMode(vix: number, term: Term): Mode {
  if (term === 'backwardation' || vix >= 24) return 'Scalp'
  if (term === 'flat' || (vix >= 16 && vix < 24)) return 'Balance'
  return 'Trending'
}

export const MODE_COPY: Record<Mode, { note: string; strategy: string }> = {
  Trending: {
    note: 'Contango + VIX < 16 → trend setups; normal sizing.',
    strategy: 'Trending regime (Contango & VIX<16): favor OR retest with VWAP support; partial at 1R, runners to R1/VAH (shorts: S1/VAL).',
  },
  Balance: {
    note: 'Flat term or VIX 16–24 → balance: smaller size; fade VAH/VAL → POC/VWAP.',
    strategy: 'Range / Balance (Flat term or VIX 16–24): fade VAH/VAL back to POC/VWAP with smaller size; avoid chasing breaks.',
  },
  Scalp: {
    note: 'Backwardation or VIX ≥ 24 → micros only, wider stops, fewer trades.',
    strategy: 'Scalp regime (Backwardation or VIX ≥24): micros only, widen to 0.8–1.0×ATR; take VWAP/POC as primary targets; reduce frequency.',
  },
}

/**
 * Internals -> risk multiplier. VIX baseline factor, TRIN/TICK directional
 * adjustments, term-structure adjustment, clamped 0.25x–1.25x. Copied
 * verbatim from the baseline's internalsMultiplier().
 */
export function internalsMultiplier(vix: number, trin: number, tick: number, term: Term, dir: Side): number {
  let vixF = 1.0
  if (vix >= 16 && vix < 24) vixF = 0.85
  else if (vix >= 24 && vix < 32) vixF = 0.65
  else if (vix >= 32) vixF = 0.50

  let trinAdj = 1.0
  if (dir === 'long') {
    if (trin > 1.2) trinAdj = 0.70
    else if (trin < 0.8) trinAdj = 1.10
  } else {
    if (trin < 0.8) trinAdj = 0.70
    else if (trin > 1.2) trinAdj = 1.10
  }

  let tickAdj = 1.0
  if (dir === 'long') {
    if (tick < -200) tickAdj = 0.85
    else if (tick > 200) tickAdj = 1.05
  } else {
    if (tick > 200) tickAdj = 0.85
    else if (tick < -200) tickAdj = 1.05
  }

  const termAdj = term === 'backwardation' ? 0.70 : term === 'flat' ? 0.90 : 1.0

  const m = vixF * trinAdj * tickAdj * termAdj
  return Math.max(0.25, Math.min(1.25, m))
}

/** Standard floor-trader pivots — same formula the snapshot generator uses. */
export function computePivots(H: number, L: number, C: number) {
  const P = (H + L + C) / 3
  return {
    P,
    R1: 2 * P - L,
    S1: 2 * P - H,
    R2: P + (H - L),
    S2: P - (H - L),
    R3: H + 2 * (P - L),
    S3: L - 2 * (H - P),
  }
}

export interface CalcInput {
  sym: Sym
  side: Side
  entry: number
  atr: number
  stopMethod: StopMethod
  stopParam: number        // ATR multiple, or fixed points
  bufferTicks: number      // structure-stop buffer
  structLevelPx: number | null // resolved price of chosen structure level
  autoModeStops: boolean
  targetMode: TargetMode
  levels: Record<string, number | null> // PP/R1/S1/... /VWAP/ORH/ORL/VAH/VAL/POC
  vix: number
  trin: number
  tick: number
  term: Term
  dailyLoss: number
  riskFracPct: number      // e.g. 30 for 30%
  maxStd: number
}

export interface CalcResult {
  ok: boolean
  error?: string
  mode: Mode
  multiplier: number
  riskTrade: number
  stopPts: number
  riskPerCon: number
  stdCount: number
  microCount: number
  entry: number
  stopPx: number
  t1: number
  t2: number
  t1Label: string
  t2Label: string
  distStopTicks: number
  distT1Pts: number
  distT2Pts: number
  perTickAcct: number
  perPointAcct: number
  riskStopAcct: number
  pnlT1Acct: number
  pnlT2Acct: number
  tickSize: number
  tickVal: number
  pointVal: number
}

export function calculate(i: CalcInput): CalcResult {
  const cfg = CONTRACTS[i.sym]
  const isMicro = MICRO_SYMS.includes(i.sym)
  const mode = currentMode(i.vix, i.term)
  const m = internalsMultiplier(i.vix, i.trin, i.tick, i.term, i.side)
  const riskTrade = i.dailyLoss * (i.riskFracPct / 100) * m

  const base: CalcResult = {
    ok: false, mode, multiplier: m, riskTrade,
    stopPts: 0, riskPerCon: 0, stdCount: 0, microCount: 0,
    entry: i.entry, stopPx: 0, t1: 0, t2: 0, t1Label: '', t2Label: '',
    distStopTicks: 0, distT1Pts: 0, distT2Pts: 0,
    perTickAcct: 0, perPointAcct: 0, riskStopAcct: 0, pnlT1Acct: 0, pnlT2Acct: 0,
    tickSize: cfg.tick, tickVal: cfg.tickVal, pointVal: cfg.pointVal,
  }

  if (!i.entry || !Number.isFinite(i.entry)) return { ...base, error: 'Enter entry price' }

  // ── Stop distance ──
  let stopPts = 0
  if (i.stopMethod === 'atr') {
    let eff = i.stopParam
    if (i.autoModeStops) {
      eff = mode === 'Trending' ? 0.60 : mode === 'Balance' ? 0.75 : (i.vix >= 32 ? 1.00 : 0.95)
    }
    stopPts = i.atr * eff
  } else if (i.stopMethod === 'fixed') {
    stopPts = i.stopParam
  } else {
    if (i.structLevelPx == null || !Number.isFinite(i.structLevelPx)) {
      return { ...base, error: 'Choose a structure level with a real price' }
    }
    let buffTicksEff = i.bufferTicks
    if (i.autoModeStops && mode === 'Scalp') buffTicksEff = i.bufferTicks * 2
    const buff = buffTicksEff * cfg.tick
    stopPts = i.side === 'long'
      ? Math.max(i.entry - (i.structLevelPx - buff), cfg.tick)
      : Math.max((i.structLevelPx + buff) - i.entry, cfg.tick)
  }

  // Stress floors — minimum stop width in Scalp mode (ATR/structure only)
  if (i.autoModeStops && mode === 'Scalp' && (i.stopMethod === 'atr' || i.stopMethod === 'structure')) {
    const minPts = (STRESS_FLOORS_TICKS[i.sym] || 8) * cfg.tick
    if (stopPts < minPts) stopPts = minPts
  }

  stopPts = Math.max(cfg.tick, roundToTick(stopPts, cfg.tick))
  if (!Number.isFinite(stopPts) || stopPts <= 0) return { ...base, error: 'Stop distance resolves to zero — check ATR / stop inputs' }

  const riskPerCon = stopPts * cfg.pointVal

  // ── Sizing ──
  let stdCount = 0, microCount = 0
  if (isMicro) {
    microCount = Math.floor(riskTrade / riskPerCon)
    microCount = Math.min(microCount, i.maxStd * (cfg.microsPerStd || 10))
    if (!Number.isFinite(microCount) || microCount < 0) microCount = 0
  } else {
    stdCount = Math.floor(riskTrade / riskPerCon)
    stdCount = Math.min(stdCount, i.maxStd)
    if (!Number.isFinite(stdCount) || stdCount < 0) stdCount = 0
    microCount = stdCount * (cfg.microsPerStd || 10)
  }

  // ── Entry / stop / targets ──
  const dirSign = i.side === 'long' ? 1 : -1
  const stopPx = roundToTick(i.entry - dirSign * stopPts, cfg.tick)
  const Rpts = stopPts

  let t1: number, t2: number, t1Label = '1R', t2Label = '2R'
  if (i.targetMode === 'r') {
    t1 = roundToTick(i.entry + dirSign * Rpts, cfg.tick)
    t2 = roundToTick(i.entry + dirSign * 2 * Rpts, cfg.tick)
  } else {
    // Nearest two structure levels in the trade's direction
    const candidates: { label: string; px: number; dist: number }[] = []
    for (const [label, px] of Object.entries(i.levels)) {
      if (px == null || !Number.isFinite(px)) continue
      const dist = (px - i.entry) * dirSign
      if (dist > 0) candidates.push({ label, px: roundToTick(px, cfg.tick), dist })
    }
    candidates.sort((a, b) => a.dist - b.dist)
    if (candidates[0]) { t1 = candidates[0].px; t1Label = candidates[0].label }
    else { t1 = roundToTick(i.entry + dirSign * Rpts, cfg.tick); t1Label = '1R (no level)' }
    if (candidates[1]) { t2 = candidates[1].px; t2Label = candidates[1].label }
    else { t2 = roundToTick(i.entry + dirSign * 2 * Rpts, cfg.tick); t2Label = '2R (no level)' }
  }

  const nUnits = isMicro ? microCount : stdCount
  const distT1Pts = (t1 - i.entry) * dirSign
  const distT2Pts = (t2 - i.entry) * dirSign
  const perPointAcct = cfg.pointVal * nUnits

  return {
    ok: true, mode, multiplier: m, riskTrade,
    stopPts, riskPerCon, stdCount, microCount,
    entry: i.entry, stopPx, t1, t2, t1Label, t2Label,
    distStopTicks: stopPts / cfg.tick, distT1Pts, distT2Pts,
    perTickAcct: cfg.tickVal * nUnits,
    perPointAcct,
    riskStopAcct: -riskPerCon * nUnits,
    pnlT1Acct: perPointAcct * distT1Pts,
    pnlT2Acct: perPointAcct * distT2Pts,
    tickSize: cfg.tick, tickVal: cfg.tickVal, pointVal: cfg.pointVal,
  }
}
