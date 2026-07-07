# Contributing to MarketMind

## Prerequisites

- Python 3.11+
- An Anthropic API key (free tier works for development)

```bash
git clone https://github.com/your-username/marketmind-llm-finance.git
cd marketmind-llm-finance
pip install -e .
pip install -r requirements-dev.txt
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=<your key>
```

## Running the stack

```bash
# Offline tests (no API key or network needed)
pytest tests/ -v

# API server
uvicorn marketmind.api:app --reload

# Streamlit UI (start API server first)
streamlit run app.py
```

## Running tests

All tests are offline — `yfinance`, `feedparser`, and the Anthropic client are mocked:

```bash
pytest tests/ -v
```

No `ANTHROPIC_API_KEY` is required to run the test suite.

## Project structure

| File | Purpose |
|---|---|
| `src/marketmind/data.py` | `get_snapshot()` and `get_news()` — yfinance + feedparser data layer |
| `src/marketmind/analyst.py` | `build_context()` + `ask()` — context builder and Claude integration |
| `src/marketmind/api.py` | FastAPI endpoints: `GET /snapshot/{ticker}`, `POST /query` |
| `src/marketmind/cli.py` | CLI entry point: `python -m marketmind.cli TICKER "question"` |
| `app.py` | Streamlit frontend |

## Adding a new data field

1. Add the field to the `Fundamentals` dataclass in `data.py`.
2. Populate it inside `get_snapshot()`.
3. Reference it in `build_context()` in `analyst.py` (skip `None` values).
4. Add the field to `tests/fixtures/snap_AAPL.json` and assert on it in `tests/test_data.py`.

## Code style

- No formatter enforced; keep lines ≤ 100 characters.
- No external type-checking CI step.

## Opening a PR

1. Run `pytest tests/ -v` locally and confirm it exits 0.
2. Open a PR against `main` — CI will run the same test suite automatically.
