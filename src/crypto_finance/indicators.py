"""Cycle indicators — the notebooks, rebuilt as causal, tested functions.

The original notebooks fit models on the *whole* sample and plotted history
as if you could have known it at the time. The versions here are the ones
that power the live dashboard at amanthakkar.com: every value at day ``t``
is computed from data up to day ``t`` only (expanding fits), so past values
never rewrite when new prices arrive. ``tests/test_indicators.py`` proves
the no-look-ahead property by truncation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import GENESIS


def _expanding_ols_slope_intercept(x: np.ndarray, y: np.ndarray):
    """Cumulative-sum expanding OLS — O(n), numerically stable enough in
    float64 for log-log series of this length."""
    n = np.arange(1, len(x) + 1, dtype=float)
    sx, sy = np.cumsum(x), np.cumsum(y)
    sxx, sxy = np.cumsum(x * x), np.cumsum(x * y)
    denom = n * sxx - sx * sx
    denom[denom == 0] = np.nan
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept


def power_law_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Expanding (causal) power-law fit + every series derived from it.

    Model per day t:  log10(price) = a_t + b_t * log10(days since genesis),
    fit on all history up to t. Residual = log10(price) - fitted.
    """
    out = df.copy()
    days = (out.index - GENESIS).days.to_numpy(dtype=float)
    days = np.maximum(days, 1)
    x, y = np.log10(days), np.log10(out["price"].to_numpy())
    slope, intercept = _expanding_ols_slope_intercept(x, y)
    fitted = intercept + slope * x
    residual = y - fitted
    out["residual"] = residual

    # Expanding percentile rank + decile (rank of today's residual among all
    # residuals seen so far) — searchsorted over a growing sorted array.
    ranks = np.empty(len(residual))
    sorted_res = np.array([], dtype=float)
    for i, r in enumerate(residual):
        pos = np.searchsorted(sorted_res, r, side="right")
        sorted_res = np.insert(sorted_res, pos, r)
        ranks[i] = (pos + 1) / (i + 1) if i else 1.0
        # count of values <= r is pos+1 after insert-consistent ordering
        ranks[i] = np.searchsorted(sorted_res, r, side="right") / (i + 1)
    out["rank"] = ranks
    out["decile"] = np.clip(np.ceil(ranks * 10), 1, 10).astype(int)

    # Sigma risk: residual as expanding z-score, clamped +-3, mapped to 0..1
    s = pd.Series(residual)
    std = s.expanding().std().replace(0, np.nan)
    z = (s / std).clip(-3, 3)
    out["risk_sigma"] = (z / 6 + 0.5).to_numpy()

    # Corridor: ONE global fit (look-ahead by design — labelled as such),
    # fair value with +-1.5 sigma bands. Context, not a causal signal.
    gx, gy = x, y
    b, a = np.polyfit(gx, gy, 1)
    gfit = a + b * gx
    sigma = float(np.std(gy - gfit))
    out["fair_value"] = 10 ** gfit
    out["fair_value_upper"] = 10 ** (gfit + 1.5 * sigma)
    out["fair_value_lower"] = 10 ** (gfit - 1.5 * sigma)
    return out


def classic_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Moving-average family: Mayer Multiple, Pi Cycle, MA-stretch risk."""
    out = df.copy()
    price = out["price"]
    out["mayer"] = price / price.rolling(200).mean()
    out["pi_cycle_111"] = price.rolling(111).mean()
    out["pi_cycle_350x2"] = 2 * price.rolling(350).mean()
    # MA stretch (open recreation in the Cowen tradition):
    # (ln P - ln MA365) * t^0.395, expanding min-max -> 0..1
    ma365 = price.rolling(365).mean()
    t = np.arange(1, len(price) + 1, dtype=float)
    preavg = (np.log(price) - np.log(ma365)) * t ** 0.395
    lo, hi = preavg.expanding().min(), preavg.expanding().max()
    out["ma_stretch"] = (preavg - lo) / (hi - lo)
    return out


def all_btc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    return classic_indicators(power_law_frame(df))


def regression_rainbow(df: pd.DataFrame, bands: int = 9) -> pd.DataFrame:
    """Logarithmic regression 'rainbow': log10(price) regressed on
    log10(days since genesis) — the BlockchainCenter construction — with
    residual-std bands. A time-linear fit can't span $0.07 → $100k; the
    log-time fit can, which is the whole point of the rainbow. Global fit
    (look-ahead in history, labelled as such); the honest summary is the
    *current* band."""
    out = df.copy()
    days = np.maximum((out.index - GENESIS).days.to_numpy(dtype=float), 1)
    t = np.log10(days)
    y = np.log10(out["price"].to_numpy())
    b, a = np.polyfit(t, y, 1)
    fit = a + b * t
    resid_std = float(np.std(y - fit))
    out["rainbow_fit"] = 10 ** fit
    width = resid_std * 2 / bands
    for k in range(bands + 1):
        out[f"band_{k}"] = 10 ** (fit - resid_std + k * width)
    last_resid = y[-1] - fit[-1]
    band_idx = int(np.clip(np.floor((last_resid + resid_std) / width), 0, bands - 1))
    out.attrs["current_band"] = band_idx
    out.attrs["bands"] = bands
    out.attrs["resid_std"] = resid_std
    return out


def btc_supply(date_index: pd.DatetimeIndex) -> pd.Series:
    """Approximate BTC supply from the halving schedule.

    Each era mines exactly 210,000 blocks, so era-end supplies are exact
    (10.5M, 15.75M, 18.375M, 19.6875M, ...). Within an era, interpolate
    linearly by elapsed days — within ~0.3% of true supply (blocks don't
    arrive at exactly 144/day, which is why a naive blocks/day integral
    drifts by ~5% over 15 years)."""
    halvings = pd.to_datetime([
        "2009-01-03", "2012-11-28", "2016-07-09", "2020-05-11",
        "2024-04-20", "2028-04-01", "2032-01-01",
    ], utc=True)
    rewards = [50.0, 25.0, 12.5, 6.25, 3.125, 1.5625, 0.78125]
    era_supply = np.concatenate([[0.0], np.cumsum([210_000 * r for r in rewards])])
    out = np.empty(len(date_index))
    for i, d in enumerate(date_index):
        era = int(np.searchsorted(halvings, d, side="right") - 1)
        era = min(max(era, 0), len(rewards) - 1)
        start, end = halvings[era], halvings[era + 1]
        frac = (d - start).days / max((end - start).days, 1)
        out[i] = era_supply[era] + frac * 210_000 * rewards[era]
    return pd.Series(out, index=date_index, dtype=float)


def stock_to_flow(df: pd.DataFrame) -> pd.DataFrame:
    """Stock-to-flow ratio + the classic log-log model price, with the
    model's failure modes left in the open (see README): fitted on monthly
    data, famous, and broken post-2021 — included as history, not gospel."""
    out = df.copy()
    stock = btc_supply(out.index)
    flow_annual = stock.diff(365)  # approx annual production
    out["sf_ratio"] = stock / flow_annual
    monthly = out.resample("M").last().dropna(subset=["sf_ratio"])
    m = (monthly["sf_ratio"] > 0) & (monthly["price"] > 0)
    b, a = np.polyfit(np.log(monthly.loc[m, "sf_ratio"]),
                      np.log(monthly.loc[m, "price"]), 1)
    out["sf_model_price"] = np.exp(a) * out["sf_ratio"] ** b
    out.attrs["sf_slope"], out.attrs["sf_intercept"] = float(b), float(a)
    return out
