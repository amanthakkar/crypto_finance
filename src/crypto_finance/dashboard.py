"""Self-contained HTML dashboard — no build step, no JS dependencies.

Generates inline-SVG charts from the same indicator frames the CLI uses,
so the file you get from ``crypto-finance dashboard`` is exactly the math
in ``indicators.py``, rendered. The live, daily-updated version of this
page runs at amanthakkar.com (see LIVE_URL) — this static export is the
open-source twin you can regenerate any time.
"""
from __future__ import annotations

import html
from pathlib import Path

import numpy as np
import pandas as pd

LIVE_URL = ("https://www.amanthakkar.com/power-law-oscillator-indicator/"
            "?source=github-crypto-finance")
REPO_URL = "https://github.com/amanthakkar/crypto_finance"


def _svg_line(dates, values, *, width=860, height=210, color="#2563eb",
              log=False, label="") -> str:
    s = pd.Series(values).dropna()
    if len(s) < 2:
        return "<p>not enough data</p>"
    v = np.log10(s.to_numpy()) if log else s.to_numpy()
    lo, hi = float(np.min(v)), float(np.max(v))
    span = (hi - lo) or 1.0
    xs = np.linspace(8, width - 8, len(v))
    ys = height - 18 - (v - lo) / span * (height - 36)
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    return (
        f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" '
        f'aria-label="{html.escape(label)}">'
        f'<polyline points="{pts}" fill="none" stroke="{color}" '
        f'stroke-width="1.6"/></svg>'
        f'<div class="axis"><span>{s.index[0].date()}</span>'
        f'<span>{label} · min {float(s.min()):,.2f} — max {float(s.max()):,.2f}</span>'
        f'<span>{s.index[-1].date()}</span></div>'
    )


def _card(title: str, value: str, sub: str = "") -> str:
    return (f'<div class="card"><div class="card-title">{html.escape(title)}'
            f'</div><div class="card-value">{html.escape(value)}</div>'
            f'<div class="card-sub">{html.escape(sub)}</div></div>')


def build_dashboard(frame: pd.DataFrame, latest: dict, signal: dict | None,
                    rainbow_band: int | None, path: Path) -> Path:
    votes_rows = ""
    if signal:
        for v in signal["votes"]:
            votes_rows += (f"<tr><td>{html.escape(v['name'])}</td>"
                           f"<td>{html.escape(v['detail'])}</td>"
                           f"<td>{v['score']:+.2f}</td>"
                           f"<td>{html.escape(v['vote'])}</td></tr>")
    sig_block = ""
    if signal:
        sig_block = (
            f'<section><h2>Composite signal: {html.escape(signal["label"])} '
            f'({signal["score"]:+.2f})</h2>'
            f'<p>{html.escape(signal["summary"])}. Every vote is shown — '
            f'the composite is a plain average, no hidden weights.</p>'
            f'<table><tr><th>Indicator</th><th>Reading</th><th>Score</th>'
            f'<th>Vote</th></tr>{votes_rows}</table></section>'
        )
    cards = "".join([
        _card("BTC price", f"${latest['price']:,.0f}",
              f"as of {frame.index[-1].date()}"),
        _card("PLO decile", str(latest["plo_decile"]), "1 cheap → 10 rich"),
        _card("PLO rank", f"{latest['plo_rank']:.2f}", "expanding percentile"),
        _card("PLO residual", f"{latest['plo_residual']:+.2f}",
              "log10 vs power-law trend"),
        _card("σ-risk", f"{latest['plo_risk_sigma']:.2f}", "0 cheap → 1 rich"),
        _card("Mayer", f"{latest['mayer']:.2f}×", "price / 200d average"),
        _card("Fair value", f"${latest['fair_value']:,.0f}",
              "global power-law corridor"),
        _card("Rainbow band", str(rainbow_band if rainbow_band is not None else "—"),
              "log-regression band (0 low)"),
    ])
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>crypto_finance — Bitcoin cycle dashboard</title>
<style>
 body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
 margin:0;background:#0b1020;color:#e6e9f2}}
 main{{max-width:920px;margin:0 auto;padding:28px 18px 60px}}
 a{{color:#7db4ff}} h1{{font-size:28px;margin:0 0 4px}}
 .sub{{color:#9aa4bf;margin:0 0 22px}}
 .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}
 .card{{background:#141a30;border:1px solid #232c4d;border-radius:12px;padding:14px}}
 .card-title{{color:#9aa4bf;font-size:12px;text-transform:uppercase;letter-spacing:.06em}}
 .card-value{{font-size:26px;font-weight:700;margin:4px 0}}
 .card-sub{{color:#9aa4bf;font-size:12px}}
 section{{background:#11172b;border:1px solid #232c4d;border-radius:12px;padding:18px;margin-top:16px}}
 .chart{{width:100%;height:auto;background:#0d1326;border-radius:8px}}
 .axis{{display:flex;justify-content:space-between;color:#7f89a6;font-size:11px;margin-top:4px}}
 table{{border-collapse:collapse;width:100%;font-size:14px}}
 td,th{{border-bottom:1px solid #232c4d;padding:6px 8px;text-align:left}}
 footer{{color:#7f89a6;font-size:12px;margin-top:22px;line-height:1.6}}
</style></head><body><main>
<h1>Bitcoin cycle dashboard</h1>
<p class="sub">Generated by <a href="{REPO_URL}">crypto_finance</a> — the
open-source twin of the live indicator at
<a href="{LIVE_URL}">amanthakkar.com</a>, which recomputes daily on my homelab.
Regenerate this file any time with <code>crypto-finance dashboard</code>.</p>
<div class="cards">{cards}</div>
{sig_block}
<section><h2>Price (log scale)</h2>
{_svg_line(frame.index, frame["price"], log=True, label="BTC/USD log10")}</section>
<section><h2>Power-law residual</h2>
{_svg_line(frame.index, frame["residual"], color="#e11d48", label="residual log10")}</section>
<section><h2>σ-risk (0–1)</h2>
{_svg_line(frame.index, frame["risk_sigma"], color="#f59e0b", label="risk")}</section>
<footer>Research and education only — not financial advice. Power-law views
are causal (expanding fits, no look-ahead); the corridor and rainbow use
global fits and are labelled context, not signals. Data: blockchain.info
(BTC history). Live version: <a href="{LIVE_URL}">{LIVE_URL}</a></footer>
</main></body></html>"""
    path.write_text(doc)
    return path
