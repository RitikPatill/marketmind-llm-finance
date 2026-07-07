"""MarketMind — Streamlit frontend (M5).

All Streamlit UI calls are inside main() so the three pure helpers
(fetch_snapshot, stream_answer, render_chart) can be imported and unit-tested
without a running Streamlit server.

streamlit is imported lazily inside main() to avoid import-time failures
when the module is loaded by the test suite in non-Streamlit environments.
"""

from __future__ import annotations

from typing import Iterator

import httpx
import plotly.graph_objects as go

BASE_URL = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Pure helpers — importable without Streamlit running
# ---------------------------------------------------------------------------


def fetch_snapshot(ticker: str) -> dict:
    """GET /snapshot/{ticker} → dict.  Raises RuntimeError on failure."""
    try:
        resp = httpx.get(f"{BASE_URL}/snapshot/{ticker}", timeout=15)
    except httpx.ConnectError:
        raise RuntimeError(
            f"Cannot reach the backend at {BASE_URL}. "
            "Start it with: uvicorn marketmind.api:app --reload"
        )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Backend returned HTTP {resp.status_code} for ticker '{ticker}'. "
            "Check that the ticker is valid and the server is running."
        )
    return resp.json()


def stream_answer(ticker: str, question: str) -> Iterator[str]:
    """POST /query → SSE stream → yields text chunks."""
    with httpx.stream(
        "POST",
        f"{BASE_URL}/query",
        json={"ticker": ticker, "question": question},
        timeout=60,
    ) as response:
        for line in response.iter_lines():
            decoded = line if isinstance(line, str) else line.decode("utf-8")
            decoded = decoded.rstrip("\r\n")
            if decoded.startswith("data: "):
                chunk = decoded[len("data: "):]
                if chunk == "[DONE]":
                    break
                yield chunk


def render_chart(history: list[dict]) -> None:
    """Render a Plotly candlestick chart into the current Streamlit column."""
    import streamlit as st  # lazy import — only used when Streamlit is running

    dates = [h["Date"] for h in history]
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=dates,
                open=[h["Open"] for h in history],
                high=[h["High"] for h in history],
                low=[h["Low"] for h in history],
                close=[h["Close"] for h in history],
                increasing_line_color="#26a69a",
                decreasing_line_color="#ef5350",
            )
        ]
    )
    fig.update_layout(
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="white"),
        xaxis=dict(
            color="white",
            gridcolor="#2d2d2d",
            rangeslider_visible=False,
        ),
        yaxis=dict(color="white", gridcolor="#2d2d2d"),
        margin=dict(l=10, r=10, t=30, b=10),
        title=dict(text="Price History (30d)", font=dict(color="white", size=14)),
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Preset examples
# ---------------------------------------------------------------------------

EXAMPLES = [
    ("NVDA", "Is NVIDIA overvalued right now?"),
    ("ASML", "Summarise the last week of news for ASML"),
    ("SAP", "What are the key risks for SAP?"),
]

# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------


def main() -> None:
    import streamlit as st  # lazy import — safe for test imports

    st.set_page_config(page_title="MarketMind", layout="wide", page_icon="📈")

    # Belt-and-suspenders dark theme CSS (supplements .streamlit/config.toml)
    st.markdown(
        """
        <style>
        .stApp { background-color: #0e1117; }
        .answer-panel {
            background-color: #161b22;
            border-radius: 8px;
            padding: 1rem;
            border: 1px solid #30363d;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Session state defaults
    st.session_state.setdefault("question", "")
    st.session_state.setdefault("ticker", "AAPL")

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------
    st.sidebar.title("📈 MarketMind")
    st.sidebar.markdown(
        "Ask a question about any stock and get a cited answer grounded in live data."
    )
    st.sidebar.divider()

    ticker = st.sidebar.text_input(
        "Ticker",
        value=st.session_state["ticker"],
        max_chars=10,
        key="ticker_input",
    ).upper().strip()
    st.session_state["ticker"] = ticker

    st.sidebar.markdown("**Try an example:**")
    for ex_ticker, ex_question in EXAMPLES:
        if st.sidebar.button(ex_question, use_container_width=True):
            st.session_state["ticker"] = ex_ticker
            st.session_state["question"] = ex_question
            st.rerun()

    st.sidebar.divider()
    st.sidebar.caption(
        "Powered by [Claude](https://anthropic.com) · data via yfinance & Yahoo Finance RSS"
    )

    # ------------------------------------------------------------------
    # Main area — two columns
    # ------------------------------------------------------------------
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.header("Ask a question")
        question = st.text_area(
            "Your question",
            value=st.session_state["question"],
            height=120,
            placeholder='e.g. "Is NVIDIA overvalued right now?"',
            label_visibility="collapsed",
        )
        st.session_state["question"] = question

        analyse_clicked = st.button("Analyse", type="primary", use_container_width=True)

    # ------------------------------------------------------------------
    # On submit
    # ------------------------------------------------------------------
    if analyse_clicked:
        if not ticker:
            st.error("Please enter a ticker symbol.")
            return
        if not question.strip():
            st.error("Please enter a question.")
            return

        # Fetch snapshot (for chart)
        with st.spinner(f"Fetching data for {ticker}…"):
            try:
                snapshot = fetch_snapshot(ticker)
            except RuntimeError as exc:
                st.error(str(exc))
                return

        # Render chart in right column
        with right_col:
            st.header(f"{ticker} — Price Chart")
            history = snapshot.get("history", [])
            if history:
                render_chart(history)
            else:
                st.info("No price history available for this ticker.")

        # Stream the LLM answer into left column
        with left_col:
            st.divider()
            st.subheader("Analysis")
            try:
                st.write_stream(stream_answer(ticker, question))
            except RuntimeError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Unexpected error while streaming answer: {exc}")
    else:
        # Show placeholder when no query yet
        with right_col:
            st.header("Price Chart")
            st.info(
                "Enter a ticker and question, then click **Analyse** to see the chart."
            )


if __name__ == "__main__":
    main()
