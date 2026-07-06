"""LLM analysis pipeline: context builder and Anthropic API integration."""

from __future__ import annotations

from collections.abc import Iterator

import anthropic
from dotenv import load_dotenv

from marketmind.data import Snapshot, NewsItem, get_snapshot, get_news


SYSTEM_PROMPT = (
    "You are a financial analyst assistant. Answer the user's question using ONLY "
    "the data provided in the context block below. You MUST cite specific numbers "
    "from the context (e.g. \"P/E of 28.5\", \"closed at $171.80 on 2024-05-01\"). "
    "Do not speculate beyond the provided data. If the data is insufficient, say so explicitly."
)


def _fmt_market_cap(cap: int) -> str:
    if cap >= 1_000_000_000_000:
        return f"${cap / 1_000_000_000_000:.2f}T"
    if cap >= 1_000_000_000:
        return f"${cap / 1_000_000_000:.2f}B"
    if cap >= 1_000_000:
        return f"${cap / 1_000_000:.2f}M"
    return f"${cap:,}"


def build_context(snapshot: Snapshot, news: list[NewsItem]) -> str:
    """Serialise snapshot + news into a compact Markdown block (< 1 500 tokens)."""
    lines: list[str] = [f"# {snapshot.ticker} Market Data\n"]

    # Section 1: Price History (summary only, not every row)
    lines.append("## Price History (last 30 days)")
    if snapshot.history:
        last = snapshot.history[-1]
        highs = [r["high"] for r in snapshot.history]
        lows = [r["low"] for r in snapshot.history]
        lines.append(f"- Last close: ${last['close']:.2f} on {last['date']}")
        lines.append(f"- 30d high: ${max(highs):.2f}")
        lines.append(f"- 30d low: ${min(lows):.2f}")
    else:
        lines.append("- No price history available")
    lines.append("")

    # Section 2: Fundamentals (skip None values)
    lines.append("## Fundamentals")
    f = snapshot.fundamentals
    field_map = [
        ("P/E ratio", f.pe_ratio, lambda v: f"{v:.2f}"),
        ("EPS (trailing)", f.eps, lambda v: f"${v:.2f}"),
        ("52-week high", f.week_52_high, lambda v: f"${v:.2f}"),
        ("52-week low", f.week_52_low, lambda v: f"${v:.2f}"),
        ("Market cap", f.market_cap, lambda v: _fmt_market_cap(int(v))),
        ("Analyst target", f.analyst_target, lambda v: f"${v:.2f}"),
        ("Currency", f.currency, lambda v: v),
    ]
    for label, value, fmt in field_map:
        if value is not None:
            lines.append(f"- {label}: {fmt(value)}")
    lines.append("")

    # Section 3: Recent News
    lines.append("## Recent News")
    if news:
        for item in news[:10]:
            lines.append(f"- [{item.title}]({item.url})")
    else:
        lines.append("- No recent news available")
    lines.append("")

    return "\n".join(lines)


def ask(
    ticker: str,
    question: str,
    stream: bool = True,
) -> str | Iterator[str]:
    """Fetch live data, build context, call Anthropic API.

    If stream=True, returns a generator yielding text chunks.
    If stream=False, returns the full response string.
    Reads ANTHROPIC_API_KEY from environment (via python-dotenv).
    """
    load_dotenv()

    client = anthropic.Anthropic()
    snapshot = get_snapshot(ticker)
    news = get_news(ticker)
    context = build_context(snapshot, news)

    user_message = f"Context:\n{context}\n\nQuestion: {question}"
    messages = [{"role": "user", "content": user_message}]

    if stream:
        def _stream_chunks() -> Iterator[str]:
            with client.messages.stream(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
            ) as s:
                yield from s.text_stream

        return _stream_chunks()
    else:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text
