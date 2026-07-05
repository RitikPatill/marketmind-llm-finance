![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

# MarketMind

Ask a question about any stock, get a cited answer grounded in live data.

<!-- GIF will be added in M6 -->

## Features

### Implemented — M1 (scaffold)

- Python package layout: `src/marketmind/` with `__init__.py` and `py.typed` marker
- All runtime dependencies pinned in `requirements.txt` (Anthropic SDK, yfinance, feedparser, FastAPI, Streamlit, Plotly, Pydantic, uvicorn, python-dotenv)
- `pyproject.toml` configured for editable install via `pip install -e .`
- `.env.example` documenting the required `ANTHROPIC_API_KEY` variable
- MIT license and `.gitignore`

### Implemented — M2 (data layer)

- `src/marketmind/data.py` — two public functions:
  - `get_snapshot(ticker)` — returns a `Snapshot` dataclass with 30-day OHLCV history (JSON-serialisable dicts) and `Fundamentals` (P/E, EPS, 52-week high/low, market cap, analyst target, currency) via `yfinance`
  - `get_news(ticker)` — returns up to 10 `NewsItem` entries (title, URL, published) via Yahoo Finance RSS and `feedparser`
- Offline unit tests in `tests/test_data.py`; all `yfinance` and `feedparser` calls are patched with `unittest.mock`, so the suite runs without any network access; `tests/fixtures/snap_AAPL.json` provides a hand-authored reference snapshot

### Planned

- Streaming LLM response via Claude with citations to specific data points
- Dark-mode Streamlit UI with an interactive mini price chart (Plotly)
- CLI mode: `python query.py ASML "What are the key risks?"`
- Fully local-first: no paid data feeds, no broker account required

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Streamlit UI (app.py)               │
│  [Ticker input] [Question box] [Streaming answer]   │
└────────────────────────┬────────────────────────────┘
                         │ HTTP POST /query
┌────────────────────────▼────────────────────────────┐
│              FastAPI Backend (api.py)                │
│   GET /snapshot/{ticker}    POST /query (stream)    │
└───────────┬────────────────────────┬────────────────┘
            │                        │
┌───────────▼──────────┐  ┌──────────▼───────────────┐
│  Data Layer           │  │  LLM Layer               │
│  data.py              │  │  analyst.py              │
│  • yfinance (OHLCV,  │  │  • build_context()       │
│    fundamentals)      │  │  • ask_claude() stream   │
│  • feedparser (RSS   │  │  • Anthropic SDK         │
│    news headlines)    │  └──────────────────────────┘
└──────────────────────┘
```

The system follows a retrieval-augmented generation (RAG) pattern: market data and news are fetched at query time, serialised into a compact Markdown context block (< 1 500 tokens), and passed to Claude alongside the user question. The system prompt requires the model to cite specific numbers from the context, making hallucination straightforward to detect.

## Quick Start

```bash
git clone https://github.com/your-username/marketmind-llm-finance.git
cd marketmind-llm-finance
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=<your key>
streamlit run app.py   # app.py is coming in a future milestone
```

## Project Layout

```
marketmind-llm-finance/
├── src/
│   └── marketmind/
│       ├── __init__.py
│       ├── py.typed
│       ├── data.py        # M2 — yfinance + feedparser data layer
│       ├── analyst.py     # coming soon — context builder + Claude integration
│       ├── api.py         # coming soon — FastAPI endpoints
│       └── cli.py         # coming soon — CLI entry point
├── tests/
│   ├── fixtures/
│   │   └── snap_AAPL.json # hand-authored reference snapshot for AAPL
│   └── test_data.py       # M2 — offline unit tests (all network calls mocked)
├── app.py                 # coming soon — Streamlit frontend
├── query.py               # coming soon — CLI wrapper
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .env.example
├── .gitignore
└── LICENSE
```

## Out of Scope

- Portfolio tracking, watchlists, authentication
- Trade execution or buy/sell signals
- Historical backtesting
- Multi-ticker comparison

## License

[MIT](LICENSE)
