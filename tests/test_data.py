"""Unit tests for marketmind.data — all network calls are patched."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from marketmind.data import Fundamentals, NewsItem, Snapshot, get_news, get_snapshot

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "snap_AAPL.json"


@pytest.fixture
def fixture_data() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def _make_history_df() -> pd.DataFrame:
    rows = [
        {"Date": pd.Timestamp("2024-05-01"), "Open": 170.1, "High": 172.5, "Low": 169.3, "Close": 171.8, "Volume": 54321000},
        {"Date": pd.Timestamp("2024-05-02"), "Open": 171.8, "High": 174.0, "Low": 171.2, "Close": 173.5, "Volume": 61234000},
    ]
    return pd.DataFrame(rows)


def _make_info() -> dict:
    return {
        "trailingPE": 28.5,
        "trailingEps": 6.43,
        "fiftyTwoWeekHigh": 199.62,
        "fiftyTwoWeekLow": 164.08,
        "marketCap": 2740000000000,
        "targetMeanPrice": 195.0,
        "currency": "USD",
    }


class TestGetSnapshotShape:
    def test_returns_snapshot_dataclass(self):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_history_df()
        mock_ticker.info = _make_info()

        with patch("marketmind.data.yf.Ticker", return_value=mock_ticker):
            result = get_snapshot("AAPL")

        assert isinstance(result, Snapshot)
        assert result.ticker == "AAPL"

    def test_history_rows_are_plain_dicts(self):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_history_df()
        mock_ticker.info = _make_info()

        with patch("marketmind.data.yf.Ticker", return_value=mock_ticker):
            result = get_snapshot("AAPL")

        assert len(result.history) == 2
        row = result.history[0]
        assert isinstance(row, dict)
        assert isinstance(row["date"], str), "date must be a string, not Timestamp"
        assert set(row.keys()) == {"date", "open", "high", "low", "close", "volume"}

    def test_history_is_json_serialisable(self):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_history_df()
        mock_ticker.info = _make_info()

        with patch("marketmind.data.yf.Ticker", return_value=mock_ticker):
            result = get_snapshot("AAPL")

        serialised = json.dumps(result.history)  # must not raise
        assert serialised

    def test_fundamentals_fields(self):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_history_df()
        mock_ticker.info = _make_info()

        with patch("marketmind.data.yf.Ticker", return_value=mock_ticker):
            result = get_snapshot("AAPL")

        f = result.fundamentals
        assert isinstance(f, Fundamentals)
        assert f.pe_ratio == 28.5
        assert f.eps == 6.43
        assert f.week_52_high == 199.62
        assert f.week_52_low == 164.08
        assert f.market_cap == 2740000000000
        assert f.analyst_target == 195.0
        assert f.currency == "USD"


class TestGetSnapshotMissingFields:
    def test_all_fundamentals_none_when_info_empty(self):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_history_df()
        mock_ticker.info = {}  # no keys at all

        with patch("marketmind.data.yf.Ticker", return_value=mock_ticker):
            result = get_snapshot("AAPL")

        f = result.fundamentals
        assert f.pe_ratio is None
        assert f.eps is None
        assert f.week_52_high is None
        assert f.week_52_low is None
        assert f.market_cap is None
        assert f.analyst_target is None
        assert f.currency is None


def _make_fake_feed(n: int):
    entries = []
    for i in range(n):
        e = SimpleNamespace(
            title=f"Headline {i}",
            link=f"https://example.com/{i}",
            published=f"2024-05-{i + 1:02d}T10:00:00",
        )
        entries.append(e)
    feed = SimpleNamespace(entries=entries)
    return feed


class TestGetNewsShape:
    def test_returns_at_most_10_items(self):
        with patch("marketmind.data.feedparser.parse", return_value=_make_fake_feed(15)):
            result = get_news("AAPL")

        assert len(result) == 10

    def test_each_item_has_required_attrs(self):
        with patch("marketmind.data.feedparser.parse", return_value=_make_fake_feed(3)):
            result = get_news("AAPL")

        for item in result:
            assert isinstance(item, NewsItem)
            assert item.title
            assert item.url
            assert isinstance(item.published, str)

    def test_fewer_than_10_entries_returned_as_is(self):
        with patch("marketmind.data.feedparser.parse", return_value=_make_fake_feed(5)):
            result = get_news("AAPL")

        assert len(result) == 5


class TestGetNewsEmptyFeed:
    def test_empty_feed_returns_empty_list(self):
        with patch("marketmind.data.feedparser.parse", return_value=_make_fake_feed(0)):
            result = get_news("AAPL")

        assert result == []
