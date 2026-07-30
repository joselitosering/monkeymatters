// Full real dataset as of Jul 29, 2026, 6:15 AM PT snapshot.
// Re-audited field-by-field against mmm_dashboard.html's actual TEXT/HTML
// snapshot after gaps were found. Nothing here is invented — fields that are
// genuinely only "est." or gated in production stay that way here too, with
// no fabricated numbers standing in for them.

// Explicit types for fields that start as `null` in the baseline but widen to
// a real number once live data merges in — without these, TS infers the
// literal type `null` from the object literal and rejects a later real value.
type OhlcBar = { o: number | null; h: number | null; l: number | null; c: number | null; sessionDate: string }
type Pivots = { r3: number | null; r2: number | null; r1: number | null; pp: number | null; s1: number | null; s2: number | null; s3: number | null }
type Fibs = { f38: number | null; f50: number | null; f62: number | null }
type SectorRow = { etf: string; sector: string; d1: number | null; real: boolean; note?: string }

const nullOhlc = (sessionDate: string): OhlcBar => ({ o: null, h: null, l: null, c: null, sessionDate })
const nullPivots: Pivots = { r3: null, r2: null, r1: null, pp: null, s1: null, s2: null, s3: null }
const nullFibs: Fibs = { f38: null, f50: null, f62: null }

export const snapshot = {
  updatedAt: "Jul 29, 2026 · 6:15 AM PT",
  bias: { flag: "FEAR", tone: "loss" as const },

  joke: { text: "Why did the stock trader bring a ladder to work? Because they heard the market was going up!", id: "DAYBREAK-20260729" },

  brief: {
    day: "Wednesday, Jul 29 · Product & Roadmap Day",
    oneThing: {
      prompt: "What is the ONE thing I must accomplish today that would make everything else easier or unnecessary?",
      note: "Write your answer before you open email or Slack. Be ruthlessly specific.",
      block: "9:00–10:30 AM Deep Work Block",
    },
    lens: {
      title: "Wed Lens: Product & Roadmap",
      text: "The AI earnings divergence this week tells a sharp story: companies with defensible product moats (Snowflake ↑ $500 PT) are being re-rated. Enterprises are throttling AI costs — \"spend at all costs\" era is over.",
      prompt: "Is the next roadmap item solving something customers urgently pay to fix — or just appreciate?",
    },
    quickWins: [
      "Send one relationship-forward message — investor, advisor, or power user you haven't spoken to in 30+ days.",
      "Open your #1 product metric. Did it move? If yes, why? Write one sentence.",
      "Resolve one outstanding decision you've been deferring. Good enough & decided beats perfect & pending.",
    ],
    mindset: { quote: "It's not the daily increase but daily decrease. Hack away at the unessential.", author: "Bruce Lee", note: "On Fed Day: max binary risk. Your edge is clarity. What can you remove from your plan?" },
  },

  command: {
    fgi: { value: 37, label: "Fear", note: "cross-source estimate" },
    vix: { value: "18.21", src: "FRED VIXCLS, close Jul 28" },
    putCall: { total: "0.96", equity: "0.71", src: "CBOE, live" },
    aaii: { spread: "-12.8", bull: 29.6, bear: 42.3, weekOf: "week ending Jul 22" },
    hyOas: { value: "277", unit: "bps", asOf: "Jul 23 (FRED)" },
    spx: { value: "7,437", src: "24/7 Wall St., pre-mkt" },
    btc: { value: "64,343", src: "CoinStats" },
    xau: { value: "4,087.70", src: "TheStreet, pre-mkt" },
    ndx: { value: null, gated: true, reason: "No Nasdaq-100 cash index feed wired" },
    gdx: { value: null, gated: true, reason: "No GDX (gold miners ETF) feed wired" },
    dxy: { value: null, gated: true, reason: "Forex API req." },
    breadth: { value: null, gated: true, reason: "Polygon key req." },
    tenYear: { value: null, gated: true, reason: "Pending FRED DGS10 fetch" },
    wti: { value: null, gated: true, reason: "Pending FRED DCOILWTICO fetch" },
    advDec: { value: null, gated: true, reason: "Breadth vendor req." },
    newHighsLows: { value: null, gated: true, reason: "Breadth vendor req." },
    newsMood: { score: "Bearish", tone: "loss" as const, heatCount: 5, windowMin: 360 },
  },

  tags: [
    "🔴 Fed Day — 2 PM ET Decision",
    "⚠️ Middle East Escalation",
    "📊 META + MSFT Earnings After Close",
    "🛢️ Oil +4.95% → $83.18",
    "😨 Fear Zone (38.6 / 100)",
  ],

  news: [
    { time: "Pre-mkt", headline: "Iran launches ballistic missiles at US forces — all intercepted. US & Saudi Arabia conduct strikes on Iran-backed groups in Iraq. Strait of Hormuz risk elevated. Oil +$4 to $83.18.", source: "TheStreet" },
    { time: "2:00 PM", headline: "Fed Rate Decision — market prices 31% probability of hike; consensus expects hold at 3.50–3.75%. Chair Warsh statement is the primary intraday catalyst.", source: "24/7 Wall St." },
    { time: "After Close", headline: "META Q2 Earnings — rev consensus $60.26B, EPS $7.22. 84% of prediction traders expect beat. Key watch: capex guidance $125–145B FY2026.", source: "24/7 Wall St." },
    { time: "Pre-mkt", headline: "Ford beat + raised guidance; GE HealthCare beat; Garmin beat + raised. SK hynix missed on semiconductor demand weakness.", source: "TheStreet" },
    { time: "Pre-mkt", headline: "AI spend discipline tightening — enterprises throttling model usage costs. Wells Fargo raises Snowflake to $500 PT as \"AI beneficiary.\"", source: "See It Market" },
  ],

  drivers: [
    { time: "2:00 PM", event: "Fed Rate Decision — hold expected at 3.50–3.75%. 31% hike probability priced. Warsh statement tone is key catalyst; hawkish surprise = SPX -1%+ scenario.", source: "Fed / Tickmill", severity: "high" as const },
    { time: "After Close", event: "META Q2 Earnings — $60.26B rev est, $7.22 EPS. 84% beat probability. AI monetization & Business AI commentary could re-rate the stock.", source: "24/7 Wall St.", severity: "high" as const },
    { time: "After Close", event: "MSFT Q2 Earnings — Azure AI growth the primary focus. Beat + strong guidance could gap /NQ significantly overnight.", source: "TheStreet", severity: "high" as const },
    { time: "Pre-mkt ✅", event: "Ford + GEHC + Garmin beat — positive earnings quality signal; raises & beats showing real demand in non-AI cyclicals.", source: "TheStreet", severity: "med" as const },
  ],
  risks: [
    { time: "All Day", event: "Iran-US military escalation — Strait of Hormuz closure risk. Any escalation headline could spike oil to $95–100+ and tank equities mid-session.", source: "TheStreet", severity: "high" as const },
    { time: "All Day", event: "Oil at $83.18 (+4.95%) — sustained above $80 refuels CPI inflation narrative and complicates Fed hold messaging. Brent at $88.49.", source: "TheStreet", severity: "high" as const },
    { time: "After Close", event: "META capex overhang — if FY2026 capex guidance raised above $145B, multiple compression risk. Stock already -9.95% YTD, P/E 22.", source: "24/7 Wall St.", severity: "med" as const },
    { time: "All Day", event: "Semiconductor weakness — SK hynix miss + AI spend discipline signals. Sector rotation away from high-multiple AI names; SOXX under pressure.", source: "TheStreet", severity: "med" as const },
  ],
  topAnalysis: "Fed Day + Binary Big Tech Earnings = maximum event risk today. Overall bias: BEARISH LEAN / WAIT — Fear & Greed at 38.6, oil spike (+4.95%), geopolitical headline risk all point to defensive posture pre-2 PM. The one bull case: META/MSFT beat with disciplined capex could gap markets higher overnight. Key levels: SPX 7,437 pre-mkt. Watch for 7,400 support (breakdown trigger) and 7,460 resistance (Fed-day breakout). Avoid adding size before 2 PM ET announcement.",
  topActions: [
    { ticker: "SPX", levels: "Range 7,400–7,460 (est.)", strategy: "Reduce size; wait for 2 PM Fed clarity. Post-announcement: breach 7,460 = add long; break 7,400 = short bias." },
    { ticker: "META", levels: "Support ~$520 est.; hist. ±1.48% post-beat avg", strategy: "Small straddle or ratio spread before 3:30 PM close. 84% beat probability; watch capex tone for re-rate signal." },
    { ticker: "XLE/XOM", levels: "Oil at $83.18; energy sector leading", strategy: "Geopolitical momentum play — Strait of Hormuz risk keeps energy bid. Trail stop if oil pulls back below $80." },
  ],

  // Every field below mirrors the production TEXT keys 1:1, including which
  // ones are genuinely gated (⚙) vs. which have a real value (e.g. ES's
  // fmv.cash_index really is 7,437 — SPX ref — while NQ's is still gated).
  futures: {
    es: {
      dir: "Bearish Lean", contract: "ESU26",
      fmv: { fair: null, basisPts: null, cashIndex: "7,437 (SPX ref.)", cashIndexGated: false },
      gapProbClosePct: null,
      live: { last: null, asOf: null },
      priorOhlc: nullOhlc("Jul 28, 2026"),
      pivots: nullPivots,
      valueArea: { vah: null, poc: null, val: null },
      fibs: nullFibs,
      gateReason: "Massive Basic (8h-delayed) / CME live feed / Polygon — prior-session OHLC pending key auth",
      analysis: "Prior-session OHLC/pivots/fibs populate from MASSIVE_API_KEY (Futures Basic, 8h-delayed) once server-side generation runs; live price and fair-value basis are not available on the free tier. Directional bias based on available signals: BEARISH LEAN. Rationale: S&P pre-mkt -0.13%, oil +4.95% (inflation risk), Fear & Greed 38.6, Fed rate decision at 2 PM with 31% hike probability, Middle East escalation. Primary catalysts: Fed 2 PM ET, META/MSFT after close. Do not add /ES size before 2 PM decision.",
      action: { levels: "Pre-Fed: 7,400–7,460 est. range", strategy: "Flat or minimal size pre-2 PM. Breakout above 7,460 post-Fed = long. Breakdown below 7,400 = short trigger. Overnight gap risk HIGH (META+MSFT)." },
    },
    nq: {
      dir: "Bearish Lean", contract: "NQU26",
      fmv: { fair: null, basisPts: null, cashIndex: null, cashIndexGated: true },
      gapProbClosePct: null,
      live: { last: null, asOf: null },
      priorOhlc: nullOhlc("Jul 28, 2026"),
      pivots: nullPivots,
      valueArea: { vah: null, poc: null, val: null },
      fibs: nullFibs,
      gateReason: "Massive Basic (8h-delayed) / CME live feed / Polygon — prior-session OHLC pending key auth",
      analysis: "Prior-session OHLC/pivots/fibs populate from MASSIVE_API_KEY (Futures Basic, 8h-delayed) once server-side generation runs; live price and fair-value basis are not available on the free tier. Directional bias: BEARISH LEAN with HIGH overnight binary risk. MSFT + META both report after close — /NQ could gap significantly in either direction overnight. AI capex commentary from both companies is the primary NQ driver. Consider reducing overnight /NQ exposure or using options for defined risk.",
      action: { levels: "Overnight gap risk HIGH", strategy: "Reduce overnight exposure before 3:30 PM. Use options straddle for defined risk on MSFT/META binary events. MASSIVE_API_KEY needed for exact prior-session technical levels." },
    },
  },

  // 1D% is only real for XLE (tied to the actual oil move). Everything else
  // in production is a literal "est." placeholder with no computable number —
  // shown that way here too, not filled in with an invented figure.
  sectors: {
    asof: "Manual estimate — Massive API pending",
    // All 11 SPDR sector ETFs generate_snapshot.mjs actually tracks (SECTOR_ETFS).
    // Only XLE has a real computed 1D% today; every other sector is honestly
    // marked "est." — no fabricated percentages standing in for the rest.
    all: [
      { etf: "XLE", sector: "Energy", d1: 4.95, real: true, note: "oil spike" },
      { etf: "XLK", sector: "Technology", d1: null, real: false, note: "est., AI spend discipline" },
      { etf: "XLF", sector: "Financials", d1: null, real: false, note: "est." },
      { etf: "XLV", sector: "Health Care", d1: null, real: false, note: "est." },
      { etf: "XLI", sector: "Industrials", d1: null, real: false, note: "est." },
      { etf: "XLY", sector: "Consumer Discretionary", d1: null, real: false, note: "est." },
      { etf: "XLP", sector: "Consumer Staples", d1: null, real: false, note: "est." },
      { etf: "XLU", sector: "Utilities", d1: null, real: false, note: "est." },
      { etf: "XLB", sector: "Materials", d1: null, real: false, note: "est." },
      { etf: "XLRE", sector: "Real Estate", d1: null, real: false, note: "est." },
      { etf: "XLC", sector: "Communication Services", d1: null, real: false, note: "est." },
    ] as SectorRow[],
    leaderComponents: [
      { ticker: "XOM", industry: "Integrated Oil & Gas" },
      { ticker: "CVX", industry: "Integrated Oil & Gas" },
      { ticker: "COP", industry: "Oil & Gas E&P" },
    ],
    laggardComponents: [
      { ticker: "NVDA", industry: "AI Semiconductors" },
      { ticker: "AMD", industry: "Semiconductors" },
      { ticker: "INTC", industry: "Semiconductors" },
    ],
    analysis: "Full sector performance data requires MASSIVE_API_KEY (Stocks Basic, end-of-day — last close, not live). Manual signal today: Energy (XLE) leading sharply on Iran-US escalation driving oil +4.95% to $83.18. Technology (XLK) and Semiconductors lagging on AI spend discipline signals and SK hynix miss. Rotation pattern: defensive value (Energy, Financials) vs growth-tech compression. Watch if XLE momentum holds after oil pulls back.",
    actions: [
      { ticker: "XLE", levels: "Oil $83.18, Brent $88.49", strategy: "Geopolitical momentum — trail stop below $80 oil. Strait of Hormuz closure = sustained XLE bid." },
      { ticker: "NVDA", levels: "AI spend discipline headwind", strategy: "Hold off new long entries until AI capex tone from META/MSFT tonight clarifies demand outlook." },
    ],
  },

  spotlight: {
    items: [
      { ticker: "META", theme: "Earnings Binary + AI Monetization", levels: "~$520 support (est.)", valuation: "P/E 22 — discount to peers", catalyst: "Q2 Earnings AC — 84% beat prob", plan: "Straddle or small directional after Fed. Watch $125–145B capex guidance for tone." },
      { ticker: "MSFT", theme: "Azure AI Growth Binary", levels: "Requires live options chain", valuation: "Premium; Azure growth priced in", catalyst: "Q2 Earnings AC — Azure beat = NQ catalyst", plan: "Watch Azure revenue growth rate; strong beat could reverse tech weakness overnight." },
      { ticker: "SNOW", theme: "AI Beneficiary Re-rate", levels: "$500 PT (Wells Fargo)", valuation: "Growth premium; WF sees AI as tailwind", catalyst: "WF upgrade — game has changed for AI SaaS", plan: "Monitor for setup post-WF upgrade; not a day-trade (no near-term catalyst)." },
      { ticker: "XOM", theme: "Oil Spike / Geopolitical Play", levels: "MASSIVE_API_KEY req.", valuation: "Fair — oil price leverage", catalyst: "Iran escalation → Strait of Hormuz risk → oil bid", plan: "Momentum entry on continued oil strength. Define risk with stop below $80 oil." },
    ],
    analysis: "Four high-conviction themes today: (1) META/MSFT earnings binaries — define risk with options, not directional; (2) SNOW re-rate thesis — WF $500 PT suggests structural AI beneficiary re-rating is underway; (3) XOM/energy momentum — pure geopolitical play, duration uncertain; (4) Avoid adding semi exposure (NVDA/AMD) until post-earnings AI capex clarity tonight.",
    actions: [
      { ticker: "META", levels: "Straddle pre-close", strategy: "Small, defined-risk options position. 84% beat prob but capex surprise = two-way risk." },
      { ticker: "SNOW", levels: "$500 WF PT; watch for setup", strategy: "AI beneficiary — not a day trade. Monitor for technical entry on pullback." },
    ],
  },

  uoa: {
    gated: true,
    note: "Unusual options activity requires a dedicated flow vendor (Market Chameleon, Unusual Whales, or similar). Manual note: expect elevated call/put flow in META, MSFT, VIX today given Fed Day + binary earnings events.",
    analysis: "UOA requires options flow vendor integration. Today's manual expectation: heavy directional flow in META (earnings), MSFT (earnings), VIX (Fed Day), and XLE (oil spike). Any large UOA print in VIX calls would signal institutional hedge escalation — monitor manually if flow vendor not connected.",
    actions: [{ ticker: "META/MSFT", levels: "Earnings events AC", strategy: "Monitor manually for large sweep activity before 3:30 PM close. Unusual put flow = institutional hedge signal." }],
  },

  ideas: {
    items: [
      { ticker: "META", strategy: "Straddle (ATM)", trigger: "Enter before 3:30 PM close, ahead of the AC earnings binary — not on a price break.", expiry: "Jul 30", strikes: "ATM (est. ~$520)", entry: "≤$8–10 debit (est.)", stop: "Straddle debit", target: "Break-even ± the debit", rr: "Est. 1.5:1" },
      { ticker: "VIX", strategy: "Call Spread (Fed hedge)", trigger: "Enter pre-2 PM ET, ahead of the Fed decision — hedge, not a breakout trade.", expiry: "Jul 30", strikes: "18/22 (est.)", entry: "Market price", stop: "Full debit", target: "22 strike", rr: "Est. 2:1" },
      { ticker: "XLE", strategy: "Long (Momentum)", trigger: "Enter on continuation while oil holds above $80; escape below $80 oil, not a fixed equity stop.", expiry: "N/A", strikes: "ATM", entry: "Market open", stop: "Below $80 oil", target: "Oil continuation", rr: "2:1" },
    ],
    caveat: "Exact strike prices and premiums require live options chain data. Levels above are illustrative — size small, verify with real quotes before entering.",
    analysis: "Three ideas for today: (1) META straddle — binary event, 84% beat prob, but capex surprise creates two-way volatility; ATM straddle captures either direction. (2) VIX call spread — Fed Day hedge; if Warsh is more hawkish than expected, VIX could spike; cost-defined upside. (3) XLE long — oil geopolitical momentum; duration unclear so use tight stop. ALL ideas require live options chain verification before entry.",
    actions: [
      { ticker: "META", levels: "ATM straddle (est. $520)", strategy: "Enter before 3:30 PM. Max loss = debit paid. Monitor capex guidance commentary for direction signal." },
      { ticker: "VIX", levels: "18/22 call spread (est.)", strategy: "Fed hedge — enter pre-2 PM. Full debit risk only. Close if Warsh holds and markets rally post-Fed." },
    ],
  },

  buzz: {
    gated: true,
    items: [
      { ticker: "META", signal: "🔴 Strong", status: "In Play", plan: "Straddle pre-close; directional post-AC", trend: "↑ +320%", now: "—", prevC: "—", reason: "Q2 earnings AC; 84% beat prob; capex watch" },
      { ticker: "MSFT", signal: "🔴 Strong", status: "In Play", plan: "Watch Azure beat for NQ overnight gap", trend: "↑ +280%", now: "—", prevC: "—", reason: "Q2 earnings AC; Azure AI growth focus" },
      { ticker: "XOM", signal: "🟡 Active", status: "Watch", plan: "Momentum long if oil holds $80+", trend: "↑ +190%", now: "—", prevC: "—", reason: "Iran escalation → oil spike; energy sector lead" },
      { ticker: "VIX", signal: "🟡 Active", status: "Watch", plan: "Fed Day hedge via call spread", trend: "↑ +150%", now: "—", prevC: "—", reason: "Fed Day; 31% hike probability; geopolitical risk" },
      { ticker: "SNOW", signal: "🟢 Rising", status: "Setup", plan: "Monitor for technical entry post-upgrade", trend: "↑ +80%", now: "—", prevC: "—", reason: "Wells Fargo $500 PT raise; AI beneficiary thesis" },
    ],
    note: "Live buzz/trends data requires RSS + Google Trends + StockTwits integration. Signal & Trends Δ above are manually derived from today's news flow. Now/PrevC require live ticker feed.",
    analysis: "Full buzz data requires social/RSS API integration. Manual signal summary: META and MSFT dominate conversation today (earnings AC). XOM trending on oil/geopolitical spike. VIX chatter elevated on Fed Day uncertainty. SNOW gaining positive sentiment from WF upgrade. Avoid chasing SKHY — semiconductor miss is a negative signal for the sector.",
    actions: [{ ticker: "META/MSFT", levels: "After-close binaries", strategy: "Define risk via options. Do not hold large directional equity positions overnight without options hedge." }],
  },

  // Analyst Rating / Consensus / Recommendation kept as three distinct real
  // fields, same as production — not collapsed into one summary string.
  earnings: {
    today: [
      { ticker: "F", name: "Ford Motor", when: "Before Open ✅ Beat", rating: "Outperform", consensus: "Beat consensus; raised FY guidance", rec: "Positive — cyclical demand holding", tone: "gain" as const },
      { ticker: "GEHC", name: "GE HealthCare", when: "Before Open ✅ Beat", rating: "Outperform", consensus: "Exceeded earnings forecasts", rec: "Positive — healthcare resilience", tone: "gain" as const },
      { ticker: "GRMN", name: "Garmin", when: "Before Open ✅ Beat", rating: "Outperform", consensus: "Beat + raised full-year guidance", rec: "Positive — consumer tech demand", tone: "gain" as const },
      { ticker: "SKHY", name: "SK hynix", when: "Before Open ❌ Miss", rating: "Neutral", consensus: "Missed expectations", rec: "Caution — semiconductor demand signal", tone: "loss" as const },
      { ticker: "META", name: "Meta Platforms", when: "After Close 🟡", rating: "Buy", consensus: "Rev $60.26B / EPS $7.22 est.", rec: "84% prediction-mkt beat; watch capex $125–145B FY2026", tone: "neutral" as const },
      { ticker: "MSFT", name: "Microsoft", when: "After Close 🟡", rating: "Buy", consensus: "Azure AI growth focus", rec: "Key NQ overnight catalyst; strong beat = tech reversal signal", tone: "neutral" as const },
      { ticker: "QCOM", name: "Qualcomm", when: "After Close 🟡", rating: "Hold", consensus: "Mobile chip demand", rec: "Watch for mobile AI chip demand signals", tone: "neutral" as const },
    ],
    restOfWeek: [
      { ticker: "AMZN", name: "Amazon", when: "Thu Jul 31 AC est.", rating: "Buy", note: "AWS AI growth + ads — key beat validates cloud AI spend thesis" },
      { ticker: "AAPL", name: "Apple", when: "Thu Jul 31 AC est.", rating: "Buy", note: "iPhone + services — services revenue growth and AI feature adoption" },
    ],
    caveat: "Full rest-of-week calendar requires NASDAQ earnings API. Dates above are estimates — verify with official calendar.",
    analysis: "Fed Day + Big Tech Earnings = dual binary risk. This morning: F, GEHC, GRMN all beat — healthy sign for non-AI cyclicals. SKHY miss is a semiconductor demand warning. Tonight: META ($60.26B rev est, 84% beat prob) and MSFT (Azure AI) are the primary catalysts. Capex guidance from META ($125–145B FY2026) is the key variable — raised guidance = multiple compression risk despite beat; in-line or lower = re-rate. QCOM adds mobile chip demand signal.",
    actions: [
      { ticker: "META", levels: "$60.26B rev / $7.22 EPS est.", strategy: "Define risk options position before 3:30 PM. Monitor capex guidance & AI monetization commentary for direction signal." },
      { ticker: "MSFT", levels: "Azure growth rate key", strategy: "Watch Azure sequential acceleration — key signal for cloud AI spend validation. NQ overnight gap risk HIGH." },
    ],
  },

  // Exactly the 7 real MLA-formatted citations from production — no additions,
  // no omissions. Author/publisher/date preserved instead of collapsed to
  // title+site only.
  sources: [
    { author: "Staff.", title: "Stock Market Live July 29, 2026: S&P 500 (SPY) Slightly Higher as Markets Wait on the Fed.", site: "24/7 Wall St.", publisher: "24/7 Wall St.", date: "29 July 2026", url: "https://247wallst.com/investing/2026/07/29/stock-market-live-july-29-2026-sp-500-spy-slightly-higher-as-markets-wait-on-the-fed/" },
    { author: "Staff.", title: "Stock Market Today (July 29, 2026): Dow Tumbles 800 Points Ahead of Fed Decision, Big Tech Earnings.", site: "TheStreet", publisher: "TheStreet", date: "29 July 2026", url: "https://www.thestreet.com/stock-market-today/stock-market-today-dow-jones-sp-500-nasdaq-updates-july-29-2026stock-market-today-july-29-2026" },
    { author: "Staff.", title: "Dow Jumps Over 500 Points As Oil Prices Fall: Greed Index Remains In Fear Zone.", site: "Benzinga", publisher: "Benzinga", date: "29 July 2026", url: "https://www.benzinga.com/markets/market-summary/26/07/60750007/dow-jumps-over-500-points-as-oil-prices-fall-investor-sentiment-improves-greed-index-remains-in-fear-zone" },
    { author: "Staff.", title: "Live: Will Meta Crush Q2 Earnings Tonight After Market Close?", site: "24/7 Wall St.", publisher: "24/7 Wall St.", date: "29 July 2026", url: "https://247wallst.com/investing/2026/07/29/live-will-meta-crush-q2-earnings-tonight-after-market-close/" },
    { author: "Staff.", title: "Mild Macro Data Sets up AI Tech Earnings and a Busy August Corporate Event Stretch.", site: "See It Market", publisher: "See It Market", date: "29 July 2026", url: "https://www.seeitmarket.com/mild-macro-data-sets-up-ai-tech-earnings-and-a-busy-august-corporate-event-stretch/" },
    { author: "Staff.", title: "Venture Capital & Startup Funding Roundup, July 27, 2026.", site: "Tech Startups", publisher: "Tech Startups", date: "27 July 2026", url: "https://techstartups.com/2026/07/27/venture-capital-startup-funding-roundup-july-27-2026-b-capital-index-ventures-paradigm-point72-ventures-ribbit-capital-more/" },
    { author: "Staff.", title: "Daily Market Outlook, July 29, 2026.", site: "Tickmill", publisher: "Tickmill", date: "29 July 2026", url: "https://www.tickmill.com/blog/daily-market-outlook-july-29-2026" },
  ],
};
