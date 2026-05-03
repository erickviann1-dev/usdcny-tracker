"""
Plotly chart factory for the three-layer dashboard.
All functions return go.Figure objects ready for st.plotly_chart().
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import (
    COLOR_BG, COLOR_CARD, COLOR_BORDER,
    COLOR_USD_BULL, COLOR_CNY_BULL, COLOR_NEUTRAL,
    COLOR_LINE_US, COLOR_LINE_CN,
    PRESSURE_ZONES,
)

# ── Shared layout defaults ────────────────────────────────────
_LAYOUT = dict(
    paper_bgcolor=COLOR_BG,
    plot_bgcolor =COLOR_CARD,
    font=dict(color="#c9d1d9", family="Inter, sans-serif", size=12),
    margin=dict(l=50, r=30, t=50, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    xaxis=dict(gridcolor=COLOR_BORDER, linecolor=COLOR_BORDER, showgrid=True),
    yaxis=dict(gridcolor=COLOR_BORDER, linecolor=COLOR_BORDER, showgrid=True),
)


def _fig(**overrides):
    fig = go.Figure()
    layout = {**_LAYOUT, **overrides}
    fig.update_layout(**layout)
    return fig


def _add_pressure_bands(fig, ymin, ymax, col="y"):
    """Light background shading by pressure zone."""
    pass  # For time-series x-axis zones, skip for clarity


# ═══════════════════════════════════════════════════════════════
#  GAUGE — Composite Pressure Score
# ═══════════════════════════════════════════════════════════════

def gauge_composite(score: float, label: str = "Policy Pressure") -> go.Figure:
    color = COLOR_CNY_BULL
    if score > 75:
        color = COLOR_USD_BULL
    elif score > 50:
        color = COLOR_NEUTRAL
    elif score > 25:
        color = "#84cc16"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": label, "font": {"size": 16, "color": "#c9d1d9"}},
        number={"suffix": "", "font": {"size": 42, "color": color}},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickwidth": 1,
                "tickcolor": COLOR_BORDER,
                "tickvals": [0, 25, 50, 75, 90, 100],
                "ticktext": ["0", "25", "50", "75", "90", "100"],
                "tickfont": {"size": 10},
            },
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": COLOR_CARD,
            "borderwidth": 0,
            "steps": [
                {"range": [0,  25], "color": "#14532d30"},
                {"range": [25, 50], "color": "#3f6212 30"},
                {"range": [50, 75], "color": "#713f1230"},
                {"range": [75, 90], "color": "#7c230730"},
                {"range": [90,100], "color": "#7f1d1d30"},
            ],
            "threshold": {
                "line": {"color": "#ffffff80", "width": 2},
                "thickness": 0.75,
                "value": score,
            },
        },
    ))
    fig.update_layout(
        paper_bgcolor=COLOR_BG,
        height=280,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


# ═══════════════════════════════════════════════════════════════
#  LAYER 1 — Carry Charts
# ═══════════════════════════════════════════════════════════════

def chart_yield_spread(df: pd.DataFrame) -> go.Figure:
    """Dual-axis: US & CN 2Y yields + spread as area."""
    needed = {"us_2y", "cn_2y", "yield_spread"}
    df = df.dropna(subset=[c for c in needed if c in df.columns])
    if df.empty:
        return _empty_chart("No yield data")

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.62, 0.38],
        vertical_spacing=0.04,
        subplot_titles=["2Y Yield: US vs CN (%)", "Yield Spread (US − CN, bps)"],
    )

    fig.add_trace(go.Scatter(
        x=df.index, y=df["us_2y"],
        name="US 2Y", line=dict(color=COLOR_LINE_US, width=1.8),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df["cn_2y"],
        name="CN 2Y", line=dict(color=COLOR_LINE_CN, width=1.8),
    ), row=1, col=1)

    spread_bps = df["yield_spread"] * 100
    colors = [COLOR_USD_BULL if v > 0 else COLOR_CNY_BULL for v in spread_bps]
    fig.add_trace(go.Bar(
        x=df.index, y=spread_bps,
        name="Spread (bps)",
        marker_color=colors,
        opacity=0.75,
    ), row=2, col=1)

    fig.add_hline(y=0, line_dash="dot", line_color="#ffffff30", row=2, col=1)

    _apply_shared_layout(fig, title="Interest Rate Differential — 2Y Tenor")
    return fig


def chart_carry_pressure(df: pd.DataFrame) -> go.Figure:
    """Raw carry with percentile rank overlay + on/offshore gap."""
    if "raw_carry" not in df.columns:
        return _empty_chart("No carry data")

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.6, 0.4], vertical_spacing=0.05,
        subplot_titles=["Raw Carry: US 2Y − CN 2Y (%)", "CNH−CNY On/Offshore Gap"],
    )

    df = df.dropna(subset=["raw_carry"])

    fig.add_trace(go.Scatter(
        x=df.index, y=df["raw_carry"],
        name="Raw Carry", fill="tozeroy",
        line=dict(color=COLOR_LINE_US, width=1.5),
        fillcolor="rgba(96,165,250,0.12)",
    ), row=1, col=1)

    for w, clr in [(20, "#60a5fa80"), (60, "#f97316")]:
        col_n = f"carry_ma{w}"
        if col_n in df:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col_n],
                name=f"MA{w}", line=dict(color=clr, width=1, dash="dot"),
            ), row=1, col=1)

    if "onoffshore_gap" in df:
        gap = df["onoffshore_gap"].dropna()
        fig.add_trace(go.Scatter(
            x=gap.index, y=gap,
            name="CNH−CNY Gap",
            line=dict(color=COLOR_NEUTRAL, width=1.2),
            fill="tozeroy", fillcolor="rgba(250,204,21,0.1)",
        ), row=2, col=1)
        fig.add_hline(y=0, line_dash="dot", line_color="#ffffff30", row=2, col=1)

    _apply_shared_layout(fig, title="Layer 1 — Carry Trade Feasibility")
    return fig


# ═══════════════════════════════════════════════════════════════
#  LAYER 2 — Mispricing Charts
# ═══════════════════════════════════════════════════════════════

def chart_regression_residuals(df: pd.DataFrame) -> go.Figure:
    """Scatter: yield_spread vs usdcny + rolling regression line + residual time-series."""
    needed = ["yield_spread", "usdcny", "reg_predicted", "reg_residual"]
    plot_df = df.dropna(subset=[c for c in needed if c in df.columns])

    if plot_df.empty or "reg_residual" not in plot_df.columns:
        return _empty_chart("Run regression requires ≥252 data points")

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.55, 0.45], vertical_spacing=0.05,
        subplot_titles=[
            "USD/CNY Actual vs OLS Regression Model",
            "Regression Residual (Actual − Model) — Mispricing Signal",
        ],
    )

    fig.add_trace(go.Scatter(
        x=plot_df.index, y=plot_df["usdcny"],
        name="USD/CNY Actual", line=dict(color=COLOR_NEUTRAL, width=1.5),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=plot_df.index, y=plot_df["reg_predicted"],
        name="OLS Model", line=dict(color=COLOR_LINE_US, width=1.5, dash="dash"),
    ), row=1, col=1)

    if "cip_fair_spot" in plot_df.columns:
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df["cip_fair_spot"],
            name="CIP Fair Value", line=dict(color=COLOR_LINE_CN, width=1, dash="dot"),
        ), row=1, col=1)

    resid = plot_df["reg_residual"]
    resid_clr = [COLOR_USD_BULL if v > 0 else COLOR_CNY_BULL for v in resid]
    fig.add_trace(go.Bar(
        x=resid.index, y=resid,
        name="Residual", marker_color=resid_clr, opacity=0.7,
    ), row=2, col=1)

    fig.add_hline(y=0, line_dash="dot", line_color="#ffffff40", row=2, col=1)

    # Annotation: what positive residual means
    _apply_shared_layout(fig, title="Layer 2 — CIP Mispricing & Regression Residuals")
    fig.add_annotation(
        text="Residual > 0: CNY weaker than model predicts (PBOC line holding?)",
        xref="paper", yref="paper", x=0.01, y=0.01,
        font=dict(size=10, color="#8b949e"), showarrow=False,
    )
    return fig


def chart_cip_deviation(df: pd.DataFrame) -> go.Figure:
    """CIP deviation time-series with ±1σ bands."""
    if "cip_deviation" not in df.columns:
        return _empty_chart("No CIP deviation data")

    d = df["cip_deviation"].dropna()
    mu = d.rolling(60).mean()
    sd = d.rolling(60).std()

    fig = _fig(title="CIP Deviation: Actual Spot − CIP-Implied Fair Value")
    fig.add_trace(go.Scatter(
        x=d.index, y=d, name="CIP Basis",
        line=dict(color=COLOR_NEUTRAL, width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=mu.index, y=(mu + sd), name="+1σ",
        line=dict(color="#60a5fa40", width=0.5),
        fill=None, mode="lines",
    ))
    fig.add_trace(go.Scatter(
        x=mu.index, y=(mu - sd), name="−1σ",
        line=dict(color="#60a5fa40", width=0.5),
        fill="tonexty", fillcolor="rgba(96,165,250,0.07)",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color="#ffffff30")
    fig.update_layout(height=320)
    return fig


# ═══════════════════════════════════════════════════════════════
#  LAYER 3 — Fixing Bias Charts
# ═══════════════════════════════════════════════════════════════

def chart_fixing_bias(df: pd.DataFrame) -> go.Figure:
    """Fixing bias bar + 20d rolling mean line + cumulative."""
    if "fixing_bias" not in df.columns or df["fixing_bias"].notna().sum() < 10:
        return _empty_chart("No fixing bias data (need PBOC fixing data from akshare)")

    plot_df = df.dropna(subset=["fixing_bias"])

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.6, 0.4], vertical_spacing=0.05,
        subplot_titles=[
            "PBOC Fixing Bias vs CNH Market Close (daily, pips)",
            "20-day Rolling Mean Bias — Defense Posture",
        ],
    )

    bias = plot_df["fixing_bias"]
    clrs = [COLOR_CNY_BULL if v < 0 else COLOR_USD_BULL for v in bias]

    fig.add_trace(go.Bar(
        x=bias.index, y=bias * 10000,   # convert to pips
        name="Daily Bias (pips)",
        marker_color=clrs, opacity=0.65,
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=plot_df.index, y=plot_df["bias_20d_mean"] * 10000,
        name="20d Mean", line=dict(color=COLOR_LINE_US, width=2),
    ), row=1, col=1)

    fig.add_hline(y=0, line_dash="dot", line_color="#ffffff40", row=1, col=1)

    if "bias_60d_mean" in plot_df.columns:
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df["bias_60d_mean"] * 10000,
            name="60d Mean", line=dict(color=COLOR_LINE_CN, width=1.5, dash="dash"),
        ), row=2, col=1)

    if "defense_intensity" in plot_df.columns:
        di = plot_df["defense_intensity"] * 10000
        fig.add_trace(go.Scatter(
            x=di.index, y=di, name="Defense Intensity",
            fill="tozeroy", fillcolor="rgba(34,197,94,0.1)",
            line=dict(color=COLOR_CNY_BULL, width=1.2),
        ), row=2, col=1)

    fig.add_hline(y=0, line_dash="dot", line_color="#ffffff30", row=2, col=1)

    _apply_shared_layout(fig, title="Layer 3 — PBOC Fixing Bias (Policy Intent Decoder)")
    fig.add_annotation(
        text="Negative = PBOC defending CNY  |  Positive = PBOC allowing weakness",
        xref="paper", yref="paper", x=0.01, y=0.62,
        font=dict(size=10, color="#8b949e"), showarrow=False,
    )
    return fig


def chart_fixing_vs_spot(df: pd.DataFrame) -> go.Figure:
    """PBOC fix, CNY spot, and CNH on same axis — the holy trinity."""
    cols = [c for c in ["pboc_fix", "usdcny", "usdcnh"] if c in df.columns]
    if not cols:
        return _empty_chart("No FX data")

    plot_df = df[cols].dropna(how="all")
    labels  = {"pboc_fix": "PBOC Fix", "usdcny": "USD/CNY Onshore", "usdcnh": "USD/CNH Offshore"}
    colors  = {"pboc_fix": COLOR_NEUTRAL, "usdcny": COLOR_LINE_CN, "usdcnh": COLOR_LINE_US}
    widths  = {"pboc_fix": 2.5, "usdcny": 1.5, "usdcnh": 1.5}
    dashes  = {"pboc_fix": "solid", "usdcny": "solid", "usdcnh": "dash"}

    fig = _fig()
    for col in cols:
        s = plot_df[col].dropna()
        fig.add_trace(go.Scatter(
            x=s.index, y=s,
            name=labels[col],
            line=dict(color=colors[col], width=widths[col], dash=dashes[col]),
        ))

    fig.update_layout(
        title="PBOC Fix vs Onshore vs Offshore — The Policy Triangle",
        yaxis_title="USD/CNY",
        height=350,
    )
    return fig


# ═══════════════════════════════════════════════════════════════
#  COMPOSITE SCORE TREND
# ═══════════════════════════════════════════════════════════════

def chart_composite_trend(df: pd.DataFrame) -> go.Figure:
    """Composite pressure score over time with colour gradient fill."""
    if "composite_score_smooth" not in df.columns:
        return _empty_chart("No composite score")

    s = df["composite_score_smooth"].dropna()

    fig = _fig()
    # Zone bands
    for lo, hi, clr, lbl in PRESSURE_ZONES:
        fig.add_hrect(y0=lo, y1=hi,
                      fillcolor=clr, opacity=0.06,
                      line_width=0,
                      annotation_text=lbl,
                      annotation_position="left",
                      annotation_font_size=9,
                      annotation_font_color="#8b949e")

    fig.add_trace(go.Scatter(
        x=s.index, y=s,
        name="Composite Score (5d smooth)",
        line=dict(color=COLOR_NEUTRAL, width=2.5),
        fill="tozeroy", fillcolor="rgba(250,204,21,0.08)",
    ))

    if "composite_score" in df.columns:
        raw = df["composite_score"].dropna()
        fig.add_trace(go.Scatter(
            x=raw.index, y=raw,
            name="Raw Score",
            line=dict(color="#ffffff30", width=0.8),
            mode="lines",
        ))

    fig.update_layout(
        title="Composite Policy Pressure Score (0–100)",
        yaxis=dict(range=[0, 100], gridcolor=COLOR_BORDER),
        height=300,
    )
    return fig


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def _apply_shared_layout(fig: go.Figure, title: str = ""):
    fig.update_layout(
        **_LAYOUT,
        title=dict(text=title, font=dict(size=14, color="#c9d1d9")),
        height=440,
    )
    for i in range(1, 5):
        ax = f"xaxis{'' if i == 1 else i}"
        ay = f"yaxis{'' if i == 1 else i}"
        if hasattr(fig.layout, ax):
            fig.update_layout(**{
                ax: dict(gridcolor=COLOR_BORDER, linecolor=COLOR_BORDER),
                ay: dict(gridcolor=COLOR_BORDER, linecolor=COLOR_BORDER),
            })


def _empty_chart(msg: str) -> go.Figure:
    fig = _fig()
    fig.add_annotation(
        text=msg, xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False, font=dict(size=14, color="#8b949e"),
    )
    fig.update_layout(height=300)
    return fig
