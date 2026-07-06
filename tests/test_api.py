"""Unit tests for the FastAPI application (all network/LLM calls mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from marketmind.api import app
from marketmind.data import Fundamentals, NewsItem, Snapshot

client = TestClient(app)

_SNAPSHOT = Snapshot(
    ticker="AAPL",
    history=[{"date": "2024-05-01", "open": 170.0, "high": 172.0, "low": 169.0, "close": 171.0, "volume": 1000000}],
    fundamentals=Fundamentals(
        pe_ratio=28.5,
        eps=6.13,
        week_52_high=199.62,
        week_52_low=164.08,
        market_cap=2_740_000_000_000,
        analyst_target=195.0,
        currency="USD",
    ),
)

_NEWS = [NewsItem(title="Apple hits record", url="https://example.com/1", published="2024-05-01")]


def test_snapshot_returns_200() -> None:
    with patch("marketmind.api.get_snapshot", return_value=_SNAPSHOT), \
         patch("marketmind.api.get_news", return_value=_NEWS):
        response = client.get("/snapshot/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert "history" in data
    assert "fundamentals" in data
    assert "news" in data


def test_snapshot_invalid_ticker_still_200() -> None:
    stub = Snapshot(
        ticker="NOTREAL",
        history=[],
        fundamentals=Fundamentals(None, None, None, None, None, None, None),
    )
    with patch("marketmind.api.get_snapshot", return_value=stub), \
         patch("marketmind.api.get_news", return_value=[]):
        response = client.get("/snapshot/NOTREAL")
    assert response.status_code == 200
    assert response.json()["ticker"] == "NOTREAL"


def test_query_streams_text_event_stream() -> None:
    with patch("marketmind.api.ask", return_value=iter(["hello", " world"])):
        response = client.post("/query", json={"ticker": "AAPL", "question": "Is it overvalued?"})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "data: hello" in response.text
    assert "data: [DONE]" in response.text


def test_query_missing_field_returns_422() -> None:
    response = client.post("/query", json={})
    assert response.status_code == 422
