# Changelog

All notable changes to the USD/CNY Macro-Policy Divergence Tracker.

Format: each entry records (1) what changed, (2) why, (3) snapshot location of
the previous state under `history/`.

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
