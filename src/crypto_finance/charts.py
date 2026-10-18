"""Matplotlib chart exports (PNG) for the classic views."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def plo_chart(frame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(11, 5))
    sc = ax.scatter(frame.index, np.log(frame["price"]),
                    c=frame["decile"], cmap="jet", s=2, vmin=1, vmax=10)
    ax.set_title("Bitcoin Power Law Oscillator — log price colored by "
                 "expanding residual decile (blue=cheap, red=expensive)")
    ax.set_ylabel("ln(price)")
    fig.colorbar(sc, ax=ax, label="decile")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def rainbow_chart(frame, path: Path, title: str) -> Path:
    bands = frame.attrs.get("bands", 9)
    colors = plt.cm.jet(np.linspace(0, 1, bands))
    fig, ax = plt.subplots(figsize=(11, 5))
    for k in range(bands):
        ax.fill_between(frame.index, frame[f"band_{k}"], frame[f"band_{k+1}"],
                        color=colors[k], alpha=0.55, linewidth=0)
    ax.plot(frame.index, frame["price"], color="black", lw=0.7)
    ax.set_yscale("log")
    ax.set_title(title)
    ax.set_ylabel("price (log)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def frontier_chart(frontier: dict, path: Path) -> Path:
    pts = frontier["frontier_sample"]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter([p["volatility"] for p in pts], [p["return"] for p in pts],
               s=6, alpha=0.4)
    for key, marker, label in [("max_sharpe", "*", "max Sharpe"),
                               ("min_volatility", "X", "min volatility")]:
        p = frontier[key]
        ax.scatter([p["volatility"]], [p["return"]], marker=marker, s=220,
                   label=label)
    ax.set_xlabel("annualized volatility")
    ax.set_ylabel("annualized return")
    ax.set_title("Efficient frontier (Monte Carlo, log returns, 365d)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
