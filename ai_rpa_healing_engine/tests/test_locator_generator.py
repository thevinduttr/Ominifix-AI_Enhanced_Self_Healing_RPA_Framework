"""
Tests for LocatorGenerator — candidate generation and scoring.

Tests:
  - ID-based candidate returned with score 100
  - Aria-label fallback when no id
  - XPath fallback for bare elements (class-only)
  - Empty HTML returns []
  - pick_best returns highest-scored candidate
  - Multiple attribute candidates generated
"""

import pytest
from src.locator_gen.locator_generator import LocatorGenerator


@pytest.fixture
def gen():
    return LocatorGenerator()


# ── ID-based locators ──

class TestIdBasedLocator:
    def test_id_returns_score_100(self, gen):
        html = '<input id="email" type="email" />'
        candidates = gen.generate_candidates(html)
        id_cands = [c for c in candidates if c["value"] == "#email"]
        assert len(id_cands) == 1
        assert id_cands[0]["score"] == 100

    def test_tag_id_returns_score_95(self, gen):
        html = '<input id="username" type="text" />'
        candidates = gen.generate_candidates(html)
        tag_id = [c for c in candidates if c["value"] == "input#username"]
        assert len(tag_id) == 1
        assert tag_id[0]["score"] == 95

    def test_pick_best_prefers_id(self, gen):
        html = '<input id="search" name="q" placeholder="Search" type="text" />'
        candidates = gen.generate_candidates(html)
        best = gen.pick_best(candidates)
        assert best is not None
        assert best["value"] == "#search"
        assert best["score"] == 100


# ── Attribute-based fallback (no id) ──

class TestAttributeFallback:
    def test_aria_label_fallback(self, gen):
        html = '<input type="text" aria-label="Username" />'
        candidates = gen.generate_candidates(html)
        aria_cands = [c for c in candidates if 'aria-label="Username"' in c["value"]]
        assert len(aria_cands) >= 1
        assert all(c["score"] in [75, 80] for c in aria_cands)

    def test_name_attribute_fallback(self, gen):
        html = '<input type="text" name="email" />'
        candidates = gen.generate_candidates(html)
        name_cands = [c for c in candidates if 'name="email"' in c["value"]]
        assert len(name_cands) >= 1

    def test_placeholder_fallback(self, gen):
        html = '<input type="text" placeholder="Enter city" />'
        candidates = gen.generate_candidates(html)
        ph_cands = [c for c in candidates if 'placeholder="Enter city"' in c["value"]]
        assert len(ph_cands) >= 1

    def test_multiple_attributes(self, gen):
        html = '<input type="email" name="email" placeholder="Email" aria-label="Email Address" />'
        candidates = gen.generate_candidates(html)
        # Should have name, placeholder, aria-label, type — at least 4 attribute-based
        attr_cands = [c for c in candidates if c["score"] in [75, 80]]
        assert len(attr_cands) >= 4


# ── XPath fallback ──

class TestXPathFallback:
    def test_xpath_generated_for_bare_element(self, gen):
        html = '<span class="icon-close"></span>'
        candidates = gen.generate_candidates(html)
        xpath_cands = [c for c in candidates if c["type"] == "xpath"]
        assert len(xpath_cands) >= 1
        assert xpath_cands[0]["score"] == 40

    def test_xpath_uses_id_if_present(self, gen):
        html = '<button id="submit">Submit</button>'
        candidates = gen.generate_candidates(html)
        xpath_cands = [c for c in candidates if c["type"] == "xpath"]
        assert len(xpath_cands) == 1
        assert "@id=" in xpath_cands[0]["value"]

    def test_xpath_for_div_with_class_only(self, gen):
        html = '<div class="card"><p>Content</p></div>'
        candidates = gen.generate_candidates(html)
        xpath_cands = [c for c in candidates if c["type"] == "xpath"]
        assert len(xpath_cands) >= 1
        assert xpath_cands[0]["value"].startswith("//div")


# ── Empty / invalid HTML ──

class TestEmptyInput:
    def test_empty_string_returns_empty(self, gen):
        assert gen.generate_candidates("") == []

    def test_whitespace_returns_empty(self, gen):
        assert gen.generate_candidates("   ") == []

    def test_none_returns_empty(self, gen):
        assert gen.generate_candidates(None) == []

    def test_no_tag_returns_empty(self, gen):
        assert gen.generate_candidates("just plain text") == []


# ── pick_best ──

class TestPickBest:
    def test_pick_best_returns_none_for_empty(self, gen):
        assert gen.pick_best([]) is None

    def test_pick_best_returns_highest_score(self, gen):
        candidates = [
            {"type": "css", "value": ".myclass", "score": 60},
            {"type": "css", "value": "#myid", "score": 100},
            {"type": "xpath", "value": "//div", "score": 40},
        ]
        best = gen.pick_best(candidates)
        assert best["value"] == "#myid"
        assert best["score"] == 100

    def test_class_candidate_generated(self, gen):
        html = '<div class="card-body active"></div>'
        candidates = gen.generate_candidates(html)
        class_cands = [c for c in candidates if c["score"] == 60]
        assert len(class_cands) >= 1
        assert "card-body" in class_cands[0]["value"]
