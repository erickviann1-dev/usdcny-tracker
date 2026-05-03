"""
v3.4 · Cross-check / data integrity audit.

Runs after every build. For each numerical relationship that ought to
hold by construction or empirical regularity, asserts the relationship
and writes a pass/warn/fail report into data.json under `cross_checks`.

These are *internal consistency* checks — they prove the math is sane
and the data isn't corrupt — plus a few external sanity bounds. They
do not require scraping a paid second source. Good enough to surface a
"data integrity OK" green badge on the dashboard.

Each check returns a dict:
  { name, status: 'pass'|'warn'|'fail', detail }
"""
from __future__ import annotations
import math
import pandas as pd


def _f(snap: dict, key: str):
    v = snap.get(key)
    if v is None or v == "N/A" or v == "—":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _check(name_en: str, name_zh: str, ok: bool | None,
           detail: str, warn_only: bool = False) -> dict:
    if ok is None:
        status = "skip"
    elif ok:
        status = "pass"
    elif warn_only:
        status = "warn"
    else:
        status = "fail"
    return {"name_en": name_en, "name_zh": name_zh,
            "status": status, "detail": detail}


def run_cross_checks(snap: dict, df: pd.DataFrame) -> list[dict]:
    """Return a list of cross-check dicts. Caller writes them into the
    JSON payload under `cross_checks`."""
    checks: list[dict] = []

    # ── 1. Hedged-carry math identity ──────────────────────────
    # By construction:
    #   hedged_offshore − hedged_onshore ≈ −(cnh_hibor_1y − shibor_1y)
    #                                    = −cnh_funding_stress
    # Because: hedged = (1+rUS)(F/S) − (1+rCN)
    # Onshore uses Shibor; offshore uses CNH HIBOR. Difference is purely
    # in the rCN term, so on − off = (cnh − shibor) = cnh_funding_stress.
    on  = _f(snap, "hedged_carry_proxy")
    off = _f(snap, "hedged_carry_offshore")
    stress = _f(snap, "cnh_funding_stress")
    if on is not None and off is not None and stress is not None:
        observed = on - off
        delta = abs(observed - stress)
        ok = delta < 0.05
        checks.append(_check(
            "Hedged carry math identity",
            "对冲后回报数学恒等式",
            ok,
            f"on − off = {observed:+.3f}%, expected ≈ stress {stress:+.3f}%, "
            f"|delta| = {delta:.4f}% (< 0.05% ⇒ pass)"
        ))

    # ── 2. CNY ↔ CNH basis sanity ──────────────────────────────
    cny = _f(snap, "usdcny")
    cnh = _f(snap, "usdcnh")
    if cny is not None and cnh is not None and cny > 0:
        basis_pct = abs(cny - cnh) / cny * 100
        ok = basis_pct < 1.0
        checks.append(_check(
            "On/Off basis range",
            "在岸/离岸价差范围",
            ok,
            f"|CNY − CNH| / CNY = {basis_pct:.3f}% "
            f"(typically < 1%; spike ⇒ liquidity event)",
            warn_only=True,
        ))

    # ── 3. PBOC fix vs spot proximity (±2% trading band) ───────
    fix = _f(snap, "pboc_fix")
    if fix is not None and cny is not None and cny > 0:
        diff_pct = abs(fix - cny) / cny * 100
        ok = diff_pct < 2.0
        checks.append(_check(
            "PBOC fix vs spot",
            "中间价 vs 即期",
            ok,
            f"|fix − spot| / spot = {diff_pct:.3f}% (PBOC band is ±2%)"
        ))

    # ── 4. DXY day-over-day sanity (no >5% daily moves) ────────
    if isinstance(df, pd.DataFrame) and "dxy" in df.columns:
        last = df["dxy"].dropna().tail(2)
        if len(last) == 2 and last.iloc[-2] != 0:
            d_pct = abs((last.iloc[-1] - last.iloc[-2]) / last.iloc[-2]) * 100
            ok = d_pct < 5.0
            checks.append(_check(
                "DXY day-over-day move",
                "DXY 日内变动",
                ok,
                f"|Δ DXY| = {d_pct:.3f}% (alarm if > 5%)"
            ))

    # ── 5. CNH HIBOR vs Shibor sane spread ─────────────────────
    cnh1y = _f(snap, "cnh_hibor_1y")
    shi1y = _f(snap, "shibor_1y")
    if cnh1y is not None and shi1y is not None:
        spread = cnh1y - shi1y
        # Empirical historical range: −1.5% to +6%
        ok = -1.5 < spread < 6.0
        checks.append(_check(
            "CNH HIBOR vs Shibor spread",
            "CNH HIBOR 与 Shibor 价差",
            ok,
            f"spread = {spread:+.3f}% (typical range −1.5% to +6%)",
            warn_only=True,
        ))

    # ── 6. Bond yields in plausible ranges ─────────────────────
    cn2y = _f(snap, "cn_2y")
    us2y = _f(snap, "us_2y")
    if cn2y is not None:
        ok = 0.3 < cn2y < 5.0
        checks.append(_check(
            "CN 2Y in plausible range",
            "中国 2 年国债利率合理性",
            ok,
            f"cn_2y = {cn2y:.3f}% (expected 0.3–5%)"
        ))
    if us2y is not None:
        ok = 0.5 < us2y < 8.0
        checks.append(_check(
            "US 2Y in plausible range",
            "美国 2 年国债利率合理性",
            ok,
            f"us_2y = {us2y:.3f}% (expected 0.5–8%)"
        ))

    # ── 7. Composite score in [0,100] ──────────────────────────
    score = _f(snap, "composite_score")
    if score is not None:
        ok = 0 <= score <= 100
        checks.append(_check(
            "Composite score bounds",
            "综合分数边界 [0,100]",
            ok,
            f"composite_score = {score:.1f} (must be 0–100)"
        ))

    # ── 8. CIP deviation magnitude sanity ──────────────────────
    cip = _f(snap, "cip_deviation")
    if cip is not None and cny is not None:
        magnitude_pct = abs(cip) / cny * 100
        ok = magnitude_pct < 15.0
        checks.append(_check(
            "CIP deviation magnitude",
            "CIP 偏离量级",
            ok,
            f"|cip_dev| / spot = {magnitude_pct:.2f}% "
            f"(typical < 10%; > 15% suggests data error)",
            warn_only=True,
        ))

    return checks


def summarize(checks: list[dict]) -> dict:
    """Counts for the dashboard badge."""
    counts = {"pass": 0, "warn": 0, "fail": 0, "skip": 0}
    for c in checks:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    overall = "pass" if counts["fail"] == 0 and counts["warn"] == 0 \
              else ("warn" if counts["fail"] == 0 else "fail")
    return {"overall": overall, "counts": counts, "total": len(checks)}
