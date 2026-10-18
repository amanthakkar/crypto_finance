"""Command-line interface.

    crypto-finance indicators            # latest BTC readings + composite
    crypto-finance indicators --json out.json
    crypto-finance dashboard             # writes outputs/dashboard.html + PNGs
    crypto-finance rainbow --coin ethereum
    crypto-finance portfolio --coins bitcoin,ethereum,solana
    crypto-finance stock-to-flow
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from . import charts
from .composite import composite_signal
from .dashboard import build_dashboard
from .data import fetch_btc_history, fetch_eth_history
from .indicators import (all_btc_indicators, regression_rainbow,
                         stock_to_flow)
from .portfolio import efficient_frontier, load_prices

OUT = Path("outputs")


def _latest(frame: pd.DataFrame) -> dict:
    row = frame.iloc[-1]
    def g(col):
        v = row.get(col)
        return None if v is None or (isinstance(v, float) and pd.isna(v)) else v
    return {
        "price": float(row["price"]),
        "plo_decile": int(row["decile"]), "plo_rank": float(row["rank"]),
        "plo_residual": float(row["residual"]),
        "plo_risk_sigma": float(row["risk_sigma"]),
        "cowen_style_v2": (float(g("ma_stretch")) if g("ma_stretch") is not None else None),
        "mayer": (float(g("mayer")) if g("mayer") is not None else None),
        "pi_cycle_111": (float(g("pi_cycle_111")) if g("pi_cycle_111") is not None else None),
        "pi_cycle_350x2": (float(g("pi_cycle_350x2")) if g("pi_cycle_350x2") is not None else None),
        "fair_value": float(row["fair_value"]),
        "mvrv": None, "mvrv_z": None, "nupl": None,
    }


def _btc_frame() -> pd.DataFrame:
    return all_btc_indicators(fetch_btc_history())


def cmd_indicators(args) -> int:
    frame = _btc_frame()
    latest = _latest(frame)
    signal = composite_signal(latest)
    print(f"BTC indicators — as of {frame.index[-1].date()}")
    for k, v in latest.items():
        print(f"  {k:16s} {v}")
    if signal:
        print(f"\nComposite: {signal['label']} ({signal['score']:+.2f}) — "
              f"{signal['summary']}")
        for v in signal["votes"]:
            print(f"  {v['name']:14s} {v['detail']:32s} {v['score']:+.2f}  {v['vote']}")
    if args.json:
        payload = {"as_of": str(frame.index[-1].date()), "latest": latest,
                   "composite": signal}
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\nwrote {args.json}")
    return 0


def cmd_dashboard(args) -> int:
    OUT.mkdir(exist_ok=True)
    frame = _btc_frame()
    latest = _latest(frame)
    signal = composite_signal(latest)
    rainbow = regression_rainbow(fetch_btc_history())
    path = build_dashboard(frame, latest, signal,
                           rainbow.attrs["current_band"],
                           OUT / "dashboard.html")
    charts.plo_chart(frame, OUT / "plo.png")
    charts.rainbow_chart(rainbow, OUT / "btc_rainbow.png",
                         "Bitcoin logarithmic regression rainbow")
    print(f"wrote {path} (+ plo.png, btc_rainbow.png in {OUT}/)")
    return 0


def cmd_rainbow(args) -> int:
    df = fetch_btc_history() if args.coin == "bitcoin" else fetch_eth_history()
    frame = regression_rainbow(df)
    OUT.mkdir(exist_ok=True)
    p = charts.rainbow_chart(frame, OUT / f"{args.coin}_rainbow.png",
                             f"{args.coin.title()} logarithmic regression rainbow")
    print(f"{args.coin}: price ${df['price'].iloc[-1]:,.0f} — currently in "
          f"band {frame.attrs['current_band']} of "
          f"{frame.attrs['bands'] - 1} (0 = cheapest)")
    print(f"wrote {p}")
    return 0


def cmd_portfolio(args) -> int:
    coins = [c.strip() for c in args.coins.split(",") if c.strip()]
    prices = load_prices(coins, days=args.days)
    result = efficient_frontier(prices)
    print(f"Efficient frontier — {coins}, {args.days}d daily log returns")
    for c, s in result["assets"].items():
        print(f"  {c:14s} return {s['ann_return'] * 100:+7.1f}%  "
              f"vol {s['ann_volatility'] * 100:5.1f}%")
    for name in ("max_sharpe", "min_volatility"):
        p = result[name]
        w = ", ".join(f"{k} {v * 100:.0f}%" for k, v in p["weights"].items())
        print(f"\n{name}: return {p['return'] * 100:+.1f}%  "
              f"vol {p['volatility'] * 100:.1f}%  sharpe {p['sharpe']:.2f}\n  {w}")
    OUT.mkdir(exist_ok=True)
    charts.frontier_chart(result, OUT / "frontier.png")
    print(f"\nwrote {OUT}/frontier.png")
    return 0


def cmd_stock_to_flow(args) -> int:
    frame = stock_to_flow(fetch_btc_history())
    row = frame.iloc[-1]
    print(f"Stock-to-flow — as of {frame.index[-1].date()}")
    print(f"  price        ${row['price']:,.0f}")
    print(f"  SF ratio     {row['sf_ratio']:.1f}")
    print(f"  model price  ${row['sf_model_price']:,.0f} "
          f"(log-log fit on monthly data)")
    print("  note: S2F famously overshot post-2021 — kept as history, "
          "not a forecast.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="crypto-finance",
                                 description="Crypto cycle research toolkit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("indicators"); p.add_argument("--json")
    p.set_defaults(fn=cmd_indicators)
    p = sub.add_parser("dashboard"); p.set_defaults(fn=cmd_dashboard)
    p = sub.add_parser("rainbow"); p.add_argument("--coin", default="bitcoin",
                                                  choices=["bitcoin", "ethereum"])
    p.set_defaults(fn=cmd_rainbow)
    p = sub.add_parser("portfolio")
    p.add_argument("--coins", default="bitcoin,ethereum,solana")
    p.add_argument("--days", type=int, default=365)
    p.set_defaults(fn=cmd_portfolio)
    p = sub.add_parser("stock-to-flow"); p.set_defaults(fn=cmd_stock_to_flow)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
