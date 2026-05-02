"""
Three-layer analytics engine.

Layer 1 — Carry Trade Feasibility   (carry.py logic)
Layer 2 — CIP Mispricing / Regression Residuals
Layer 3 — PBOC Fixing Bias / Policy Intent Decoding
"""

import numpy as np
import pandas as pd
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

from config import W_CARRY, W_MISPR, W_FIXING


# ═══════════════════════════════════════════════════════════════
#  LAYER 1 — Carry Trade Feasibility
# ═══════════════════════════════════════════════════════════════

def calc_carry(df: pd.DataFrame) -> pd.DataFrame:
    """
    Layer 1 — Unhedged Raw Carry (名义敞口套利).

    HONEST DOWNGRADE: We do NOT have access to real-time USD/CNY swap points
    or NDF forward quotes via free APIs. This module therefore tracks the
    NOMINAL 2Y yield differential — the gross carry-trade incentive BEFORE
    hedging costs. The narrative on the dashboard explicitly labels this as
    "Unhedged Raw Carry" so users understand the limitation.

    Computes:
        raw_carry          = US_2Y - CN_2Y                     (positive → USD pickup)
        carry_ma{20,60,120}= rolling means
        carry_pct_rank     = percentile rank vs trailing 252 days
        carry_pct_rank_2y  = percentile rank vs trailing 504 days (2Y window)
        carry_narrative    = string for live commentary
    """
    out = df.copy()

    if "yield_spread" not in out.columns:
        if "us_2y" in out.columns and "cn_2y" in out.columns:
            out["yield_spread"] = out["us_2y"] - out["cn_2y"]
        else:
            return out

    out["raw_carry"] = out["yield_spread"]

    # v3.1 — Money-market spread (Libor-Shibor analog, using UST 1Y as Libor successor)
    # If both 1Y money-market rates are present, expose the short-term carry too.
    # The 2Y vs 1Y comparison itself reveals term-structure stress.
    if "us_1y" in out.columns and "shibor_1y" in out.columns:
        out["mm_carry"] = out["us_1y"] - out["shibor_1y"]
    elif "mm_spread" in out.columns:
        out["mm_carry"] = out["mm_spread"]

    # Under CIP, the cost of hedging a 2Y USD position via FX swap ≈ yield differential
    # Positive raw_carry → hedge costs almost exactly that amount in fair markets.
    # The *deviation* from this parity (excess hedged carry) is the CIP basis (Layer 2).
    # Here we estimate hedged carry assuming CIP holds approximately:
    #   hedged_carry ≈ raw_carry - forward_cost ≈ 0 in CIP world
    # Real hedged carry = raw_carry - actual_swap_rate; we proxy with CIP basis as residual.
    # For display we show the "theoretical max carry pressure" = raw_carry.

    # On-offshore gap signal: if CNH > CNY (CNH weaker), depreciation pressure confirmed
    if "onoffshore_gap" in out.columns:
        out["cnh_pressure"] = out["onoffshore_gap"]  # positive → offshore CNY weaker → pressure

    # Percentile ranks: 1Y and 2Y trailing windows
    for win, col in [(252, "carry_pct_rank"), (504, "carry_pct_rank_2y")]:
        out[col] = (
            out["raw_carry"]
            .rolling(win, min_periods=60)
            .apply(lambda x: stats.percentileofscore(x.dropna(), x.iloc[-1])
                   if len(x.dropna()) > 1 else 50, raw=False)
        )

    # 20/60/120-day moving averages for trend context
    for w in [20, 60, 120]:
        out[f"carry_ma{w}"] = out["raw_carry"].rolling(w).mean()

    return out


# ═══════════════════════════════════════════════════════════════
#  LAYER 2 — CIP Mispricing & Regression Residuals
# ═══════════════════════════════════════════════════════════════

def calc_mispricing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Two complementary mispricing measures:

    A) CIP Implied Spot vs Actual Spot
       CIP: F = S × (1 + r_CN)^T / (1 + r_US)^T
       If we treat the 2Y CIP-implied "fair" spot as anchored at some baseline:
       CIP_fair_Δ = S_base × [(1 + r_CN)^2 / (1 + r_US)^2] / [(1 + r_CN_base)^2 / (1 + r_US_base)^2]
       We track how actual spot deviates from this CIP-adjusted path.

    B) Rolling OLS Regression: spot ~ f(yield_spread)
       Model: usdcny = α + β × yield_spread + ε
       Residual > 0 → spot weaker than model predicts (CNY "oversold" or PBOC holding)
       Residual < 0 → spot stronger than model predicts (CNY "propped up" by PBOC)
    """
    out = df.copy()
    needed = {"usdcny", "yield_spread", "cn_2y", "us_2y"}
    if not needed.issubset(out.columns):
        return out

    # ── A: CIP Fair Value Path ──────────────────────────────
    # Anchor to 252-day rolling start (1Y lookback within the 2Y window)
    out["cip_fair_spot"] = np.nan
    out["cip_deviation"] = np.nan

    window = 252
    s_col = out["usdcny"].values
    cn    = out["cn_2y"].values / 100
    us    = out["us_2y"].values / 100

    for i in range(window, len(out)):
        base_i = i - window
        s_base  = s_col[base_i]
        cn_base = cn[base_i]
        us_base = us[base_i]

        if np.isnan(s_base) or np.isnan(cn_base) or np.isnan(us_base):
            continue

        # CIP path: spot adjusted by cumulative rate differential
        cip_factor = ((1 + cn[i]) ** 2 / (1 + us[i]) ** 2) / \
                     ((1 + cn_base) ** 2 / (1 + us_base) ** 2)
        fair = s_base * cip_factor
        out.iloc[i, out.columns.get_loc("cip_fair_spot")] = fair
        if not np.isnan(s_col[i]):
            out.iloc[i, out.columns.get_loc("cip_deviation")] = s_col[i] - fair

    # ── B: Rolling MULTIVARIATE OLS Regression ──────────────
    #
    #   Single-variable model (legacy):
    #       USD/CNY = α + β₁ × Yield_Spread + ε
    #   Multivariate model (this version):
    #       USD/CNY = α + β₁ × Yield_Spread + β₂ × DXY + ε
    #
    #   By orthogonalising against DXY, the residual reflects ONLY
    #   China-specific factors (risk premium, capital-account stress,
    #   policy intervention) — not broad-dollar moves.
    roll_window = 252
    has_dxy = "dxy" in out.columns and out["dxy"].notna().sum() > roll_window

    for c in ["reg_predicted", "reg_residual",
              "reg_beta_spread", "reg_beta_dxy", "reg_r2",
              "reg_predicted_uni", "reg_residual_uni"]:
        out[c] = np.nan

    spread = out["yield_spread"].values
    spot   = out["usdcny"].values
    dxy    = out["dxy"].values if has_dxy else np.full(len(out), np.nan)

    for i in range(roll_window, len(out)):
        sl = slice(i - roll_window, i)
        y  = spot[sl]
        x1 = spread[sl]

        # Univariate (kept for comparison)
        m_uni = ~(np.isnan(y) | np.isnan(x1))
        if m_uni.sum() >= 60:
            sl_u, ic_u, *_ = stats.linregress(x1[m_uni], y[m_uni])
            out.iat[i, out.columns.get_loc("reg_predicted_uni")] = ic_u + sl_u * x1[-1]
            out.iat[i, out.columns.get_loc("reg_residual_uni")]  = spot[i] - (ic_u + sl_u * x1[-1])

        # Multivariate (the canonical residual)
        if has_dxy:
            x2 = dxy[sl]
            m  = ~(np.isnan(y) | np.isnan(x1) | np.isnan(x2))
            if m.sum() < 60: continue

            X = np.column_stack([np.ones(m.sum()), x1[m], x2[m]])
            try:
                beta, *_ = np.linalg.lstsq(X, y[m], rcond=None)
            except np.linalg.LinAlgError:
                continue

            # Out-of-sample prediction at current point
            x1_t = spread[i]; x2_t = dxy[i]
            if np.isnan(x1_t) or np.isnan(x2_t): continue
            pred = beta[0] + beta[1] * x1_t + beta[2] * x2_t

            # In-sample R²
            y_hat = X @ beta
            ss_res = np.sum((y[m] - y_hat) ** 2)
            ss_tot = np.sum((y[m] - y[m].mean()) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

            out.iat[i, out.columns.get_loc("reg_predicted")]   = pred
            out.iat[i, out.columns.get_loc("reg_residual")]    = spot[i] - pred
            out.iat[i, out.columns.get_loc("reg_beta_spread")] = beta[1]
            out.iat[i, out.columns.get_loc("reg_beta_dxy")]    = beta[2]
            out.iat[i, out.columns.get_loc("reg_r2")]          = r2
        else:
            # Fall back to univariate as canonical when no DXY
            out.iat[i, out.columns.get_loc("reg_predicted")] = out.iat[i, out.columns.get_loc("reg_predicted_uni")]
            out.iat[i, out.columns.get_loc("reg_residual")]  = out.iat[i, out.columns.get_loc("reg_residual_uni")]

    # ── Composite Mispricing Score (0-100) ──────────────────
    # CIP deviation percentile + regression residual percentile
    out["mispricing_score"] = _dual_percentile_score(
        out["cip_deviation"], out["reg_residual"]
    )

    # ── Hedged carry / return — market 1Y forward when available ─────────
    # Primary (when usdcny_fwd_1y + 1Y rates exist): exact 1Y covered return (% of notional):
    #   hedged_return = 100 × [ (1 + r_US) × (F/S) − (1 + r_CN) ]
    #   ≡ US asset yield + FX forward premium (100×(F/S−1)) − CN funding in tiny spreads
    # Fallback (no market forward): legacy 2Y CIP proxy
    #   hedged_carry_proxy = raw_carry − cip_dev_pct
    #
    # Forward curve: CFETS USD/CNY 1Y all-in (see data_fetcher cache), forward-filled.
    if "raw_carry" in out.columns and "cip_deviation" in out.columns and "usdcny" in out.columns:
        out["cip_dev_pct"] = (out["cip_deviation"] / out["usdcny"]) * 100
        out["forward_premium_pct"] = np.nan
        out["hedged_carry_proxy"] = np.nan
        out["hedged_carry_method"] = ""

        S = pd.to_numeric(out["usdcny"], errors="coerce")
        if "usdcny_fwd_1y" in out.columns:
            F = pd.to_numeric(out["usdcny_fwd_1y"], errors="coerce")
        else:
            F = pd.Series(np.nan, index=out.index)
        rus = pd.to_numeric(out["us_1y"], errors="coerce") / 100.0 if "us_1y" in out.columns else pd.Series(np.nan, index=out.index)
        rcn = pd.to_numeric(out["shibor_1y"], errors="coerce") / 100.0 if "shibor_1y" in out.columns else pd.Series(np.nan, index=out.index)

        mkt = (
            F.notna() & S.notna() & rus.notna() & rcn.notna()
            & (F > 0) & (S > 0) & (F / S <= 1.15) & (F / S >= 0.85)
        )
        out.loc[mkt, "forward_premium_pct"] = 100.0 * (F[mkt] / S[mkt] - 1.0)
        out.loc[mkt, "hedged_carry_proxy"] = 100.0 * (
            (1.0 + rus[mkt]) * (F[mkt] / S[mkt]) - (1.0 + rcn[mkt])
        )
        out.loc[mkt, "hedged_carry_method"] = "market_1y"

        cip_fb = (
            (~mkt) & out["raw_carry"].notna() & out["cip_dev_pct"].notna()
        )
        out.loc[cip_fb, "hedged_carry_proxy"] = (
            out.loc[cip_fb, "raw_carry"] - out.loc[cip_fb, "cip_dev_pct"]
        )
        out.loc[cip_fb, "hedged_carry_method"] = "cip_proxy_2y"

        out["hedged_carry_pct_rank"] = (
            out["hedged_carry_proxy"]
            .rolling(252, min_periods=60)
            .apply(lambda x: stats.percentileofscore(x.dropna(), x.iloc[-1])
                   if len(x.dropna()) > 1 else 50, raw=False)
        )

        # ── v3.3 · OFFSHORE hedged return (uses CNH HIBOR, not Shibor) ──
        # The honest formula for what a real Hong-Kong-booked carry trade
        # actually earns. r_CNY uses CNH 1Y HIBOR (offshore fixing), since
        # onshore Shibor is not a tradable funding cost for offshore desks.
        # Market typically: cnh_hibor > shibor → offshore hedged return
        # is WORSE than onshore (CNH costs more to short).
        if "cnh_hibor_1y" in out.columns:
            r_cnh = pd.to_numeric(out["cnh_hibor_1y"], errors="coerce") / 100.0
            mkt_off = (
                F.notna() & S.notna() & rus.notna() & r_cnh.notna()
                & (F > 0) & (S > 0) & (F / S <= 1.15) & (F / S >= 0.85)
            )
            out["hedged_carry_offshore"] = np.nan
            out.loc[mkt_off, "hedged_carry_offshore"] = 100.0 * (
                (1.0 + rus[mkt_off]) * (F[mkt_off] / S[mkt_off]) - (1.0 + r_cnh[mkt_off])
            )

    # ── v3.3 · CNH funding stress (PBOC offshore liquidity defence signal) ──
    # CNH HIBOR 1Y − Shibor 1Y. Positive = PBOC pulling CNH out of HK banks.
    # Historical squeezes: Jan 2017 overnight HIBOR hit 60%+; Sep 2018 hit 25%+.
    # This is one of the few directly observable "PBOC defence in action" signals.
    if "cnh_hibor_1y" in out.columns and "shibor_1y" in out.columns:
        out["cnh_funding_stress"] = out["cnh_hibor_1y"] - out["shibor_1y"]
        # Percentile rank — highlights tail events
        out["cnh_stress_pct_rank"] = (
            out["cnh_funding_stress"]
            .rolling(252, min_periods=60)
            .apply(lambda x: stats.percentileofscore(x.dropna(), x.iloc[-1])
                   if len(x.dropna()) > 1 else 50, raw=False)
        )

    # Rolling-window z-score of multivariate residual (in-sample distribution)
    if "reg_residual" in out.columns:
        rr = out["reg_residual"]
        mu = rr.rolling(252, min_periods=60).mean()
        sig = rr.rolling(252, min_periods=60).std()
        out["reg_residual_z"] = (rr - mu) / sig.replace(0, np.nan)

    return out


def _dual_percentile_score(s1: pd.Series, s2: pd.Series) -> pd.Series:
    """Average percentile rank of two series (higher = more CNY weakness vs model)."""
    r1 = s1.rolling(252, min_periods=30).rank(pct=True) * 100
    r2 = s2.rolling(252, min_periods=30).rank(pct=True) * 100
    return ((r1.fillna(50) + r2.fillna(50)) / 2).clip(0, 100)


# ═══════════════════════════════════════════════════════════════
#  LAYER 3 — PBOC Fixing Bias / Policy Intent
# ═══════════════════════════════════════════════════════════════

def calc_fixing_bias(df: pd.DataFrame) -> pd.DataFrame:
    """
    PBOC Fixing Bias — the "policy red line" detector.

    Method:
        Market expectation of today's fix ≈ previous business day's CNH close.
        (Offshore CNH is the unconstrained market price; PBOC looks at this overnight.)

        Fixing Bias = pboc_fix - usdcnh_prev_close
        Negative bias → PBOC set FIX stronger than market → defending CNY
        Positive bias → PBOC set FIX weaker than market → neutral/allowing depreciation

    Secondary signals:
        - 20-day cumulative bias: sustained negative = strong defense posture
        - Bias volatility: rising vol = PBOC losing control of narrative
        - "Defense Intensity" = -1 × rolling mean bias (higher = more defense)
    """
    out = df.copy()

    has_fix = "pboc_fix" in out.columns and out["pboc_fix"].notna().sum() > 20
    has_cnh = "usdcnh" in out.columns and out["usdcnh"].notna().sum() > 20
    has_cny = "usdcny" in out.columns

    if has_fix and has_cnh:
        out["market_anchor"]   = out["usdcnh"].shift(1)             # CNH prev close
        out["fixing_bias_raw"] = out["pboc_fix"] - out["market_anchor"]
    elif has_fix and has_cny:
        out["market_anchor"]   = out["usdcny"].shift(1)
        out["fixing_bias_raw"] = out["pboc_fix"] - out["market_anchor"]
    else:
        out["market_anchor"]   = np.nan
        out["fixing_bias_raw"] = (-(out["usdcnh"] - out["usdcny"]) if has_cnh and has_cny
                                   else pd.Series(np.nan, index=out.index))

    # ── DXY overnight adjustment (the missing piece) ──────────
    # Beijing 4:30pm close → next-day 9:15am fix ≈ 17h gap covering NY trading.
    # If DXY rallies overnight, the next-day CNY would mechanically fix weaker
    # *without* PBOC doing anything — we must remove that mechanical move first.
    #
    #   Expected_Fix = market_anchor × (1 + α × dxy_overnight_return)
    #   fixing_bias  = pboc_fix - Expected_Fix
    #
    # α is the empirical CNY/DXY beta (typically 0.3–0.5). We estimate it
    # dynamically from a rolling 252-day OLS of CNY returns on DXY returns.
    has_dxy = "dxy_ret" in out.columns and out["dxy_ret"].notna().sum() > 60

    if has_dxy and not out["market_anchor"].isna().all():
        # Rolling beta of CNY returns vs DXY returns
        cny_ret = out["usdcny"].pct_change()
        dxy_ret = out["dxy_ret"]
        out["alpha_cny_dxy"] = (cny_ret.rolling(252, min_periods=60)
                                       .cov(dxy_ret)
                                / dxy_ret.rolling(252, min_periods=60).var())

        # DXY overnight return — use yesterday's DXY return as overnight proxy
        # (DXY data is daily NY close → captures the relevant overnight session)
        out["dxy_overnight"] = out["dxy_ret"].shift(0)   # value on day t = NY-close move that PBOC sees
        out["expected_fix"] = (out["market_anchor"]
                               * (1 + out["alpha_cny_dxy"] * out["dxy_overnight"]))
        out["fixing_bias"]  = out["pboc_fix"] - out["expected_fix"]
    else:
        # No DXY → fall back to raw (mechanical-move-contaminated) bias
        out["alpha_cny_dxy"] = np.nan
        out["expected_fix"]  = out["market_anchor"]
        out["fixing_bias"]   = out["fixing_bias_raw"]

    # Rolling stats on bias
    out["bias_20d_mean"]   = out["fixing_bias"].rolling(20).mean()
    out["bias_60d_mean"]   = out["fixing_bias"].rolling(60).mean()
    out["bias_20d_vol"]    = out["fixing_bias"].rolling(20).std()

    # Defense Intensity: how aggressively is PBOC leaning against depreciation?
    # Negative mean bias = strong defense → flip sign so high = strong defense
    out["defense_intensity"] = -out["bias_20d_mean"].rolling(20).mean()

    # Cumulative bias (directional)
    out["cum_bias_60d"] = out["fixing_bias"].rolling(60).sum()

    # Fixing vs PBOC's stated band (±2%)
    if has_fix and has_cny:
        out["fix_vs_spot_pct"] = (out["pboc_fix"] / out["usdcny"] - 1) * 100

    # Policy pressure score (0-100): 100 = PBOC under maximum pressure, minimal defense
    out["policy_score"] = _policy_pressure_score(out["fixing_bias"])

    return out


def _policy_pressure_score(bias: pd.Series) -> pd.Series:
    """
    Map fixing bias to 0-100 pressure score.
    Large positive bias (PBOC not defending) → 100.
    Large negative bias (PBOC aggressively defending) → 0.
    """
    roll_rank = bias.rolling(252, min_periods=30).rank(pct=True) * 100
    return roll_rank.fillna(50).clip(0, 100)


# ═══════════════════════════════════════════════════════════════
#  COMPOSITE PRESSURE GAUGE
# ═══════════════════════════════════════════════════════════════

def calc_composite(df: pd.DataFrame) -> pd.DataFrame:
    """
    Weighted composite of three layer scores → single "Policy Pressure" reading.

    Interpretation:
        0  – 25: Low — CNY is stable/appreciating, carry unattractiv
        25 – 50: Moderate — mild carry trade pressure, PBOC comfortable
        50 – 75: Elevated — significant carry pressure, PBOC actively managing
        75 – 90: High — carry trade running hot, fixing bias shows strong defense
        90 –100: Extreme — structural stress, potential for sharp adjustment
    """
    out = df.copy()

    scores = {}

    # Layer 1: carry_pct_rank already 0-100
    if "carry_pct_rank" in out.columns:
        scores["carry"] = out["carry_pct_rank"].fillna(50)

    # Layer 2: mispricing_score already 0-100
    if "mispricing_score" in out.columns:
        scores["mispr"] = out["mispricing_score"].fillna(50)

    # Layer 3: policy_score already 0-100
    if "policy_score" in out.columns:
        scores["fixing"] = out["policy_score"].fillna(50)

    if not scores:
        return out

    weights = {"carry": W_CARRY, "mispr": W_MISPR, "fixing": W_FIXING}
    total_w = sum(weights[k] for k in scores)

    composite = sum(scores[k] * weights[k] for k in scores) / total_w
    out["composite_score"] = composite.clip(0, 100)

    # 5-day smooth for the gauge display
    out["composite_score_smooth"] = out["composite_score"].rolling(5).mean().clip(0, 100)

    return out


# ═══════════════════════════════════════════════════════════════
#  FULL PIPELINE
# ═══════════════════════════════════════════════════════════════

def run_full_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Run all three layers + composite on a master dataframe."""
    df = calc_carry(df)
    df = calc_mispricing(df)
    df = calc_fixing_bias(df)
    df = calc_composite(df)
    return df


# ─────────────────────────────────────────────────────────────
#  Summary statistics helper
# ─────────────────────────────────────────────────────────────

def latest_snapshot(df: pd.DataFrame) -> dict:
    """Extract latest key metrics as a flat dict for KPI cards."""
    if df.empty:
        return {k: "N/A" for k in [
            "date","usdcny","usdcnh","pboc_fix","us_2y","cn_2y","raw_carry",
            "carry_pct_rank","cip_deviation","reg_residual","fixing_bias",
            "bias_20d_mean","defense_intensity","composite_score"]}

    # Pick the row with the most non-null values among recent rows
    candidate_col = next((c for c in ["usdcny", "pboc_fix", "us_2y"] if c in df.columns), df.columns[0])
    valid = df.dropna(subset=[candidate_col])
    last = valid.iloc[-1] if not valid.empty else df.iloc[-1]

    def g(col, fmt=".2f"):
        v = last.get(col, np.nan)
        try:
            fv = float(v)
            return f"{fv:{fmt}}" if not np.isnan(fv) else "N/A"
        except (TypeError, ValueError):
            return "N/A"

    return {
        "date":              last.name.strftime("%Y-%m-%d"),
        "usdcny":            g("usdcny"),
        "usdcnh":            g("usdcnh"),
        "pboc_fix":          g("pboc_fix"),
        "us_2y":             g("us_2y"),
        "cn_2y":             g("cn_2y"),
        "dxy":               g("dxy"),
        "raw_carry":         g("raw_carry"),
        "carry_pct_rank":    g("carry_pct_rank",    ".0f"),
        "carry_pct_rank_2y": g("carry_pct_rank_2y", ".0f"),
        # v3.1 — money-market & hedged carry
        "shibor_1y":            g("shibor_1y"),
        "us_1y":                g("us_1y"),
        "mm_spread":            g("mm_spread"),
        "usdcny_fwd_1y":        g("usdcny_fwd_1y"),
        "hedged_carry_proxy":   g("hedged_carry_proxy"),
        "hedged_carry_pct_rank":g("hedged_carry_pct_rank", ".0f"),
        "hedged_carry_method":  (
            ""
            if "hedged_carry_method" not in last.index
            or last.get("hedged_carry_method") in ("", None)
            else str(last.get("hedged_carry_method"))
        ),
        # v3.3 — offshore CNH funding layer
        "cnh_hibor_1y":         g("cnh_hibor_1y"),
        "cnh_hibor_3m":         g("cnh_hibor_3m"),
        "cnh_hibor_on":         g("cnh_hibor_on"),
        "cnh_funding_stress":   g("cnh_funding_stress"),
        "cnh_stress_pct_rank":  g("cnh_stress_pct_rank", ".0f"),
        "hedged_carry_offshore":g("hedged_carry_offshore"),
        "cip_deviation":     g("cip_deviation"),
        "reg_residual":      g("reg_residual"),
        "reg_residual_uni":  g("reg_residual_uni"),
        "reg_beta_spread":   g("reg_beta_spread", ".3f"),
        "reg_beta_dxy":      g("reg_beta_dxy",    ".4f"),
        "reg_r2":            g("reg_r2", ".3f"),
        "reg_residual_z":    g("reg_residual_z", ".2f"),
        "alpha_cny_dxy":     g("alpha_cny_dxy", ".3f"),
        "expected_fix":      g("expected_fix",  ".4f"),
        "fixing_bias":       g("fixing_bias"),
        "fixing_bias_raw":   g("fixing_bias_raw"),
        "bias_20d_mean":     g("bias_20d_mean"),
        "defense_intensity": g("defense_intensity"),
        "composite_score":   g("composite_score_smooth", ".0f"),
    }
