"""Composite cycle signal — a faithful Python port of the scoring used by
the live site (src/components/Indicator/signalScore.js in personal-site).

Each indicator votes in [-2, +2]: negative = buy-leaning, positive =
sell-leaning. The composite is the simple average — deliberately naive,
fully inspectable, and every vote is shown. No hidden weighting.
"""
from __future__ import annotations


def _clip(x, lo=-2.0, hi=2.0):
    return max(lo, min(hi, x))


def _label(avg: float) -> str:
    if avg <= -1.2:
        return "Strong buy"
    if avg <= -0.4:
        return "Buy"
    if avg < 0.4:
        return "Hold"
    if avg < 1.2:
        return "Sell"
    return "Strong sell"


def _vote_label(score: float) -> str:
    if score <= -1.2:
        return "Strong buy"
    if score <= -0.4:
        return "Buy"
    if score < 0.4:
        return "Hold"
    if score < 1.2:
        return "Sell"
    return "Strong sell"


def composite_signal(latest: dict) -> dict | None:
    votes = []

    def push(id_, name, score, detail):
        if score is None:
            return
        try:
            s = float(score)
        except (TypeError, ValueError):
            return
        if s != s:  # NaN
            return
        votes.append({"id": id_, "name": name, "score": round(s, 2),
                      "vote": _vote_label(s), "detail": detail})

    def from_risk01(v):
        return None if v is None else _clip((float(v) - 0.5) * 4)

    if latest.get("plo_rank") is not None:
        push("plo_rank", "PLO rank", from_risk01(latest["plo_rank"]),
             f"rank {float(latest['plo_rank']):.2f}")
    if latest.get("plo_risk_sigma") is not None:
        push("plo_risk_sigma", "σ-risk", from_risk01(latest["plo_risk_sigma"]),
             f"{float(latest['plo_risk_sigma']):.2f}")
    if latest.get("cowen_style_v2") is not None:
        push("ma_stretch", "MA stretch", from_risk01(latest["cowen_style_v2"]),
             f"{float(latest['cowen_style_v2']):.2f}")
    if latest.get("plo_residual") is not None:
        push("plo_residual", "PLO residual",
             _clip((float(latest["plo_residual"]) / 0.85) * 2),
             f"{float(latest['plo_residual']):.2f}")
    if latest.get("plo_decile") is not None:
        push("plo_decile", "PLO decile",
             _clip(((float(latest["plo_decile"]) - 5.5) / 4.5) * 2),
             f"band {latest['plo_decile']}")
    if latest.get("mayer") is not None:
        push("mayer", "Mayer", _clip((float(latest["mayer"]) - 1.2) / 0.9),
             f"{float(latest['mayer']):.2f}×")
    if latest.get("pi_cycle_111") and latest.get("pi_cycle_350x2"):
        ratio = float(latest["pi_cycle_111"]) / float(latest["pi_cycle_350x2"])
        push("pi_cycle", "Pi Cycle", _clip((ratio - 0.85) / 0.15),
             f"111 / (2×350) = {ratio:.2f}")
    if latest.get("price") and latest.get("fair_value"):
        prem = float(latest["price"]) / float(latest["fair_value"]) - 1
        push("corridor", "Corridor", _clip(prem / 0.35),
             f"price {prem * 100:+.0f}% vs fair value")
    if latest.get("mvrv") is not None:
        push("mvrv", "MVRV", _clip((float(latest["mvrv"]) - 1.4) / 0.9),
             f"{float(latest['mvrv']):.2f}")

    if not votes:
        return None
    avg = sum(v["score"] for v in votes) / len(votes)
    buyish = sum(1 for v in votes if v["score"] <= -0.4)
    sellish = sum(1 for v in votes if v["score"] >= 0.4)
    neutral = len(votes) - buyish - sellish
    return {
        "label": _label(avg), "score": round(avg, 2), "votes": votes,
        "summary": f"{buyish} buy-leaning · {neutral} neutral · "
                   f"{sellish} sell-leaning (of {len(votes)})",
    }
