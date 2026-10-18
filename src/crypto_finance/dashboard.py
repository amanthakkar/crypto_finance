"""Interactive HTML dashboard — the open-source twin of the live site.

One self-contained file (Chart.js from CDN) with switchable views, the
composite signal with every vote shown, and a "how to read this" tip for
every chart — the same explainer-first standard as amanthakkar.com.
Regenerate any time with ``crypto-finance dashboard``; the live version
at LIVE_URL recomputes daily on the author's homelab.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd

LIVE_URL = ("https://www.amanthakkar.com/power-law-oscillator-indicator/"
            "?source=github-crypto-finance")
REPO_URL = "https://github.com/amanthakkar/crypto_finance"
CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"


def _series(frame: pd.DataFrame, col: str, step: int = 3) -> list:
    s = frame[col].dropna().iloc[::step]
    return [None if pd.isna(v) else round(float(v), 4) for v in s]


def _labels(frame: pd.DataFrame, step: int = 3) -> list:
    s = frame["price"].dropna().iloc[::step]
    return [str(d.date()) for d in s.index]


def _card(title: str, value: str, sub: str = "", tip: str = "") -> str:
    t = f' title="{html.escape(tip)}"' if tip else ""
    return (f'<div class="card"{t}><div class="card-title">{html.escape(title)}'
            f'</div><div class="card-value">{html.escape(value)}</div>'
            f'<div class="card-sub">{html.escape(sub)}</div></div>')


def build_dashboard(frame: pd.DataFrame, latest: dict, signal: dict | None,
                    rainbow_band: int | None, path: Path) -> Path:
    labels = _labels(frame)
    data = {
        "labels": labels,
        "price": _series(frame, "price"),
        "residual": _series(frame, "residual"),
        "risk": _series(frame, "risk_sigma"),
        "rank": _series(frame, "rank"),
        "mayer": _series(frame, "mayer"),
        "fair": _series(frame, "fair_value"),
    }
    scatter_step = 5
    sc = frame.iloc[::scatter_step]
    scatter = [{"x": round(float(np.log10(p)), 3), "y": round(float(np.log(p)), 3),
                "d": int(d)} for p, d in zip(sc["price"], sc["decile"])]
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
            f'<p class="tip-line">💡 {html.escape(signal["summary"])}. '
            f'Every vote is shown — the composite is a plain average with no '
            f'hidden weights. When the votes disagree, that disagreement '
            f'<i>is</i> the information.</p>'
            f'<table><tr><th>Indicator</th><th>Reading</th><th>Score</th>'
            f'<th>Vote</th></tr>{votes_rows}</table></section>')
    cards = "".join([
        _card("BTC price", f"${latest['price']:,.0f}",
              f"as of {frame.index[-1].date()}",
              "Spot close from blockchain.info daily data"),
        _card("PLO decile", str(latest["plo_decile"]), "1 cheap → 10 rich",
              "Which tenth of its own history today's power-law residual sits in — causal, never rewrites"),
        _card("PLO rank", f"{latest['plo_rank']:.2f}", "expanding percentile",
              "0 = cheapest residual ever seen up to today; 1 = richest"),
        _card("PLO residual", f"{latest['plo_residual']:+.2f}",
              "log10 vs power-law trend",
              "+0.85 ≈ 7× above trend — where historic tops clustered"),
        _card("σ-risk", f"{latest['plo_risk_sigma']:.2f}", "0 cheap → 1 rich",
              "Residual as an expanding z-score, clamped ±3σ and mapped to 0–1"),
        _card("Mayer", f"{latest['mayer']:.2f}×", "price / 200d average",
              "Above ~2.4 was treated as expensive in Mayer's original filter"),
        _card("Fair value", f"${latest['fair_value']:,.0f}",
              "global power-law corridor",
              "Context only — the corridor refits on all data (look-ahead), unlike the causal PLO"),
        _card("Rainbow band", str(rainbow_band if rainbow_band is not None else "—"),
              "log-regression band (0 low)",
              "Log-time regression bands — where price sits vs the long rainbow"),
    ])
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>crypto_finance — Bitcoin cycle dashboard</title>
<script src="{CDN}"></script>
<style>
 body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#0b1020;color:#e6e9f2}}
 main{{max-width:940px;margin:0 auto;padding:28px 18px 60px}}
 a{{color:#7db4ff}} h1{{font-size:28px;margin:0 0 4px}} h2{{margin:0 0 8px;font-size:19px}}
 .sub{{color:#9aa4bf;margin:0 0 20px}} .tip-line{{color:#c8d2ea;font-size:14px}}
 .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}
 .card{{background:#141a30;border:1px solid #232c4d;border-radius:12px;padding:14px;cursor:help}}
 .card-title{{color:#9aa4bf;font-size:12px;text-transform:uppercase;letter-spacing:.06em}}
 .card-value{{font-size:26px;font-weight:700;margin:4px 0}} .card-sub{{color:#9aa4bf;font-size:12px}}
 section{{background:#11172b;border:1px solid #232c4d;border-radius:12px;padding:18px;margin-top:16px}}
 .views{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}}
 .views button{{background:#1a2440;color:#e6e9f2;border:1px solid #2b3a63;border-radius:999px;padding:6px 14px;cursor:pointer;font:inherit;font-size:13.5px}}
 .views button.active{{background:#2563eb;border-color:#2563eb}}
 .explainer{{background:#16203c;border-left:3px solid #f5b04c;border-radius:8px;padding:10px 14px;font-size:14px;color:#dbe2f2;min-height:54px}}
 table{{border-collapse:collapse;width:100%;font-size:14px}}
 td,th{{border-bottom:1px solid #232c4d;padding:6px 8px;text-align:left}}
 footer{{color:#7f89a6;font-size:12px;margin-top:22px;line-height:1.6}}
 canvas{{max-height:340px}}
</style></head><body><main>
<h1>Bitcoin cycle dashboard</h1>
<p class="sub">Generated by <a href="{REPO_URL}">crypto_finance</a> — the open-source twin of the
live indicator at <a href="{LIVE_URL}">amanthakkar.com</a>, which recomputes daily on my homelab.
Hover any metric card for a plain-English hint; switch views below for explainers.</p>
<div class="cards">{cards}</div>
{sig_block}
<section><h2>Charts — pick a view</h2>
<div class="views">
 <button data-view="price" class="active">Price + fair value (log)</button>
 <button data-view="plo">PLO scatter</button>
 <button data-view="residual">Residual</button>
 <button data-view="risk">σ-risk</button>
 <button data-view="mayer">Mayer</button>
</div>
<canvas id="chart"></canvas>
<div class="explainer" id="explainer"></div>
</section>
<footer>Research and education only — not financial advice. Power-law views are causal
(expanding fits, no look-ahead); the corridor and rainbow use global fits and are labelled
context, not signals. Data: blockchain.info (BTC history). Live version:
<a href="{LIVE_URL}">{LIVE_URL}</a></footer>
</main>
<script>
const DATA = {json.dumps(data)};
const SCATTER = {json.dumps(scatter)};
const EXPLAIN = {{
 price: "📈 <b>Price vs fair value.</b> The blue line is the global power-law corridor's center — where price has 'typically' lived vs a time trend. Price far below it has historically been accumulation territory; far above, distribution. <i>Hint: the corridor refits on all data, so treat it as context, not a causal signal.</i>",
 plo: "🎨 <b>The Power Law Oscillator scatter.</b> Each dot is a day: x = log₁₀(price), y = ln(price) trajectory, colored jet by its expanding residual decile (dark blue = cheapest tenth of history so far, red = richest). Tops cluster red; long blue stretches mark bear-market floors. <i>Hint: colors are causal — a dot's color never changes later.</i>",
 residual: "📉 <b>Raw residual.</b> log₁₀(price) minus the expanding power-law fit. +0.8 ≈ 6× above trend (historic top zone); deep negatives ≈ capitulation vs trend. <i>Hint: compare peak heights across cycles — similar peaks are the 'magic band' observation behind this model.</i>",
 risk: "🌡️ <b>σ-risk (0–1).</b> The residual as an expanding z-score. Below ~0.2 = multi-sigma cheap; above ~0.85 = multi-sigma rich. <i>Hint: risk moves slowly by design — it's a positioning gauge, not a timing trigger.</i>",
 mayer: "⚖️ <b>Mayer Multiple.</b> Price ÷ its 200-day average. ≈1 = at the average; long stretches below 1 often coincide with bear markets. <i>Hint: simple and robust, but blind to the power-law growth the other views model.</i>"
}};
let chart;
function render(view){{
  const ctx = document.getElementById('chart');
  if (chart) chart.destroy();
  document.getElementById('explainer').innerHTML = EXPLAIN[view];
  document.querySelectorAll('.views button').forEach(b=>b.classList.toggle('active', b.dataset.view===view));
  if (view==='plo'){{
    chart = new Chart(ctx, {{type:'scatter', data:{{datasets:[{{data:SCATTER,
      pointRadius:2, backgroundColor: SCATTER.map(p=>{{const hue = 240 - (p.d-1)/9*240; return 'hsl('+hue+',90%,55%)';}})}}]}},
      options:{{plugins:{{legend:{{display:false}}, tooltip:{{callbacks:{{label:(c)=>'decile '+c.raw.d}}}}}},
      scales:{{x:{{type:'linear', title:{{display:true,text:'log10(price)',color:'#9aa4bf'}}, ticks:{{color:'#9aa4bf'}}}},
               y:{{title:{{display:true,text:'ln(price)',color:'#9aa4bf'}}, ticks:{{color:'#9aa4bf'}}}}}}}}}});
    return;
  }}
  const cfg = {{
    price: {{labels:DATA.labels, sets:[{{label:'BTC price', data:DATA.price, borderColor:'#7db4ff'}},{{label:'Fair value', data:DATA.fair, borderColor:'#f5b04c'}}], log:true}},
    residual: {{labels:DATA.labels, sets:[{{label:'Residual', data:DATA.residual, borderColor:'#fb7185'}}], log:false}},
    risk: {{labels:DATA.labels, sets:[{{label:'σ-risk', data:DATA.risk, borderColor:'#f59e0b'}}], log:false}},
    mayer: {{labels:DATA.labels, sets:[{{label:'Mayer', data:DATA.mayer, borderColor:'#4ade80'}}], log:false}}
  }}[view];
  chart = new Chart(ctx, {{type:'line', data:{{labels:cfg.labels,
    datasets:cfg.sets.map(s=>({{...s, pointRadius:0, borderWidth:1.4}}))}},
    options:{{interaction:{{mode:'index', intersect:false}},
      plugins:{{legend:{{labels:{{color:'#e6e9f2'}}}}}},
      scales:{{x:{{ticks:{{color:'#9aa4bf', maxTicksLimit:9}}}},
               y:{{type: cfg.log?'logarithmic':'linear', ticks:{{color:'#9aa4bf'}}}}}}}}}});
}}
document.querySelectorAll('.views button').forEach(b=>b.onclick=()=>render(b.dataset.view));
render('price');
</script></body></html>"""
    path.write_text(doc)
    return path
