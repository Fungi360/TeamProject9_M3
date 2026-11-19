"""Tests for changes made from Catalog IQ user testing feedback (Nov 2026)."""

import json

from app import render_page
from catalog_mcp_server import (
    compare_vendor_catalogs,
    find_category_in_text,
    normalize_category,
    product_links,
)


def test_misspelled_categories_are_corrected() -> None:
    assert normalize_category("resturant gloves") == "restaurant nitrile gloves"
    assert normalize_category("brake pdas") == "brake pads"
    assert normalize_category("holliday string lights") == "holiday string lights"


def test_unrelated_items_are_not_forced_into_a_category() -> None:
    assert normalize_category("christmas tree") == "christmas tree"
    result = json.loads(compare_vendor_catalogs("christmas tree"))
    assert "error" in result
    assert len(result["example_questions"]) == 3


def test_category_found_in_free_text_question() -> None:
    assert find_category_in_text("Best place to purchase restaurant gloves?") == "restaurant nitrile gloves"
    assert find_category_in_text("Which string lights give me the best bang for my buck?") == "holiday string lights"
    assert find_category_in_text("cheapest brake pdas for my shop") == "brake pads"
    assert find_category_in_text("Best place near me to purchase a Christmas tree") is None


def test_each_vendor_record_has_product_and_reviews_links() -> None:
    result = json.loads(compare_vendor_catalogs("brake pads"))
    for vendor in result["vendors"]:
        assert vendor["product_url"].startswith("https://www.amazon.com/s?")
        assert "s=review-rank" in vendor["reviews_url"]


def test_affiliate_tag_is_added_when_configured(monkeypatch) -> None:
    record = {"product": "Blue nitrile gloves"}
    monkeypatch.delenv("AMAZON_ASSOCIATE_TAG", raising=False)
    assert "tag=" not in product_links(record)["product_url"]
    monkeypatch.setenv("AMAZON_ASSOCIATE_TAG", "catalogiq-20")
    links = product_links(record)
    assert "tag=catalogiq-20" in links["product_url"]
    assert "tag=catalogiq-20" in links["reviews_url"]


def test_landing_page_has_one_line_hook_and_examples() -> None:
    page = render_page()
    assert "Compare vendor prices and quality for your business in seconds." in page
    assert "holiday string lights, restaurant gloves, and brake pads" in page
    assert 'class="product-links"' not in page


def test_answer_page_shows_two_links_per_vendor() -> None:
    page = render_page("Best place to purchase restaurant gloves?", answer="FoodSafe Supply is cheapest.")
    assert page.count("View product") == 2
    assert page.count("Read reviews") == 2
    assert "Kitchen Direct" in page


def test_no_links_for_questions_outside_the_catalog() -> None:
    page = render_page("Best place to buy a Christmas tree?", answer="No catalog found.")
    assert 'class="product-links"' not in page
