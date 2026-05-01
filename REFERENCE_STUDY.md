# Reference Study — us-macro.streamlit.app

**Date analysed:** 2026-05-01
**Reference URL:** https://us-macro.streamlit.app/
**Author of reference:** Anders Staxen (Columbia University grad student, FX & quant)

This document captures what I learned from the reference dashboard, what we
**adopted**, and where we deliberately **deviated to surpass** it. Future edits
should preserve the "surpass" decisions unless there's a strong reason to
revert.

---

## 1. What the reference does well

| Element | Implementation | Why it works |
|---|---|---|
| **Author/credibility sidebar** | Bio paragraph + LinkedIn button | Establishes the person behind the work — turns dashboard into a "publication" |
| **Related Research block** | Short paragraph linking to companion paper + Claude Artifact | Embeds the dashboard in a larger research narrative |
| **Features list with emoji bullets** | 📊 Table view · 📁 Excel · 🐍 Python · 📓 Notebook | 30-second elevator pitch of what the visitor can take away |
| **Right-aligned download links** | Excel / Python / Notebook side-by-side with features | One-click access to all artefacts |
| **Collapsible variable expander** | "Click to see full list of variables" | Keeps page clean, on-demand depth |
| **Frequency selector** | Dropdown switches table aggregation | Adapts data resolution to user's mental model |
| **Multi-select chart builder** | Choose any N variables → custom plot | Exploratory analysis without writing code |
| **Featured cards in footer** | Streamlit-community pinned dashboards | Social/community proof |
| **Dark theme + Streamlit consistency** | Default Streamlit dark | Professional but generic — "polished demo" feel |

## 2. What the reference does not do (gaps we exploited)

| Gap | Impact |
|---|---|
| **No editorial typography** — generic Streamlit headings | The page feels like a "data widget" not a "research artefact" |
| **No narrative scaffolding** — pure tabular indicator dump | Visitor has to construct meaning themselves; no story |
| **No methodology surfacing** — no formulas, no derivations | Looks like a data viewer, not a quant research product |
| **No author voice** — bio is bio, content is mechanical | Misses the chance to demonstrate analytical sophistication |
| **No live commentary** — values shown but not interpreted | Reader can't tell what "good" or "bad" looks like |
| **Dark theme = no editorial gravitas** | FT / Economist / BIS quarterly all use light paper aesthetics |
| **No design hierarchy** — every section equal weight | Hero / chapter / footer all visually similar |
| **No animation / motion** — static page | Feels static; no sense of "live data" |
| **English-only** | No CJK audience support — limits reach in the market this tracks |

## 3. Design decisions we made to surpass it

### 3.1 Editorial > Dashboard
- **Adopted:** sidebar with author + related research + nav
- **Deviated:** sidebar uses serif typography, hairline rules, paper card styling
- **Surpassed:** added "Methodology Lineage" block (BIS / IMF / Giacomelli &
  Pesenti) — signals the work has academic blood, not just a side project
- **Surpassed:** placeholder slots for 3 papers, with metadata fields
  (paper-meta / paper-title / paper-authors) — turns the sidebar into a mini-CV

### 3.2 Chapter format > Tab format
- **Reference:** flat sections separated by H2 headings
- **Ours:** each layer is a numbered chapter (`01`, `02`, `03`, `∑`, `⊞`, `⊕`,
  `↓`) rendered in 88px italic Source Serif 4 — borrows from FT / NYTimes
  longform layout
- Each chapter has: eyebrow tag → serif title → lead paragraph → method box
  → charts → auto-generated Findings list

### 3.3 Hero > Page header
- **Reference:** title + paragraph
- **Ours:** "AS OF DATE" overline → large serif statement headline ("Quantifying
  the battle between *carry-trade pressure* and *PBOC policy intent*") → drop-
  cap lead paragraph (FT-style)
- **Surpassed:** custom-built composite score card (no Plotly indicator) with
  animated easing counter, zone bar with marker triangle, status pill that
  recolours by zone

### 3.4 Live commentary
- **Reference:** values dump
- **Ours:** every chapter ends with auto-generated `<ul class="findings">` —
  4-5 bullets written from the snapshot in plain English. Example:
  > Multivariate fit yields β_DXY = 0.0736 — every 1-point rise in the broad
  > dollar predicts 0.0736 CNY of USD/CNY appreciation.

### 3.5 Pull-quote callout
- **Reference:** none
- **Ours:** Layer 02 has a serif italic pull-quote with citation. Used
  sparingly to mark thesis statements.

### 3.6 Method box with formula block
- **Reference:** prose only
- **Ours:** every chapter has a `.method-box` containing a JetBrains Mono
  formula block on `var(--bg-tint)` with ochre accent border. Quant-paper
  aesthetic.

### 3.7 Color palette
- **Reference:** Streamlit dark
- **Ours:** off-white paper (`#faf8f5`), pure white cards, ink black
  (`#0c0a09`), ochre highlights (`#a16207`), institutional navy (`#1e3a5f`).
  The vibe references Financial Times broadsheet, BIS Quarterly Review, and
  Two Sigma Venn — not Streamlit Cloud.

### 3.8 Typography stack
- **Reference:** Streamlit's default sans
- **Ours:** Source Serif 4 (display + chapter numbers + hero + paper titles),
  Inter (body), JetBrains Mono (numbers + formulas) — three-font system used
  consistently for hierarchy

### 3.9 Score visualisation
- **Reference:** would have been a Plotly indicator (we did this in v1.5)
- **Ours v2.0:** custom HTML/CSS score card with:
  - 96px display-serif number
  - Animated counter (1.1s cubic-bezier ease-out on page load)
  - Status pill (Low / Moderate / Elevated / High / Extreme + Tag)
  - 5-zone horizontal bar with sliding triangle marker
  - Top-edge accent stripe colored by zone
  Avoids Plotly's generic dial look. Looks bespoke.

### 3.10 Chart Builder
- **Reference:** good — multi-select + frequency
- **Ours:** chip-style checkbox toggles (pill-shaped, dark-on-active), 16
  fields, daily/weekly/monthly aggregation, live re-render. Same idea, more
  polished interaction.

### 3.11 Glossary
- **Reference:** "Click to see the full list of variables" expander
- **Ours:** `<details>` with custom `+/−` indicator that morphs on open. Inside
  is a 4-column table (Field / Unit / Source / Definition) styled as a research-
  paper data appendix.

### 3.12 Featured / Citation
- **Reference:** Featured Streamlit-community cards
- **Ours:**
  - 3 placeholder cards with greek-letter thumbnail (α / β / γ in 56px serif)
  - Each card: tag (Working Paper / Note / Letter) + title + description
  - **Plus a Citation block** at the end — JetBrains Mono pre-formatted text
    "[Author] (2026). USD/CNY Macro-Policy Divergence Tracker. Online dashboard.
    Accessed [date]." Auto-fills year and date.
  - Researchers know: a dashboard with a how-to-cite is a serious dashboard.

### 3.13 Sticky top bar
- **Reference:** none (Streamlit's chrome)
- **Ours:** custom 14px-tall sticky bar with:
  - Left: "SD" monogram + tracker name + version
  - Right: live composite-score readout (recolours by zone) + EN/中 toggle +
    Download button + "Begin →" CTA jumping to chapter 01
  - Backdrop-filter blur for glass effect on scroll

### 3.14 Loader
- **Reference:** Streamlit's standard "Running…" indicator
- **Ours:** full-screen branded loader with pulsing 48px SD monogram + "LOADING
  MARKET DATA…" caption. Fades out on data ready.

### 3.15 Bilingual i18n (v3.0)
- **Reference:** English only
- **Ours:** full Chinese/English bilingual support:
  - Fixed-position language toggle (EN / 中文) in top-right corner
  - `localStorage` persistence — remembers user's language across sessions
  - **Every user-visible string** has EN and ZH variants (~150 keys per language)
  - Static HTML text via `data-i18n` / `data-i18n-html` attribute scanning
  - Dynamic JS content (KPIs, alerts, charts, narrative, stats) via `t(key)` function
  - Chart titles, axis labels, trace names, zone labels all translated
  - Language switch triggers full re-render including all Plotly charts
  - **Why this matters for surpassing the reference:** this tracker analyses the
    USD/CNY market — its natural audience includes Chinese-speaking macro
    researchers, PBOC watchers, and onshore fund managers. English-only is a
    self-imposed ceiling on reach. The reference dashboard (US macro focus) can
    get away with English-only; we cannot.

### 3.16 Data Integrity Transparency (v3.0)
- **Reference:** no data-quality disclosure
- **Ours:**
  - Quality badges at the top (each source shows coverage %)
  - Explicit "Data Integrity Notice" alert when onshore spot is missing
  - **"No fake data" principle**: missing market data stays missing; never silently
    replaced with fixing proxy. This is a quant-credibility decision — seasoned
    researchers will immediately notice if `fixing_bias ≈ 0` across all dates and
    conclude the model is broken. Better to show N/A with an explanation.
  - β₁ negative-value annotation: when the spread coefficient goes negative
    (multicollinearity artefact), a yellow callout appears explaining why, rather
    than hiding a confusing number. This signals analytical maturity.

---

## 4. What we deliberately kept

- **Sidebar position** (left, sticky, scrollable) — proven UX pattern
- **Author placeholder pattern** — easy for user to fill in
- **Multi-select + frequency chart builder** — perfect for exploration
- **Collapsible glossary** — clean by default, deep on demand
- **Citation/featured footer** — establishes scholarly framing

## 5. What we explicitly didn't copy

- ❌ Streamlit-default look — feels like a tutorial demo
- ❌ Dark theme — contradicts editorial gravitas
- ❌ Emoji-driven feature list — too playful for institutional research
- ❌ Generic dropdown components — built our own pill toggles
- ❌ Plotly indicator gauges — built custom score card
- ❌ Equal-weight section spacing — used asymmetric grid + hero hierarchy
- ❌ English-only — limited reach for a CNY-focused product

## 6. Decisions left as placeholders for the user

- Brand monogram (currently "SD" — change in `index.html` 2 places + `dashboard.js` 0 places)
- Author bio + name + role + LinkedIn/email/CV
- 3 sidebar paper cards
- 3 featured-research cards
- Citation author name and year
- Optional: replace FRED Trade-Weighted with true ICE DXY when available

## 7. Future direction principle

If a feature would make us look more like a Streamlit demo and less like a
BIS Quarterly Review article, **don't do it**. The deliberate target audience is
quant researchers, FX strategists, and policy economists — people who read the
BIS, the IMF Working Paper series, and Two Sigma Venn. Optimise for their taste.

Bilingual support is not a "nice to have" — it's a **reach multiplier**. The
tracker analyses the most politically sensitive exchange rate in the world. Its
audience is split between English-dominant (sell-side, global macro) and
Chinese-dominant (buy-side onshore, PBOC watchers, academic). Serve both.
