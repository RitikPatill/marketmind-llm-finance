"""Unit tests for marketmind.analyst — no network calls, no API key required."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from marketmind.data import Fundamentals, NewsItem, Snapshot
from marketmind.analyst import build_context, ask

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "snap_AAPL.json"


@pytest.fixture()
def aapl_data() -> tuple[Snapshot, list[NewsItem]]:
    raw = json.loads(FIXTURE_PATH.read_text())
    s = raw["snapshot"]
    fundamentals = Fundamentals(**s["fundamentals"])
    snapshot = Snapshot(
        ticker=s["ticker"],
        history=s["history"],
        fundamentals=fundamentals,
    )
    news = [NewsItem(**n) for n in raw["news"]]
    return snapshot, news


def test_build_context_contains_ticker(aapl_data):
    snapshot, news = aapl_data
    output = build_context(snapshot, news)
    assert "AAPL" in output


def test_build_context_contains_fundamentals(aapl_data):
    snapshot, news = aapl_data
    output = build_context(snapshot, news)
    assert "28.50" in output  # pe_ratio formatted as 28.50


def test_build_context_contains_news_title(aapl_data):
    snapshot, news = aapl_data
    output = build_context(snapshot, news)
    assert news[0].title in output


def test_build_context_token_budget(aapl_data):
    snapshot, news = aapl_data
    output = build_context(snapshot, news)
    assert len(output.split()) < 1200


def test_ask_non_stream_returns_string(aapl_data):
    snapshot, news = aapl_data

    fake_content = MagicMock()
    fake_content.text = "test answer"
    fake_response = MagicMock()
    fake_response.content = [fake_content]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = fake_response

    with (
        patch("marketmind.analyst.anthropic.Anthropic", return_value=mock_client),
        patch("marketmind.analyst.get_snapshot", return_value=snapshot),
        patch("marketmind.analyst.get_news", return_value=news),
        patch("marketmind.analyst.load_dotenv"),
    ):
        result = ask("AAPL", "test?", stream=False)

    assert result == "test answer"


def test_ask_stream_yields_chunks(aapl_data):
    snapshot, news = aapl_data

    mock_stream = MagicMock()
    mock_stream.__enter__ = lambda s: mock_stream
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.text_stream = iter(["hello", " world"])

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    with (
        patch("marketmind.analyst.anthropic.Anthropic", return_value=mock_client),
        patch("marketmind.analyst.get_snapshot", return_value=snapshot),
        patch("marketmind.analyst.get_news", return_value=news),
        patch("marketmind.analyst.load_dotenv"),
    ):
        chunks = list(ask("AAPL", "test?", stream=True))

    assert chunks == ["hello", " world"]
