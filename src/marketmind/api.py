"""FastAPI application exposing MarketMind endpoints."""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from marketmind.analyst import ask
from marketmind.data import get_news, get_snapshot

app = FastAPI(title="MarketMind")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    ticker: str
    question: str


@app.get("/snapshot/{ticker}")
def snapshot(ticker: str) -> dict:
    """Return raw price history, fundamentals, and news for a ticker."""
    ticker = ticker.upper().strip()
    snap = get_snapshot(ticker)
    news = get_news(ticker)
    return {
        "ticker": snap.ticker,
        "history": snap.history,
        "fundamentals": dataclasses.asdict(snap.fundamentals),
        "news": [{"title": n.title, "url": n.url, "published": n.published} for n in news],
    }


@app.post("/query")
def query(req: QueryRequest) -> StreamingResponse:
    """Stream an LLM answer for the given ticker and question as SSE."""
    ticker = req.ticker.upper().strip()
    chunks: Iterator[str] = ask(ticker, req.question, stream=True)  # type: ignore[assignment]

    def _sse_generator() -> Iterator[str]:
        for chunk in chunks:
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(_sse_generator(), media_type="text/event-stream")
