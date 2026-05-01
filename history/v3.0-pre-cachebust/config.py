import os
from datetime import datetime, timedelta

# ── Date Range ──────────────────────────────────────────────
LOOKBACK_DAYS = 730          # 2-year history
START_DATE = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d")
END_DATE   = datetime.now().strftime("%Y%m%d")

# ── Alert Thresholds ─────────────────────────────────────────
RAW_CARRY_ALERT   = 2.5      # % — flag when US-CN 2Y spread > this
HEDGED_CARRY_ALERT = 0.5     # % — flag when hedged carry still positive
CIP_BASIS_ALERT   = 1.0      # % — flag when CIP deviation > this
FIXING_BIAS_ALERT = 150      # pips — flag when PBOC bias > this in abs terms

# ── Composite Score Weights ──────────────────────────────────
W_CARRY   = 0.35   # Layer 1 weight
W_MISPR   = 0.30   # Layer 2 weight
W_FIXING  = 0.35   # Layer 3 weight

# ── Color Palette ────────────────────────────────────────────
COLOR_BG        = "#0d1117"
COLOR_CARD      = "#161b22"
COLOR_BORDER    = "#30363d"
COLOR_USD_BULL  = "#ef4444"   # red  = USD strength / CNY pressure
COLOR_CNY_BULL  = "#22c55e"   # green = CNY strength
COLOR_NEUTRAL   = "#facc15"   # yellow = neutral
COLOR_LINE_US   = "#60a5fa"   # blue
COLOR_LINE_CN   = "#f97316"   # orange

PRESSURE_ZONES = [
    (0,  25,  "#22c55e", "低压力 Low"),
    (25, 50,  "#84cc16", "温和 Moderate"),
    (50, 75,  "#facc15", "偏高 Elevated"),
    (75, 90,  "#f97316", "高压 High"),
    (90, 100, "#ef4444", "极端 Extreme"),
]
