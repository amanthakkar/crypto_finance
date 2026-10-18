"""The tests that make this repo different from the notebooks:

1. NO LOOK-AHEAD — truncating the future must not change any past
   expanding indicator value. (The notebooks failed this by construction.)
2. The power-law recovery test — synthetic data generated from a known
   power law must come back with ~zero residual.
3. Sanity ranges on the classic indicators.
"""
import numpy as np
import pandas as pd
import pytest

from crypto_finance.indicators import (all_btc_indicators, btc_supply,
                                       power_law_frame, regression_rainbow)


def synthetic_power_law(n=1500, slope=5.5, intercept=-20.0, noise=0.0, seed=1):
    idx = pd.date_range("2012-01-01", periods=n, freq="D", tz="UTC")
    days = np.maximum((idx - pd.Timestamp("2009-01-03", tz="UTC")).days, 1)
    y = intercept + slope * np.log10(days)
    rng = np.random.default_rng(seed)
    y = y + rng.normal(0, noise, n)
    return pd.DataFrame({"price": 10 ** y}, index=idx)


def test_no_lookahead():
    df = synthetic_power_law(noise=0.15)
    full = all_btc_indicators(df)
    cut = all_btc_indicators(df.iloc[:1000])
    for col in ["residual", "rank", "decile", "risk_sigma"]:
        pd.testing.assert_series_equal(
            full[col].iloc[:1000], cut[col], check_names=False)


def test_power_law_recovery():
    frame = power_law_frame(synthetic_power_law(noise=0.0))
    assert np.nanmax(np.abs(frame["residual"].iloc[100:])) < 0.05
    assert frame["rank"].iloc[-1] == pytest.approx(0.5, abs=0.35)


def test_classic_indicator_ranges():
    frame = all_btc_indicators(synthetic_power_law(noise=0.2))
    tail = frame.iloc[400:]
    # Mayer on a smooth synthetic curve can run hot (no drawdowns to pull
    # the 200d average up) — the invariant is positive & finite, not a band.
    assert (tail["mayer"] > 0).all() and np.isfinite(tail["mayer"]).all()
    assert tail["risk_sigma"].between(0, 1).all()
    assert tail["decile"].between(1, 10).all()


def test_supply_schedule():
    idx = pd.to_datetime(["2024-04-19", "2024-04-21"], utc=True)
    s = btc_supply(idx)
    assert 19_500_000 < s.iloc[0] < 19_800_000  # ~19.7M just pre-4th halving
    assert s.iloc[1] > s.iloc[0]


def test_rainbow_band_in_range():
    frame = regression_rainbow(synthetic_power_law(noise=0.2))
    assert 0 <= frame.attrs["current_band"] < frame.attrs["bands"]
