"""
USD/CNY Macro-Policy Divergence Tracker
2-Year Focus | Three-Layer Analysis

Layer 1 — Carry Trade Feasibility
Layer 2 — CIP Mispricing & Regression Residuals
Layer 3 — PBOC Fixing Bias / Policy Intent
"""

import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import io

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="USD/CNY Policy Divergence Tracker",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background-color: #0d1117; }

.kpi-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 8px;
}
.kpi-label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.8px; }
.kpi-value { font-size: 26px; font-weight: 600; color: #f0f6fc; margin: 4px 0 0; }
.kpi-value.bull { color: #22c55e; }
.kpi-value.bear { color: #ef4444; }
.kpi-value.warn { color: #facc15; }

.layer-header {
    font-size: 13px; font-weight: 500; color: #8b949e;
    border-left: 3px solid #60a5fa; padding-left: 10px;
    margin: 20px 0 8px;
    text-transform: uppercase; letter-spacing: 0.6px;
}
.section-divider { border-top: 1px solid #21262d; margin: 24px 0; }

.data-badge {
    display: inline-block;
    padding: 2px 8px; border-radius: 4px; font-size: 10px;
    font-weight: 500; margin: 2px;
}
.badge-ok  { background: #1a3a2a; color: #22c55e; border: 1px solid #22c55e40; }
.badge-est { background: #3a2a1a; color: #f97316; border: 1px solid #f9731640; }
.badge-err { background: #3a1a1a; color: #ef4444; border: 1px solid #ef444440; }
</style>
""", unsafe_allow_html=True)


from data_fetcher import get_master_data
from analytics   import run_full_analysis, latest_snapshot
from charts      import (
    gauge_composite,
    chart_yield_spread,
    chart_carry_pressure,
    chart_regression_residuals,
    chart_cip_deviation,
    chart_fixing_bias,
    chart_fixing_vs_spot,
    chart_composite_trend,
)
from config import (
    RAW_CARRY_ALERT, FIXING_BIAS_ALERT,
    PRESSURE_ZONES,
)


# ═══════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 📡 USD/CNY Tracker")
    st.markdown("**2Y Macro-Policy Divergence**")
    st.markdown("---")

    st.markdown("### ⚙️ Controls")

    refresh = st.button("🔄 Refresh Data", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()

    st.markdown("### 🔔 Alert Thresholds")
    carry_thr = st.slider(
        "Raw Carry Alert (%)", 0.5, 5.0, RAW_CARRY_ALERT, 0.1,
        help="Flag when US−CN 2Y spread exceeds this value"
    )
    bias_thr = st.slider(
        "Fixing Bias Alert (pips)", 50, 500, FIXING_BIAS_ALERT, 10,
        help="Flag when PBOC fixing deviates from CNH by this amount"
    )

    st.markdown("### 📊 Layer Weights")
    w1 = st.slider("Layer 1 — Carry",   0.1, 0.6, 0.35, 0.05)
    w2 = st.slider("Layer 2 — Mispr.",  0.1, 0.6, 0.30, 0.05)
    w3 = st.slider("Layer 3 — Policy",  0.1, 0.6, 0.35, 0.05)

    st.markdown("---")
    st.markdown("### 📖 Interpretation Guide")
    for lo, hi, clr, lbl in PRESSURE_ZONES:
        st.markdown(
            f'<span style="color:{clr}">●</span> **{lo}–{hi}**: {lbl}',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown(
        "<span style='color:#8b949e;font-size:11px;'>"
        "Data: akshare (CN bonds, PBOC fixing)<br>"
        "yfinance (USD/CNY, USD/CNH)<br>"
        "Refreshes every 60 min</span>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════
#  LOAD & ANALYSE DATA
# ═══════════════════════════════════════════════════════════════

with st.spinner("Loading market data..."):
    master_df, quality = get_master_data()

if master_df.empty:
    st.error("Failed to load data. Check your internet connection and try refreshing.")
    st.stop()

# Patch composite weights from sidebar
import config as _cfg
_cfg.W_CARRY  = w1 / (w1 + w2 + w3)
_cfg.W_MISPR  = w2 / (w1 + w2 + w3)
_cfg.W_FIXING = w3 / (w1 + w2 + w3)

df = run_full_analysis(master_df)
snap = latest_snapshot(df)


# ═══════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════

col_title, col_ts = st.columns([3, 1])
with col_title:
    st.markdown("# USD/CNY Macro-Policy Divergence Tracker")
    st.markdown(
        "Quantifying the battle between **carry trade pressure** "
        "and **PBOC policy intervention** — 2-year tenor focus."
    )
with col_ts:
    st.markdown(f"<br><span style='color:#8b949e'>Last data: **{snap['date']}**</span>",
                unsafe_allow_html=True)

    # Data quality badges
    badge_map = {
        "CN 2Y": quality.get("cn_2y", 0),
        "US 2Y": quality.get("us_2y", 0),
        "CNY":   quality.get("usdcny", 0),
        "CNH":   quality.get("usdcnh", 0),
        "Fix":   quality.get("pboc_fix", 0),
    }
    badges = ""
    for name, q in badge_map.items():
        cls = "badge-ok" if q > 0.8 else "badge-est" if q > 0.3 else "badge-err"
        badges += f'<span class="data-badge {cls}">{name}: {q:.0%}</span>'
    st.markdown(badges, unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  HERO ROW — Gauge + KPI Cards
# ═══════════════════════════════════════════════════════════════

composite_val = float(snap["composite_score"]) if snap["composite_score"] != "N/A" else 50.0
zone_label = next(
    (lbl for lo, hi, _, lbl in PRESSURE_ZONES if lo <= composite_val < hi),
    PRESSURE_ZONES[-1][3]
)

g_col, kpi_col = st.columns([1, 2])

with g_col:
    st.plotly_chart(
        gauge_composite(composite_val, f"Policy Pressure — {zone_label}"),
        use_container_width=True, config={"displayModeBar": False}
    )

with kpi_col:
    r1, r2, r3 = st.columns(3)

    def kpi(col, label, value, cls=""):
        col.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value {cls}">{value}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    carry_v = float(snap["raw_carry"]) if snap["raw_carry"] != "N/A" else 0
    carry_cls = "bear" if carry_v > carry_thr else "bull" if carry_v < 1 else "warn"

    bias_v = float(snap["fixing_bias"]) if snap["fixing_bias"] != "N/A" else 0
    bias_cls = "bull" if bias_v < -bias_thr/10000 else "bear" if bias_v > bias_thr/10000 else ""

    kpi(r1, "USD/CNY Spot",      snap["usdcny"])
    kpi(r2, "USD/CNH Offshore",  snap["usdcnh"])
    kpi(r3, "PBOC Fix",          snap["pboc_fix"])

    r4, r5, r6 = st.columns(3)
    kpi(r4, "US 2Y Yield",       f"{snap['us_2y']}%")
    kpi(r5, "CN 2Y Yield",       f"{snap['cn_2y']}%")
    kpi(r6, "Raw Carry (US−CN)", f"{snap['raw_carry']}%", carry_cls)

    r7, r8, r9 = st.columns(3)
    kpi(r7, "Carry Pctile Rank", f"{snap['carry_pct_rank']}/100")
    kpi(r8, "Fixing Bias (est.)", snap["fixing_bias"], bias_cls)
    kpi(r9, "20d Mean Bias",     snap["bias_20d_mean"])


# ═══════════════════════════════════════════════════════════════
#  ALERTS
# ═══════════════════════════════════════════════════════════════

alerts = []
if snap["raw_carry"] != "N/A" and float(snap["raw_carry"]) > carry_thr:
    alerts.append(
        f"🔴 **Carry Alert**: US−CN 2Y spread = **{snap['raw_carry']}%** "
        f"(threshold: {carry_thr}%). Significant carry trade incentive active."
    )
if snap["fixing_bias"] != "N/A" and abs(float(snap["fixing_bias"])) * 10000 > bias_thr:
    direction = "defending CNY 🟢" if float(snap["fixing_bias"]) < 0 else "allowing weakness 🔴"
    alerts.append(
        f"📌 **Fixing Bias Alert**: PBOC bias = **{float(snap['fixing_bias'])*10000:.0f} pips** — "
        f"{direction}"
    )
if composite_val > 75:
    alerts.append(
        f"⚠️ **High Pressure**: Composite score = **{composite_val:.0f}/100**. "
        f"Multi-layer stress convergence detected."
    )

if alerts:
    with st.container():
        for a in alerts:
            st.warning(a)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  THREE-LAYER TABS
# ═══════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Layer 1 — Carry",
    "🔍 Layer 2 — Mispricing",
    "🏛️ Layer 3 — Policy Intent",
    "📁 Data & Export",
])


# ── Tab 1: Carry ─────────────────────────────────────────────

with tab1:
    st.markdown(
        '<div class="layer-header">Layer 1 — Carry Trade Feasibility</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        **Core question:** Is there a profitable incentive to borrow CNY and invest in USD?

        - **Raw Carry** = US 2Y − CN 2Y yield: the gross yield pickup
        - **Hedged Carry** ≈ Raw Carry − Swap Cost (= ~0 under CIP; CIP deviation captured in Layer 2)
        - **CNH−CNY Gap**: offshore weakness signals unhedged depreciation pressure
        - High carry + widening CNH gap = **maximum pressure on the PBOC defense line**
        """
    )

    st.plotly_chart(chart_yield_spread(df), use_container_width=True)
    st.plotly_chart(chart_carry_pressure(df), use_container_width=True)

    # Layer 1 summary table
    l1_cols = [c for c in ["raw_carry","carry_ma20","carry_ma60","carry_ma120",
                            "carry_pct_rank","onoffshore_gap"] if c in df.columns]
    if l1_cols:
        recent = df[l1_cols].tail(60).copy()
        recent.index = recent.index.strftime("%Y-%m-%d")
        st.dataframe(recent.round(4).tail(20), use_container_width=True)


# ── Tab 2: Mispricing ─────────────────────────────────────────

with tab2:
    st.markdown(
        '<div class="layer-header">Layer 2 — CIP Mispricing & Regression Residuals</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        **Core question:** Where *should* USD/CNY be trading given the interest rate differential?

        - **OLS Regression Model**: regress USD/CNY spot on yield spread (rolling 252-day window)
        - **Residual > 0**: CNY weaker than the model predicts → PBOC is "holding a line"
          (spot would normally follow the spread higher, but CNY is being held back)
        - **Residual < 0**: CNY stronger than model → PBOC propping beyond fundamentals,
          or carry trade is driving overshooting appreciation
        - **CIP Fair Value**: interest-rate-parity implied spot path; deviation = arbitrage signal
        """
    )

    c1, c2 = st.columns([2, 1])
    with c1:
        st.plotly_chart(chart_regression_residuals(df), use_container_width=True)
    with c2:
        st.plotly_chart(chart_cip_deviation(df), use_container_width=True)

        # Regression stats
        if "reg_beta" in df.columns and "reg_r2" in df.columns:
            latest_beta = df["reg_beta"].dropna().iloc[-1] if df["reg_beta"].notna().any() else np.nan
            latest_r2   = df["reg_r2"].dropna().iloc[-1]   if df["reg_r2"].notna().any()   else np.nan
            st.markdown("**Latest Regression Stats**")
            st.metric("β (spread sensitivity)", f"{latest_beta:.2f}" if not np.isnan(latest_beta) else "N/A")
            st.metric("R²", f"{latest_r2:.2%}" if not np.isnan(latest_r2) else "N/A")
            st.caption(
                "β ≈ 0.3–0.8 historically (CNY depreciates ~0.5 yuan per 1% spread widening). "
                "High R² suggests model is reliable; falling R² = structural break."
            )


# ── Tab 3: Policy Intent ──────────────────────────────────────

with tab3:
    st.markdown(
        '<div class="layer-header">Layer 3 — PBOC Fixing Bias / Policy Intent Decoder</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        **Core question:** How much political will is PBOC currently deploying?

        - **PBOC Daily Fixing** (中间价): the official midpoint rate set each morning at 09:15
        - **Market Expectation Proxy**: previous day's offshore CNH close (unconstrained market price)
        - **Fixing Bias** = Official Fix − CNH Previous Close:
          - **Negative** (< 0): PBOC set a *stronger* CNY than market → **active defense posture**
          - **Positive** (> 0): PBOC set a *weaker* CNY than market → allowing depreciation / neutral
        - **20-day Cumulative Bias**: if persistently negative → PBOC is drawing a red line
        - **The key insight**: the bigger the negative bias *alongside* rising carry,
          the more unsustainable the defense — a "coiled spring" setup
        """
    )

    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.plotly_chart(chart_fixing_vs_spot(df), use_container_width=True)
        st.plotly_chart(chart_fixing_bias(df), use_container_width=True)
    with col_b:
        st.markdown("**Defense Intensity Monitor**")

        di = df["defense_intensity"].dropna() if "defense_intensity" in df.columns else pd.Series(dtype=float)
        if not di.empty:
            latest_di = di.iloc[-1]
            di_label = (
                "Strong Defense 🟢" if latest_di > 0.01
                else "Neutral ⚪" if abs(latest_di) < 0.005
                else "Allowing Weakness 🔴"
            )
            st.metric("Current Posture", di_label)
            st.metric("Defense Intensity (20d avg bias)", f"{latest_di*10000:+.0f} pips")

        if "bias_20d_mean" in df.columns:
            recent_bias = df[["fixing_bias", "bias_20d_mean", "bias_60d_mean"]].tail(30)
            recent_bias.index = recent_bias.index.strftime("%m-%d")
            st.dataframe((recent_bias * 10000).round(1).rename(columns={
                "fixing_bias": "Daily(pips)",
                "bias_20d_mean": "20d Avg",
                "bias_60d_mean": "60d Avg",
            }), use_container_width=True)

        st.markdown("---")
        st.markdown(
            """
            **Reading the tea leaves:**

            | Scenario | Carry | Bias | Implication |
            |---|---|---|---|
            | Max Tension | High ↑ | Strongly Neg ↓ | PBOC spending reserves to hold; watch for capitulation |
            | Managed Decline | High ↑ | Near Zero | PBOC allowing gradual weakness |
            | Comfortable | Low ↓ | Near Zero | No policy dilemma |
            | CNY Bull | Neg / Low | Pos ↑ | PBOC resisting appreciation |
            """,
            unsafe_allow_html=False,
        )


# ── Tab 4: Data & Export ──────────────────────────────────────

with tab4:
    st.markdown("### 📁 Full Dataset Export")

    export_cols = [c for c in [
        "us_2y", "cn_2y", "yield_spread",
        "usdcny", "usdcnh", "pboc_fix", "onoffshore_gap",
        "raw_carry", "carry_pct_rank",
        "cip_fair_spot", "cip_deviation", "reg_predicted", "reg_residual", "reg_beta", "reg_r2",
        "fixing_bias", "bias_20d_mean", "bias_60d_mean", "defense_intensity",
        "composite_score", "composite_score_smooth",
    ] if c in df.columns]

    export_df = df[export_cols].tail(504).copy()   # 2 years of business days
    export_df.index.name = "date"

    st.dataframe(export_df.round(5), use_container_width=True, height=400)

    col_x1, col_x2 = st.columns(2)
    with col_x1:
        csv = export_df.to_csv().encode("utf-8")
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name=f"usdcny_tracker_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_x2:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            export_df.to_excel(writer, sheet_name="Master Data")
            # Summary sheet
            summary = pd.DataFrame.from_dict(snap, orient="index", columns=["Latest"])
            summary.to_excel(writer, sheet_name="Snapshot")
        st.download_button(
            label="⬇️ Download Excel",
            data=buf.getvalue(),
            file_name=f"usdcny_tracker_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.markdown("---")
    st.markdown("### 📊 Data Quality Report")
    qdf = pd.DataFrame.from_dict(quality, orient="index", columns=["Coverage"])
    qdf["Status"] = qdf["Coverage"].apply(
        lambda x: "✅ Live" if x > 0.8 else "⚠️ Partial" if x > 0.3 else "❌ Missing"
    )
    st.dataframe(qdf.style.format({"Coverage": "{:.1%}"}), use_container_width=True)

    st.markdown("---")
    st.markdown("### 🔢 Composite Score Trend")
    st.plotly_chart(chart_composite_trend(df), use_container_width=True)


# ═══════════════════════════════════════════════════════════════
#  FOOTER
# ═══════════════════════════════════════════════════════════════

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
st.markdown(
    "<span style='color:#484f58;font-size:11px;'>"
    "USD/CNY Macro-Policy Divergence Tracker · "
    "Data sourced from akshare (CN bonds, PBOC fixing), yfinance (FX) · "
    "For research purposes only — not investment advice · "
    f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    "</span>",
    unsafe_allow_html=True,
)
