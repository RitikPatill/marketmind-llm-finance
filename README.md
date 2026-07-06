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

### Implemented — M3 (LLM analysis pipeline)

- `src/marketmind/analyst.py` — core LLM module:
  - `build_context(snapshot, news)` — serialises a `Snapshot` + news list into a compact Markdown block (< 1 500 tokens): price summary (last close, 30d high/low), fundamentals (skipping `None` fields, market cap formatted as `$2.74T`), and up to 10 news bullets
  - `ask(ticker, question, stream=True)` — fetches live data, builds context, calls Claude (`claude-haiku-4-5-20251001`) via the Anthropic SDK; returns a generator of text chunks (streaming) or a full string (non-streaming); loads `ANTHROPIC_API_KEY` via `python-dotenv`
  - System prompt enforces citation of specific numbers from context to mitigate hallucination
- `src/marketmind/cli.py` — CLI entry point: `python -m marketmind.cli TICKER "question"` streams the answer to stdout
- `tests/test_analyst.py` — 6 unit tests; all Anthropic API calls and data-layer calls are mocked (no network, no API key needed)

### Implemented — M4 (FastAPI backend)

- `src/marketmind/api.py` — FastAPI application with two endpoints:
  - `GET /snapshot/{ticker}` — returns raw JSON (price history, fundamentals, news)
  - `POST /query` — accepts `{ticker, question}`, streams the LLM answer as `text/event-stream` (SSE) with a `data: [DONE]` sentinel
- CORS middleware (`allow_origins=["*"]`) so the Streamlit frontend can call the API from a different port
- `tests/test_api.py` — 4 unit tests using `TestClient`; all network and Anthropic calls are mocked

### Planned

- Dark-mode Streamlit UI with an interactive mini price chart (Plotly)
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
│    fundamentals)      │  │  • ask() (streaming)     │
│  • feedparser (RSS   │  │  • Anthropic SDK         │
│    news headlines)    │  └──────────────────────────┘
└──────────────────────┘
```

The system follows a retrieval-augmented generation (RAG) pattern: market data and news are fetched at query time, serialised into a compact Markdown context block (< 1 500 tokens), and passed to Claude alongside the user question. The system prompt requires the model to cite specific numbers from the context, making hallucination straightforward to detect.

## Quick Start

```bash
git clone https://github.com/your-username/marketmind-llm-finance.git
cd marketmind-llm-finance
pip install -e .
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=<your key>

# CLI — works now (M3)
python -m marketmind.cli AAPL "What does the current P/E ratio suggest about valuation?"

# API server — works now (M4)
uvicorn marketmind.api:app --reload
# Then: GET  http://localhost:8000/snapshot/AAPL
#       POST http://localhost:8000/query  {"ticker":"AAPL","question":"Is it overvalued?"}

# Streamlit UI — coming in a future milestone
# streamlit run app.py
```

## Project Layout

```
marketmind-llm-finance/
├── src/
│   └── marketmind/
│       ├── __init__.py
│       ├── py.typed
│       ├── data.py        # M2 — yfinance + feedparser data layer
│       ├── analyst.py     # M3 — context builder + Claude integration
│       ├── cli.py         # M3 — CLI entry point
│       ├── api.py         # M4 — FastAPI endpoints (snapshot + query stream)
├── tests/
│   ├── fixtures/
│   │   └── snap_AAPL.json # hand-authored reference snapshot for AAPL
│   ├── test_data.py       # M2 — offline unit tests (all network calls mocked)
│   ├── test_analyst.py    # M3 — analyst unit tests (Anthropic client mocked)
│   └── test_api.py        # M4 — API unit tests (all external calls mocked)
├── app.py                 # coming soon — Streamlit frontend
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
