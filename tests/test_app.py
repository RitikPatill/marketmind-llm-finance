"""Smoke tests for app.py helper functions.

No network access, no Streamlit runtime, no API key required.
All httpx calls are patched with unittest.mock.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app import fetch_snapshot, stream_answer


class TestFetchSnapshot(unittest.TestCase):
    def test_fetch_snapshot_returns_dict(self):
        canned = {"history": [{"Date": "2024-01-01", "Open": 100.0, "High": 110.0, "Low": 95.0, "Close": 105.0}]}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = canned

        with patch("httpx.get", return_value=mock_resp) as mock_get:
            result = fetch_snapshot("AAPL")

        mock_get.assert_called_once()
        self.assertEqual(result, canned)

    def test_fetch_snapshot_raises_on_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("httpx.get", return_value=mock_resp):
            with self.assertRaises(RuntimeError):
                fetch_snapshot("BADTICKER")

    def test_fetch_snapshot_raises_on_connect_error(self):
        with patch("httpx.get", side_effect=Exception("connection refused")):
            # Should propagate as some exception (ConnectError or RuntimeError)
            with self.assertRaises(Exception):
                fetch_snapshot("AAPL")


class TestStreamAnswer(unittest.TestCase):
    def test_stream_answer_yields_chunks(self):
        lines = ["data: hello\n", "data: world\n", "data: [DONE]\n"]

        # Build a mock context manager for httpx.stream
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = iter(lines)
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("httpx.stream", return_value=mock_response):
            chunks = list(stream_answer("AAPL", "What is the P/E ratio?"))

        self.assertEqual(chunks, ["hello", "world"])

    def test_stream_answer_stops_at_done(self):
        lines = ["data: first\n", "data: [DONE]\n", "data: should_not_appear\n"]

        mock_response = MagicMock()
        mock_response.iter_lines.return_value = iter(lines)
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("httpx.stream", return_value=mock_response):
            chunks = list(stream_answer("AAPL", "Any question"))

        self.assertEqual(chunks, ["first"])


if __name__ == "__main__":
    unittest.main()
