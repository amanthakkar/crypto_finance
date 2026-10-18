# crypto_finance

Quantitative research on crypto markets and portfolio construction — written as runnable Jupyter notebooks, each paired with a long-form article that explains the method, the code, and where the model breaks.

This is the research that got me into systematic thinking about markets: not price predictions, but *frameworks* — how to size a portfolio, how to read a cycle, and how to be honest about a model's limitations.

> **Live indicator:** The Power Law Oscillator from this repo, updated daily — [amanthakkar.com/power-law-oscillator-indicator](https://www.amanthakkar.com/power-law-oscillator-indicator/?source=github)

## The notebooks

| Notebook | Question it answers | Article |
|---|---|---|
| `Efficient_Portfolio.ipynb` | How do you build a crypto portfolio that isn't just vibes? Efficient frontier, Sharpe ratio, and sensible weights for BTC/ETH/alts. | [Start smart with an efficient portfolio](https://medium.datadriveninvestor.com/want-to-invest-in-bitcoin-and-crypto-start-smart-with-an-efficient-portfolio-built-using-python-3966bf70f453) |
| `Regression Rainbows.ipynb` + `Regression Rainbows_2.ipynb` | Where are we in the long cycle? Logarithmic regression bands ("rainbows") for BTC and ETH. | [Using logarithmic regression to value BTC & ETH](https://medium.datadriveninvestor.com/using-logarithmic-regression-to-predict-the-future-prices-of-bitcoin-and-ethereum-52f05e7b92b8) |
| `Stock2Flow.ipynb` | Does stock-to-flow actually hold up? A code-first summary — and its limitations. | [Stock-to-flow, summarized honestly](https://medium.datadriveninvestor.com/stock-to-flow-summarized-the-code-a-brief-outline-and-its-limitations-42a524163dde) |
| `Power Oscillator.ipynb` | Can Bitcoin's power law give a cleaner cycle oscillator? The original model, plus a suggested improvement. | [Bitcoin's Power Law Oscillator](https://medium.datadriveninvestor.com/bitcoins-power-law-oscillator-the-code-a-summary-and-a-suggested-improvement-b78b59a2bc9c) |

## Run it

```bash
git clone https://github.com/amanthakkar/crypto_finance.git
cd crypto_finance
pip install jupyter pandas numpy matplotlib requests
jupyter notebook
```

Each notebook is self-contained: it fetches its own price data and walks from raw series to chart to conclusion.

## What I'd do next

- Metcalfe's-law valuations for smaller networks
- On-chain metrics as portfolio inputs, not just price
- A composite risk metric that combines the frameworks above instead of treating each in isolation

## Disclaimer

Research and education only — not financial advice. Every model here has failed at some point; the articles say where.

## License

MIT — see [LICENSE](LICENSE).
