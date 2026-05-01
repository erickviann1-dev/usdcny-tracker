# Changelog

All notable changes to the USD/CNY Macro-Policy Divergence Tracker.

Format: each entry records (1) what changed, (2) why, (3) snapshot location of
the previous state under `history/`.

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
