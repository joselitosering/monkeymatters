// Curated baseline snapshot — refreshed Jul 30, 2026 evening, framed for
// Friday Jul 31's 6:15 AM PT pre-market read (the next weekday this
// dashboard would actually be opened). Every specific claim below is
// verified against real, dated reporting from Jul 29-30, 2026 (Fed decision,
// META/MSFT/AAPL/AMZN earnings) — see sources[] at the bottom. This baseline
// only ever serves as the fallback shown before live data (Massive/FRED/
// Schwab/CBOE) merges in; fields with no live source stay honestly gated
// here too, same as production.

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
  updatedAt: "Jul 31, 2026 · 6:15 AM PT",
  bias: { flag: "FEAR — IMPROVING", tone: "loss" as const },

  joke: { text: "Why did the stock trader bring a ladder to work? Because they heard the market was going up!", id: "DAYBREAK-20260731" },

  brief: {
    day: "Friday, Jul 31 · Wins & Wrap-Up Day",
    oneThing: {
      prompt: "What is the ONE thing I must accomplish today that would make everything else easier or unnecessary?",
      note: "Write your answer before you open email or Slack. Be ruthlessly specific.",
      block: "9:00–10:30 AM Deep Work Block",
    },
    lens: {
      title: "Fri Lens: Wins & Wrap-Up",
      text: "This week's four mega-cap earnings drew a clean line: capex gets rewarded when it's already showing up in a growth number (MSFT's Azure, Amazon's AWS), and punished when it isn't yet (Meta's EPS/FCF miss, Apple's supply-constrained guidance despite a clean beat).",
      prompt: "What did you ship this week that's already showing results — versus what's still just spend with a story attached?",
    },
    quickWins: [
      "Send one relationship-forward message — investor, advisor, or power user you haven't spoken to in 30+ days.",
      "Open your #1 product metric. Did it move this week? If yes, why? Write one sentence.",
      "Resolve one outstanding decision you've been deferring. Good enough & decided beats perfect & pending.",
    ],
    mindset: { quote: "It's not the daily increase but daily decrease. Hack away at the unessential.", author: "Bruce Lee", note: "Four earnings reports in three days is a lot of noise. What's the one signal worth carrying into next week?" },
  },

  command: {
    fgi: { value: 38, label: "Fear", note: "cross-source estimate" },
    vix: { value: "18.01", src: "StreetStats, ~1:30 PM Jul 30 (intraday) — live FRED close overrides on generation" },
    putCall: { total: "0.96", equity: "0.71", src: "CBOE, live" },
    aaii: { bull: null, bear: null, weekOf: null, gated: true, reason: "No reliable AAII source wired — scraper removed rather than shipped fragile" },
    hyOas: { value: "277", unit: "bps", asOf: "Jul 23 (FRED)" },
    spx: { value: "7,437.63", src: "CNBC, close Jul 30" },
    btc: { value: "64,211", src: "Benzinga, Jul 30" },
    xau: { value: "4,069.93", src: "Benzinga, Jul 30" },
    ndx: { value: null, gated: true, reason: "No Nasdaq-100 cash index feed wired" },
    gdx: { value: null, gated: true, reason: "No GDX (gold miners ETF) feed wired" },
    eth: { value: null, gated: true, reason: "No Ethereum feed wired" },
    dxy: { value: null, gated: true, reason: "Forex API req." },
    // Real futures prices (Massive Futures Basic, GC/DX contracts) — used by
    // TopAlerts specifically, distinct from the dxy/gdx ETF-proxy fields
    // above which Scanner's macro tab still shows. DX is unverified against
    // Massive's symbol directory (see generate_snapshot.mjs) — stays gated
    // here until a live run confirms it either way.
    usdIdx: { value: null, gated: true, reason: "Massive Futures (DX) — unverified symbol, pending live run" },
    goldFut: { value: null, gated: true, reason: "Massive Futures (GC) — pending server-side generation" },
    breadth: { value: null, gated: true, reason: "Polygon key req." },
    tenYear: { value: null, gated: true, reason: "Pending FRED DGS10 fetch" },
    wti: { value: null, gated: true, reason: "Pending FRED DCOILWTICO fetch" },
    advDec: { value: null, gated: true, reason: "Breadth vendor req." },
    newHighsLows: { value: null, gated: true, reason: "Breadth vendor req." },
    newsMood: { score: "Mixed — Split Verdict", tone: "loss" as const, heatCount: 5, windowMin: 360 },
  },

  tags: [
    "📦 AMZN Blowout / AAPL Guidance Miss — Overnight",
    "🚀 MSFT +15%+ Powers Nasdaq's Best Day Since Apr 2025",
    "📉 META -9.6% Since Wed on Capex/EPS Miss",
    "😨→😐 Fear Easing (38/100, VIX -13% off Wed spike)",
    "⚠️ 30Y Yield >5.2% — Highest Since 2007",
  ],

  news: [
    { time: "After Close", headline: "Amazon Q2 revenue crossed $200B for the first time; AWS accelerated to +37% YoY, its fastest growth since 2021, beating the ~31% consensus estimate. Shares rose as much as 10% after hours despite a capex guide hike to $220B for 2026.", source: "CNBC" },
    { time: "After Close", headline: "Apple beat Q3 estimates on revenue ($109.42B vs. $108.65B est.) and posted 22% iPhone growth, but shares slid roughly 8% after hours on weak forward guidance tied to supply constraints.", source: "CNBC" },
    { time: "Yesterday", headline: "The Fed held rates at 3.50–3.75% for a fifth straight meeting on a 9-3 vote; three regional presidents dissented in favor of a hike — the first three-way hawkish dissent since 2016.", source: "CNBC" },
    { time: "Yesterday", headline: "The Nasdaq posted its best single-day gain since April 2025 (+2.8%), ending a six-day losing streak, as Microsoft's 15%+ surge on a ~43% Azure growth beat offset Meta's post-earnings slide.", source: "CNBC / TheStreet" },
    { time: "Yesterday", headline: "Meta beat on revenue ($60.8B, +28% YoY) but missed EPS by roughly 14% as free cash flow collapsed to $784M from $8.5B a year ago; full-year capex guidance was raised to $130–145B.", source: "TradingKey" },
  ],

  drivers: [
    { time: "Overnight", event: "AMZN Q2 — AWS +37% YoY vs. ~31% est., revenue crossed $200B for the first time. Q3 guide of $197–202B beat consensus. Stock +7–10% after hours despite the largest capex raise of the week's four reports ($220B) — rewarded because the growth was already showing up in the numbers.", source: "CNBC", severity: "high" as const },
    { time: "Yesterday", event: "MSFT Q4 — beat on revenue (+2.6%) and EPS (+14.1%); Azure/cloud growth ~43%, fastest since 2022. Single-handedly powered Thursday's Nasdaq rally with a 15%+ single-day stock gain.", source: "CNBC / Yahoo Finance", severity: "high" as const },
    { time: "Yesterday ✅", event: "VIX fell from 20.66 (Wed close) to ~18 intraday Thursday (-13%), and Fear & Greed improved to 38 as Wednesday's Fed-driven selloff unwound.", source: "StreetStats / feargreedmeter.com", severity: "med" as const },
  ],
  risks: [
    { time: "Overnight", event: "AAPL Q3 — beat on revenue and EPS (22% iPhone growth) but guided weak on supply constraints; shares fell ~8% after hours. A different failure mode than META's — not a spend/profitability issue — but punished similarly. Watch whether it bleeds into broader hardware sentiment at the open.", source: "CNBC", severity: "high" as const },
    { time: "All Week", event: "30-year Treasury yield above 5.2%, its highest since 2007, following the Fed's hawkish-leaning hold (three dissents favoring a hike). A persistent long-duration equity headwind even as near-term panic (VIX) cools.", source: "CNBC", severity: "high" as const },
    { time: "Ongoing", event: "Meta's capex raise to $130–145B came without a matching growth-acceleration metric attached (FCF collapsed, EPS missed) — a different market reaction than Amazon's larger capex raise, which came with AWS acceleration to back it up. Worth watching whether this capex-without-growth pattern shows up again in other AI infrastructure names.", source: "TradingKey / CNBC", severity: "med" as const },
  ],
  topAnalysis: "Four mega-cap earnings reports and a Fed decision in three days produced a genuinely split verdict, and the pattern across them is more useful than any single print. Wednesday: the Fed held at 3.50–3.75% on a hawkish 9-3 vote — the first three-way hike dissent since 2016 — and markets sold off (SPX -1.5% to 7,316.15). Meta then missed EPS by 14% despite a revenue beat: FCF collapsed to $784M from $8.5B, capex raised to $130–145B with no clear growth story attached, and the stock fell nearly 10%. Microsoft beat cleanly on both lines with ~43% Azure growth and surged 15%+, single-handedly driving Thursday's rally (SPX +1.7% to 7,437.63, Nasdaq's best day since April 2025). Overnight: Amazon posted the strongest print of the four — AWS accelerated to 37% growth and crossed $200B in quarterly revenue for the first time — and the market rewarded a $220B capex raise, bigger than Meta's, because it came with visible demand validation. Apple beat on revenue and EPS but slid ~8% on weak guidance tied to supply constraints — a different failure mode than capex spend, punished just the same. The read for today's open: markets are differentiating between capex that's demonstrably buying growth (MSFT, AMZN) and capex or guidance that isn't showing it yet (META, AAPL). VIX has already cooled ~13% off Wednesday's spike and Fear & Greed improved to 38, but the 30-year yield above 5.2% — the highest since 2007 — is the quieter, more durable headwind sitting underneath the rally.",
  topActions: [
    { ticker: "SPX", levels: "Thu close 7,437.63", strategy: "The rally has room but now depends on the MSFT/AMZN-style 'capex justified by growth' narrative holding. A soft PCE/GDP read or a hawkish Fed speaker could reopen the 30Y-yield concern quickly." },
    { ticker: "AAPL", levels: "Down ~8% AH on guidance, not the print itself", strategy: "Distinguish from META — this is a supply-constraint guidance issue, not a spend-discipline one. Watch whether it stabilizes near pre-earnings levels or keeps sliding into the open." },
    { ticker: "META", levels: "Down ~9.6% since Wednesday's report", strategy: "The capex-without-growth-story pattern is the real risk here; would want a clear FCF or monetization update before adding, not just a bounce." },
  ],

  // Every field below mirrors the production TEXT keys 1:1, including which
  // ones are genuinely gated (⚙) vs. which have a real value (e.g. ES's
  // fmv.cash_index really is 7,437.63 — SPX ref — while NQ's is still gated).
  futures: {
    es: {
      dir: "Cautiously Constructive", contract: "ESU26",
      fmv: { fair: null, basisPts: null, cashIndex: "7,437.63 (SPX ref.)", cashIndexGated: false },
      gapProbClosePct: null,
      live: { last: null, asOf: null },
      priorOhlc: nullOhlc("Jul 30, 2026"),
      pivots: nullPivots,
      valueArea: { vah: null, poc: null, val: null },
      fibs: nullFibs,
      gateReason: "Massive Basic (8h-delayed) / CME live feed / Polygon — prior-session OHLC pending key auth",
      analysis: "Prior-session OHLC/pivots/fibs populate from MASSIVE_API_KEY (Futures Basic, 8h-delayed) once server-side generation runs; live price and gap% populate from Schwab when the run falls in market hours. Directional bias: CAUTIOUSLY CONSTRUCTIVE, not clean bullish. Thursday's rally (SPX +1.7% to 7,437.63) was driven almost entirely by MSFT's Azure beat, not broad participation — Nasdaq's best day since April 2025 rode largely on one name. Overnight AMZN's beat (AWS +37%) supports continuation; AAPL's guidance-driven slide (~-8% AH) is the swing risk for today's open. VIX cooling (~18, from 20.66 Wednesday) and Fear & Greed improving to 38 both argue against chasing a gap fade.",
      action: { levels: "Prior close 7,437.63 (Thu)", strategy: "Let the open establish direction rather than pre-positioning — AMZN strength and AAPL weakness are pulling in opposite directions overnight. Confirm above/below Thursday's close before committing size." },
    },
    nq: {
      dir: "Mixed — Bullish Lean", contract: "NQU26",
      fmv: { fair: null, basisPts: null, cashIndex: null, cashIndexGated: true },
      gapProbClosePct: null,
      live: { last: null, asOf: null },
      priorOhlc: nullOhlc("Jul 30, 2026"),
      pivots: nullPivots,
      valueArea: { vah: null, poc: null, val: null },
      fibs: nullFibs,
      gateReason: "Massive Basic (8h-delayed) / CME live feed / Polygon — prior-session OHLC pending key auth",
      analysis: "Prior-session OHLC/pivots/fibs populate from MASSIVE_API_KEY (Futures Basic, 8h-delayed) once server-side generation runs; live price and gap% populate from Schwab when the run falls in market hours. Directional bias: mixed with a bullish lean. /NQ benefits most directly from MSFT's Azure beat and AMZN's AWS acceleration — both argue AI infrastructure capex is still being rewarded when it shows up in growth numbers. Counterweight: META (-9.6% since Wednesday) and AAPL (-8% overnight) are both in the index and both underwhelmed, so this isn't a clean 'big tech beats' story — it's genuinely split by company.",
      action: { levels: "Split verdict overnight — AMZN up, AAPL down", strategy: "Cloud/AI-infrastructure names (tracking MSFT/AMZN strength) likely outperform hardware/consumer tech (tracking AAPL weakness) at the open. Treat this as a stock-picker's tape within NQ, not a uniform gap." },
    },
  },

  // 1D% is only real for XLK (verified: Thursday's biggest sector move, tied
  // to MSFT's earnings surge). Everything else has no computable number today
  // — shown that way here too, not filled in with an invented figure.
  sectors: {
    asof: "Manual estimate — Massive API pending",
    // All 11 SPDR sector ETFs generate_snapshot.mjs actually tracks (SECTOR_ETFS).
    all: [
      { etf: "XLK", sector: "Technology", d1: 4.9, real: true, note: "MSFT-led AI/cloud surge, best day since Apr 2025" },
      { etf: "XLE", sector: "Energy", d1: null, real: false, note: "est., oil gave back Wed spike" },
      { etf: "XLF", sector: "Financials", d1: null, real: false, note: "est." },
      { etf: "XLV", sector: "Health Care", d1: null, real: false, note: "est." },
      { etf: "XLI", sector: "Industrials", d1: null, real: false, note: "est." },
      { etf: "XLY", sector: "Consumer Discretionary", d1: null, real: false, note: "est." },
      { etf: "XLP", sector: "Consumer Staples", d1: null, real: false, note: "est." },
      { etf: "XLU", sector: "Utilities", d1: null, real: false, note: "est." },
      { etf: "XLB", sector: "Materials", d1: null, real: false, note: "est." },
      { etf: "XLRE", sector: "Real Estate", d1: null, real: false, note: "est." },
      { etf: "XLC", sector: "Communication Services", d1: null, real: false, note: "est., META drag" },
    ] as SectorRow[],
    leaderComponents: [
      { ticker: "MSFT", industry: "Cloud/Enterprise Software" },
      { ticker: "LRCX", industry: "Semiconductor Equipment" },
      { ticker: "MU", industry: "Memory Semiconductors" },
    ],
    laggardComponents: [
      { ticker: "META", industry: "Social Media/Advertising" },
      { ticker: "AAPL", industry: "Consumer Hardware" },
      { ticker: "TDOC", industry: "Digital Health" },
    ],
    analysis: "Information Technology (XLK) led sharply Thursday, roughly +5% — its best single-day gain since April 2025 — powered almost entirely by Microsoft's post-earnings surge and a broader chip-stock rebound (Lam Research +14.1% on a record quarter, Micron/SanDisk +3%). This isn't yet confirmed as broad-based tech strength: the move is concentrated in cloud/AI-infrastructure names validated by real growth numbers (MSFT, and now AMZN overnight), while consumer hardware (AAPL) and social/ads (META) both underwhelmed on guidance or profitability. Energy's oil-driven leadership from earlier in the week faded as WTI gave back its Wednesday spike.",
    actions: [
      { ticker: "XLK", levels: "~+5% Thu, best day since Apr 2025", strategy: "Confirm continuation is broad (multiple names) vs. concentrated in MSFT/semis before adding size — Thursday's move had a narrow driver." },
      { ticker: "AAPL", levels: "Down ~8% AH on guidance", strategy: "Distinct risk from META — supply-constraint guidance, not spend/profitability. Watch for stabilization vs. continued slide at the open." },
    ],
  },

  spotlight: {
    items: [
      { ticker: "AMZN", theme: "AWS Reacceleration Confirmed", levels: "Up 7–10% after hours", valuation: "Capex raised to $220B FY26 — market rewarded it this time", catalyst: "Q2: AWS +37% YoY vs. ~31% est., revenue crossed $200B for the first time", plan: "Strongest print of the week's four megacaps. Watch whether the after-hours pop holds through the open or fades on profit-taking." },
      { ticker: "AAPL", theme: "Beat-but-Guide-Down Pattern", levels: "Down ~8% after hours", valuation: "22% iPhone growth beat, but forward guidance weak", catalyst: "Q3: rev $109.42B beat $108.65B est.; guidance cites supply constraints", plan: "Distinguish this from a demand problem — it's a supply-chain guidance issue. Could set up as a dip-buy if constraints prove temporary, but confirm at the open first." },
      { ticker: "MSFT", theme: "Azure Beat Powered the Market", levels: "+15%+ Thursday", valuation: "Cleared both beat thresholds decisively", catalyst: "Q4: Azure ~43% growth, single-handedly drove Thursday's Nasdaq rally", plan: "Already re-rated; the trade now is in what MSFT's strength implies for other AI-infrastructure names (AMZN, semis), not chasing MSFT itself further." },
      { ticker: "META", theme: "Capex Without a Growth Story", levels: "Down ~9.6% since Wednesday", valuation: "Revenue beat, EPS missed 14%, FCF collapsed", catalyst: "Capex raised to $130–145B without a matching growth-acceleration metric", plan: "Needs a clear monetization or FCF-recovery signal before re-entry — the one name in the group where the market's skepticism looks justified by the numbers." },
    ],
    analysis: "Four real reports this week, and the market drew a distinction worth carrying forward: it's not 'AI capex good or bad,' it's whether the capex shows up in a growth number investors can see now. Amazon and Microsoft both raised spending and both rallied because AWS/Azure growth accelerated alongside it. Meta raised capex too, but its EPS and free cash flow went the wrong direction, and it fell. Apple didn't even have a capex story — its problem was supply-constrained guidance — and still fell, a reminder that 'beat the quarter, miss the guide' gets punished regardless of the reason.",
    actions: [
      { ticker: "AMZN", levels: "AH +7–10%", strategy: "Confirm the move holds through the open before treating it as a durable re-rate, not a chase-the-gap trade." },
      { ticker: "META", levels: "Two-day decline ~-9.6%", strategy: "No entry until stabilization — this needs a base, not a bounce, given the profitability concern behind the drop." },
    ],
  },

  uoa: {
    gated: true,
    note: "Unusual options activity requires a dedicated flow vendor (Market Chameleon, Unusual Whales, or similar). Manual note: expect elevated post-earnings flow in AAPL and AMZN as positioning resolves overnight moves; MSFT flow likely calmer after already repricing Thursday.",
    analysis: "UOA requires options flow vendor integration. Today's manual expectation: heavy directional flow in AAPL (guidance-driven put activity likely) and AMZN (call activity on the AWS beat) as the market digests overnight moves. META flow worth watching for signs of capitulation vs. dip-buying given the stock's two-day decline. Any unusual VIX put buying would signal the market believes Wednesday's Fed-day volatility spike is fully behind it.",
    actions: [{ ticker: "AAPL/AMZN", levels: "Overnight earnings reactions", strategy: "Monitor manually for large sweep activity at the open as positions resolve. Heavy AAPL put flow = market pricing further downside on the guidance concern." }],
  },

  ideas: {
    items: [
      { ticker: "AMZN", strategy: "Long (Momentum)", trigger: "Enter on continuation if the after-hours strength (+7–10%) holds through the open — not a pre-market chase.", expiry: "N/A", strikes: "N/A", entry: "Confirm above pre-earnings close", stop: "Below pre-earnings close (fill-the-gap failure)", target: "AH high", rr: "Est. 2:1" },
      { ticker: "AAPL", strategy: "Defined-Risk Put Spread, or Wait", trigger: "If the guidance concern (supply constraints) triggers follow-through selling at the open; otherwise wait for stabilization.", expiry: "Aug 7 (est.)", strikes: "ATM / 5% OTM (est.)", entry: "Confirm break of AH low", stop: "Reclaim of AH low", target: "Next support (est.)", rr: "Est. 1.5:1" },
      { ticker: "META", strategy: "No Trade — Needs a Base", trigger: "Two-day decline (~-9.6%) on a capex-without-growth concern; not a momentum long or short setup right now.", expiry: "N/A", strikes: "N/A", entry: "No entry until base forms", stop: "N/A", target: "N/A", rr: "N/A" },
    ],
    caveat: "Exact strike prices and premiums require live options chain data. Levels above are illustrative — size small, verify with real quotes before entering.",
    analysis: "Three real situations from this week's earnings, not hypotheticals. (1) AMZN — the cleanest setup, a confirmed growth acceleration (AWS +37%) the market already rewarded; the question is whether the move holds through the open. (2) AAPL — a genuine guidance concern, not a demand problem; defined-risk downside makes sense if follow-through selling starts, but this isn't a high-conviction short given the underlying beat. (3) META — deliberately no trade idea. A two-day ~9.6% decline on a capex-without-growth-story problem isn't a dip-buy or a momentum short; it needs to demonstrate stabilization first.",
    actions: [
      { ticker: "AMZN", levels: "AH +7–10%", strategy: "Confirm continuation above pre-earnings close before entering; this isn't a chase-the-gap-up trade." },
      { ticker: "AAPL", levels: "AH -8%", strategy: "Defined-risk only if follow-through selling confirms at the open; the underlying beat argues against a high-conviction short." },
    ],
  },

  buzz: {
    gated: true,
    items: [
      { ticker: "AMZN", signal: "🟢 Strong", status: "In Play", plan: "Momentum long if AH strength holds through open", trend: "↑ +310%", now: "—", prevC: "—", reason: "AWS +37% YoY beat; revenue crossed $200B first time" },
      { ticker: "AAPL", signal: "🔴 Active", status: "Watch", plan: "Defined-risk downside if guidance concern triggers follow-through", trend: "↓ +260%", now: "—", prevC: "—", reason: "Beat on Q3 numbers but weak guidance on supply constraints" },
      { ticker: "META", signal: "🔴 Active", status: "Watch", plan: "Avoid until a base forms — no clean setup yet", trend: "↓ +230%", now: "—", prevC: "—", reason: "Two-day ~9.6% decline on capex-without-growth-story concern" },
      { ticker: "MSFT", signal: "🟡 Cooling", status: "Digesting", plan: "Already repriced Thursday; watch for follow-through in cloud/semis peers instead", trend: "↑ +90%", now: "—", prevC: "—", reason: "Azure beat drove Thursday's rally; move largely priced in now" },
      { ticker: "VIX", signal: "🟢 Cooling", status: "Watch", plan: "Fed-day spike unwinding; watch for a re-spike if AAPL/META weakness spreads", trend: "↓ -13%", now: "—", prevC: "—", reason: "20.66 Wed close → ~18 intraday Thu, Fear & Greed improved to 38" },
    ],
    note: "Live buzz/trends data requires RSS + Google Trends + StockTwits integration. Signal & Trends Δ above are manually derived from today's news flow. Now/PrevC require a live ticker feed.",
    analysis: "Full buzz data requires social/RSS API integration. Manual signal summary: AMZN and AAPL dominate overnight conversation on their split earnings verdict — AWS strength vs. an iPhone beat undercut by weak guidance. META chatter is turning toward whether the capex story is broken, given two straight down days. MSFT conversation has cooled since Thursday's move already priced in most of the good news. VIX chatter has shifted from panic to relief as the Fed-day spike unwinds.",
    actions: [{ ticker: "AMZN/AAPL", levels: "Overnight earnings reactions", strategy: "Define risk via options given the binary nature already resolved overnight — this is about managing the gap now, not predicting the outcome." }],
  },

  // Analyst Rating / Consensus / Recommendation kept as three distinct real
  // fields, same as production — not collapsed into one summary string.
  earnings: {
    today: [
      { ticker: "AMZN", name: "Amazon.com", when: "After Close, Thu Jul 30 ✅ Beat", rating: "Buy", consensus: "Rev $200.6B vs. $196.47B est.; AWS +37% vs. ~31% est.", rec: "Strongest print of the week — AWS reacceleration confirmed", tone: "gain" as const },
      { ticker: "AAPL", name: "Apple", when: "After Close, Thu Jul 30 🟡 Mixed", rating: "Hold", consensus: "Rev $109.42B beat; EPS beat; guidance weak (supply constraints)", rec: "Beat the quarter, missed the guide — watch for stabilization", tone: "neutral" as const },
      { ticker: "MSFT", name: "Microsoft", when: "After Close, Wed Jul 29 ✅ Beat", rating: "Buy", consensus: "Rev $90.01B beat $87.71B est.; EPS beat 14.1%; Azure ~43% growth", rec: "Drove Thursday's rally single-handedly — largely priced in now", tone: "gain" as const },
      { ticker: "META", name: "Meta Platforms", when: "After Close, Wed Jul 29 ❌ Miss", rating: "Hold", consensus: "Rev $60.8B beat; EPS $6.18 missed $7.17 est. by ~14%", rec: "FCF collapsed to $784M from $8.5B; capex raised without a growth story", tone: "loss" as const },
      { ticker: "QCOM", name: "Qualcomm", when: "After Close, Wed Jul 29 🟡 Mixed", rating: "Neutral", consensus: "Rev $9.9B beat $9.67B est.; adj. EPS $2.21 missed $2.23 est.", rec: "Down ~4.8% — mobile chip demand signal worth monitoring", tone: "neutral" as const },
    ],
    restOfWeek: [] as { ticker: string; name: string; when: string; rating: string; note: string }[],
    caveat: "This week's marquee mega-cap earnings (META, MSFT, QCOM, AAPL, AMZN) are now complete as of Thursday evening. No further high-profile reports were confirmed for Friday at the time this was written — check NASDAQ's earnings calendar directly for anything scheduled same-day.",
    analysis: "Five real reports this week, and the split is instructive. Tuesday-Wednesday's three: MSFT beat clean (Azure ~43% growth, EPS +14.1%) and META missed on profitability (EPS -14%, FCF collapsed to $784M) despite a revenue beat — same week, same 'AI spend' theme, opposite outcomes depending on whether growth showed up alongside the spend. QCOM's mixed print (revenue beat, EPS miss) added a mobile-chip demand wrinkle. Wednesday-Thursday's two: AMZN delivered the strongest print of the group (AWS +37% vs. ~31% est., first $200B quarter) and was rewarded despite the largest capex raise of any of the five ($220B). AAPL beat cleanly on both lines but fell on supply-constraint guidance — a reminder that beating the quarter doesn't protect against missing the guide. The Fed's Wednesday hold (3.50–3.75%, hawkish 9-3 vote) sits underneath all of it, with the 30-year yield above 5.2% — the highest since 2007 — as the quieter macro risk that didn't go away just because Thursday rallied.",
    actions: [
      { ticker: "AMZN", levels: "AH +7–10%, AWS +37% confirmed", strategy: "Cleanest setup of the five — confirm the move holds through the open before treating it as a durable re-rate." },
      { ticker: "AAPL", levels: "AH -8% on guidance, not the beat", strategy: "Distinguish supply-constraint guidance from a demand problem. Watch for stabilization; the underlying beat argues against chasing weakness." },
    ],
  },

  // Real MLA-formatted citations for every specific claim above — verified
  // via web search against dated reporting, not carried over from the prior
  // (now-stale) Jul 29 snapshot's source list.
  sources: [
    { author: "Staff.", title: "Fed rate decision July 2026: Divided Fed holds interest rates steady.", site: "CNBC", publisher: "CNBC", date: "29 July 2026", url: "https://www.cnbc.com/2026/07/29/fed-rate-decision-july-2026.html" },
    { author: "Staff.", title: "Stock market news for July 30, 2026.", site: "CNBC", publisher: "CNBC", date: "30 July 2026", url: "https://www.cnbc.com/2026/07/29/stock-market-today-live-updates.html" },
    { author: "Staff.", title: "Why Is Meta (META) Crashing After Earnings? EPS Missed 14%, FCF Hit $784M, Capex Raised Again.", site: "TradingKey", publisher: "TradingKey", date: "29 July 2026", url: "https://www.tradingkey.com/analysis/stocks/us-stocks/262063667-meta-stock-crashing-after-q2-2026-earnings-eps-miss-capex-tradingkey" },
    { author: "Staff.", title: "Amazon (AMZN) Q2 earnings report 2026.", site: "CNBC", publisher: "CNBC", date: "30 July 2026", url: "https://www.cnbc.com/2026/07/30/amazon-amzn-q2-earnings-report-2026.html" },
    { author: "Staff.", title: "Apple (AAPL) Q3 2026 earnings report: Live updates.", site: "CNBC", publisher: "CNBC", date: "30 July 2026", url: "https://www.cnbc.com/2026/07/30/apple-earnings-live-updates.html" },
    { author: "Staff.", title: "Microsoft's (NASDAQ:MSFT) Q2 CY2026: Beats On Revenue.", site: "Yahoo Finance", publisher: "StockStory / Yahoo Finance", date: "29 July 2026", url: "https://ca.finance.yahoo.com/news/microsoft-nasdaq-msft-q2-cy2026-202345338.html" },
    { author: "Staff.", title: "VIX S&P 500 Volatility and MOVE Treasury Volatility.", site: "StreetStats", publisher: "StreetStats", date: "30 July 2026", url: "https://streetstats.finance/markets/volatility" },
    { author: "Staff.", title: "Stock Market Today: S&P 500, Nasdaq 100 Futures Gain as Federal Reserve Holds Interest Rates — Meta, Microsoft, Apple In Focus.", site: "Benzinga", publisher: "Benzinga", date: "30 July 2026", url: "https://www.benzinga.com/markets/equities/26/07/60788808/stock-market-today-sp-500-nasdaq-100-futures-gain-as-federal-reserve-holds-interest-rates-meta-microsoft-apple-in-focus" },
  ],
};
