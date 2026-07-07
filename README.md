![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![CI](https://github.com/your-username/marketmind-llm-finance/actions/workflows/ci.yml/badge.svg)

# MarketMind

Ask a question about any stock, get a cited answer grounded in live data.

> **Demo** — record with [Terminalizer](https://github.com/faressoft/terminalizer) or [ShareX](https://getsharex.com/) and drop the GIF here.
<!-- GIF skipped: cannot capture an interactive terminal session in a non-interactive automated environment; record manually and replace this line with ![Demo](docs/demo.gif) -->

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

### Implemented — M5 (Streamlit UI)

- `app.py` — Streamlit frontend with wide dark layout:
  - Sidebar ticker input and three preset "Try an example" buttons (NVDA / ASML / SAP)
  - Two-column layout: question text area + Analyse button (left), Plotly candlestick chart (right)
  - Streaming answer panel powered by `st.write_stream` (Streamlit ≥ 1.31)
  - Dark theme via `.streamlit/config.toml` and CSS injection
  - Clear error messages when the backend is unreachable
- `tests/test_app.py` — 5 unit tests (all httpx calls mocked, no network needed)

### Fully local-first: no paid data feeds, no broker account required

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

## How hallucination is mitigated

MarketMind uses a retrieval-grounded prompt strategy:

1. **Data is fetched at query time** — prices, P/E, EPS, and news are pulled live from Yahoo Finance via `yfinance` and `feedparser` immediately before the LLM call. The model never invents numbers it wasn't given.
2. **System prompt enforces citation** — the system prompt in `analyst.py` instructs Claude to reference specific values from the context block (e.g. *"P/E of 28.5"*, *"52-week high of $199.62"*). Answers that drift from the provided numbers are immediately detectable.
3. **Context is compact and scoped** — the context block is kept under 1 500 tokens (one ticker, 30 days, 10 headlines). Smaller context → less opportunity for the model to conflate unrelated data.
4. **Manual eval is easy** — every cited number in the answer can be spot-checked against the raw `/snapshot/{ticker}` endpoint in one browser tab.

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

# Streamlit UI — works now (M5); run the API server first, then launch the UI
uvicorn marketmind.api:app --reload &
streamlit run app.py
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
│   ├── test_api.py        # M4 — API unit tests (all external calls mocked)
│   └── test_app.py        # M5 — Streamlit helper unit tests (httpx mocked)
├── app.py                 # M5 — Streamlit frontend
├── .streamlit/
│   └── config.toml        # M5 — dark theme config
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .env.example
├── .gitignore
└── LICENSE
```

## Example output

**Query:** `ASML "What are the key risks for ASML right now?"`

```
## ASML Risk Summary

Based on the current data (last close €812.40, P/E 35.2):

- **Geopolitical export controls**: ASML's EUV machines are subject to Dutch and US export
  restrictions. Any tightening toward China could reduce the addressable market.
- **Concentration risk**: TSMC, Samsung, and Intel collectively account for the majority
  of EUV revenue. Capex pullbacks at any of these customers flow directly to ASML order books.
- **Analyst consensus**: Mean target of €950 implies ~17% upside, but 3 of 12 analysts
  recently lowered estimates citing macro uncertainty (per headlines, 2024-05-03).

*All figures sourced from the context block above.*
```

## Out of Scope

- Portfolio tracking, watchlists, authentication
- Trade execution or buy/sell signals
- Historical backtesting
- Multi-ticker comparison

## License

[MIT](LICENSE)
