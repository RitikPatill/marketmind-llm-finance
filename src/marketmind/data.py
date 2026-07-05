"""Data layer: fetches price history, fundamentals, and news for a ticker."""

from __future__ import annotations

from dataclasses import dataclass

import feedparser
import yfinance as yf


@dataclass
class Fundamentals:
    pe_ratio: float | None
    eps: float | None
    week_52_high: float | None
    week_52_low: float | None
    market_cap: int | None
    analyst_target: float | None
    currency: str | None


@dataclass
class Snapshot:
    ticker: str
    history: list[dict]  # rows: {date, open, high, low, close, volume}
    fundamentals: Fundamentals


@dataclass
class NewsItem:
    title: str
    url: str
    published: str  # ISO-8601 string, best-effort


def get_snapshot(ticker: str) -> Snapshot:
    """Return 30-day OHLCV history and key fundamentals for *ticker*."""
    t = yf.Ticker(ticker)

    df = t.history(period="30d")
    df = df.reset_index()
    history: list[dict] = []
    for _, row in df.iterrows():
        history.append(
            {
                "date": row["Date"].strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            }
        )

    info = t.info
    fundamentals = Fundamentals(
        pe_ratio=info.get("trailingPE"),
        eps=info.get("trailingEps"),
        week_52_high=info.get("fiftyTwoWeekHigh"),
        week_52_low=info.get("fiftyTwoWeekLow"),
        market_cap=info.get("marketCap"),
        analyst_target=info.get("targetMeanPrice"),
        currency=info.get("currency"),
    )

    return Snapshot(ticker=ticker.upper(), history=history, fundamentals=fundamentals)


def get_news(ticker: str) -> list[NewsItem]:
    """Return up to 10 recent news headlines for *ticker* via Yahoo Finance RSS."""
    url = (
        f"https://feeds.finance.yahoo.com/rss/2.0/headline"
        f"?s={ticker}&region=US&lang=en-US"
    )
    feed = feedparser.parse(url)
    items: list[NewsItem] = []
    for entry in feed.entries[:10]:
        items.append(
            NewsItem(
                title=getattr(entry, "title", ""),
                url=getattr(entry, "link", ""),
                published=getattr(entry, "published", ""),
            )
        )
    return items
