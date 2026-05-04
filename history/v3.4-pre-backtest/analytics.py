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


# ═══════════════════════════════════════════════════════════════
#  v3.4 — DECISION-LAYER INTERPRETERS
#  These translate raw signals into the two questions the user
#  actually asks: "can I do this trade?" and "what is PBOC doing?"
# ═══════════════════════════════════════════════════════════════

def interpret_carry_verdict(snap: dict) -> dict:
    """
    Translate hedged-carry numbers into a plain-English BUY / DON'T BUY
    verdict. The number `hedged_carry_proxy` (or `hedged_carry_offshore`)
    already answers the question — this just makes the answer obvious.

    Returns a dict with:
      verdict        : 'yes' | 'marginal' | 'no'
      headline_en/zh : one-line answer ("NO — would lose 0.29%/yr")
      chain          : list of [label, value, unit] tuples showing the math
      reasoning_en/zh: 1–2 sentence "why"
    """
    def f(k, default=None):
        v = snap.get(k)
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    on   = f("hedged_carry_proxy")
    off  = f("hedged_carry_offshore")
    raw  = f("raw_carry")
    fwd  = f("usdcny_fwd_1y")
    spot = f("usdcny")
    us1y = f("us_1y")
    sh1y = f("shibor_1y")
    fwd_premium = f("forward_premium_pct")

    # Headline number is offshore if available (more honest for HK desks),
    # else onshore proxy. Both should be < 0 today per our v3.3 data.
    headline_val = off if off is not None else on
    method = "offshore (CNH HIBOR)" if off is not None else "onshore (Shibor)"

    if headline_val is None:
        return {"verdict": "unknown", "headline_en": "—", "headline_zh": "—",
                "chain": [], "reasoning_en": "Insufficient data.",
                "reasoning_zh": "数据不足，无法判断。"}

    # Decision rule (annualised %, after FX hedge)
    if headline_val > 0.5:
        verdict = "yes"
        en_label = f"YES — would earn {headline_val:+.2f}% / year"
        zh_label = f"可以 — 一年净收益 {headline_val:+.2f}%"
        why_en = ("Positive after-hedge return is rare on USD/CNY — usually "
                  "signals dislocated USD funding or capital-control friction. "
                  "Verify forward quote before sizing.")
        why_zh = ("USD/CNY 套利做出正收益很罕见 — 通常意味着美元融资紧张或资本"
                  "管制摩擦。建议核实远期报价后再下单。")
    elif headline_val < -0.5:
        verdict = "no"
        en_label = f"NO — would lose {abs(headline_val):.2f}% / year"
        zh_label = f"不能 — 一年净亏 {abs(headline_val):.2f}%"
        if fwd_premium is not None and raw is not None:
            why_en = (f"Market already prices CNY {abs(fwd_premium):.2f}% stronger "
                      f"in the 1Y forward, exceeding the {raw:.2f}% nominal yield "
                      f"pickup. CIP closes the apparent arbitrage.")
            why_zh = (f"远期已把 CNY 升值 {abs(fwd_premium):.2f}% 定价进去，超过名义"
                      f"利差 {raw:.2f}%。CIP 把表面套利空间填平了。")
        else:
            why_en = ("Forward premium absorbs the nominal carry. "
                      "Hedging cost > yield pickup.")
            why_zh = "远期升水吃掉了名义利差，对冲成本 > 收益。"
    else:
        verdict = "marginal"
        en_label = f"MARGINAL — only {headline_val:+.2f}% / year"
        zh_label = f"边缘 — 仅 {headline_val:+.2f}%/年"
        why_en = ("Within transaction-cost band. Bid/offer + execution slippage "
                  "likely consumes any apparent edge.")
        why_zh = ("在交易成本带内。买卖价差 + 滑点很可能吃掉这点收益。")

    chain = []
    if sh1y is not None:
        chain.append(["borrow CNY @ Shibor 1Y", f"{sh1y:.2f}%", "cost"])
    if spot is not None:
        chain.append(["convert USD @ spot", f"{spot:.4f}", "USD/CNY"])
    if us1y is not None:
        chain.append(["invest UST 1Y", f"{us1y:.2f}%", "yield"])
    if fwd is not None:
        chain.append(["lock 1Y forward", f"{fwd:.4f}", "USD/CNY"])
    if fwd_premium is not None:
        chain.append(["forward premium",
                      f"{fwd_premium:+.2f}%", "CNY appreciation priced in"])
    if headline_val is not None:
        chain.append(["NET (after hedge)", f"{headline_val:+.2f}%/yr",
                      method])

    return {
        "verdict":      verdict,
        "headline_en":  en_label,
        "headline_zh":  zh_label,
        "chain":        chain,
        "reasoning_en": why_en,
        "reasoning_zh": why_zh,
        "method":       method,
    }


def _snap_dict_from_row(row: pd.Series) -> dict:
    """Float-valued snapshot fields for interpret_carry_verdict (historical row)."""

    def fv(col: str):
        if col not in row.index:
            return None
        v = row[col]
        if pd.isna(v):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    return {
        "hedged_carry_proxy": fv("hedged_carry_proxy"),
        "hedged_carry_offshore": fv("hedged_carry_offshore"),
        "raw_carry": fv("raw_carry"),
        "usdcny_fwd_1y": fv("usdcny_fwd_1y"),
        "usdcny": fv("usdcny"),
        "us_1y": fv("us_1y"),
        "shibor_1y": fv("shibor_1y"),
        "forward_premium_pct": fv("forward_premium_pct"),
    }


def _headline_hedged_row(row: pd.Series) -> float:
    off = row["hedged_carry_offshore"] if "hedged_carry_offshore" in row.index else np.nan
    if pd.notna(off):
        return float(off)
    px = row["hedged_carry_proxy"] if "hedged_carry_proxy" in row.index else np.nan
    return float(px) if pd.notna(px) else np.nan


def _position_from_verdict(verdict: str) -> float:
    if verdict == "yes":
        return 1.0
    if verdict == "marginal":
        return 0.5
    return 0.0


def backtest_verdict(df: pd.DataFrame) -> dict:
    """
    Historical replay of interpret_carry_verdict with simple trading-style P&L.

    Daily P&L (ROADMAP D.1): Δ hedged_carry × prior-day position ÷ 252 ÷ 100,
    where hedged_carry is the same headline series as the verdict (offshore if
    available, else onshore proxy). Benchmark: passive long USD/CNY spot.
    """
    empty = {
        "dates": [], "verdict": [], "position": [], "daily_pnl": [],
        "cumulative": [], "benchmark": [], "benchmark_cumulative": [],
        "stats": {
            "total_return": None, "sharpe": None, "max_dd": None,
            "hit_rate": None, "days_long": 0, "days_flat": 0,
            "n_days": 0,
        },
    }
    if df.empty or "usdcny" not in df.columns:
        return empty

    dates_out = []
    verdict_out = []
    position_out = []
    hedged_series = []
    spot_series = []

    for idx, row in df.iterrows():
        snap_r = _snap_dict_from_row(row)
        vc = interpret_carry_verdict(snap_r)
        v = vc.get("verdict", "unknown")
        h = _headline_hedged_row(row)
        spt = row.get("usdcny")
        spt = float(spt) if pd.notna(spt) else np.nan

        dates_out.append(idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx))
        verdict_out.append(v if v in ("yes", "marginal", "no") else "unknown")
        position_out.append(_position_from_verdict(v))
        hedged_series.append(h)
        spot_series.append(spt)

    n = len(dates_out)
    daily_pnl = [None] * n
    cumulative = [1.0] * n
    benchmark = [None] * n
    bench_cum = [1.0] * n

    for t in range(1, n):
        h_t = hedged_series[t]
        h_tm = hedged_series[t - 1]
        pos_tm = position_out[t - 1]

        if np.isnan(h_t) or np.isnan(h_tm):
            r_sig = 0.0
        else:
            r_sig = pos_tm * (h_t - h_tm) / 252.0 / 100.0

        s_t = spot_series[t]
        s_tm = spot_series[t - 1]
        if np.isnan(s_t) or np.isnan(s_tm) or s_tm == 0:
            r_bm = 0.0
        else:
            r_bm = (s_t - s_tm) / s_tm

        daily_pnl[t] = float(r_sig)
        benchmark[t] = float(r_bm)

        prev_eq = cumulative[t - 1] if cumulative[t - 1] is not None else 1.0
        cumulative[t] = float(prev_eq * (1.0 + r_sig))
        prev_b = bench_cum[t - 1] if bench_cum[t - 1] is not None else 1.0
        bench_cum[t] = float(prev_b * (1.0 + r_bm))

    daily_pnl[0] = 0.0
    benchmark[0] = 0.0

    r_tail = np.array([daily_pnl[i] for i in range(1, n) if daily_pnl[i] is not None])
    mean_d = float(np.nanmean(r_tail)) if len(r_tail) else 0.0
    std_d = float(np.nanstd(r_tail, ddof=1)) if len(r_tail) > 1 else 0.0
    sharpe = (mean_d / std_d * np.sqrt(252)) if std_d > 1e-12 else 0.0

    eq = np.array([cumulative[i] for i in range(n)])
    peak = np.maximum.accumulate(eq)
    dd = eq / np.where(peak > 0, peak, np.nan) - 1.0
    max_dd = float(np.nanmin(dd)) if len(dd) else 0.0

    total_ret = float(cumulative[-1] - 1.0) if n else 0.0

    long_pnls = [
        daily_pnl[t]
        for t in range(1, n)
        if position_out[t - 1] > 0 and daily_pnl[t] is not None
    ]
    hits = sum(1 for x in long_pnls if x > 0)
    hit_rate = (hits / len(long_pnls)) if long_pnls else None

    days_long = sum(1 for p in position_out if p > 0)
    days_flat = sum(1 for p in position_out if p == 0)

    return {
        "dates": dates_out,
        "verdict": verdict_out,
        "position": position_out,
        "daily_pnl": daily_pnl,
        "cumulative": cumulative,
        "benchmark": benchmark,
        "benchmark_cumulative": bench_cum,
        "stats": {
            "total_return": round(total_ret, 6),
            "sharpe": round(sharpe, 4),
            "max_dd": round(max_dd, 6),
            "hit_rate": None if hit_rate is None else round(hit_rate, 4),
            "days_long": int(days_long),
            "days_flat": int(days_flat),
            "n_days": int(n),
        },
    }


def _snap_float(snap: dict, key: str):
    v = snap.get(key)
    if v is None or v == "" or v == "N/A":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _spot_from_target_hedged(F: float, rus_pct: float, rcn_pct: float, target_hedged_pct: float) -> float | None:
    """Solve S where hedged (market 1Y) equals target_hedged_pct."""
    k = target_hedged_pct / 100.0
    rus = rus_pct / 100.0
    rcn = rcn_pct / 100.0
    den = (1.0 + rcn) + k
    if den <= 1e-9:
        return None
    return (1.0 + rus) * F / den


def _fwd_from_target_hedged(S: float, rus_pct: float, rcn_pct: float, target_hedged_pct: float) -> float | None:
    k = target_hedged_pct / 100.0
    rus = rus_pct / 100.0
    rcn = rcn_pct / 100.0
    num = ((1.0 + rcn) + k) * S
    den = (1.0 + rus)
    if den <= 1e-9:
        return None
    return num / den


def _ust_from_target_hedged(S: float, F: float, rcn_pct: float, target_hedged_pct: float) -> float | None:
    """Solve US 1Y (% flat) given spot, forward, CN funding."""
    k = target_hedged_pct / 100.0
    rcn = rcn_pct / 100.0
    if S <= 0 or F <= 0:
        return None
    rus = ((k + (1.0 + rcn)) * S / F) - 1.0
    return rus * 100.0


def _cn_funding_from_target_hedged(S: float, F: float, rus_pct: float, target_hedged_pct: float) -> float | None:
    """Solve CN funding rate (% flat)."""
    k = target_hedged_pct / 100.0
    rus = rus_pct / 100.0
    if S <= 0 or F <= 0:
        return None
    rcn = (1.0 + rus) * (F / S) - 1.0 - k
    return rcn * 100.0


def _plausible_spot(S: float | None) -> bool:
    return S is not None and 5.35 <= S <= 8.95


def _plausible_fwd_ratio(F: float, S: float) -> bool:
    if F is None or S is None or S <= 0:
        return False
    r = F / S
    return 0.84 <= r <= 1.16


def _plausible_rate_pct(r: float | None) -> bool:
    return r is not None and -1.0 <= r <= 22.0


def compute_flip_lines(snap: dict) -> list[dict]:
    """
    ROADMAP D.2 — analytic flip levels for ±0.5% hedged carry thresholds,
    holding other inputs fixed (market 1Y formula only).
    """
    S = _snap_float(snap, "usdcny")
    F = _snap_float(snap, "usdcny_fwd_1y")
    rus = _snap_float(snap, "us_1y")
    shib = _snap_float(snap, "shibor_1y")
    cnh = _snap_float(snap, "cnh_hibor_1y")

    off = _snap_float(snap, "hedged_carry_offshore")
    use_offshore = off is not None

    rcn = cnh if use_offshore and cnh is not None else shib

    rows_cfg = [
        ("usdcny", "Spot", "即期"),
        ("usdcny_fwd_1y", "1Y forward", "1年远期"),
        ("us_1y", "UST 1Y", "美债 1年"),
        ("shibor_1y", "Shibor 1Y", "Shibor 1年"),
        ("cnh_hibor_1y", "CNH HIBOR 1Y", "CNH HIBOR 1年"),
    ]

    out: list[dict] = []

    if (
        S is None or F is None or rus is None or rcn is None
        or not _plausible_fwd_ratio(F, S)
    ):
        for inp, en, zh in rows_cfg:
            tv = _snap_float(snap, inp)
            out.append({
                "input": inp,
                "today": tv,
                "flip_to_yes": None,
                "flip_to_no": None,
                "dist_yes_pct": None,
                "dist_no_pct": None,
                "dist_yes_pp": None,
                "dist_no_pp": None,
                "label_en": en,
                "label_zh": zh,
                "mode": "unavailable",
            })
        return out

    def pack(inp: str, label_en: str, label_zh: str,
             flip_yes: float | None, flip_no: float | None,
             today_v: float | None, *, kind: str):
        fy = flip_yes if (flip_yes is not None and (
            (kind == "rate" and _plausible_rate_pct(flip_yes))
            or (kind == "fx" and (
                (inp == "usdcny_fwd_1y" and _plausible_spot(S) and _plausible_fwd_ratio(flip_yes, S))
                or (inp == "usdcny" and _plausible_spot(flip_yes) and _plausible_fwd_ratio(F, flip_yes))
            ))
        )) else None
        fn = flip_no if (flip_no is not None and (
            (kind == "rate" and _plausible_rate_pct(flip_no))
            or (kind == "fx" and (
                (inp == "usdcny_fwd_1y" and _plausible_spot(S) and _plausible_fwd_ratio(flip_no, S))
                or (inp == "usdcny" and _plausible_spot(flip_no) and _plausible_fwd_ratio(F, flip_no))
            ))
        )) else None

        # Recompute distances from validated flips
        dy_pct = dn_pct = dy_pp = dn_pp = None
        if kind == "fx":
            if today_v is not None and fy is not None:
                dy_pct = (fy / today_v - 1.0) * 100.0
            if today_v is not None and fn is not None:
                dn_pct = (fn / today_v - 1.0) * 100.0
        else:
            if today_v is not None and fy is not None:
                dy_pp = fy - today_v
            if today_v is not None and fn is not None:
                dn_pp = fn - today_v

        return {
            "input": inp,
            "today": today_v,
            "flip_to_yes": round(fy, 6) if fy is not None else None,
            "flip_to_no": round(fn, 6) if fn is not None else None,
            "dist_yes_pct": None if dy_pct is None else round(dy_pct, 4),
            "dist_no_pct": None if dn_pct is None else round(dn_pct, 4),
            "dist_yes_pp": None if dy_pp is None else round(dy_pp, 6),
            "dist_no_pp": None if dn_pp is None else round(dn_pp, 6),
            "label_en": label_en,
            "label_zh": label_zh,
            "mode": "market_1y_offshore" if use_offshore else "market_1y_onshore",
        }

    # Spot flips
    s_yes = _spot_from_target_hedged(F, rus, rcn, 0.5)
    s_no = _spot_from_target_hedged(F, rus, rcn, -0.5)
    if not _plausible_spot(s_yes):
        s_yes = None
    if not _plausible_spot(s_no):
        s_no = None
    out.append(pack("usdcny", "Spot", "即期", s_yes, s_no, S, kind="fx"))

    # Forward flips
    f_yes = _fwd_from_target_hedged(S, rus, rcn, 0.5)
    f_no = _fwd_from_target_hedged(S, rus, rcn, -0.5)
    if not _plausible_fwd_ratio(f_yes, S):
        f_yes = None
    if not _plausible_fwd_ratio(f_no, S):
        f_no = None
    out.append(pack("usdcny_fwd_1y", "1Y forward", "1年远期", f_yes, f_no, F, kind="fx"))

    # UST — solve both thresholds
    u_yes = _ust_from_target_hedged(S, F, rcn, 0.5)
    u_no = _ust_from_target_hedged(S, F, rcn, -0.5)
    out.append(pack("us_1y", "UST 1Y", "美债 1年", u_yes, u_no, rus, kind="rate"))

    # Onshore funding — only meaningful when headline uses Shibor proxy path;
    # still emit row using same formula with rcn = shib when shib present.
    if shib is not None:
        cn_yes = _cn_funding_from_target_hedged(S, F, rus, 0.5)
        cn_no = _cn_funding_from_target_hedged(S, F, rus, -0.5)
        fy_s = cn_yes
        fn_s = cn_no
        if not _plausible_rate_pct(fy_s):
            fy_s = None
        if not _plausible_rate_pct(fn_s):
            fn_s = None
        out.append({
            "input": "shibor_1y",
            "today": shib,
            "flip_to_yes": None if fy_s is None else round(fy_s, 6),
            "flip_to_no": None if fn_s is None else round(fn_s, 6),
            "dist_yes_pct": None,
            "dist_no_pct": None,
            "dist_yes_pp": None if fy_s is None or shib is None else round(fy_s - shib, 6),
            "dist_no_pp": None if fn_s is None or shib is None else round(fn_s - shib, 6),
            "label_en": "Shibor 1Y",
            "label_zh": "Shibor 1年",
            "mode": "market_1y_onshore",
        })

    # CNH HIBOR row — solves cnh rate holding S,F,r_us fixed
    if cnh is not None and use_offshore:
        cy_yes = _cn_funding_from_target_hedged(S, F, rus, 0.5)
        cy_no = _cn_funding_from_target_hedged(S, F, rus, -0.5)
        fy_c = cy_yes
        fn_c = cy_no
        if not _plausible_rate_pct(fy_c):
            fy_c = None
        if not _plausible_rate_pct(fn_c):
            fn_c = None
        out.append({
            "input": "cnh_hibor_1y",
            "today": cnh,
            "flip_to_yes": None if fy_c is None else round(fy_c, 6),
            "flip_to_no": None if fn_c is None else round(fn_c, 6),
            "dist_yes_pct": None,
            "dist_no_pct": None,
            "dist_yes_pp": None if fy_c is None else round(fy_c - cnh, 6),
            "dist_no_pp": None if fn_c is None else round(fn_c - cnh, 6),
            "label_en": "CNH HIBOR 1Y",
            "label_zh": "CNH HIBOR 1年",
            "mode": "market_1y_offshore",
        })

    return out


def interpret_policy_stance(snap: dict, df: pd.DataFrame) -> dict:
    """
    Combine fixing_bias + defense_intensity + cnh_funding_stress + on/offshore
    gap into a single PBOC posture: defending / neutral / allowing weakness /
    resisting strength. Plus prose explanation.

    Returns:
      stance   : 'defending' | 'neutral' | 'weakening' | 'resisting'
      label_en : "DEFENDING CNY" / "NEUTRAL · hands-off" / etc.
      label_zh : (Chinese mirror)
      signals  : list of [name, value, status_color] for the evidence row
      reading_en/zh : 2–3 sentence interpretation
    """
    def f(k, default=None):
        v = snap.get(k)
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    bias       = f("fixing_bias")           # CNY units; <0 = stronger fix = defending
    defense    = f("defense_intensity")     # negative-sign convention; high = defending
    cnh_stress = f("cnh_funding_stress")    # CNH HIBOR − Shibor
    onoff_gap  = None
    if isinstance(df, pd.DataFrame) and "onoffshore_gap" in df.columns:
        try:
            onoff_gap = float(df["onoffshore_gap"].dropna().iloc[-1])
        except Exception:
            pass
    bias_pctile = None
    if isinstance(df, pd.DataFrame) and "fixing_bias" in df.columns:
        try:
            recent = df["fixing_bias"].dropna().tail(252)
            cur = recent.iloc[-1]
            bias_pctile = (recent < cur).mean() * 100
        except Exception:
            pass

    # Decide stance — count active defence vs weakness signals
    defending_signals = 0
    weakening_signals = 0
    if bias is not None:
        if bias < -0.001: defending_signals += 1
        elif bias > +0.001: weakening_signals += 1
    if cnh_stress is not None and cnh_stress > 1.0:
        defending_signals += 1   # CNH liquidity squeeze = active defence
    if onoff_gap is not None:
        if onoff_gap > 0.005: weakening_signals += 1   # CNH weaker than CNY
        elif onoff_gap < -0.005: defending_signals += 1  # CNH stronger

    if defending_signals >= 2 and weakening_signals == 0:
        stance, label_en, label_zh = "defending", "DEFENDING CNY", "防御人民币"
        reading_en = ("Multiple defence levers active — fix biased stronger, "
                      "and either CNH funding squeeze or offshore-onshore basis "
                      "confirms intervention. PBOC is spending policy capital.")
        reading_zh = ("多条防御工具在动 — 中间价定得偏强，叠加 CNH 流动性挤压"
                      "或在离岸价差确认介入。央行正在消耗政策资本。")
    elif weakening_signals >= 2 and defending_signals == 0:
        stance, label_en, label_zh = "weakening", "ALLOWING WEAKNESS", "默许走弱"
        reading_en = ("Fix drifting weaker than DXY-adjusted expectation, "
                      "and offshore market also bids USD higher. PBOC is "
                      "letting CNY find its own level.")
        reading_zh = ("中间价比 DXY 调整后预期更弱，且离岸市场也在做多美元。"
                      "央行让人民币自己找位置。")
    elif defending_signals == 1 and weakening_signals == 0:
        stance, label_en, label_zh = "leaning_defend", "MILD DEFENCE", "轻度防御"
        reading_en = ("One of the three levers shows defence; others quiet. "
                      "Soft signal, not full intervention.")
        reading_zh = ("三条工具里有一条出现防御信号，其他静音。属于软信号，"
                      "不是全面干预。")
    elif weakening_signals == 1 and defending_signals == 0:
        stance, label_en, label_zh = "leaning_weak", "MILD TILT WEAK", "轻度允许走弱"
        reading_en = ("One signal mildly tilts toward weaker CNY tolerance.")
        reading_zh = ("有一条信号轻度倾向允许人民币走弱。")
    else:
        stance, label_en, label_zh = "neutral", "NEUTRAL · hands-off", "中性 · 被动观察"
        reading_en = ("None of the three defence levers is active. PBOC is "
                      "letting market dynamics run; current spot level appears "
                      "inside the tolerance band.")
        reading_zh = ("三条防御工具都没有出手。央行让市场自己跑，当前汇率水平"
                      "在容忍区间内。")

    def signal_row(name_en, name_zh, value, fmt, defend_test, weaken_test):
        if value is None:
            return [name_en, name_zh, "—", "—", "neutral"]
        formatted = fmt(value)
        if defend_test(value):
            color = "defend"
        elif weaken_test(value):
            color = "weaken"
        else:
            color = "neutral"
        return [name_en, name_zh, formatted, color]

    signals = [
        signal_row("Fixing bias", "中间价偏离",
                   bias, lambda v: f"{v*10000:+.0f} pips",
                   lambda v: v < -0.001, lambda v: v > +0.001),
        signal_row("CNH funding stress", "CNH 资金紧张",
                   cnh_stress, lambda v: f"{v:+.2f}%",
                   lambda v: v > 1.0, lambda v: v < -0.5),
        signal_row("On/Off basis", "在/离岸价差",
                   onoff_gap, lambda v: f"{v:+.4f}",
                   lambda v: v < -0.005, lambda v: v > 0.005),
    ]

    return {
        "stance":     stance,
        "label_en":   label_en,
        "label_zh":   label_zh,
        "signals":    signals,
        "reading_en": reading_en,
        "reading_zh": reading_zh,
        "bias_pctile": bias_pctile,
    }


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


def build_decision_layer(snap: dict, df: pd.DataFrame) -> dict:
    """v3.4 — produce the verdict + policy-stance dicts that feed the
    headline cards on the dashboard. Called from build.py after
    latest_snapshot() so it can read the formatted snapshot values."""
    return {
        "carry_verdict":  interpret_carry_verdict(snap),
        "policy_stance":  interpret_policy_stance(snap, df),
    }
