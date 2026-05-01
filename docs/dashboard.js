/* ═══════════════════════════════════════════════════════════════
 *  USD/CNY Macro-Policy Divergence Tracker · Dashboard renderer
 *  Editorial / institutional design · v3.2.6
 * ═══════════════════════════════════════════════════════════════ */

/** Single source for top bar + cache-bust alignment (footer & script tag in index.html). */
const TRACKER_VERSION = "3.2.6";

/* ─────────────────────────────────────────────────────────────
 *  I18N Engine + Dictionaries
 * ───────────────────────────────────────────────────────────── */
const I18N = {
  en: {
    "loader.text":       "Loading market data…",
    "boot.error":        'Could not load data.json — run <code>python build.py</code> first.',

    "score.asof":        "As of",
    "score.composite":   "Composite Policy Pressure",

    "zone.low":          "Low",
    "zone.low.tag":      "Stable",
    "zone.moderate":     "Moderate",
    "zone.moderate.tag": "Manageable",
    "zone.elevated":     "Elevated",
    "zone.elevated.tag": "Pressure Building",
    "zone.high":         "High",
    "zone.high.tag":     "Stress",
    "zone.extreme":      "Extreme",
    "zone.extreme.tag":  "Crisis Watch",

    "scorebar.low":  "Low",
    "scorebar.mod":  "Mod",
    "scorebar.elev": "Elev",
    "scorebar.high": "High",
    "scorebar.extr": "Extr",

    "kpi.usdcny":       "USD/CNY Spot",
    "kpi.usdcnh":       "USD/CNH Offshore",
    "kpi.fix":          "PBOC Fix",
    "kpi.yields":       "US 2Y · CN 2Y",
    "kpi.carry":        "Raw Carry",
    "kpi.carrypct":     "Carry Pctile",
    "kpi.hedged":       "Hedged Carry (CIP-implied)",
    "kpi.mm":           "MM Spread (1Y)",
    "kpi.shibor":       "Shibor 1Y",
    "kpi.us1y":         "UST 1Y",
    "kpi.dxy":          "DXY (TWI)",
    "kpi.beta_spread":  "Reg β · Spread",
    "kpi.beta_dxy":     "Reg β · DXY",
    "kpi.r2":           "Reg R²",
    "kpi.alpha":        "α · CNY/DXY",
    "kpi.bias":         "Fixing Bias",

    "meta.onshore":     "Onshore",
    "meta.hongkong":    "Hong Kong",
    "meta.bjt":         "09:15 BJT",
    "meta.yields":      "yields",
    "meta.uscn2y":      "US − CN 2Y",
    "meta.vs252d":      "vs 252d",
    "meta.fred":        "FRED broad",
    "meta.afterdxy":    "after DXY",
    "meta.broadDollar": "broad-dollar",
    "meta.modelfit":    "model fit",
    "meta.fixadj":      "fix adj.",
    "meta.vsdxyadj":    "vs DXY-adj.",
    "meta.cipResid":    "raw − CIP basis",
    "meta.mm1y":        "UST1Y − Shibor1Y",
    "meta.cn1y":        "CN money market",
    "meta.us1y":        "US money market",

    "alert.cnh_unavailable": () =>
        `<strong>Data note —</strong> USD/CNH offshore feed unavailable in this build. ` +
        `Layer 03 market anchor falls back to onshore previous close, which may ` +
        `under-estimate true defence intensity.`,
    "alert.spot_eq_fix": () =>
        `<strong>Data note —</strong> USD/CNY spot is currently identical to PBOC fix — ` +
        `this build uses fixing as spot proxy because yfinance is unreachable on this ` +
        `network. Layer 03 fixing-bias signal will appear degenerate (≈ 0) until ` +
        `a true onshore-spot source is restored.`,
    "alert.carry_body": (carry) =>
        `<strong>Carry alert —</strong> US−CN 2Y spread = <strong>${carry}%</strong>. ` +
        `Significant carry-trade incentive active.`,
    "alert.fixbias_body": (pips, dir) =>
        `<strong>Fixing-bias alert —</strong> bias = <strong>${pips} pips</strong> · ${dir}.`,
    "alert.defending":   "PBOC defending CNY",
    "alert.weakness":    "PBOC permitting weakness",
    "alert.highpressure_body": (score) =>
        `<strong>High pressure —</strong> composite = <strong>${score}/100</strong>. ` +
        `Multi-layer stress convergence detected.`,

    "narrative.carry": (carry, p1y, p2y) => {
        const direction = carry > 0
            ? `borrowing CNY to invest in USD generates a nominal <strong>${carry.toFixed(2)}%</strong> annualised yield pickup`
            : `the differential favours holding CNY (<strong>${carry.toFixed(2)}%</strong>)`;
        const intensity = p1y > 90 ? "near a historical extreme"
                         : p1y > 75 ? "elevated relative to history"
                         : p1y > 50 ? "above its trailing-year median"
                         : p1y > 25 ? "below median"
                         : "near historical lows";
        return `<strong>Live narrative —</strong> US−CN 2Y spread is currently ` +
            `<strong>${carry.toFixed(2)}%</strong>: ${direction}. This sits at the ` +
            `<strong>${p1y.toFixed(0)}<sup>th</sup> percentile (1Y)</strong>${
                !isNaN(p2y) ? ` / <strong>${p2y.toFixed(0)}<sup>th</sup> percentile (2Y)</strong>` : ""
            }, ${intensity}. Even after adjusting for forward-hedging costs, the implied ` +
            `capital-outflow gravity remains in this percentile range — a structural pressure ` +
            `source against the PBOC defence line.`;
    },

    "chart.yields":     "Interest-Rate Differential — 2Y Tenor",
    "chart.carry":      "Carry Pressure & On-Offshore Gap",
    "chart.dxy":        "DXY — Broad Dollar Index",
    "chart.regression": "USD/CNY — Actual vs Multivariate Model",
    "chart.residual":   "Residual De-Noising",
    "chart.cip":        "CIP Deviation",
    "chart.trinity":    "The Policy Triangle",
    "chart.fixing":     "Fixing Bias — Raw vs DXY-Adjusted",
    "chart.composite":  "One Number, Three Forces",
    "chart.hedgedCarry":    "Carry Decomposition — Raw vs Hedged",
    "chart.hedgedCarrySub": "Hedged carry = raw carry minus CIP basis (forward-hedge cost proxy)",
    "chart.mmFunding":      "Money-Market Funding Layer — 1Y Tenor",
    "chart.mmFundingSub":   "Short-end funding rate differential (modern Libor-Shibor analog)",
    "chart.regBetas":       "Rolling OLS — β₁ & β₂",
    "chart.regBetasSub":    "252d window: USD/CNY ~ spread + DXY",
    "chart.regFit":         "Model fit & residual z-score",
    "chart.regFitSub":      "In-sample R² and rolling (ε−μ)/σ (not pseudo-OOS)",

    "roadmap.label":        "Roadmap",
    "roadmap.swap.title":   "Real swap points, forwards & NDF",
    "roadmap.swap.body":    "This build uses a <strong>CIP-implied hedged-carry proxy</strong> because public APIs do not expose onshore swap strips. The next upgrade is to layer in <strong>USD/CNY forward points</strong>, <strong>CNH forwards</strong>, <strong>NDF</strong> pricing, and <strong>multi-tenor</strong> (1M–2Y) hedged carry — onshore vs offshore — so Layer 1 reflects tradable economics, not only theoretical pressure.",
    "roadmap.reg.title":    "Model stability & alternatives",
    "roadmap.reg.body":     "Rolling coefficients and R² are a first diagnostic. Further work: richer controls, <strong>pseudo out-of-sample</strong> forecasts, and benchmarks vs <strong>ridge / VAR</strong> — published when the specification survives stability tests.",
    "roadmap.policy.title": "Policy toolkit monitor",
    "roadmap.policy.body":  "Fixing bias is one lever. A fuller panel would add <strong>CNH liquidity / Hibor</strong>, <strong>offshore bills</strong>, <strong>FX risk reserve</strong> changes, <strong>counter-cyclical factor</strong> usage, <strong>verbal guidance</strong>, <strong>state-bank spot flow</strong>, and the <strong>CNY–CNH spread</strong> as feeds land in the open pipeline.",

    "method.composite.label": "Composite methodology",
    "method.composite.title": "Weights, standardisation & the 75 line",
    "method.composite.p1": (a, b, c) =>
        `Each layer outputs a <strong>0–100</strong> score built from percentile ranks. The headline composite is ` +
        `<strong>${a}%</strong> × Layer-1 carry percentile + <strong>${b}%</strong> × Layer-2 mispricing score + ` +
        `<strong>${c}%</strong> × Layer-3 policy percentile. Values are pinned in <code>config.py</code> and echoed under ` +
        `<code>methodology</code> in <code>data.json</code>.`,
    "method.composite.p2": () =>
        "<strong>Standardisation.</strong> Layer 1: trailing percentile of raw carry vs history. Layer 2: average of " +
        "percentile ranks of CIP deviation and multivariate regression residual. Layer 3: percentile of DXY-adjusted fixing bias " +
        "(high = less defensive / more market-led softness).",
    "method.composite.p3": (h) =>
        `The <strong>High</strong> pressure colour band starts at <strong>${h}</strong> (75–90 on the sidebar). That line is a ` +
        `<em>reporting convention</em> linking the headline score to the zone legend — not a backtested crisis trigger.`,
    "method.composite.p4": (rw) =>
        `The multivariate OLS coefficients and R² use a <strong>${rw}</strong>-trading-day rolling window. The residual z-score uses the same span on the residual level: (ε − μ) / σ.`,

    "hist.eyebrow":         "Credibility · Historical stress lens",
    "hist.title":           "Episodes to read against the dashboard",
    "hist.lead":            "This is <strong>not</strong> a formal event-study: rebuilt public series are not point-in-time. " +
        "Use the table as a qualitative checklist — did composite, fixing bias, hedged-carry proxy, and residual <em>line up</em> ahead of known stress windows?",
    "hist.col.period":      "Window",
    "hist.col.context":     "Context",
    "hist.col.watch":       "What to check on this site",
    "hist.r2015.p": "2015",   "hist.r2015.c": "CNY reform + devaluation pressure",
    "hist.r2015.w": "Composite vs carry percentile; fixing bias turning defensive; residual volatility.",
    "hist.r2018.p": "2018",   "hist.r2018.c": "US–China trade war",
    "hist.r2018.w": "Policy score vs spreads; whether the mispricing layer leads spot after DXY is filtered.",
    "hist.r2022.p": "2022",   "hist.r2022.c": "Strong USD / Fed cycle",
    "hist.r2022.w": "DXY-orthogonalised residual — isolating China-specific stress vs broad dollar.",
    "hist.r2023.p": "2023",   "hist.r2023.c": "CNY near 7.30 defence narrative",
    "hist.r2023.w": "Sustained composite > 75 with negative fixing bias; hedged-carry proxy path.",
    "hist.r20245.p": "2024–25", "hist.r20245.c": "Managed defence / range phase",
    "hist.r20245.w": "Rolling β stability; residual z extremes; policy vs carry percentile divergence.",

    "axis.yield":       "Yield (%)",
    "axis.spread_bps":  "Spread (bps)",
    "axis.carry":       "Carry (%)",
    "axis.carry_pct":   "Carry (%)",
    "axis.cip_basis":   "CIP Basis (%)",
    "axis.yield_1y":    "1Y Yield (%)",
    "axis.mm_bps":      "MM Spread (bps)",
    "axis.cnh_cny":     "CNH − CNY",
    "axis.index":       "Index",
    "axis.usdcny":      "USD/CNY",
    "axis.residual":    "Residual",
    "axis.residual_cny":"Residual (CNY)",
    "axis.deviation":   "Deviation (CNY)",
    "axis.bias_pips":   "Bias (pips)",
    "axis.defense_60d": "Defense / 60d",
    "axis.pressure":    "Pressure",
    "axis.value":       "Value",
    "axis.betaCoef":    "β coefficients",
    "axis.r2short":     "R²",
    "axis.residZ":      "Residual z",

    "trace.us2y":       "US 2Y",
    "trace.cn2y":       "CN 2Y",
    "trace.spread":     "Spread (bps)",
    "trace.rawCarry":   "Raw Carry",
    "trace.hedgedCarry":"Hedged Carry (CIP-implied)",
    "trace.ust1y":      "UST 1Y",
    "trace.shibor1y":   "Shibor 1Y",
    "trace.mmSpread":   "MM Spread (bps)",
    "trace.ma60":       "60d MA",
    "trace.cnh_gap":    "CNH−CNY Gap",
    "trace.dxy":        "DXY (TWI)",
    "trace.actual":     "USD/CNY Actual",
    "trace.multiModel": "Multivariate model",
    "trace.cipFair":    "CIP fair value",
    "trace.residual":   "Residual",
    "trace.singleVar":  "Single-var (legacy)",
    "trace.multiDxy":   "Multivariate (DXY-adj.)",
    "trace.cipBasis":   "CIP basis",
    "trace.fix":        "PBOC Fix",
    "trace.onshore":    "USD/CNY (onshore)",
    "trace.offshore":   "USD/CNH (offshore)",
    "trace.dxyAdjPips": "DXY-adjusted (pips)",
    "trace.rawBias":    "Raw bias",
    "trace.m20":        "20d mean",
    "trace.m60":        "60d mean",
    "trace.defense":    "Defense intensity",
    "trace.scoreRaw":   "Score (raw)",
    "trace.score5d":    "Score (5d)",
    "trace.betaSpreadRoll": "β₁ · spread",
    "trace.betaDxyRoll":    "β₂ · DXY",
    "trace.r2Roll":         "R²",
    "trace.residZ":         "Residual z",

    "reg.beta_spread":  "β₁ · Spread",
    "reg.beta_dxy":     "β₂ · DXY",
    "reg.r2":           "R²",
    "reg.alpha":        "α · CNY/DXY",
    "reg.afterdxy":     "after DXY",
    "reg.per1pt":       "per 1pt DXY",
    "reg.modelfit":     "model fit",
    "reg.fixadj":       "fix adj.",

    "findings.title":   "Key Findings",
    "finding.01.carry": (carry, pct1, pct2) => {
        let s = `Raw carry stands at <strong>${carry}%</strong>`;
        if (pct1 != null) s += ` — the <strong>${pct1}<sup>th</sup> percentile</strong> over the trailing year`;
        if (pct2 != null) s += `, <strong>${pct2}<sup>th</sup> percentile</strong> over two years`;
        return s + ".";
    },
    "finding.01.spread_high": () =>
        "A spread above 2.5% historically corresponds with sustained CNY depreciation pressure absent active intervention.",
    "finding.01.spread_neg": () =>
        "Negative differential has flipped the trade — borrowing USD to invest in CNY now offers a positive nominal pickup.",
    "finding.01.hedged": () =>
        "Without forward quotes, hedged carry remains uncomputed; the residual hedged-carry signal is captured in Layer 02's CIP basis.",

    "finding.02.beta_dxy": (beta2, delta) =>
        `Multivariate fit yields β<sub>DXY</sub> = <strong>${beta2}</strong> — every 1-point rise in the broad dollar predicts ${delta} CNY of USD/CNY appreciation.`,
    "finding.02.r2": (r2) =>
        `Joint model (spread + DXY) explains <strong>${r2}%</strong> of USD/CNY variance over the 252-day window.`,
    "finding.02.multicol": () =>
        `β<sub>spread</sub> turning negative is a multicollinearity artefact: spread and DXY co-move, ` +
        `and DXY absorbs most of the explanatory power. Read the residual, not β<sub>spread</sub> in isolation.`,
    "finding.02.residual": (regRes, regResUni, shrunk) =>
        `Today's <strong>multivariate residual</strong> is ${regRes} CNY vs single-variable ${regResUni} CNY${
            shrunk ? " — DXY de-noising has shrunk the unexplained gap" : ""}.`,
    "finding.02.cip": (dir, dev) =>
        `CIP fair value sits ${dir} actual spot by <strong>${dev} CNY</strong> — a measure of cross-currency basis stress.`,
    "finding.02.cip.above": "above",
    "finding.02.cip.below": "below",

    "finding.03.alpha": (alpha, inRange) =>
        `Rolling CNY/DXY beta α = <strong>${alpha}</strong>${inRange ? " — squarely in the 0.3–0.5 textbook range" : ""}.`,
    "finding.03.bias": (adjPips, rawPips) =>
        `DXY-adjusted bias today: <strong>${adjPips} pips</strong> (raw: ${rawPips} pips). ` +
        `The adjustment isolates true policy intent from mechanical overnight DXY moves.`,
    "finding.03.bias_neg": () =>
        "Negative bias indicates the PBOC is setting a <strong>stronger</strong> CNY than DXY-adjusted expectation — active defence posture.",
    "finding.03.bias_pos": () =>
        "Positive bias indicates the PBOC is permitting <strong>weaker</strong> CNY than expectation — letting the market lead.",
    "finding.03.bias_zero": () =>
        "Bias near zero — no clear directional intent revealed today.",
    "finding.03.defense": (defi) =>
        `20-day defence intensity: <strong>${defi} pips</strong> of cumulative leaning against depreciation.`,

    "table.date":   "Date",
    "table.usdcny": "USD/CNY",
    "table.usdcnh": "USD/CNH",
    "table.fix":    "Fix",
    "table.us2y":   "US 2Y",
    "table.cn2y":   "CN 2Y",
    "table.dxy":    "DXY",
    "table.carry":  "Carry",
    "table.resid":  "Resid",
    "table.bias":   "Bias",
    "table.score":  "Score",

    "glossary.field":      "Field",
    "glossary.unit":       "Unit",
    "glossary.source":     "Source",
    "glossary.definition": "Definition",
    "glossary.code":       "Source Code",

    "builder.daily":    "Daily",
    "builder.weekly":   "Weekly (mean)",
    "builder.monthly":  "Monthly (mean)",
    "builder.empty":    "Select one or more series above",

    "coverage":         "Coverage",

    "cite.retrieved":   "Retrieved",
    "cite.generated":   "Generated",

    /* ── Static-HTML keys (mirror of zh dict for full symmetry, v3.0.1) ── */
    "html.loader":      "Loading market data…",
    "html.download":    "Download",
    "html.begin":       "Begin →",
    "html.contents":    "Contents",
    "html.papers":      "Related Research",
    "html.lineage":     "Methodology Lineage",
    "html.zones":       "Pressure Zones",
    "html.author.role": "Independent researcher · FX & macro",
    "html.author.bio":  "Open research tooling on USDCNY carry, CIP-implied hedging, and PBOC fixing signals.",

    "nav.gauge":        "Pressure Gauge",
    "nav.carry":        "Carry Feasibility",
    "nav.mispricing":   "Mispricing",
    "nav.policy":       "Policy Intent",
    "nav.composite":    "Composite Trend",
    "nav.method":       "Composite methodology",
    "nav.history":      "Historical stress lens",
    "nav.builder":      "Build a Chart",
    "nav.glossary":     "Glossary",
    "nav.data":         "Data & Export",

    "zone.Low":         "Low",
    "zone.Moderate":    "Moderate",
    "zone.Elevated":    "Elevated",
    "zone.High":        "High",
    "zone.Extreme":     "Extreme",

    "hero.overline":    "As of",
    "hero.display":     "Quantifying the battle between <em>carry-trade pressure</em> and <em>PBOC policy intent</em>.",
    "hero.lead":        "<span class=\"drop-cap\">A</span> three-layer pressure gauge for USD/CNY at the 2-year tenor — from the gross yield differential, through DXY-orthogonalised regression residuals, to the daily fixing's hidden defence posture. One number that tells you whether the line still holds.",

    "score.label":      "Composite Policy Pressure",
    "bar.Low":          "Low",
    "bar.Mod":          "Mod",
    "bar.Elev":         "Elev",
    "bar.High":         "High",
    "bar.Extr":         "Extr",
    "quality.label":    "Coverage",

    "ch01.eyebrow":     "Layer One · Carry Monitor",
    "ch01.title":       "Carry Monitor — From Gross Spread to Hedged P&L",
    "ch01.lead":        'The "water pressure" of carry-trade capital: how much can you earn borrowing CNY and lending USD? We track both the <strong>raw 2Y yield differential</strong> and a <strong>CIP-implied hedged carry proxy</strong> that strips out forward-point costs. When hedged carry is positive and rising, speculative outflow pressure is structurally building — regardless of what the spot rate does today.',
    "ch01.method.note": "Free APIs do not expose real swap-point quotes. We derive the hedging cost from Covered Interest Parity: the CIP basis measures how far the actual spot deviates from what arbitrage-free forwards imply. A <strong>positive</strong> hedged carry proxy means real arbitrage profit exists after hedging — historically rare and a sign of USD funding stress or capital-control friction.",

    "ch02.eyebrow":     "Layer Two · Mispricing",
    "ch02.title":       "De-Noising With the Broad Dollar",
    "ch02.lead":        "A pure spread-vs-spot regression confounds two drivers: Sino-US rate differentials and broad-dollar moves. If the spread widens while DXY rallies, a stable CNY is rational, not intervention. We upgrade to <strong>multivariate OLS</strong>, regressing USD/CNY on <em>both</em> spread and DXY. The residual then isolates China-specific factors.",
    "ch02.pullquote":   "Only after the broad-dollar noise is filtered out does the residual become a clean reading of risk-premium and policy-intervention dynamics.",

    "ch03.eyebrow":     "Layer Three · Policy Intent",
    "ch03.title":       "Decoding the Daily Fixing",
    "ch03.lead":        "Between Beijing 4:30 PM close and 9:15 AM fixing lies a full New York trading session. Overnight DXY moves print mechanical CNY changes that a naive model mistakes for intervention. We strip those out, then read what remains: the <strong>true defence posture</strong> of the central bank.",

    "method":           "Method",
    "method.def":       "Definition",
    "method.carry":     "Carry Decomposition",
    "method.multivar":  "Multivariate Specification",
    "method.dxyadj":    "DXY-Adjusted Bias",
    "find.title":       "Key Findings",

    "synth.eyebrow":    "Synthesis · Composite Trend",
    "synth.title":      "One Number, Three Forces",
    "synth.lead":       "A weighted blend of all three layers. Watch sustained crossings into the 75+ region — historically the moments when something gives.",

    "build.eyebrow":    "Explore · Build a Chart",
    "build.title":      "Roll Your Own View",
    "build.lead":       "Pick any combination of the underlying series. Rendered live in your browser — no server round-trip.",
    "build.freq":       "Frequency",
    "build.series":     "Series",
    "build.daily":      "Daily",
    "build.weekly":     "Weekly (mean)",
    "build.monthly":    "Monthly (mean)",

    "gloss.eyebrow":    "Reference · Variable Glossary",
    "gloss.title":      "Every Field, Sourced",
    "gloss.lead":       "Each computed field, its formula, source, and unit. Click to expand.",
    "gloss.summary":    "Full Variable Glossary",
    "gloss.count":      "(38 fields)",

    "data.eyebrow":     "Export · Data",
    "data.title":       "Recent Observations",
    "data.lead":        "Last 30 trading days · full series available below.",
    "data.csv":         "↓ Download CSV (full series)",
    "data.json":        "↓ Download data.json",
    "data.xlsx":        "↓ Download Excel (.xlsx)",
    "data.ipynb":       "↓ Replication Notebook (.ipynb)",

    "feat.title":       "Featured Research",
    "feat.sub":         "Companion papers and adjacent work. Replace these placeholders with your own publications.",
    "cite.label":       "How to Cite",
    "footer.gen":       "Generated",
    "footer.disclaimer":"For research purposes only — not investment advice.",

    "interp.scenario":  "Scenario",
    "interp.carry":     "Carry",
    "interp.bias":      "Bias",
    "interp.impl":      "Implication",
    "interp.maxT":      "Max Tension",
    "interp.highUp":    "High ↑",
    "interp.strongNeg": "Strongly Negative",
    "interp.maxTd":     "PBOC burning reserves to hold the line — watch for capitulation.",
    "interp.managed":   "Managed Decline",
    "interp.zero":      "≈ 0",
    "interp.managedd":  "PBOC permitting orderly weakness.",
    "interp.comfort":   "Comfortable",
    "interp.lowDown":   "Low ↓",
    "interp.comfortd":  "No policy dilemma.",
    "interp.strong":    "CNY Strong",
    "interp.negLow":    "Negative / Low",
    "interp.pos":       "Positive",
    "interp.strongd":   "PBOC resisting <em>appreciation</em>.",
  },

  zh: {
    "loader.text":       "正在加载市场数据……",
    "boot.error":        '无法加载 data.json — 请先运行 <code>python build.py</code>。',

    "score.asof":        "截至",
    "score.composite":   "综合政策压力",

    "zone.low":          "低",
    "zone.low.tag":      "稳定",
    "zone.moderate":     "温和",
    "zone.moderate.tag": "可控",
    "zone.elevated":     "偏高",
    "zone.elevated.tag": "压力积聚",
    "zone.high":         "高压",
    "zone.high.tag":     "承压",
    "zone.extreme":      "极端",
    "zone.extreme.tag":  "危机警戒",

    "scorebar.low":  "低",
    "scorebar.mod":  "温和",
    "scorebar.elev": "偏高",
    "scorebar.high": "高",
    "scorebar.extr": "极端",

    "kpi.usdcny":       "USD/CNY 即期",
    "kpi.usdcnh":       "USD/CNH 离岸",
    "kpi.fix":          "央行中间价",
    "kpi.yields":       "美 2Y · 中 2Y",
    "kpi.carry":        "名义套利",
    "kpi.carrypct":     "套利分位",
    "kpi.hedged":       "对冲后利差（CIP 推算）",
    "kpi.mm":           "1Y 货币市场利差",
    "kpi.shibor":       "Shibor 1Y",
    "kpi.us1y":         "美 1Y 国债",
    "kpi.dxy":          "DXY（贸易加权）",
    "kpi.beta_spread":  "β₁ · 利差",
    "kpi.beta_dxy":     "β₂ · DXY",
    "kpi.r2":           "R²",
    "kpi.alpha":        "α · CNY/DXY",
    "kpi.bias":         "中间价偏差",

    "meta.onshore":     "在岸",
    "meta.hongkong":    "香港",
    "meta.bjt":         "09:15 北京时间",
    "meta.yields":      "收益率",
    "meta.uscn2y":      "美−中 2Y",
    "meta.vs252d":      "过去 252 日",
    "meta.fred":        "FRED 广义",
    "meta.afterdxy":    "去 DXY 后",
    "meta.broadDollar": "broad-dollar",
    "meta.modelfit":    "模型拟合度",
    "meta.fixadj":      "中间价调整",
    "meta.vsdxyadj":    "vs DXY 调整",
    "meta.cipResid":    "毛利差 − CIP 基差",
    "meta.mm1y":        "UST1Y − Shibor1Y",
    "meta.cn1y":        "CN 货币市场",
    "meta.us1y":        "US 货币市场",

    "alert.cnh_unavailable": () =>
        `<strong>数据提示 —</strong> 本次构建中 USD/CNH 离岸报价不可用。` +
        `第三层市场锚点回落至在岸前收盘价，可能低估真实防御强度。`,
    "alert.spot_eq_fix": () =>
        `<strong>数据提示 —</strong> USD/CNY 即期与央行中间价完全一致 — ` +
        `本次构建因 yfinance 不可达而以中间价替代即期。第三层偏差信号将呈退化状态（≈ 0），` +
        `直至恢复真实在岸即期源。`,
    "alert.carry_body": (carry) =>
        `<strong>套利预警 —</strong> 美中 2Y 利差 = <strong>${carry}%</strong>，套利激励显著。`,
    "alert.fixbias_body": (pips, dir) =>
        `<strong>中间价偏差预警 —</strong> 偏差 = <strong>${pips} 基点</strong> · ${dir}。`,
    "alert.defending":   "央行防御人民币",
    "alert.weakness":    "央行容许走弱",
    "alert.highpressure_body": (score) =>
        `<strong>高压预警 —</strong> 综合分 = <strong>${score}/100</strong>，多层压力交汇。`,

    "narrative.carry": (carry, p1y, p2y) => {
        const direction = carry > 0
            ? `借入人民币投资美元可获名义年化 <strong>${carry.toFixed(2)}%</strong> 的收益差`
            : `利差倾向于持有人民币（<strong>${carry.toFixed(2)}%</strong>）`;
        const intensity = p1y > 90 ? "接近历史极值"
                         : p1y > 75 ? "相对历史偏高"
                         : p1y > 50 ? "高于过去一年中位数"
                         : p1y > 25 ? "低于中位数"
                         : "接近历史低位";
        return `<strong>实时叙述 —</strong> 美中 2Y 利差目前为 ` +
            `<strong>${carry.toFixed(2)}%</strong>：${direction}。该水平位于` +
            `<strong>过去 1 年第 ${p1y.toFixed(0)} 百分位</strong>${
                !isNaN(p2y) ? ` / <strong>过去 2 年第 ${p2y.toFixed(0)} 百分位</strong>` : ""
            }，${intensity}。即使扣除远期对冲成本，隐含的资本外流引力仍处于此分位区间` +
            ` —— 对央行防线构成结构性压力。`;
    },

    "chart.yields":     "利率差异 — 2 年期",
    "chart.carry":      "套利压力与在离岸价差",
    "chart.dxy":        "DXY — 美元广义指数",
    "chart.regression": "USD/CNY — 实际 vs 多变量模型",
    "chart.residual":   "残差去噪",
    "chart.cip":        "CIP 偏离",
    "chart.trinity":    "政策三角",
    "chart.fixing":     "中间价偏差 — 原始 vs DXY 调整",
    "chart.composite":  "一个数字，三重力量",
    "chart.hedgedCarry":    "套利分解 — 名义 vs 对冲后",
    "chart.hedgedCarrySub": "对冲后套利 = 名义套利 − CIP 基差（远期对冲成本代理）",
    "chart.mmFunding":      "货币市场资金层 — 1 年期",
    "chart.mmFundingSub":   "短端资金利率差异（现代版 Libor-Shibor 利差）",
    "chart.regBetas":       "滚动 OLS — β₁ 与 β₂",
    "chart.regBetasSub":    "252 个交易日窗口：USD/CNY ~ 利差 + DXY",
    "chart.regFit":         "模型拟合与残差 z 分数",
    "chart.regFitSub":      "样本内 R² 与滚动 (ε−μ)/σ（非样本外检验）",

    "roadmap.label":        "路线图",
    "roadmap.swap.title":   "真实掉期点、远期与 NDF",
    "roadmap.swap.body":    "当前版本因公开数据限制，使用 <strong>CIP 隐含对冲后套利代理</strong>。下一步拟接入 <strong>USD/CNY 远期点</strong>、<strong>CNH 远期</strong>、<strong>NDF</strong> 及 <strong>多期限（1M–2Y）</strong> 对冲收益，区分在岸与离岸，使第一层更贴近可交易的经济学含义。",
    "roadmap.reg.title":    "模型稳定性与替代设定",
    "roadmap.reg.body":     "滚动系数与 R² 是第一步诊断。后续可扩展控制变量、<strong>伪样本外</strong>预测，并与 <strong>岭回归 / VAR</strong> 等对照——仅在设定通过稳定性检验后对外固化。",
    "roadmap.policy.title": "政策工具箱监控",
    "roadmap.policy.body":  "中间价偏差只是工具之一。完整面板可纳入 <strong>CNH 流动性 / CNH Hibor</strong>、<strong>离岸央票</strong>、<strong>外汇风险准备金</strong>调整、<strong>逆周期因子</strong>信号、<strong>口头引导</strong>、<strong>大行即期行为</strong>与 <strong>CNY–CNH 价差</strong>，视数据入 pipeline 情况迭代。",

    "method.composite.label": "综合指数方法论",
    "method.composite.title": "权重、标准化与 75 分界线",
    "method.composite.p1": (a, b, c) =>
        `每一层先产出 <strong>0–100</strong> 的分位化得分。头条综合分 = ` +
        `<strong>${a}%</strong> × 第一层（利差套利分位）+ <strong>${b}%</strong> × 第二层（定价偏离分）+ ` +
        `<strong>${c}%</strong> × 第三层（经 DXY 调整的中间价政策分位）。权重写在 <code>config.py</code>，构建时写入 <code>data.json</code> 的 <code>methodology</code>。`,
    "method.composite.p2": () =>
        "<strong>标准化方式。</strong>第一层：名义利差的历史分位；第二层：CIP 偏离与多变量回归残差的分位平均；第三层：经 DXY 调整的中间价偏差分位（分值高 = 防御弱 / 更随市场走弱）。",
    "method.composite.p3": (h) =>
        `侧边栏「高压」色带从 <strong>${h}</strong> 起（75–90 区间）。该阈值是 <em>与色阶对齐的披露约定</em>，并非经严格回测的危机触发线。`,
    "method.composite.p4": (rw) =>
        `多变量 OLS 的系数与 R² 使用 <strong>${rw}</strong> 个交易日滚动窗口。残差 z 分数在同一窗口长度内对残差水平做标准化：(ε − μ) / σ。`,

    "hist.eyebrow":         "可信度 · 历史压力视角",
    "hist.title":           "可与仪表盘对照的压力片段",
    "hist.lead":            "本节 <strong>不是</strong> 正式事件研究或回测：公开重建序列难以做到完全时点一致。下表作为定性清单——在已知压力窗口前，综合分、中间价偏差、对冲后套利代理与残差是否<strong>共振</strong>？",
    "hist.col.period":      "时段",
    "hist.col.context":     "背景",
    "hist.col.watch":       "在本站重点看什么",
    "hist.r2015.p": "2015",   "hist.r2015.c": "汇改与贬值压力",
    "hist.r2015.w": "综合分 vs 利差分位；中间价偏防御；残差波动。",
    "hist.r2018.p": "2018",   "hist.r2018.c": "中美贸易摩擦",
    "hist.r2018.w": "政策分 vs 利差；剔除 DXY 后错定价层是否领先即期。",
    "hist.r2022.p": "2022",   "hist.r2022.c": "强势美元 / 美联储周期",
    "hist.r2022.w": "DXY 正交化残差——区分中国因素与美元 beta。",
    "hist.r2023.p": "2023",   "hist.r2023.c": "CNY 临近 7.30 的防守叙事",
    "hist.r2023.w": "综合分持续高于 75 且中间价偏负；对冲后套利代理路径。",
    "hist.r20245.p": "2024–25", "hist.r20245.c": "有管理浮动 / 区间阶段",
    "hist.r20245.w": "滚动 β 是否漂移；残差 z 极值；政策分位与套利分位是否背离。",

    "axis.yield":       "收益率 (%)",
    "axis.spread_bps":  "利差（基点）",
    "axis.carry":       "套利 (%)",
    "axis.carry_pct":   "套利 (%)",
    "axis.cip_basis":   "CIP 基差 (%)",
    "axis.yield_1y":    "1Y 收益率 (%)",
    "axis.mm_bps":      "MM 利差（基点）",
    "axis.cnh_cny":     "CNH − CNY",
    "axis.index":       "指数",
    "axis.usdcny":      "USD/CNY",
    "axis.residual":    "残差",
    "axis.residual_cny":"残差（CNY）",
    "axis.deviation":   "偏离（CNY）",
    "axis.bias_pips":   "偏差（基点）",
    "axis.defense_60d": "防御 / 60 日",
    "axis.pressure":    "压力",
    "axis.value":       "数值",
    "axis.betaCoef":    "β 系数",
    "axis.r2short":     "R²",
    "axis.residZ":      "残差 z",

    "trace.us2y":       "美 2Y",
    "trace.cn2y":       "中 2Y",
    "trace.spread":     "利差（基点）",
    "trace.rawCarry":   "名义套利",
    "trace.hedgedCarry":"对冲后套利（CIP 推算）",
    "trace.ust1y":      "美国 1Y 国债",
    "trace.shibor1y":   "Shibor 1Y",
    "trace.mmSpread":   "MM 利差（基点）",
    "trace.ma60":       "60 日均线",
    "trace.cnh_gap":    "CNH−CNY 价差",
    "trace.dxy":        "DXY（贸易加权）",
    "trace.actual":     "USD/CNY 实际",
    "trace.multiModel": "多变量模型",
    "trace.cipFair":    "CIP 公允值",
    "trace.residual":   "残差",
    "trace.singleVar":  "单变量（旧版）",
    "trace.multiDxy":   "多变量（DXY 调整）",
    "trace.cipBasis":   "CIP 基差",
    "trace.fix":        "央行中间价",
    "trace.onshore":    "USD/CNY（在岸）",
    "trace.offshore":   "USD/CNH（离岸）",
    "trace.dxyAdjPips": "DXY 调整偏差（基点）",
    "trace.rawBias":    "原始偏差",
    "trace.m20":        "20 日均值",
    "trace.m60":        "60 日均值",
    "trace.defense":    "防御强度",
    "trace.scoreRaw":   "分数（原始）",
    "trace.score5d":    "分数（5 日平滑）",
    "trace.betaSpreadRoll": "β₁ · 利差",
    "trace.betaDxyRoll":    "β₂ · DXY",
    "trace.r2Roll":         "R²",
    "trace.residZ":         "残差 z",

    "reg.beta_spread":  "β₁ · 利差",
    "reg.beta_dxy":     "β₂ · DXY",
    "reg.r2":           "R²",
    "reg.alpha":        "α · CNY/DXY",
    "reg.afterdxy":     "去 DXY 后",
    "reg.per1pt":       "每 1pt DXY",
    "reg.modelfit":     "模型拟合度",
    "reg.fixadj":       "中间价调整",

    "findings.title":   "关键发现",
    "finding.01.carry": (carry, pct1, pct2) => {
        let s = `名义套利为 <strong>${carry}%</strong>`;
        if (pct1 != null) s += ` — 位于过去一年<strong>第 ${pct1} 百分位</strong>`;
        if (pct2 != null) s += `，过去两年<strong>第 ${pct2} 百分位</strong>`;
        return s + "。";
    },
    "finding.01.spread_high": () =>
        "利差超过 2.5% 历史上对应持续的人民币贬值压力（除非央行主动干预）。",
    "finding.01.spread_neg": () =>
        "利差已反转 — 借入美元投资人民币可获正名义收益。",
    "finding.01.hedged": () =>
        "因缺乏远期报价，对冲后套利暂无法计算；残余对冲信号体现在第二层 CIP 基差中。",

    "finding.02.beta_dxy": (beta2, delta) =>
        `多变量拟合 β<sub>DXY</sub> = <strong>${beta2}</strong> — 广义美元每上升 1 点，预测 USD/CNY 升值 ${delta} CNY。`,
    "finding.02.r2": (r2) =>
        `联合模型（利差 + DXY）解释了 252 日窗口内 USD/CNY 方差的 <strong>${r2}%</strong>。`,
    "finding.02.multicol": () =>
        `β<sub>spread</sub> 转负属多重共线性产物：利差与 DXY 共动，DXY 吸收了大部分解释力。` +
        `应关注残差而非孤立的 β<sub>spread</sub>。`,
    "finding.02.residual": (regRes, regResUni, shrunk) =>
        `今日<strong>多变量残差</strong>为 ${regRes} CNY，对比单变量 ${regResUni} CNY${
            shrunk ? " — DXY 去噪缩小了未解释缺口" : ""}。`,
    "finding.02.cip": (dir, dev) =>
        `CIP 公允值${dir}实际即期 <strong>${dev} CNY</strong> — 衡量跨币种基差压力。`,
    "finding.02.cip.above": "高于",
    "finding.02.cip.below": "低于",

    "finding.03.alpha": (alpha, inRange) =>
        `滚动 CNY/DXY β α = <strong>${alpha}</strong>${inRange ? " — 正处于 0.3–0.5 的教科书区间" : ""}。`,
    "finding.03.bias": (adjPips, rawPips) =>
        `DXY 调整偏差：<strong>${adjPips} 基点</strong>（原始：${rawPips} 基点）。` +
        `调整可隔离真实政策意图与隔夜 DXY 机械变动。`,
    "finding.03.bias_neg": () =>
        "负偏差表明央行将人民币定价<strong>强于</strong> DXY 调整预期 — 积极防御姿态。",
    "finding.03.bias_pos": () =>
        "正偏差表明央行容许人民币<strong>弱于</strong>预期 — 顺应市场。",
    "finding.03.bias_zero": () =>
        "偏差接近零 — 今日无明确方向性意图。",
    "finding.03.defense": (defi) =>
        `20 日防御强度：<strong>${defi} 基点</strong>累计逆向贬值倾斜。`,

    "table.date":   "日期",
    "table.usdcny": "USD/CNY",
    "table.usdcnh": "USD/CNH",
    "table.fix":    "中间价",
    "table.us2y":   "美 2Y",
    "table.cn2y":   "中 2Y",
    "table.dxy":    "DXY",
    "table.carry":  "套利",
    "table.resid":  "残差",
    "table.bias":   "偏差",
    "table.score":  "分数",

    "glossary.field":      "字段",
    "glossary.unit":       "单位",
    "glossary.source":     "来源",
    "glossary.definition": "定义",
    "glossary.code":       "数据代码",

    "builder.daily":    "日频",
    "builder.weekly":   "周频（均值）",
    "builder.monthly":  "月频（均值）",
    "builder.empty":    "请在上方选择一个或多个系列",

    "coverage":         "覆盖率",

    "cite.retrieved":   "获取于",
    "cite.generated":   "生成于",

    "html.loader":      "正在加载市场数据……",
    "html.download":    "下载",
    "html.begin":       "开始 →",
    "html.contents":    "目录",
    "html.papers":      "相关研究",
    "html.lineage":     "方法论渊源",
    "html.zones":       "压力区间",
    "html.author.role": "独立研究者 · 外汇与宏观",
    "html.author.bio":  "开源研究工具：USD/CNY 套利、CIP 隐含对冲与中间价政策信号。",

    "nav.gauge":        "压力仪表盘",
    "nav.carry":        "套利可行性",
    "nav.mispricing":   "定价偏离",
    "nav.policy":       "政策意图",
    "nav.composite":    "综合趋势",
    "nav.method":       "综合指数方法论",
    "nav.history":      "历史压力参考",
    "nav.builder":      "自建图表",
    "nav.glossary":     "术语表",
    "nav.data":         "数据导出",

    "zone.Low":         "低",
    "zone.Moderate":    "温和",
    "zone.Elevated":    "偏高",
    "zone.High":        "高压",
    "zone.Extreme":     "极端",

    "hero.overline":    "截至",
    "score.label":      "综合政策压力",
    "bar.Low":          "低",
    "bar.Mod":          "温和",
    "bar.Elev":         "偏高",
    "bar.High":         "高",
    "bar.Extr":         "极端",
    "quality.label":    "覆盖率",

    "ch01.eyebrow":     "第一层 · 套利监控",
    "ch02.eyebrow":     "第二层 · 定价偏离",
    "ch03.eyebrow":     "第三层 · 政策意图",
    "method":           "方法论",
    "method.def":       "定义",
    "method.carry":     "套利分解",
    "method.multivar":  "多变量规格",
    "method.dxyadj":    "DXY 调整偏差",
    "find.title":       "关键发现",

    "synth.eyebrow":    "综合 · 复合趋势",
    "build.eyebrow":    "探索 · 自建图表",
    "build.freq":       "频率",
    "build.series":     "系列",
    "build.daily":      "日频",
    "build.weekly":     "周频（均值）",
    "build.monthly":    "月频（均值）",

    "gloss.eyebrow":    "参考 · 术语表",
    "gloss.summary":    "完整术语表",
    "gloss.count":      "（38 个字段）",

    "data.eyebrow":     "导出 · 数据",
    "data.title":       "近期观测数据",
    "data.lead":        "最近 30 个交易日 · 完整序列见下方。",
    "data.csv":         "↓ 下载 CSV（完整序列）",
    "data.json":        "↓ 下载 data.json",
    "data.xlsx":        "↓ 下载 Excel (.xlsx)",
    "data.ipynb":       "↓ 复制验证笔记本 (.ipynb)",

    "feat.title":       "研究精选",
    "feat.sub":         "伴随论文与相关工作。请将占位符替换为您自己的出版物。",
    "cite.label":       "引用方式",
    "footer.gen":       "生成于",
    "footer.disclaimer":"仅供研究使用——非投资建议。",

    "interp.scenario":  "情景",
    "interp.carry":     "套利",
    "interp.bias":      "偏差",
    "interp.impl":      "含义",
    "interp.maxT":      "最大张力",
    "interp.highUp":    "高 ↑",
    "interp.strongNeg": "强烈负值",
    "interp.maxTd":     "央行消耗外储坚守防线——警惕失守。",
    "interp.managed":   "有序贬值",
    "interp.zero":      "≈ 0",
    "interp.managedd":  "央行允许有序走弱。",
    "interp.comfort":   "舒适区",
    "interp.lowDown":   "低 ↓",
    "interp.comfortd":  "无政策两难。",
    "interp.strong":    "人民币走强",
    "interp.negLow":    "负值 / 低",
    "interp.pos":       "正值",
    "interp.strongd":   "央行抵制<em>升值</em>。",

    "hero.display":     "量化<em>套利压力</em>与<em>央行政策意图</em>之间的博弈。",
    "hero.lead":        "<span class=\"drop-cap\">一</span>个以 2 年期限为焦点的 USD/CNY 三层压力仪表盘——从毛利差，到 DXY 正交化回归残差，到每日中间价的隐性防御态势。一个数字告诉你：防线还守不守得住。",

    "ch01.title":       "套利监控 — 从毛利差到对冲后 P&L",
    "ch01.lead":        "套利资本的「水压」：借人民币、投美元，能赚多少？我们同时追踪<strong>名义 2 年期利差</strong>和<strong>CIP 隐含对冲后套利代理</strong>（扣除远期对冲成本）。当对冲后套利为正且趋势上行时，投机性资本外流压力正在结构性积聚——无论今天即期汇率怎么走。",
    "ch01.method.note": "免费 API 无法获取真实掉期点报价。我们通过抛补利率平价（CIP）反推对冲成本：CIP 基差衡量的是实际即期汇率偏离无套利远期隐含值的程度。对冲后套利代理为<strong>正值</strong>意味着扣除对冲成本后仍存在真实套利利润——历史上很少出现，通常预示美元融资压力或资本管制摩擦。",
    "ch02.title":       "用美元广义指数去噪",
    "ch02.lead":        "纯利差-汇率回归混淆了两个驱动因素：中美利差和美元广义走势。如果利差扩大的同时 DXY 也在上涨，人民币稳定其实是合理的——并非干预。因此升级为<strong>多变量 OLS</strong>，将 USD/CNY 对利差<em>和</em> DXY 同时回归。残差隔离了中国特有因素。",
    "ch02.pullquote":   "只有在过滤掉美元广义噪音之后，残差才成为风险溢价与政策干预动态的干净读数。",
    "ch03.title":       "解码每日中间价",
    "ch03.lead":        "北京下午 4:30 收盘到 9:15 中间价之间，隔了一整个纽约交易时段。隔夜 DXY 波动会打印出机械性的 CNY 变动——朴素模型会误判为干预。我们剥离这些，然后读取剩余部分：央行的<strong>真实防御态势</strong>。",
    "synth.title":      "一个数字，三重力量",
    "synth.lead":       "三层加权混合。关注持续突破 75+ 的时段——历史上这些往往是转折点。",
    "build.title":      "自定义视图",
    "build.lead":       "选择任意组合的底层序列，浏览器端实时渲染，无需服务器。",
    "gloss.title":      "每个字段，有据可查",
    "gloss.lead":       "每个计算字段的公式、来源和单位。点击展开。",
  },
};

let LANG = localStorage.getItem("tracker-lang") || "en";

function t(key, ...args) {
    const val = I18N[LANG]?.[key];
    if (typeof val === "function") return val(...args);
    if (val != null) return val;
    const fb = I18N.en?.[key];
    if (typeof fb === "function") return fb(...args);
    return fb ?? key;
}

function switchLang(lang) {
    LANG = lang;
    localStorage.setItem("tracker-lang", lang);
    document.querySelectorAll(".lang-toggle button[data-lang]").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.lang === lang);
    });
    applyStaticI18n();
    if (window.__data) renderAll(window.__data);
}

function applyStaticI18n() {
    document.querySelectorAll("[data-i18n]").forEach(el => {
        if (!el.dataset.i18nOrig) el.dataset.i18nOrig = el.textContent;
        el.textContent = LANG === "en" ? el.dataset.i18nOrig : t(el.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-html]").forEach(el => {
        if (!el.dataset.i18nOrigHtml) el.dataset.i18nOrigHtml = el.innerHTML;
        el.innerHTML = LANG === "en" ? el.dataset.i18nOrigHtml : t(el.dataset.i18nHtml);
    });
}

function renderCompositeMethodology(data) {
    const el = document.getElementById("composite-method-body");
    if (!el) return;
    const m = data.methodology || {};
    const pc = Math.round((Number(m.w_carry) || 0.35) * 100);
    const pm = Math.round((Number(m.w_mispr) || 0.30) * 100);
    const pf = Math.round((Number(m.w_fixing) || 0.35) * 100);
    const hi = m.high_threshold != null ? Number(m.high_threshold) : 75;
    const rw = m.reg_window_days != null ? Number(m.reg_window_days) : 252;
    el.innerHTML = [
        `<p>${t("method.composite.p1", pc, pm, pf)}</p>`,
        `<p>${t("method.composite.p2")}</p>`,
        `<p>${t("method.composite.p3", hi)}</p>`,
        `<p>${t("method.composite.p4", rw)}</p>`,
    ].join("");
}

function renderAll(data) {
    applyStaticI18n();
    renderTopbar(data);
    renderHero(data);
    renderScore(data.snapshot);
    renderKPIs(data.snapshot);
    renderQuality(data.quality);
    renderAlerts(data.snapshot, data.quality);
    renderCarryNarrative(data.snapshot);
    renderCharts(data.series);
    renderRegStats(data.snapshot);
    renderFindings(data.snapshot);
    renderGlossary();
    renderTable(data.series);
    renderDownload(data.series);
    renderBuilder(data.series);
    renderCompositeMethodology(data);
    renderCitation(data);
    renderChartTitles();
}

function renderChartTitles() {
    const map = {
        "chart-yields":           "chart.yields",
        "chart-carry":            "chart.carry",
        "chart-dxy":              "chart.dxy",
        "chart-regression":       "chart.regression",
        "chart-residual-compare": "chart.residual",
        "chart-cip":              "chart.cip",
        "chart-trinity":          "chart.trinity",
        "chart-fixing":           "chart.fixing",
        "chart-composite":        "chart.composite",
    };
    for (const [id, key] of Object.entries(map)) {
        const plotEl = document.getElementById(id);
        if (!plotEl) continue;
        const card = plotEl.closest(".chart-card");
        if (!card) continue;
        const head = card.querySelector(".chart-card-head");
        if (!head) continue;
        const titleEl = head.querySelector(".chart-card-title");
        if (titleEl?.dataset.i18n) continue;
        if (titleEl) titleEl.textContent = t(key);
        else head.textContent = t(key);
    }
}

/* ─────────────────────────────────────────────────────────────
 *  Constants
 * ───────────────────────────────────────────────────────────── */
const COLORS = {
    bull:   "#15803d",
    bear:   "#b91c1c",
    warn:   "#a16207",
    navy:   "#1e3a5f",
    ochre:  "#a16207",
    line1:  "#1e3a5f",
    line2:  "#a16207",
    line3:  "#7c2d12",
    line4:  "#14532d",
    grid:   "#e8e4dc",
    text:   "#0c0a09",
    muted:  "#57534e",
    bg:     "#ffffff",
    bgTint: "#f5f2ec",
};

const ZONES = [
    { lo: 0,  hi: 25,  color: "#22c55e", bg: "#dcfce7", key: "low",      label: "Low",      tag: "Stable" },
    { lo: 25, hi: 50,  color: "#65a30d", bg: "#ecfccb", key: "moderate", label: "Moderate", tag: "Manageable" },
    { lo: 50, hi: 75,  color: "#ca8a04", bg: "#fef3c7", key: "elevated", label: "Elevated", tag: "Pressure Building" },
    { lo: 75, hi: 90,  color: "#ea580c", bg: "#ffedd5", key: "high",     label: "High",     tag: "Stress" },
    { lo: 90, hi: 100, color: "#b91c1c", bg: "#fee2e2", key: "extreme",  label: "Extreme",  tag: "Crisis Watch" },
];

const LAYOUT_BASE = {
    paper_bgcolor: COLORS.bg,
    plot_bgcolor:  COLORS.bg,
    font: { family: "Inter, sans-serif", size: 11, color: COLORS.text },
    margin: { l: 50, r: 24, t: 16, b: 40 },
    xaxis: { gridcolor: COLORS.grid, linecolor: COLORS.grid, zerolinecolor: COLORS.grid,
             tickfont: { size: 10, color: COLORS.muted } },
    yaxis: { gridcolor: COLORS.grid, linecolor: COLORS.grid, zerolinecolor: COLORS.grid,
             tickfont: { size: 10, color: COLORS.muted } },
    legend: { orientation: "h", y: -0.18, font: { size: 10, color: COLORS.muted } },
    hovermode: "x unified",
    hoverlabel: { bgcolor: "#fff", bordercolor: COLORS.grid, font: { size: 11, family: "JetBrains Mono, monospace" } },
};
const PLOTLY_CONFIG = { responsive: true, displaylogo: false,
                        modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"] };

const GLOSSARY_DEFS = [
    ["us_2y",            "%",      "akshare bond_zh_us_rate", "US 2Y Treasury yield",            "bond_zh_us_rate|https://github.com/akfamily/akshare/wiki"],
    ["cn_2y",            "%",      "akshare bond_zh_us_rate", "China 2Y govt bond yield",        "bond_zh_us_rate|https://github.com/akfamily/akshare/wiki"],
    ["yield_spread",     "%",      "computed",                "us_2y − cn_2y",                   ""],
    ["usdcny",           "CNY",    "yfinance / PBOC proxy",   "Onshore USD/CNY spot",            "DEXCHUS|https://fred.stlouisfed.org/series/DEXCHUS"],
    ["usdcnh",           "CNY",    "yfinance",                "Offshore USD/CNH spot",           ""],
    ["pboc_fix",         "CNY",    "akshare currency_boc_sina","PBOC daily central parity",      "currency_boc_sina|https://github.com/akfamily/akshare/wiki"],
    ["dxy",              "index",  "FRED DTWEXBGS",           "Trade-weighted broad dollar index","DTWEXBGS|https://fred.stlouisfed.org/series/DTWEXBGS"],
    ["dxy_ret",          "ret",    "computed",                "DXY daily pct change",            ""],
    ["onoffshore_gap",   "CNY",    "computed",                "usdcnh − usdcny",                ""],
    ["raw_carry",        "%",      "computed",                "us_2y − cn_2y (Layer 01)",        ""],
    ["carry_ma20",       "%",      "computed",                "20d MA of raw_carry",             ""],
    ["carry_ma60",       "%",      "computed",                "60d MA of raw_carry",             ""],
    ["carry_ma120",      "%",      "computed",                "120d MA of raw_carry",            ""],
    ["carry_pct_rank",   "0–100",  "computed",                "Pctile vs trailing 252d",         ""],
    ["carry_pct_rank_2y","0–100",  "computed",                "Pctile vs trailing 504d",         ""],
    ["cip_fair_spot",    "CNY",    "computed",                "CIP-implied fair value",          ""],
    ["cip_deviation",    "CNY",    "computed",                "usdcny − cip_fair_spot",          ""],
    ["reg_predicted",    "CNY",    "OLS multivariate",        "α + β₁·spread + β₂·DXY",         ""],
    ["reg_residual",     "CNY",    "computed",                "actual − multivariate model",     ""],
    ["reg_predicted_uni","CNY",    "OLS univariate",          "Single-var (legacy)",             ""],
    ["reg_residual_uni", "CNY",    "computed",                "actual − univariate model",       ""],
    ["reg_beta_spread",  "coef",   "computed",                "β₁ in multivariate OLS",         ""],
    ["reg_beta_dxy",     "coef",   "computed",                "β₂ in multivariate OLS",         ""],
    ["reg_r2",           "0–1",    "computed",                "Multivariate model R²",           ""],
    ["reg_residual_z",   "z",      "computed",                "Rolling z-score of multivariate residual",""],
    ["mispricing_score", "0–100",  "computed",                "Avg pctile of CIP & regr residual",""],
    ["alpha_cny_dxy",    "coef",   "computed",                "Rolling β of CNY ret on DXY ret", ""],
    ["expected_fix",     "CNY",    "computed",                "DXY-adjusted expected fix",       ""],
    ["fixing_bias",      "CNY",    "computed",                "pboc_fix − expected_fix (Layer 03)",""],
    ["fixing_bias_raw",  "CNY",    "computed",                "pboc_fix − anchor (legacy)",      ""],
    ["bias_20d_mean",    "CNY",    "computed",                "20d avg fixing_bias",             ""],
    ["defense_intensity","CNY",    "computed",                "−rolling_mean(bias,20d)",         ""],
    ["composite_score",  "0–100",  "weighted blend",          "Final pressure reading",          ""],
    ["shibor_1y",        "%",      "akshare rate_interbank",  "Shibor 1Y interbank rate",        "rate_interbank|https://github.com/akfamily/akshare/wiki"],
    ["us_1y",            "%",      "FRED DGS1",              "US 1Y Treasury yield",            "DGS1|https://fred.stlouisfed.org/series/DGS1"],
    ["mm_spread",        "%",      "computed",                "us_1y − shibor_1y",               ""],
    ["hedged_carry_proxy","%",     "computed",                "raw_carry − cip_dev_pct",         ""],
    ["cip_dev_pct",      "%",      "computed",                "cip_deviation / spot × 100",      ""],
    ["policy_score",     "0–100",  "computed",                "Fixing-bias percentile",          ""],
];

let CURRENT_DATA = null;

/* ─────────────────────────────────────────────────────────────
 *  Boot
 * ───────────────────────────────────────────────────────────── */
async function boot() {
    let data;
    try {
        const resp = await fetch("data.json", { cache: "no-store" });
        if (!resp.ok) throw new Error("data.json fetch failed: " + resp.status);
        data = await resp.json();
        CURRENT_DATA = data;
        window.__data = data;
    } catch (e) {
        document.querySelector("#loader .loader-text").innerHTML = t("boot.error");
        return;
    }

    document.getElementById("loader").style.opacity = "0";
    setTimeout(() => document.getElementById("loader").style.display = "none", 300);

    document.querySelectorAll(".lang-toggle button[data-lang]").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.lang === LANG);
        btn.addEventListener("click", () => switchLang(btn.dataset.lang));
    });

    renderAll(data);
}

/* ─────────────────────────────────────────────────────────────
 *  Topbar + Hero
 * ───────────────────────────────────────────────────────────── */
function renderTopbar(d) {
    document.getElementById("topbar-date").textContent = d.snapshot.date;
    const verEl = document.getElementById("topbar-version");
    if (verEl) verEl.textContent = `2Y FOCUS · v${TRACKER_VERSION}`;
    const score = parseFloat(d.snapshot.composite_score);
    const zone  = zoneOf(score);
    document.getElementById("topbar-score").innerHTML =
        `<strong style="color:${zone.color}">${isNaN(score) ? "—" : score.toFixed(0)}</strong>
         <span style="color:var(--muted);margin-left:6px">${t("zone." + zone.key)}</span>`;
}

function renderHero(d) {
    const locale = LANG === "zh" ? "zh-CN" : "en-US";
    document.getElementById("hero-date").textContent =
        new Date(d.snapshot.date).toLocaleDateString(locale,
            { year: "numeric", month: "long", day: "numeric" });
}

/* ─────────────────────────────────────────────────────────────
 *  Composite Score (custom, non-Plotly)
 * ───────────────────────────────────────────────────────────── */
function zoneOf(score) {
    if (isNaN(score)) return ZONES[2];
    return ZONES.find(z => score >= z.lo && score < z.hi) || ZONES[ZONES.length - 1];
}

function renderScore(s) {
    const score = parseFloat(s.composite_score);
    const safe  = isNaN(score) ? 50 : score;
    const zone  = zoneOf(safe);

    const card = document.getElementById("score-card");
    card.style.setProperty("--score-color", zone.color);
    card.style.setProperty("--score-bg", zone.bg);

    document.getElementById("score-asof").textContent = `${t("score.asof")} ${s.date}`;
    document.getElementById("score-status").textContent = `${t("zone." + zone.key)} · ${t("zone." + zone.key + ".tag")}`;
    document.getElementById("score-bar-marker").style.left = `${safe}%`;

    const target = safe;
    const el = document.getElementById("score-value");
    let start = 0;
    const duration = 1100;
    const t0 = performance.now();
    function tick(now) {
        const p = Math.min(1, (now - t0) / duration);
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = (start + (target - start) * eased).toFixed(0);
        if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

/* ─────────────────────────────────────────────────────────────
 *  KPI Tiles
 * ───────────────────────────────────────────────────────────── */
function renderKPIs(s) {
    const carry = parseFloat(s.raw_carry);
    const bias  = parseFloat(s.fixing_bias);
    const carryCls = isNaN(carry) ? "" : carry > 2.5 ? "bear" : carry > 1 ? "warn" : "bull";
    const biasCls  = isNaN(bias)  ? "" : bias < -0.005 ? "bull" : bias > 0.005 ? "bear" : "";

    const isNA = (v) => !v || v === "N/A" || v === "nan" || v === "—";
    const tile = (label, value, cls = "", meta = "", codeBadge = "") => {
        if (isNA(value)) return null;
        const badge = codeBadge
            ? ` <code style="font-family:'JetBrains Mono',monospace;font-size:9px;background:var(--bg-tint);padding:1px 4px;border-radius:3px;color:var(--muted);margin-left:4px">${codeBadge}</code>`
            : "";
        return `
            <div class="kpi-tile">
                <div>
                    <div class="kpi-tile-label">${label}</div>
                    <div class="kpi-tile-value ${cls}">${value}</div>
                </div>
                <div class="kpi-tile-meta">
                    <span>${meta}${badge}</span>
                </div>
            </div>`;
    };

    const tiles = [
        tile(t("kpi.usdcny"),      s.usdcny,                          "",      t("meta.onshore"),    "DEXCHUS"),
        tile(t("kpi.usdcnh"),      s.usdcnh,                          "",      t("meta.hongkong")),
        tile(t("kpi.fix"),         s.pboc_fix,                        "",      t("meta.bjt")),
        tile(t("kpi.yields"),      `${s.us_2y}% · ${s.cn_2y}%`,       "",      t("meta.yields")),
        tile(t("kpi.carry"),       `${s.raw_carry}%`,                 carryCls, t("meta.uscn2y")),
        tile(t("kpi.carrypct"),    `${s.carry_pct_rank} / 100`,       "",      t("meta.vs252d")),
        tile(t("kpi.hedged"),      isNA(s.hedged_carry_proxy) ? "—" : `${s.hedged_carry_proxy}%`,
                                                                       hedgedCls(s.hedged_carry_proxy),
                                                                                t("meta.cipResid")),
        tile(t("kpi.mm"),          isNA(s.mm_spread) ? "—" : `${s.mm_spread}%`, "", t("meta.mm1y")),
        tile(t("kpi.shibor"),      isNA(s.shibor_1y) ? "—" : `${s.shibor_1y}%`, "", t("meta.cn1y")),
        tile(t("kpi.us1y"),        isNA(s.us_1y)     ? "—" : `${s.us_1y}%`,     "", t("meta.us1y"),    "DGS1"),
        tile(t("kpi.dxy"),         s.dxy,                             "",      t("meta.fred"),       "DTWEXBGS"),
        tile(t("kpi.beta_spread"), s.reg_beta_spread,                 "",      t("meta.afterdxy")),
        tile(t("kpi.beta_dxy"),    s.reg_beta_dxy,                    "",      t("meta.broadDollar")),
        tile(t("kpi.r2"),          isNA(s.reg_r2) ? "—" : `${(parseFloat(s.reg_r2)*100).toFixed(1)}%`, "", t("meta.modelfit")),
        tile(t("kpi.alpha"),       s.alpha_cny_dxy,                   "",      t("meta.fixadj")),
        tile(t("kpi.bias"),        biasInPips(s.fixing_bias),         biasCls, t("meta.vsdxyadj")),
    ].filter(Boolean);

    document.getElementById("kpi-panel").innerHTML = tiles.join("");
}

function biasInPips(v) {
    const x = parseFloat(v);
    if (isNaN(x)) return "—";
    return `${(x * 10000).toFixed(0)} pips`;
}

// v3.1 — class for hedged-carry tile colour
function hedgedCls(v) {
    const x = parseFloat(v);
    if (isNaN(x)) return "";
    return x > 4 ? "bear" : x > 1 ? "warn" : x < -1 ? "bull" : "";
}

/* ─────────────────────────────────────────────────────────────
 *  Quality Badges
 * ───────────────────────────────────────────────────────────── */
function renderQuality(q) {
    const labels = { cn_2y: "CN 2Y", us_2y: "US 2Y", usdcny: "USD/CNY",
                     usdcnh: "USD/CNH", pboc_fix: "Fix", dxy: "DXY" };
    const html = Object.entries(q).map(([k, v]) => {
        const cls = v > 0.8 ? "ok" : v > 0.3 ? "est" : "err";
        return `<span class="q-badge ${cls}">${labels[k] || k} ${(v*100).toFixed(0)}%</span>`;
    }).join("");
    document.getElementById("quality-badges").innerHTML = html;
}

/* ─────────────────────────────────────────────────────────────
 *  Alerts (data limitations + signals)
 * ───────────────────────────────────────────────────────────── */
function renderAlerts(s, q) {
    const wrap = document.getElementById("alerts");
    const alerts = [];

    if (q.usdcnh < 0.3) {
        alerts.push({ cls: "", html: t("alert.cnh_unavailable") });
    }
    if (q.usdcny > 0.8 && q.pboc_fix > 0.8) {
        const usdcny = parseFloat(s.usdcny), pboc = parseFloat(s.pboc_fix);
        if (!isNaN(usdcny) && !isNaN(pboc) && Math.abs(usdcny - pboc) < 0.001) {
            alerts.push({ cls: "", html: t("alert.spot_eq_fix") });
        }
    }

    const carry = parseFloat(s.raw_carry);
    if (!isNaN(carry) && carry > 2.5) {
        alerts.push({ cls: "bear", html: t("alert.carry_body", carry.toFixed(2)) });
    }
    const bias = parseFloat(s.fixing_bias);
    if (!isNaN(bias) && Math.abs(bias) * 10000 > 100) {
        const dir = bias < 0 ? t("alert.defending") : t("alert.weakness");
        alerts.push({ cls: bias < 0 ? "bull" : "bear",
            html: t("alert.fixbias_body", (bias*10000).toFixed(0), dir) });
    }
    const score = parseFloat(s.composite_score);
    if (!isNaN(score) && score > 75) {
        alerts.push({ cls: "bear", html: t("alert.highpressure_body", score.toFixed(0)) });
    }

    wrap.innerHTML = alerts.map(a => `<div class="banner ${a.cls}">${a.html}</div>`).join("");
}

/* ─────────────────────────────────────────────────────────────
 *  Carry Narrative
 * ───────────────────────────────────────────────────────────── */
function renderCarryNarrative(s) {
    const wrap = document.getElementById("carry-narrative");
    const carry = parseFloat(s.raw_carry);
    const p1y = parseFloat(s.carry_pct_rank);
    const p2y = parseFloat(s.carry_pct_rank_2y);
    if (isNaN(carry) || isNaN(p1y)) { wrap.style.display = "none"; return; }

    wrap.style.display = "";
    wrap.innerHTML = t("narrative.carry", carry, p1y, p2y);
}

/* ─────────────────────────────────────────────────────────────
 *  Charts
 * ───────────────────────────────────────────────────────────── */
function renderCharts(series) {
    const dates = series.map(r => r.date);
    const get = (col) => series.map(r => r[col]);

    /* Yields */
    Plotly.newPlot("chart-yields", [
        { x: dates, y: get("us_2y"), name: t("trace.us2y"), type: "scatter",
          line: { color: COLORS.line1, width: 1.8 }, xaxis: "x", yaxis: "y" },
        { x: dates, y: get("cn_2y"), name: t("trace.cn2y"), type: "scatter",
          line: { color: COLORS.line2, width: 1.8 }, xaxis: "x", yaxis: "y" },
        { x: dates,
          y: get("yield_spread").map(v => v == null ? null : v * 100),
          name: t("trace.spread"), type: "bar",
          marker: { color: get("yield_spread").map(v => v == null ? COLORS.muted : v > 0 ? COLORS.bear : COLORS.bull),
                    opacity: 0.6 },
          xaxis: "x2", yaxis: "y2" },
    ], {
        ...LAYOUT_BASE,
        grid: { rows: 2, columns: 1, pattern: "independent", roworder: "top to bottom" },
        xaxis:  { ...LAYOUT_BASE.xaxis, anchor: "y",  domain: [0, 1] },
        yaxis:  { ...LAYOUT_BASE.yaxis, domain: [0.42, 1], title: { text: t("axis.yield"), font: { size: 10 } } },
        xaxis2: { ...LAYOUT_BASE.xaxis, anchor: "y2", domain: [0, 1] },
        yaxis2: { ...LAYOUT_BASE.yaxis, domain: [0, 0.34], title: { text: t("axis.spread_bps"), font: { size: 10 } } },
        margin: { l: 60, r: 24, t: 16, b: 50 },
    }, PLOTLY_CONFIG);

    /* Carry pressure */
    Plotly.newPlot("chart-carry", [
        { x: dates, y: get("raw_carry"), name: t("trace.rawCarry"), type: "scatter",
          line: { color: COLORS.line1, width: 1.6 },
          fill: "tozeroy", fillcolor: "rgba(30,58,95,0.10)",
          xaxis: "x", yaxis: "y" },
        { x: dates, y: get("carry_ma60"), name: t("trace.ma60"), type: "scatter",
          line: { color: COLORS.line2, width: 1.2, dash: "dot" }, xaxis: "x", yaxis: "y" },
        { x: dates, y: get("onoffshore_gap"), name: t("trace.cnh_gap"), type: "scatter",
          line: { color: COLORS.warn, width: 1.4 },
          fill: "tozeroy", fillcolor: "rgba(161,98,7,0.10)",
          xaxis: "x2", yaxis: "y2" },
    ], {
        ...LAYOUT_BASE,
        grid: { rows: 2, columns: 1, pattern: "independent", roworder: "top to bottom" },
        xaxis:  { ...LAYOUT_BASE.xaxis, anchor: "y",  domain: [0, 1] },
        yaxis:  { ...LAYOUT_BASE.yaxis, domain: [0.42, 1], title: { text: t("axis.carry"), font: { size: 10 } } },
        xaxis2: { ...LAYOUT_BASE.xaxis, anchor: "y2", domain: [0, 1] },
        yaxis2: { ...LAYOUT_BASE.yaxis, domain: [0, 0.34], title: { text: t("axis.cnh_cny"), font: { size: 10 } } },
        margin: { l: 60, r: 24, t: 16, b: 50 },
    }, PLOTLY_CONFIG);

    /* Carry decomposition — raw vs hedged */
    const elDecomp = document.getElementById("chart-carry-decomp");
    const elMm = document.getElementById("chart-mm");
    if (elDecomp) {
    const cipBasis = get("cip_dev_pct");
    const hedgedCarry = get("hedged_carry_proxy");
    Plotly.newPlot("chart-carry-decomp", [
        { x: dates, y: get("raw_carry"), name: t("trace.rawCarry"), type: "scatter",
          line: { color: COLORS.line1, width: 1.8 },
          xaxis: "x", yaxis: "y" },
        { x: dates, y: hedgedCarry, name: t("trace.hedgedCarry"), type: "scatter",
          line: { color: COLORS.warn, width: 2.2 },
          fill: "tozeroy", fillcolor: "rgba(161,98,7,0.12)",
          xaxis: "x", yaxis: "y" },
        { x: dates, y: get("carry_ma60"), name: t("trace.ma60"), type: "scatter",
          line: { color: COLORS.muted, width: 1, dash: "dot" },
          xaxis: "x", yaxis: "y" },
        { x: dates, y: cipBasis, name: t("trace.cipBasis"), type: "bar",
          marker: { color: cipBasis.map(v => v == null ? COLORS.muted : v > 0 ? COLORS.bull : COLORS.bear),
                    opacity: 0.55 },
          xaxis: "x2", yaxis: "y2" },
    ], {
        ...LAYOUT_BASE,
        grid: { rows: 2, columns: 1, pattern: "independent", roworder: "top to bottom" },
        xaxis:  { ...LAYOUT_BASE.xaxis, anchor: "y",  domain: [0, 1] },
        yaxis:  { ...LAYOUT_BASE.yaxis, domain: [0.42, 1], title: { text: t("axis.carry_pct"), font: { size: 10 } } },
        xaxis2: { ...LAYOUT_BASE.xaxis, anchor: "y2", domain: [0, 1] },
        yaxis2: { ...LAYOUT_BASE.yaxis, domain: [0, 0.34], title: { text: t("axis.cip_basis"), font: { size: 10 } } },
        margin: { l: 60, r: 24, t: 16, b: 50 },
    }, PLOTLY_CONFIG);
    }

    /* Money-market funding layer — 1Y */
    if (elMm) {
    Plotly.newPlot("chart-mm", [
        { x: dates, y: get("us_1y"), name: t("trace.ust1y"), type: "scatter",
          line: { color: COLORS.line1, width: 1.8 },
          xaxis: "x", yaxis: "y" },
        { x: dates, y: get("shibor_1y"), name: t("trace.shibor1y"), type: "scatter",
          line: { color: COLORS.line2, width: 1.8 },
          xaxis: "x", yaxis: "y" },
        { x: dates,
          y: get("mm_spread").map(v => v == null ? null : v * 100),
          name: t("trace.mmSpread"), type: "bar",
          marker: { color: get("mm_spread").map(v => v == null ? COLORS.muted : v > 0 ? COLORS.bear : COLORS.bull),
                    opacity: 0.6 },
          xaxis: "x2", yaxis: "y2" },
    ], {
        ...LAYOUT_BASE,
        grid: { rows: 2, columns: 1, pattern: "independent", roworder: "top to bottom" },
        xaxis:  { ...LAYOUT_BASE.xaxis, anchor: "y",  domain: [0, 1] },
        yaxis:  { ...LAYOUT_BASE.yaxis, domain: [0.42, 1], title: { text: t("axis.yield_1y"), font: { size: 10 } } },
        xaxis2: { ...LAYOUT_BASE.xaxis, anchor: "y2", domain: [0, 1] },
        yaxis2: { ...LAYOUT_BASE.yaxis, domain: [0, 0.34], title: { text: t("axis.mm_bps"), font: { size: 10 } } },
        margin: { l: 60, r: 24, t: 16, b: 50 },
    }, PLOTLY_CONFIG);
    }

    /* DXY */
    Plotly.newPlot("chart-dxy", [
        { x: dates, y: get("dxy"), name: t("trace.dxy"), type: "scatter",
          line: { color: COLORS.line1, width: 1.8 },
          fill: "tozeroy", fillcolor: "rgba(30,58,95,0.06)" },
    ], {
        ...LAYOUT_BASE,
        yaxis: { ...LAYOUT_BASE.yaxis, title: { text: t("axis.index"), font: { size: 10 } } },
    }, PLOTLY_CONFIG);

    /* Regression */
    const residColors = get("reg_residual").map(v => v == null ? COLORS.muted : v > 0 ? COLORS.bear : COLORS.bull);
    Plotly.newPlot("chart-regression", [
        { x: dates, y: get("usdcny"),         name: t("trace.actual"),     type: "scatter",
          line: { color: COLORS.line2, width: 1.6 }, xaxis: "x", yaxis: "y" },
        { x: dates, y: get("reg_predicted"),  name: t("trace.multiModel"), type: "scatter",
          line: { color: COLORS.line1, width: 1.6, dash: "dash" }, xaxis: "x", yaxis: "y" },
        { x: dates, y: get("cip_fair_spot"),  name: t("trace.cipFair"),    type: "scatter",
          line: { color: COLORS.line3, width: 1, dash: "dot" }, xaxis: "x", yaxis: "y" },
        { x: dates, y: get("reg_residual"),   name: t("trace.residual"),   type: "bar",
          marker: { color: residColors, opacity: 0.65 }, xaxis: "x2", yaxis: "y2" },
    ], {
        ...LAYOUT_BASE,
        grid: { rows: 2, columns: 1, pattern: "independent", roworder: "top to bottom" },
        xaxis:  { ...LAYOUT_BASE.xaxis, anchor: "y",  domain: [0, 1] },
        yaxis:  { ...LAYOUT_BASE.yaxis, domain: [0.42, 1], title: { text: t("axis.usdcny"), font: { size: 10 } } },
        xaxis2: { ...LAYOUT_BASE.xaxis, anchor: "y2", domain: [0, 1] },
        yaxis2: { ...LAYOUT_BASE.yaxis, domain: [0, 0.34], title: { text: t("axis.residual"), font: { size: 10 } } },
        margin: { l: 60, r: 24, t: 16, b: 50 },
    }, PLOTLY_CONFIG);

    /* Univariate vs multivariate residual */
    Plotly.newPlot("chart-residual-compare", [
        { x: dates, y: get("reg_residual_uni"), name: t("trace.singleVar"), type: "scatter",
          line: { color: "rgba(87,83,78,0.55)", width: 1.2, dash: "dot" } },
        { x: dates, y: get("reg_residual"),     name: t("trace.multiDxy"), type: "scatter",
          line: { color: COLORS.bear, width: 2 },
          fill: "tozeroy", fillcolor: "rgba(185,28,28,0.06)" },
    ], {
        ...LAYOUT_BASE,
        yaxis: { ...LAYOUT_BASE.yaxis, title: { text: t("axis.residual_cny"), font: { size: 10 } }, zeroline: true },
    }, PLOTLY_CONFIG);

    Plotly.newPlot("chart-reg-betas-roll", [
        { x: dates, y: get("reg_beta_spread"), name: t("trace.betaSpreadRoll"), type: "scatter",
          line: { color: COLORS.line1, width: 1.6 } },
        { x: dates, y: get("reg_beta_dxy"), name: t("trace.betaDxyRoll"), type: "scatter",
          line: { color: COLORS.line2, width: 1.6 } },
    ], {
        ...LAYOUT_BASE,
        yaxis: { ...LAYOUT_BASE.yaxis, title: { text: t("axis.betaCoef"), font: { size: 10 } }, zeroline: true },
    }, PLOTLY_CONFIG);

    Plotly.newPlot("chart-reg-fit-roll", [
        { x: dates, y: get("reg_r2"), name: t("trace.r2Roll"), type: "scatter",
          line: { color: COLORS.navy, width: 1.8 }, yaxis: "y" },
        { x: dates, y: get("reg_residual_z"), name: t("trace.residZ"), type: "scatter",
          line: { color: COLORS.ochre, width: 1.4 }, yaxis: "y2" },
    ], {
        ...LAYOUT_BASE,
        yaxis: {
            ...LAYOUT_BASE.yaxis,
            title: { text: t("axis.r2short"), font: { size: 10 } },
            rangemode: "tozero",
            side: "left",
        },
        yaxis2: {
            ...LAYOUT_BASE.yaxis,
            title: { text: t("axis.residZ"), font: { size: 10 } },
            overlaying: "y",
            side: "right",
            showgrid: false,
            zeroline: true,
        },
        margin: { l: 52, r: 52, t: 16, b: 40 },
    }, PLOTLY_CONFIG);

    /* CIP deviation */
    Plotly.newPlot("chart-cip", [
        { x: dates, y: get("cip_deviation"), name: t("trace.cipBasis"), type: "scatter",
          line: { color: COLORS.warn, width: 1.5 },
          fill: "tozeroy", fillcolor: "rgba(161,98,7,0.10)" },
    ], {
        ...LAYOUT_BASE,
        yaxis: { ...LAYOUT_BASE.yaxis, title: { text: t("axis.deviation"), font: { size: 10 } } },
    }, PLOTLY_CONFIG);

    /* Trinity */
    Plotly.newPlot("chart-trinity", [
        { x: dates, y: get("pboc_fix"), name: t("trace.fix"),      type: "scatter",
          line: { color: COLORS.line2, width: 2.3 } },
        { x: dates, y: get("usdcny"),   name: t("trace.onshore"),  type: "scatter",
          line: { color: COLORS.line1, width: 1.5 } },
        { x: dates, y: get("usdcnh"),   name: t("trace.offshore"), type: "scatter",
          line: { color: COLORS.line3, width: 1.5, dash: "dash" } },
    ], {
        ...LAYOUT_BASE,
        yaxis: { ...LAYOUT_BASE.yaxis, title: { text: t("axis.usdcny"), font: { size: 10 } } },
    }, PLOTLY_CONFIG);

    /* Fixing bias */
    const biasPips    = get("fixing_bias").map(v => v == null ? null : v * 10000);
    const biasRawPips = get("fixing_bias_raw").map(v => v == null ? null : v * 10000);
    const biasColors  = biasPips.map(v => v == null ? COLORS.muted : v < 0 ? COLORS.bull : COLORS.bear);
    const m20 = get("bias_20d_mean").map(v => v == null ? null : v * 10000);
    const m60 = get("bias_60d_mean").map(v => v == null ? null : v * 10000);
    const di  = get("defense_intensity").map(v => v == null ? null : v * 10000);

    Plotly.newPlot("chart-fixing", [
        { x: dates, y: biasPips, name: t("trace.dxyAdjPips"), type: "bar",
          marker: { color: biasColors, opacity: 0.7 }, xaxis: "x", yaxis: "y" },
        { x: dates, y: biasRawPips, name: t("trace.rawBias"), type: "scatter",
          line: { color: "rgba(87,83,78,0.55)", width: 1, dash: "dot" }, xaxis: "x", yaxis: "y" },
        { x: dates, y: m20, name: t("trace.m20"), type: "scatter",
          line: { color: COLORS.line1, width: 2 }, xaxis: "x", yaxis: "y" },
        { x: dates, y: m60, name: t("trace.m60"), type: "scatter",
          line: { color: COLORS.line2, width: 1.5, dash: "dash" }, xaxis: "x2", yaxis: "y2" },
        { x: dates, y: di, name: t("trace.defense"), type: "scatter",
          line: { color: COLORS.bull, width: 1.4 },
          fill: "tozeroy", fillcolor: "rgba(21,128,61,0.10)",
          xaxis: "x2", yaxis: "y2" },
    ], {
        ...LAYOUT_BASE,
        grid: { rows: 2, columns: 1, pattern: "independent", roworder: "top to bottom" },
        xaxis:  { ...LAYOUT_BASE.xaxis, anchor: "y",  domain: [0, 1] },
        yaxis:  { ...LAYOUT_BASE.yaxis, domain: [0.42, 1], title: { text: t("axis.bias_pips"), font: { size: 10 } }, zeroline: true },
        xaxis2: { ...LAYOUT_BASE.xaxis, anchor: "y2", domain: [0, 1] },
        yaxis2: { ...LAYOUT_BASE.yaxis, domain: [0, 0.34], title: { text: t("axis.defense_60d"), font: { size: 10 } }, zeroline: true },
        margin: { l: 60, r: 24, t: 16, b: 50 },
    }, PLOTLY_CONFIG);

    /* Composite trend */
    const shapes = ZONES.map(z => ({
        type: "rect", xref: "paper", x0: 0, x1: 1, y0: z.lo, y1: z.hi,
        fillcolor: z.color, opacity: 0.06, line: { width: 0 },
    }));
    Plotly.newPlot("chart-composite", [
        { x: dates, y: get("composite_score"), name: t("trace.scoreRaw"), type: "scatter",
          line: { color: "rgba(12,10,9,0.22)", width: 1 } },
        { x: dates, y: get("composite_score_smooth"), name: t("trace.score5d"), type: "scatter",
          line: { color: COLORS.warn, width: 2.5 },
          fill: "tozeroy", fillcolor: "rgba(161,98,7,0.06)" },
    ], {
        ...LAYOUT_BASE,
        yaxis: { ...LAYOUT_BASE.yaxis, range: [0, 100], title: { text: t("axis.pressure"), font: { size: 10 } } },
        shapes,
    }, PLOTLY_CONFIG);
}

/* ─────────────────────────────────────────────────────────────
 *  Regression Stats Panel
 * ───────────────────────────────────────────────────────────── */
function renderRegStats(s) {
    const num = (v) => { const x = parseFloat(v); return isNaN(x) ? null : x; };
    const fmt = (v, d=3) => v == null ? "—" : v.toFixed(d);
    const cell = (label, value, cls, meta) => `
        <div class="regstats-cell">
            <div class="regstats-label">${label}</div>
            <div class="regstats-value ${cls||''}">${value}</div>
            <div class="regstats-meta">${meta}</div>
        </div>`;

    const r2 = num(s.reg_r2);
    document.getElementById("regstats").innerHTML = [
        cell(t("reg.beta_spread"), fmt(num(s.reg_beta_spread)),       "",       t("reg.afterdxy")),
        cell(t("reg.beta_dxy"),    fmt(num(s.reg_beta_dxy), 4),       "ochre",  t("reg.per1pt")),
        cell(t("reg.r2"),          r2 == null ? "—" : (r2*100).toFixed(1)+"%", "accent", t("reg.modelfit")),
        cell(t("reg.alpha"),       fmt(num(s.alpha_cny_dxy)),         "",       t("reg.fixadj")),
    ].join("");
}

/* ─────────────────────────────────────────────────────────────
 *  Findings (auto-generated)
 * ───────────────────────────────────────────────────────────── */
function renderFindings(s) {
    const num = (k) => parseFloat(s[k]);
    const fmt = (v, d=2) => isNaN(v) ? "—" : v.toFixed(d);

    const carry  = num("raw_carry"),    pct1  = num("carry_pct_rank"), pct2 = num("carry_pct_rank_2y");
    const beta1  = num("reg_beta_spread"), beta2 = num("reg_beta_dxy"), r2 = num("reg_r2");
    const cipDev = num("cip_deviation"), regRes = num("reg_residual"), regResUni = num("reg_residual_uni");
    const bias   = num("fixing_bias"),  biasRaw = num("fixing_bias_raw"), defi = num("defense_intensity");
    const alpha  = num("alpha_cny_dxy");

    /* Layer 01 */
    const f01 = [];
    if (!isNaN(carry)) {
        f01.push(t("finding.01.carry",
            fmt(carry),
            !isNaN(pct1) ? pct1.toFixed(0) : null,
            !isNaN(pct2) ? pct2.toFixed(0) : null));
    }
    if (!isNaN(carry) && carry > 2.5) {
        f01.push(t("finding.01.spread_high"));
    } else if (!isNaN(carry) && carry < 0) {
        f01.push(t("finding.01.spread_neg"));
    }
    f01.push(t("finding.01.hedged"));
    document.getElementById("findings-01").innerHTML = f01.map(x => `<li>${x}</li>`).join("");

    /* Layer 02 */
    const f02 = [];
    if (!isNaN(beta2)) {
        f02.push(t("finding.02.beta_dxy", fmt(beta2, 4), (beta2*1).toFixed(4)));
    }
    if (!isNaN(r2)) {
        f02.push(t("finding.02.r2", (r2*100).toFixed(1)));
    }
    if (!isNaN(beta1) && beta1 < 0 && !isNaN(beta2) && beta2 > 0) {
        f02.push(t("finding.02.multicol"));
    }
    if (!isNaN(regRes) && !isNaN(regResUni)) {
        const delta = Math.abs(regRes) - Math.abs(regResUni);
        f02.push(t("finding.02.residual", fmt(regRes, 4), fmt(regResUni, 4), delta < 0));
    }
    if (!isNaN(cipDev)) {
        const dir = cipDev > 0 ? t("finding.02.cip.above") : t("finding.02.cip.below");
        f02.push(t("finding.02.cip", dir, fmt(Math.abs(cipDev), 4)));
    }
    document.getElementById("findings-02").innerHTML = f02.map(x => `<li>${x}</li>`).join("");

    /* Layer 03 */
    const f03 = [];
    if (!isNaN(alpha)) {
        f03.push(t("finding.03.alpha", fmt(alpha), alpha >= 0.3 && alpha <= 0.5));
    }
    if (!isNaN(bias) && !isNaN(biasRaw)) {
        f03.push(t("finding.03.bias", (bias * 10000).toFixed(0), (biasRaw * 10000).toFixed(0)));
    }
    if (!isNaN(bias)) {
        if (bias < -0.005)      f03.push(t("finding.03.bias_neg"));
        else if (bias > 0.005)  f03.push(t("finding.03.bias_pos"));
        else                    f03.push(t("finding.03.bias_zero"));
    }
    if (!isNaN(defi)) {
        f03.push(t("finding.03.defense", (defi*10000).toFixed(0)));
    }
    document.getElementById("findings-03").innerHTML = f03.map(x => `<li>${x}</li>`).join("");
}

/* ─────────────────────────────────────────────────────────────
 *  Glossary
 * ───────────────────────────────────────────────────────────── */
function renderGlossary() {
    const tbl = document.getElementById("glossary-table");
    const rows = GLOSSARY_DEFS.map(([field, unit, source, desc, codeLink]) => {
        let codeTd;
        if (!codeLink) {
            codeTd = "—";
        } else {
            const [code, url] = codeLink.split("|");
            codeTd = `<a href="${url}" target="_blank" rel="noopener" style="font-family:'JetBrains Mono',monospace;font-size:11px;background:var(--bg-tint);padding:2px 6px;border-radius:3px;text-decoration:none;color:var(--navy)">${code}</a>`;
        }
        return `<tr><td>${field}</td><td>${unit}</td><td>${source}</td><td>${desc}</td><td>${codeTd}</td></tr>`;
    }).join("");
    tbl.innerHTML = `<thead><tr><th>${t("glossary.field")}</th><th>${t("glossary.unit")}</th><th>${t("glossary.source")}</th><th>${t("glossary.definition")}</th><th>${t("glossary.code")}</th></tr></thead><tbody>${rows}</tbody>`;
}

/* ─────────────────────────────────────────────────────────────
 *  Recent Data Table
 * ───────────────────────────────────────────────────────────── */
function renderTable(series) {
    const cols = ["date", "usdcny", "usdcnh", "pboc_fix", "us_2y", "cn_2y", "dxy",
                  "raw_carry", "reg_residual", "fixing_bias", "composite_score"];
    const labels = {
        date: t("table.date"), usdcny: t("table.usdcny"), usdcnh: t("table.usdcnh"),
        pboc_fix: t("table.fix"), us_2y: t("table.us2y"), cn_2y: t("table.cn2y"),
        dxy: t("table.dxy"), raw_carry: t("table.carry"), reg_residual: t("table.resid"),
        fixing_bias: t("table.bias"), composite_score: t("table.score"),
    };
    document.getElementById("data-thead").innerHTML =
        cols.map(c => `<th>${labels[c]}</th>`).join("");
    const rows = series.slice(-30).reverse();
    document.getElementById("data-tbody").innerHTML = rows.map(r => `
        <tr>${cols.map(c => {
            const v = r[c];
            if (v == null) return "<td>—</td>";
            if (c === "date") return `<td>${v}</td>`;
            const num = parseFloat(v);
            if (c === "fixing_bias")     return `<td>${(num*10000).toFixed(0)}</td>`;
            if (c === "composite_score") return `<td>${num.toFixed(0)}</td>`;
            return `<td>${num.toFixed(c.includes("2y") || c === "raw_carry" || c === "dxy" ? 2 : 4)}</td>`;
        }).join("")}</tr>`).join("");
}

/* ─────────────────────────────────────────────────────────────
 *  Download
 * ───────────────────────────────────────────────────────────── */
function renderDownload(series) {
    if (!series.length) return;
    const cols = Object.keys(series[0]);
    const csv = [cols.join(",")]
        .concat(series.map(r => cols.map(c => r[c] ?? "").join(",")))
        .join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    document.getElementById("download-csv").href = url;
    const top = document.getElementById("dl-csv-top");
    if (top) { top.href = url; top.setAttribute("download", "usdcny_tracker.csv"); }
}

/* ─────────────────────────────────────────────────────────────
 *  Chart Builder
 * ───────────────────────────────────────────────────────────── */
const BUILDER_FIELDS = [
    { key: "us_2y",            label: "US 2Y" },
    { key: "cn_2y",            label: "CN 2Y" },
    { key: "yield_spread",     label: "Spread" },
    { key: "usdcny",           label: "USD/CNY" },
    { key: "usdcnh",           label: "USD/CNH" },
    { key: "pboc_fix",         label: "PBOC Fix" },
    { key: "dxy",              label: "DXY" },
    { key: "raw_carry",        label: "Raw Carry" },
    { key: "carry_pct_rank",   label: "Carry Pctile" },
    { key: "cip_deviation",    label: "CIP Dev" },
    { key: "reg_residual",     label: "Residual (multi)" },
    { key: "reg_residual_z",   label: "Residual z" },
    { key: "reg_r2",           label: "Reg R²" },
    { key: "reg_residual_uni", label: "Residual (uni)" },
    { key: "fixing_bias",      label: "Fixing Bias" },
    { key: "fixing_bias_raw",  label: "Bias (raw)" },
    { key: "defense_intensity",label: "Defense Intensity" },
    { key: "composite_score",  label: "Composite" },
];

const BUILDER_DEFAULTS = ["raw_carry", "dxy"];

function renderBuilder(series) {
    const wrap = document.getElementById("builder-checkboxes");
    const prevChecked = [...wrap.querySelectorAll("input:checked")].map(i => i.value);
    const useDefaults = prevChecked.length === 0;

    wrap.innerHTML = BUILDER_FIELDS.map(f => {
        const checked = useDefaults ? BUILDER_DEFAULTS.includes(f.key) : prevChecked.includes(f.key);
        return `<label class="${checked ? "checked" : ""}">
                    <input type="checkbox" value="${f.key}" ${checked ? "checked" : ""}>
                    ${f.label}
                </label>`;
    }).join("");

    wrap.querySelectorAll("label").forEach(lbl => {
        lbl.addEventListener("click", () => {
            const cb = lbl.querySelector("input");
            setTimeout(() => {
                lbl.classList.toggle("checked", cb.checked);
                renderBuilderChart(series);
            }, 0);
        });
    });

    const freqEl = document.getElementById("builder-freq");
    const opts = freqEl.querySelectorAll("option");
    if (opts.length >= 3) {
        opts[0].textContent = t("builder.daily");
        opts[1].textContent = t("builder.weekly");
        opts[2].textContent = t("builder.monthly");
    }

    freqEl.onchange = () => renderBuilderChart(series);
    renderBuilderChart(series);
}

function aggregate(series, freq) {
    if (freq === "D") return series;
    const buckets = new Map();
    for (const r of series) {
        if (!r.date) continue;
        const d = new Date(r.date);
        let key;
        if (freq === "W") {
            const day = d.getUTCDay() || 7;
            d.setUTCDate(d.getUTCDate() - day + 1);
            key = d.toISOString().slice(0, 10);
        } else {
            key = `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,"0")}-01`;
        }
        if (!buckets.has(key)) buckets.set(key, []);
        buckets.get(key).push(r);
    }
    const out = [];
    for (const [date, rows] of [...buckets.entries()].sort()) {
        const merged = { date };
        for (const k of Object.keys(rows[0])) {
            if (k === "date") continue;
            const vals = rows.map(r => r[k]).filter(v => v != null && !isNaN(parseFloat(v))).map(parseFloat);
            merged[k] = vals.length ? vals.reduce((a,b)=>a+b,0) / vals.length : null;
        }
        out.push(merged);
    }
    return out;
}

function renderBuilderChart(series) {
    const freq = document.getElementById("builder-freq").value;
    const checked = [...document.querySelectorAll("#builder-checkboxes input:checked")].map(i => i.value);
    const data = aggregate(series, freq);
    const dates = data.map(r => r.date);

    const palette = [COLORS.line1, COLORS.line2, COLORS.line3, COLORS.line4, COLORS.bear, COLORS.bull];
    const traces = checked.map((key, i) => {
        const fld = BUILDER_FIELDS.find(f => f.key === key);
        return {
            x: dates, y: data.map(r => r[key]), name: fld ? fld.label : key, type: "scatter",
            line: { color: palette[i % palette.length], width: 1.7 },
        };
    });

    if (!traces.length) {
        Plotly.newPlot("chart-builder", [], {
            ...LAYOUT_BASE,
            annotations: [{ text: t("builder.empty"), xref: "paper", yref: "paper",
                            x: 0.5, y: 0.5, showarrow: false, font: { size: 14, color: COLORS.muted } }],
        }, PLOTLY_CONFIG);
        return;
    }

    Plotly.newPlot("chart-builder", traces, {
        ...LAYOUT_BASE,
        yaxis: { ...LAYOUT_BASE.yaxis, title: { text: t("axis.value"), font: { size: 10 } } },
    }, PLOTLY_CONFIG);
}

/* ─────────────────────────────────────────────────────────────
 *  Citation
 * ───────────────────────────────────────────────────────────── */
function renderCitation(d) {
    document.getElementById("cite-year").textContent = d.snapshot.date.slice(0, 4);
    document.getElementById("cite-date").textContent = d.snapshot.date;
    document.getElementById("footer-ts").textContent = d.generated_at;
}

/* boot */
document.addEventListener("DOMContentLoaded", boot);
