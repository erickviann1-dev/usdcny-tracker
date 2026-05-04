# Changelog

All notable changes to the USD/CNY Macro-Policy Divergence Tracker.

Format: each entry records (1) what changed, (2) why, (3) snapshot location of
the previous state under `history/`.

> **Looking for what to do NEXT?** See `ROADMAP.md` → ⭐ **Phase D**
> — **D.3 + D.4** (v3.6.0) next. **D.1 + D.2** shipped in **v3.5.0**.

---

## [v3.5.0] — 2026-05-04 · Trading Workbench Foundations (Phase D · D.1 + D.2)

### Vision
The dashboard answered *“can I trade carry today?”* in v3.4; v3.5 adds the next
two trader questions: *historical edge* (Sharpe-style track record) and
*sensitivity* (what price/rate level flips the verdict).

### Added — `analytics.py`

**`backtest_verdict(df)` → dict**  
Replays `interpret_carry_verdict()` on every historical row. Position sizing:
`yes → 1.0`, `marginal → 0.5`, `no`/`unknown → 0`. Daily P&L uses the ROADMAP
spec: **Δ headline hedged carry × prior-day position ÷ 252 ÷ 100** (headline =
offshore hedged when present, else onshore proxy). Cumulative equity compounds
`(1 + daily_pnl)`. **Benchmark:** passive long USD/CNY (spot arithmetic returns).
Exports `dates`, `verdict`, `position`, `daily_pnl`, `cumulative`,
`benchmark`, `benchmark_cumulative`, and `stats`:
`total_return`, `sharpe`, `max_dd`, `hit_rate`, `days_long`, `days_flat`, `n_days`.

**`compute_flip_lines(snap)` → list[dict]**  
Holds other inputs fixed and solves the **market 1Y** hedged formula for
**±0.5%/yr** crossings on: `usdcny`, `usdcny_fwd_1y`, `us_1y`, `shibor_1y`,
`cnh_hibor_1y` (CNH row only when offshore headline applies). Each row includes
`today`, `flip_to_yes`, `flip_to_no`, signed distance helpers (`dist_*_pct` /
`dist_*_pp`), labels, and `mode`. Values outside plausible FX/rate bands →
`null` (dashboard shows **—**).

### Added — `build.py`
- Top-level JSON keys **`backtest`** and **`flip_lines`**, printed at end of build.

### Added — `docs/index.html` + `docs/dashboard.js`
- Inside **`#verdict-card`**: small Plotly chart **`chart-verdict-backtest`**
  (strategy vs benchmark, indexed to 100), stats strip (`backtest.*` i18n keys),
  and **`verdict-flip-lines`** grid (`flip.*` i18n keys). Survives EN/ZH toggle.

### Added — `tools/selfcheck.py`
- **[15] v3.5 BACKTEST + FLIP LINES** — schema checks; **WARN** if Sharpe ≤ 0
  (informational; sample-dependent).

### Release hygiene
- Cache-bust **`dashboard.js?v=3.5.0`**; **`TRACKER_VERSION`** `3.5.0`.
- Snapshot of pre-release tree: **`history/v3.4-pre-backtest/`**.

---

## [v3.4.0] — 2026-05-03 · Decision Layer + Cross-Check Integrity Audit

### Vision
The user's pointed feedback after v3.3.2: *"this site doesn't clearly show
whether I can do the carry trade today, and there's no plain-English read
on PBOC policy intent."* True — the numbers were all there, but buried
in research-style KPI tiles. v3.4.0 promotes them into **two headline
decision cards** sitting right under the composite score, plus a
data-integrity badge in the topbar.

### Added — `analytics.py` decision interpreters

**`interpret_carry_verdict(snap)` → dict**
Translates `hedged_carry_offshore` (preferred) / `hedged_carry_proxy`
into a YES / MARGINAL / NO answer with full transparency:
```
verdict     : 'yes' | 'marginal' | 'no'
headline_en : "NO — would lose 0.90% / year"
headline_zh : "不能 — 一年净亏 0.90%"
chain       : 5-step Borrow → Convert → Invest → Hedge → NET
reasoning_en/zh : 1-2 sentence "why" using forward_premium_pct
                  when available, plain CIP framing otherwise
```
Decision rule:
- `hedged > +0.5%` → YES (rare; signals CIP arbitrage)
- `−0.5% ≤ hedged ≤ +0.5%` → MARGINAL (within transaction-cost band)
- `hedged < −0.5%` → NO (forward absorbs the carry)

**`interpret_policy_stance(snap, df)` → dict**
Combines `fixing_bias` + `cnh_funding_stress` + `onoffshore_gap` into
one of five postures with prose explanation:
- `defending`         — multiple levers active, e.g. CNH liquidity squeeze
- `weakening`         — letting CNY drift weak, fix biased weaker
- `leaning_defend`    — single soft signal of defence
- `leaning_weak`      — single soft signal of tolerance
- `neutral`           — all three levers quiet (= PBOC hands-off)

### Added — `tools/cross_check.py` (data integrity audit)
9 internal-consistency checks run on every build:
1. **Hedged-carry math identity** — `on − off ≈ cnh_funding_stress`
   (mathematical, must be exact within rounding)
2. On/Off basis range (`|CNY − CNH| / CNY < 1%`)
3. PBOC fix vs spot in trading band (`< 2%`)
4. DXY day-over-day move sane (`< 5%`)
5. CNH HIBOR vs Shibor spread (typical −1.5% to +6%)
6. CN 2Y in plausible range (0.3–5%)
7. US 2Y in plausible range (0.5–8%)
8. Composite score in [0, 100]
9. CIP deviation magnitude (`< 15%`)

Each check returns `{name_en, name_zh, status, detail}`. Today: 9/9 pass.

### Added — `build.py` payload integration
- `build_decision_layer(snap, df)` runs after `latest_snapshot` and
  attaches `decision: {carry_verdict, policy_stance}` to the JSON
- `run_cross_checks(snap, df)` runs after analytics, attaches
  `cross_checks: [...]` array
- Build output now prints the verdict + stance + integrity counts

### Added — `docs/index.html` decision-grid UI
- New `.decision-grid` after the hero, before chapter-01
- Two `.decision-card` panels — `#verdict-card`, `#stance-card`
- Top-edge accent stripe colour-codes the answer (green/red/ochre/muted)
- Method-box style "chain" table for verdict math, signals row for stance
- Italic prose footer ("why this verdict") in card body
- Topbar gets an `#topbar-xcheck` badge (small green/yellow/red dot +
  "Integrity 9/9" count, tooltip lists every check)

### Added — `docs/dashboard.js` render functions
- `renderVerdict(carry_verdict)` — wires headline / chain / reasoning,
  applies `verdict-{yes|no|marginal}` class for stripe colour
- `renderStance(policy_stance)` — wires headline / signals / reading,
  applies `stance-{defending|weakening|...}` class
- `renderCrossChecks(checks)` — sets badge colour + count + hover tooltip
- All three honour `LANG === "zh"` for bilingual switching
- Wired into `renderAll()` → re-renders on language toggle

### Added — i18n keys (EN + ZH symmetric)
| Key | EN | ZH |
|---|---|---|
| `verdict.eyebrow` | "The Carry-Trade Verdict Today" | "今日套利交易判断" |
| `stance.eyebrow`  | "PBOC Policy Stance Today"      | "央行政策姿态" |

Other strings come from `decision.carry_verdict.headline_en/zh` etc.
inside `data.json` itself (not in the i18n dict, since they're computed
each build). Total dict size: EN 317 = ZH 317.

### Verified locally (today's snapshot)
```
Carry verdict:    NO — would lose 0.90% / year
                  • borrow CNY @ Shibor 1Y    1.47%
                  • convert USD @ spot        6.8600
                  • invest UST 1Y             3.72%
                  • lock 1Y forward           6.6700
                  • NET (offshore CNH HIBOR)  -0.90%/yr

Policy stance:    MILD DEFENCE
                  • Fixing bias        -0 pips     (neutral)
                  • CNH funding stress +0.21%      (neutral)
                  • On/Off basis       -0.0319     (defend) ← CNH stronger
                  → "One lever shows defence; others quiet."

Integrity:        ✓ 9 pass · 0 warn · 0 fail (all bounds sane)
                  Hedged-carry math identity: |delta| = 0.0000% ✓
```

### Cache-bust → v3.4.0
- `dashboard.js` header + `TRACKER_VERSION` constant
- `<script src="dashboard.js?v=3.4.0">`
- `index.html` footer

### Files Touched
- `analytics.py`           — +180 lines (2 interpreters + helper export)
- `tools/cross_check.py`   — new file, 130 lines, 9 checks
- `build.py`               — wired both into payload + summary print
- `docs/index.html`        — decision-grid section + topbar badge + ~120 lines CSS
- `docs/dashboard.js`      — 3 render functions + 2 i18n keys + version bump

### Snapshot
Pre-edit state saved to `history/v3.3.2-pre-verdict/`.

### What this closes from user feedback
- ✅ "看不出能不能做这笔套利" → headline verdict YES/NO/MARGINAL with full math chain
- ✅ "不确定数字是否准确" → 9-check integrity audit + green badge in topbar
- ✅ "看不到对央行政策的明确解读" → stance card with 5 enumerated postures + prose

### Deliberately NOT done (per user's directive)
- Skipped per-KPI "verify ↗" external links (user said skip)

### Open after v3.4.0
- Phase B (v4.0 Macro Backdrop) still in `ROADMAP.md`, awaits assignment
- CNH spot history still accumulating via Yahoo v8 cache (1 row today)
- True hedged-carry with NDF / paid swap-points (paid data only)

---

## [v3.3.2] — 2026-05-01 · Daily DXY (was secretly weekly!) + Freshness Audit

### Bug fixed — DXY was a *weekly* series silently ffill'd to look daily
The pre-v3.3.2 `fetch_dxy()` chain went: yfinance → akshare → FRED `DTWEXBGS`.
On the user's Windows machine yfinance fails (SSL), akshare returns nothing
useful, and FRED `DTWEXBGS` is the **Trade-Weighted Broad Dollar Index**
which is published **weekly** (Fridays only). Combined with
`get_master_data`'s `df.ffill(limit=5)`, the dashboard showed `dxy = 118.73`
on the same value Mon–Fri **for 5 days at a time**. The OLS regression
was fitting weekly data masquerading as daily.

A freshness audit revealed:
```
dxy  last 5 days: 118.7294 118.7294 118.7294 118.7294 118.7294   🔴 FLAT
```
All other fields moved daily as expected.

### Fix — daily-first fallback chain
```
1. yfinance DX-Y.NYB           (works on Linux/GitHub Actions; SSL fails on Windows)
2. Yahoo v8 chart API DX-Y.NYB (works EVERYWHERE — no SSL cert dependency)
3. FRED DTWEXAFEGS             (Advanced Foreign Economies, DAILY)
4. akshare legacy paths
5. FRED DTWEXBGS               (Broad TWI WEEKLY — last resort only)
```

### Verified after fix
```
dxy  last 5 days: 98.4800 98.6200 98.9200 98.0800 98.2100   ✅ all unique
```

### Headline metric change (expected, not a regression)
| | Before (weekly TWI) | After (true ICE DXY) |
|---|---:|---:|
| Latest DXY value | 118.73 | **98.21** |
| Movement / day | ≈ 0 | ✅ daily |
| OLS β₂ (regression coef) | 0.0738 | will recalibrate |

Different basket → different absolute level. ICE DXY is what FX desks
actually trade and watch (EUR 57.6%, JPY 13.6%, GBP 11.9%, CAD 9.1%,
SEK 4.2%, CHF 3.6%). FRED Broad TWI is academic/Fed-favoured but not
tradable. For a quant tracker, ICE DXY is the right primitive.

### Files Touched
- `data_fetcher.py` — `fetch_dxy()` rewritten with 5-tier daily-first chain
- `CHANGELOG.md` — this entry

### Audit method (saved for future regressions)
```python
import pandas as pd, json
d = json.load(open('docs/data.json'))
df = pd.DataFrame(d['series']).set_index(pd.to_datetime([r['date'] for r in d['series']]))
for f in ['dxy', 'us_2y', 'cn_2y', 'usdcny']:
    last5 = df[f].dropna().tail(5).values
    n_uniq = len(set(round(v,6) for v in last5))
    print(f'{f}: {n_uniq}/5 unique → {"FLAT" if n_uniq==1 else "moving"}')
```
Run after any data-source change. If a field comes back FLAT, suspect
either (a) source published weekly, or (b) a stale cache.

### What's now genuinely daily-fresh (full audit)
| Field | Status |
|---|---|
| US 2Y, CN 2Y | ✅ daily (akshare bond_zh_us_rate) |
| USD/CNY, USD/CNH spot | ✅ daily (yfinance + Yahoo v8 fallback) |
| PBOC fix | ✅ daily (akshare currency_boc_sina) |
| **DXY** | **✅ daily (Yahoo v8 ICE DXY) — fixed in this release** |
| Shibor 1Y, US 1Y | ✅ daily (akshare + FRED DGS1) |
| CNH HIBOR 1Y/3M/ON | ✅ daily (akshare HK interbank) |
| CFETS USDCNY 1Y forward | ⚠️ accumulating cache (1 row/day, growing) |
| USD/CNH spot (Yahoo v8 cache) | ⚠️ accumulating cache (1 row/day, growing) |

The two ⚠️ items are by-design — paid alternatives don't exist on free feeds.
Cache will accumulate naturally with each scheduled build.

---

## [v3.3.1] — 2026-05-01 · Real ET Auto-Schedule + Live Update Timestamp

> Tightly scoped patch on top of v3.3.0. Fixes a silent scheduling bug
> and surfaces the auto-build timestamp prominently on the dashboard.

### Bug fixed — GitHub Actions cron was firing at the wrong hour
`.github/workflows/daily-build.yml` previously had:
```yaml
- cron: "0 10 * * *"
  timezone: "America/New_York"
```
**The `timezone:` field is silently ignored by GitHub Actions cron** —
it accepts UTC only. The schedule was therefore firing at 10:00 / 15:00
UTC, which is 06:00 / 11:00 ET in EDT or 05:00 / 10:00 ET in EST. The
target was **10:00 AM and 2:00 PM New York time**.

### Fix — 4-cron pattern covers both DST regimes
```yaml
- cron: "0 14 * * *"   # 10am EDT  /  9am  EST   ← target #1 (summer)
- cron: "0 15 * * *"   # 11am EDT  /  10am EST   ← target #1 (winter)
- cron: "0 18 * * *"   # 2pm  EDT  /  1pm  EST   ← target #2 (summer)
- cron: "0 19 * * *"   # 3pm  EDT  /  2pm  EST   ← target #2 (winter)
```
Burns 4 builds/day instead of 2, but exactly 2 hit the target on any
given day. Free tier covers it easily (4 × 3 min ≈ 12 min/day).

### Added — Timezone-aware build timestamps
`build.py` now writes three fields into `data.json`:
- `generated_at`     — runner local time (UTC on GitHub Actions)
- `generated_at_utc` — explicit UTC stamp e.g. `"2026-05-03 04:25:50 UTC"`
- `generated_at_et`  — **user-facing ET stamp** e.g. `"2026-05-03 00:25 EDT"`
  (auto switches between EDT and EST via `zoneinfo.ZoneInfo("America/New_York")`)

### Added — Topbar "Updated [time]" element
- New `#topbar-updated` span next to the score; populated from `d.generated_at_et`
- Footer `#footer-ts` upgraded to use `generated_at_et` as well
- New i18n key `updated.label` (EN: "Updated", ZH: "更新于")
- Dictionaries still symmetric — EN 315 = ZH 315

### Files Touched
- `.github/workflows/daily-build.yml` — 4 cron entries replacing 2 + comment
- `build.py` — `from datetime import timezone`, `from zoneinfo import ZoneInfo`,
  three timestamp fields in payload
- `docs/dashboard.js` — `renderTopbar()` writes `#topbar-updated`,
  `renderCitation()` footer uses ET, +2 i18n keys
- `docs/index.html` — topbar gets `#topbar-updated` element

### Verified locally
```
generated_at     : 2026-05-02 23:25:50
generated_at_utc : 2026-05-03 04:25:50 UTC
generated_at_et  : 2026-05-03 00:25 EDT     ← shown on website
```

---

## [v3.3.0] — 2026-05-01 · Offshore CNH Funding Layer + Market-Quoted Hedged Carry

### Why this is one **minor** release (not a string of patches)

Two substantive layers shipped together: **(A)** Layer 1 headline hedged carry can be a **market-quoted 1Y covered return** (CFETS **F**, UST 1Y, onshore Shibor 1Y) instead of a pure **CIP residual proxy**; **(B)** the long-standing **CNH data gap** is partially closed with **CNH HIBOR** (full history on free feeds) plus **incremental USDCNH spot** (Yahoo v8 cache). Together they change interpretability enough to warrant **v3.3.0** rather than more v3.2.x patches.

### Market F/S vs legacy CIP proxy (onshore hedged)

- **Old pipeline** (`hedged_carry_proxy = raw_carry − cip_dev_pct`, 2Y-flavoured): could print a large **positive** number (e.g. **+8.04%**) while **money-market carry** was only ~**+2.25%** (UST1Y − Shibor1Y) — a **“free lunch”** mix in frictionless terms, because a **2Y spread minus a CIP %** is **not** a **1Y hedged deposit loop**.
- **New pipeline** (when `usdcny_fwd_1y` is present):  
  \(\text{Hedged (\%)} = 100 \times \big[(1+r_{USD})\frac{F}{S} - (1+r_{CNY})\big]\)  
  Recent builds land near **−0.29%**: **CNY forward premium / hedge cost** consumes the nominal MM wedge — a more plausible **tradable** reading than +8% hedged upside.

### Offshore CNH funding & hedged return

- **CNH HIBOR** (akshare `rate_interbank`, HK interbank market): 1Y / 3M / overnight fixings; **~100% series coverage** from 2013-03-22.
- **Offshore hedged carry**:  
  `hedged_carry_offshore = 100 × [(1 + r_USD) × (F/S) − (1 + r_CNH)]` with **r_CNH = CNH HIBOR 1Y** (not Shibor). Example: **−0.50%** offshore vs **−0.29%** onshore; wedge ≈ **`cnh_funding_stress`** (CNH HIBOR 1Y − Shibor 1Y, e.g. **+0.21%** with a low historical percentile — squeeze tail indicator).
- **USDCNH spot**: Yahoo Finance v8 **daily append** to `cache/usdcnh_spot.csv` where other paths fail; **no free deep history** (see reconnaissance table in repo history). Quality badge for `usdcnh` may stay weak until the cache accumulates.

### Data & plumbing (summary)

- **CFETS 1Y forward**: `akshare.fx_c_swap_cm()` → `cache/cfets_usdcny_1y_fwd.csv` (`CFETS_FWD_CACHE`); merge **forward-fills only after first cache date**; else **2Y CIP fallback** (`cip_proxy_2y`).
- **Snapshot / series**: `usdcny_fwd_1y`, `hedged_carry_method` (`market_1y` | `cip_proxy_2y`), `forward_premium_pct`; plus `cnh_hibor_1y`, `cnh_hibor_3m`, `cnh_hibor_on`, `cnh_funding_stress`, `cnh_stress_pct_rank`, `hedged_carry_offshore`.
- **Build**: `build.py` exports new columns to `data.json` and Excel **series** sheet.

### Dashboard (surfacing)

- **KPI tiles**: CNH HIBOR 1Y, CNH funding stress (colour **warn** if > +0.3%, **bear** if > +1%; meta shows 252d percentile), offshore hedged return (same colour logic as onshore hedged).
- **Layer 03 chart**: `cnh_funding_stress` time series with reference lines at **+1%** and **+5%** (+1% / +5% annotations).
- **Glossary**: **+6 rows** (`cnh_hibor_1y/3m/on`, `cnh_funding_stress`, `cnh_stress_pct_rank`, `hedged_carry_offshore`); **`gloss.count` → 48 fields** (full `GLOSSARY_DEFS` row count after prior v3.1/v3.2 expansions).
- **i18n**: **+10 keys × EN/ZH** (`kpi.*`, `meta.*`, `chart.cnhStress*`, `axis.cnh_stress`); **319 × 2** keys total, dictionaries remain symmetric.

### Patches rolled in (v3.2.1 → v3.2.8)

Consolidated **without re-refactoring** tested code: methodology payload + `reg_residual_z` + regression diagnostics; composite methodology & historical stress lens; author/i18n/Glossary/builder growth; **CFETS forward-first hedged** + cache; **dashboard.js** KPI **`hedgedMeta`** placement fix.

### i18n & QA

- **Self-check**: HTML `data-i18n`, glossary row count, **`TRACKER_VERSION`** ↔ script/footer/header; notebook / `.xlsx` / `.ipynb` artefacts; hedged carry vs snapshot **&lt; 0.05%** drift on validation runs.
- **USDCNH coverage** may still **WARN/FAIL** on fresh clones until the spot cache grows — expected; **CNH HIBOR** series are complete.

### Cache-bust & version

- `docs/index.html`: `<script src="dashboard.js?v=3.3.0">`, footer/topbar **v3.3.0**; README banner **v3.3.0**.

### Snapshot

Pre–CNH-layer UI state: `history/v3.2.8-pre-cnh/`.

### Reconnaissance — USDCNH history (unchanged facts)

| Source | Outcome |
|---|---|
| `Stooq.com/q/d/l/?s=usdcnh` | API-key gated since 2024 |
| HKMA CNH segment param | Returns HKD, not CNH |
| `akshare` Baidu / Eastmoney USDCNH | Empty or errors on probe networks |
| Yahoo v8 multi-year range | Only ~1 row — backend has no free depth |

**Conclusion:** institutional spot/forward history is paid-data territory; **HIBOR** is the high-ROI free anchor.

---

## [v3.2] — 2026-05-01 · Authority & Export Layer

### Vision
Neutralise the "GitHub demo" perception by adding data provenance
transparency and production-tool exports. No model changes — pure
surfacing + export polish. Addresses critique #1 from the user-supplied
review (Anders Staxen comparison): the tracker now ships `.xlsx` and
`.ipynb` take-home downloads, and every FRED-sourced field carries a
clickable source-code badge.

### A.1 — FRED code transparency in the glossary
- `GLOSSARY_DEFS` expanded from 4-column to 5-column arrays:
  `[field, unit, source, description, codeLink]`
- 38 glossary rows (was 31): added `shibor_1y`, `us_1y`, `mm_spread`,
  `hedged_carry_proxy`, `cip_dev_pct`, `policy_score` from v3.1
- 7 rows carry clickable source-code badges:
  `DTWEXBGS`, `DGS1`, `DEXCHUS` (FRED); `bond_zh_us_rate`,
  `currency_boc_sina`, `rate_interbank` (akshare wiki)
- `renderGlossary()` updated to render 5th column with styled `<a>` badges
- New i18n key: `glossary.code` (EN: "Source Code", ZH: "数据代码")
- `gloss.count` updated to "(38 fields)" / "（38 个字段）"

### A.2 — Excel export
- `build.py`: new `write_excel()` function generates
  `docs/usdcny_tracker.xlsx` with three sheets:
  - **series** — full time-series (42 columns × 523 rows)
  - **snapshot** — single-row current values
  - **methodology** — Layer 1/2/3 + Composite formula descriptions
- `docs/index.html`: new download button in the Data & Export chapter
- New i18n key: `data.xlsx` (EN: "↓ Download Excel (.xlsx)",
  ZH: "↓ 下载 Excel (.xlsx)")
- `openpyxl` was already in `requirements.txt`

### A.3 — Auto-generated replication notebook
- New file: `tools/build_notebook.py` — uses `nbformat` to generate
  `docs/usdcny_tracker_replication.ipynb` on each build. Five cells:
  1. Markdown — title, data date, citation block
  2. Code — imports (pandas, numpy, requests, matplotlib)
  3. Code — fetch live `data.json` from deployed site
  4. Code — independently re-compute raw_carry, CIP deviation,
     fixing_bias from raw series (proves nothing is hidden)
  5. Code — three diagnostic plots (composite score, residual histogram,
     fixing-bias rolling mean)
- `build.py`: calls `build_replication_notebook()` after data export
- `docs/index.html`: new download button for `.ipynb`
- New i18n key: `data.ipynb` (EN: "↓ Replication Notebook (.ipynb)",
  ZH: "↓ 复制验证笔记本 (.ipynb)")
- `nbformat>=5.9.0` added to `requirements.txt`

### A.4 — Source-code badges on KPI tiles
- `tile()` function in `renderKPIs()` now accepts optional 5th parameter
  `codeBadge` — renders a tiny `<code>` badge in the meta line
- Applied to: USD/CNY (`DEXCHUS`), UST 1Y (`DGS1`), DXY (`DTWEXBGS`)
- Other tiles (computed or akshare-sourced) left clean

### Cache-bust
- `<script src="dashboard.js?v=3.2">` (was `?v=3.1`)
- Header version comment `v3.2`, footer version label `v3.2`

### i18n symmetry
- 3 new keys added to both EN and ZH: `glossary.code`, `data.xlsx`,
  `data.ipynb`. Dictionaries remain symmetric.

### Build verification
```
✓ data.json        772 KB
✓ usdcny_tracker.xlsx  172 KB
✓ usdcny_tracker_replication.ipynb  generated
Composite Score:   58/100
USD/CNY:           6.84
Raw Carry:         2.62%
```

### Snapshot
Pre-edit state saved to `history/v3.1-pre-export/`.

### Files Touched
- `docs/dashboard.js` — GLOSSARY_DEFS 5th column, renderGlossary() rewrite,
  KPI tile badge, 3 new i18n keys × 2 langs, version bump
- `docs/index.html` — 2 new download buttons, script tag + footer version bump
- `build.py` — `write_excel()` function, `build_replication_notebook()` call,
  v3.1 series columns added
- `tools/build_notebook.py` — new file (replication notebook generator)
- `requirements.txt` — `nbformat>=5.9.0`
- `README.md` — version banner bump
- `CHANGELOG.md` — this entry

### Remaining work after v3.2
Phase B (v4.0 — Macro Backdrop Layer) and Phase C (v5.0 — Working Paper)
remain in `ROADMAP.md`, awaiting user assignment.

---

## 🗺️ Pending — see `ROADMAP.md` for the canonical work order

A user-supplied review (2026-05-01) compared the tracker to Anders Staxen's
us-macro.streamlit.app. Two of the four critiques landed:

1. **Production-tool gap** — no `.ipynb` / `.xlsx` "take-home" downloads
2. **Macro-context gap** — no Layer 0 explaining *why* the spread moves
   (Fed liquidity / China credit impulse / global risk)

The other two ("no Z-score", "no fix-vs-market") were already shipped in
v1.5–v3.1 (see those entries) — the reviewer didn't read carefully.

`ROADMAP.md` lays out:
- **v3.2** (½ day) — FRED code transparency + Excel export + auto-generated
  replication notebook
- **v4.0** (1–2 days) — Macro Backdrop layer (WALCL / RRP / VIX / CN credit
  impulse / CN M2) + dual-axis chart builder
- **v5.0** (writing project, not a Cursor task) — companion working paper
  (8–12 pp PDF) + real academic citations

---

## [v3.1] — 2026-05-01 · Hedged Carry + Money-Market Layer

### Vision
Address the user's three-layer critique screenshot: 套利层 was showing
**unhedged** carry only. The screenshot called for "1Y Swap Points /
Libor-Shibor Spread → 真实对冲后利差". Without paid swap-point feeds we
can't get true hedged P&L directly, but we can derive an **analytically
correct CIP-implied proxy** using data we already compute.

### Three new economic measurements

**1. Money-market layer (Libor-Shibor analog)**
- `shibor_1y` — CN 1Y interbank rate (akshare `rate_interbank`)
- `us_1y`     — UST 1Y constant maturity (FRED `DGS1`, no auth)
- `mm_spread` — `us_1y − shibor_1y` (the modern Libor-Shibor analog;
  Libor itself was discontinued 2023-06)
- `mm_carry`  — alias for `mm_spread`, surfaces in carry layer

**2. Hedged-carry proxy (analytical, no swap-point data needed)**
The mathematical chain:
```
raw_carry          = US_2Y − CN_2Y                      (% per year)
cip_dev_pct        = cip_deviation / spot × 100         (%)
hedged_carry_proxy = raw_carry − cip_dev_pct            (% per year)
```
Interpretation:
- CIP-perfect world → proxy ≈ 0 (no free lunch)
- Positive proxy → real arbitrage exists (rare; signals USD funding stress
  or capital-control friction)
- Negative proxy → hedging more than wipes out carry (PBOC defence + CCB
  baked into forward points)

**3. Hedged-carry percentile rank**
- `hedged_carry_pct_rank` — 252d rolling percentile, surfaces today's
  hedged opportunity vs trailing year

### Verified numbers (today's snapshot)
| Field | Value |
|---|---|
| `shibor_1y` | **1.47%** ✅ (akshare 100% coverage) |
| `us_1y`     | **3.75%** ✅ (FRED 100% coverage) |
| `mm_spread` | **2.28%** (vs raw_carry 2.62% — 2Y term premium ≈ 0.34%) |
| `cip_deviation` | -0.37 CNY |
| `cip_dev_pct`   | ≈ -5.4% |
| `hedged_carry_proxy` | **8.04%** ✅ (76th percentile, near 1Y high) |

### Added — `data_fetcher.py`
- `fetch_shibor_1y()` — akshare `rate_interbank(market='上海银行同业拆借市场',
  symbol='Shibor人民币', indicator='1年')`. Robust column-name matching
  (handles `'报告日'` / `'利率'`).
- `fetch_us_1y()` — FRED CSV `DGS1` (same auth-free pattern as `DTWEXBGS`)
- `get_master_data()` — wires both into master_df, computes `mm_spread`,
  exposes coverage in quality dict.

### Added — `analytics.py`
- `calc_carry()` now computes `mm_carry`
- `calc_mispricing()` now computes `cip_dev_pct`, `hedged_carry_proxy`,
  `hedged_carry_pct_rank` (need spot for `cip_dev_pct = cip_deviation / spot`)

### Added — `latest_snapshot()` (5 new fields)
`shibor_1y`, `us_1y`, `mm_spread`, `hedged_carry_proxy`, `hedged_carry_pct_rank`

### Added — `build.py` series export
Six new series: `shibor_1y`, `us_1y`, `mm_spread`, `mm_carry`, `cip_dev_pct`,
`hedged_carry_proxy`, `hedged_carry_pct_rank`. Payload grew 725→772 KB.

### Added — `docs/dashboard.js`
Four new KPI tiles (with auto-hide if N/A):
- "Hedged Carry (CIP-implied)" — colour-coded by magnitude
- "MM Spread (1Y)"
- "Shibor 1Y"
- "UST 1Y"

i18n: 8 new keys × 2 languages (kpi.hedged / kpi.mm / kpi.shibor / kpi.us1y +
4 meta sub-labels). Both dictionaries now 242 keys, still symmetric.

### Bug fixed during implementation
- **Lazy-import gotcha**: codebase imports `akshare as ak` *inside* each
  fetcher (akshare is heavy + has SSL quirks on Windows). My new
  `fetch_shibor_1y` referenced `ak.rate_interbank` without the local import,
  which raised `NameError` — silently swallowed by the bare `except Exception`.
  Lesson for Cursor: when adding a new akshare fetcher, **always copy the
  `import akshare as ak` line into the function body**.

### Cache-bust
- `<script src="dashboard.js?v=3.1">` (was `?v=3.0.1`)
- Header version comment, footer version label both bumped.

### Snapshot
Pre-edit state saved to `history/v3.0.1-pre-hedged/`.

### Files Touched
- `data_fetcher.py` — +60 lines (2 new fetchers + master_df wiring)
- `analytics.py` — +25 lines (mm_carry, cip_dev_pct, hedged_carry_proxy,
  pct_rank)
- `build.py` — series export list extended
- `docs/dashboard.js` — 4 KPI tiles + 8 i18n keys × 2 langs + version bump
- `docs/index.html` — script tag + footer version
- `CHANGELOG.md` — this entry

### Honest limitation acknowledged
The "Hedged Carry" proxy is **CIP-implied total return**, not a true
swap-locked P&L. They differ by the empirical CIP basis vs. swap-market
basis. For a research-grade tracker this is the right approximation; for
trade execution you still need real NDF/swap quotes.

### Remaining work after v3.1 (still open)
🔴 P0 — **CNH offshore data still 0%.** Pipeline ready, no free source.
🟠 P1 — User content placeholders (author / papers / featured / citation).
🟠 P1 — FRED TWI → true ICE DXY (~118 vs ~104).
🟠 P1 — KPI sparklines (CSS slot exists, JS not implemented).
🟡 P2 — OLS covariate expansion (VIX / copper / CN-US PMI gap).
🟡 P2 — True hedged carry with real swap points (paid data).
🟡 P3 — akshare column matching by name not position (`bond_zh_us_rate`).

---

## [v3.0.1] — 2026-05-01 · i18n Symmetry + Cache-Busting + Snapshot Path Fix

### Vision
Patch release. Three concrete bugs fixed, all observed via a single user
screenshot showing literal i18n keys (`hero.display`, `html.download`, …)
rendered on the live page.

### Root cause analysis
1. **EN dictionary was a strict subset of ZH** — 89 keys lived only in `zh`.
   In ZH mode `t(key)` worked. In EN mode `applyStaticI18n` fell back to
   `dataset.i18nOrig` (the HTML-baked English) so it *coincidentally* worked
   too — but only because the HTML originals exist. Any future edit clearing
   an HTML original would have surfaced raw key names.
2. **No cache-busting on `dashboard.js`** — after the v3.0 i18n fix in
   commit `f515e71`, browsers kept serving the pre-fix JS from cache and
   showed literal keys even though the deployed file was correct. This is
   what the user actually saw.
3. **`tools/snapshot.py` still pointed at `web/`** — directory was renamed
   to `docs/` in commit `687106d`, leaving snapshots silently incomplete
   (the public site files were skipped on every snapshot).

### Changed — `docs/dashboard.js`
- Added 89 EN keys mirroring the ZH dictionary (now both 234 keys, perfectly
  symmetric — `EN ⊕ ZH = ∅`)
- Bumped header version comment from `v2.0` → `v3.0.1` (was stale across
  v2.0 → v3.0 → v3.0.1)

### Changed — `docs/index.html`
- `<script src="dashboard.js">` → `<script src="dashboard.js?v=3.0.1">` so
  every future JS edit invalidates browser + CDN caches automatically.
  **Convention:** every CHANGELOG release that touches `dashboard.js` MUST
  bump this query string (e.g. `?v=3.1.0`, `?v=3.0.2`). Cursor: enforce.
- Footer version label `v3.0` → `v3.0.1`

### Changed — `tools/snapshot.py`
- `SNAPSHOT_FILES` now includes both `docs/*` (current) and `web/*` (legacy
  fallback for old snapshots). Previously only saved Python files when run
  after the `web/→docs/` rename.

### Symmetry verification
```
EN: 234 keys · ZH: 234 keys
Only-ZH: ∅ · Only-EN: ∅
```

### Snapshot
Pre-edit state saved to `history/v3.0-pre-cachebust/` (full `docs/` set +
all Python files).

### Files Touched
- `docs/dashboard.js` — +90 lines (1 version bump + 89 EN keys)
- `docs/index.html` — 2 lines (script tag query string + footer version)
- `tools/snapshot.py` — `SNAPSHOT_FILES` list expanded
- `CHANGELOG.md` — this entry
- `README.md` — version pointer + status updates

### Remaining work after v3.0.1 (still open)
🔴 P0 — **CNH offshore data still 0% covered.** Pipeline (`fetch_usdcnh_offshore_spot`)
is wired but no free source returns CNH history. Without CNH, Layer 03's
"market anchor" falls back to onshore previous close, which under-estimates
true defence intensity. Candidates to try next: TradingView scraping, Wind
free tier, Bloomberg Terminal export (manual CSV), or paid API.

🟠 P1 — **User-content placeholders unfilled** (this is for 魏来 personally,
not Cursor):
- `#author-name` / `#author-role` / `#author-bio` in `docs/index.html`
- `#author-linkedin` / `#author-email` / `#author-cv`
- `#paper-1` / `#paper-2` / `#paper-3` (sidebar)
- 3 cards in `<section id="featured">` (footer)
- Citation author name in `#citation-block`
- Brand monogram `SD` (2 places in HTML, 1 in JS loader caption)

🟠 P1 — **Replace FRED TWI (~118) with true ICE DXY (~104).** Different basket;
correlation ~0.95 but readers may misread absolute level.

🟡 P2 — **KPI sparklines.** CSS slot `.kpi-tile-spark` exists, JS not implemented.

🟡 P2 — **Hedged carry with real swap points.** Currently labelled "Unhedged
Raw Carry" honestly; turning it into true hedged P&L needs paid NDF data.

🟡 P2 — **OLS covariate expansion.** Current R² = 45.7%. Candidates: VIX,
copper, China-US PMI gap. Watch for multicollinearity (β₁ already inverted).

🟡 P3 — **akshare column selection by name not position** — `bond_zh_us_rate()`
schema-fragile (CN_2Y = col[0], US_2Y = col[6]).

---

## [v3.0] — 2026-05-01 · Data Integrity + Bilingual + CNH Pipeline

### Vision
Three goals: (1) fix the "fatal degeneration" where PBOC fix was silently
replacing onshore spot — causing Layer 3 to collapse to a pure DXY-overnight
inverse; (2) add bilingual (EN/中文) support across the entire site; (3) build
the USD/CNH offshore data pipeline so it activates automatically when a free
source becomes available.

### Design Principle — "No fake data is better than fake data"
When all market sources for USD/CNY fail, we **no longer** backfill with
`pboc_fix`. Missing `usdcny` surfaces as a "Data Integrity Notice" alert on the
dashboard (in both languages). This prevents Layer 3's `fixing_bias` from
degenerating into `-pboc_fix × α × dxy_ret`, which is a pure overnight-DXY
inverse with no policy signal.

### Added — Data Layer (`data_fetcher.py`)

**USD/CNY onshore spot multi-source pipeline:**
- `fetch_usdcny_onshore_spot()` — dedicated fallback chain:
  1. akshare `forex_hist_em()` with 5 symbol variants (`USDCNY`, `USD/CNY`,
     `USDCNY.FXCM`, `USDCNYC`, `美元人民币`)
  2. Eastmoney historical K-line API (`push2his.eastmoney.com`) with 3 secid
     candidates (`133.USDCNY`, `119.USDCNY`, `90.USDCNY`)
  3. FRED `DEXCHUS` CSV (lower-frequency fallback)
- `_is_valid_usdcny_series()` — sanity filter (min 30 points, median in 5.0–9.0)
- `_extract_fx_series()` — heterogeneous FX table parser (auto-detects date/value
  columns by name patterns in CN/EN)
- yfinance ticker variants: `USDCNY=X` → `CNY=X`, `USDCNH=X` → `CNH=X`

**USD/CNH offshore pipeline:**
- `fetch_usdcnh_offshore_spot()` — same pattern:
  1. akshare `forex_hist_em()` with 4 symbol variants
  2. Eastmoney K-line with 3 CNH secid candidates
- Currently 0% coverage (no free API exposes CNH history), but pipeline is ready

**Removed:**
- PBOC-fix → usdcny silent backfill (the "fatal degeneration" bug)

### Added — Bilingual i18n (`web/index.html` + `web/dashboard.js`)

**Language toggle:**
- Fixed-position EN / 中文 button pair in top-right corner of all pages
- Language preference persisted to `localStorage` (key: `tracker_lang`)
- Switching re-renders all static HTML (`data-i18n` / `data-i18n-html` attributes)
  AND all dynamic content (KPIs, alerts, charts, narrative, regression stats, table)

**i18n engine:**
- `I18N` object with `en` and `zh` dictionaries (~150 keys each)
- `t(key)` function — looks up current language, falls back to English
- `applyStaticI18n()` — scans all `data-i18n` / `data-i18n-html` DOM elements
- `switchLang(lang)` — toggles state, re-renders everything including Plotly charts

**Coverage — every user-visible string is bilingual:**
- Sidebar: about, sections nav, pressure zones, data sources, refresh instructions
- Main: title, subtitle, feature list, gauge label, zone pill text
- Sections: all tags, titles, lead paragraphs, methodology text, formulas
- KPI cards: all 9 labels + sub-labels
- Alerts: carry, fixing bias, high pressure, data integrity — all 4 types
- Carry narrative: direction text, intensity descriptors, full template
- Charts: all 17 chart titles + all axis labels + all 22 trace names
- Regression stats panel: all 4 metric labels + sub-text + explainer + β₁ note
- Interpretation table: all 4 headers + all 4 scenario rows
- Data table: all 10 column headers
- Footer text
- Loader text

### Added — β₁ Negative-Value Annotation

When `β₁ (Spread) < 0` in the regression stats panel, a yellow callout box
appears explaining: "Negative β₁ suggests strong multicollinearity with DXY;
in the current rolling window, DXY acts as the dominant driver." This prevents
misinterpretation as a bug. Displayed in both EN and ZH.

### Changed
- `fetch_fx_spot()` uses ticker variant lists instead of single tickers
- `fetch_fx_akshare()` uses multi-symbol fallback for both CNY and CNH
- `get_master_data()` shows explicit warning when falling back to fix (previously silent)
- Dashboard alerts include a "Data Integrity Notice" when usdcny is missing
- Composite score changed from 63 → 58 (due to real spot data replacing fix proxy)
- `α (CNY/DXY)` shifted from 0.318 → 0.271 (new data path changes rolling window composition)

### Calibrated Values (v3.0 snapshot)
| Metric | Value | Status |
|---|---|---|
| USD/CNY | 6.84 | ✅ Market source (not fix proxy) |
| PBOC Fix | 6.82 | ✅ |
| Composite | 58/100 | 🟡 Elevated |
| β₁ (Spread) | -0.033 | ⚠️ Multicollinearity — documented |
| β₂ (DXY) | 0.0738 | ✅ |
| R² | 45.7% | — |
| α (CNY/DXY) | 0.271 | ✅ Reasonable |
| Fixing Bias | -0.01 | ✅ Non-degenerate |

### Files Touched
- `data_fetcher.py` — major: added 3 new public functions, 4 private helpers,
  refactored `fetch_fx_spot()` and `fetch_fx_akshare()`, removed fix backfill
- `web/index.html` — major: added language toggle, `data-i18n`/`data-i18n-html`
  attributes on all static text elements, `.lang-toggle` CSS, `.alert.warn` CSS
- `web/dashboard.js` — full rewrite: added `I18N` dictionaries, `t()` function,
  `switchLang()`, `applyStaticI18n()`, converted all string literals to `t()` calls,
  added `renderDynamic()` wrapper for language-switch re-rendering

---

## [v2.0] — 2026-05-01 · Editorial Redesign

### Vision
Move beyond the streamlit-default look. Adopt institutional / editorial
design language: large serif chapter numbers, drop caps, pull-quotes,
auto-generated findings, custom-built composite score (no Plotly indicator),
chart builder, glossary expander.

### Design Reference Study
Studied https://us-macro.streamlit.app/ as the user-supplied reference.
Adopted: sidebar-author pattern, related-research block, multi-select chart
builder, frequency selector, collapsible glossary, featured cards, citation.
Deviated: editorial chapter numbering in serif italic, drop-cap hero, custom
HTML score card (no Plotly indicator), chip-style toggles, off-white paper
palette over dark Streamlit, three-font system (Source Serif 4 + Inter +
JetBrains Mono), pull-quote callouts, method-box formula blocks, auto-
generated findings prose, sticky branded top bar.

**Full design rationale:** see `REFERENCE_STUDY.md` — read this before any
visual edit so we don't accidentally regress to "Streamlit demo" look.

### Added
- **Sticky top bar** with brand mark, live composite-score readout, EN/中 toggle, action buttons
- **Custom composite score card** with animated counter + zone bar marker
- **12-tile KPI panel** with auto-hide for N/A values
- **Editorial chapter format** for Layer 01/02/03 + ∑ Synthesis + ⊞ Builder + ⊕ Glossary + ↓ Data
- **Auto-generated Findings** lists per chapter, written from snapshot data
- **Variable Glossary** (`<details>` expander) — 31 fields × unit / source / definition
- **Chart Builder** — multi-select 16 fields, D/W/M frequency aggregation, live Plotly
- **Featured Research** placeholder cards (3 slots)
- **Citation block** auto-filled
- **Data limitation banners** that explicitly call out USD/CNY=fix proxy and CNH=missing
- **Loader** with branded SD monogram + pulsing animation

### Changed
- Color palette: paper off-white (`#faf8f5`) + ink (`#0c0a09`) + ochre accent (`#a16207`)
- Typography: Source Serif 4 for display, Inter for body, JetBrains Mono for numbers
- Type scale: H1 → 36-52px responsive, H2 → 40px serif, body 15px
- Sidebar reorganised: author → contents → papers → lineage → zones
- All charts use minimal Tufte-style grid, low-opacity fills

### Author / Paper Placeholders
The following slots in `web/index.html` are awaiting user content:
- `#author-name`, `#author-role`, `#author-bio` — sidebar self-introduction
- `#author-linkedin`, `#author-email`, `#author-cv` — author links
- `#paper-1`, `#paper-2`, `#paper-3` — sidebar related-research cards
- `#featured` section — 3 footer paper cards (title / desc / link)
- `#citation-block` — citation format template

### Snapshot
Pre-edit state saved to `history/v1.5-multivariate/` (HTML + JS + JSON).

### Files Touched
- `web/index.html` — full rewrite
- `web/dashboard.js` — full rewrite to support new structure

---

## [v1.5] — 2026-05-01 · Multivariate OLS + DXY

### Vision
Address user's "三个补齐" feedback:
1. Layer 1: honest downgrade — explicitly label "Unhedged Raw Carry"
2. Layer 2: add DXY as second regressor (multivariate OLS)
3. Layer 3: add DXY overnight adjustment to fixing bias

### Added
- `fetch_dxy()` — multi-source DXY: yfinance → akshare → **FRED CSV `DTWEXBGS`** fallback
- `reg_beta_spread`, `reg_beta_dxy`, `reg_r2` — multivariate OLS via `np.linalg.lstsq`
- `reg_predicted_uni`, `reg_residual_uni` — kept legacy single-var for comparison
- `alpha_cny_dxy` — rolling 252d β of CNY ret on DXY ret (CIP/DXY beta)
- `expected_fix` — `anchor × (1 + α × ΔDXY_overnight)`
- `fixing_bias` (DXY-adjusted) + `fixing_bias_raw` (legacy) coexisting
- `carry_pct_rank_2y` — 504-day rolling percentile in addition to 1Y

### Calibrated Values (sanity check)
- α (CNY/DXY) = 0.318 → in textbook 0.3–0.5 range ✓
- β₂ (DXY) = 0.0736 → CNY weakens 7.4 pips per 1pt DXY rise ✓
- R² = 46.1% over 252d window
- β₁ (Spread) = -0.033 (multicollinearity artefact, documented)

### Snapshot
Pre-edit state saved to `history/v1.0-mvp/` (HTML + JS + JSON).

### Files Touched
- `data_fetcher.py` — added DXY pipeline + akshare FX fallback
- `analytics.py` — Layer 2 multivariate OLS, Layer 3 DXY adjustment
- `build.py` — exports new fields
- `web/index.html` + `web/dashboard.js` — surfaced new metrics

---

## [v1.0] — 2026-05-01 · MVP

### Vision
Initial three-layer USD/CNY pressure tracker. Streamlit app first, then
ported to static HTML for hosting flexibility.

### Added
- Layer 1: Raw carry + percentile rank
- Layer 2: CIP fair value + single-variable OLS regression
- Layer 3: PBOC fixing bias vs prev close (no DXY adjustment)
- Composite score (weighted average, 0-100)
- 5 pressure zones (Low / Moderate / Elevated / High / Extreme)
- Static HTML/CSS/JS dashboard
- Build pipeline: `python build.py` → `web/data.json`
- akshare for CN bonds + PBOC fixing
- yfinance attempted for FX (SSL failure on user's network)

### Known Limits at v1.0
- yfinance SSL failure on user's network → no live FX data
- Bond yield columns positional (akshare schema-fragile)
- Hedged carry uncomputable without forward quotes
- No DXY (added in v1.5)

---

## How to Snapshot Before Future Edits

Run from project root:

```bash
python tools/snapshot.py "v3.1-next"
```

This copies the current `web/`, `analytics.py`, `data_fetcher.py`, `build.py`
into `history/<tag>/` with a timestamp. See `tools/snapshot.py`.
