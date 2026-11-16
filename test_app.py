"""Focused tests for the CatalogIQ browser front end."""

import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from unittest.mock import patch

from app import CatalogIQHandler, render_page


def test_render_page_escapes_question_without_expanding_template_tokens() -> None:
    page = render_page(question='<script>alert("x")</script>{error}')

    assert "&lt;script&gt;" in page
    assert '<script>alert("x")</script>' not in page
    assert "{error}" in page
    assert '<p class="error"' not in page


def test_agent_markdown_formats_tables_and_escapes_raw_html() -> None:
    answer = (
        "## Comparison\n\n"
        "| Vendor | Price |\n"
        "|:--|--:|\n"
        "| **A** | $10 |\n"
        "| <img src=x onerror=alert(1)> | $12 |\n\n"
        "- Lowest price"
    )
    page = render_page(answer=answer)

    assert "<h2>Comparison</h2>" in page
    assert '<div class="comparison-list"><article class="comparison-card">' in page
    assert "<dt>Price</dt><dd>$10</dd>" in page
    assert "<table>" not in page
    assert "| Vendor | Price |" not in page
    assert "<strong>A</strong>" in page
    assert "<ul><li>Lowest price</li></ul>" in page
    assert "<img src=x" not in page
    assert "&lt;img" in page


def test_agent_pipe_rows_without_separator_are_formatted_as_cards() -> None:
    page = render_page(answer="Vendor | Price\nSeasonal Source | $16.75")

    assert '<div class="comparison-list"><article class="comparison-card">' in page
    assert "<span>Vendor: </span>Seasonal Source" in page
    assert "<dt>Price</dt><dd>$16.75</dd>" in page
    assert "| Price" not in page


def test_agent_error_response_does_not_expose_exception_details() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), CatalogIQHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        body = urlencode({"question": "Compare brake pads"}).encode("utf-8")
        request = Request(
            f"http://127.0.0.1:{server.server_port}/",
            data=body,
            method="POST",
        )
        with patch("app.ask_agent", side_effect=RuntimeError("NRP_API_KEY=private-value")):
            try:
                urlopen(request)
            except HTTPError as response:
                page = response.read().decode("utf-8")
                assert response.code == 500
            else:
                raise AssertionError("Expected the app to return an error response.")

        assert "private-value" not in page
        assert "could not finish this request" in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
