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

## ⭐ Phase D · v3.5 / v3.6 — Verdict → Trading Workbench
**This is the new highest-priority queue. Phase A is shipped (v3.2). Phase B
(Macro Backdrop) and Phase C (Working Paper) remain open but rank LOWER than
Phase D items.**

After v3.4.0 shipped the Verdict Card + Policy Stance Card + Integrity Audit,
the user's review surfaced a clear gap: the dashboard now answers *"is this
trade on today?"* but doesn't answer the four follow-on questions a real
carry trader asks before sizing a position:

1. *"Has this signal historically worked? What's the Sharpe?"* → **D.1 Backtest**
2. *"How close am I to the verdict flipping?"* → **D.2 Sensitivity**
3. *"How long does this PBOC stance usually last?"* → **D.3 Stance persistence**
4. *"Does this hold for me, not just for an institutional desk?"* → **D.4 Retail toggle**

The first two are P0 — they convert the site from "signal panel" to
"trading workbench". The third and fourth are P1.

> Hard rule for Cursor: when working on Phase D, the existing v3.4.0
> verdict + stance + integrity infrastructure must NOT be removed or
> reshaped. New work additively bolts onto `data.json` and the UI.

### D.1 — Verdict Backtest (P0 · ~3 hours)
**File:** `analytics.py` new function `backtest_verdict()`,
`build.py` payload key `backtest`, `docs/dashboard.js` new chart.

**Goal:** prove the verdict signal has historical edge. Reproduce the
v3.4.0 `interpret_carry_verdict()` decision over the full historical
window (~2 years) and compute a backtest P&L curve.

**Method:**
```python
def backtest_verdict(df: pd.DataFrame) -> dict:
    # For each historical date with full inputs, recompute the verdict.
    # Position rule: if verdict == 'yes', long carry (notional 1.0);
    #                if verdict == 'marginal', size 0.5;
    #                if verdict == 'no' or 'unknown', flat.
    # Daily P&L: change in hedged_carry_proxy × position size, scaled
    #            from %/year to %/day (÷ 252).
    # Cumulative P&L = compounded daily returns.
    # Stats: total return, Sharpe (annualised), max drawdown, hit rate
    #        (fraction of long days that closed positive).
    # Benchmark: passive long USD/CNY (no carry overlay).
```
Returns:
```python
{
  "dates":       [...],
  "verdict":     [...],     # 'yes' / 'marginal' / 'no' per day
  "position":    [...],     # 1.0 / 0.5 / 0.0
  "daily_pnl":   [...],
  "cumulative":  [...],     # cumulative product of (1 + daily_pnl)
  "benchmark":   [...],     # passive long
  "stats": {
    "total_return": 0.034, "sharpe": 0.81, "max_dd": -0.032,
    "hit_rate": 0.62, "days_long": 187, "days_flat": 130,
  }
}
```

**Dashboard surfacing:** new chart `chart-verdict-backtest` rendered
inside the verdict card (or a small chapter `01.5 · Track Record` right
after Layer 1). Two lines: strategy cumulative vs benchmark. Footer
shows the 4 stats above with i18n labels (`backtest.sharpe`, `.maxdd`,
`.hitrate`, `.days`).

**Acceptance:**
- [ ] `data.json` has top-level `backtest` key with the above schema
- [ ] Chart renders both series; final values match the stats block
- [ ] Sharpe > 0 (sanity — a totally random signal should give ≈ 0)
- [ ] Stats visible in both EN and ZH

### D.2 — Verdict Sensitivity / Flip-Lines (P0 · ~2 hours)
**File:** `analytics.py` new function `compute_flip_lines()`,
`build.py` payload key `flip_lines`, render inside verdict card.

**Goal:** answer *"what spot / forward / yield level would flip the
verdict?"* — a one-line sensitivity panel under the verdict.

**Method:** for each of `usdcny`, `usdcny_fwd_1y`, `us_1y`, `shibor_1y`,
`cnh_hibor_1y`, hold all other inputs constant and binary-search for the
value where `hedged_carry_proxy` crosses ±0.5% (the verdict thresholds).
Return today's value, the flip level, and signed distance.

```python
def compute_flip_lines(snap: dict) -> list[dict]:
    return [
        {"input": "usdcny",        "today": 6.86, "flip_to_yes": 7.06, "flip_to_no": 6.74,
         "label_en": "Spot", "label_zh": "即期"},
        {"input": "usdcny_fwd_1y", "today": 6.67, "flip_to_yes": 6.55, "flip_to_no": 6.74, ...},
        ...
    ]
```

**Dashboard surfacing:** small grid below the verdict chain titled
"Verdict flips when:" listing 3-5 most relevant inputs with current
value + flip level + arrow indicating distance.

```
Verdict flips when:
  Spot      6.86 ─→ 7.06   (need +2.9%)
  Forward   6.67 ─→ 6.55   (need −1.8%)
  UST 1Y    3.72 ─→ 4.20   (need +48 bps)
```

**Acceptance:**
- [ ] `data.json` has `flip_lines` array with at least `usdcny`, `usdcny_fwd_1y`, `us_1y`
- [ ] Flip distances are signed (positive = need to rise, negative = need to fall)
- [ ] If a flip is mathematically unreachable in plausible range,
  display "—" rather than a wild number
- [ ] Renders inside verdict card; survives EN/ZH switch

### D.3 — Policy Stance Persistence (P1 · ~2 hours)
**File:** `analytics.py` new function `compute_stance_persistence()`,
attach into the existing `policy_stance` dict.

**Goal:** historical context for today's PBOC stance. Three pieces:

1. **Average duration** of each of the 5 stances over the full sample
2. **Transition matrix**: from each stance, probability of moving to
   each other stance on the next state change
3. **Today's run length**: how many consecutive days the current
   stance has held

```python
def compute_stance_persistence(df: pd.DataFrame) -> dict:
    # Re-run interpret_policy_stance() over the full history (cheap).
    # Identify "runs" of identical stance values.
    # Compute mean run length per stance.
    # Build 5×5 transition matrix from end-of-run states.
    return {
      "current_run_days": 5,
      "current_stance":   "leaning_defend",
      "avg_duration": {"defending": 14, "weakening": 22, ...},
      "transitions":  {"leaning_defend": {"defending": 0.30, "neutral": 0.55, ...}, ...}
    }
```

**Dashboard surfacing:** small footer line in the stance card:
```
Today is day 5 of MILD DEFENCE.
Historically lasts 8 days · 55% chance reverts to NEUTRAL next.
```

**Acceptance:**
- [ ] `decision.policy_stance.persistence` populated
- [ ] Footer line renders below the existing `stance-reading`
- [ ] If history < 50 days for a given stance, show "—" not garbage

### D.4 — Retail Cost Toggle (P1 · ~2 hours)
**File:** `docs/index.html` new toggle, `docs/dashboard.js` new function
`recomputeVerdictForRetail()`.

**Goal:** acknowledge the brutal reality that retail can't fund at
Shibor. Add a toggle in the verdict card switching between two
scenarios:

| Component | Institutional (current) | Retail |
|---|---:|---:|
| CNY borrow rate | Shibor 1Y (1.47%) | Shibor + 250 bps |
| USD invest rate | UST 1Y (3.72%) | UST − 50 bps |
| FX round-trip | 0 | 30 bps |
| Custody / fees | 0 | 50 bps/yr |

**Spec:**
- Toggle UI: `[Institutional ✓] [Retail ▢]` chip pair, persists to
  `localStorage("verdict_mode")`
- On switch, recompute `hedged_carry_proxy` in the browser (no rebuild
  needed — the math is just `(1+rUS_adj)(F/S) − (1+rCN_adj) − costs`)
- Re-render verdict card with new headline + chain
- Both modes' values shipped in `data.json` (preferred) OR computed in
  JS using the toggled spreads (acceptable, simpler)
- Add a small italic note: `* Retail spreads are illustrative; check your
  actual rates with the broker.`

**Acceptance:**
- [ ] Toggle visible inside verdict card
- [ ] Switching changes the headline number and the chain
- [ ] Persists across page reloads
- [ ] EN / ZH labels for the toggle (`mode.institutional`, `mode.retail`)

### D.5 (P2) — Cross-EM Carry Snapshot
Sidebar mini-table comparing today's USD/CNY hedged carry against
USD/BRL, USD/MXN, USD/TRY (and any others with free FRED + Yahoo v8
data). Same `(1+rUS)(F/S) − (1+rEM)` formula. Frame as "if CNY carry
isn't on, what is?"

Sources:
- BRL: FRED `DEXBZUS` (spot), Yahoo v8 `BRLUSD=X` for forward proxy
- MXN: FRED `DEXMXUS`, Banxico policy rate, Yahoo `MXN=X`
- TRY: Yahoo `TRY=X`, TCMB policy rate

Each row colour-coded YES/MARGINAL/NO using the same -0.5/+0.5 cutoffs.

### D.6 (P2) — Carry / Vol Information Ratio
Add `usdcny_implied_vol_1y` field. Free source candidates: Yahoo v8
options chain for USDCNH spot ETF; or compute realised vol from spot
history as a free proxy. New KPI `carry_per_vol = hedged / vol`. Useful
because -0.5% in 1% vol world ≠ -0.5% in 5% vol world.

### D.7 (P3) — Triggered Email/Webhook Alerts
GitHub Actions step that compares today's snapshot vs yesterday's.
Triggers (configurable):
- Verdict transitions across YES/MARGINAL/NO boundaries
- Composite score crosses 75
- CNH funding stress > +2%
- Policy stance changes

Output: hit a user-provided webhook URL stored in GitHub Secrets
(`ALERT_WEBHOOK_URL`). User can wire to email, Telegram, Discord, etc.

### D.8 (P3) — Mobile Sticky Verdict Header
On scroll past the hero, sticky-pin a thin 28px-tall bar at top showing
current verdict (one word + colour stripe) so the user always knows the
answer regardless of scroll position. Hide on >900px (desktop already
shows topbar).

### Phase D acceptance summary
- [x] D.1 Backtest chart + stats live (P0) — shipped **v3.5.0**
- [x] D.2 Flip-lines panel under verdict (P0) — shipped **v3.5.0**
- [ ] D.3 Stance persistence one-liner in stance card (P1)
- [ ] D.4 Retail toggle in verdict card (P1)
- [x] CHANGELOG `[v3.5.0]` covering D.1+D.2 — done; `[v3.6.0]` for D.3+D.4 next
- [x] Cache-bust `?v=3.5.0` for v3.5.0 release (`?v=3.6.0` with v3.6.0)
- [x] Snapshot before v3.5.0: `history/v3.4-pre-backtest/` — done · `history/v3.5-pre-stance-persistence/` before v3.6.0

### What NOT to do (Phase D guardrails)
- Don't remove the existing verdict / stance / integrity cards. Add
  detail INSIDE them, don't replace them.
- Don't open Phase B (Macro Backdrop) until Phase D is fully done.
  Phase B was a pre-v3.4 plan; user feedback redirected priorities.
- Don't add paid data sources. If a feature needs Bloomberg/Reuters,
  document it in the relevant entry as "deferred to paid tier" and skip.
- Don't break the i18n symmetry. Every new key needs both EN and ZH.

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
