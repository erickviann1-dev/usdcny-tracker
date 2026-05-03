"""
Data fetching layer — pulls from akshare (CN data), yfinance (FX), with
graceful fallbacks and a unified aligned DataFrame as output.
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path
from config import START_DATE, END_DATE


# Incremental store of CFETS USD/CNY 1Y all-in forward (全价) from fx_c_swap_cm.
# Each successful build appends/updates the latest fixing so history grows over time.
CFETS_FWD_CACHE = Path(__file__).resolve().parent / "cache" / "cfets_usdcny_1y_fwd.csv"


# ─────────────────────────────────────────────────────────────
#  Individual fetchers
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_bond_yields() -> pd.DataFrame:
    """
    China & US 2Y government bond yields via akshare.
    Returns DataFrame with columns: cn_2y, us_2y (index = date).
    Falls back to SHIBOR-based proxy for CN if primary fails.
    """
    try:
        import akshare as ak
        raw = ak.bond_zh_us_rate(start_date=START_DATE)

        # First column is date — convert and set as index
        raw = raw.copy()
        raw.iloc[:, 0] = pd.to_datetime(raw.iloc[:, 0])
        raw = raw.set_index(raw.columns[0]).sort_index()
        raw.index.name = "date"

        # Schema (positional, robust to encoding):
        #  [CN_2Y, CN_5Y, CN_10Y, CN_30Y, CN_10-2, CN_GDP,
        #   US_2Y, US_5Y, US_10Y, US_30Y, US_10-2, US_GDP]
        numeric = raw.select_dtypes(include=[np.number])
        if numeric.shape[1] < 7:
            raise ValueError(f"Unexpected schema: {numeric.shape[1]} numeric cols")

        out = pd.DataFrame(index=raw.index)
        out["cn_2y"] = pd.to_numeric(numeric.iloc[:, 0], errors="coerce")
        out["us_2y"] = pd.to_numeric(numeric.iloc[:, 6], errors="coerce")

        # Sanity check: typical ranges
        if not (out["cn_2y"].mean() < 5 and 1 < out["us_2y"].mean() < 7):
            # Fallback: scan columns for sensible ranges
            for i in range(numeric.shape[1]):
                col = pd.to_numeric(numeric.iloc[:, i], errors="coerce")
                m = col.mean()
                if 0.5 < m < 4 and out["cn_2y"].isna().all():
                    out["cn_2y"] = col
                elif 1.5 < m < 7 and out["us_2y"].isna().all():
                    out["us_2y"] = col

        return out.dropna(how="all")

    except Exception as e:
        st.warning(f"⚠️ Bond yield fetch (akshare) failed: {e}. Using SHIBOR proxy for CN.")
        return _fallback_yields()


def _fallback_yields() -> pd.DataFrame:
    """SHIBOR 1Y as proxy for CN 2Y + Yahoo Finance for US 2Y."""
    try:
        import akshare as ak
        shibor = ak.rate_interbank(market="上海银行间同业拆放利率", symbol="Shibor人民币", period="1年")
        shibor.columns = shibor.columns.str.strip()
        date_col = shibor.columns[0]
        rate_col = [c for c in shibor.columns if c != date_col][0]
        shibor = shibor.rename(columns={date_col: "date", rate_col: "cn_2y"})
        shibor["date"] = pd.to_datetime(shibor["date"])
        shibor = shibor.set_index("date").sort_index()
        shibor["cn_2y"] = pd.to_numeric(shibor["cn_2y"], errors="coerce")
    except Exception:
        idx = pd.date_range(start=START_DATE, end=END_DATE, freq="B")
        shibor = pd.DataFrame({"cn_2y": np.nan}, index=idx)

    us = _fetch_us_2y_yf()
    return shibor[["cn_2y"]].join(us, how="outer").ffill().dropna(how="all")


def _fetch_us_2y_yf() -> pd.Series:
    try:
        ticker = yf.Ticker("^IRX")   # 13-week; use TNX proxy scaled
        # ^IRX = 13w T-bill; for 2Y use "2YY=F" or approximate from TNX
        data = yf.download("^FVX", start=START_DATE[:4]+"-"+START_DATE[4:6]+"-"+START_DATE[6:],
                           end=END_DATE[:4]+"-"+END_DATE[4:6]+"-"+END_DATE[6:],
                           auto_adjust=True, progress=False)
        s = data["Close"].squeeze() * 0.5  # FVX is 5Y, rough proxy
        s.name = "us_2y"
        return s
    except Exception:
        try:
            data = yf.download("^TNX", start=_yfdate(START_DATE), end=_yfdate(END_DATE),
                               auto_adjust=True, progress=False)
            s = data["Close"].squeeze() * 0.8
            s.name = "us_2y"
            return s
        except Exception:
            return pd.Series(name="us_2y", dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fx_spot() -> pd.DataFrame:
    """
    USD/CNY onshore spot + USD/CNH offshore spot from yfinance.
    Returns DataFrame: usdcny, usdcnh (index = date).
    """
    start = _yfdate(START_DATE)
    end   = _yfdate(END_DATE)
    out   = pd.DataFrame()

    ticker_variants = {
        "usdcny": ["USDCNY=X", "CNY=X"],
        "usdcnh": ["USDCNH=X", "CNH=X"],
    }
    for col, tickers in ticker_variants.items():
        picked = pd.Series(dtype=float)
        for ticker in tickers:
            try:
                raw = yf.download(ticker, start=start, end=end,
                                  auto_adjust=True, progress=False)
                if raw.empty:
                    continue
                s = raw["Close"].squeeze()
                s.name = col
                if s.notna().sum() >= 10:
                    picked = s
                    break
            except Exception as e:
                st.warning(f"⚠️ FX fetch ({ticker}) failed: {e}")
        if not picked.empty:
            out = picked.to_frame() if out.empty else out.join(picked, how="outer")

    # Onshore USD/CNY is critical for Layer 3. If Yahoo fails, try dedicated fallbacks.
    usdcny_ok = ("usdcny" in out.columns and _is_valid_usdcny_series(out["usdcny"]))
    if not usdcny_ok:
        usdcny_fallback = fetch_usdcny_onshore_spot()
        if not usdcny_fallback.empty:
            if out.empty:
                out = usdcny_fallback.to_frame("usdcny")
            elif "usdcny" not in out.columns:
                out = out.join(usdcny_fallback.rename("usdcny"), how="outer")
            else:
                out["usdcny"] = out["usdcny"].combine_first(usdcny_fallback)

    # Offshore USD/CNH is critical for Layer 3 market anchor.
    usdcnh_ok = ("usdcnh" in out.columns and _is_valid_usdcny_series(out.get("usdcnh", pd.Series(dtype=float))))
    if not usdcnh_ok:
        usdcnh_fallback = fetch_usdcnh_offshore_spot()
        if not usdcnh_fallback.empty:
            if out.empty:
                out = usdcnh_fallback.to_frame("usdcnh")
            elif "usdcnh" not in out.columns:
                out = out.join(usdcnh_fallback.rename("usdcnh"), how="outer")
            else:
                out["usdcnh"] = out["usdcnh"].combine_first(usdcnh_fallback)

    return out.ffill().dropna(how="all")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_pboc_fixing() -> pd.Series:
    """
    PBOC daily central parity (mid-price fixing) for USD/CNY.
    Source: akshare → currency_boc_sina.
    Returns Series named 'pboc_fix' (index = date).
    """
    try:
        import akshare as ak
        raw = ak.currency_boc_sina(start_date=START_DATE, end_date=END_DATE)
        raw.columns = raw.columns.str.strip()

        date_col = [c for c in raw.columns if "日期" in c or "date" in c.lower()]
        usd_col  = [c for c in raw.columns if "美元" in c or "USD" in c.upper()]

        if not date_col:
            date_col = [raw.columns[0]]
        if not usd_col:
            usd_col = [raw.columns[1]]

        raw["date"]     = pd.to_datetime(raw[date_col[0]])
        raw["pboc_fix"] = pd.to_numeric(raw[usd_col[0]], errors="coerce")
        s = raw.set_index("date")["pboc_fix"].sort_index()

        # akshare returns CNY per 100 USD → convert to USD/CNY
        if s.mean() > 100:
            s = s / 100

        return s.dropna()

    except Exception as e:
        st.warning(f"⚠️ PBOC fixing fetch failed: {e}. Fixing Bias (Layer 3) will be estimated.")
        return pd.Series(name="pboc_fix", dtype=float)


# ─────────────────────────────────────────────────────────────
#  Master data assembly
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_dxy() -> pd.Series:
    """
    DXY (US Dollar Index) — the "soul variable" for de-noising the regression.

    Try-order:
      1. yfinance DX-Y.NYB  (canonical ICE DXY; SSL may fail on some networks)
      2. akshare macro_usa_real_dollar_index (Trade-weighted, FRED proxy)
      3. akshare index_investing_global / fx_quote_baidu
      4. FRED CSV direct: DTWEXBGS (Broad Dollar Index — proxy, ~95% corr to DXY)

    Returns: Series named 'dxy' indexed by date.
    """
    # ── Attempt 1: yfinance ─────────────────────────────────
    try:
        raw = yf.download("DX-Y.NYB",
                          start=_yfdate(START_DATE),
                          end=_yfdate(END_DATE),
                          auto_adjust=True, progress=False)
        if not raw.empty:
            s = raw["Close"].squeeze()
            s.name = "dxy"
            return s.dropna()
    except Exception:
        pass

    # ── Attempt 2 & 3: akshare ──────────────────────────────
    try:
        import akshare as ak
        for fn_name in ["macro_usa_real_dollar_index",
                        "index_investing_global",
                        "fx_quote_baidu"]:
            try:
                fn = getattr(ak, fn_name, None)
                if fn is None: continue
                raw = fn() if fn_name == "macro_usa_real_dollar_index" else None
                if raw is None: continue
                date_col = next((c for c in raw.columns
                                 if "日期" in c or "date" in c.lower() or "时间" in c), raw.columns[0])
                val_col = next((c for c in raw.columns
                                if any(k in str(c).lower() for k in ["指数", "index", "value", "美元"])
                                and c != date_col), None)
                if val_col is None:
                    val_col = raw.select_dtypes(include=[np.number]).columns[0]
                raw = raw[[date_col, val_col]].copy()
                raw.columns = ["date", "dxy"]
                raw["date"] = pd.to_datetime(raw["date"])
                raw["dxy"] = pd.to_numeric(raw["dxy"], errors="coerce")
                s = raw.set_index("date")["dxy"].sort_index().dropna()
                s = s[s.index >= pd.Timestamp(START_DATE)]
                if len(s) > 30:
                    return s
            except Exception:
                continue
    except Exception:
        pass

    # ── Attempt 4: FRED direct CSV (no auth) ────────────────
    try:
        import requests
        url = ("https://fred.stlouisfed.org/graph/fredgraph.csv"
               f"?id=DTWEXBGS&cosd={START_DATE[:4]}-{START_DATE[4:6]}-{START_DATE[6:]}")
        resp = requests.get(url, timeout=15, verify=False)
        if resp.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(resp.text))
            date_c = df.columns[0]
            val_c  = df.columns[1]
            df[date_c] = pd.to_datetime(df[date_c])
            df[val_c]  = pd.to_numeric(df[val_c], errors="coerce")
            s = df.set_index(date_c)[val_c].sort_index().dropna()
            s.name = "dxy"
            return s
    except Exception as e:
        st.warning(f"⚠️ DXY fetch (all sources) failed: {e}")

    return pd.Series(name="dxy", dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_usdcny_onshore_spot() -> pd.Series:
    """
    Dedicated USD/CNY onshore spot fetcher.
    Try-order:
      1) akshare.forex_hist_em with multiple symbol variants
      2) Eastmoney kline direct endpoint
      3) FRED DEXCHUS CSV (lower frequency fallback)
    """
    # ── Attempt 1: akshare forex_hist_em (symbol variants) ─────────
    try:
        import akshare as ak
        symbols = [
            "USDCNY",
            "USD/CNY",
            "USDCNY.FXCM",
            "USDCNYC",
            "美元人民币",
        ]
        for symbol in symbols:
            try:
                raw = ak.forex_hist_em(symbol=symbol)
                s = _extract_fx_series(raw, value_aliases=("收盘", "close", "最新价", "price"))
                if _is_valid_usdcny_series(s):
                    return s.rename("usdcny")
            except Exception:
                continue
    except Exception:
        pass

    # ── Attempt 2: Eastmoney direct kline API ───────────────────────
    s_em = _fetch_usdcny_eastmoney()
    if _is_valid_usdcny_series(s_em):
        return s_em.rename("usdcny")

    # ── Attempt 3: FRED DEXCHUS (fallback, lower frequency) ─────────
    s_fred = _fetch_usdcny_fred()
    if _is_valid_usdcny_series(s_fred, min_points=10):
        return s_fred.rename("usdcny")

    return pd.Series(name="usdcny", dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_usdcnh_offshore_spot() -> pd.Series:
    """
    Dedicated USD/CNH offshore spot fetcher.
    Try-order:
      1) akshare.forex_hist_em with multiple symbol variants
      2) Eastmoney kline direct endpoint (CNH secids)
    """
    # ── Attempt 1: akshare forex_hist_em ────────────────────────────
    try:
        import akshare as ak
        symbols = [
            "USDCNH",
            "USD/CNH",
            "USDCNH.FXCM",
            "美元离岸人民币",
        ]
        for symbol in symbols:
            try:
                raw = ak.forex_hist_em(symbol=symbol)
                s = _extract_fx_series(raw, value_aliases=("收盘", "close", "最新价", "price"))
                if _is_valid_usdcny_series(s):
                    return s.rename("usdcnh")
            except Exception:
                continue
    except Exception:
        pass

    # ── Attempt 2: Eastmoney direct kline API (CNH secids) ─────────
    try:
        import requests
        secid_candidates = [
            "133.USDCNH",
            "119.USDCNH",
            "90.USDCNH",
        ]
        for secid in secid_candidates:
            try:
                url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
                params = {
                    "secid": secid,
                    "klt": "101",
                    "fqt": "0",
                    "beg": START_DATE,
                    "end": END_DATE,
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
                }
                resp = requests.get(url, params=params, timeout=12, verify=False)
                if resp.status_code != 200:
                    continue
                payload = resp.json()
                klines = (((payload or {}).get("data") or {}).get("klines")) or []
                if not klines:
                    continue
                rows = [k.split(",") for k in klines if isinstance(k, str) and "," in k]
                if not rows:
                    continue
                df = pd.DataFrame(rows)
                if df.shape[1] < 3:
                    continue
                df = df.rename(columns={0: "date", 2: "usdcnh"})
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df["usdcnh"] = pd.to_numeric(df["usdcnh"], errors="coerce")
                s = df.set_index("date")["usdcnh"].sort_index().dropna()
                s = s[s.index >= pd.Timestamp(START_DATE)]
                if _is_valid_usdcny_series(s):
                    return s
            except Exception:
                continue
    except Exception:
        pass

    return pd.Series(name="usdcnh", dtype=float)


def _fetch_usdcny_eastmoney() -> pd.Series:
    """Fetch USD/CNY from Eastmoney historical kline endpoint."""
    try:
        import requests
        secid_candidates = [
            "133.USDCNY",
            "119.USDCNY",
            "90.USDCNY",
        ]
        start = START_DATE
        end = END_DATE
        for secid in secid_candidates:
            try:
                url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
                params = {
                    "secid": secid,
                    "klt": "101",      # daily
                    "fqt": "0",
                    "beg": start,
                    "end": end,
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
                }
                resp = requests.get(url, params=params, timeout=12, verify=False)
                if resp.status_code != 200:
                    continue
                payload = resp.json()
                klines = (((payload or {}).get("data") or {}).get("klines")) or []
                if not klines:
                    continue
                rows = [k.split(",") for k in klines if isinstance(k, str) and "," in k]
                if not rows:
                    continue
                df = pd.DataFrame(rows)
                # Eastmoney kline fields2: date, open, close, high, low, ...
                if df.shape[1] < 3:
                    continue
                df = df.rename(columns={0: "date", 2: "usdcny"})
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df["usdcny"] = pd.to_numeric(df["usdcny"], errors="coerce")
                s = df.set_index("date")["usdcny"].sort_index().dropna()
                s = s[s.index >= pd.Timestamp(START_DATE)]
                if _is_valid_usdcny_series(s):
                    return s
            except Exception:
                continue
    except Exception:
        pass

    return pd.Series(name="usdcny", dtype=float)


def _fetch_usdcny_fred() -> pd.Series:
    """Fetch USD/CNY from FRED DEXCHUS CSV."""
    try:
        import requests
        url = ("https://fred.stlouisfed.org/graph/fredgraph.csv"
               f"?id=DEXCHUS&cosd={START_DATE[:4]}-{START_DATE[4:6]}-{START_DATE[6:]}")
        resp = requests.get(url, timeout=12, verify=False)
        if resp.status_code != 200:
            return pd.Series(name="usdcny", dtype=float)
        from io import StringIO
        df = pd.read_csv(StringIO(resp.text))
        if df.shape[1] < 2:
            return pd.Series(name="usdcny", dtype=float)
        date_col = df.columns[0]
        val_col = df.columns[1]
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
        s = df.set_index(date_col)[val_col].sort_index().dropna()
        s = s[s.index >= pd.Timestamp(START_DATE)]
        return s.rename("usdcny")
    except Exception:
        return pd.Series(name="usdcny", dtype=float)


def _extract_fx_series(raw: pd.DataFrame, value_aliases=("收盘", "close")) -> pd.Series:
    """Extract date/value series from heterogeneous FX tables."""
    if raw is None or raw.empty:
        return pd.Series(dtype=float)
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    lower_map = {c: c.lower() for c in df.columns}
    date_col = next(
        (c for c in df.columns
         if ("日期" in c) or ("date" in lower_map[c]) or ("时间" in c) or ("day" in lower_map[c])),
        df.columns[0]
    )
    val_col = None
    for c in df.columns:
        lc = lower_map[c]
        if c == date_col:
            continue
        if any(alias.lower() in lc for alias in value_aliases):
            val_col = c
            break
    if val_col is None:
        numeric_cols = [c for c in df.columns if c != date_col and pd.api.types.is_numeric_dtype(df[c])]
        if numeric_cols:
            val_col = numeric_cols[0]
    if val_col is None:
        return pd.Series(dtype=float)
    df["date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["value"] = pd.to_numeric(df[val_col], errors="coerce")
    s = df.set_index("date")["value"].sort_index().dropna()
    s = s[s.index >= pd.Timestamp(START_DATE)]
    return s


def _is_valid_usdcny_series(s: pd.Series, min_points: int = 30) -> bool:
    """Basic sanity filter to avoid mis-mapped columns."""
    if s is None or len(s) < min_points:
        return False
    x = pd.to_numeric(s, errors="coerce").dropna()
    if len(x) < min_points:
        return False
    med = float(x.median())
    return 5.0 < med < 9.0


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fx_akshare() -> pd.DataFrame:
    """
    Akshare-based FX fallback: fetches USD/CNY and USD/CNH from East Money.
    Returns DataFrame with columns: usdcny, usdcnh.
    """
    out = pd.DataFrame()
    try:
        import akshare as ak
        symbol_variants = {
            "usdcny": ["USDCNY", "USD/CNY", "USDCNY.FXCM", "USDCNYC", "美元人民币"],
            "usdcnh": ["USDCNH", "USD/CNH", "USDCNH.FXCM", "美元离岸人民币"],
        }
        for col, symbols in symbol_variants.items():
            try:
                picked = pd.Series(dtype=float)
                for symbol in symbols:
                    try:
                        raw = ak.forex_hist_em(symbol=symbol)
                        s = _extract_fx_series(raw, value_aliases=("收盘", "close", "最新价", "price"))
                        if not s.empty:
                            picked = s.rename(col)
                            break
                    except Exception:
                        continue
                if picked.empty:
                    continue
                out = picked.to_frame() if out.empty else out.join(picked, how="outer")
            except Exception:
                continue
    except Exception:
        pass
    return out


def fetch_shibor_1y() -> pd.Series:
    """
    Shibor 1Y rate (% annualised), the CN-side money-market funding cost
    that anchors the FX swap-point implied yield. Used in v3.1 hedged-carry
    proxy: a CIP-fair 1Y FX swap should cost approximately
    (SOFR1Y_or_UST1Y − Shibor1Y) — deviations reveal CIP basis stress.
    Source: akshare `rate_interbank` (PBOC SHIBOR).
    """
    try:
        import akshare as ak  # lazy import (akshare is heavy; matches other fetchers)
        df = ak.rate_interbank(
            market="上海银行同业拆借市场",   # akshare correct market name
            symbol="Shibor人民币",
            indicator="1年",
        )
    except Exception as e:
        st.warning(f"shibor 1y akshare failed: {e}")
        return pd.Series(dtype=float, name="shibor_1y")

    if df is None or df.empty:
        return pd.Series(dtype=float, name="shibor_1y")

    df.columns = df.columns.str.strip()
    # akshare Shibor returns ['报告日', '利率', '涨跌']
    date_col = next(
        (c for c in df.columns if "报告" in c or "日期" in c or "date" in c.lower()),
        df.columns[0],
    )
    val_col = next(
        (c for c in df.columns if "利率" in c or "Shibor" in c or "rate" in c.lower()),
        [c for c in df.columns if c != date_col][0],
    )
    s = pd.Series(
        pd.to_numeric(df[val_col], errors="coerce").values,
        index=pd.to_datetime(df[date_col]),
        name="shibor_1y",
    ).sort_index()
    return s.dropna()


def load_cfets_usdcny_1y_fwd_cache() -> pd.Series:
    """Load cached 1Y outright forward (CNY per USD) indexed by calendar date."""
    if not CFETS_FWD_CACHE.exists():
        return pd.Series(dtype=float, name="usdcny_fwd_1y")
    df = pd.read_csv(CFETS_FWD_CACHE, parse_dates=["date"])
    if df.empty or "fwd_1y" not in df.columns:
        return pd.Series(dtype=float, name="usdcny_fwd_1y")
    s = pd.to_numeric(df["fwd_1y"], errors="coerce")
    s.index = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    return s.dropna().sort_index().loc[lambda x: x.index.notna()].astype(float)


def update_cfets_usdcny_1y_fwd_cache() -> None:
    """
    Fetch today's USD/CNY 1Y all-in forward from CFETS C-Swap curve (akshare fx_c_swap_cm)
    and merge into CSV cache (one row per calendar date).
    Silent no-op on failure (network/SSL) — analytics will fall back to CIP proxy.
    """
    try:
        import akshare as ak
        raw = ak.fx_c_swap_cm()
        if raw is None or raw.empty:
            return
        tenor_col = raw["期限品种"].astype(str).str.upper().str.strip()
        sub = raw.loc[tenor_col == "1Y"]
        if sub.empty:
            return
        row = sub.iloc[0]
        fwd = float(pd.to_numeric(row["全价汇率"], errors="coerce"))
        if not np.isfinite(fwd) or fwd <= 0:
            return
        pts_raw = row["掉期点(Pips)"] if "掉期点(Pips)" in row.index else np.nan
        pts = float(pd.to_numeric(pts_raw, errors="coerce"))
        if not np.isfinite(pts):
            pts = np.nan
        dt = pd.to_datetime(row["日期时间"], errors="coerce")
        if pd.isna(dt):
            return
        d = dt.normalize()
    except Exception:
        return

    CFETS_FWD_CACHE.parent.mkdir(parents=True, exist_ok=True)
    if CFETS_FWD_CACHE.exists() and CFETS_FWD_CACHE.stat().st_size > 0:
        try:
            prev = pd.read_csv(CFETS_FWD_CACHE, parse_dates=["date"])
        except Exception:
            prev = pd.DataFrame(columns=["date", "fwd_1y", "swap_pts"])
    else:
        prev = pd.DataFrame(columns=["date", "fwd_1y", "swap_pts"])

    new_row = pd.DataFrame([{"date": d, "fwd_1y": fwd, "swap_pts": pts}])
    merged = pd.concat([prev, new_row], ignore_index=True)
    merged["date"] = pd.to_datetime(merged["date"], errors="coerce").dt.normalize()
    merged = merged.dropna(subset=["date"]).drop_duplicates(subset=["date"], keep="last")
    merged = merged.sort_values("date")
    merged.to_csv(CFETS_FWD_CACHE, index=False)


def fetch_us_1y() -> pd.Series:
    """
    US 1Y Treasury yield (% annualised) via FRED CSV (no auth).
    Series: DGS1 — Market Yield on US Treasury Securities at 1-Year
    Constant Maturity. The natural USD-side counterpart to Shibor 1Y.
    """
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS1"
        raw = pd.read_csv(url)
        if raw.shape[1] < 2:
            return pd.Series(dtype=float, name="us_1y")
        date_col, val_col = raw.columns[0], raw.columns[1]
        s = pd.Series(
            pd.to_numeric(raw[val_col], errors="coerce").values,
            index=pd.to_datetime(raw[date_col], errors="coerce"),
            name="us_1y",
        ).sort_index().dropna()
        return s
    except Exception as e:
        st.warning(f"FRED DGS1 fetch failed: {e}")
        return pd.Series(dtype=float, name="us_1y")


@st.cache_data(ttl=3600, show_spinner=False)
def get_master_data() -> tuple[pd.DataFrame, dict]:
    """
    Fetches and aligns all data sources.
    Returns (master_df, data_quality_dict).

    master_df columns:
        cn_2y       — China 2Y govt bond yield (%)
        us_2y       — US 2Y Treasury yield (%)
        yield_spread — US 2Y - CN 2Y (%)
        usdcny      — onshore USD/CNY spot
        usdcnh      — offshore USD/CNH spot
        pboc_fix    — PBOC daily fixing
        onoffshore_gap — usdcnh - usdcny (CNH premium/discount)
        usdcny_fwd_1y — USD/CNY 1Y all-in forward from CFETS cache (after first cache date)
    """
    bonds    = fetch_bond_yields()
    fx       = fetch_fx_spot()
    fix      = fetch_pboc_fixing()
    dxy      = fetch_dxy()
    shibor1y = fetch_shibor_1y()      # v3.1: money-market CN funding cost
    us1y     = fetch_us_1y()          # v3.1: money-market US funding cost

    update_cfets_usdcny_1y_fwd_cache()
    fwd_1y_hist = load_cfets_usdcny_1y_fwd_cache()

    # If yfinance gave us nothing, try akshare for FX
    if fx.empty or "usdcny" not in fx.columns or fx["usdcny"].notna().sum() < 30:
        ak_fx = fetch_fx_akshare()
        if not ak_fx.empty:
            for col in ak_fx.columns:
                if col not in fx.columns or fx[col].notna().sum() < 30:
                    fx = pd.concat([fx, ak_fx[[col]]], axis=1) if col not in fx.columns else fx
                    fx[col] = ak_fx[col].reindex(fx.index, method="nearest") if col in fx.columns and not fx.empty else ak_fx[col]
            if fx.empty:
                fx = ak_fx

    # Never backfill onshore spot with fixing proxy:
    # for Layer 3, missing market spot is better than fake spot.
    if fx.empty or "usdcny" not in fx.columns or fx["usdcny"].notna().sum() < 30:
        st.warning("⚠️ USD/CNY onshore spot unavailable from market sources. Keeping usdcny as missing (no fixing substitution).")

    # Align on business-day index
    idx = pd.date_range(
        start=max(bonds.index.min() if not bonds.empty else pd.Timestamp(START_DATE),
                  fx.index.min()    if not fx.empty    else pd.Timestamp(START_DATE)),
        end=pd.Timestamp(END_DATE),
        freq="B"
    )

    df = pd.DataFrame(index=idx)
    for col in ["cn_2y", "us_2y"]:
        if col in bonds.columns:
            df[col] = bonds[col].reindex(idx, method="ffill")

    for col in ["usdcny", "usdcnh"]:
        if col in fx.columns:
            df[col] = fx[col].reindex(idx, method="ffill")

    if not fix.empty:
        df["pboc_fix"] = fix.reindex(idx, method="ffill")

    if not dxy.empty:
        df["dxy"] = dxy.reindex(idx, method="ffill")
        df["dxy_ret"] = df["dxy"].pct_change()    # daily % return → overnight proxy

    # v3.1 — Money-market 1Y funding rates (Shibor / UST 1Y)
    if not shibor1y.empty:
        df["shibor_1y"] = shibor1y.reindex(idx, method="ffill")
    if not us1y.empty:
        df["us_1y"] = us1y.reindex(idx, method="ffill")

    # Derived columns
    if "us_2y" in df and "cn_2y" in df:
        df["yield_spread"] = df["us_2y"] - df["cn_2y"]

    # v3.1 — Money-market spread (USD−CNY), the Libor-Shibor analog using
    # SOFR-anchored 1Y UST as the USD leg (legacy Libor was discontinued 2023-06).
    if "us_1y" in df and "shibor_1y" in df:
        df["mm_spread"] = df["us_1y"] - df["shibor_1y"]

    if "usdcnh" in df and "usdcny" in df:
        df["onoffshore_gap"] = df["usdcnh"] - df["usdcny"]

    if not fwd_1y_hist.empty:
        first_obs = fwd_1y_hist.index.min()
        ser = fwd_1y_hist.reindex(idx).ffill()
        ser = ser.where(ser.index >= first_obs, np.nan)
        df["usdcny_fwd_1y"] = ser

    df = df.dropna(how="all").ffill(limit=5)

    quality = {
        "cn_2y":     df["cn_2y"].notna().mean()     if "cn_2y"     in df else 0,
        "us_2y":     df["us_2y"].notna().mean()     if "us_2y"     in df else 0,
        "usdcny":    df["usdcny"].notna().mean()    if "usdcny"    in df else 0,
        "usdcnh":    df["usdcnh"].notna().mean()    if "usdcnh"    in df else 0,
        "pboc_fix":  df["pboc_fix"].notna().mean()  if "pboc_fix"  in df else 0,
        "dxy":       df["dxy"].notna().mean()       if "dxy"       in df else 0,
        "shibor_1y": df["shibor_1y"].notna().mean() if "shibor_1y" in df else 0,
        "us_1y":     df["us_1y"].notna().mean()     if "us_1y"     in df else 0,
        "usdcny_fwd_1y": df["usdcny_fwd_1y"].notna().mean() if "usdcny_fwd_1y" in df else 0,
    }

    return df, quality


# ─────────────────────────────────────────────────────────────
#  Utilities
# ─────────────────────────────────────────────────────────────

def _yfdate(yyyymmdd: str) -> str:
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"
