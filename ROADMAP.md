# Roadmap — Beyond v3.1

> **For Cursor:** this is the forward-looking work order. Three phases,
> ordered by ROI. Each phase has acceptance criteria; mark items `[x]`
> as you finish them and append a CHANGELOG entry when a phase ships.
> Always run `python tools/snapshot.py "vX.Y-pre-<tag>"` before starting.

## Why this exists — the critique that drove it

A user-supplied review compared this tracker to Anders Staxen's
[us-macro.streamlit.app](https://us-macro.streamlit.app/) and called us
out on four things. Two of those four are **wrong** (the reviewer
clearly didn't read v3.x carefully — we DO compute volatility,
percentile rank, fix-vs-market deviation, and CIP fair-value gaps).
But two are **right**:

1. **Production tool nature** — Anders gives you `.ipynb` + `.xlsx`
   downloads so you can take the data home and run your own
   regressions. We only ship CSV and `data.json`.
2. **Macro context** — Anders surfaces 49 macro indicators. We focus
   tightly on USD/CNY mechanics and don't help users answer *"why is
   the spread widening today — Fed taper or China credit?"*.

This roadmap closes both gaps without diluting the tracker's
three-layer thesis.

---

## Phase A · v3.2 — Authority + Production-Tool Polish
**Effort: half a day · Risk: low · ROI: very high**

The cheapest way to neutralise the "GitHub demo" perception. No model
changes; pure surfacing + export improvements.

### A.1 — FRED code transparency in the glossary
**File:** `docs/dashboard.js` → `GLOSSARY_DEFS` (around line ~660-690)

Today the glossary table is `[Field, Unit, Source, Definition]`. Add a
fifth column **`Source Code`** that for FRED-sourced fields shows the
official series ID *as a hyperlink*:

| Field | FRED code | Hyperlink target |
|---|---|---|
| `dxy` | `DTWEXBGS` | `https://fred.stlouisfed.org/series/DTWEXBGS` |
| `us_1y` | `DGS1` | `https://fred.stlouisfed.org/series/DGS1` |
| `us_2y` | `DGS2`* | `https://fred.stlouisfed.org/series/DGS2` |

\* note: `us_2y` is currently fetched from akshare `bond_zh_us_rate`, not FRED.
For symmetry, add a second source: try yfinance first, fall back to
FRED `DGS2` (no auth, same pattern as `DGS1`). That way the badge isn't
a lie.

For akshare-sourced fields, link the akshare function docstring on
github.com/akfamily/akshare. For Eastmoney, link the API doc.

**Glossary table CSS:** add column to `<table class="glossary-table">`
in `index.html` line ~1745 (`#glossary-table` → header row gets a 5th
`<th>`). Update i18n: `gloss.col.code` (EN: "Source Code", ZH: "数据代码").

**Acceptance:** every fetched series has a clickable code badge that
opens the canonical source page.

### A.2 — Excel export
**File:** `build.py` and `requirements.txt`

Add `openpyxl` to requirements. After `data.json` is written, also
write `docs/usdcny_tracker.xlsx` with three sheets:

- **`series`** — full time-series, every column from the JSON `series`
  array
- **`snapshot`** — single row, every key from `snapshot` dict
- **`methodology`** — three rows for Layer 1/2/3, each with the formula
  string from `analytics.py` docstrings (lifted programmatically)

Surface the download in the existing `data` chapter (`docs/index.html`
~line 1768): add a third button next to the CSV / JSON ones:
`<a class="dl-btn ghost" href="usdcny_tracker.xlsx" download>↓ Excel
(.xlsx)</a>`.

i18n: add `data.xlsx` key both EN ("↓ Download Excel") and ZH
("↓ 下载 Excel 工作簿").

**Acceptance:** clicking the Excel button downloads a file that opens
cleanly in Excel/Numbers, with three sheets, headers in row 1, dates
in `YYYY-MM-DD`.

### A.3 — Auto-generated replication notebook
**New file:** `tools/build_notebook.py` (called from `build.py`)

Use `nbformat` to generate `docs/usdcny_tracker_replication.ipynb` on
each build. Five cells:

1. **Markdown** — title, current data date, link to live dashboard,
   citation block (mirror what `#citation-block` shows)
2. **Code** — `pip install pandas numpy requests` + import
3. **Code** — fetch the live `data.json` from the deployed site
   (`SITE_PUBLIC_ORIGIN` in `config.py`, or env `TRACKER_SITE_ORIGIN`), so
   the notebook always pulls the latest snapshot
4. **Code** — independently re-compute `raw_carry`,
   `hedged_carry_proxy`, `cip_deviation`, `fixing_bias` from the raw
   series (NOT just trust the JSON). This proves nothing is being
   hidden.
5. **Code** — three diagnostic plots: composite score time series,
   regression residual histogram, fixing-bias rolling mean

Surface as another button in the `data` chapter. i18n key:
`data.ipynb`.

**Acceptance:** `jupyter nbconvert --execute usdcny_tracker_replication.ipynb`
runs end-to-end without errors against the live JSON.

### A.4 — Source-Code badges on KPI tiles (optional polish)
For each KPI tile that wraps a single FRED-or-akshare field, add a tiny
mono-font code badge in the tile meta line (e.g. `DGS1`, `DTWEXBGS`).
Builds on the v3.0 KPI panel.

### Phase A acceptance summary
- [x] Every FRED field has a clickable FRED code
- [x] `docs/usdcny_tracker.xlsx` builds and downloads
- [x] `docs/usdcny_tracker_replication.ipynb` builds, executes
  end-to-end, and reproduces three layer values within rounding
- [x] Cache-bust: `?v=3.2` in `<script>` tag and footer
- [x] CHANGELOG entry titled `[v3.2] — Authority & Export Layer`
- [x] Snapshot taken to `history/v3.1-pre-export/` before starting

---

## Phase B · v4.0 — Macro Backdrop Layer
**Effort: 1–2 days · Risk: medium · ROI: high**

Add a *zoom-out* layer that explains **why** the three-layer signals
move. This kills the "single-dimension" critique definitively.

### B.1 — New data sources
**File:** `data_fetcher.py`

Add fetchers (lazy `import akshare as ak` inside each — see v3.1
gotcha note in CHANGELOG):

| Field | Source | Function |
|---|---|---|
| `fed_balance_sheet` | FRED `WALCL` | `fetch_fed_walcl()` (FRED CSV) |
| `fed_rrp` | FRED `RRPONTSYD` | `fetch_fed_rrp()` (FRED CSV) |
| `fed_reserves` | FRED `WRESBAL` | `fetch_fed_reserves()` (FRED CSV) |
| `vix` | FRED `VIXCLS` | `fetch_vix()` (FRED CSV) |
| `cn_social_financing_yoy` | akshare `macro_china_shrzgm` | `fetch_cn_credit_impulse()` |
| `cn_m2_yoy` | akshare `macro_china_m2_yearly` | `fetch_cn_m2()` |
| `cn_policy_rate` | akshare `rate_interbank` indicator='隔夜' | `fetch_cn_overnight()` |

All FRED fetchers reuse the `fetch_us_1y()` pattern (no auth, just
`pd.read_csv` of `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>`).

Wire into `get_master_data()` as forward-fill columns. Add coverage
keys to the `quality` dict.

### B.2 — Layer 0 analytics
**File:** `analytics.py` — add a `calc_macro_backdrop()` function

Compute:
- `usd_liquidity_index` = z-score(`fed_balance_sheet`) − z-score(`fed_rrp`)
  · 252d window
  → high = USD flowing into markets, low = USD pulled out
- `cn_credit_impulse` = 12m change of `cn_social_financing_yoy`
- `risk_appetite` = − z-score(`vix`, 252d)
  → positive = risk-on, negative = risk-off
- `macro_pressure` = standardised composite of the three above
  (0-100 like the other layer scores, but represents external
  macro stress on USD/CNY)

Don't fold into the existing 0-100 composite (that's the *internal*
pressure on the PBOC line). Surface separately in a new chapter.

### B.3 — New chapter `00 · Macro Backdrop`
**File:** `docs/index.html` — insert before `chapter-01`

Same editorial format as the other chapters (chapter num `00` in serif
italic, eyebrow tag, title, lead, method-box, charts, findings).

Charts (per Tufte minimalism — small multiples, low chrome):
1. Fed liquidity stack (WALCL, RRP, Reserves)
2. China credit impulse vs USD/CNY (dual-axis overlay)
3. VIX vs composite_score (correlation lens)

The point of the dual-axis charts is **answering "why"** — let the
user *see* that the spread widened the same week the Fed reserve
balance dropped. This is the deliberate response to "它无法告诉你是
因为美债收益率上行，还是因为国内信贷不及预期".

### B.4 — Builder upgrade: dual-axis support
**File:** `docs/dashboard.js` → `renderBuilder()`

Currently the chart builder picks N series and stacks them on one
y-axis (auto-scaled). Add a "right axis" toggle per series so users
can overlay e.g. `usdcny` (CNY scale) and `cn_social_financing_yoy`
(% scale) without one swamping the other.

### B.5 — i18n + glossary
- ~20 new keys × 2 langs (EN / ZH)
- Glossary gets ~7 new rows for the macro fields
- Each macro row links to its FRED page (Phase A.1 must ship first)

### Phase B acceptance summary
- [ ] All 7 new macro fields populate ≥ 80% in `quality` dict
- [ ] Chapter 00 renders, all charts populate
- [ ] Dual-axis builder works (verify visually with a mismatched-scale
  pair)
- [ ] i18n symmetric (EN keys = ZH keys)
- [ ] CHANGELOG entry titled `[v4.0] — Macro Backdrop`
- [ ] Snapshot to `history/v3.2-pre-macro/`

---

## Phase C · v5.0 — Working Paper + Academic Framing
**Effort: 1–2 weeks (mostly writing) · Risk: low · ROI: highest for
academic credibility**

This is **NOT for Cursor.** It's for 魏来 personally — your SIPA
training is the differentiator here. Cursor can scaffold the LaTeX
template but the content has to come from you.

### C.1 — Companion working paper
**Suggested target:** 8–12 pages, formatted as an SSRN/working-paper
PDF. Sections:

1. Abstract (½ page)
2. Three-layer pressure framework (cite BIS / IMF / Giacomelli &
   Pesenti)
3. Methodology (the three formulas, derivations, hedge-carry proxy
   derivation)
4. Empirical calibration (today's snapshot, historical episodes —
   Aug 2015 devaluation, 2018 trade-war, 2022 PBOC defence)
5. Limitations (CNH gap, FRED TWI vs ICE DXY, hedged carry vs true
   swap-locked P&L)
6. Conclusion + future work

Drop the PDF into `docs/paper.pdf` and link from:
- The `#featured` section's first card
- A new sidebar entry "Companion Paper"
- The citation block

### C.2 — Academic citation lineage
Replace the placeholder paper cards in the sidebar with three real
references:
- A BIS Quarterly Review piece on cross-currency basis
- An IMF working paper on capital flow diagnostics
- Either Giacomelli & Pesenti (your namesake citation) or a more
  recent successor

### C.3 — Submit to a venue
Once the paper exists, submit to:
- SSRN (free, fast, gives a citable handle)
- Optionally: Columbia SIPA student journal, or post on LinkedIn for
  professional reach

This is what turns the project from "GitHub repo with a dashboard"
into "research artefact".

### Phase C acceptance summary
- [ ] `docs/paper.pdf` exists and is linked from 3 places in the site
- [ ] Sidebar paper cards reference real citations, not placeholders
- [ ] CHANGELOG entry titled `[v5.0] — Companion Paper Released`
- [ ] (Optional) SSRN submission ID added to the citation block

---

## Cross-cutting reminders for Cursor

1. **Snapshot before edits.** Always: `python tools/snapshot.py "vX.Y-pre-<tag>"`.
2. **Cache-bust on every JS edit.** Bump both:
   - `<script src="dashboard.js?v=X.Y">` in `docs/index.html`
   - Header version comment in `docs/dashboard.js`
   - Footer version label in `docs/index.html`
3. **i18n symmetry is enforced.** After every dashboard edit run:
   ```bash
   python -c "import re; ..." # the verifier from v3.0.1 changelog
   ```
   `EN keys = ZH keys` must hold. Do not commit asymmetric.
4. **Lazy import akshare.** Inside every new `data_fetcher.py`
   function: `import akshare as ak` as the first line of the function
   body. Top-level `ak.` references will silently fail and `bare except`
   will hide the NameError (this bit us in v3.1).
5. **Append BUILD_LOG.md is automatic.** Don't manually edit it.
6. **README's 当前版本 banner** at top must stay accurate. Bump on
   every minor release.
7. **Honesty over polish.** If a data source fails, surface a "Data
   note" banner on the page. Never silently substitute proxies (the
   v3.0 fix-as-spot bug taught us this).

---

## Quick decision tree for Cursor

```
Did the user ask for a feature in this roadmap?
├── Yes → start with the phase that matches; follow acceptance criteria
├── No, asked for something not here → check if it conflicts with
│   the "Future direction principle" in REFERENCE_STUDY.md §7
│   ("don't make us look like a Streamlit demo")
└── Unsure → bias toward Phase A items first (lowest risk)
```

---

*Last revised: 2026-05-01 by Claude (after v3.1 ship).*
*If this file diverges from CHANGELOG.md, CHANGELOG wins for past;
ROADMAP wins for future.*
