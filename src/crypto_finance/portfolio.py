"""Efficient-portfolio analysis — the Efficient_Portfolio notebook as a
reusable, testable function.

Fetches aligned daily closes for a set of CoinGecko ids, computes annualized
return / volatility / correlations, then Monte-Carlo samples the frontier
and reports the max-Sharpe and min-volatility portfolios.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import fetch_coingecko_history

TRADING_DAYS = 365  # crypto trades every day — the notebook's key correction
                    # to the stock-market 252 convention


def load_prices(coin_ids: list[str], days: int = 365) -> pd.DataFrame:
    series = {}
    for cid in coin_ids:
        series[cid] = fetch_coingecko_history(cid, days=days)["price"]
    prices = pd.DataFrame(series).dropna()
    return prices


def portfolio_stats(prices: pd.DataFrame) -> dict:
    returns = np.log(prices / prices.shift(1)).dropna()
    ann_return = returns.mean() * TRADING_DAYS
    ann_vol = returns.std() * np.sqrt(TRADING_DAYS)
    corr = returns.corr()
    return {"returns": returns, "ann_return": ann_return,
            "ann_vol": ann_vol, "corr": corr}


def efficient_frontier(prices: pd.DataFrame, n_portfolios: int = 5000,
                       risk_free: float = 0.0, seed: int = 42) -> dict:
    stats = portfolio_stats(prices)
    mu = stats["ann_return"].to_numpy()
    cov = stats["returns"].cov().to_numpy() * TRADING_DAYS
    rng = np.random.default_rng(seed)
    n = len(mu)
    weights = rng.random((n_portfolios, n))
    weights /= weights.sum(axis=1, keepdims=True)
    port_ret = weights @ mu
    port_vol = np.sqrt(np.einsum("ij,jk,ik->i", weights, cov, weights))
    sharpe = (port_ret - risk_free) / port_vol
    cols = list(prices.columns)

    def describe(i: int) -> dict:
        return {"return": float(port_ret[i]), "volatility": float(port_vol[i]),
                "sharpe": float(sharpe[i]),
                "weights": {c: round(float(w), 4)
                            for c, w in zip(cols, weights[i])}}

    return {
        "assets": {c: {"ann_return": float(stats["ann_return"][c]),
                       "ann_volatility": float(stats["ann_vol"][c])}
                   for c in cols},
        "max_sharpe": describe(int(np.argmax(sharpe))),
        "min_volatility": describe(int(np.argmin(port_vol))),
        "frontier_sample": [
            {"return": float(r), "volatility": float(v)}
            for r, v in zip(port_ret[:: max(1, n_portfolios // 500)],
                            port_vol[:: max(1, n_portfolios // 500)])
        ],
    }
