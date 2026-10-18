"""Data layer — free, key-less public price sources with a local disk cache.

Sources
-------
BTC long history : blockchain.info Charts API (daily, back to 2010, no key)
Any coin (<=1y+) : CoinGecko public market_chart (no key, rate-limited)
ETH long history : Coinbase Exchange candles (public, 300 days/request, paged)

Everything returns a tidy DataFrame indexed by UTC date with a ``price``
column, so the indicator code never cares where the data came from.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

CACHE_DIR = Path.home() / ".cache" / "crypto_finance"
GENESIS = pd.Timestamp("2009-01-03", tz="UTC")  # Bitcoin genesis block

_HEADERS = {"User-Agent": "crypto-finance/2.0 (personal research)"}


def _cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{name}.json"


def _cached(name: str, max_age_hours: float = 12.0):
    p = _cache_path(name)
    if p.exists() and (time.time() - p.stat().st_mtime) < max_age_hours * 3600:
        return json.loads(p.read_text())
    return None


def _save(name: str, payload) -> None:
    _cache_path(name).write_text(json.dumps(payload))


def _frame_from_pairs(pairs) -> pd.DataFrame:
    df = pd.DataFrame(pairs, columns=["ts", "price"])
    df["date"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.normalize()
    df = df[df["price"] > 0].drop_duplicates("date").set_index("date")
    return df[["price"]].sort_index()


def fetch_btc_history(use_cache: bool = True) -> pd.DataFrame:
    """Full BTC/USD daily history from blockchain.info (2010–today)."""
    if use_cache and (c := _cached("btc_blockchain")) is not None:
        return _frame_from_pairs(c)
    r = requests.get(
        "https://api.blockchain.info/charts/market-price",
        params={"timespan": "all", "format": "json", "sampled": "false"},
        headers=_HEADERS, timeout=30,
    )
    r.raise_for_status()
    pairs = [[v["x"], v["y"]] for v in r.json()["values"]]
    if use_cache:
        _save("btc_blockchain", pairs)
    return _frame_from_pairs(pairs)


def fetch_coingecko_history(coin_id: str, days: int = 365,
                            use_cache: bool = True) -> pd.DataFrame:
    """Daily closes for any CoinGecko coin id (free tier: ~1 year)."""
    key = f"cg_{coin_id}_{days}"
    if use_cache and (c := _cached(key)) is not None:
        return _frame_from_pairs(c)
    r = requests.get(
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
        params={"vs_currency": "usd", "days": days},
        headers=_HEADERS, timeout=30,
    )
    r.raise_for_status()
    pairs = [[int(ts / 1000), px] for ts, px in r.json()["prices"]]
    if use_cache:
        _save(key, pairs)
    # market_chart at long ranges is hourly — collapse to daily last value
    df = _frame_from_pairs(pairs)
    return df.resample("D").last().dropna()


def fetch_coinbase_history(product: str = "ETH-USD",
                           use_cache: bool = True) -> pd.DataFrame:
    """Full daily history from Coinbase Exchange (paged, 300 days/call)."""
    key = f"cb_{product}"
    if use_cache and (c := _cached(key, max_age_hours=24)) is not None:
        return _frame_from_pairs(c)
    start = pd.Timestamp("2015-01-01", tz="UTC")
    end = pd.Timestamp.now(tz="UTC").normalize()
    pairs, cursor = [], start
    while cursor < end:
        chunk_end = min(cursor + pd.Timedelta(days=300), end)
        r = requests.get(
            f"https://api.exchange.coinbase.com/products/{product}/candles",
            params={"granularity": 86400,
                    "start": cursor.isoformat(), "end": chunk_end.isoformat()},
            headers=_HEADERS, timeout=30,
        )
        r.raise_for_status()
        pairs += [[int(c[0]), float(c[4])] for c in r.json()]  # close
        cursor = chunk_end
        time.sleep(0.15)  # be polite to a free API
    if use_cache:
        _save(key, pairs)
    return _frame_from_pairs(pairs)


def fetch_eth_history(use_cache: bool = True) -> pd.DataFrame:
    """ETH/USD full history — Coinbase, falling back to CoinGecko 1y."""
    try:
        return fetch_coinbase_history("ETH-USD", use_cache=use_cache)
    except Exception:
        return fetch_coingecko_history("ethereum", days=365, use_cache=use_cache)
